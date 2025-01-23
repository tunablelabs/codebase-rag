from datetime import datetime
import json
import shutil
from typing import List, Dict
from fastapi import HTTPException
from git import Repo
from pydantic import BaseModel
from git_repo_parser.base_parser import CodeParser
from vector_store.chunk_store import ChunkStoreHandler
from vector_store.retrive_generate import ChatLLM, OpenAIProvider, AzureOpenAIProvider
from chunking.document_chunks import DocumentChunker
from evaluation import Evaluator, LLMMetricType, NonLLMMetricType
from config.config import OPENAI_API_KEY, QDRANT_HOST, QDRANT_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_MODEL
import os
from pathlib import Path
from dataclasses import dataclass


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
        openai_provider = OpenAIProvider(api_key=OPENAI_API_KEY,model="gpt-4o")
        # For Azure OpenAI
        azure_provider = AzureOpenAIProvider(api_key=AZURE_OPENAI_KEY,endpoint=AZURE_OPENAI_ENDPOINT,deployment_name=AZURE_OPENAI_MODEL)
        # Initialize ChatLLM with required provider
        _llm_instance = ChatLLM(
            provider = azure_provider,
            qdrant_url=QDRANT_HOST,
            qdrant_api_key=QDRANT_API_KEY
        )
    return _llm_instance

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
            "system": system_msg
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