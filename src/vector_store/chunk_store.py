from typing import Dict, Any, List
from qdrant_client import QdrantClient
from config.config import QDRANT_HOST, QDRANT_API_KEY, OPENAI_API_KEY
import logging
from qdrant_client.http import models
from urllib.parse import urlparse
import re
from openai import OpenAI
import time
from tqdm import tqdm 
import uuid


logger = logging.getLogger(__name__)

class ChunkStoreHandler:
    """Handles storage of chunks in the vector database."""
    
    def __init__(self, repo_path):
        self.client = QdrantClient(
            url=QDRANT_HOST,
            api_key=QDRANT_API_KEY
        )
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.repo_path = repo_path
        self.collection_name = self._create_collection_name()
        self._ensure_collection_exists()
        
    def _create_collection_name(self):
        """
        Generate a unique collection name for QDrant from a git repository URL.
        The collection name will be lowercase, use underscores instead of special characters,
        and include the repository owner and name.
        
        Args:
            git_url (str): The Git repository URL
            
        Returns:
            str: A formatted collection name suitable for QDrant
        """
        # Handle both HTTPS and SSH URLs
        if self.repo_path.startswith('git@'):
            # Parse SSH URL (git@github.com:username/repo.git)
            parts = self.repo_path.split(':')
            if len(parts) != 2:
                raise ValueError("Invalid SSH Git URL format")
            path = parts[1]
        else:
            # Parse HTTPS URL
            parsed_url = urlparse(self.repo_path)
            path = parsed_url.path
        path = path.replace('.git', '')
    
        # Split into components and remove empty strings
        components = [x for x in path.split('/') if x]
        # Take the last two components (usually username/org and repo name)
        name_components = components[-2:]
        base_name = '-'.join(name_components)
        clean_name = re.sub(r'[^a-z0-9-]+', '_', base_name.lower()).strip('_')
        
        return clean_name
        
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} exists")
        except Exception as e:
            logger.info(f"Creating collection {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE)  # OpenAI embeddings are 1536 dimensions
            )


    def _get_embeddings(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Get embeddings for a list of texts using OpenAI's API with rate limiting and batching.
        
        Args:
            texts: List of texts to get embeddings for
            batch_size: Number of texts to process in each batch
            
        Returns:
            List of embeddings
        """
        all_embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch = texts[i:i + batch_size]
            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch: {str(e)}")
                raise
                
        return all_embeddings


    def store_chunks(self, file_chunks) -> bool:
        """
        Store code chunks in the vector database.
        
        Args:
            file_chunks: Dictionary mapping file paths to lists of ChunkInfo objects
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            docs_contents = []
            docs_metadatas = []
            
            # Process each file's chunks
            for file_path, file_data in file_chunks.items():
                if file_path == "summary":
                    continue
                # Process chunks from the file data
                for chunk in file_data['chunks']:
                    # Extract content and metadata
                    docs_contents.append(chunk.content)
                    
                    metadata = {
                        'file_path': getattr(chunk, 'chunk_id', file_path),
                        'language': getattr(chunk, 'language', 'unknown'),
                        'type': getattr(chunk, 'type', 'unknown'),
                        'start_line': getattr(chunk, 'start_line', 0),
                        'end_line': getattr(chunk, 'end_line', 0),
                        'metadata': getattr(chunk, 'metadata', {}),
                        'dependencies': getattr(chunk, 'dependencies', []),
                        'imports': getattr(chunk, 'imports', [])
                    }
                    docs_metadatas.append(metadata)
                    
            if docs_contents and docs_metadatas:
                # Generate embeddings for all chunks
                logger.info("Generating embeddings for chunks...")
                embeddings = self._get_embeddings(docs_contents)
                
                # Create points for Qdrant
                points = []
                for content, metadata, embedding in zip(docs_contents, docs_metadatas, embeddings):
                    point_id = str(uuid.uuid4())
                    
                    point = models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            'content': content,
                            'metadata': metadata
                        }
                    )
                    points.append(point)
                
                # Store in Qdrant
                logger.info(f"Storing {len(points)} points in Qdrant...")
                operation_info = self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                
                logger.info(f"Successfully stored {len(points)} chunks in vector database")
                return True
            
            else:
                logger.warning("No chunks found to store")
                return False
                
        except Exception as e:
            logger.error(f"Error storing chunks: {str(e)}")
            return False

    def get_collection_info(self):
        """Get information about the current collection"""
        try:
            return self.client.get_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return None