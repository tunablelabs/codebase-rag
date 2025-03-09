# from typing import Dict
# import logging
#
# from .language_specific_chunk.python_chunker import PythonChunker
# from .language_specific_chunk.javascript_chunker import JavaScriptChunker
# from .language_specific_chunk.typescript_chunker import TypeScriptChunker
# from .language_specific_chunk.java_chunker import JavaChunker
#
# class ChunkManager:
#     """Manages code chunking across different languages"""
#
#     def __init__(self, parsers: Dict[str, any]):
#         """
#         Initialize chunk manager with language parsers.
#
#         Args:
#             parsers: Dict mapping file extensions to tree-sitter parsers
#         """
#         self.LANGUAGE_MAPPING = {
#         '.py': ('python', PythonChunker),
#         '.js': ('javascript', JavaScriptChunker),
#         '.java': ('java', JavaChunker),
#         '.ts': ('typescript', TypeScriptChunker),
#         '.tsx': ('typescript', TypeScriptChunker),
#         }
#         self.logger = logging.getLogger(self.__class__.__name__)
#         self.parsers = parsers  # Store the parsers
#         self.chunkers = self._initialize_chunkers(parsers)
#
#     def _initialize_chunkers(self, parsers: Dict[str, any]) -> Dict[str, any]:
#         """Initialize language-specific chunkers"""
#         chunkers = {}
#         self.parsers = parsers
#         try:
#             for ext, (lang, chunker_class) in self.LANGUAGE_MAPPING.items():
#                 parser = self.parsers.get(ext)
#                 if parser:
#                     chunkers[ext] = chunker_class(parser)
#                     self.logger.info(f"Initialized chunker for {lang}")
#                 else:
#                     self.logger.warning(f"No parser found for {lang}, chunking will be unavailable")
#         except Exception as e:
#             self.logger.error(f"Error initializing chunkers: {e}")
#         return chunkers


from typing import Dict, Optional, Union, List
import logging
import os

# Import from your existing codebase
from .language_specific_chunk.python_chunker import PythonChunker
from .language_specific_chunk.javascript_chunker import JavaScriptChunker
from .language_specific_chunk.typescript_chunker import TypeScriptChunker
from .language_specific_chunk.java_chunker import JavaChunker

# Import from the provided CodeParser and Chunker
from .code_parser import CodeParser
from .code_chunker import CodeChunker

# Import a fallback chunker for unsupported languages
from langchain.text_splitter import RecursiveCharacterTextSplitter


class FallbackChunker:
    """A fallback chunker that uses RecursiveCharacterTextSplitter from langchain"""

    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def chunk(self, code: str, token_limit: int) -> dict:
        """
        Chunk code using recursive character splitting

        Args:
            code: The code to chunk
            token_limit: Approximate token limit per chunk

        Returns:
            Dictionary of chunks with numbers as keys
        """
        # Convert token_limit to approximate character count (rough estimate)
        char_limit = token_limit * 4

        # Adjust the splitter's chunk size
        self.splitter.chunk_size = char_limit

        # Split the text
        chunks = self.splitter.split_text(code)

        # Convert to the expected format (dict with numbers as keys)
        return {i + 1: chunk for i, chunk in enumerate(chunks)}

    def get_chunk(self, chunked_content, chunk_number):
        """Get a specific chunk by number"""
        return chunked_content.get(chunk_number, "")


