from typing import Iterator, Optional, Any, Tuple, List
from openai import OpenAI
from qdrant_client import QdrantClient
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import json
import requests
from datetime import datetime

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

class ChatLLM:
    """Main class for handling chat interactions with context from Qdrant."""
    
    def __init__(
        self, 
        api_key: str, 
        model: str, 
        qdrant_url: str, 
        qdrant_api_key: str, 
        base_url: str = "https://api.openai.com/v1/chat/completions"
    ):
        """
        Initialize the ChatLLM with necessary configurations.
        
        Args:
            api_key (str): OpenAI API key
            model (str): OpenAI model name (e.g., "gpt-3.5-turbo")
            qdrant_url (str): Qdrant server URL
            qdrant_api_key (str): Qdrant API key
            base_url (str): OpenAI API base URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        
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

    def get_context_from_qdrant(self, collection_name, query: str, limit: int = 5) -> list[str]:
        """
        Fetch relevant context chunks from Qdrant.
        
        Args:
            collection_name (str): Name of the Qdrant collection
            query (str): Search query
            limit (int): Maximum number of chunks to retrieve
            
        Returns:
            list[str]: Formatted context chunks
        """
        try:
            openai_client = OpenAI(api_key=self.api_key)
            # Get embedding for the query
            query_embedd = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_vector = query_embedd.data[0].embedding
            # Search in Qdrant using the embedded vector
            search_result = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
            contexts = [
            f"content: {r.payload.get('content', '')}, "
            f"type: {r.payload.get('metadata', {}).get('type', 'unknown')}, "
            f"file: {os.path.basename(r.payload.get('metadata', {}).get('file_path', ''))}, "
            f"dependencies: {r.payload.get('metadata', {}).get('dependencies', [])}, "
            f"imports: {r.payload.get('metadata', {}).get('imports', [])}"
            for r in search_result
            ]
            return contexts
            
        except Exception as e:
            raise Exception(f"Qdrant query failed: {str(e)}")

    def prepare_messages_with_context(self, collection_name, query: str, limit: int = 5) -> Tuple[list[BaseMessage], list[str]]:
        """
        Prepare messages with context for the LLM.
        
        Args:
            query (str): User query
            limit (int): Maximum number of context chunks
            
        Returns:
            Tuple[list[BaseMessage], list[str]]: Prepared messages and raw contexts
        """
        contexts = self.get_context_from_qdrant(collection_name, query, limit)
        
        system_prompt = """You're assisting a user who has a question based on the documentation.
        Address their query using relevant information from the documentation.
        If the query is general (e.g., "hi"), respond normally without using the context.
        For specific queries, use the context to provide accurate information.
        Reference relevant sources to support your answer.
        If you cannot find the answer in the context, respond with "I don't know"."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Context:\n" + "\n\n---\n\n".join(contexts)),
            HumanMessage(content=f"Question: {query}")
        ]
        return messages, contexts

    def invoke(
        self, 
        collection_name,
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
        messages, contexts = self.prepare_messages_with_context(collection_name, query, limit)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": self.prepare_message(messages),
            "temperature": temperature,
            **kwargs,
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            return contexts, LLMInterface(
                content=data["choices"][0]["message"]["content"],
                candidates=[choice["message"]["content"] for choice in data["choices"]],
                completion_tokens=data["usage"]["completion_tokens"],
                total_tokens=data["usage"]["total_tokens"],
                prompt_tokens=data["usage"]["prompt_tokens"],
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")

    def stream(
        self, 
        collection_name,
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
        messages, contexts = self.prepare_messages_with_context(collection_name, query, limit)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": self.prepare_message(messages),
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        try:
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
                                    if chunk_data.get("choices"):
                                        content = chunk_data["choices"][0].get("delta", {}).get("content")
                                        if content:
                                            yield contexts, LLMInterface(content=content)
                                except json.JSONDecodeError:
                                    continue
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API streaming request failed: {str(e)}")