from typing import Dict
import logging
from config.logging_config import info, warning, debug, error

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
        info("Initializing ChunkManager")
        self.LANGUAGE_MAPPING = {
        '.py': ('python', PythonChunker),
        '.js': ('javascript', JavaScriptChunker),
        '.java': ('java', JavaChunker),
        '.ts': ('typescript', TypeScriptChunker),
        '.tsx': ('typescript', TypeScriptChunker),
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parsers = parsers  # Store the parsers
        debug(f"Received {len(parsers)} language parsers")
        self.chunkers = self._initialize_chunkers(parsers)
        info(f"ChunkManager initialized with {len(self.chunkers)} language chunkers")
    
    def _initialize_chunkers(self, parsers: Dict[str, any]) -> Dict[str, any]:
        """Initialize language-specific chunkers"""
        info("Initializing language-specific chunkers")
        chunkers = {}
        self.parsers = parsers
        try:
            for ext, (lang, chunker_class) in self.LANGUAGE_MAPPING.items():
                parser = self.parsers.get(ext)
                if parser:
                    chunkers[ext] = chunker_class(parser)
                    info(f"Initialized chunker for {lang} ({ext})")
                else:
                    warning(f"No parser found for {lang} ({ext}), chunking will be unavailable")
        except Exception as e:
            error(f"Error initializing chunkers: {e}")
        return chunkers