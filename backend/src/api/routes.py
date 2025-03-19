from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid
from git import Repo
from fastapi import APIRouter, Form, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from qdrant_client import QdrantClient
from git_repo_parser.stats_parser import StatsParser
from vector_store.chunk_store import ChunkStoreHandler
from vector_store.retrive_generate import ChatLLM
from config.config import QDRANT_HOST, QDRANT_API_KEY
import json
import os
from .utils import *
import traceback
from config.logging_config import start_log_request, info, warning, debug, error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

router = APIRouter()

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

@router.get("/healthcheck")
async def health_check():
    start_log_request()
    """Check system health and vector store connection"""
    try:
        info("Checking server health")
        return {"status": "healthy"}
    except Exception as e:
        error(f"Error with health service {e}")
        raise HTTPException(status_code=503, detail=str(e))
   
    
@router.post("/follow-up-questions")
async def follow_up_questions(request: QuestionRequest):
    start_log_request()
    """To Generate follow-up-questions for the input question"""
    try:
        info("Calling to follow up questions")
        question = request.question
        resposne = follow_up_question(question)
        return QuestionResponse(follow_up_questions=resposne)
        
    except Exception as e:
        error(f"Error with follow up service {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/create/user")
async def check_create_user(user_id: UserID):
    start_log_request()
    try:
        info("Creating user if dont exist in our DataBase")
        response = await dynamo_db_service.create_user(user_id.user_id)
        return response
    
    except Exception as e:
        error(f"Error while creating user service {e}")
        raise HTTPException(status_code=500, detail=str(e))

    
@router.post("/create/session/uploadproject")
async def upload_folder(
    user_id: str = Form(...),
    local_dir: str = Form(...),
    repo: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
):
    start_log_request()
    try:
        local_dir_flag = local_dir == "True"
        if local_dir_flag:
            info("Uploading project from local directory")
            project_name = git_clone_service.folder_upload(user_id, files)
        else:
            info("Uploading project from Git Repository")
            project_name = git_clone_service.clone(user_id, repo)
        
        info("creating session")
        await dynamo_db_service.create_session(user_id, project_name)

        return {"success": True, "session_id": project_name}

    except Exception as e:
        error(f"Error uploading project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/storage")
async def extract_repository(user_session: UserSessionID):
    start_log_request()
    try:
        info(f"Extracting repository for user {user_session.user_id}, session {user_session.session_id}")
        project_path = get_project_path(user_session.user_id, user_session.session_id)
        if not os.path.exists(project_path):
            warning(f"Project path not available: {project_path}")
            raise HTTPException(status_code=400, detail="project Not Avilable")
        
        info("Processing repository for storage")
        result = repo_service.process_repository(project_path, user_session.user_id, user_session.session_id)
        info("Repository processed successfully")
        return result
    except Exception as e:
        error(f"Error extracting repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/list")
async def get_session_list(user_id: str) -> List[Dict]:
    """List all the Sessions for user"""
    start_log_request()
    try:
        info(f"Getting session list for user: {user_id}")
        session_list = await dynamo_db_service.get_user_sessions(user_id)
        info(f"Retrieved {len(session_list)} sessions")
        return session_list
        
    except Exception as e:
        error(f"Error retrieving session list: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/session/rename")
async def session_rename(rename_request: Rename):
    """List all the Sessions for user"""
    start_log_request()
    try:
        info(f"Renaming session {rename_request.session_id} to {rename_request.updated_name}")
        await dynamo_db_service.rename_session(rename_request.user_id, rename_request.session_id, rename_request.updated_name)
        info("Session renamed successfully")
        return {"success": True}
        
    except Exception as e:
        error(f"Error renaming session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/session/delete")
