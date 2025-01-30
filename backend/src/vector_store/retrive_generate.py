from typing import Iterator, Optional, Any, Tuple, List
from openai import OpenAI, AzureOpenAI
from qdrant_client import QdrantClient
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import json
import requests
from datetime import datetime
from abc import ABC, abstractmethod
from config.config import OPENAI_API_KEY

from .get_local_db import fetch_user_data, check_and_create_table, add_user, update_conversation, user_exists

# checks & creates user localdb if not already
check_and_create_table()

# Message Classes for OpenAI Chat Format
class BaseMessage:
    """Base class for all message types."""
    def __init__(self, content: str):
        self.content = content

    def to_openai_format(self) -> dict:
        """Convert message to OpenAI API format."""
        raise NotImplementedError("This method should be implemented in subclasses.")

class HumanMessage(BaseMessage):
    """Represents a message from the human user."""
    def to_openai_format(self) -> dict:
        return {"role": "user", "content": self.content}

class AIMessage(BaseMessage):
    """Represents a message from the AI assistant."""
    def to_openai_format(self) -> dict:
        return {"role": "assistant", "content": self.content}

class SystemMessage(BaseMessage):
    """Represents a system message for setting context/behavior."""
    def to_openai_format(self) -> dict:
        return {"role": "system", "content": self.content}

class LLMInterface:
    """Interface for LLM responses with metadata."""
    def __init__(
        self,
        content: str,
        candidates: Optional[List[str]] = None,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        prompt_tokens: int = 0,
        total_cost: float = 0.0,
        timestamp: Optional[str] = None
    ):
        self.content = content
        self.candidates = candidates or []
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.prompt_tokens = prompt_tokens
        self.total_cost = total_cost
        self.timestamp = timestamp or datetime.now().isoformat()

# Abstract base class for LLM providers
class BaseLLMProvider(ABC):
    @abstractmethod
    def prepare_client(self):
        pass

    @abstractmethod
    def invoke(self, messages: list[dict], temperature: float, **kwargs) -> dict:
        pass

    @abstractmethod
    def stream(self, messages: list[dict], temperature: float, **kwargs) -> Iterator[Any]:
        pass

