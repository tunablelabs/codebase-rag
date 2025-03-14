from datetime import datetime
import json
import shutil
from typing import Any, List, Dict
import uuid
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
from config.logging_config import info, warning, debug, error


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
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        self.base_path = os.path.join(project_root, "project_repos")
        os.makedirs(self.base_path, exist_ok=True)
        info(f"GitCloneService initialized with base path: {self.base_path}")
    
    def clone(self, user_id, repo_url: str) -> str:
        try:
            info(f"Cloning repository for user {user_id}: {repo_url}")
            user_name = user_id.replace('@', '_').replace('.', '_')    
            user_folder_path = os.path.join(self.base_path, user_name)
            os.makedirs(user_folder_path, exist_ok=True)
            # Generate a 5-digit unique identifier from a UUID
            session_number = str(uuid.uuid4().int)[:5]
           
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_name = f"{session_number}_{repo_name}"
            repo_path = os.path.join(user_folder_path, repo_name)
            
            Repo.clone_from(repo_url, repo_path)
            info(f"Repository cloned successfully: {repo_name}")
            return repo_name
            
        except Exception as e:
            error(f"Failed to clone repository: {str(e)}")
            raise Exception(f"Failed to clone repository: {str(e)}")
        
    def folder_upload(self, user_id, input_files) -> str:
        try:    
            info(f"Uploading folder for user {user_id} with {len(input_files)} files")
            user_name = user_id.replace('@', '_').replace('.', '_')            
            user_folder_path = os.path.join(self.base_path, user_name)
            os.makedirs(user_folder_path, exist_ok=True)
            # Generate a 5-digit unique identifier from a UUID
            session_number = str(uuid.uuid4().int)[:5]
            
            folder_name = input_files[0].filename.split('/')[0]
            folder_name = f"{session_number}_{folder_name}"
            folder_path = os.path.join(user_folder_path, folder_name)
            
            os.makedirs(folder_path, exist_ok=True)
            
            for file in input_files:
                file_path = os.path.join(folder_path, file.filename)
                
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            
            info(f"Folder upload completed successfully: {folder_name}")
            return folder_name
        
        except Exception as e:
            error(f"Failed to upload folder: {str(e)}")
            return {"error": str(e)}
        
    def folder_delete(self, user_id, session_id):
        try:    
            info(f"Deleting folder for user {user_id}, session {session_id}")
            user_name = user_id.replace('@', '_').replace('.', '_')  
            session_folder_path = os.path.join(self.base_path, user_name, session_id)
            shutil.rmtree(Path(session_folder_path))
            info(f"Folder deleted successfully")
        
        except:
            warning(f"Error during folder deletion, attempting with permission changes")
            for root, dirs, files in os.walk(session_folder_path):
                for dir_name in dirs:
                    os.chmod(os.path.join(root, dir_name), 0o777)
                for file_name in files:
                    os.chmod(os.path.join(root, file_name), 0o777)
                    
            os.chmod(session_folder_path, 0o777)
            shutil.rmtree(Path(session_folder_path))
            info("Folder deleted successfully after permission changes")
            
        
