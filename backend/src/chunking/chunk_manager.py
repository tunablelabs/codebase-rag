from typing import Dict
import logging

from .language_specific_chunk.python_chunker import PythonChunker
from .language_specific_chunk.javascript_chunker import JavaScriptChunker
from .language_specific_chunk.typescript_chunker import TypeScriptChunker
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
        '.java': ('java', JavaChunker),
        '.ts': ('typescript', TypeScriptChunker),
        '.tsx': ('typescript', TypeScriptChunker),
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