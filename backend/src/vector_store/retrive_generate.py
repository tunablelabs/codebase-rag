from typing import Iterator, Optional, Any, Tuple, List
from openai import OpenAI
from qdrant_client import QdrantClient
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import json
from datetime import datetime
import logging

from .providers import BaseLLMProvider, OpenAIProvider, AzureOpenAIProvider, ClaudeProvider
from .get_local_db import fetch_user_data, check_and_create_table, add_user, update_conversation, user_exists
from config.config import OPENAI_API_KEY

# checks & creates user localdb if not already
check_and_create_table()

logger = logging.getLogger(__name__)

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

    def get_context_from_qdrant(self, ast_flag: str, collection_name, query: str, limit: int = 5) -> Tuple[list[str], list[str]]:
        """
        Fetch relevant context chunks from Qdrant.
        
        Args:
            ast_flag (str): To include AST chunks in retrived chunks
            collection_name (str): Name of the Qdrant collection
            query (str): Search query
            limit (int): Maximum number of chunks to retrieve
            
        Returns:
            Tuple[list[str], list[str]]: Formatted context chunks and source attributes
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
            
            # Apply filter based on ast_flag
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
            num_retrieved_chunks = len(search_result)
            logger.info(f"Number of retrieved chunks: {num_retrieved_chunks}")
            
            source_attributes = []
            contexts = []

            for r in search_result:
                # Add the file basename to source_attributes list
                source_attributes.append(os.path.basename(r.payload.get('metadata', {}).get('file_path', '')))
                
                # Create context string
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

    def prepare_messages_with_context(self, ast_flag: str, collection_name: str, user_id: str, query: str, limit: int = 5) -> Tuple[list[BaseMessage], list[str], list[str]]:
        """
        Prepare messages with context for the LLM.
        
        Args:
            ast_flag (str): Flag for including AST chunks
            collection_name (str): Name of the Qdrant collection
            user_id (str): User identifier
            query (str): User query
            limit (int): Maximum number of context chunks
            
        Returns:
            Tuple[list[BaseMessage], list[str], list[str]]: Messages, contexts, and source attributes
        """
        
        if user_exists(user_id):
            user_context = fetch_user_data(user_id)['context_window']
        else:
            add_user(user_id)
            user_context = None
        
        contexts, source_attributes = self.get_context_from_qdrant(ast_flag, collection_name, query, limit)
        
        system_prompt =  """
        You are an advanced AI Code Assistant. Your primary objectives are:

        1. **Code Generation & Explanation**  
        - Provide syntactically correct and well-commented code snippets.  
        - Explain code structure, logic, and best practices.  

        2. **Debugging & Optimization**  
        - Identify errors, inefficiencies, and suggest improvements.  
        - Offer structured debugging techniques and performance optimizations.  

        3. **Integration & Best Practices**  
        - Guide users on integrating libraries, frameworks, and APIs effectively.  
        - Reference official documentation when relevant for clarity and accuracy.  

        4. **Reliable & Clear Communication**  
        - Use structured responses with clear formatting and examples.  
        - If uncertain, respond honestly (e.g., "I'm not entirely sure" or "I don't know") rather than making assumptions.  

        ---

        ### **Response Formatting Guidelines**

        #### **1. Overview**  
        - Summarize the user query or problem statement.  
        - Emphasize key details or goals from the request.  

        #### **2. Solution Explanation**  
        - Describe the approach or algorithm step by step.  
        - Highlight relevant libraries, dependencies, or concepts.  

        #### **3. Example Code (if applicable)**  
        - Provide clean, well-structured code with inline comments.  
        - Ensure correctness, readability, and practical usability.  

        #### **4. Conclusion**  
        - Summarize the core solution or final recommendation.  
        - Mention possible optimizations, edge cases, or next steps.  

        ---

        ### **Additional Behavioral Guidelines**  

        - **Clarify Ambiguities:** If the user's request is unclear, ask for clarification before proceeding.  
        - **Adapt to User Needs:** If the user modifies the request, adjust your response accordingly.  
        - **Professional & Ethical Standards:** Do not generate or suggest content that violates ethical guidelines.  
        - **Conciseness & Readability:** Keep explanations clear, focused, and free from unnecessary complexity. 
        - **If the user's query is general (e.g., "hi," "good morning"),greet them normally and avoid using the context from the documentation. 

        Always follow these principles to ensure effective and user-friendly responses. **Now, proceed with the user's request.**

        Context:\n"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Context:\n" + "\n\n".join(contexts)+"\n\n"+ "\n\n"+user_context if user_context else ""),
            HumanMessage(content=f"Question: {query}\nAnswer:")
        ]
        
        return messages, contexts, source_attributes

    def invoke(
        self, 
        ast_flag: str,
        collection_name: str,
        user_id: str,
        query: str, 
        limit: int = 5, 
        temperature: float = 0.1, 
        **kwargs
    ) -> Tuple[list[str], LLMInterface]:
        """
        Invoke LLM with context from Qdrant.
        
        Args:
            ast_flag (str): Flag for including AST chunks
            collection_name (str): Name of the Qdrant collection
            user_id (str): User identifier
            query (str): User query
            limit (int): Maximum number of context chunks
            temperature (float): LLM temperature parameter
            **kwargs: Additional parameters for LLM API
            
        Returns:
            Tuple[list[str], LLMInterface]: Contexts and LLM response
        """
        messages, contexts, source_attributes = self.prepare_messages_with_context(
            ast_flag, collection_name, user_id, query, limit
        )
        
        try:
            response_data = self.provider.invoke(
                messages=self.prepare_message(messages),
                temperature=temperature,
                **kwargs
            )
            
            llm_response = response_data["choices"][0]["message"]["content"]
            update_conversation(user_id, question=query, answer=llm_response, turn=3)
            
            return contexts, LLMInterface(
                content=f"{llm_response}\nSource files: {', '.join(source_attributes)}",
                candidates=[choice["message"]["content"] for choice in response_data["choices"]],
                completion_tokens=response_data["usage"]["completion_tokens"],
                total_tokens=response_data["usage"]["total_tokens"],
                prompt_tokens=response_data["usage"]["prompt_tokens"],
            )
        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise Exception(f"LLM request failed: {str(e)}")

    def stream(
        self, 
        ast_flag: str,
        collection_name: str,
        user_id: str,
        query: str, 
        limit: int = 5, 
        temperature: float = 0, 
        **kwargs
    ) -> Iterator[Tuple[list[str], LLMInterface]]:
        """
        Stream LLM responses with context from Qdrant.
        
        Args:
            ast_flag (str): Flag for including AST chunks
            collection_name (str): Name of the Qdrant collection
            user_id (str): User identifier
            query (str): User query
            limit (int): Maximum number of context chunks
            temperature (float): LLM temperature parameter
            **kwargs: Additional parameters for LLM API
            
        Yields:
            Tuple[list[str], LLMInterface]: Contexts and partial LLM response
        """
        messages, contexts, _ = self.prepare_messages_with_context(
            ast_flag, collection_name, user_id, query, limit
        )

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
            logger.error(f"LLM streaming request failed: {str(e)}")
            raise Exception(f"LLM streaming request failed: {str(e)}")

    def get_collection_info(self) -> Optional[dict]:
        """Get information about the current collection"""
        try:
            return self.qdrant_client.get_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return None