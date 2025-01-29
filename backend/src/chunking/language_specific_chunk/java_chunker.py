from typing import List, Dict, Optional, Set
from tree_sitter import Node
import logging

from git_repo_parser.base_types import CodeEntity
from ..strategies import (
    BaseChunkingStrategy,
    ChunkInfo
)

class JavaImportStrategy(BaseChunkingStrategy):
    """Handles Java imports and package declarations"""
    
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        imports = []
        current_imports = []
        package_line = None
        start_line = 1
        
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            
            # Handle package declaration
            if stripped.startswith('package '):
                package_line = line
                continue
                
            # Handle imports
            if stripped.startswith('import '):
                if not current_imports:
                    start_line = i
                current_imports.append(line)
                
            elif current_imports and stripped:
                # End of import block
                content = '\n'.join(current_imports)
                if package_line:
                    content = f"{package_line}\n\n{content}"
                    
                imports.append(ChunkInfo(
                    content=content,
                    language='java',
                    chunk_id=self._generate_chunk_id(content, file_path),
                    type='import',
                    start_line=start_line,
                    end_line=i-1,
                    imports=set(current_imports)
                ))
                current_imports = []
        
        # Handle remaining imports
        if current_imports:
            content = '\n'.join(current_imports)
            if package_line:
                content = f"{package_line}\n\n{content}"
                
            imports.append(ChunkInfo(
                content=content,
                language='java',
                chunk_id=self._generate_chunk_id(content, file_path),
                type='import',
                start_line=start_line,
                end_line=len(code.splitlines()),
                imports=set(current_imports)
            ))
        
        return imports

class JavaChunker:
    """Java-specific code chunker using tree-sitter"""
    
    def __init__(self, parser):
        self.parser = parser
        self.logger = logging.getLogger(self.__class__.__name__)
        self.import_strategy = JavaImportStrategy()
    
    def create_chunks(self, code: str, file_path: str) -> List[ChunkInfo]:
        """Create chunks from Java code"""
        try:
            chunks = []
            
            tree = self.parser.parse(bytes(code, 'utf-8'))
            if not tree:
                raise ValueError("Failed to parse Java code")
            
            # First: Extract imports and package
            import_chunks = self.import_strategy.chunk(code, file_path)
            chunks.extend(import_chunks)
            
            # Second: Process rest of the code with tree-sitter
            self._process_node(tree.root_node, code, file_path, chunks)
            
            # Enrich chunks with dependencies and relationships
            self._enrich_chunks(chunks, tree.root_node, code)
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error creating Java chunks: {e}")
            return []
    
    def create_chunks_from_entities(self, entities: List[CodeEntity], file_path: str) -> List[ChunkInfo]:
        """Create chunks from parsed entities."""
        chunks = []
        try:
            # Convert entities to chunks
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

            # Add imports (read file to get imports)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import_chunks = self.import_strategy.chunk(content, file_path)
            chunks.extend(import_chunks)
            
            # Enrich all chunks with dependencies
            tree = self.parser.parse(bytes(content, 'utf-8'))
            if tree:
                self._enrich_chunks(chunks, tree.root_node, content)
                
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error creating chunks from entities: {e}")
            return chunks
    
    def _process_node(self, node: Node, code: str, file_path: str, chunks: List[ChunkInfo]) -> None:
        """Process a Java AST node"""
        try:
            if self._is_chunk_worthy(node):
                chunk_content = code[node.start_byte:node.end_byte]
                chunk_type = self._determine_chunk_type(node)
                
                chunk = ChunkInfo(
                    content=chunk_content,
                    language='java',
                    chunk_id=self._generate_chunk_id(chunk_content, file_path),
                    type=chunk_type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    metadata=self._extract_metadata(node)
                )
                chunks.append(chunk)
            
            # Process child nodes
            for child in node.children:
                self._process_node(child, code, file_path, chunks)
                
        except Exception as e:
            self.logger.warning(f"Error processing node: {e}")
    
    def _is_chunk_worthy(self, node: Node) -> bool:
        """Determine if a node should be its own chunk"""
        return node.type in {
            'class_declaration',
            'method_declaration',
            'interface_declaration',
            'enum_declaration',
            'constructor_declaration',
            'static_initializer',
            'annotation_type_declaration'
        }
    
    def _determine_chunk_type(self, node: Node) -> str:
        """Determine the type of Java chunk"""
        type_mapping = {
            'class_declaration': 'class',
            'method_declaration': 'method',
            'interface_declaration': 'interface',
            'enum_declaration': 'enum',
            'constructor_declaration': 'constructor',
            'static_initializer': 'static_block',
            'annotation_type_declaration': 'annotation'
        }
        return type_mapping.get(node.type, 'code')
    
    def _extract_metadata(self, node: Node) -> Dict:
        """Extract Java-specific metadata"""
        metadata = {
            'node_type': node.type,
            'modifiers': [],
            'is_public': False,
            'is_private': False,
            'is_protected': False,
            'is_static': False,
            'is_final': False,
            'return_type': None
        }
        
        try:
            # Extract modifiers
            for child in node.children:
                if child.type == 'modifiers':
                    for modifier in child.children:
                        mod_text = modifier.text.decode('utf-8')
                        metadata['modifiers'].append(mod_text)
                        metadata[f'is_{mod_text}'] = True
                
                # Extract return type for methods
                elif child.type == 'type_identifier' and node.type == 'method_declaration':
                    metadata['return_type'] = child.text.decode('utf-8')
                    
        except Exception as e:
            self.logger.warning(f"Error extracting metadata: {e}")
            
        return metadata
    
    def _extract_dependencies(self, content: str, name_to_chunk: Dict[str, ChunkInfo]) -> Set[str]:
        """Extract dependencies from chunk content"""
        deps = set()
        try:
            # Parse the chunk
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            def visit_node(node: Node):
                if node.type == 'type_identifier':
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
    
    def _enrich_chunks(self, chunks: List[ChunkInfo], root_node: Node, code: str) -> None:
        """Add dependencies and relationships to chunks"""
        try:
            # Build name to chunk mapping
            name_to_chunk = {}
            for chunk in chunks:
                if chunk.type in ['class', 'interface', 'enum']:
                    # Extract name from first line
                    first_line = chunk.content.splitlines()[0]
                    words = first_line.split()
                    for word in words:
                        if word not in ['class', 'interface', 'enum', 'public', 'private', 'protected', 'static', 'final']:
                            name = word.split('{')[0].strip()
                            name_to_chunk[name] = chunk
                            break
            
            # Find dependencies
            for chunk in chunks:
                if chunk.type != 'import':
                    deps = self._extract_dependencies(chunk.content, name_to_chunk)
                    chunk.dependencies.update(deps)
                    
        except Exception as e:
            self.logger.warning(f"Error enriching chunks: {e}")
    
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