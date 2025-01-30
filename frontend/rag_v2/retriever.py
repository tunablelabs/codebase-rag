import logging
import os
from typing import Dict, List, Optional, Any

import tiktoken
from anytree import Node, RenderTree
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.schema import BaseRetriever, Document, SystemMessage, HumanMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_voyageai import VoyageAIEmbeddings
from pydantic import Field

from rag_v2.code_symbols import get_code_symbols
from rag_v2.data_manager import DataManager, GitHubRepoManager
from rag_v2.llm import build_llm_via_langchain
from rag_v2.reranker import build_reranker
from rag_v2.vector_store import build_vector_store_from_args

import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_model_context_size(model_name):
    model_context_sizes = {
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "claude-1": 9000,
        "claude-1-100k": 100000,
        # Add other models as needed
    }
    return model_context_sizes.get(model_name, 4096)

def num_tokens_from_messages(messages, model_name):
    """Returns the number of tokens used by a list of messages."""
    encoding = tiktoken.encoding_for_model(model_name)
    if "gpt-3.5-turbo" in model_name or "gpt-4" in model_name:
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # Every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
        num_tokens += 2  # Every reply is primed with <im_start>assistant
        return num_tokens
    else:
        # For other models
        return sum(len(encoding.encode(m.content)) for m in messages)
    
