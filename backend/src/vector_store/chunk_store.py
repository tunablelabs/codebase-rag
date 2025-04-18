from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient
from config.config import QDRANT_HOST, QDRANT_API_KEY, OPENAI_API_KEY
import logging
from config.logging_config import info, warning, debug, error
from qdrant_client.http import models
from urllib.parse import urlparse
import re
from openai import OpenAI
import time
from tqdm import tqdm 
import uuid
import tiktoken


logger = logging.getLogger(__name__)

class ChunkStoreHandler:
    """Handles storage of chunks in the vector database."""
    
    def __init__(self, repo_path, user_id: Optional[str] = None, session_id: Optional[str] = None):
        info(f"Initializing ChunkStoreHandler for repo: {repo_path}, user: {user_id}, session: {session_id}")
        self.client = QdrantClient(
            url=QDRANT_HOST,
            api_key=QDRANT_API_KEY
        )
        self.user_id = user_id.replace('@', '_').replace('.', '_') 
        self.session_id = session_id
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.repo_path = repo_path
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.MAX_TOKENS = 8192
        self.MAX_RETRIES = 3  # Added retry limit
        self.BATCH_SIZE = 500
        self.collection_name = self._create_collection_name()
        self.processed_chunks = set()  # Track processed chunks
        self._ensure_collection_exists()
        info(f"ChunkStoreHandler initialized with collection: {self.collection_name}")
        
    def _create_collection_name(self):
        """
        Generate a unique collection name for QDrant from a git repository URL.
        The collection name will be lowercase, use underscores instead of special characters,
        and include the repository owner and name.
        """
        components = [x for x in self.repo_path.split('\\') if x]
        name_components = components[-1:]
        base_name = '-'.join(name_components)
        clean_name = re.sub(r'[^a-z0-9-]+', '_', base_name.lower()).strip('_')
        # Build the collection name userid-sessionid-projectname
        clean_name = "-".join([self.user_id, self.session_id, clean_name])
        return clean_name
        
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            info(f"Collection {self.collection_name} exists")
        except Exception as e:
            info(f"Creating collection {self.collection_name}")
            try:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=1536, 
                        distance=models.Distance.COSINE,
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=20000  # Optimize for larger datasets
                    )
                )
                info(f"Successfully created collection {self.collection_name}")
            except Exception as create_err:
                error(f"Failed to create collection {self.collection_name}: {create_err}")
                raise

    def _count_tokens(self, text: str) -> int:
        """Return the number of tokens in a given text."""
        return len(self.tokenizer.encode(text, disallowed_special=()))

    def _split_text(self, text: str) -> List[str]:
        """Splits long texts into smaller chunks within token limits."""
        tokens = self.tokenizer.encode(text, disallowed_special=())
        chunks = []
        
        for i in range(0, len(tokens), self.MAX_TOKENS):
            chunk = self.tokenizer.decode(tokens[i : i + self.MAX_TOKENS])
            if chunk.strip():  # Only add non-empty chunks
                chunks.append(chunk)
        
        return chunks
    
    def _prepare_batches(self, texts: List[str], batch_size: int) -> List[List[str]]:
        """Prepares batches ensuring each batch does not exceed max token limit."""
        info(f"Preparing batches for {len(texts)} texts")
        batches = []
        current_batch = []
        current_tokens = 0
        skipped_count = 0

        for text in texts:
            # Skip if already processed
            text_hash = hash(text)
            if text_hash in self.processed_chunks:
                skipped_count += 1
                continue
                
            token_count = self._count_tokens(text)

            if token_count > self.MAX_TOKENS:
                chunks = self._split_text(text)
                # Process split chunks immediately
                for chunk in chunks:
                    chunk_hash = hash(chunk)
                    if chunk_hash not in self.processed_chunks:
                        if current_tokens + self._count_tokens(chunk) > self.MAX_TOKENS:
                            if current_batch:
                                batches.append(current_batch)
                            current_batch = []
                            current_tokens = 0
                        current_batch.append(chunk)
                        current_tokens += self._count_tokens(chunk)
                        self.processed_chunks.add(chunk_hash)
                continue

            if current_tokens + token_count > self.MAX_TOKENS or len(current_batch) >= batch_size:
                if current_batch:
                    batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(text)
            current_tokens += token_count
            self.processed_chunks.add(text_hash)

        if current_batch:
            batches.append(current_batch)

        info(f"Created {len(batches)} batches, skipped {skipped_count} already processed texts")
        return batches
    
    def _get_embeddings(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Get embeddings for a list of texts using OpenAI's API with rate limiting and batching.
        """
        info(f"Getting embeddings for {len(texts)} texts")
        all_embeddings = []
        batches = self._prepare_batches(texts, batch_size)

        for batch_idx, batch in enumerate(tqdm(batches, desc="Generating embeddings")):
            for attempt in range(self.MAX_RETRIES):
                try:
                    if attempt > 0:
                        time.sleep(attempt * 2)  # Exponential backoff
                    response = self.openai_client.embeddings.create(
                        model="text-embedding-ada-002",
                        input=batch
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    if attempt == self.MAX_RETRIES - 1:
                        error(f"Failed to generate embeddings after {self.MAX_RETRIES} attempts: {str(e)}")
                        raise
                    warning(f"Embedding attempt {attempt + 1} failed: {str(e)}")

        info(f"Successfully generated {len(all_embeddings)} embeddings")
        return all_embeddings

    def store_chunks(self, file_chunks) -> bool:
        """
        Store code chunks and summary in the vector database in batches.
        """
        try:
            info(f"Storing chunks for {len(file_chunks)} files in collection {self.collection_name}")
            if not isinstance(file_chunks, dict):
                error("file_chunks must be a dictionary")
                return False

            docs_contents = []
            docs_metadatas = []
            
            # Process each file's chunks
            for file_path, file_data in file_chunks.items():
                if file_path == "summary":
                    continue
                
                if not isinstance(file_data, dict) or 'chunks' not in file_data:
                    error(f"Invalid file data structure for {file_path}")
                    continue
                
                for chunk in file_data['chunks']:
                    # Validate chunk has required attributes
                    if not hasattr(chunk, 'content'):
                        warning(f"Chunk missing content in {file_path}")
                        continue

                    docs_contents.append(chunk.content)
                    metadata = {
                        'file_path': getattr(chunk, 'file_path', file_path),
                        'language': getattr(chunk, 'language', 'unknown'),
                        'type': getattr(chunk, 'type', 'unknown'),
                        'start_line': getattr(chunk, 'start_line', 0),
                        'end_line': getattr(chunk, 'end_line', 0),
                        'metadata': getattr(chunk, 'metadata', {}),
                        'dependencies': getattr(chunk, 'dependencies', []),
                        'imports': getattr(chunk, 'imports', []),
                        'chunk_hash': hash(chunk.content)  # For duplicate detection
                    }
                    docs_metadatas.append(metadata)
                    
            if docs_contents and docs_metadatas:
                info(f"Generating embeddings for {len(docs_contents)} chunks")
                embeddings = self._get_embeddings(docs_contents)
                
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
                
                # Store in Qdrant in batches with retry logic
                info(f"Storing {len(points)} points in Qdrant")
                total_batches = (len(points) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
                
                for i in range(0, len(points), self.BATCH_SIZE):
                    batch = points[i:i + self.BATCH_SIZE]
                    batch_num = i // self.BATCH_SIZE + 1
                    
                    for attempt in range(self.MAX_RETRIES):
                        try:
                            if attempt > 0:
                                warning(f"Retry {attempt+1}/{self.MAX_RETRIES} for vector storage")
                                time.sleep(attempt * 2)  # Exponential backoff
                            self.client.upsert(
                                collection_name=self.collection_name,
                                points=batch
                            )
                            break
                        except Exception as e:
                            if attempt == self.MAX_RETRIES - 1:
                                error(f"Failed to store batch {batch_num}: {str(e)}")
                                return False
                            warning(f"Storage attempt {attempt + 1} failed: {str(e)}")
                
                info("Successfully stored all chunks in vector database")
            else:
                warning("No valid chunks found to store")
            
            # Store summary with retry logic
            if "summary" in file_chunks and file_chunks["summary"]:
                summary_data = file_chunks["summary"]
                info("Storing repository summary in Qdrant")
                
                summary_point = models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=[0] * 1536,  # Default zero vector
                    payload={
                        'metadata': {
                            'type': 'summary',
                            **summary_data
                        }
                    }
                )
                
                for attempt in range(self.MAX_RETRIES):
                    try:
                        if attempt > 0:
                            warning(f"Retry {attempt+1}/{self.MAX_RETRIES} for summary storage")
                            time.sleep(attempt * 2)  # Exponential backoff
                        self.client.upsert(
                            collection_name=self.collection_name,
                            points=[summary_point]
                        )
                        info("Successfully stored repository summary")
                        break
                    except Exception as e:
                        if attempt == self.MAX_RETRIES - 1:
                            error(f"Failed to store repository summary: {str(e)}")
                            return False
                        warning(f"Summary storage attempt {attempt + 1} failed: {str(e)}")
            
            info(f"Completed storing all data for collection {self.collection_name}")
            return True
                
        except Exception as e:
            error(f"Error storing chunks: {str(e)}")
            return False

    def get_collection_info(self):
        """Get information about the current collection"""
        info(f"Getting collection info for {self.collection_name}")
        try:
            collection_info = self.client.get_collection(self.collection_name)
            info(f"Retrieved collection info for {self.collection_name}")
            return collection_info
        except Exception as e:
            error(f"Error getting collection info: {str(e)}")
            return None
        
    def delete_collection(self, collection_name):
        """Delete the current collection from Qdrant DB"""
        info(f"Deleting collection {collection_name}")
        try:
            result = self.client.delete_collection(collection_name)
            info(f"Successfully deleted collection {collection_name}")
            return result
        except Exception as e:
            error(f"Error deleting collection {collection_name}: {str(e)}")
            return False