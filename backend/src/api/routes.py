from datetime import datetime
from typing import Optional, List
import uuid
from git import Repo
from fastapi import APIRouter, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from qdrant_client import QdrantClient
from git_repo_parser.stats_parser import StatsParser
from vector_store.chunk_store import ChunkStoreHandler
from vector_store.retrive_generate import ChatLLM
from config.config import QDRANT_HOST, QDRANT_API_KEY
import json
import os
from .utils import *


router = APIRouter()


@router.get("/healthcheck")
async def health_check():
    """Check system health and vector store connection"""
    try:
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    

@router.post("/create/user")
async def check_create_user(user_id: str):
    try:
        await dynamo_db_service.create_user(user_id)
        return {"success": True}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@router.post("/create/session/uploadproject")
async def upload_folder(
    user_id: str = Form(...),
    local_dir: str = Form(...),
    repo: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
):
    try:
        local_dir_flag = local_dir == "True"
        if local_dir_flag:
            project_name = git_clone_service.folder_upload(user_id, files)
        else:
            project_name = git_clone_service.clone(user_id, repo)
        
        # Create Session
        await dynamo_db_service.create_session(user_id, project_name)

        return {"success": True, "session_id": project_name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/storage")
async def extract_repository(user_id: str, session_id: str):
    try:
        project_path = get_project_path(user_id, session_id)
        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")
        # Need to work on Vector DB logic for user specific
        result = repo_service.process_repository(project_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/list")
async def get_session_list(user_id: str) -> List[Dict]:
    """List all the Sessions for user"""
    try:
        session_list = await dynamo_db_service.get_user_sessions(user_id)
        return session_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/session/rename")
async def session_rename(user_id: str, session_id: str, updated_name):
    """List all the Sessions for user"""
    try:
        await dynamo_db_service.rename_session(user_id, session_id, updated_name)
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/session/delete")
async def session_delete(user_id: str, session_id: str):
    """Delete all the messages and Session from DB and Local Project for that session"""
    try:
        git_clone_service.folder_delete(user_id, session_id)
        await dynamo_db_service.delete_session(user_id, session_id)
        
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/session/data")
async def get_session_data(user_id: str, session_id: str):
    """Get the session data/chat"""
    try:
        session_data = await dynamo_db_service.get_session_messages(user_id, session_id)
        return session_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@router.post("/stats")
async def analyze_repository(user_id: str, session_id: str):
    try:
        project_path = get_project_path(user_id, session_id)
        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")
        print(project_path)
        parser = StatsParser(project_path)
        return await parser.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_code(request: QueryRequest, llm: ChatLLM = Depends(lambda: get_llm("azure"))):
    """
    Endpoint for regular queries.

    Args:
        request (QueryRequest): Query request with text and limit

    Returns:
        dict: Query results with contexts and response
    """
    try:
        project_path = get_project_path(request.user_id, request.session_id) 

        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")

        collection_info = ChunkStoreHandler(project_path)
        contexts, response = await llm.invoke(
            request.ast_flag,
            collection_name=collection_info.collection_name,
            user_id=request.user_id,
            session_id=request.session_id,
            sys_prompt=request.sys_prompt,
            query=request.query,
            limit=request.limit,
            temperature=0.1
        )
        evaluation_metrics = evaluator.evaluate(
            use_llm=request.use_llm == "True",
            request=request.query,
            contexts=contexts,
            response=response.content,
        )
        
        await dynamo_db_service.create_message(request.user_id, request.session_id, request.query, response.content, evaluation_metrics)
        
        return {
            "query": request.query,
            "response": response.content,
            "metric": evaluation_metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.post("/query/stream")
# async def query_code_stream(request: QueryRequest, llm: ChatLLM = Depends(get_llm)):
#     """
#     Endpoint for streaming queries.

#     Args:
#         request (QueryRequest): Query request with text and limit

#     Returns:
#         StreamingResponse: Stream of query results
#     """
#     try:
#         if not os.path.exists(request.path):
#             raise HTTPException(status_code=400, detail="project Not Avilable")
#         collection_info = ChunkStoreHandler(request.path)

#         async def generate():
#             for contexts, partial_response in llm.stream(
#                 request.ast_flag,
#                 collection_name=collection_info.collection_name,
#                 query=request.query,
#                 limit=request.limit,
#                 temperature=0,
#             ):
#                 yield json.dumps(
#                     {"query": request.query, "contexts": contexts, "partial_response": partial_response.content}
#                 ) + "\n"

#         return StreamingResponse(generate(), media_type="text/event-stream")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/reindex")
# async def reindex_vectoredb(repo: FileID):
#     chat_history_path = get_chat_history_class.base_path
#     file_name = os.path.join(chat_history_path, f"{repo.file_id}.json")
#     project_path, _ = get_project_path(file_name)
#     if not os.path.exists(project_path):
#         raise HTTPException(status_code=400, detail="project Not Avilable")
#     chunkhandler = ChunkStoreHandler(project_path)
#     collection_name = chunkhandler.collection_name
#     client = chunkhandler.client
#     try:
#         # Delete the collection
#         if collection_name:
#             client.delete_collection(collection_name=collection_name)
#         try:
#             result = repo_service.process_repository(project_path)
#             return result
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")