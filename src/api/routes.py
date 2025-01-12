from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from git_repo_parser.stats_parser import StatsParser
from git_repo_parser.base_parser import CodeParser
from vector_store.chunk_store import ChunkStoreHandler
from vector_store.retrive_generate import ChatLLM, OpenAIProvider, AzureOpenAIProvider
from chunking.document_chunks import DocumentChunker
from config.config import OPENAI_API_KEY, QDRANT_HOST, QDRANT_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_MODEL
import json


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

class RepoPath(BaseModel):
    path: str
    
class QueryRequest(RepoPath):
    """Request model for querying the code"""
    ast_flag: str
    query: str
    limit: int = 3
    

@router.get("/health_check")
async def health_check():
    """Check system health and vector store connection"""
    try:
        return {
            "status": "healthy"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/stats")
async def analyze_repository(repo: RepoPath):
    try:
        parser = StatsParser(repo.path)
        return await parser.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/data_storage")
async def extract_repository(repo: RepoPath):
    try:
        # Initialize parsers and handlers
        parser = CodeParser()
        doc_chunker = DocumentChunker()
        # Create Collection name and check if collection exist, If not exist create a collection
        chunk_store = ChunkStoreHandler(repo.path)
        # Parse the repository and get chunks for code files
        code_chunks = parser.parse_directory(repo.path) 
        # Parse the repository and get chunks for document files
        doc_chunks = doc_chunker.parse_directory(repo.path) 
        # Store chunks in vector database
        success_code_files = chunk_store.store_chunks(code_chunks)
        success_doc_files = chunk_store.store_chunks(doc_chunks)
        if not success_code_files or not success_doc_files:
            raise HTTPException(
                status_code=500, 
                detail="Failed to store chunks in vector database"
            )
        return {
            "status": "success",
            "chunks_processed": len(code_chunks)+len(doc_chunks),
            "repository": repo.path
        }
        
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
        collection_info = ChunkStoreHandler(request.path)
        contexts, response = llm.invoke(
            request.ast_flag,
            collection_name = collection_info.collection_name,
            query=request.query,
            limit=request.limit,
            temperature=0
        )
        return {
            "query": request.query,
            "contexts": contexts,
            "response": response.content
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
        collection_info = ChunkStoreHandler(request.path)
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