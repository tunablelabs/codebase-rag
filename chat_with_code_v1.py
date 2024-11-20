import os
import ast
import json
import gc
import re
import uuid
import textwrap
import subprocess
import nest_asyncio
from dotenv import load_dotenv
from IPython.display import Markdown, display
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Document,
    PromptTemplate,
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Allows nested access to the event loop
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Environment setup
os.environ["HF_HOME"] = "/teamspace/studios/this_studio/weights"
os.environ["TORCH_HOME"] = "/teamspace/studios/this_studio/weights"

# Initialize the LLM
llm = OpenAI(model="gpt-4o", temperature=0, request_timeout=60.0)

# Initialize embedding model only once
embed_model = None


def get_embedding_model():
    """Initialize the embedding model if not already loaded."""
    global embed_model
    if embed_model is None:
        api_key = os.getenv('OPENAI_API_KEY')
        embed_model = OpenAIEmbedding(model='text-embedding-ada-002')
    return embed_model


# Utility functions
def parse_github_url(url):
    """Parse GitHub URL to extract owner and repository name."""
    pattern = r"https://github\.com/([^/]+)/([^/]+)"
    match = re.match(pattern, url)
    return match.groups() if match else (None, None)


def clone_github_repo(repo_url):
    """Clone the GitHub repository."""
    try:
        print('Cloning the repository...')
        subprocess.run(["git", "clone", repo_url], check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")


def generate_repo_ast(repo_path):
    """Generate an AST summary for all Python files in the repository."""
    repo_summary = {}
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    try:
                        tree = ast.parse(f.read())
                        node_counts = {}
                        for node in ast.walk(tree):
                            node_type = type(node).__name__
                            node_counts[node_type] = node_counts.get(node_type, 0) + 1
                        repo_summary[file_path] = node_counts
                    except SyntaxError:
                        repo_summary[file_path] = "Unable to parse file"
    return repo_summary


def setup_query_engine(github_url):
    """Setup the query engine for interacting with the repository."""
    owner, repo = parse_github_url(github_url)
    if not owner or not repo:
        print("Invalid GitHub repository URL.")
        return None, None

    repo_path = repo
    if not os.path.exists(repo_path):
        clone_github_repo(github_url)

    try:
        loader = SimpleDirectoryReader(
            input_dir=repo_path,
            required_exts=[".py", ".ipynb", ".js", ".ts", ".md"],
            recursive=True
        )
        docs = loader.load_data()
        if not docs:
            print("No data found. The repository might be empty.")
            return None, None

        # Add AST summary to documents
        repo_ast = generate_repo_ast(repo_path)
        ast_text = json.dumps(repo_ast, indent=2)
        docs.append(Document(text=f"Repository AST:\n{ast_text}", metadata={"source": "repo_ast"}))

        # Create vector store index
        embedding_model = get_embedding_model()
        index = VectorStoreIndex.from_documents(docs, embed_model=embedding_model, show_progress=True)

        # Customize the query prompt
        qa_prompt_tmpl_str = (
            "Context information is below.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Repository AST:\n"
            "{repo_ast}\n"
            "---------------------\n"
            "You are a coding assistant. Please answer the user's coding questions step by step, "
            "considering the code content and file structure. If unsure, say 'I don't know.'\n"
            "Query: {query_str}\n"
            "Answer: "
        )
        qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)

        query_engine = index.as_query_engine(
            text_qa_template=qa_prompt_tmpl,
            similarity_top_k=4
        )
        print("Query engine setup complete. Ready to answer questions!")
        return query_engine, repo_ast

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None


# Main execution
github_url = "https://github.com/codingwithsurya/chat-with-your-code-with-rag"
query_engine, repo_ast = setup_query_engine(github_url)

if query_engine:
    question = "What does the function in rag.py do?"
    query = (
        f"Given the repository AST:\n{json.dumps(repo_ast, indent=2)}\n\n"
        f"{question} Considering the file structure, explain in detail."
    )
    response = query_engine.query(query)
    print(response)
