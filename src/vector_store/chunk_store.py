from typing import Dict, Any, List
from qdrant_client import QdrantClient
from config.config import QDRANT_URL, QDRANT_API_KEY, POC_COLLECTION_NAME
import logging
from qdrant_client.http import models

logger = logging.getLogger(__name__)

class ChunkStoreHandler:
    """Handles storage and retrieval of code chunks in the vector database."""
    
    def __init__(self, collection_name: str = POC_COLLECTION_NAME):
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY
        )
        self.collection_name = collection_name
        
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
                # Store in Qdrant
                self.client.add(
                    collection_name=self.collection_name,
                    documents=docs_contents,
                    metadata=docs_metadatas
                )
                
                logger.info(f"Successfully stored {len(docs_contents)} chunks in vector database")
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