# OpenAI Provider Implementation
class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def prepare_client(self):
        pass  # Empty implementation since we're using REST API

    def invoke(self, messages: list[dict], temperature: float, **kwargs) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        response = requests.post(self.base_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def stream(self, messages: list[dict], temperature: float, **kwargs) -> Iterator[Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        with requests.post(self.base_url, headers=headers, json=payload, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk = line.decode("utf-8").strip()
                    if chunk.startswith("data: "):
                        chunk = chunk[6:]
                        if chunk != "[DONE]":
                            try:
                                chunk_data = json.loads(chunk)
                                yield chunk_data
                            except json.JSONDecodeError:
                                continue

# Azure OpenAI Provider Implementation
class AzureOpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, endpoint: str, deployment_name: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment_name = deployment_name

    def prepare_client(self):
        pass  # Empty implementation since we're using REST API

    def invoke(self, messages: list[dict], temperature: float, **kwargs) -> dict:
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        
        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2024-02-15-preview"
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    def stream(self, messages: list[dict], temperature: float, **kwargs) -> Iterator[Any]:
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        
        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2024-02-15-preview"
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        with requests.post(url, headers=headers, json=payload, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk = line.decode("utf-8").strip()
                    if chunk.startswith("data: "):
                        chunk = chunk[6:]
                        if chunk != "[DONE]":
                            try:
                                chunk_data = json.loads(chunk)
                                yield chunk_data
                            except json.JSONDecodeError:
                                continue



class ChatLLM:
    """Main class for handling chat interactions with context from Qdrant."""
    
    def __init__(
        self, 
        provider: BaseLLMProvider,
        qdrant_url: str, 
        qdrant_api_key: str,
    ):
        self.provider = provider
        self.provider.prepare_client()
              
        # Initialize Qdrant client
        try:
            self.qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Qdrant client: {str(e)}")

    def prepare_message(self, messages: str | BaseMessage | list[BaseMessage]) -> list[dict]:
        """
        Convert different message formats to OpenAI API format.
        
        Args:
            messages: Single message or list of messages
            
        Returns:
            list[dict]: Messages formatted for OpenAI API
        """
        input_: list[BaseMessage] = []

        if isinstance(messages, str):
            input_ = [HumanMessage(content=messages)]
        elif isinstance(messages, BaseMessage):
            input_ = [messages]
        else:
            input_ = messages

        return [m.to_openai_format() for m in input_]

    def get_context_from_qdrant(self, ast_flag: str, collection_name, query: str, limit: int = 5) -> list[str]:
        """
        Fetch relevant context chunks from Qdrant.
        
        Args:
            ast_flag (str): To include AST chunks in retrived chunks
            collection_name (str): Name of the Qdrant collection
            query (str): Search query
            limit (int): Maximum number of chunks to retrieve
            
        Returns:
            list[str]: Formatted context chunks
        """
        try:
            # Str to Bool Conversion
            ast_filter = ast_flag == "True"
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            # Get embedding for the query
            query_embedd = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_vector = query_embedd.data[0].embedding
            search_params = {
                    "collection_name": collection_name,
                    "query_vector": query_vector,
                    "limit": limit
            }
            # Apply a filter condition based on the value of `ast_flag`. 
            # - If `ast_flag` is False, retrieve only text-based data. 
            # - If `ast_flag` is True, retrieve all data chunks without restriction.
            if ast_filter:
                search_params["query_filter"] = {
                    "must": []
                } 
                
            else:
                search_params["query_filter"] = {
                    "must": [
                        {
                            "key": "metadata.language",
                            "match": {"value": "text"}
                        }
                    ]
                }        
            # Search in Qdrant using the embedded vector
            search_result = self.qdrant_client.search(**search_params)
            source_attributes = []
            contexts = []

            for r in search_result:
                # Add the file basename to source_attributes list
                source_attributes.append(os.path.basename(r.payload.get('metadata', {}).get('file_path', '')))
                
                # Your existing context creation
                contexts.append(
                    f"content: {r.payload.get('content', '')}, "
                    f"type: {r.payload.get('metadata', {}).get('type', 'unknown')}, "
                    f"file: {os.path.basename(r.payload.get('metadata', {}).get('file_path', ''))}, "
                    f"dependencies: {r.payload.get('metadata', {}).get('dependencies', [])}, "
                    f"imports: {r.payload.get('metadata', {}).get('imports', [])}"
                )
            return contexts, list(set(source_attributes))
            
        except Exception as e:
            raise Exception(f"Qdrant query failed: {str(e)}")

    def prepare_messages_with_context(self, ast_flag, collection_name, user_id: str, query: str, limit: int = 5) -> Tuple[list[BaseMessage], list[str]]:
        """
        Prepare messages with context for the LLM.
        
        Args:
            query (str): User query
            limit (int): Maximum number of context chunks
            
        Returns:
            Tuple[list[BaseMessage], list[str]]: Prepared messages and raw contexts
        """
        
        if user_exists(user_id):
            user_context = fetch_user_data(user_id)['context_window']
        else:
            add_user(user_id)
            user_context = None
        
        contexts, source_attributes = self.get_context_from_qdrant(ast_flag, collection_name, query, limit)
        
        system_prompt =  """You're assisting a user who has a question based on the documentation.
            Your goal is to provide a clear and concise response that addresses their query while referencing relevant information
            from the documentation.
            Remember to:
            - Understand the user's question thoroughly.
            - If the user's query is general (e.g., "hi," "good morning"),
              greet them normally and avoid using the context from the documentation.
            - If the user's query is specific and related to the documentation, locate and extract the pertinent information.
            - Craft a response that directly addresses the user's query and provides accurate information
              referring to the relevant source and page from the 'source' field of fetched context from the documentation to support your answer.
            - Use a friendly and professional tone in your response.
            - If you cannot find the answer in the provided context, do not pretend to know it.
              Instead, respond with "I don't know".
            
            Context:\n"""
            
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Context:\n" + "\n\n---\n\n".join(contexts)+"\n\n---\n\n".join(user_context)),
            HumanMessage(content=f"Question: {query}\nAnswer:")
        ]
        return messages, contexts, source_attributes

    def invoke(
        self, 
        ast_flag,
        collection_name,
        user_id: str,
        query: str, 
        limit: int = 5, 
        temperature: float = 0, 
        **kwargs
    ) -> Tuple[list[str], LLMInterface]:
        """
        Invoke LLM with context from Qdrant.
        
        Args:
            query (str): User query
            limit (int): Maximum number of context chunks
            temperature (float): OpenAI temperature parameter
            **kwargs: Additional parameters for OpenAI API
            
        Returns:
            Tuple[list[str], LLMInterface]: Contexts and LLM response
        """
        messages, contexts, source_attributes = self.prepare_messages_with_context(ast_flag, collection_name, user_id, query, limit)
        
        
        try:
            response_data = self.provider.invoke(
                messages=self.prepare_message(messages),
                temperature=temperature,
                **kwargs
            )
            llm_response = response_data["choices"][0]["message"]["content"]
            update_conversation(user_id, question=query , answer=llm_response, turn=3)
            return contexts, LLMInterface(
                # content=response_data["choices"][0]["message"]["content"],
                content=f"{response_data['choices'][0]['message']['content']}\nSource files: {', '.join(source_attributes)}",
                candidates=[choice["message"]["content"] for choice in response_data["choices"]],
                completion_tokens=response_data["usage"]["completion_tokens"],
                total_tokens=response_data["usage"]["total_tokens"],
                prompt_tokens=response_data["usage"]["prompt_tokens"],
            )
        except Exception as e:
            raise Exception(f"LLM request failed: {str(e)}")

    def stream(
        self, 
        ast_flag,
        collection_name,
        user_id: str,
        query: str, 
        limit: int = 5, 
        temperature: float = 0, 
        **kwargs
    ) -> Iterator[Tuple[list[str], LLMInterface]]:
        """
        Stream LLM responses with context from Qdrant.
        
        Args:
            query (str): User query
            limit (int): Maximum number of context chunks
            temperature (float): OpenAI temperature parameter
            **kwargs: Additional parameters for OpenAI API
            
        Yields:
            Tuple[list[str], LLMInterface]: Contexts and partial LLM response
        """
        messages, contexts = self.prepare_messages_with_context(ast_flag, collection_name, user_id, query, limit)

        try:
            for chunk_data in self.provider.stream(
                messages=self.prepare_message(messages),
                temperature=temperature,
                **kwargs
            ):
                if chunk_data.get("choices"):
                    content = chunk_data["choices"][0].get("delta", {}).get("content")
                    if content:
                        yield contexts, LLMInterface(content=content)
        except Exception as e:
            raise Exception(f"LLM streaming request failed: {str(e)}")