# from abc import ABC, abstractmethod
# from dataclasses import dataclass, field
# from typing import List, Dict, Optional, Set
# import logging
#
# @dataclass
# class ChunkInfo:
#     """Represents a code chunk with metadata"""
#     content: str
#     language: str  # 'python', 'javascript', etc.
#     chunk_id: str
#     type: str  # 'function', 'class', 'api', etc.
#     start_line: int
#     end_line: int
#     metadata: Dict = field(default_factory=dict)
#     dependencies: Set[str] = field(default_factory=set)
#     imports: Set[str] = field(default_factory=set)
#
# class BaseChunkingStrategy(ABC):
#     """Base class for all chunking strategies"""
#
#     def __init__(self):
#         self.logger = logging.getLogger(self.__class__.__name__)
#
#     @abstractmethod
#     def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
#         """Create chunks from code"""
#         pass
#
#     def _generate_chunk_id(self, content: str, file_path: str) -> str:
#         """Generate unique chunk ID"""
#         import hashlib
#         content = f"{file_path}:{content}".encode('utf-8')
#         return f"chunk_{hashlib.md5(content).hexdigest()[:8]}"
#
# class ApiChunkingStrategy(BaseChunkingStrategy):
#     """Strategy for API code chunks"""
#
#     def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
#         chunks = []
#         current_lines = []
#         in_api_block = False
#         start_line = 0
#
#         for i, line in enumerate(code.splitlines(), 1):
#             stripped = line.strip()
#
#             # Detect API patterns
#             if any(pattern in stripped for pattern in ['@app.', '@router.', 'app.get', 'app.post']):
#                 if current_lines:  # Save previous non-API chunk
#                     content = '\n'.join(current_lines)
#                     chunks.append(ChunkInfo(
#                         content=content,
#                         language='python',
#                         chunk_id=self._generate_chunk_id(content, file_path),
#                         type='code',
#                         start_line=start_line,
#                         end_line=i-1
#                     ))
#                     current_lines = []
#
#                 in_api_block = True
#                 start_line = i
#                 current_lines = [line]
#
#             elif in_api_block:
#                 current_lines.append(line)
#                 if stripped == '' and len(current_lines) > 2:  # End of API block
#                     content = '\n'.join(current_lines)
#                     chunks.append(ChunkInfo(
#                         content=content,
#                         language='python',
#                         chunk_id=self._generate_chunk_id(content, file_path),
#                         type='api',
#                         start_line=start_line,
#                         end_line=i,
#                         metadata={'api_type': 'endpoint'}
#                     ))
#                     current_lines = []
#                     in_api_block = False
#                     start_line = i + 1
#
#             else:
#                 current_lines.append(line)
#
#         # Handle remaining lines
#         if current_lines:
#             content = '\n'.join(current_lines)
#             chunks.append(ChunkInfo(
#                 content=content,
#                 language='python',
#                 chunk_id=self._generate_chunk_id(content, file_path),
#                 type='code',
#                 start_line=start_line,
#                 end_line=len(code.splitlines())
#             ))
#
#         return chunks
#
# class LogicalChunkingStrategy(BaseChunkingStrategy):
#     """Strategy for logical code blocks (functions, classes)"""
#
#     def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
#         chunks = []
#         current_lines = []
#         start_line = 1
#
#         for i, line in enumerate(code.splitlines(), 1):
#             stripped = line.strip()
#
#             # Detect new logical block
#             if stripped.startswith(('def ', 'class ', 'async def ')):
#                 if current_lines:  # Save previous chunk
#                     content = '\n'.join(current_lines)
#                     chunks.append(ChunkInfo(
#                         content=content,
#                         language='python',
#                         chunk_id=self._generate_chunk_id(content, file_path),
#                         type=self._determine_type(current_lines[0]),
#                         start_line=start_line,
#                         end_line=i-1
#                     ))
#
#                 current_lines = [line]
#                 start_line = i
#             else:
#                 current_lines.append(line)
#
#         # Handle remaining lines
#         if current_lines:
#             content = '\n'.join(current_lines)
#             chunks.append(ChunkInfo(
#                 content=content,
#                 language='python',
#                 chunk_id=self._generate_chunk_id(content, file_path),
#                 type=self._determine_type(current_lines[0]),
#                 start_line=start_line,
#                 end_line=len(code.splitlines())
#             ))
#
#         return chunks
#
#     def _determine_type(self, first_line: str) -> str:
#         stripped = first_line.strip()
#         if stripped.startswith('class '):
#             return 'class'
#         elif stripped.startswith(('def ', 'async def ')):
#             return 'function'
#         return 'code'
#
# class ImportChunkingStrategy(BaseChunkingStrategy):
#     """Strategy for import statements"""
#
#     def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
#         imports = []
#         current_imports = []
#         other_lines = []
#         start_line = 1
#         in_imports = False
#
#         for i, line in enumerate(code.splitlines(), 1):
#             stripped = line.strip()
#
#             if stripped.startswith(('import ', 'from ')):
#                 if not in_imports and current_imports:
#                     # Save previous import block
#                     content = '\n'.join(current_imports)
#                     imports.append(ChunkInfo(
#                         content=content,
#                         language='python',
#                         chunk_id=self._generate_chunk_id(content, file_path),
#                         type='import',
#                         start_line=start_line,
#                         end_line=i-1,
#                         imports=set(imp.strip() for imp in current_imports)
#                     ))
#
#                 in_imports = True
#                 if not current_imports:
#                     start_line = i
#                 current_imports.append(line)
#
#             elif in_imports and stripped == '':
#                 # Empty line after imports
#                 current_imports.append(line)
#
#             else:
#                 if in_imports:
#                     # End of import block
#                     content = '\n'.join(current_imports)
#                     imports.append(ChunkInfo(
#                         content=content,
#                         language='python',
#                         chunk_id=self._generate_chunk_id(content, file_path),
#                         type='import',
#                         start_line=start_line,
#                         end_line=i-1,
#                         imports=set(imp.strip() for imp in current_imports)
#                     ))
#                     current_imports = []
#                     in_imports = False
#
#                 other_lines.append(line)
#
#         # Handle remaining imports
#         if current_imports:
#             content = '\n'.join(current_imports)
#             imports.append(ChunkInfo(
#                 content=content,
#                 language='python',
#                 chunk_id=self._generate_chunk_id(content, file_path),
#                 type='import',
#                 start_line=start_line,
#                 end_line=len(code.splitlines()),
#                 imports=set(imp.strip() for imp in current_imports)
#             ))
#
#         return imports


