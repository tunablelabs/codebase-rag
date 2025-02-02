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

class PythonImportStrategy(ImportChunkingStrategy):
    """Enhanced Python import strategy"""
    
    MAX_IMPORTS_PER_CHUNK = 10
    
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        chunks = []
        current_imports = []
        start_line = 1
        
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
                
            # Check for imports
            if (stripped.startswith('import ') or 
                stripped.startswith('from ')):
                
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
                # End of import block
                chunks.append(self._create_import_chunk(
                    current_imports, file_path, start_line, i-1
                ))
                current_imports = []
        
        # Handle remaining imports
        if current_imports:
            chunks.append(self._create_import_chunk(
                current_imports, file_path, start_line, len(code.splitlines())
            ))
        
        return chunks
    
    def _create_import_chunk(self, imports: List[str], file_path: str, 
                           start_line: int, end_line: int) -> ChunkInfo:
        """Create an import chunk with metadata"""
        content = '\n'.join(imports)
        return ChunkInfo(
            content=content,
            language='python',
            chunk_id=f"{file_path}:import_{start_line}_{end_line}",
            type='import',
            start_line=start_line,
            end_line=end_line,
            imports=set(imports),
            metadata={
                'num_imports': len(imports),
                'has_from_imports': any('from ' in imp for imp in imports),
                'has_relative_imports': any('from .' in imp for imp in imports)
            }
        )

