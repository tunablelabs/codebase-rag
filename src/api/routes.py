from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from git_repo_parser.stats_doc_parser import StatsDocParser
from git_repo_parser.base_parser import CodeParser
from vector_store.query_handler import query_with_context
from vector_store.config import POC_COLLECTION_NAME
from vector_store.chunk_store import ChunkStoreHandler

router = APIRouter()

class RepoPath(BaseModel):
    path: str
    collection_name: Optional[str] = POC_COLLECTION_NAME
    
class QueryRequest(BaseModel):
    """Request model for querying the code"""
    query: str
    limit: int = 3
    collection_name: Optional[str] = POC_COLLECTION_NAME

@router.post("/stats")
async def analyze_repository(repo: RepoPath):
    try:
        parser = StatsDocParser(repo.path)
        return await parser.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/analyze")
async def extract_repository(repo: RepoPath):
    try:
        # Initialize parsers and handlers
        parser = CodeParser()
        chunk_store = ChunkStoreHandler()
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
async def query_code(request: QueryRequest):
    """
    Endpoint to query the codebase using natural language.
    Uses the existing query_handler implementation.
    """
    try:
        contexts, response = query_with_context(
            request.query,
            request.limit
        )

        return {
            "query": request.query,
            "contexts": contexts,
            "response": response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Check system health and vector store connection"""
    try:
        chunk_store = ChunkStoreHandler()
        collection_info = chunk_store.get_collection_info()
        return {
            "status": "healthy",
            "collection_info": collection_info
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))