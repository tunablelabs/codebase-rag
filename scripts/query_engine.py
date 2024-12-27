import sys
import json
import os
import ast
import json
import re
import subprocess
import sys
import nest_asyncio
from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Document,
    PromptTemplate,
)
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from llama_index.core import StorageContext

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
QDRANT_HOST = os.getenv('QDRANT_HOST')
QDRANT_PORT = int(os.getenv('QDRANT_PORT'))
API_Key = os.getenv('QDRANT_API_KEY')

def get_qdrant_client():
    """Initialize and return Qdrant client."""
    #print("Initializing Qdrant client")
    
    try:
        if QDRANT_HOST == "localhost":
            client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                prefer_grpc=False
            )
        else:
            client = QdrantClient(
                url=QDRANT_HOST,
                api_key=API_Key,
                prefer_grpc=False
            )
        #print(f"Successfully connected to Qdrant instance")
        return client
    except Exception as e:
        print(f"Failed to connect to Qdrant: {str(e)}")

def get_embedding_model():
    """Initialize the embedding model if not already loaded."""
    global embed_model
    if embed_model is None:
        api_key = os.getenv('OPENAI_API_KEY')
        embed_model = OpenAIEmbedding(model='text-embedding-ada-002')
    return embed_model


def parse_github_url(url):
    """Parse GitHub URL to extract owner and repository name."""
    pattern = r"https://github\.com/([^/]+)/([^/]+)"
    match = re.match(pattern, url)
    return match.groups() if match else (None, None)


def clone_github_repo(repo_url,repo_path):
    """Clone the GitHub repository."""
    try:
        #print('Cloning the repository...')
        subprocess.run(["git", "clone", repo_url,repo_path], check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository: {e}")


def generate_repo_ast(repo_path):
    """Generate an AST summary for all Python files in the repository."""
    repo_summary = {}
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(('.py','.ts','.js','.ipynb')):
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


def setup_query_engine(github_url,systm_prompt,ast_bool):
    """Setup the query engine for interacting with the repository."""
    try:
        if github_url.startswith('http'):
            owner, repo = github_url.split("/")[-2:]
            if not owner or not repo:
                return None, None
            repo_path = './repos/'+repo
            if not os.path.exists('./repos/'):
                os.makedirs('./repos/')
            if not os.path.exists(repo_path):
                clone_github_repo(github_url,repo_path)
        else:
            owner, repo= 'user', github_url
            github_url='./repos/'+github_url
            if not os.path.exists(github_url):
                return None, None
            else:
                repo_path=github_url
        try:
            loader = SimpleDirectoryReader(
                input_dir=repo_path,
                required_exts=[".py", ".ipynb", ".js", ".ts", ".md"],
                recursive=True
            )
        except Exception as e:
            return 'no_files', None
        docs = loader.load_data()
        if not docs:
            #print("No data found. The repository might be empty.")
            return None, None

        # Add AST summary to documents
        if ast_bool:
            repo_ast = generate_repo_ast(repo_path)
            ast_text = json.dumps(repo_ast, indent=2)
            docs.append(Document(text=f"Repository AST:\n{ast_text}", metadata={"source": "repo_ast"}))

        # Create vector store index
        embedding_model = get_embedding_model()
        collection_name = f"{owner}_{repo}".lower()
        qdrant_client = get_qdrant_client()
        collections = qdrant_client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)
        
        if not collection_exists:
            #print('adding new collections')
             # Add collection creation
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": 1536,  # OpenAI embedding dimension
                    "distance": "Cosine"
                }
            )
            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=collection_name,
                batch_size=100,  # Explicit batch size
                prefer_grpc=False,  # Use REST API
                timeout=60  # Seconds
            )
            # Create storage context explicitly
            storage_context = StorageContext.from_defaults(vector_store=vector_store, persist_dir=None )
            index = VectorStoreIndex.from_documents(
                    docs,
                    storage_context=storage_context,
                    embed_model=get_embedding_model(),
                    show_progress=True
                )
        else:
            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=collection_name
            )
            # Create storage context with persist_dir=None to avoid local storage
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=None
            )
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                storage_context=storage_context,
                embed_model=get_embedding_model(),
                show_progress=True)
            
        
        #index = VectorStoreIndex.from_documents(docs, embed_model=embedding_model, show_progress=True)

        # Customize the query prompt
        qa_prompt_tmpl_str = (
            "Context information is below.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "{system_prompt}\n"
            "Query: {query_str}\n"
            "Answer: "
        )
        qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)
        qa_prompt_tmpl= qa_prompt_tmpl.format(system_prompt=systm_prompt)
        qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl)
        query_engine = index.as_query_engine(
            text_qa_template=qa_prompt_tmpl,
            similarity_top_k=4
        )
        # print("Query engine setup complete. Ready to answer questions!")
        if ast_bool:
            return query_engine, repo_ast
        else:
            return query_engine, None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None


# Ensure all output is JSON
def output_json(data):
    print(json.dumps(data))

if __name__ == "__main__":
    try:
        github_url = sys.argv[1]
        question = sys.argv[2]
        system_prompt= sys.argv[3]
        ast_bool= sys.argv[4]
        ast_bool= True if ast_bool=='true' else False
        query_engine, repo_ast = setup_query_engine(github_url,system_prompt,ast_bool)
        if query_engine=='no_files':
            output_json({"response": "This github repo doesn't contain python or javascript files, as of now we are only supporting Python and Javascript"})
        else:
            if query_engine:
                if ast_bool:
                    query = (
                        f"Given the repository AST:\n{json.dumps(repo_ast, indent=2)}\n\n"
                        f"{question} Considering the file structure, explain in detail."
                    )
                else:
                    query = (
                        f"{question} Considering the repository files, explain in detail."
                    )
                response = query_engine.query(query)
                output_json({"response": response.response})
            else:
                output_json({"error": "Failed to set up query engine"})
    except Exception as e:
        output_json({"error": str(e)})