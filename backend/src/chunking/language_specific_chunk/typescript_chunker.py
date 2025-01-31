from typing import List, Dict, Optional, Set
from tree_sitter import Node
import logging

from git_repo_parser.base_types import CodeEntity

from ..strategies import (
    BaseChunkingStrategy,
    ChunkInfo
)

class TSImportStrategy(BaseChunkingStrategy):
    """Handles TypeScript imports, exports, and type imports"""
    
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        imports = []
        current_imports = []
        start_line = 1
        max_import_chunk_size = 10  # Set a reasonable limit for chunk size
        
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            
            # Match TypeScript imports, including type imports
            if (stripped.startswith('import ') or 
                stripped.startswith('import type ') or
                stripped.startswith('export type ') or
                stripped.startswith('export ') or
                stripped.startswith('require(')):
                
                if not current_imports:
                    start_line = i
                current_imports.append(line)
            
            elif current_imports and stripped:
                # End of import block
                if len(current_imports) >= max_import_chunk_size:
                    content = '\n'.join(current_imports)
                    imports.append(ChunkInfo(
                        content=content,
                        language='typescript',
                        chunk_id=self._generate_chunk_id(content, file_path),
                        type='import',
                        start_line=start_line,
                        end_line=i-1,
                        imports=set(current_imports)
                    ))
                    current_imports = []
                else:
                    # Continue adding imports together
                    content = '\n'.join(current_imports)
                    imports.append(ChunkInfo(
                        content=content,
                        language='typescript',
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
            imports.append(ChunkInfo(
                content=content,
                language='typescript',
                chunk_id=self._generate_chunk_id(content, file_path),
                type='import',
                start_line=start_line,
                end_line=len(code.splitlines()),
                imports=set(current_imports)
            ))
        
        return imports

class TypeScriptChunker:
    """TypeScript-specific code chunker using tree-sitter"""
    
    def __init__(self, parser):
        self.parser = parser
        self.logger = logging.getLogger(self.__class__.__name__)
        self.import_strategy = TSImportStrategy()
    
    def create_chunks(self, code: str, file_path: str) -> List[ChunkInfo]:
        """Create chunks from TypeScript code"""
        try:
            chunks = []
            
            # Parse code with tree-sitter
            tree = self.parser.parse(bytes(code, 'utf-8'))
            if not tree:
                raise ValueError("Failed to parse TypeScript code")
            
            # First: Handle imports
            import_chunks = self.import_strategy.chunk(code, file_path)
            chunks.extend(import_chunks)
            
            # Second: Process rest of the code
            self._process_node(tree.root_node, code, file_path, chunks)
            
            # Enrich chunks with dependencies
            self._enrich_chunks(chunks, tree.root_node, code)
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error creating TypeScript chunks: {e}")
            return []
    
    def _process_node(self, node: Node, code: str, file_path: str, chunks: List[ChunkInfo]) -> None:
        """Process a TypeScript AST node"""
        try:
            if self._is_chunk_worthy(node):
                # Combine multiple statements or function declarations into one chunk
                chunk_content = code[node.start_byte:node.end_byte]
                chunk_type = self._determine_chunk_type(node)
                
                # Group multiple nodes if they belong together
                chunk = ChunkInfo(
                    content=chunk_content,
                    language='typescript',
                    chunk_id=self._generate_chunk_id(chunk_content, file_path),
                    type=chunk_type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    metadata=self._extract_metadata(node)
                )
                chunks.append(chunk)
        
            # Process children nodes and consider grouping them together
            for child in node.children:
                self._process_node(child, code, file_path, chunks)
    
        except Exception as e:
            self.logger.warning(f"Error processing node: {e}")
    
    def _is_chunk_worthy(self, node: Node) -> bool:
        """Determine if a node should be its own chunk based on context"""
        # Example rule to keep larger chunks
        return node.type in {
            'function_declaration',
            'class_declaration',
            'method_definition',
            'interface_declaration',
            'type_alias_declaration',
            'namespace_declaration'
        } or (len(node.children) > 3)  # If a node has many children, make it a larger chunk
    
    def _determine_chunk_type(self, node: Node) -> str:
        """Determine the type of TypeScript chunk"""
        type_mapping = {
            'function_declaration': 'function',
            'arrow_function': 'function',
            'class_declaration': 'class',
            'abstract_class_declaration': 'class',
            'method_definition': 'method',
            'export_statement': 'export',
            'object_pattern': 'object',
            'class_body': 'class_body',
            'interface_declaration': 'interface',
            'type_alias_declaration': 'type',
            'enum_declaration': 'enum',
            'namespace_declaration': 'namespace',
            'ambient_declaration': 'ambient'
        }
        return type_mapping.get(node.type, 'code')
    
    def _extract_metadata(self, node: Node) -> Dict:
        """Extract TypeScript-specific metadata"""
        metadata = {
            'node_type': node.type,
            'is_export': False,
            'is_async': False,
            'is_generator': False,
            'is_abstract': False,
            'is_interface': node.type == 'interface_declaration',
            'is_type_alias': node.type == 'type_alias_declaration',
            'is_enum': node.type == 'enum_declaration',
            'is_namespace': node.type == 'namespace_declaration',
            'is_ambient': node.type == 'ambient_declaration',
            'type_parameters': [],
            'type_constraints': [],
            'modifiers': []
        }
        
        try:
            # Check for exports
            parent = node.parent
            while parent:
                if parent.type == 'export_statement':
                    metadata['is_export'] = True
                    break
                parent = parent.parent
            
            # Check for modifiers and other properties
            for child in node.children:
                if child.type == 'async':
                    metadata['is_async'] = True
                elif child.type == 'generator_function':
                    metadata['is_generator'] = True
                elif child.type == 'abstract':
                    metadata['is_abstract'] = True
                elif child.type in ['public', 'private', 'protected', 'readonly', 'static']:
                    metadata['modifiers'].append(child.type)
                    
            # Extract type parameters if present
            type_params = self._get_type_parameters(node)
            if type_params:
                metadata['type_parameters'] = type_params
                
        except Exception as e:
            self.logger.warning(f"Error extracting metadata: {e}")
            
        return metadata
    
    def _get_type_parameters(self, node: Node) -> List[str]:
        """Extract type parameters from a node"""
        try:
            type_params = []
            for child in node.children:
                if child.type == 'type_parameters':
                    for param in child.children:
                        if param.type == 'type_parameter':
                            param_text = param.text.decode('utf-8')
                            type_params.append(param_text)
            return type_params
        except Exception as e:
            self.logger.warning(f"Error extracting type parameters: {e}")
            return []
    
    def _extract_dependencies(self, content: str, name_to_chunk: Dict[str, ChunkInfo]) -> Set[str]:
        """Extract dependencies from chunk content"""
        deps = set()
        try:
            # Parse the chunk
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            def visit_node(node: Node):
                if node.type == 'identifier' or node.type == 'type_identifier':
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
                if chunk.type in ['function', 'class', 'method', 'interface', 'type', 'enum', 'namespace']:
                    # Extract name from first line
                    first_line = chunk.content.splitlines()[0]
                    words = first_line.split()
                    for word in words:
                        if word not in ['function', 'class', 'interface', 'type', 'enum', 'namespace', 
                                      'async', 'export', 'default', 'abstract']:
                            name = word.split('(')[0].strip()
                            name = name.split('<')[0].strip()  # Remove type parameters
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
        
        # Read file to get imports as they might not be in entities
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Add import chunks
            import_chunks = self.import_strategy.chunk(content, file_path)
            chunks.extend(import_chunks)
            
            # Enrich with dependencies
            tree = self.parser.parse(bytes(content, 'utf-8'))
            if tree:
                self._enrich_chunks(chunks, tree.root_node, content)
                
        except Exception as e:
            self.logger.warning(f"Error processing imports and dependencies: {e}")
            
        return chunks