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
    
    MAX_IMPORTS_PER_CHUNK = 15  # Maximum imports per chunk
    
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
                
                # Create chunk when reaching max size
                if len(current_imports) >= self.MAX_IMPORTS_PER_CHUNK:
                    content = '\n'.join(current_imports)
                    if package_line and start_line == 1:
                        content = f"{package_line}\n\n{content}"
                        
                    imports.append(ChunkInfo(
                        content=content,
                        language='java',
                        chunk_id=f"{file_path}:import_{start_line}",
                        type='import',
                        start_line=start_line,
                        end_line=i,
                        imports=set(current_imports),
                        metadata={
                            'num_imports': len(current_imports),
                            'has_static_imports': any('import static' in imp for imp in current_imports)
                        }
                    ))
                    current_imports = []
                
            elif current_imports and stripped:
                # End of import block
                content = '\n'.join(current_imports)
                if package_line and start_line == 1:
                    content = f"{package_line}\n\n{content}"
                    
                imports.append(ChunkInfo(
                    content=content,
                    language='java',
                    chunk_id=f"{file_path}:import_{start_line}",
                    type='import',
                    start_line=start_line,
                    end_line=i-1,
                    imports=set(current_imports),
                    metadata={
                        'num_imports': len(current_imports),
                        'has_static_imports': any('import static' in imp for imp in current_imports)
                    }
                ))
                current_imports = []
        
        # Handle remaining imports
        if current_imports:
            content = '\n'.join(current_imports)
            if package_line and start_line == 1:
                content = f"{package_line}\n\n{content}"
                
            imports.append(ChunkInfo(
                content=content,
                language='java',
                chunk_id=f"{file_path}:import_{start_line}",
                type='import',
                start_line=start_line,
                end_line=len(code.splitlines()),
                imports=set(current_imports),
                metadata={
                    'num_imports': len(current_imports),
                    'has_static_imports': any('import static' in imp for imp in current_imports)
                }
            ))
        
        return imports