async def session_delete(user_session: UserSessionID):
    """Delete all the messages and Session from DB and Local Project for that session"""
    start_log_request()
    try:
        info(f"Deleting session {user_session.session_id} for user {user_session.user_id}")
        project_path = get_project_path(user_session.user_id, user_session.session_id) 

        if not os.path.exists(project_path):
            warning(f"Project path not available: {project_path}")
            raise HTTPException(status_code=400, detail="project Not Avilable")
        
        info("Deleting repository folder")
        git_clone_service.folder_delete(user_session.user_id, user_session.session_id)
        
        info("Deleting session from DynamoDB")
        await dynamo_db_service.delete_session(user_session.user_id, user_session.session_id)
        
        info("Deleting vector collection")
        chunk_store = ChunkStoreHandler(project_path, user_session.user_id, user_session.session_id)
        chunk_store.delete_collection(chunk_store.collection_name)
        
        info("Session deleted successfully")     
        return {"success": True}
        
    except Exception as e:
        error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/session/data")
async def get_session_data(user_id: str, session_id: str):
    """Get the session data/chat"""
    start_log_request()
    try:
        info(f"Getting session data for user {user_id}, session {session_id}")
        session_data = await dynamo_db_service.get_session_messages(user_id, session_id)
        info(f"Retrieved {len(session_data)} messages")
        return session_data
        
    except Exception as e:
        error(f"Error retrieving session data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        

@router.post("/stats")
async def analyze_repository(user_session: UserSessionID):
    start_log_request()
    try:
        info(f"Analyzing repository stats for user {user_session.user_id}, session {user_session.session_id}")
        existing_stats = await dynamo_db_service.get_session_stats(user_session.user_id, user_session.session_id)
        if existing_stats:
            info(f"Returning existing stats from DB for session {user_session.session_id}")
            return existing_stats
        
        info(f"Generating new stats for session {user_session.session_id}")
        project_path = get_project_path(user_session.user_id, user_session.session_id)
        if not os.path.exists(project_path):
            warning(f"Project path not available: {project_path}")
            raise HTTPException(status_code=400, detail="project Not Avilable")
        
        info("Parsing repository stats")
        parser = StatsParser(project_path)
        stats = await parser.get_stats()
        await dynamo_db_service.update_session_stats(user_session.user_id, user_session.session_id, stats)
        info("Stats retrieved successfully")
        return stats
    except Exception as e:
        error(f"Error analyzing repository: {e}")
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
    start_log_request()
    try:
        info(f"Processing query for user {request.user_id}, session {request.session_id}")
        project_path = get_project_path(request.user_id, request.session_id) 

        if not os.path.exists(project_path):
            warning(f"Project path not available: {project_path}")
            raise HTTPException(status_code=400, detail="project Not Avilable")

        info("Initializing chunk store handler")
        collection_info = ChunkStoreHandler(project_path, request.user_id, request.session_id)
        
        info("Invoking LLM for query")
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
        
        info("Evaluating response quality")
        evaluation_metrics = evaluator.evaluate(
            use_llm=request.use_llm == "True",
            request=request.query,
            contexts=contexts,
            response=response.content,
        )
        
        info("Storing message in database")
        await dynamo_db_service.create_message(request.user_id, request.session_id, request.query, response.content, evaluation_metrics)
        
        info("Query processed successfully")
        return {
            "query": request.query,
            "response": response.content,
            "metric": evaluation_metrics,
        }
    except Exception as e:
        error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/query/stream")
async def query_code_stream_ws(
    websocket: WebSocket,
    llm: ChatLLM = Depends(lambda: get_llm("azure"))
):
    """
    WebSocket endpoint for streaming queries with evaluation metrics.

    Args:
        websocket (WebSocket): The WebSocket connection
    """
    start_log_request()
    try:
        info("Accepting WebSocket connection")
        await websocket.accept()
        
        async def send_json_with_custom_encoder(data):
            json_str = json.dumps(data, cls=CustomJSONEncoder)
            await websocket.send_text(json_str)
        
        info("Waiting for query data")
        query_data = await websocket.receive_json()
        info("Received query data")
        
        try:
            request = QueryRequest(
                user_id=query_data.get("user_id", ""),
                session_id=query_data.get("session_id", ""),
                query=query_data.get("query", ""),
                sys_prompt=query_data.get("sys_prompt", ""),
                limit=query_data.get("limit", 5),
                ast_flag=query_data.get("ast_flag", "False"),
                use_llm=query_data.get("use_llm", "False")
            )
            info(f"Processing streaming query for user {request.user_id}, session {request.session_id}")
        except Exception as e:
            error(f"Invalid request format: {e}")
            await send_json_with_custom_encoder({"error": f"Invalid request format: {str(e)}"})
            await websocket.close()
            return
        
        project_path = get_project_path(request.user_id, request.session_id) 

        if not os.path.exists(project_path):
            warning(f"Project path not available: {project_path}")
            await send_json_with_custom_encoder({"error": "Project Not Available"})
            await websocket.close()
            return
        
        info("Initializing chunk store handler")
        collection_info = ChunkStoreHandler(project_path, request.user_id, request.session_id)
        
        complete_response = []
        last_contexts = None
        
        try:
            info("Checking usage limits")
            limit_checker = await dynamo_db_service.check_for_limit(request.user_id,
                                                                    request.session_id,
                                                                    request.query)
            logger.info(f'limit_checker:{limit_checker}')
            
            if not limit_checker.get("success", True) and "limit_info" in limit_checker:
                limit_message = limit_checker["limit_info"].get("notification_message", "Daily message limit reached")
                warning(f"User {request.user_id} reached message limit: {limit_message}")
                await send_json_with_custom_encoder({
                    "limit_reached": True,
                    "message": limit_message,
                    "remaining": 0,
                    "complete": True
                })
                info("Closing WebSocket due to message limit")
                await websocket.close()
                return

            remaining = limit_checker.get("limit_info", {}).get("remaining_messages", None)
            if remaining is not None and remaining <= 5:
                warning(f"User {request.user_id} has only {remaining} messages left")
                await send_json_with_custom_encoder({
                    "notification": f"Warning: You have only {remaining} messages left."
                })
                
            info("Starting LLM streaming response")
            async for contexts, partial_response in llm.stream(
                ast_flag=request.ast_flag,
                collection_name=collection_info.collection_name,
                user_id=request.user_id,
                session_id=request.session_id,
                sys_prompt=request.sys_prompt,
                query=request.query,
                limit=request.limit,
                temperature=0.1
            ):
                last_contexts = contexts
                
                if partial_response and hasattr(partial_response, 'content'):
                    complete_response.append(partial_response.content)
                
                    await send_json_with_custom_encoder({
                        "query": request.query, 
                        "contexts": contexts, 
                        "partial_response": partial_response.content,
                        "metric": None
                    })

                    import asyncio
                    await asyncio.sleep(0.02)

            info("Stream complete, performing evaluation")
            full_response = "".join(complete_response)
            evaluation_metrics = evaluator.evaluate(
                use_llm=request.use_llm == "True",
                request=request.query,
                contexts=last_contexts,
                response=full_response,
            )
            
            info("Storing message in database")
            await dynamo_db_service.create_message(
                request.user_id, 
                request.session_id, 
                request.query, 
                full_response, 
                evaluation_metrics
            )
            
            info("Sending final metrics to client")
            await send_json_with_custom_encoder({
                "query": request.query, 
                "contexts": last_contexts, 
                "partial_response": "",
                "metric": evaluation_metrics,
                "complete": True
            })
            
        except Exception as e:
            error(f"Streaming error: {str(e)}")
            await send_json_with_custom_encoder({"error": f"Streaming error: {str(e)}"})
        
        info("Closing WebSocket connection")
        await websocket.close()
        
    except WebSocketDisconnect:
        warning(f"WebSocket disconnected")
    except Exception as e:
        error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
            await websocket.close()
        except:
            pass
        
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