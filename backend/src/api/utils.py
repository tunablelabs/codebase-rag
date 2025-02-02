from datetime import datetime
import json
import shutil
from typing import List, Dict
from fastapi import HTTPException, logger
from git import Repo
from pydantic import BaseModel
from git_repo_parser.base_parser import CodeParser
from vector_store.chunk_store import ChunkStoreHandler
from vector_store.retrive_generate import ChatLLM
from chunking.document_chunks import DocumentChunker
from evaluation import Evaluator, LLMMetricType, NonLLMMetricType
from config.config import OPENAI_API_KEY, QDRANT_HOST, QDRANT_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_MODEL
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import logging
from enum import Enum
from vector_store.providers import OpenAIProvider, AzureOpenAIProvider, ClaudeProvider


class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    CLAUDE = "claude"

class FileID(BaseModel):
    file_id: str
      
class QueryRequest(FileID):
    """Request model for querying the code"""
    use_llm: str
    ast_flag: str
    query: str
    limit: int = 3
    


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
                return repo_name
                
            # Clone repository
            Repo.clone_from(repo_url, repo_path)
            return repo_name
            
        except Exception as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
        
    def folder_upload(self, input_files) -> str:
        try:                
            # Get the folder name from the first file's path
            folder_name = input_files[0].filename.split('/')[0]
            folder_path = os.path.join(self.base_path, folder_name)
            
            # Create the directory
            os.makedirs(folder_path, exist_ok=True)
            
            # Save all files preserving their structure
            for file in input_files:
                # Create full file path
                file_path = os.path.join(self.base_path, file.filename)
                
                # Create necessary subdirectories
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save the file
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            
            return folder_name
        
        except Exception as e:
            return {"error": str(e)}
        
        
        
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
            if code_chunks:
                success_code = self._store_chunks(chunk_store, code_chunks)
            if doc_chunks:
                success_doc = self._store_chunks(chunk_store, doc_chunks)
    
            if not success_code and not success_doc:
                raise Exception("Failed to store chunks in vector database, Mostly Repo is empty")

            return {
                "success": True
            }

        except Exception as e:
            raise Exception(f"Repository processing failed: {str(e)}")

class GetChatHistoryLocation:
    def __init__(self):
        # Get project root directory (2 levels up from current file)
        self.current_file = Path(__file__).resolve()
        self.project_root = self.current_file.parent.parent.parent
        self.base_path = os.path.join(self.project_root, "chat_history")
        os.makedirs(self.base_path, exist_ok=True)


def get_llm(provider_type: Optional[str] = None) -> ChatLLM:
    """
    Create ChatLLM instance for the specified provider.
    
    Args:
        provider_type: Type of LLM provider to use ("openai", "azure", or "claude")
        
    Returns:
        ChatLLM: Configured ChatLLM instance
        
    Raises:
        ValueError: If no valid provider credentials are found
        Exception: If provider creation fails
    """
    try:
        CLAUDE_API_KEY = None
        # Default to Azure if no provider specified
        provider_type = provider_type or "azure"
        
        # Create provider based on type
        if provider_type == "openai" and OPENAI_API_KEY:
            provider = OpenAIProvider(
                api_key=OPENAI_API_KEY,
                model="gpt-40"
            )
        elif provider_type == "azure" and AZURE_OPENAI_KEY:
            provider = AzureOpenAIProvider(
                api_key=AZURE_OPENAI_KEY,
                endpoint=AZURE_OPENAI_ENDPOINT,
                deployment_name=AZURE_OPENAI_MODEL
            )
        
        elif provider_type == "claude" and CLAUDE_API_KEY:
            provider = ClaudeProvider(
                api_key=CLAUDE_API_KEY,
                model="claude-3-opus-20240229"
            )
        else:
            raise ValueError(f"Invalid provider type or missing credentials: {provider_type}")
        
        # Create and return new ChatLLM instance
        return ChatLLM(
            provider=provider,
            qdrant_url=QDRANT_HOST,
            qdrant_api_key=QDRANT_API_KEY
        )
        
    except Exception as e:
        logger.error(f"Failed to create LLM instance: {str(e)}")
        raise
    
def get_project_path(file_name: str):
    
    try:
        with open(file_name, "r") as f:
            data = json.load(f)
        project_name = data['repo_name']
        project_folder_path = git_clone_service.base_path
        project_path = os.path.join(project_folder_path, project_name)
             
        return project_path, project_name
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project File Not found")
    
        
    

async def update_project_name(file_id: str, project_name: str):
    chat_history_path = get_chat_history_class.base_path
    file_path = os.path.join(chat_history_path, f"{file_id}.json")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data['repo_name'] = project_name
        data['last_updated'] = timestamp

        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        return True
            
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found")
    
async def update_chat_data(file_id: str, user_msg: str, system_msg: str):
    chat_history_path = get_chat_history_class.base_path
    file_path = os.path.join(chat_history_path, f"{file_id}.json")
  
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        if not data['repo_name']:
            return {"success": False, "message": "Project not available"}
            
        data['chat'].append({
            "user": user_msg,
            "bot": system_msg
        })
        
        data['last_updated'] = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
            
        return {"success": True}    
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found")


# Initialize service
get_chat_history_class = GetChatHistoryLocation()
repo_service = RepositoryStorageService()
git_clone_service = GitCloneService()
evaluator = Evaluator(
    llm_metrics=[
        LLMMetricType.ANSWER_RELEVANCY,
        LLMMetricType.FAITHFULNESS,
        LLMMetricType.CONTEXT_RELEVANCY
    ],
    non_llm_metrics=[
        NonLLMMetricType.CONTEXT_QUERY_MATCH,
        NonLLMMetricType.INFORMATION_DENSITY,
        NonLLMMetricType.ANSWER_COVERAGE,
        NonLLMMetricType.RESPONSE_CONSISTENCY,
        NonLLMMetricType.SOURCE_DIVERSITY,
    ]
)