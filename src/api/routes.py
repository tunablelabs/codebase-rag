from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from git_repo_parser.stats_parser import StatsParser
from git_repo_parser.base_parser import CodeParser
from vector_store.query_handler import query_with_context
from vector_store.chunk_store import ChunkStoreHandler
from vector_store.retrive_generate import ChatLLM
from config.config import OPENAI_API_KEY, QDRANT_HOST, QDRANT_API_KEY
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
        _llm_instance = ChatLLM(
            api_key=OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            qdrant_url=QDRANT_HOST,
            qdrant_api_key=QDRANT_API_KEY
        )
    return _llm_instance


router = APIRouter()

class RepoPath(BaseModel):
    path: str
    
class QueryRequest(RepoPath):
    """Request model for querying the code"""
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
        # Create Collection name and check if collection exist, If not exist create a collection
        chunk_store = ChunkStoreHandler(repo.path)
        # Parse the repository and get chunks
        chunks = parser.parse_directory(repo.path) 
        # Store chunks in vector database
        success = chunk_store.store_chunks(chunks)
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to store chunks in vector database"
            )
        return {
            "status": "success",
            "chunks_processed": len(chunks),
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