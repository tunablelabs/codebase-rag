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
    """Check system health and vector store connection"""
    try:
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
   
    
@router.post("/follow-up-questions")
async def follow_up_questions(request: QuestionRequest):
    """To Generate follow-up-questions for the input question"""
    try:
        question = request.question
        resposne = follow_up_question(question)
        return QuestionResponse(follow_up_questions=resposne)
        
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/create/user")
async def check_create_user(user_id: UserID):
    try:
        response = await dynamo_db_service.create_user(user_id.user_id)
        return response
    
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
async def extract_repository(user_session: UserSessionID):
    try:
        project_path = get_project_path(user_session.user_id, user_session.session_id)
        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")
        # Need to work on Vector DB logic for user specific
        result = repo_service.process_repository(project_path, user_session.user_id, user_session.session_id)
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
async def session_rename(rename_request: Rename):
    """List all the Sessions for user"""
    try:
        await dynamo_db_service.rename_session(rename_request.user_id, rename_request.session_id, rename_request.updated_name)
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/session/delete")
async def session_delete(user_session: UserSessionID):
    """Delete all the messages and Session from DB and Local Project for that session"""
    try:
        project_path = get_project_path(user_session.user_id, user_session.session_id) 

        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")
        
        # Delete Repo
        git_clone_service.folder_delete(user_session.user_id, user_session.session_id)
        # Dynamo DB purge
        await dynamo_db_service.delete_session(user_session.user_id, user_session.session_id)
        # Qdrent DB collection delection
        chunk_store = ChunkStoreHandler(project_path, user_session.user_id, user_session.session_id)
        chunk_store.delete_collection(chunk_store.collection_name)
             
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
async def analyze_repository(user_session: UserSessionID):
    try:
        project_path = get_project_path(user_session.user_id, user_session.session_id)
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

        collection_info = ChunkStoreHandler(project_path, request.user_id, request.session_id)
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
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Helper function to send JSON with custom encoder
        async def send_json_with_custom_encoder(data):
            json_str = json.dumps(data, cls=CustomJSONEncoder)
            await websocket.send_text(json_str)
        
        # Wait for the query request data
        query_data = await websocket.receive_json()
        
        # Convert to QueryRequest model
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
        except Exception as e:
            await send_json_with_custom_encoder({"error": f"Invalid request format: {str(e)}"})
            await websocket.close()
            return
        
        project_path = get_project_path(request.user_id, request.session_id) 

        if not os.path.exists(project_path):
            await send_json_with_custom_encoder({"error": "Project Not Available"})
            await websocket.close()
            return
        
        collection_info = ChunkStoreHandler(project_path, request.user_id, request.session_id)
        
        # Store the complete response for evaluation and DB storage
        complete_response = []
        last_contexts = None
        
        # Stream all LLM response chunks immediately without any evaluation
        try:

            limit_checker = await dynamo_db_service.check_for_limit(request.user_id,
                                                                    request.session_id,
                                                                    request.query)
            logger.info(f'limit_checker:{limit_checker}')
            # Check if message creation was successful or if user hit limits
            # If the user has reached (or exceeded) their limit
            if not limit_checker.get("success", True) and "limit_info" in limit_checker:
                limit_message = limit_checker["limit_info"].get("notification_message", "Daily message limit reached")
                await send_json_with_custom_encoder({
                    "limit_reached": True,
                    "message": limit_message,
                    "remaining": 0,
                    "complete": True
                })
                # Stop streaming since user is out of messages
                await websocket.close()
                return

            remaining = limit_checker.get("limit_info", {}).get("remaining_messages", None)
            if remaining is not None and remaining <= 5:
                await send_json_with_custom_encoder({
                    "notification": f"Warning: You have only {remaining} messages left."
                })
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
                # Save contexts from the chunk
                last_contexts = contexts
                
                # Save response chunk
                if partial_response and hasattr(partial_response, 'content'):
                    complete_response.append(partial_response.content)
                
                    # Stream the chunk immediately via WebSocket without metrics
                    await send_json_with_custom_encoder({
                        "query": request.query, 
                        "contexts": contexts, 
                        "partial_response": partial_response.content,
                        "metric": None  # No metrics during streaming
                    })

                    # Small delay between chunks
                    import asyncio
                    await asyncio.sleep(0.02)

            # After the stream is completely finished, perform evaluation
            full_response = "".join(complete_response)
            evaluation_metrics = evaluator.evaluate(
                use_llm=request.use_llm == "True",
                request=request.query,
                contexts=last_contexts,
                response=full_response,
            )
            
            # Save to DynamoDB
            await dynamo_db_service.create_message(
                request.user_id, 
                request.session_id, 
                request.query, 
                full_response, 
                evaluation_metrics
            )
            
            # Send a final update with the metrics via WebSocket
            await send_json_with_custom_encoder({
                "query": request.query, 
                "contexts": last_contexts, 
                "partial_response": "",  # Empty content since this is just for metrics
                "metric": evaluation_metrics,
                "complete": True  # Signal that streaming is complete
            })
            
        except Exception as e:
            print(traceback.format_exc())
            logger.info(f"Streaming error: {str(e)}")
            await send_json_with_custom_encoder({"error": f"Streaming error: {str(e)}"})
        
        # Close the WebSocket connection
        await websocket.close()
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected")
    except Exception as e:
        logger.info(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
            await websocket.close()
        except:
            pass  # If sending the error failed, the connection is likely already closed
    
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