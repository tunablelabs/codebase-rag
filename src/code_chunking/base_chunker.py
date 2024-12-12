from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional
from pathlib import Path
import logging
from dataclasses import dataclass

from .context import ChunkingContext
from git_parser.schemas import BaseEntity, ChunkMetadata

@dataclass
class DependencyInfo:
    """Store code dependency information"""
    imports: Set[str]
    class_refs: Set[str]
    function_calls: Set[str]
    variable_refs: Set[str]

class BaseChunker(ABC):
    """
    Base class for all code chunkers with integrated relationship analysis
    """
    
    def __init__(self, parser=None, relationship_analyzer=None):
        self.parser = parser
        self.relationship_analyzer = relationship_analyzer
        self.min_chunk_size = 100  # Minimum lines per chunk
        self.max_chunk_size = 1000  # Maximum lines per chunk
        self.chunks_metadata: Dict[str, ChunkMetadata] = {}
        
        # Configure logging
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def create_chunks(self, code: str, file_path: str, context: ChunkingContext) -> List[str]:
        """
        Create chunks from code based on context and file path.
        
        Args:
            code: Source code to chunk
            file_path: Path to the source file
            context: ChunkingContext containing analysis metadata
            
        Returns:
            List of code chunks
            
        Raises:
            ValueError: If input parameters are invalid
            RuntimeError: If chunking fails
        """
        pass
    
    @abstractmethod
    def merge_chunks(self, chunks: List[str], context: ChunkingContext) -> str:
        """
        Merge chunks back into a single code block.
        
        Args:
            chunks: List of code chunks to merge
            context: ChunkingContext containing merge metadata
            
        Returns:
            Merged code as single string
            
        Raises:
            ValueError: If chunks are invalid
        """
        pass
    
    @abstractmethod
    def _extract_dependencies(self, node) -> DependencyInfo:
        """
        Extract dependencies from a code node.
        Must be implemented by language-specific chunkers.
        
        Args:
            node: AST node to analyze
            
        Returns:
            DependencyInfo containing extracted dependencies
        """
        pass
    
    def get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """
        Get metadata for a specific chunk.
        
        Args:
            chunk_id: Unique identifier for the chunk
            
        Returns:
            ChunkMetadata if found, None otherwise
        """
        return self.chunks_metadata.get(chunk_id)
    
    def set_chunk_size_limits(self, min_size: int, max_size: int) -> None:
        """
        Configure minimum and maximum chunk sizes.
        
        Args:
            min_size: Minimum chunk size in lines
            max_size: Maximum chunk size in lines
            
        Raises:
            ValueError: If sizes are invalid
        """
        if min_size >= max_size:
            raise ValueError("Minimum size must be less than maximum size")
        if min_size < 0 or max_size < 0:
            raise ValueError("Chunk sizes cannot be negative")
            
        self.min_chunk_size = min_size
        self.max_chunk_size = max_size
    
    def _is_chunk_worthy(self, code_block: str, context: ChunkingContext) -> bool:
        """
        Determine if a code block should be its own chunk based on size and complexity.
        
        Args:
            code_block: Code block to evaluate
            context: Current chunking context
            
        Returns:
            Boolean indicating if block should be separate chunk
        """
        # Basic size check
        lines = code_block.count('\n') + 1
        if lines < self.min_chunk_size:
            return False
            
        # Check complexity
        complexity = self._analyze_complexity(code_block)
        
        # Consider both size and complexity
        return lines >= self.min_chunk_size or complexity > 5
    
    def _analyze_complexity(self, code: str) -> int:
        """
        Analyze code complexity.
        
        Args:
            code: Code to analyze
            
        Returns:
            Complexity score
        """
        complexity = 0
        for line in code.splitlines():
            stripped = line.strip()
            if any(keyword in stripped for keyword in ['if', 'for', 'while', 'except']):
                complexity += 1
            elif 'def ' in stripped or 'class ' in stripped:
                complexity += 2
        return complexity
    
    def _can_split_at_line(self, line: str) -> bool:
        """
        Check if it's safe to split at this line.
        
        Args:
            line: Line to check
            
        Returns:
            Boolean indicating if safe to split
        """
        stripped = line.strip()
        
        # Don't split in middle of statements
        if any(x in line for x in ['\\', '(', '{', '[']):
            return False
            
        # Don't split before closing brackets
        if any(stripped.startswith(x) for x in [')', '}', ']']):
            return False
            
        # Good split points
        return (not stripped or 
                stripped.endswith(':') or
                not any(x in stripped for x in ['\\', '(', '{', '[', ')', '}', ']']))
    
    def _split_by_size(self, code: str, target_size: int) -> List[str]:
        """
        Split code into chunks of approximately equal size while respecting code structure.
        
        Args:
            code: Code to split
            target_size: Target size for chunks
            
        Returns:
            List of code chunks
        """
        if not code:
            return []
            
        lines = code.splitlines()
        chunks = []
        current_chunk = []
        current_size = 0
        
        indent_level = 0
        for line in lines:
            # Track indent level
            stripped = line.lstrip()
            if stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try:')):
                indent_level += 1
            elif line.strip() == '' and indent_level > 0:
                indent_level -= 1
                
            current_chunk.append(line)
            current_size += 1
            
            if current_size >= target_size and indent_level == 0 and self._can_split_at_line(line):
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
                
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        return chunks
    
    def _update_context(self, chunk: str, file_path: str, context: ChunkingContext) -> None:
        """
        Update chunking context with chunk information.
        
        Args:
            chunk: Code chunk content
            file_path: Source file path
            context: ChunkingContext to update
        """
        chunk_id = self._generate_chunk_id(chunk, file_path)
        context.add_chunk(chunk_id, chunk)
        
        # Extract and add relationships if we have a relationship analyzer
        if self.relationship_analyzer and self.parser:
            try:
                tree = self.parser.parse(bytes(chunk, 'utf8'))
                deps = self._extract_dependencies(tree.root_node)
                for dep in deps.function_calls | deps.class_refs:
                    # Find which chunk contains this dependency
                    for other_id, other_chunk in context.chunks.items():
                        if dep in other_chunk:
                            context.add_relationship(chunk_id, other_id)
            except Exception as e:
                self.logger.warning(f"Failed to analyze relationships in chunk: {e}")
    
    def _generate_chunk_id(self, code: str, file_path: str) -> str:
        """
        Generate a unique identifier for a chunk.
        
        Args:
            code: Chunk content
            file_path: Source file path
            
        Returns:
            Unique chunk identifier
        """
        import hashlib
        content_hash = hashlib.md5(code.encode()).hexdigest()[:8]
        return f"{file_path}:{content_hash}"