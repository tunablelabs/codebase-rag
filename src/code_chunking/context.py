from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Any
from pathlib import Path
import logging
import uuid
from git_parser.schemas import ChunkMetadata, BaseEntity

@dataclass
class ChunkingContext:
    """
    Stores context information for chunking decisions and tracking relationships,
    with enhanced support for vector database preparation.
    """
    
    file_path: str
    chunks: Dict[str, str] = field(default_factory=dict)  # chunk_id -> code
    chunk_relationships: Dict[str, Set[str]] = field(default_factory=dict)  # chunk_id -> dependent_chunks
    metadata: Dict[str, ChunkMetadata] = field(default_factory=dict)  # chunk_id -> metadata
    entities: Dict[str, List[BaseEntity]] = field(default_factory=dict)  # chunk_id -> entities
    
    # New fields for vector DB support
    vector_metadata: Dict[str, Dict] = field(default_factory=dict)  # chunk_id -> vector db metadata
    semantic_contexts: Dict[str, str] = field(default_factory=dict)  # chunk_id -> semantic context
    embedding_metadata: Dict[str, Dict] = field(default_factory=dict)  # chunk_id -> embedding metadata
    
    def __post_init__(self):
        """Initialize additional attributes after instance creation."""
        self.path = Path(self.file_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Track import statements separately
        self.imports: Dict[str, Set[str]] = {}  # chunk_id -> set of imports
        
        # Track API components
        self.api_chunks: Set[str] = set()  # chunk_ids containing API components
        
        # Track async code
        self.async_chunks: Set[str] = set()  # chunk_ids containing async code
        
        # Track dependency graph
        self.dependencies: Dict[str, Set[str]] = {}  # chunk_id -> set of dependencies
        
        # Initialize session ID for tracking
        self.session_id = str(uuid.uuid4())
    
    def add_chunk(self, chunk_id: str, code: str, metadata: Optional[ChunkMetadata] = None) -> None:
        """
        Add a new code chunk with optional metadata.
        
        Args:
            chunk_id: Unique identifier for the chunk
            code: The chunk's code content
            metadata: Optional ChunkMetadata for the chunk
        """
        try:
            self.chunks[chunk_id] = code
            
            if metadata:
                self.metadata[chunk_id] = metadata
                
                # Track special characteristics
                if metadata.imports:
                    self.imports[chunk_id] = set(metadata.imports)
                if metadata.api_components:
                    self.api_chunks.add(chunk_id)
                if metadata.async_code:
                    self.async_chunks.add(chunk_id)
                if metadata.dependencies:
                    self.dependencies[chunk_id] = set(metadata.dependencies)
            
            self.logger.debug(f"Added chunk {chunk_id} with {len(code)} bytes")
        except Exception as e:
            self.logger.error(f"Failed to add chunk {chunk_id}: {e}")
            raise
    
    def add_vector_metadata(self, chunk_id: str, metadata: Dict[str, Any]) -> None:
        """
        Add vector database specific metadata for a chunk.
        
        Args:
            chunk_id: Chunk identifier
            metadata: Vector database metadata
        """
        if chunk_id not in self.chunks:
            raise ValueError(f"Chunk {chunk_id} not found in context")
            
        self.vector_metadata[chunk_id] = metadata
    
    def add_semantic_context(self, chunk_id: str, context: str) -> None:
        """
        Add semantic context for a chunk.
        
        Args:
            chunk_id: Chunk identifier
            context: Semantic context string
        """
        if chunk_id not in self.chunks:
            raise ValueError(f"Chunk {chunk_id} not found in context")
            
        self.semantic_contexts[chunk_id] = context
    
    def add_embedding_metadata(self, chunk_id: str, metadata: Dict[str, Any]) -> None:
        """
        Add embedding-specific metadata for a chunk.
        
        Args:
            chunk_id: Chunk identifier
            metadata: Embedding metadata
        """
        if chunk_id not in self.chunks:
            raise ValueError(f"Chunk {chunk_id} not found in context")
            
        self.embedding_metadata[chunk_id] = metadata
    
    def get_vector_db_info(self, chunk_id: str) -> Dict[str, Any]:
        """
        Get all vector database related information for a chunk.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Dictionary containing all vector DB related information
        """
        return {
            'metadata': self.vector_metadata.get(chunk_id, {}),
            'semantic_context': self.semantic_contexts.get(chunk_id, ''),
            'embedding_metadata': self.embedding_metadata.get(chunk_id, {}),
            'relationships': self.get_relationships(chunk_id),
            'code_type': self._determine_code_type(chunk_id)
        }
    
    def _determine_code_type(self, chunk_id: str) -> str:
        """Determine the type of code in the chunk."""
        if chunk_id in self.api_chunks:
            return 'api_endpoint'
        elif chunk_id in self.async_chunks:
            return 'async_code'
        else:
            code = self.chunks.get(chunk_id, '')
            if 'class ' in code:
                return 'class_definition'
            elif 'def ' in code:
                return 'function_definition'
            elif 'import ' in code or 'from ' in code:
                return 'imports'
            return 'code_block'
    
    def get_chunk_summary(self, chunk_id: str) -> Dict[str, Any]:
        """
        Get a complete summary of a chunk's information.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Dictionary containing all chunk information
        """
        if chunk_id not in self.chunks:
            raise ValueError(f"Chunk {chunk_id} not found")
            
        return {
            'content': self.chunks[chunk_id],
            'metadata': self.metadata.get(chunk_id),
            'relationships': self.get_relationships(chunk_id),
            'entities': self.entities.get(chunk_id, []),
            'imports': self.imports.get(chunk_id, set()),
            'dependencies': self.dependencies.get(chunk_id, set()),
            'vector_db_info': self.get_vector_db_info(chunk_id),
            'type': self._determine_code_type(chunk_id)
        }
    
    def clear(self) -> None:
        """Clear all tracked information."""
        self.chunks.clear()
        self.chunk_relationships.clear()
        self.metadata.clear()
        self.entities.clear()
        self.imports.clear()
        self.api_chunks.clear()
        self.async_chunks.clear()
        self.dependencies.clear()
        self.vector_metadata.clear()
        self.semantic_contexts.clear()
        self.embedding_metadata.clear()
        self.logger.info("Cleared all context data")