class PythonChunker:
    """Enhanced Python code chunker with large entity handling"""
    
    # Chunking configuration
    MAX_CHUNK_LINES = 100    # Maximum lines per chunk
    MIN_CHUNK_LINES = 10     # Minimum lines for standalone chunk
    MAX_METHOD_LINES = 50    # Maximum lines for method chunks
    LARGE_ENTITY_THRESHOLD = 100  # Threshold for splitting entities
    
    # Python-specific patterns
    COHESIVE_TYPES = {
        'class', 'module', 'function', 'dataclass'
    }
    
    RELATED_TYPES = {
        'class': {'method', 'property', 'class_variable'},
        'dataclass': {'method', 'field'},
        'function': {'function', 'async_function'},
        'module': {'function', 'class', 'constant'}
    }
    
    # Logical split points for large entities
    SPLIT_MARKERS = [
        'def ',        # Function definition
        'class ',      # Class definition
        'async def ',  # Async function
        '@',          # Decorator
        'if ',        # Control structures
        'for ',
        'while ',
        'try:',       # Exception handling
        'except ',
        'finally:',
        'return ',    # Return statements
        '# SECTION',  # Manual section markers
        '\n\n'        # Double newline
    ]
    
    def __init__(self, parser):
        self.parser = parser
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize strategies
        self.import_strategy = PythonImportStrategy()
        self.api_strategy = ApiChunkingStrategy()
        self.logical_strategy = LogicalChunkingStrategy()
        self.file_path = None
    
    def create_chunks_from_entities(self, entities: List[CodeEntity], file_path: str) -> List[ChunkInfo]:
        """Create optimized chunks from Python entities"""
        try:
            self.file_path = file_path
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks = []
            
            # Handle imports first
            import_chunks = self.import_strategy.chunk(content, file_path)
            chunks.extend(import_chunks)
            
            # Group and process entities
            sorted_entities = sorted(entities, key=lambda e: e.location.start_line)
            entity_groups = self._group_entities(sorted_entities)
            
            # Process each group
            for group in entity_groups:
                new_chunks = self._process_entity_group(group)
                chunks.extend(new_chunks)
            
            # Process API endpoints if any
            api_entities = [e for e in entities if self._is_api_entity(e)]
            for entity in api_entities:
                api_chunks = self.api_strategy.chunk(entity.content, file_path)
                chunks.extend(api_chunks)
            
            # Add dependencies
            tree = self.parser.parse(bytes(content, 'utf-8'))
            if tree:
                self._enrich_chunks(chunks, tree.root_node, content)
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error creating Python chunks: {e}")
            return []

    def _is_api_entity(self, entity: CodeEntity) -> bool:
        """Check if entity is an API endpoint"""
        decorators = entity.metadata.get('decorators', [])
        return any(d.startswith(('@app.', '@router.')) for d in decorators)

    def _process_entity_group(self, group: List[CodeEntity]) -> List[ChunkInfo]:
        """Process a group of entities, handling large entities appropriately"""
        chunks = []
        total_lines = self._get_group_size(group)
        
        if total_lines > self.LARGE_ENTITY_THRESHOLD and len(group) == 1:
            # Single large entity - split it
            chunks.extend(self._split_large_entity(group[0]))
        elif total_lines > self.LARGE_ENTITY_THRESHOLD:
            # Multiple entities forming large group - split at logical boundaries
            chunks.extend(self._split_large_group(group))
        else:
            # Normal sized group - process with appropriate strategy
            if self._is_api_entity(group[0]):
                chunks.extend(self.api_strategy.chunk(group[0].content, self.file_path))
            else:
                chunk = self._create_chunk_from_group(group)
                if chunk:
                    chunks.append(chunk)
        
        return chunks

    def _split_large_entity(self, entity: CodeEntity) -> List[ChunkInfo]:
        """Split a large entity into multiple smaller chunks"""
        chunks = []
        lines = entity.content.splitlines()
        current_chunk_lines = []
        current_start_line = entity.location.start_line
        chunk_number = 1
        current_indent = None
        
        for i, line in enumerate(lines):
            # Track Python indentation
            if not line.strip():
                current_chunk_lines.append(line)
                continue
                
            indent = len(line) - len(line.lstrip())
            if current_indent is None:
                current_indent = indent
            
            current_chunk_lines.append(line)
            
            # Check for logical split points
            should_split = False
            if len(current_chunk_lines) >= self.MAX_CHUNK_LINES:
                should_split = True
            elif len(current_chunk_lines) > self.MIN_CHUNK_LINES:
                # Only split at matching indentation level
                if indent <= current_indent:
                    for marker in self.SPLIT_MARKERS:
                        if line.lstrip().startswith(marker):
                            should_split = True
                            break
            
            if should_split or i == len(lines) - 1:
                chunk = ChunkInfo(
                    content='\n'.join(current_chunk_lines),
                    language='python',
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
                        'original_type': entity.type,
                        'is_async': entity.metadata.get('is_async', False),
                        'decorators': entity.metadata.get('decorators', []),
                        'docstring': self._extract_docstring(current_chunk_lines)
                    }
                )
                chunks.append(chunk)
                current_chunk_lines = []
                current_start_line += len(current_chunk_lines)
                chunk_number += 1
                current_indent = None
        
        return chunks

    def _extract_docstring(self, lines: List[str]) -> Optional[str]:
        """Extract docstring from chunk lines"""
        try:
            content = '\n'.join(lines)
            tree = self.parser.parse(bytes(content, 'utf-8'))
            for node in tree.root_node.children:
                if node.type == 'expression_statement':
                    child = node.children[0] if node.children else None
                    if child and child.type in ('string', 'string_content'):
                        return child.text.decode('utf-8').strip('"\' \n\t')
            return None
        except Exception:
            return None

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
        
        return chunks

    def _group_entities(self, entities: List[CodeEntity]) -> List[List[CodeEntity]]:
        """Group related entities based on type and proximity"""
        if not entities:
            return []
            
        groups = []
        current_group = [entities[0]]
        current_indent = None
        
        for entity in entities[1:]:
            prev_entity = current_group[-1]
            
            # Get indentation level from first line
            first_line = entity.content.splitlines()[0]
            indent = len(first_line) - len(first_line.lstrip())
            
            if current_indent is None:
                current_indent = indent
            
            # Check merging conditions
            should_merge = (
                self._should_merge_entities(prev_entity, entity) and
                indent >= current_indent and
                self._get_group_size(current_group + [entity]) <= self.MAX_CHUNK_LINES
            )
            
            if should_merge:
                current_group.append(entity)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [entity]
                current_indent = indent
        
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
            
            # Check for related functions
            if entity1.type in ['function', 'async_function'] and entity2.type in ['function', 'async_function']:
                lines1 = len(entity1.content.splitlines())
                lines2 = len(entity2.content.splitlines())
                if lines1 < self.MAX_METHOD_LINES and lines2 < self.MAX_METHOD_LINES:
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
            chunk_type = self._determine_group_type(entities)
            content = self._combine_entity_contents(entities)
            
            metadata = {
                'primary_type': chunk_type,
                'entity_types': list(set(e.type for e in entities)),
                'num_entities': len(entities),
                'declarations': [e.name for e in entities],
                'is_async': any(e.metadata.get('is_async', False) for e in entities),
                'decorators': [d for e in entities 
                             for d in e.metadata.get('decorators', [])],
                'has_docstring': any(e.metadata.get('docstring') for e in entities),
                'is_api': any(self._is_api_entity(e) for e in entities),
            }
            
            return ChunkInfo(
                content=content,
                language='python',
                chunk_id=f"{self.file_path}:{chunk_type}_{entities[0].location.start_line}",
                type=chunk_type,
                start_line=entities[0].location.start_line,
                end_line=entities[-1].location.end_line,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.warning(f"Error creating chunk from group: {e}")
            return None

    def _determine_group_type(self, entities: List[CodeEntity]) -> str:
        """Determine the primary type for a group"""
        type_priority = ['class', 'function', 'async_function', 'method', 
                        'property', 'dataclass']
        
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
        """Combine entity contents preserving formatting and indentation"""
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

    def _extract_dependencies(self, content: str, name_to_chunk: Dict[str, ChunkInfo]) -> Set[str]:
        """Extract dependencies from chunk content"""
        deps = set()
        try:
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

    def _enrich_chunks(self, chunks: List[ChunkInfo], root_node: Node, code: str) -> None:
        """Add dependencies and relationships to chunks"""
        try:
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
            'has_docstring': chunk.metadata.get('has_docstring', False),
            'is_api': chunk.metadata.get('is_api', False)
        }