from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any
import logging
import os
import hashlib
import re

# Import the CodeParser to help with code analysis
from .code_parser import CodeParser


@dataclass
class ChunkInfo:
    """Represents a code chunk with metadata"""
    content: str
    language: str  # 'python', 'javascript', etc.
    chunk_id: str
    type: str  # 'function', 'class', 'api', 'import', etc.
    start_line: int
    end_line: int
    metadata: Dict = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)

    @property
    def line_count(self) -> int:
        """Return the number of lines in the chunk"""
        return self.end_line - self.start_line + 1

    @property
    def is_empty(self) -> bool:
        """Check if the chunk is empty or contains only whitespace"""
        return not self.content.strip()


class BaseChunkingStrategy(ABC):
    """Base class for all chunking strategies"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def chunk(self, code: str, file_path: str, language: Optional[str] = None) -> List[ChunkInfo]:
        """Create chunks from code"""
        pass

    def _generate_chunk_id(self, content: str, file_path: str, chunk_type: str = '') -> str:
        """Generate unique chunk ID"""
        content = f"{file_path}:{chunk_type}:{content[:100]}".encode('utf-8')
        return f"chunk_{hashlib.md5(content).hexdigest()[:8]}"

    def _extract_file_extension(self, file_path: str) -> str:
        """Extract file extension from file path"""
        _, ext = os.path.splitext(file_path)
        return ext.lstrip('.')

    def _identify_language(self, file_path: str) -> str:
        """Identify programming language from file extension"""
        extension = self._extract_file_extension(file_path)

        # Map extensions to languages
        language_map = {
            'py': 'python',
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'java': 'java',
            'php': 'php',
            'rb': 'ruby',
            'css': 'css',
            'html': 'html',
            'xml': 'xml',
            'json': 'json',
            'yml': 'yaml',
            'yaml': 'yaml',
            'md': 'markdown',
            'txt': 'text',
            'sh': 'shell',
            'bash': 'shell',
            'go': 'go',
            'swift': 'swift',
            'kt': 'kotlin',
            'rs': 'rust'
        }

        return language_map.get(extension, 'unknown')


class ParserBasedChunkingStrategy(BaseChunkingStrategy):
    """
    A chunking strategy that uses CodeParser to identify structural elements
    in the code and create chunks accordingly
    """

    def __init__(self):
        super().__init__()
        self.code_parser = None

    def _ensure_parser(self, file_ext: str):
        """Ensure we have a code parser for the given file extension"""
        if self.code_parser is None:
            self.code_parser = CodeParser(file_ext)

    def chunk(self, code: str, file_path: str, language: Optional[str] = None) -> List[ChunkInfo]:
        """
        Create chunks based on code structure using CodeParser

        Args:
            code: Source code to chunk
            file_path: Path to the source file
            language: Optional language identifier

        Returns:
            List of ChunkInfo objects
        """
        extension = self._extract_file_extension(file_path)
        language = language or self._identify_language(file_path)

        try:
            # Try to use CodeParser for supported languages
            self._ensure_parser(extension)

            # Get points of interest (functions, classes, etc.)
            points_of_interest_lines = self.code_parser.get_lines_for_points_of_interest(code, extension)

            # Get comment lines
            comment_lines = self.code_parser.get_lines_for_comments(code, extension)

            # Sort and organize lines of interest
            all_lines = sorted(points_of_interest_lines)

            # Create chunks based on points of interest
            chunks = self._create_chunks_from_points(code, file_path, all_lines, language)

            # If no chunks were created or only one large chunk, fall back to simple chunking
            if len(chunks) <= 1 and len(code.splitlines()) > 50:
                self.logger.info("Falling back to simple chunking due to insufficient structure detection")
                return self._simple_chunk(code, file_path, language)

            return chunks

        except Exception as e:
            self.logger.warning(f"Error using CodeParser for {language}: {e}. Falling back to simple chunking.")
            return self._simple_chunk(code, file_path, language)

    def _create_chunks_from_points(self, code: str, file_path: str,
                                   points: List[int], language: str) -> List[ChunkInfo]:
        """Create chunks based on identified points of interest"""
        if not points:
            # If no points of interest, return the whole code as one chunk
            return [ChunkInfo(
                content=code,
                language=language,
                chunk_id=self._generate_chunk_id(code, file_path, 'full'),
                type='code',
                start_line=1,
                end_line=len(code.splitlines())
            )]

        lines = code.splitlines()
        chunks = []

        # Add the first point to simplify logic
        if 0 not in points:
            points = [0] + points

        # Add the end line to simplify logic
        if len(lines) - 1 not in points:
            points.append(len(lines) - 1)

        # Sort the points
        points = sorted(points)

        # Create chunks
        for i in range(len(points) - 1):
            start_idx = points[i]
            end_idx = points[i + 1] - 1 if i + 1 < len(points) else len(lines) - 1

            # Adjust for first chunk
            if start_idx == 0:
                start_idx = 0
                start_line = 1
            else:
                start_line = start_idx + 1

            # Create chunk content
            chunk_lines = lines[start_idx:end_idx + 1]
            content = "\n".join(chunk_lines)

            # Skip empty chunks
            if not content.strip():
                continue

            # Determine chunk type
            chunk_type = self._determine_chunk_type(chunk_lines)

            # Create the chunk
            chunk = ChunkInfo(
                content=content,
                language=language,
                chunk_id=self._generate_chunk_id(content, file_path, chunk_type),
                type=chunk_type,
                start_line=start_line,
                end_line=start_line + len(chunk_lines) - 1
            )

            # Extract imports if present
            chunk.imports = self._extract_imports(content, language)

            chunks.append(chunk)

        return chunks

    def _determine_chunk_type(self, lines: List[str]) -> str:
        """Determine the type of a chunk based on its content"""
        if not lines:
            return 'empty'

        first_line = lines[0].strip()

        # Check for imports
        if first_line.startswith(('import ', 'from ')):
            return 'import'

        # Check for class definitions
        if first_line.startswith('class '):
            return 'class'

        # Check for function definitions
        if any(first_line.startswith(prefix) for prefix in ['def ', 'async def ', 'function ', 'public ']):
            return 'function'

        # Check for API endpoints
        if any(pattern in first_line for pattern in ['@app.', '@router.', 'app.get', 'app.post']):
            return 'api'

        # Default to code
        return 'code'

    def _extract_imports(self, content: str, language: str) -> Set[str]:
        """Extract import statements from code"""
        imports = set()

        if language == 'python':
            # Regular expressions for Python imports
            import_patterns = [
                r'^import\s+(\S+)(?:\s+as\s+\S+)?',
                r'^from\s+(\S+)\s+import\s+'
            ]

            for line in content.splitlines():
                for pattern in import_patterns:
                    match = re.match(pattern, line.strip())
                    if match:
                        imports.add(match.group(1))

        elif language in ['javascript', 'typescript']:
            # Regular expressions for JS/TS imports
            import_patterns = [
                r'^import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'^import\s+[\'"]([^\'"]+)[\'"]'
            ]

            for line in content.splitlines():
                for pattern in import_patterns:
                    match = re.match(pattern, line.strip())
                    if match:
                        imports.add(match.group(1))

        return imports

    def _simple_chunk(self, code: str, file_path: str, language: str) -> List[ChunkInfo]:
        """
        Simple chunking method for when parser-based chunking fails or for unsupported languages
        """
        lines = code.splitlines()
        chunks = []

        # For very small files, just return the whole file
        if len(lines) <= 50:
            return [ChunkInfo(
                content=code,
                language=language,
                chunk_id=self._generate_chunk_id(code, file_path, 'full'),
                type='code',
                start_line=1,
                end_line=len(lines)
            )]

        # For larger files, use a sliding window approach
        chunk_size = 50
        overlap = 10

        for i in range(0, len(lines), chunk_size - overlap):
            end_idx = min(i + chunk_size, len(lines))
            chunk_content = "\n".join(lines[i:end_idx])

            # Skip empty chunks
            if not chunk_content.strip():
                continue

            chunk = ChunkInfo(
                content=chunk_content,
                language=language,
                chunk_id=self._generate_chunk_id(chunk_content, file_path, f'simple_{i}'),
                type='code',
                start_line=i + 1,
                end_line=end_idx
            )

            chunks.append(chunk)

            # Stop if we've reached the end
            if end_idx == len(lines):
                break

        return chunks


class ApiChunkingStrategy(BaseChunkingStrategy):
    """Strategy for API code chunks"""

    def chunk(self, code: str, file_path: str, language: Optional[str] = None) -> List[ChunkInfo]:
        language = language or self._identify_language(file_path)
        chunks = []
        current_lines = []
        in_api_block = False
        start_line = 0

        # Adjust API patterns based on language
        api_patterns = {
            'python': ['@app.', '@router.', 'app.get', 'app.post', 'app.put', 'app.delete'],
            'javascript': ['app.get', 'app.post', 'app.put', 'app.delete', 'router.get', 'router.post'],
            'typescript': ['app.get', 'app.post', 'app.put', 'app.delete', 'router.get', 'router.post']
        }

        # Get patterns for the current language or use Python patterns as default
        patterns = api_patterns.get(language, api_patterns['python'])

        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()

            # Detect API patterns
            if any(pattern in stripped for pattern in patterns):
                if current_lines:  # Save previous non-API chunk
                    content = '\n'.join(current_lines)
                    chunks.append(ChunkInfo(
                        content=content,
                        language=language,
                        chunk_id=self._generate_chunk_id(content, file_path, 'code'),
                        type='code',
                        start_line=start_line,
                        end_line=i - 1
                    ))
                    current_lines = []

                in_api_block = True
                start_line = i
                current_lines = [line]

            elif in_api_block:
                current_lines.append(line)
                if stripped == '' and len(current_lines) > 2:  # End of API block
                    content = '\n'.join(current_lines)
                    chunks.append(ChunkInfo(
                        content=content,
                        language=language,
                        chunk_id=self._generate_chunk_id(content, file_path, 'api'),
                        type='api',
                        start_line=start_line,
                        end_line=i,
                        metadata={'api_type': 'endpoint'}
                    ))
                    current_lines = []
                    in_api_block = False
                    start_line = i + 1

            else:
                current_lines.append(line)

        # Handle remaining lines
        if current_lines:
            content = '\n'.join(current_lines)
            chunks.append(ChunkInfo(
                content=content,
                language=language,
                chunk_id=self._generate_chunk_id(content, file_path, 'code'),
                type='code',
                start_line=start_line,
                end_line=len(code.splitlines())
            ))

        return chunks


class LogicalChunkingStrategy(BaseChunkingStrategy):
    """Strategy for logical code blocks (functions, classes)"""

    def chunk(self, code: str, file_path: str, language: Optional[str] = None) -> List[ChunkInfo]:
        language = language or self._identify_language(file_path)
        chunks = []
        current_lines = []
        start_line = 1

        # Different patterns based on language
        markers = {
            'python': [('def ', 'function'), ('class ', 'class'), ('async def ', 'function')],
            'javascript': [('function ', 'function'), ('class ', 'class'), ('const ', 'variable'),
                           ('let ', 'variable'), ('var ', 'variable')],
            'typescript': [('function ', 'function'), ('class ', 'class'), ('interface ', 'interface'),
                           ('type ', 'type'), ('const ', 'variable'), ('let ', 'variable')],
            'java': [('public class ', 'class'), ('private class ', 'class'), ('public interface ', 'interface'),
                     ('public void ', 'method'), ('private void ', 'method')]
        }

        # Get markers for the current language or use Python markers as default
        lang_markers = markers.get(language, markers['python'])

        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()

            # Check if line starts with any of the markers
            is_marker = False
            current_type = 'code'

            for marker, marker_type in lang_markers:
                if stripped.startswith(marker):
                    is_marker = True
                    current_type = marker_type
                    break

            if is_marker:
                if current_lines:  # Save previous chunk
                    content = '\n'.join(current_lines)
                    prev_type = self._determine_type(current_lines[0], language)
                    chunks.append(ChunkInfo(
                        content=content,
                        language=language,
                        chunk_id=self._generate_chunk_id(content, file_path, prev_type),
                        type=prev_type,
                        start_line=start_line,
                        end_line=i - 1
                    ))

                current_lines = [line]
                start_line = i
            else:
                current_lines.append(line)

        # Handle remaining lines
        if current_lines:
            content = '\n'.join(current_lines)
            current_type = self._determine_type(current_lines[0], language)
            chunks.append(ChunkInfo(
                content=content,
                language=language,
                chunk_id=self._generate_chunk_id(content, file_path, current_type),
                type=current_type,
                start_line=start_line,
                end_line=len(code.splitlines())
            ))

        return chunks

    def _determine_type(self, first_line: str, language: str) -> str:
        """Determine the type of a chunk based on its first line"""
        stripped = first_line.strip()

        if language == 'python':
            if stripped.startswith('class '):
                return 'class'
            elif stripped.startswith(('def ', 'async def ')):
                return 'function'

        elif language in ['javascript', 'typescript']:
            if stripped.startswith('class '):
                return 'class'
            elif stripped.startswith('function ') or '=> {' in stripped:
                return 'function'
            elif stripped.startswith('interface '):
                return 'interface'
            elif stripped.startswith('type '):
                return 'type'

        elif language == 'java':
            if stripped.startswith(('public class ', 'private class ')):
                return 'class'
            elif stripped.startswith(('public interface ', 'private interface ')):
                return 'interface'
            elif stripped.startswith(('public ', 'private ', 'protected ')) and ' void ' in stripped:
                return 'method'

        return 'code'


class ImportChunkingStrategy(BaseChunkingStrategy):
    """Strategy for import statements"""

    def chunk(self, code: str, file_path: str, language: Optional[str] = None) -> List[ChunkInfo]:
        language = language or self._identify_language(file_path)
        imports = []
        current_imports = []
        other_lines = []
        start_line = 1
        in_imports = False

        # Different import patterns based on language
        import_patterns = {
            'python': [('import ', 'from ')],
            'javascript': [('import ', 'require(')],
            'typescript': [('import ', 'require(')],
            'java': [('import ')]
        }

        # Get patterns for the current language or use Python patterns as default
        patterns = import_patterns.get(language, import_patterns['python'])
        patterns = [pattern for sublist in patterns for pattern in sublist]  # Flatten the list

        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()

            # Check if line starts with any import pattern
            if any(stripped.startswith(pattern) for pattern in patterns):
                if not in_imports and current_imports:
                    # Save previous import block
                    content = '\n'.join(current_imports)
                    imports.append(ChunkInfo(
                        content=content,
                        language=language,
                        chunk_id=self._generate_chunk_id(content, file_path, 'import'),
                        type='import',
                        start_line=start_line,
                        end_line=i - 1,
                        imports=set(imp.strip() for imp in current_imports)
                    ))

                in_imports = True
                if not current_imports:
                    start_line = i
                current_imports.append(line)

            elif in_imports and stripped == '':
                # Empty line after imports
                current_imports.append(line)

            else:
                if in_imports:
                    # End of import block
                    content = '\n'.join(current_imports)
                    imports.append(ChunkInfo(
                        content=content,
                        language=language,
                        chunk_id=self._generate_chunk_id(content, file_path, 'import'),
                        type='import',
                        start_line=start_line,
                        end_line=i - 1,
                        imports=set(imp.strip() for imp in current_imports)
                    ))
                    current_imports = []
                    in_imports = False

                other_lines.append(line)

        # Handle remaining imports
        if current_imports:
            content = '\n'.join(current_imports)
            imports.append(ChunkInfo(
                content=content,
                language=language,
                chunk_id=self._generate_chunk_id(content, file_path, 'import'),
                type='import',
                start_line=start_line,
                end_line=len(code.splitlines()),
                imports=set(imp.strip() for imp in current_imports)
            ))

        return imports


class CompositeChunkingStrategy(BaseChunkingStrategy):
    """
    A composite strategy that combines multiple strategies and merges their results
    """

    def __init__(self, strategies=None):
        super().__init__()
        self.strategies = strategies or [
            ParserBasedChunkingStrategy(),
            ImportChunkingStrategy(),
            ApiChunkingStrategy(),
            LogicalChunkingStrategy()
        ]

    def chunk(self, code: str, file_path: str, language: Optional[str] = None) -> List[ChunkInfo]:
        """
        Apply multiple chunking strategies and merge the results

        Args:
            code: Source code to chunk
            file_path: Path to the source file
            language: Optional language identifier

        Returns:
            List of ChunkInfo objects
        """
        language = language or self._identify_language(file_path)
        all_chunks = []

        # First try the parser-based strategy, which is most sophisticated
        try:
            parser_strategy = next(s for s in self.strategies if isinstance(s, ParserBasedChunkingStrategy))
            chunks = parser_strategy.chunk(code, file_path, language)

            # If parser-based strategy worked well, return its results
            if chunks and len(chunks) > 1:
                self.logger.info(f"Using parser-based chunking for {file_path}")
                return chunks

        except (StopIteration, Exception) as e:
            self.logger.warning(f"Parser-based chunking failed: {str(e)}")

        # If parser-based chunking didn't work well, try all other strategies
        for strategy in self.strategies:
            if isinstance(strategy, ParserBasedChunkingStrategy):
                continue  # Skip parser strategy as we already tried it

            try:
                chunks = strategy.chunk(code, file_path, language)
                all_chunks.extend(chunks)
            except Exception as e:
                self.logger.warning(f"Strategy {strategy.__class__.__name__} failed: {str(e)}")

        # If no chunks were found, fall back to simple line-based chunking
        if not all_chunks:
            self.logger.info(f"No chunks found by any strategy, falling back to simple chunking")
            return self._simple_chunk(code, file_path, language)

        # Sort chunks by start line and remove overlaps
        return self._resolve_overlaps(all_chunks)

    def _simple_chunk(self, code: str, file_path: str, language: str) -> List[ChunkInfo]:
        """Simple line-based chunking fallback"""
        lines = code.splitlines()
        chunk_size = 50  # lines per chunk
        overlap = 5  # lines of overlap between chunks
        chunks = []

        for i in range(0, len(lines), chunk_size - overlap):
            end_idx = min(i + chunk_size, len(lines))
            chunk_lines = lines[i:end_idx]
            content = "\n".join(chunk_lines)

            chunk = ChunkInfo(
                content=content,
                language=language,
                chunk_id=self._generate_chunk_id(content, file_path, f'simple'),
                type='code',
                start_line=i + 1,
                end_line=i + len(chunk_lines)
            )

            chunks.append(chunk)

            if end_idx >= len(lines):
                break

        return chunks

    def _resolve_overlaps(self, chunks: List[ChunkInfo]) -> List[ChunkInfo]:
        """Resolve overlapping chunks by prioritizing smaller, more specific chunks"""
        if not chunks:
            return []

        # Sort chunks by start line, then by size (smaller first)
        sorted_chunks = sorted(chunks, key=lambda c: (c.start_line, c.end_line - c.start_line))

        # For overlapping chunks, keep the one with higher priority type
        result = []

        # Define type priorities (lower number = higher priority)
        type_priority = {
            'import': 1,
            'api': 2,
            'function': 3,
            'class': 4,
            'interface': 5,
            'code': 6
        }

        for chunk in sorted_chunks:
            # Check if this chunk overlaps with any existing result
            overlapping = False

            for i, existing in enumerate(result):
                # Check for overlap
                if (chunk.start_line <= existing.end_line and
                        chunk.end_line >= existing.start_line):

                    # If overlapping, keep the higher priority one
                    chunk_priority = type_priority.get(chunk.type, 99)
                    existing_priority = type_priority.get(existing.type, 99)

                    if chunk_priority < existing_priority:
                        # Replace existing with current (higher priority)
                        result[i] = chunk

                    overlapping = True
                    break

            if not overlapping:
                result.append(chunk)

        # Sort the final result by start line
        return sorted(result, key=lambda c: c.start_line)