class ChunkManager:
    """
    Enhanced chunk manager that supports multiple languages and provides fallbacks
    for unsupported languages
    """

    def __init__(self, parsers: Optional[Dict[str, any]] = None):
        """
        Initialize chunk manager with language parsers.

        Args:
            parsers: Dict mapping file extensions to tree-sitter parsers
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Define supported languages and their corresponding chunkers
        self.LANGUAGE_MAPPING = {
            '.py': ('python', PythonChunker),
            '.js': ('javascript', JavaScriptChunker),
            '.jsx': ('javascript', JavaScriptChunker),
            '.java': ('java', JavaChunker),
            '.ts': ('typescript', TypeScriptChunker),
            '.tsx': ('typescript', TypeScriptChunker),
            '.css': ('css', None),  # Will use CodeChunker
            '.php': ('php', None),  # Will use CodeChunker
            '.rb': ('ruby', None),  # Will use CodeChunker
        }

        # Initialize code parser for various languages
        self.code_parser = CodeParser(
            file_extensions=list(ext.lstrip('.') for ext in self.LANGUAGE_MAPPING.keys())
        )

        # Store the external parsers
        self.parsers = parsers or {}

        # Initialize specialized chunkers
        self.chunkers = self._initialize_chunkers()

        # Create a fallback chunker for unsupported languages
        self.fallback_chunker = FallbackChunker()

    def _initialize_chunkers(self) -> Dict[str, any]:
        """Initialize language-specific chunkers"""
        chunkers = {}

        try:
            # Initialize specialized chunkers first
            for ext, (lang, chunker_class) in self.LANGUAGE_MAPPING.items():
                if chunker_class:
                    parser = self.parsers.get(ext)
                    if parser:
                        chunkers[ext] = chunker_class(parser)
                        self.logger.info(f"Initialized specialized chunker for {lang}")
                    else:
                        self.logger.warning(f"No parser found for {lang}, will use generic chunker")

                # For all languages, also initialize a CodeChunker as a backup
                try:
                    code_chunker = CodeChunker(ext.lstrip('.'))
                    chunkers[f"{ext}_generic"] = code_chunker
                    self.logger.info(f"Initialized generic CodeChunker for {lang}")
                except Exception as e:
                    self.logger.warning(f"Could not initialize generic chunker for {lang}: {e}")

            # Add support for other file extensions that might not be in the mapping
            common_extensions = ['.html', '.xml', '.json', '.yml', '.yaml', '.md', '.txt', '.sh', '.bash', '.go',
                                 '.swift', '.kt', '.rs']
            for ext in common_extensions:
                if ext not in self.LANGUAGE_MAPPING:
                    try:
                        code_chunker = CodeChunker(ext.lstrip('.'))
                        chunkers[ext] = code_chunker
                        self.logger.info(f"Initialized generic CodeChunker for {ext}")
                    except Exception as e:
                        self.logger.warning(f"Could not initialize generic chunker for {ext}: {e}")

        except Exception as e:
            self.logger.error(f"Error initializing chunkers: {e}")

        return chunkers

    def get_chunker(self, file_path: str) -> Union[object, None]:
        """
        Get appropriate chunker for the given file path

        Args:
            file_path: Path to the file to be chunked

        Returns:
            A chunker object or None if no suitable chunker found
        """
        _, ext = os.path.splitext(file_path.lower())

        # Try to get a specialized chunker first
        chunker = self.chunkers.get(ext)
        if chunker:
            return chunker

        # Try to get a generic chunker
        generic_chunker = self.chunkers.get(f"{ext}_generic")
        if generic_chunker:
            return generic_chunker

        # If no chunker available, return the fallback chunker
        self.logger.warning(f"No chunker found for extension {ext}, using fallback chunker")
        return self.fallback_chunker

    def chunk_code(self, code: str, file_path: str, token_limit: int = 1000) -> Dict[int, str]:
        """
        Chunk code based on file type

        Args:
            code: Source code to chunk
            file_path: Path to the source file (used to determine file type)
            token_limit: Maximum tokens per chunk

        Returns:
            Dictionary mapping chunk numbers to code chunks
        """
        chunker = self.get_chunker(file_path)

        if chunker:
            try:
                return chunker.chunk(code, token_limit)
            except Exception as e:
                self.logger.error(f"Error chunking code with {type(chunker).__name__}: {e}")
                self.logger.info("Falling back to FallbackChunker")
                return self.fallback_chunker.chunk(code, token_limit)
        else:
            return self.fallback_chunker.chunk(code, token_limit)

    def get_chunk(self, chunked_code: Dict[int, str], chunk_number: int) -> str:
        """
        Get a specific chunk from chunked code

        Args:
            chunked_code: Dictionary of chunked code
            chunk_number: Chunk number to retrieve

        Returns:
            The requested chunk or empty string if not found
        """
        return chunked_code.get(chunk_number, "")