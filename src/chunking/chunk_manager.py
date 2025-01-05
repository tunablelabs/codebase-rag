from typing import Dict, List, Optional
from pathlib import Path
import logging

from .strategies import ChunkInfo
from .language_specific_chunk.python_chunker import PythonChunker
from .language_specific_chunk.javascript_chunker import JavaScriptChunker
from .language_specific_chunk.java_chunker import JavaChunker

class ChunkManager:
    """Manages code chunking across different languages"""
      
    def __init__(self, parsers: Dict[str, any]):
        """
        Initialize chunk manager with language parsers.
        
        Args:
            parsers: Dict mapping file extensions to tree-sitter parsers
        """
        self.LANGUAGE_MAPPING = {
        '.py': ('python', PythonChunker),
        '.js': ('javascript', JavaScriptChunker),
        '.java': ('java', JavaChunker)
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parsers = parsers  # Store the parsers
        self.chunkers = self._initialize_chunkers(parsers)
    
    def _initialize_chunkers(self, parsers: Dict[str, any]) -> Dict[str, any]:
        """Initialize language-specific chunkers"""
        chunkers = {}
        self.parsers = parsers
        try:
            for ext, (lang, chunker_class) in self.LANGUAGE_MAPPING.items():
                parser = self.parsers.get(ext)
                if parser:
                    chunkers[ext] = chunker_class(parser)
                    self.logger.info(f"Initialized chunker for {lang}")
                else:
                    self.logger.warning(f"No parser found for {lang}, chunking will be unavailable")
        except Exception as e:
            self.logger.error(f"Error initializing chunkers: {e}")
        return chunkers
    
    def create_chunks(self, code: str, file_path: str) -> List[ChunkInfo]:
        """
        Create chunks from source code.
        
        Args:
            code: Source code to chunk
            file_path: Path to source file
            
        Returns:
            List of ChunkInfo objects
        """
        try:
            # Get file extension
            ext = Path(file_path).suffix
            
            # Get appropriate chunker
            parser = self.parsers.get(ext)
            chunker = self.chunkers.get(ext)
            if not parser or not chunker:
                raise ValueError(f"No parser or chunker available for {ext} files")
            
            # Parse the file to extract entities
            entities = parser.parse_file(file_path)
            
             # Chunk the entities
            chunks = chunker.create_chunks_from_entities(entities, file_path)
                        
            # Validate chunks
            valid_chunks = self._validate_chunks(chunks)
            
            # Add file-level metadata
            for chunk in valid_chunks:
                chunk.metadata['file_path'] = file_path
                chunk.metadata['language'] = self.LANGUAGE_MAPPING[ext][0]
            
            return valid_chunks
            
        except Exception as e:
            self.logger.error(f"Error chunking file {file_path}: {e}")
            return []
    
    def _validate_chunks(self, chunks: List[ChunkInfo]) -> List[ChunkInfo]:
        """Validate and filter chunks"""
        valid_chunks = []
        for chunk in chunks:
            try:
                if not chunk.content.strip():
                    continue
                    
                if not chunk.chunk_id:
                    self.logger.warning(f"Chunk missing ID: {chunk.content[:100]}...")
                    continue
                    
                valid_chunks.append(chunk)
                
            except Exception as e:
                self.logger.warning(f"Invalid chunk: {e}")
                continue
                
        return valid_chunks
    
    def process_file(self, file_path: str) -> List[ChunkInfo]:
        try:
            # Get file extension
            ext = Path(file_path).suffix
            
            # Get appropriate chunker
            chunker = self.chunkers.get(ext)
            
            if  not chunker:
                raise ValueError(f"No chunker available for {ext} files")
            
            # Parse the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Create chunks 
            return chunker.create_chunks(content, file_path)
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return []
    
    def process_directory(self, directory_path: str) -> Dict[str, List[ChunkInfo]]:
        """
        Process all supported files in a directory.
        
        Args:
            directory_path: Path to directory
            
        Returns:
            Dict mapping file paths to their chunks
        """
        results = {}
        try:
            directory = Path(directory_path)
            
            # Process each supported file type
            for ext in self.chunkers:
                for file_path in directory.rglob(f"*{ext}"):
                    chunks = self.process_file(str(file_path))
                    if chunks:
                        results[str(file_path)] = chunks
                        
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing directory {directory_path}: {e}")
            return results
    
    def get_summary(self, chunks: List[ChunkInfo]) -> Dict:
        """
        Get summary information about chunks.
        
        Args:
            chunks: List of chunks to summarize
            
        Returns:
            Dictionary with summary information
        """
        try:
            return {
                'total_chunks': len(chunks),
                'by_type': self._count_by_type(chunks),
                'by_language': self._count_by_language(chunks),
                'total_lines': sum(c.end_line - c.start_line + 1 for c in chunks),
                'dependencies': self._summarize_dependencies(chunks)
            }
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return {}
    
    def _count_by_type(self, chunks: List[ChunkInfo]) -> Dict[str, int]:
        """Count chunks by type"""
        counts = {}
        for chunk in chunks:
            counts[chunk.type] = counts.get(chunk.type, 0) + 1
        return counts
    
    def _count_by_language(self, chunks: List[ChunkInfo]) -> Dict[str, int]:
        """Count chunks by language"""
        counts = {}
        for chunk in chunks:
            counts[chunk.language] = counts.get(chunk.language, 0) + 1
        return counts
    
    def _summarize_dependencies(self, chunks: List[ChunkInfo]) -> Dict:
        """Summarize chunk dependencies"""
        return {
            'total_dependencies': sum(len(c.dependencies) for c in chunks),
            'isolated_chunks': len([c for c in chunks if not c.dependencies]),
            'most_dependent': max((len(c.dependencies), c.chunk_id) for c in chunks)[1] if chunks else None
        }

    def get_chunk_by_id(self, chunk_id: str, chunks: List[ChunkInfo]) -> Optional[ChunkInfo]:
        """Get a specific chunk by ID"""
        for chunk in chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None