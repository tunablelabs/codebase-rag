from typing import Optional, List, Dict
from git import Repo
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from git_repo_parser.stats_parser import StatsParser
from git_repo_parser.base_parser import CodeParser
from vector_store.chunk_store import ChunkStoreHandler
from vector_store.retrive_generate import ChatLLM, OpenAIProvider, AzureOpenAIProvider
from chunking.document_chunks import DocumentChunker
from evaluation import Evaluation, EvaluationMetric
from config.config import OPENAI_API_KEY, QDRANT_HOST, QDRANT_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_MODEL
import json
import os
from pathlib import Path

class GitCloneService:
    def __init__(self):
        # Get project root directory (2 levels up from current file)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        self.base_path = os.path.join(project_root, "project_repos")
        os.makedirs(self.base_path, exist_ok=True)
    
    def clone(self, repo_url: str) -> str:
        try:
            # Extract repo name from URL
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(self.base_path, repo_name)
            if os.path.exists(repo_path):
                return repo_path
                
            # Clone repository
            Repo.clone_from(repo_url, repo_path)
            return repo_path
            
        except Exception as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
        
class RepositoryStorageService:
    def __init__(self):
        self.code_parser = CodeParser()
        self.doc_chunker = DocumentChunker()

    def _create_chunk_store(self, repo_path: str) -> ChunkStoreHandler:
        """Initialize chunk store for the repository"""
        try:
            return ChunkStoreHandler(repo_path)
        except Exception as e:
            raise Exception(f"Failed to initialize chunk store: {str(e)}")

    def _process_code_chunks(self, repo_path: str) -> List[Dict]:
        """Process and parse code files"""
        try:
            return self.code_parser.parse_directory(repo_path)
        except Exception as e:
            raise Exception(f"Failed to process code files: {str(e)}")

    def _process_doc_chunks(self, repo_path: str) -> List[Dict]:
        """Process and parse document files"""
        try:
            return self.doc_chunker.parse_directory(repo_path)
        except Exception as e:
            raise Exception(f"Failed to process document files: {str(e)}")

    def _store_chunks(self, chunk_store: ChunkStoreHandler, 
                     chunks: List[Dict]) -> bool:
        """Store chunks in vector database"""
        try:
            return chunk_store.store_chunks(chunks)
        except Exception as e:
            raise Exception(f"Failed to store chunks: {str(e)}")

    def process_repository(self, repo_path: str) -> Dict:
        """Main method to process and store repository data"""
        try:
            # Initialize chunk store
            chunk_store = self._create_chunk_store(repo_path)

            # Process code and document chunks
            code_chunks = self._process_code_chunks(repo_path)
            doc_chunks = self._process_doc_chunks(repo_path)

            # Store chunks
            success_code = self._store_chunks(chunk_store, code_chunks)
            success_doc = self._store_chunks(chunk_store, doc_chunks)

            if not success_code or not success_doc:
                raise Exception("Failed to store chunks in vector database")

            return {
                "status": "success",
                "chunks_processed": len(code_chunks) + len(doc_chunks),
                "repository": repo_path
            }

        except Exception as e:
            raise Exception(f"Repository processing failed: {str(e)}")


# Initialize ChatLLM as a module-level singleton
_llm_instance = None

def get_llm() -> ChatLLM:
    """
    Dependency injection function to get or create ChatLLM instance.
    Uses singleton pattern to ensure only one instance exists.
    """
    global _llm_instance
    if _llm_instance is None:
        # For OpenAI
        openai_provider = OpenAIProvider(api_key=OPENAI_API_KEY,model="gpt-4")
        # For Azure OpenAI
        azure_provider = AzureOpenAIProvider(api_key=AZURE_OPENAI_KEY,endpoint=AZURE_OPENAI_ENDPOINT,deployment_name=AZURE_OPENAI_MODEL)
        # Initialize ChatLLM with required provider
        _llm_instance = ChatLLM(
            provider = openai_provider,
            qdrant_url=QDRANT_HOST,
            qdrant_api_key=QDRANT_API_KEY
        )
    return _llm_instance


router = APIRouter()

# Initialize service
repo_service = RepositoryStorageService()
git_clone_service = GitCloneService()

class RepoPath(BaseModel):
    path: str
    
class QueryRequest(RepoPath):
    """Request model for querying the code"""
    ast_flag: str
    query: str
    limit: int = 3
    

@router.get("/healthcheck")
async def health_check():
    """Check system health and vector store connection"""
    try:
        return {
            "status": "healthy"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    
@router.get("/project/indexlist")
async def get_indexed_project():
    client = QdrantClient(
            url=QDRANT_HOST,
            api_key=QDRANT_API_KEY
        )
    repo_index_list = []
    collections = client.get_collections()
    for collection in collections.collections:
        index_details = collection.name.split("-")
        owner_repo_name = "/".join(index_details)
        repo_index_list.append(owner_repo_name)
    try:
        return {
            "project_list" : repo_index_list
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))       
    

@router.post("/stats")
async def analyze_repository(repo: RepoPath):
    try:
        repo_path = git_clone_service.clone(repo.path)
        parser = StatsParser(repo_path)
        return await parser.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/storage")
async def extract_repository(repo: RepoPath):
    try:
        repo_path = git_clone_service.clone(repo.path)
        result = repo_service.process_repository(repo_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_code(request: QueryRequest, llm: ChatLLM = Depends(get_llm)):
    """
    Endpoint for regular queries.
    
    Args:
        request (QueryRequest): Query request with text and limit
        
    Returns:
        dict: Query results with contexts and response
    """
    try:
        repo_path = git_clone_service.clone(request.path)
        collection_info = ChunkStoreHandler(repo_path)
        contexts, response = llm.invoke(
            request.ast_flag,
            collection_name = collection_info.collection_name,
            query=request.query,
            limit=request.limit,
            temperature=0
        )
        evaluation_metrics = Evaluation.get_evaluation(
            request=request.query,
            context=contexts,
            response=response.content,
            metrics=[
                EvaluationMetric.ANSWER_RELEVANCY, 
                EvaluationMetric.FAITHFULNESS,
                EvaluationMetric.CONTEXT_RELEVANCY,
            ]
        )
        return {
            "query": request.query,
            "contexts": contexts,
            "response": response.content,
            "metric": evaluation_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query/stream")
async def query_code_stream(request: QueryRequest, llm: ChatLLM = Depends(get_llm)):
    """
    Endpoint for streaming queries.
    
    Args:
        request (QueryRequest): Query request with text and limit
        
    Returns:
        StreamingResponse: Stream of query results
    """
    try:
        repo_path = git_clone_service.clone(request.path)
        collection_info = ChunkStoreHandler(repo_path)
        async def generate():
            for contexts, partial_response in llm.stream(
                request.ast_flag,
                collection_name = collection_info.collection_name,
                query=request.query,
                limit=request.limit,
                temperature=0
            ):
                yield json.dumps({
                    "query": request.query,
                    "contexts": contexts,
                    "partial_response": partial_response.content
                }) + "\n"
        
        return StreamingResponse(
            generate(),
            media_type='text/event-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/reindex")
async def reindex_vectoredb(repo: RepoPath):
    repo_path = git_clone_service.clone(repo.path)
    chunkhandler = ChunkStoreHandler(repo_path)
    collection_name = chunkhandler.collection_name
    client = chunkhandler.client
    try:
        # Delete the collection
        if collection_name:
            client.delete_collection(collection_name=collection_name)
        try:
            result = repo_service.process_repository(repo_path)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Failed to delete collection: {str(e)}")