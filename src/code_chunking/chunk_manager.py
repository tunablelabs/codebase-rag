from typing import Dict, Optional, List
from pathlib import Path
import logging
from .python_chunker import PythonChunker
from .base_chunker import BaseChunker
from .context import ChunkingContext
from .chunk_formatter import ChunkFormatter

class ChunkManager:
    """Manages different language-specific chunkers and chunk formatting."""
    
    def __init__(self, parser, relationship_analyzer):
        self.parser = parser
        self.relationship_analyzer = relationship_analyzer
        self.chunkers: Dict[str, BaseChunker] = {}
        self.formatter = ChunkFormatter()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize chunkers
        self._initialize_chunkers()
    
    def _initialize_chunkers(self) -> None:
        """Initialize supported language-specific chunkers."""
        try:
            self.chunkers = {
                '.py': PythonChunker(self.parser, self.relationship_analyzer),
            }
            self.logger.info(f"Initialized chunkers for extensions: {list(self.chunkers.keys())}")
        except Exception as e:
            self.logger.error(f"Failed to initialize chunkers: {e}")
            raise RuntimeError(f"Chunker initialization failed: {e}")
    
    def get_chunker(self, file_path: str) -> Optional[BaseChunker]:
        """Get appropriate chunker based on file extension."""
        try:
            ext = Path(file_path).suffix
            chunker = self.chunkers.get(ext)
            if not chunker:
                self.logger.warning(f"No chunker found for extension {ext}, using Python chunker")
                chunker = self.chunkers['.py']  # Default to Python chunker
            return chunker
        except Exception as e:
            self.logger.error(f"Error getting chunker for {file_path}: {e}")
            return None
    
    def create_chunks(self, code: str, file_path: str, context: Optional[ChunkingContext] = None) -> List[Dict]:
        """
        Create and format chunks using appropriate language chunker.
        
        Args:
            code: Source code to chunk
            file_path: Path to the source file
            context: Optional ChunkingContext, created if not provided
            
        Returns:
            List of formatted chunk dictionaries ready for vector DB
        """
        if not code or not file_path:
            raise ValueError("Code and file path must be provided")
            
        # Create context if not provided
        if context is None:
            context = ChunkingContext(file_path)
            
        try:
            # Get appropriate chunker
            chunker = self.get_chunker(file_path)
            if not chunker:
                raise RuntimeError(f"No suitable chunker found for {file_path}")
            
            # Create raw chunks
            raw_chunks = chunker.create_chunks(code, file_path, context)
            
            # Format chunks with metadata
            formatted_chunks = self._format_chunks(raw_chunks, file_path, chunker)
            
            # Enhance chunks for vector DB
            vector_db_chunks = [
                self.formatter.format_for_vector_db(chunk)
                for chunk in formatted_chunks
            ]
            
            return vector_db_chunks
            
        except Exception as e:
            self.logger.error(f"Chunking failed for {file_path}: {e}")
            raise RuntimeError(f"Failed to create chunks: {e}")
    
    def _format_chunks(self, raw_chunks: List[str], file_path: str, chunker: BaseChunker) -> List[Dict]:
        """Format raw chunks with metadata."""
        formatted_chunks = []
        
        for chunk in raw_chunks:
            try:
                # Generate chunk ID
                chunk_id = self._generate_chunk_id(chunk, file_path)
                
                # Get metadata if available
                metadata = chunker.get_chunk_metadata(chunk_id) or {}
                
                # Create formatted chunk
                formatted_chunk = {
                    'chunk_id': chunk_id,
                    'content': chunk,
                    'metadata': {
                        'file_path': file_path,
                        'language': Path(file_path).suffix[1:],
                        'size': len(chunk.encode('utf-8')),
                        'lines': chunk.count('\n') + 1,
                        **metadata  # Include any additional metadata from chunker
                    }
                }
                
                formatted_chunks.append(formatted_chunk)
                
            except Exception as e:
                self.logger.warning(f"Failed to format chunk: {e}")
                continue
                
        return formatted_chunks
    
    def _generate_chunk_id(self, code: str, file_path: str) -> str:
        """Generate a unique ID for a code chunk."""
        import hashlib
        # Create hash from content and file path
        content = f"{file_path}:{code}".encode('utf-8')
        return f"chunk_{hashlib.md5(content).hexdigest()[:8]}"
    
    def merge_chunks(self, chunks: List[Dict], file_path: str, context: Optional[ChunkingContext] = None) -> str:
        """Merge formatted chunks back into single code block."""
        if not chunks:
            return ""
            
        try:
            chunker = self.get_chunker(file_path)
            if not chunker:
                raise RuntimeError(f"No suitable chunker found for {file_path}")
                
            # Extract raw chunks while preserving order
            raw_chunks = [chunk['content'] for chunk in chunks]
            
            # Create context if not provided
            if context is None:
                context = ChunkingContext(file_path)
                
            # Merge using appropriate chunker
            return chunker.merge_chunks(raw_chunks, context)
            
        except Exception as e:
            self.logger.error(f"Failed to merge chunks: {e}")
            raise RuntimeError(f"Chunk merging failed: {e}")
    
    def configure_chunker(self, extension: str, min_size: int, max_size: int) -> None:
        """Configure chunk size limits for a specific language chunker."""
        chunker = self.chunkers.get(extension)
        if not chunker:
            raise ValueError(f"No chunker found for extension {extension}")
            
        chunker.set_chunk_size_limits(min_size, max_size)
        self.logger.info(f"Configured {extension} chunker with size limits: {min_size}-{max_size}")