class JavaChunker:
    """Enhanced Java code chunker using tree-sitter"""
    
    # Chunking configuration
    MAX_CHUNK_LINES = 100    # Maximum lines per chunk
    MIN_CHUNK_LINES = 10     # Minimum lines for standalone chunk
    MAX_METHOD_LINES = 50    # Maximum lines for method chunks
    LARGE_ENTITY_THRESHOLD = 100  # Threshold for splitting entities
    
    # Java-specific patterns
    COHESIVE_TYPES = {
        'class', 'interface', 'enum', 'annotation'
    }
    
    RELATED_TYPES = {
        'class': {'method', 'constructor', 'field', 'inner_class'},
        'interface': {'method', 'field'},
        'enum': {'field', 'method', 'constructor'},
        'annotation': {'method', 'field'}
    }
    
    # Logical split points for large entities
    SPLIT_MARKERS = [
        '}',           # End of block
        '\n\n',       # Double newline
        'public ',    # Method modifiers
        'private ',
        'protected ',
        'static ',
        'class ',     # Inner class
        'if ',        # Control structures
        'for ',
        'while ',
        'try {',      # Error handling
        '@Override',  # Common annotations
        'return '     # Return statements
    ]
    
    def __init__(self, parser):
        self.parser = parser
        self.logger = logging.getLogger(self.__class__.__name__)
        self.import_strategy = JavaImportStrategy()
        self.file_path = None
    
    def create_chunks(self, code: str, file_path: str) -> List[ChunkInfo]:
        """Create chunks from Java code"""
        try:
            self.file_path = file_path
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
        """Create optimized chunks from Java entities"""
        try:
            self.file_path = file_path
            chunks = []
            
            # Group and process entities
            sorted_entities = sorted(entities, key=lambda e: e.location.start_line)
            entity_groups = self._group_entities(sorted_entities)
            
            # Process each group
            for group in entity_groups:
                new_chunks = self._process_entity_group(group)
                chunks.extend(new_chunks)
            
            # Add imports (read file to get imports)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            import_chunks = self.import_strategy.chunk(content, file_path)
            chunks.extend(import_chunks)
            
            # Add dependencies
            tree = self.parser.parse(bytes(content, 'utf-8'))
            if tree:
                self._enrich_chunks(chunks, tree.root_node, content)
                
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error creating chunks from entities: {e}")
            return chunks
    
    def _process_node(self, node: Node, code: str, file_path: str, chunks: List[ChunkInfo]) -> None:
        """Process a Java AST node with improved chunking logic"""
        try:
            if self._is_chunk_worthy(node):
                chunk_content = code[node.start_byte:node.end_byte]
                chunk_type = self._determine_chunk_type(node)
                metadata = self._extract_metadata(node)
                
                # Handle large entities
                content_lines = len(chunk_content.splitlines())
                if content_lines > self.LARGE_ENTITY_THRESHOLD:
                    chunks.extend(self._split_large_entity(
                        chunk_content, chunk_type,
                        node.start_point[0] + 1,
                        file_path, metadata
                    ))
                else:
                    chunk = ChunkInfo(
                        content=chunk_content,
                        language='java',
                        chunk_id=f"{file_path}:{chunk_type}_{node.start_point[0]+1}",
                        type=chunk_type,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        metadata=metadata
                    )
                    chunks.append(chunk)
            
            # Process child nodes
            for child in node.children:
                self._process_node(child, code, file_path, chunks)
                
        except Exception as e:
            self.logger.warning(f"Error processing node: {e}")
    
    def _process_entity_group(self, group: List[CodeEntity]) -> List[ChunkInfo]:
        """Process a group of entities, handling large entities appropriately"""
        chunks = []
        total_lines = self._get_group_size(group)
        
        if total_lines > self.LARGE_ENTITY_THRESHOLD and len(group) == 1:
            # Single large entity - split it
            chunks.extend(self._split_large_entity(
                group[0].content,
                group[0].type,
                group[0].location.start_line,
                self.file_path,
                group[0].metadata
            ))
        elif total_lines > self.LARGE_ENTITY_THRESHOLD:
            # Multiple entities forming large group - split at logical boundaries
            chunks.extend(self._split_large_group(group))
        else:
            # Normal sized group - create single chunk
            chunk = self._create_chunk_from_group(group)
            if chunk:
                chunks.append(chunk)
        
        return chunks

    def _split_large_entity(self, content: str, entity_type: str, start_line: int, 
                           file_path: str, metadata: Dict) -> List[ChunkInfo]:
        """Split a large entity into multiple smaller chunks"""
        chunks = []
        lines = content.splitlines()
        current_chunk_lines = []
        current_start = start_line
        chunk_number = 1
        
        for i, line in enumerate(lines):
            current_chunk_lines.append(line)
            
            # Check for logical split points
            should_split = False
            if len(current_chunk_lines) >= self.MAX_CHUNK_LINES:
                should_split = True
            elif len(current_chunk_lines) > self.MIN_CHUNK_LINES:
                if any(line.strip().startswith(marker) for marker in self.SPLIT_MARKERS):
                    should_split = True
            
            if should_split or i == len(lines) - 1:
                chunk = ChunkInfo(
                    content='\n'.join(current_chunk_lines),
                    language='java',
                    chunk_id=f"{file_path}:{entity_type}_{current_start}_{chunk_number}",
                    type=entity_type,
                    start_line=current_start,
                    end_line=current_start + len(current_chunk_lines) - 1,
                    metadata={
                        **metadata,
                        'is_partial': True,
                        'section_number': chunk_number,
                        'total_sections': (len(lines) // self.MAX_CHUNK_LINES) + 1
                    }
                )
                chunks.append(chunk)
                current_chunk_lines = []
                current_start += len(current_chunk_lines)
                chunk_number += 1
        
        return chunks

    def _split_large_group(self, group: List[CodeEntity]) -> List[ChunkInfo]:
        """Split a large group of entities into logical chunks"""
        chunks = []
        current_group = []
        current_lines = 0
        
        for entity in group:
            entity_lines = len(entity.content.splitlines())
            
            if entity_lines > self.LARGE_ENTITY_THRESHOLD:
                # Handle individual large entity
                if current_group:
                    chunk = self._create_chunk_from_group(current_group)
                    if chunk:
                        chunks.append(chunk)
                    current_group = []
                    current_lines = 0
                
                chunks.extend(self._split_large_entity(
                    entity.content,
                    entity.type,
                    entity.location.start_line,
                    self.file_path,
                    entity.metadata
                ))
            elif current_lines + entity_lines > self.MAX_CHUNK_LINES:
                # Create chunk from current group and start new group
                chunk = self._create_chunk_from_group(current_group)
                if chunk:
                    chunks.append(chunk)
                current_group = [entity]
                current_lines = entity_lines
            else:
                # Add to current group
                current_group.append(entity)
                current_lines += entity_lines
        
        # Handle remaining group
        if current_group:
            chunk = self._create_chunk_from_group(current_group)
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _group_entities(self, entities: List[CodeEntity]) -> List[List[CodeEntity]]:
        """Group related entities based on type and proximity"""
        if not entities:
            return []
            
        groups = []
        current_group = [entities[0]]
        
        for entity in entities[1:]:
            prev_entity = current_group[-1]
            
            if self._should_merge_entities(prev_entity, entity):
                if self._get_group_size(current_group + [entity]) <= self.MAX_CHUNK_LINES:
                    current_group.append(entity)
                    continue
            
            if current_group:
                groups.append(current_group)
            current_group = [entity]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _should_merge_entities(self, entity1: CodeEntity, entity2: CodeEntity) -> bool:
        """Determine if two entities should be merged"""
        try:
            # Check if entities are closely related
            if entity1.type in self.COHESIVE_TYPES:
                related_types = self.RELATED_TYPES.get(entity1.type, set())
                if entity2.type in related_types:
                    return True
            
            # Check for related methods
            if entity1.type == 'method' and entity2.type == 'method':
                lines1 = len(entity1.content.splitlines())
                lines2 = len(entity2.content.splitlines())
                if (lines1 < self.MAX_METHOD_LINES and lines2 < self.MAX_METHOD_LINES and
                    entity2.location.start_line - entity1.location.end_line <= 3):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking entity merge: {e}")
            return False
    
    def _get_group_size(self, entities: List[CodeEntity]) -> int:
        """Get total lines in a group of entities"""
        if not entities:
            return 0
            
        start_line = min(e.location.start_line for e in entities)
        end_line = max(e.location.end_line for e in entities)
        return end_line - start_line + 1

    def _create_chunk_from_group(self, entities: List[CodeEntity]) -> Optional[ChunkInfo]:
        """Create a chunk from a group of entities"""
        if not entities:
            return None
            
        try:
            entities = sorted(entities, key=lambda e: e.location.start_line)
            chunk_type = self._determine_primary_type(entities)
            content = self._combine_entity_contents(entities)
            
            metadata = {
                'primary_type': chunk_type,
                'entity_types': list(set(e.type for e in entities)),
                'num_entities': len(entities),
                'declarations': [e.name for e in entities],
                'has_constructor': any(
                    e.type == 'constructor' for e in entities
                ),
                'has_inner_class': any(
                    e.metadata.get('is_inner_class', False) for e in entities
                ),
                'is_public': any(e.metadata.get('is_public', False) for e in entities),
                'is_static': any(e.metadata.get('is_static', False) for e in entities),
                'is_abstract': any(e.metadata.get('is_abstract', False) for e in entities),
                'annotations': list(set(
                    ann for e in entities 
                    for ann in e.metadata.get('annotations', [])
                ))
            }
            
            return ChunkInfo(
                content=content,
                language='java',
                chunk_id=f"{self.file_path}:{chunk_type}_{entities[0].location.start_line}",
                type=chunk_type,
                start_line=entities[0].location.start_line,
                end_line=entities[-1].location.end_line,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.warning(f"Error creating chunk from group: {e}")
            return None

    def _determine_primary_type(self, entities: List[CodeEntity]) -> str:
        """Determine the primary type for a group of entities"""
        type_priority = ['class', 'interface', 'enum', 'annotation',
                        'constructor', 'method', 'field']
        
        # First check priority types
        for priority_type in type_priority:
            if any(e.type == priority_type for e in entities):
                return priority_type
        
        # Default to most common type
        type_counts = {}
        for entity in entities:
            type_counts[entity.type] = type_counts.get(entity.type, 0) + 1
        
        return max(type_counts.items(), key=lambda x: x[1])[0]

    def _combine_entity_contents(self, entities: List[CodeEntity]) -> str:
        """Combine entity contents preserving formatting"""
        if len(entities) == 1:
            return entities[0].content
        
        contents = []
        last_end_line = 0
        
        for entity in sorted(entities, key=lambda e: e.location.start_line):
            if last_end_line > 0:
                line_diff = entity.location.start_line - last_end_line
                if line_diff > 1:
                    contents.append('\n' * min(line_diff - 1, 2))
            
            contents.append(entity.content)
            last_end_line = entity.location.end_line
        
        return '\n'.join(filter(None, contents))

    def _is_chunk_worthy(self, node: Node) -> bool:
        """Determine if a node should be its own chunk"""
        return node.type in {
            'class_declaration',
            'method_declaration',
            'interface_declaration',
            'enum_declaration',
            'constructor_declaration',
            'static_initializer',
            'annotation_type_declaration',
            'field_declaration'
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
            'annotation_type_declaration': 'annotation',
            'field_declaration': 'field'
        }
        return type_mapping.get(node.type, 'code')
    
    def _extract_metadata(self, node: Node) -> Dict:
        """Extract enhanced Java-specific metadata"""
        metadata = {
            'node_type': node.type,
            'modifiers': [],
            'is_public': False,
            'is_private': False,
            'is_protected': False,
            'is_static': False,
            'is_final': False,
            'is_abstract': False,
            'is_synchronized': False,
            'return_type': None,
            'annotations': [],
            'extends': None,
            'implements': [],
            'has_inner_classes': False,
            'is_inner_class': False,
            'parent_class': None,
            'generics': [],
            'throws': [],
            'is_interface_method': False,
            'is_override': False
        }
        
        try:
            # Extract modifiers and more detailed information
            for child in node.children:
                if child.type == 'modifiers':
                    for modifier in child.children:
                        mod_text = modifier.text.decode('utf-8')
                        metadata['modifiers'].append(mod_text)
                        metadata[f'is_{mod_text.lower()}'] = True
                
                elif child.type == 'type_identifier' and node.type == 'method_declaration':
                    metadata['return_type'] = child.text.decode('utf-8')
                
                elif child.type == 'superclass':
                    metadata['extends'] = child.text.decode('utf-8')
                
                elif child.type == 'super_interfaces':
                    metadata['implements'] = [
                        i.text.decode('utf-8') for i in child.children 
                        if i.type == 'type_identifier'
                    ]
                
                elif child.type == 'annotation':
                    ann_text = child.text.decode('utf-8')
                    metadata['annotations'].append(ann_text)
                    if ann_text == '@Override':
                        metadata['is_override'] = True
                
                elif child.type == 'throws':
                    metadata['throws'] = [
                        e.text.decode('utf-8') for e in child.children 
                        if e.type == 'type_identifier'
                    ]
                
            # Additional context checks
            if node.parent and node.parent.type == 'class_body':
                for sibling in node.parent.children:
                    if sibling.type == 'class_declaration':
                        metadata['has_inner_classes'] = True
                        break
            
            if (node.parent and node.parent.parent and 
                node.parent.parent.type == 'class_declaration'):
                metadata['is_inner_class'] = True
                
            if (node.parent and node.parent.parent and 
                node.parent.parent.type == 'interface_declaration'):
                metadata['is_interface_method'] = True
                
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
                if node.type in {'type_identifier', 'identifier'}:
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
                if chunk.type in ['class', 'interface', 'enum', 'annotation']:
                    # Extract name from first line
                    first_line = chunk.content.splitlines()[0]
                    words = first_line.split()
                    for word in words:
                        if word not in ['class', 'interface', 'enum', 'public', 
                                      'private', 'protected', 'static', 'final']:
                            name = word.split('{')[0].strip()
                            name_to_chunk[name] = chunk
                            break
            
            # Find dependencies between chunks
            for chunk in chunks:
                if chunk.type != 'import':
                    deps = self._extract_dependencies(chunk.content, name_to_chunk)
                    chunk.dependencies.update(deps)
                    
                    # Add relationship metadata
                    if chunk.metadata.get('extends'):
                        parent = chunk.metadata['extends']
                        if parent in name_to_chunk:
                            chunk.metadata['parent_chunk'] = name_to_chunk[parent].chunk_id
                    
                    implements = chunk.metadata.get('implements', [])
                    if implements:
                        chunk.metadata['interface_chunks'] = [
                            name_to_chunk[iface].chunk_id 
                            for iface in implements 
                            if iface in name_to_chunk
                        ]
                    
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
            'metadata': chunk.metadata,
            'is_partial': chunk.metadata.get('is_partial', False),
            'parent_entity': chunk.metadata.get('parent_entity', None),
            'section_number': chunk.metadata.get('section_number'),
            'total_sections': chunk.metadata.get('total_sections')
        }