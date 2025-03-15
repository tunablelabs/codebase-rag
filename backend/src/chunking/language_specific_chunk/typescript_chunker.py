from typing import List, Dict, Any, Optional, Set
from tree_sitter import Node
import logging
from config.logging_config import info, warning, debug, error
from ..strategies import BaseChunkingStrategy, ChunkInfo
from git_repo_parser.base_types import CodeEntity

class TSImportStrategy(BaseChunkingStrategy):
    """Handles TypeScript imports and exports"""
    
    MAX_IMPORTS_PER_CHUNK = 10
    
    def __init__(self):
        super().__init__()
        info("TSImportStrategy initialized")
    
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        info(f"Chunking TypeScript imports for file: {file_path}")
        chunks = []
        current_imports = []
        start_line = 1
        
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                continue
                
            # Check for imports and exports
            if (stripped.startswith('import ') or 
                stripped.startswith('import type ') or
                stripped.startswith('export type ') or
                stripped.startswith('export ') or
                stripped.startswith('require(')):
                
                if not current_imports:
                    start_line = i
                current_imports.append(line)
                
                # Create chunk when reaching max size
                if len(current_imports) >= self.MAX_IMPORTS_PER_CHUNK:
                    chunks.append(self._create_import_chunk(
                        current_imports, file_path, start_line, i
                    ))
                    current_imports = []
                    
            elif current_imports:
                # End of import block reached
                chunks.append(self._create_import_chunk(
                    current_imports, file_path, start_line, i-1
                ))
                current_imports = []
        
        # Handle remaining imports
        if current_imports:
            chunks.append(self._create_import_chunk(
                current_imports, file_path, start_line, len(code.splitlines())
            ))
        
        info(f"Created {len(chunks)} TypeScript import chunks")
        return chunks
    
    def _create_import_chunk(self, imports: List[str], file_path: str, 
                           start_line: int, end_line: int) -> ChunkInfo:
        """Create an import chunk with given imports"""
        content = '\n'.join(imports)
        return ChunkInfo(
            content=content,
            language='typescript',
            chunk_id=f"{file_path}:import_{start_line}_{end_line}",
            type='import',
            start_line=start_line,
            end_line=end_line,
            imports=set(imports),
            metadata={'num_imports': len(imports)}
        )

