from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging
from src.vector_store.embeddings import EmbeddingsHandler
from src.vector_store.config import POC_COLLECTION_NAME
from src.vector_store.query_handler import query_with_context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Code RAG API")

# Initialize handler
embeddings_handler = EmbeddingsHandler()

# Request/Response Models


class CodeIngestRequest(BaseModel):
    """Request model for code ingestion"""
    code: str
    file_path: str
    collection_name: Optional[str] = POC_COLLECTION_NAME


class QueryRequest(BaseModel):
    """Request model for querying the code"""
    query: str
    limit: int = Field(default=3, ge=1, le=10)
    collection_name: Optional[str] = POC_COLLECTION_NAME


@app.post("/ingest")
async def ingest_code(request: CodeIngestRequest):
    """
    Endpoint to ingest code into the vector database.
    Handles chunking and storage in one operation.
    """
    try:
        success = embeddings_handler.process_and_store_code(
            request.code,
            request.file_path
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to process and store code")

        return {
            "status": "success",
            "file_path": request.file_path
        }

    except Exception as e:
        logger.error(f"Ingestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
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
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Check system health and vector store connection"""
    try:
        collection_info = embeddings_handler.get_collection_info()
        return {
            "status": "healthy",
            "collection_info": collection_info
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
