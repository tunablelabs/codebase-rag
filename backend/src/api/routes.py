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


@router.get("/project/indexlist")
async def get_indexed_project():
    client = QdrantClient(url=QDRANT_HOST, api_key=QDRANT_API_KEY)
    repo_index_list = []
    collections = client.get_collections()
    for collection in collections.collections:
        index_details = collection.name.split("-")
        owner_repo_name = "/".join(index_details)
        repo_index_list.append(owner_repo_name)
    try:
        return {"project_list": repo_index_list}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/create/chat")
async def create_chat() -> Dict:
    try:
        chat_history_path = get_chat_history_class.base_path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = uuid.uuid4().hex[:9]
        file_path = os.path.join(chat_history_path, f"{file_id}.json")

        while os.path.exists(file_path):
            file_id = uuid.uuid4().hex[:9]
            file_path = os.path.join(chat_history_path, f"{file_id}.json")

        data = {"created_at": timestamp, "last_updated": timestamp, "repo_name": "", "chat": []}

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        return {"success": True, "file_id": file_id}

    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/chat/history")
async def get_chat_history() -> List[Dict]:
    """List all the Chat Sessions"""
    try:
        chat_history_path = get_chat_history_class.base_path
        chat_files = Path(chat_history_path).glob("*")
        chats = []

        for file_path in chat_files:
            with open(file_path) as f:
                chat_data = json.load(f)

            chat_preview = ""
            if chat_data.get("chat"):
                last_msg = str(chat_data["chat"][-1].get("user", "")).split("\n")[-1]
                chat_preview = last_msg[:10]

            chats.append({
                "file_id": file_path.stem,
                "last_message_preview": chat_preview,
                "last_updated": chat_data["last_updated"],
                "repo_name": chat_data.get("repo_name", ""),
                "messages": chat_data.get("chat", []) 
            })

        sorted_chats = sorted(chats, key=lambda x: x["last_updated"], reverse=True)[:10]
        return [{
            "file_id": chat["file_id"],
            "last_message_preview": chat["last_message_preview"],
            "repo_name": chat["repo_name"],
            "messages": chat["messages"]
        } for chat in sorted_chats]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat/history/{file_id}")
async def get_chat(file_id: str):
    try:
        chat_history_path = get_chat_history_class.base_path
        file_path = os.path.join(chat_history_path, f"{file_id}.json")
        with open(file_path, "r") as f:
            chat_data = json.load(f)
        return chat_data["chat"]
        l
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.post("/uploadproject")
async def upload_folder(
    file_id: str = Form(...),
    local_dir: str = Form(...),
    repo: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
):
    try:
        local_dir_flag = local_dir == "True"
        if local_dir_flag:
            project_name = git_clone_service.folder_upload(files)
        else:
            project_name = git_clone_service.clone(repo)
        await update_project_name(file_id, project_name)

        return {"success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats")
async def analyze_repository(repo: FileID):
    try:
        chat_history_path = get_chat_history_class.base_path
        file_name = os.path.join(chat_history_path, f"{repo.file_id}.json")
        project_path, _ = get_project_path(file_name)
        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")
        print(project_path)
        parser = StatsParser(project_path)
        return await parser.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/storage")
async def extract_repository(repo: FileID):
    try:
        chat_history_path = get_chat_history_class.base_path
        file_name = os.path.join(chat_history_path, f"{repo.file_id}.json")
        project_path, _ = get_project_path(file_name)
        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")
        result = repo_service.process_repository(project_path)
        return result
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
        chat_history_path = get_chat_history_class.base_path
        file_name = os.path.join(chat_history_path, f"{request.file_id}.json")
        project_path, _ = get_project_path(file_name)

        if not os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="project Not Avilable")

        collection_info = ChunkStoreHandler(project_path)
        contexts, response = llm.invoke(
            request.ast_flag,
            collection_name=collection_info.collection_name,
            user_id=request.file_id,
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
        await update_chat_data(request.file_id, request.query, response.content)
        return {
            "query": request.query,
            "response": response.content,
            "metric": evaluation_metrics,
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
        if not os.path.exists(request.path):
            raise HTTPException(status_code=400, detail="project Not Avilable")
        collection_info = ChunkStoreHandler(request.path)

        async def generate():
            for contexts, partial_response in llm.stream(
                request.ast_flag,
                collection_name=collection_info.collection_name,
                query=request.query,
                limit=request.limit,
                temperature=0,
            ):
                yield json.dumps(
                    {"query": request.query, "contexts": contexts, "partial_response": partial_response.content}
                ) + "\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex")
async def reindex_vectoredb(repo: FileID):
    chat_history_path = get_chat_history_class.base_path
    file_name = os.path.join(chat_history_path, f"{repo.file_id}.json")
    project_path, _ = get_project_path(file_name)
    if not os.path.exists(project_path):
        raise HTTPException(status_code=400, detail="project Not Avilable")
    chunkhandler = ChunkStoreHandler(project_path)
    collection_name = chunkhandler.collection_name
    client = chunkhandler.client
    try:
        # Delete the collection
        if collection_name:
            client.delete_collection(collection_name=collection_name)
        try:
            result = repo_service.process_repository(project_path)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")