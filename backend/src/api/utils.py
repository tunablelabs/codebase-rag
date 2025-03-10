from datetime import datetime
import json
import shutil
from typing import Any, List, Dict
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
from vector_store.dynamo_db_crud import DynamoDBManager


class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    CLAUDE = "claude"
      
class QueryRequest(BaseModel):
    """Request model for querying the code"""
    user_id: str
    session_id: str
    use_llm: str
    ast_flag: str
    query: str
    sys_prompt: Optional[str] = ""
    limit: int = 5
    
class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    follow_up_questions: List[str]
    
class UserID(BaseModel):
    user_id: str
    
class SessionID(BaseModel):
    session_id: str
    
class Rename(UserID, SessionID):
    updated_name: str
    
class UserSessionID(UserID, SessionID):
    pass


class GitCloneService:
    def __init__(self):
        # Get project root directory (2 levels up from current file)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        self.base_path = os.path.join(project_root, "project_repos")
        os.makedirs(self.base_path, exist_ok=True)
    
    def clone(self, user_id, repo_url: str) -> str:
        try:
            user_name = user_id.replace('@', '_').replace('.', '_')    
            # Check if user exist in project folder
            user_folder_path = os.path.join(self.base_path, user_name)
            # Create the user folder if dont exist
            os.makedirs(user_folder_path, exist_ok=True)
            # prefix the project with number of the project for the user
            # For evry session we create single project uploaded during the create session
            session_number = len(os.listdir(user_folder_path))
           
            # Extract repo name from URL
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_name = f"{session_number+1}_{repo_name}"
            repo_path = os.path.join(user_folder_path, repo_name)
            
            # Clone repository
            Repo.clone_from(repo_url, repo_path)
            return repo_name
            
        except Exception as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
        
    def folder_upload(self, user_id, input_files) -> str:
        try:    
            user_name = user_id.replace('@', '_').replace('.', '_')            
            # Check if user exist in project folder
            user_folder_path = os.path.join(self.base_path, user_name)
            # Create the user folder if dont exist
            os.makedirs(user_folder_path, exist_ok=True)
            # prefix the project with number of the project for the user
            # For evry session we create single project uploaded during the create session
            session_number = len(os.listdir(user_folder_path))
            
            # Get the folder name from the first file's path
            folder_name = input_files[0].filename.split('/')[0]
            folder_name = f"{session_number+1}_{folder_name}"
            folder_path = os.path.join(user_folder_path, folder_name)
            
            # Create the directory
            os.makedirs(folder_path, exist_ok=True)
            
            # Save all files preserving their structure
            for file in input_files:
                # Create full file path
                file_path = os.path.join(folder_path, file.filename)
                
                # Create necessary subdirectories
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Save the file
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            
            return folder_name
        
        except Exception as e:
            return {"error": str(e)}
        
    def folder_delete(self, user_id, session_id):
        try:    
            user_name = user_id.replace('@', '_').replace('.', '_')  
            session_folder_path = os.path.join(self.base_path, user_name, session_id)
            shutil.rmtree(Path(session_folder_path))
        
        except:
            # Change permissions on all files and folders
            for root, dirs, files in os.walk(session_folder_path):
                for dir_name in dirs:
                    os.chmod(os.path.join(root, dir_name), 0o777)
                for file_name in files:
                    os.chmod(os.path.join(root, file_name), 0o777)
                    
            # Change permission of the root folder
            os.chmod(session_folder_path, 0o777)
            # Remove the folder
            shutil.rmtree(Path(session_folder_path))
            
        
class RepositoryStorageService:
    def __init__(self):
        self.code_parser = CodeParser()
        self.doc_chunker = DocumentChunker()

    def _create_chunk_store(self, repo_path: str, user_id: str, session_id: str) -> ChunkStoreHandler:
        """Initialize chunk store for the repository"""
        try:
            return ChunkStoreHandler(repo_path, user_id, session_id)
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

    def _store_chunks(self, chunk_store, 
                     chunks: List[Dict]) -> bool:
        """Store chunks in vector database"""
        try:
            return chunk_store.store_chunks(chunks)
        except Exception as e:
            raise Exception(f"Failed to store chunks: {str(e)}")

    def process_repository(self, repo_path: str, user_id: str, session_id: str) -> Dict:
        """Main method to process and store repository data"""
        try:
            # Initialize chunk store
            chunk_store = self._create_chunk_store(repo_path, user_id, session_id)

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
                model="gpt-4o"
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
        logging.info(f"Failed to create LLM instance: {str(e)}")
        raise
    
def get_project_path(user_id: str, session_id: str):
    
    try:
        user_id = user_id.replace('@', '_').replace('.', '_')   
        project_folder_path = git_clone_service.base_path
        project_path = os.path.join(project_folder_path, user_id, session_id)
             
        return project_path
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project File Not found")
    
def follow_up_question(question: str):
    provider = OpenAIProvider(
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini"
        )
    # Define the messages for follow-up question generation
    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates exactly 3 relevant follow-up questions based on an input question. Return ONLY the three questions as a numbered list (1, 2, 3). Do not include any other text."},
        {"role": "user", "content": f"Generate 3 follow-up questions for this question: {question}"}
    ]
    
    # Call the OpenAI API using the provider
    response = provider.invoke(
        messages=messages,
        temperature=0.4,
        max_tokens=150
    )
    result = response["choices"][0]["message"]["content"]
    result = result.strip()
    follow_up_questions = [line.strip() for line in result.split('\n') if line.strip()]
        
    return follow_up_questions


# Initialize service
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

dynamo_db_service = DynamoDBManager()