class TypeScriptChunker:
    """Enhanced TypeScript code chunker"""
    
    # Chunking configuration
    MAX_CHUNK_LINES = 100    # Maximum lines per chunk
    MIN_CHUNK_LINES = 10     # Minimum lines for standalone chunk
    MAX_METHOD_LINES = 50    # Maximum lines for method chunks
    MAX_GROUP_DISTANCE = 3   # Maximum lines between related entities
    LARGE_ENTITY_THRESHOLD = 100  # Threshold for splitting entities
    
    # TypeScript-specific patterns
    COHESIVE_TYPES = {
        'class', 'interface', 'enum', 'namespace', 'module'
    }
    
    RELATED_TYPES = {
        'class': {'method', 'property', 'constructor'},
        'interface': {'type', 'method_signature', 'property_signature'},
        'enum': {'enum_member'},
        'namespace': {'function', 'const', 'let', 'var', 'type'}
    }
    
    # Logical split points for large entities
    SPLIT_MARKERS = [
        '}',           # End of block
        '\n\n',       # Double newline
        'function',   # Function declaration
        'class',      # Class declaration
        'interface',  # Interface declaration
        'if ',        # Control structures
        'for ',
        'while ',
        'switch '
    ]
    
    def __init__(self, parser):
        self.parser = parser
        self.logger = logging.getLogger(self.__class__.__name__)
        self.import_strategy = TSImportStrategy()
        self.file_path = None
        info("TypeScriptChunker initialized")

    def create_chunks_from_entities(self, entities: List[CodeEntity], file_path: str) -> List[ChunkInfo]:
        """Create optimized chunks from TypeScript entities"""
        try:
            info(f"Creating chunks from {len(entities)} TypeScript entities for file: {file_path}")
            self.file_path = file_path
            
            # Read file content
            info(f"Reading TypeScript file: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                error(f"Error reading TypeScript file {file_path}: {e}")
                raise
            
            chunks = []
            
            # Handle imports first
            info("Processing TypeScript imports")
            import_chunks = self.import_strategy.chunk(content, file_path)
            chunks.extend(import_chunks)
            
            # Group and process entities
            info("Grouping and sorting TypeScript entities")
            sorted_entities = sorted(entities, key=lambda e: e.location.start_line)
            entity_groups = self._group_entities(sorted_entities)
            info(f"Created {len(entity_groups)} entity groups")
            
            # Process each group
            info("Processing entity groups")
            for group in entity_groups:
                new_chunks = self._process_entity_group(group)
                chunks.extend(new_chunks)
            
            # Add dependencies
            info("Adding dependencies between chunks")
            try:
                tree = self.parser.parse(bytes(content, 'utf-8'))
                if tree:
                    self._enrich_chunks(chunks, tree.root_node, content)
            except Exception as e:
                warning(f"Could not add dependencies: {e}")
            
            # Final size check and merging of small chunks
            info("Optimizing chunk sizes")
            chunks = self._optimize_chunk_sizes(chunks)
            
            info(f"Created total of {len(chunks)} chunks for {file_path}")
            return chunks
            
        except Exception as e:
            error(f"Error creating TypeScript chunks: {e}")
            return []

    def _process_entity_group(self, group: List[CodeEntity]) -> List[ChunkInfo]:
        """Process a group of entities, handling large entities appropriately"""
        chunks = []
        
        # Check if group contains large entities that need splitting
        total_lines = self._get_group_size(group)
        
        if total_lines > self.LARGE_ENTITY_THRESHOLD and len(group) == 1:
            # Single large entity - split it
            info(f"Splitting large entity of {total_lines} lines")
            chunks.extend(self._split_large_entity(group[0]))
        elif total_lines > self.LARGE_ENTITY_THRESHOLD:
            # Multiple entities forming large group - split at logical boundaries
            info(f"Splitting large group of {len(group)} entities with {total_lines} lines")
            chunks.extend(self._split_large_group(group))
        else:
            # Normal sized group - process as before
            chunk = self._create_chunk_from_group(group)
            if chunk:
                chunks.append(chunk)
        
        return chunks

    def _split_large_entity(self, entity: CodeEntity) -> List[ChunkInfo]:
        """Split a large entity into multiple smaller chunks"""
        info(f"Splitting large {entity.type} entity: {entity.name}")
        chunks = []
        lines = entity.content.splitlines()
        current_chunk_lines = []
        current_start_line = entity.location.start_line
        chunk_number = 1
        
        for i, line in enumerate(lines):
            current_chunk_lines.append(line)
            
            # Check for logical split points
            should_split = False
            if len(current_chunk_lines) >= self.MAX_CHUNK_LINES:
                should_split = True
            elif len(current_chunk_lines) > self.MIN_CHUNK_LINES:
                # Look for natural split points
                for marker in self.SPLIT_MARKERS:
                    if line.strip().startswith(marker):
                        should_split = True
                        break
            
            if should_split or i == len(lines) - 1:  # Also handle last chunk
                chunk = ChunkInfo(
                    content='\n'.join(current_chunk_lines),
                    language='typescript',
                    chunk_id=f"{self.file_path}:{entity.type}_{entity.name}_{chunk_number}",
                    type=entity.type,
                    start_line=current_start_line,
                    end_line=current_start_line + len(current_chunk_lines) - 1,
                    metadata={
                        'is_partial': True,
                        'parent_entity': entity.name,
                        'section_number': chunk_number,
                        'total_sections': (len(lines) // self.MAX_CHUNK_LINES) + 1,
                        'original_start': entity.location.start_line,
                        'original_end': entity.location.end_line,
                        'original_type': entity.type
                    }
                )
                chunks.append(chunk)
                current_chunk_lines = []
                current_start_line += len(current_chunk_lines)
                chunk_number += 1
        
        info(f"Split large entity into {len(chunks)} chunks")
        return chunks

    def _split_large_group(self, group: List[CodeEntity]) -> List[ChunkInfo]:
        """Split a large group of entities into logical chunks"""
        info(f"Splitting large group of {len(group)} entities")
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
                
                chunks.extend(self._split_large_entity(entity))
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
        
        info(f"Split large group into {len(chunks)} chunks")
        return chunks

    def _group_entities(self, entities: List[CodeEntity]) -> List[List[CodeEntity]]:
        """Group related entities based on type and proximity"""
        info(f"Grouping {len(entities)} entities by relation")
        if not entities:
            return []
            
        groups = []
        current_group = [entities[0]]
        
        for entity in entities[1:]:
            prev_entity = current_group[-1]
            
            # Check if entities should be grouped
            if self._should_merge_entities(prev_entity, entity):
                if self._get_group_size(current_group + [entity]) <= self.MAX_CHUNK_LINES:
                    current_group.append(entity)
                    continue
            
            # Start new group if can't merge
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
            
            # Check for small helper functions
            if entity1.type == 'function' and entity2.type == 'function':
                lines1 = len(entity1.content.splitlines())
                lines2 = len(entity2.content.splitlines())
                if (lines1 < self.MAX_METHOD_LINES and 
                    lines2 < self.MAX_METHOD_LINES and
                    entity2.location.start_line - entity1.location.end_line <= self.MAX_GROUP_DISTANCE):
                    return True
            
            return False
            
        except Exception as e:
            warning(f"Error checking entity merge: {e}")
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
            chunk_type = self._determine_group_type(entities)
            content = self._combine_entity_contents(entities)
            
            metadata = {
                'primary_type': chunk_type,
                'entity_types': list(set(e.type for e in entities)),
                'num_entities': len(entities),
                'declarations': [e.name for e in entities],
                'exports': any(e.metadata.get('is_export', False) for e in entities),
                'decorators': [d for e in entities 
                             for d in e.metadata.get('decorators', [])]
            }
            
            return ChunkInfo(
                content=content,
                language='typescript',
                chunk_id=f"{self.file_path}:{chunk_type}_{entities[0].location.start_line}",
                type=chunk_type,
                start_line=entities[0].location.start_line,
                end_line=entities[-1].location.end_line,
                metadata=metadata
            )
            
        except Exception as e:
            warning(f"Error creating chunk from group: {e}")
            return None

    def _determine_group_type(self, entities: List[CodeEntity]) -> str:
        """Determine the primary type for a group"""
        type_priority = ['class', 'interface', 'namespace', 'enum', 
                        'function', 'type', 'variable']
        
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

    def _optimize_chunk_sizes(self, chunks: List[ChunkInfo]) -> List[ChunkInfo]:
        """Optimize chunk sizes by merging small chunks"""
        info("Optimizing chunk sizes by merging small chunks")
        optimized = []
        current = None
        
        for chunk in sorted(chunks, key=lambda c: c.start_line):
            if chunk.type == 'import':
                optimized.append(chunk)
                continue
                
            if not current:
                current = chunk
                continue
            
            # Try to merge small chunks
            current_lines = len(current.content.splitlines())
            chunk_lines = len(chunk.content.splitlines())
            
            if (current_lines < self.MIN_CHUNK_LINES and 
                chunk_lines < self.MIN_CHUNK_LINES and
                current_lines + chunk_lines <= self.MAX_CHUNK_LINES and
                not current.metadata.get('is_partial') and 
                not chunk.metadata.get('is_partial')):
                # Merge chunks
                current = self._merge_chunks(current, chunk)
            else:
                optimized.append(current)
                current = chunk
        
        if current:
            optimized.append(current)
        
        info(f"Optimized chunks: {len(chunks)} -> {len(optimized)}")
        return optimized

    def _merge_chunks(self, chunk1: ChunkInfo, chunk2: ChunkInfo) -> ChunkInfo:
        """Merge two chunks into one"""
        content = f"{chunk1.content}\n\n{chunk2.content}"
        
        # Combine metadata
        metadata = {
            'primary_type': chunk1.metadata['primary_type'],
            'entity_types': list(set(chunk1.metadata['entity_types'] + 
                                   chunk2.metadata['entity_types'])),
            'num_entities': (chunk1.metadata['num_entities'] + 
                           chunk2.metadata['num_entities']),
            'declarations': (chunk1.metadata['declarations'] + 
                           chunk2.metadata['declarations']),
            'exports': (chunk1.metadata['exports'] or 
                       chunk2.metadata['exports'])
        }
        
        return ChunkInfo(
            content=content,
            language='typescript',
            chunk_id=f"{chunk1.chunk_id}_merged",
            type=chunk1.type,
            start_line=chunk1.start_line,
            end_line=chunk2.end_line,
            metadata=metadata
        )

    def _extract_dependencies(self, content: str, 
                            name_to_chunk: Dict[str, ChunkInfo]) -> Set[str]:
        """Extract dependencies from chunk content"""
        deps = set()
        try:
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            def visit_node(node: Node):
                if node.type in ['identifier', 'type_identifier']:
                    name = node.text.decode('utf-8')
                    if name in name_to_chunk:
                        deps.add(name)
                for child in node.children:
                    visit_node(child)
            
            visit_node(tree.root_node)
            return deps
            
        except Exception as e:
            warning(f"Error extracting dependencies: {e}")
            return deps

    def _enrich_chunks(self, chunks: List[ChunkInfo], root_node: Node, 
                      code: str) -> None:
        """Add dependencies and relationships to chunks"""
        try:
            info("Enriching chunks with dependencies")
            # Build name to chunk mapping
            name_to_chunk = {}
            for chunk in chunks:
                if chunk.type != 'import':
                    for name in chunk.metadata.get('declarations', []):
                        name_to_chunk[name] = chunk
            
            # Find dependencies
            for chunk in chunks:
                if chunk.type != 'import':
                    deps = self._extract_dependencies(chunk.content, name_to_chunk)
                    chunk.dependencies.update(deps)
            
            info("Chunks enriched successfully")
                    
        except Exception as e:
            warning(f"Error enriching chunks: {e}")