class LLMRetriever(BaseRetriever):
    """Custom Langchain retriever based on an LLM.

    Builds a representation of the folder structure of the repo, feeds it to an LLM, and asks the LLM for the most
    relevant files for a particular user query, expecting it to make decisions based solely on file names.

    Supports both OpenAI and Anthropic models.
    """

    repo_manager: GitHubRepoManager = Field(...)
    top_k: int = Field(...)
    llm: Any = Field(...)

    cached_repo_metadata: List[Dict] = Field(default_factory=list)
    cached_repo_files: List[str] = Field(default_factory=list)
    cached_repo_hierarchy: str = Field(default=None)

    def __init__(self, repo_manager: GitHubRepoManager, top_k: int, llm):
        super().__init__()
        self.repo_manager = repo_manager
        self.top_k = top_k
        self.llm = llm

        # Check for required API keys
        if isinstance(llm, ChatOpenAI) and not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("Please set the OPENAI_API_KEY environment variable for the LLMRetriever.")

        if isinstance(llm, ChatAnthropic) and not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("Please set the ANTHROPIC_API_KEY environment variable for the LLMRetriever.")

    @property
    def repo_metadata(self):
        if not self.cached_repo_metadata:
            self.cached_repo_metadata = [metadata for metadata in self.repo_manager.walk(get_content=False)]

            # Extracting code symbols takes quite a while, since we need to read each file from disk.
            # As a compromise, we do it for small codebases only.
            small_codebase = len(self.repo_files) <= 200
            if small_codebase:
                for metadata in self.cached_repo_metadata:
                    file_path = metadata["file_path"]
                    content = self.repo_manager.read_file(file_path)
                    metadata["code_symbols"] = get_code_symbols(file_path, content)

        return self.cached_repo_metadata

    @property
    def repo_files(self):
        if not self.cached_repo_files:
            self.cached_repo_files = set(metadata["file_path"] for metadata in self.repo_metadata)
        return self.cached_repo_files

    @property
    def repo_hierarchy(self):
        """Produces a string that describes the structure of the repository. Depending on how big the codebase is, it
        might include class and method names."""
        if self.cached_repo_hierarchy is None:
            render = LLMRetriever._render_file_hierarchy(self.repo_metadata, include_classes=True, include_methods=True)
            model_context_size = get_model_context_size(self.llm.model_name)
            max_tokens = model_context_size - 1000  # Reserve 1000 tokens for other parts of the prompt.

            def count_tokens(text):
                encoding = tiktoken.encoding_for_model(self.llm.model_name)
                return len(encoding.encode(text))

            if count_tokens(render) > max_tokens:
                logging.info("File hierarchy is too large; excluding methods.")
                render = LLMRetriever._render_file_hierarchy(
                    self.repo_metadata, include_classes=True, include_methods=False
                )
                if count_tokens(render) > max_tokens:
                    logging.info("File hierarchy is still too large; excluding classes.")
                    render = LLMRetriever._render_file_hierarchy(
                        self.repo_metadata, include_classes=False, include_methods=False
                    )
                    if count_tokens(render) > max_tokens:
                        logging.info("File hierarchy is still too large; truncating.")
                        encoding = tiktoken.encoding_for_model(self.llm.model_name)
                        tokens = encoding.encode(render)[:max_tokens]
                        render = encoding.decode(tokens)
            self.cached_repo_hierarchy = render
        return self.cached_repo_hierarchy

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None) -> List[Document]:
        """Retrieve relevant documents for a given query."""
        filenames = self._ask_llm_to_retrieve(user_query=query, top_k=self.top_k)
        documents = []
        for filename in filenames:
            document = Document(
                page_content=self.repo_manager.read_file(filename),
                metadata={"file_path": filename, "url": self.repo_manager.url_for_file(filename)},
            )
            documents.append(document)
        return documents

    def _ask_llm_to_retrieve(self, user_query: str, top_k: int) -> List[str]:
        """Feeds the file hierarchy and user query to the LLM and asks which files might be relevant."""
        repo_hierarchy = str(self.repo_hierarchy)
        sys_prompt = f"""
You are a retriever system. You will be given a user query and a list of files in a GitHub repository, together with the class names in each file.

For instance:
folder1
    folder2
        folder3
            file123.py
                ClassName1
                ClassName2
                ClassName3
means that there is a file with path folder1/folder2/folder3/file123.py, which contains classes ClassName1, ClassName2, and ClassName3.

Your task is to determine the top {top_k} files that are most relevant to the user query.
DO NOT RESPOND TO THE USER QUERY DIRECTLY. Instead, respond with full paths to relevant files that could contain the answer to the query. Say absolutely nothing else other than the file paths.

Here is the file hierarchy of the GitHub repository, together with the class names in each file:

{repo_hierarchy}
"""

        # We are deliberately repeating the "DO NOT RESPOND TO THE USER QUERY DIRECTLY" instruction here.
        augmented_user_query = f"""
User query: {user_query}

DO NOT RESPOND TO THE USER QUERY DIRECTLY. Instead, respond with full paths to relevant files that could contain the answer to the query. Say absolutely nothing else other than the file paths.
"""
        response = self._call_via_llm(sys_prompt, augmented_user_query)

        response_text = response.strip()
        files_from_llm = response_text.split("\n")
        validated_files = []

        for filename in files_from_llm:
            filename = filename.strip()
            if filename not in self.repo_files:
                if "/" not in filename:
                    # This is most likely some natural language excuse from the LLM; skip it.
                    continue
                # Try a few heuristics to fix the filename.
                filename = LLMRetriever._fix_filename(filename, self.repo_manager.repo_id)
                if filename not in self.repo_files:
                    # The heuristics failed; try to find the closest filename in the repo.
                    filename = LLMRetriever._find_closest_filename(filename, self.repo_files)
            if filename in self.repo_files:
                validated_files.append(filename)
        return validated_files

    def _call_via_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Calls the LLM with the given prompts and returns the response."""
        if isinstance(self.llm, (ChatOpenAI, ChatAnthropic)):
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            # Check if the request will exceed the tokens per minute limit
            total_tokens = num_tokens_from_messages(messages, self.llm.model_name)
            tpm_limit = self._get_tpm_limit(self.llm.model_name)
            if total_tokens > tpm_limit:
                logging.error(f"Total tokens ({total_tokens}) exceed tokens per minute limit ({tpm_limit}). Reducing prompt size.")
                # Reduce the size of the repo_hierarchy or other parts of the prompt
                # You may need to further reduce the prompt here
                raise ValueError("Prompt exceeds tokens per minute limit. Reduce the size of the repository or prompt.")

            try:
                response = self.llm(messages)
                return response.content
            except openai.error.RateLimitError as e:
                logging.error(f"OpenAI RateLimitError: {e}")
                # Handle rate limit error, possibly by waiting and retrying
                time.sleep(60)  # Wait for a minute
                response = self.llm(messages)
                return response.content
        else:
            # For non-chat models
            full_prompt = system_prompt + "\n" + user_prompt
            response = self.llm(full_prompt)
            return response

    def _get_tpm_limit(self, model_name):
        """Returns the tokens per minute limit for the given model."""
        tpm_limits = {
            "gpt-4": 10000,
            "gpt-4-32k": 10000,
            "gpt-3.5-turbo": 90000,
            "gpt-3.5-turbo-16k": 90000,
            # Add other models and their limits as needed
        }
        return tpm_limits.get(model_name, 10000)  # Default to 10,000 if not specified

    @staticmethod
    def _render_file_hierarchy(
        repo_metadata: List[Dict], include_classes: bool = True, include_methods: bool = True
    ) -> str:
        """Given a list of files, produces a visualization of the file hierarchy. This hierarchy optionally includes
        class and method names, if available.

        For large codebases, including both classes and methods might exceed the token limit of the LLM. In that case,
        try setting `include_methods=False` first. If that's still too long, try also setting `include_classes=False`.

        Example:
        folder1
            folder11
                file111.md
                file112.py
                    ClassName1
                        method_name1
                        method_name2
                        method_name3
            folder12
                file121.py
                    ClassName2
                    ClassName3
        folder2
            file21.py
        """
        # The "nodepath" is the path from root to the node (e.g. huggingface/transformers/examples)
        nodepath_to_node = {}

        for metadata in repo_metadata:
            path = metadata["file_path"]
            paths = [path]

            if include_classes or include_methods:
                # Add the code symbols to the path. For instance, "folder/myfile.py/ClassName/method_name".
                for class_name, method_name in metadata.get("code_symbols", []):
                    if include_classes and class_name:
                        paths.append(path + "/" + class_name)
                    # We exclude private methods to save tokens.
                    if include_methods and method_name and not method_name.startswith("_"):
                        paths.append(
                            path + "/" + class_name + "/" + method_name if class_name else path + "/" + method_name
                        )

            for path in paths:
                items = path.split("/")
                nodepath = ""
                parent_node = None
                for item in items:
                    nodepath = f"{nodepath}/{item}"
                    if nodepath in nodepath_to_node:
                        node = nodepath_to_node[nodepath]
                    else:
                        node = Node(item, parent=parent_node)
                        nodepath_to_node[nodepath] = node
                    parent_node = node

        root_path = "/" + repo_metadata[0]["file_path"].split("/")[0]
        full_render = ""
        root_node = nodepath_to_node[root_path]
        for pre, fill, node in RenderTree(root_node):
            render = "%s%s\n" % (pre, node.name)
            # Replace special lines with empty strings to save on tokens.
            render = render.replace("└", " ").replace("├", " ").replace("│", " ").replace("─", " ")
            full_render += render
        return full_render

    @staticmethod
    def _fix_filename(filename: str, repo_id: str) -> str:
        """Attempts to "fix" a filename output by the LLM.

        Common issues with LLM-generated filenames:
        - The LLM prepends an extraneous "/".
        - The LLM omits the name of the org (e.g. "transformers/README.md" instead of "huggingface/transformers/README.md").
        - The LLM omits the name of the repo (e.g. "huggingface/README.md" instead of "huggingface/transformers/README.md").
        - The LLM omits the org/repo prefix (e.g. "README.md" instead of "huggingface/transformers/README.md").
        """
        if filename.startswith("/"):
            filename = filename[1:]
        org_name, repo_name = repo_id.split("/")
        items = filename.split("/")
        if filename.startswith(org_name) and not filename.startswith(repo_id):
            new_items = [org_name, repo_name] + items[1:]
            return "/".join(new_items)
        if not filename.startswith(org_name) and filename.startswith(repo_name):
            return f"{org_name}/{filename}"
        if not filename.startswith(org_name) and not filename.startswith(repo_name):
            return f"{org_name}/{repo_name}/{filename}"
        return filename

    @staticmethod
    def _find_closest_filename(filename: str, repo_filenames: List[str], max_edit_distance: int = 10) -> Optional[str]:
        """Returns the path in the repo with smallest edit distance from `filename`. Helpful when the `filename` was
        generated by an LLM and parts of it might have been hallucinated. Returns None if the closest path is more than
        `max_edit_distance` away. In case of a tie, returns an arbitrary closest path.
        """
        distances = [(path, Levenshtein.distance(filename, path)) for path in repo_filenames]
        distances.sort(key=lambda x: x[1])
        if distances[0][1] <= max_edit_distance:
            closest_path = distances[0][0]
            return closest_path
        return None

class RerankerWithErrorHandling(BaseRetriever):
    """Wraps a `ContextualCompressionRetriever` to catch errors during inference.

    In practice, we see occasional `requests.exceptions.ReadTimeout` from the NVIDIA reranker, which crash the entire
    pipeline. This wrapper catches such exceptions by simply returning the documents in the original order.
    """

    def __init__(self, reranker: ContextualCompressionRetriever):
        self.reranker = reranker

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        try:
            return self.reranker._get_relevant_documents(query, run_manager=run_manager)
        except Exception as e:
            logging.error(f"Error in reranker; preserving original document order from retriever. {e}")
            return self.reranker.base_retriever._get_relevant_documents(query, run_manager=run_manager)

def build_retriever_from_args(args, data_manager: Optional[DataManager] = None):
    """Builds a retriever (with optional reranking) from command-line arguments."""
    if args.llm_retriever:
        llm = build_llm_via_langchain(args.llm_provider, args.llm_model)
        retriever = LLMRetriever(GitHubRepoManager.from_args(args), top_k=args.retriever_top_k, llm=llm)

    else:
        if args.embedding_provider == "openai":
            embeddings = OpenAIEmbeddings(model=args.embedding_model)
        elif args.embedding_provider == "voyage":
            embeddings = VoyageAIEmbeddings(model=args.embedding_model)
        elif args.embedding_provider == "gemini":
            embeddings = GoogleGenerativeAIEmbeddings(model=args.embedding_model)
        else:
            embeddings = None

        retriever = build_vector_store_from_args(args, data_manager).as_retriever(
            top_k=args.retriever_top_k, embeddings=embeddings, namespace=args.index_namespace
        )

    if args.multi_query_retriever:
        retriever = MultiQueryRetriever.from_llm(
            retriever=retriever, llm=build_llm_via_langchain(args.llm_provider, args.llm_model)
        )

    reranker = build_reranker(args.reranker_provider, args.reranker_model, args.reranker_top_k)
    if reranker:
        retriever = ContextualCompressionRetriever(base_compressor=reranker, base_retriever=retriever)
    return retriever