class RepositoryStorageService:
    def __init__(self):
        self.code_parser = CodeParser()
        self.doc_chunker = DocumentChunker()
        info("RepositoryStorageService initialized")

    def _create_chunk_store(self, repo_path: str, user_id: str, session_id: str) -> ChunkStoreHandler:
        """Initialize chunk store for the repository"""
        try:
            info(f"Creating chunk store for {repo_path}")
            return ChunkStoreHandler(repo_path, user_id, session_id)
        except Exception as e:
            error(f"Failed to initialize chunk store: {str(e)}")
            raise Exception(f"Failed to initialize chunk store: {str(e)}")

    def _process_code_chunks(self, repo_path: str) -> List[Dict]:
        """Process and parse code files"""
        try:
            info(f"Processing code files in {repo_path}")
            code_chunks = self.code_parser.parse_directory(repo_path)
            info(f"Processed {len(code_chunks)} code chunks")
            return code_chunks
        except Exception as e:
            error(f"Failed to process code files: {str(e)}")
            raise Exception(f"Failed to process code files: {str(e)}")

    def _process_doc_chunks(self, repo_path: str) -> List[Dict]:
        """Process and parse document files"""
        try:
            info(f"Processing document files in {repo_path}")
            doc_chunks = self.doc_chunker.parse_directory(repo_path)
            info(f"Processed {len(doc_chunks)} document chunks")
            return doc_chunks
        except Exception as e:
            error(f"Failed to process document files: {str(e)}")
            raise Exception(f"Failed to process document files: {str(e)}")

    def _store_chunks(self, chunk_store, 
                     chunks: List[Dict]) -> bool:
        """Store chunks in vector database"""
        try:
            info(f"Storing {len(chunks)} chunks in vector database")
            result = chunk_store.store_chunks(chunks)
            info(f"Chunks stored successfully")
            return result
        except Exception as e:
            error(f"Failed to store chunks: {str(e)}")
            raise Exception(f"Failed to store chunks: {str(e)}")

    def process_repository(self, repo_path: str, user_id: str, session_id: str) -> Dict:
        """Main method to process and store repository data"""
        try:
            info(f"Processing repository {repo_path} for user {user_id}, session {session_id}")
            chunk_store = self._create_chunk_store(repo_path, user_id, session_id)

            code_chunks = self._process_code_chunks(repo_path)
            doc_chunks = self._process_doc_chunks(repo_path)

            success_code = False
            success_doc = False
            
            if code_chunks:
                info(f"Storing {len(code_chunks)} code chunks")
                success_code = self._store_chunks(chunk_store, code_chunks)
            else:
                warning("No code chunks found to store")
                
            if doc_chunks:
                info(f"Storing {len(doc_chunks)} document chunks")
                success_doc = self._store_chunks(chunk_store, doc_chunks)
            else:
                warning("No document chunks found to store")
    
            if not success_code and not success_doc:
                warning("Failed to store any chunks, repository may be empty")
                raise Exception("Failed to store chunks in vector database, Mostly Repo is empty")

            info("Repository processing completed successfully")
            return {
                "success": True
            }

        except Exception as e:
            error(f"Repository processing failed: {str(e)}")
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
        info(f"Creating LLM instance with provider: {provider_type or 'default'}")
        CLAUDE_API_KEY = None
        provider_type = provider_type or "azure"
        
        if provider_type == "openai" and OPENAI_API_KEY:
            info("Initializing OpenAI provider")
            provider = OpenAIProvider(
                api_key=OPENAI_API_KEY,
                model="gpt-4o"
            )
        elif provider_type == "azure" and AZURE_OPENAI_KEY:
            info("Initializing Azure OpenAI provider")
            provider = AzureOpenAIProvider(
                api_key=AZURE_OPENAI_KEY,
                endpoint=AZURE_OPENAI_ENDPOINT,
                deployment_name=AZURE_OPENAI_MODEL
            )
        
        elif provider_type == "claude" and CLAUDE_API_KEY:
            info("Initializing Claude provider")
            provider = ClaudeProvider(
                api_key=CLAUDE_API_KEY,
                model="claude-3-opus-20240229"
            )
        else:
            error(f"Invalid provider type or missing credentials: {provider_type}")
            raise ValueError(f"Invalid provider type or missing credentials: {provider_type}")
        
        info(f"LLM instance created successfully with {provider_type} provider")
        return ChatLLM(
            provider=provider,
            qdrant_url=QDRANT_HOST,
            qdrant_api_key=QDRANT_API_KEY
        )
        
    except Exception as e:
        error(f"Failed to create LLM instance: {str(e)}")
        raise
    
def get_project_path(user_id: str, session_id: str):
    
    try:
        info(f"Getting project path for user {user_id}, session {session_id}")
        user_id = user_id.replace('@', '_').replace('.', '_')   
        project_folder_path = git_clone_service.base_path
        project_path = os.path.join(project_folder_path, user_id, session_id)
             
        return project_path
    
    except FileNotFoundError:
        error(f"Project path not found for user {user_id}, session {session_id}")
        raise HTTPException(status_code=404, detail="Project File Not found")
    
def follow_up_question(question: str):
    info(f"Generating follow-up questions for: {question}")
    provider = OpenAIProvider(
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini"
        )
    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates exactly 3 relevant follow-up questions based on an input question. Return ONLY the three questions as a numbered list (1, 2, 3). Do not include any other text."},
        {"role": "user", "content": f"Generate 3 follow-up questions for this question: {question}"}
    ]
    
    info("Calling OpenAI API for follow-up questions")
    response = provider.invoke(
        messages=messages,
        temperature=0.4,
        max_tokens=150
    )
    result = response["choices"][0]["message"]["content"]
    result = result.strip()
    follow_up_questions = [line.strip() for line in result.split('\n') if line.strip()]
    info(f"Generated {len(follow_up_questions)} follow-up questions")
        
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
info("Evaluator initialized with metrics")

dynamo_db_service = DynamoDBManager()
info("DynamoDB manager initialized")