from typing import List, Dict, Optional, Set
from tree_sitter import Node
import logging

from git_repo_parser.base_types import CodeEntity

from ..strategies import (
    BaseChunkingStrategy, 
    ApiChunkingStrategy, 
    LogicalChunkingStrategy, 
    ImportChunkingStrategy,
    ChunkInfo
)

class PythonChunker:
    """Python-specific code chunker using tree-sitter and multiple strategies"""
    
    def __init__(self, parser):
        self.parser = parser
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize strategies
        self.import_strategy = ImportChunkingStrategy()
        self.api_strategy = ApiChunkingStrategy()
        self.logical_strategy = LogicalChunkingStrategy()
    
    def create_chunks(self, code: str, file_path: str) -> List[ChunkInfo]:
        """Create chunks from Python code using multiple strategies"""
        try:
            chunks = []
            
            # Parse code with tree-sitter
            tree = self.parser.parse(bytes(code, 'utf-8'))
            if not tree:
                raise ValueError("Failed to parse Python code")
            
            # First: Extract imports
            import_chunks = self.import_strategy.chunk(code, file_path)
            chunks.extend(import_chunks)
            
            # Second: Process rest of the code with tree-sitter
            self._process_node(tree.root_node, code, file_path, chunks)
            
            # Enrich chunks with dependencies and relationships
            self._enrich_chunks(chunks, tree.root_node, code)
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error creating Python chunks: {e}")
            return []
    
    def _process_node(self, node: Node, code: str, file_path: str, chunks: List[ChunkInfo]) -> None:
        """Process a Python AST node"""
        try:
            if self._is_chunk_worthy(node):
                chunk_content = code[node.start_byte:node.end_byte]
                
                # Determine chunk type and create appropriate chunk
                if self._is_api_node(node):
                    new_chunks = self.api_strategy.chunk(chunk_content, file_path)
                else:
                    new_chunks = self.logical_strategy.chunk(chunk_content, file_path)
                
                # Add tree-sitter specific metadata
                for chunk in new_chunks:
                    chunk.metadata.update({
                        'node_type': node.type,
                        'is_async': node.type == 'async_function_definition',
                        'has_decorators': any(child.type == 'decorator' for child in node.children)
                    })
                    chunks.append(chunk)
            
            # Process child nodes
            for child in node.children:
                self._process_node(child, code, file_path, chunks)
                
        except Exception as e:
            self.logger.warning(f"Error processing node: {e}")
    
    def _is_chunk_worthy(self, node: Node) -> bool:
        """Determine if a node should be its own chunk"""
        return node.type in {
            'function_definition',
            'async_function_definition',
            'class_definition',
            'decorated_definition'
        }
    
    def _is_api_node(self, node: Node) -> bool:
        """Check if node is an API endpoint"""
        try:
            # Check decorators for API patterns
            for child in node.children:
                if child.type == 'decorator':
                    decorator_text = child.text.decode('utf-8')
                    if any(pattern in decorator_text for pattern in ['@app.', '@router.']):
                        return True
            return False
        except Exception as e:
            self.logger.warning(f"Error checking API node: {e}")
            return False
    
    def _enrich_chunks(self, chunks: List[ChunkInfo], root_node: Node, code: str) -> None:
        """Add dependencies and relationships to chunks"""
        try:
            # Build a map of function and class names to chunks
            name_to_chunk = {}
            for chunk in chunks:
                if chunk.type in ['function', 'class']:
                    # Extract name from first line
                    first_line = chunk.content.splitlines()[0]
                    name = first_line.split()[1].split('(')[0]
                    name_to_chunk[name] = chunk
            
            # Process each chunk for dependencies
            for chunk in chunks:
                if chunk.type != 'import':  # Skip import chunks
                    deps = self._extract_dependencies(chunk.content, name_to_chunk)
                    chunk.dependencies.update(deps)
                    
        except Exception as e:
            self.logger.warning(f"Error enriching chunks: {e}")
    
    def _extract_dependencies(self, content: str, name_to_chunk: Dict[str, ChunkInfo]) -> Set[str]:
        """Extract dependencies from chunk content"""
        deps = set()
        try:
            # Parse the chunk
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            def visit_node(node: Node):
                if node.type == 'identifier':
                    name = node.text.decode('utf-8')
                    if name in name_to_chunk:
                        deps.add(name)
                for child in node.children:
                    visit_node(child)
            
            visit_node(tree.root_node)
            return deps
            
        except Exception as e:
            self.logger.warning(f"Error extracting dependencies: {e}")
            return deps
    
    def get_chunk_summary(self, chunk: ChunkInfo) -> Dict:
        """Get a summary of a chunk's contents"""
        return {
            'type': chunk.type,
            'language': chunk.language,
            'start_line': chunk.start_line,
            'end_line': chunk.end_line,
            'size': len(chunk.content),
            'num_lines': len(chunk.content.splitlines()),
            'dependencies': list(chunk.dependencies),
            'imports': list(chunk.imports),
            'metadata': chunk.metadata
        }
    
    def create_chunks_from_entities(self, entities: List[CodeEntity], file_path: str) -> List[ChunkInfo]:
        """Create chunks from parsed entities."""
        chunks = []
        for entity in entities:
            chunk_info = ChunkInfo(
                content=entity.content,
                language=entity.language,
                chunk_id=f"{file_path}:{entity.name}",
                type=entity.type,
                start_line=entity.location.start_line,
                end_line=entity.location.end_line,
                metadata=entity.metadata
            )
            chunks.append(chunk_info)
        return chunks
