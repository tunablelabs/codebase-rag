from typing import List, Optional, Dict, Set
from tree_sitter import Node
import logging

from .base_chunker import BaseChunker, DependencyInfo
from .context import ChunkingContext
from git_parser.schemas import BaseEntity, ChunkMetadata

class PythonChunker(BaseChunker):
    """Python-specific implementation of code chunker with vector DB support."""
    
    def __init__(self, parser, relationship_analyzer):
        super().__init__(parser, relationship_analyzer)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.dependency_cache = {}
        
    def _extract_dependencies(self, node: Node) -> DependencyInfo:
        """
        Extract dependencies from a Python code node.
        Implementation of required BaseChunker method.
        """
        # Cache check
        node_id = id(node)
        if node_id in self.dependency_cache:
            return self.dependency_cache[node_id]

        imports = set()
        class_refs = set()
        function_calls = set()
        variable_refs = set()

        def visit_node(current_node: Node):
            if current_node.type == "import_statement":
                imports.add(current_node.text.decode('utf-8').strip())
            elif current_node.type == "import_from_statement":
                imports.add(current_node.text.decode('utf-8').strip())
            elif current_node.type == "identifier":
                text = current_node.text.decode('utf-8')
                if text:
                    if text[0].isupper():
                        class_refs.add(text)
                    else:
                        # Check if it's a function call
                        parent = current_node.parent
                        if parent and parent.type == "call":
                            function_calls.add(text)
                        else:
                            variable_refs.add(text)
            
            for child in current_node.children:
                visit_node(child)

        visit_node(node)
        
        deps = DependencyInfo(
            imports=imports,
            class_refs=class_refs,
            function_calls=function_calls,
            variable_refs=variable_refs
        )
        
        self.dependency_cache[node_id] = deps
        return deps
    
    
    def _is_complex_node(self, node: Node) -> bool:
        """
        Determine if a node is complex enough to warrant its own chunk.
        """
        try:
            # Count nested structures
            nested_count = sum(1 for child in node.children 
                            if self._is_significant_python_node(child))
            
            # Count lines
            lines = node.text.decode('utf8').count('\n') + 1
            
            return nested_count >= 2 or lines >= self.min_chunk_size
            
        except Exception as e:
            self.logger.warning(f"Error checking node complexity: {e}")
            return False

    def _is_pydantic_model(self, node: Node) -> bool:
        """Check if node is a Pydantic model."""
        try:
            if node.type != "class_definition":
                return False
                
            bases_node = node.child_by_field_name("bases")
            if bases_node:
                bases_text = bases_node.text.decode('utf8')
                return 'BaseModel' in bases_text
            return False
        except Exception as e:
            self.logger.warning(f"Error checking Pydantic model: {e}")
            return False

    def _is_exception_class(self, node: Node) -> bool:
        """Check if node is an exception class."""
        try:
            if node.type != "class_definition":
                return False
                
            bases_node = node.child_by_field_name("bases")
            if bases_node:
                bases_text = bases_node.text.decode('utf8')
                return any(base in bases_text for base in ['Exception', 'Error'])
            return False
        except Exception as e:
            self.logger.warning(f"Error checking exception class: {e}")
            return False

    def _is_test_class(self, node: Node) -> bool:
        """Check if node is a test class."""
        try:
            if node.type != "class_definition":
                return False
                
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode('utf8')
                return name.startswith('Test') or name.endswith('Test')
            return False
        except Exception as e:
            self.logger.warning(f"Error checking test class: {e}")
            return False

    def _is_test_function(self, node: Node) -> bool:
        """Check if node is a test function."""
        try:
            if node.type not in ["function_definition", "async_function_definition"]:
                return False
                
            name_node = node.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode('utf8')
                return name.startswith('test_')
            return False
        except Exception as e:
            self.logger.warning(f"Error checking test function: {e}")
            return False

    def _has_api_decorators(self, node: Node) -> bool:
        """Check if node has API-related decorators."""
        try:
            for child in node.children:
                if child.type == "decorator":
                    text = child.text.decode('utf8')
                    if any(api_dec in text for api_dec in ['@app.', '@router.', '@api.']):
                        return True
            return False
        except Exception as e:
            self.logger.warning(f"Error checking API decorators: {e}")
            return False

    def _extract_base_classes(self, node: Node) -> List[str]:
        """Extract base classes from a class definition."""
        bases = []
        try:
            bases_node = node.child_by_field_name("bases")
            if bases_node:
                for base in bases_node.children:
                    if base.type == "identifier":
                        bases.append(base.text.decode('utf8'))
        except Exception as e:
            self.logger.warning(f"Error extracting base classes: {e}")
        return bases

    def _extract_entities(self, node: Node, chunk: str) -> Dict[str, List[BaseEntity]]:
        """Extract entities from a node."""
        # This is a placeholder - implement based on your BaseEntity structure
        return {'functions': [], 'classes': [], 'api_endpoints': []}

    def _extract_imports_chunk(self, node: Node) -> Optional[str]:
        """Extract all imports into a separate chunk."""
        import_lines = []

        def collect_imports(current_node: Node):
            try:
                if current_node.type in {"import_statement", "import_from_statement"}:
                    import_lines.append(current_node.text.decode('utf-8'))
                for child in current_node.children:
                    collect_imports(child)
            except Exception as e:
                self.logger.warning(f"Error collecting imports: {e}")

        try:
            collect_imports(node)
            return '\n'.join(import_lines) if import_lines else None
        except Exception as e:
            self.logger.error(f"Failed to extract imports: {e}")
            return None
    
    def merge_chunks(self, chunks: List[str], context: ChunkingContext) -> str:
        """
        Merge Python chunks while preserving validity.
        
        Args:
            chunks: List of code chunks
            context: ChunkingContext for tracking
            
        Returns:
            Merged Python code
        """
        try:
            # Get optimal chunk order based on dependencies
            chunk_order = context.get_dependency_order()
            ordered_chunks = []
            
            # Collect imports first
            import_chunks = []
            non_import_chunks = []
            
            for chunk in chunks:
                if chunk.strip().startswith(('import ', 'from ')):
                    import_chunks.append(chunk)
                else:
                    non_import_chunks.append(chunk)
            
            # Combine in proper order
            if import_chunks:
                ordered_chunks.append('\n'.join(import_chunks))
            ordered_chunks.extend(non_import_chunks)
            
            # Add proper spacing between chunks
            return '\n\n'.join(ordered_chunks)
            
        except Exception as e:
            self.logger.error(f"Failed to merge chunks: {e}")
            return '\n\n'.join(chunks)  # Fallback to simple joining
        
    def _is_processable_file(self, file_path: str, code: str) -> bool:
        """
        Check if a file should be processed.
        
        Args:
            file_path: Path to the file
            code: File content
            
        Returns:
            Boolean indicating if file should be processed
        """
        try:
            # Skip empty files
            if not code.strip():
                self.logger.info(f"Skipping empty file: {file_path}")
                return False
                
            # Special case for __init__.py
            if file_path.endswith('__init__.py') and not code.strip():
                self.logger.info("Skipping empty __init__.py file")
                return False
                
            # Skip files that are too small
            if len(code.splitlines()) < self.min_chunk_size:
                self.logger.info(f"File too small to chunk: {file_path}")
                return True  # Still process but might be single chunk
                
            return True
            
        except Exception as e:
            self.logger.warning(f"Error checking file processability: {e}")
            return False
                
    def create_chunks(self, code: str, file_path: str, context: ChunkingContext) -> List[str]:
        """Create chunks from Python code."""
        if not code or not file_path:
            self.logger.error("Code and file path must be provided")
            return []

        try:
            # Parse the code
            tree = self.parser.parse(bytes(code, 'utf8'))
            chunks = []

            # Extract imports first
            imports = self._extract_imports_chunk(tree.root_node)
            if imports:
                chunk_id = self._get_chunk_id_for_code(imports)
                context.add_chunk(chunk_id, imports)
                context.add_semantic_context(chunk_id, "Import statements")
                chunks.append(imports)

            # Process remaining code
            remaining_chunks = self._process_node(tree.root_node, context)
            chunks.extend(remaining_chunks)

            # Validate all chunks are in context
            valid_chunks = []
            for chunk in chunks:
                chunk_id = self._get_chunk_id_for_code(chunk)
                if chunk_id in context.chunks:
                    valid_chunks.append(chunk)
                else:
                    self.logger.warning(f"Chunk {chunk_id} not found in context, skipping")

            # Update metadata only for valid chunks
            self._update_chunks_metadata(valid_chunks, file_path, context)

            return valid_chunks

        except Exception as e:
            self.logger.error(f"Python chunking failed: {e}")
            return []
        
    def _update_chunks_metadata(self, chunks: List[str], file_path: str, context: ChunkingContext) -> None:
        """Update context with metadata for each chunk."""
        for chunk in chunks:
            try:
                # Generate chunk ID
                chunk_id = self._get_chunk_id_for_code(chunk)
                if not chunk_id:  # Add null check
                    continue
                
                # Ensure chunk is added to context before adding metadata
                if chunk_id not in context.chunks:
                    context.add_chunk(chunk_id, chunk)
                    
                # Parse chunk to extract metadata
                tree = self.parser.parse(bytes(chunk, 'utf8'))
                if not tree or not tree.root_node:  # Add null checks for tree and root_node
                    self.logger.warning(f"Failed to parse chunk: {chunk_id}")
                    continue
                deps = self._extract_dependencies(tree.root_node)
                
                # Create metadata
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    entities=self._extract_entities(tree.root_node, chunk),
                    dependencies=list(deps.function_calls | deps.class_refs),
                    imports=list(deps.imports),
                    api_components=self._has_api_components(tree.root_node),
                    async_code=self._has_async_code(tree.root_node),
                    type_dependencies=list(deps.class_refs)
                )
                
                # Update context
                context.add_chunk(chunk_id, chunk, metadata)
                
            except Exception as e:
                self.logger.warning(f"Failed to update metadata for chunk: {e}")
                continue
            
    def _has_api_components(self, node: Node) -> bool:
        """
        Check if node contains API components.
        
        Args:
            node: Tree-sitter node to check
            
        Returns:
            Boolean indicating if node contains API components
        """
        try:
            text = node.text.decode('utf8')
            return (
                '@app.route' in text or
                '@app.get' in text or
                '@app.post' in text or
                '@app.put' in text or
                '@app.delete' in text or
                '@router.' in text or
                'APIRouter' in text or
                'FastAPI' in text
            )
        except Exception as e:
            self.logger.warning(f"Error checking API components: {e}")
            return False

    def _has_async_code(self, node: Node) -> bool:
        """
        Check if node contains async code.
        
        Args:
            node: Tree-sitter node to check
            
        Returns:
            Boolean indicating if node contains async code
        """
        try:
            text = node.text.decode('utf8')
            return (
                'async ' in text or
                'await ' in text or
                'asyncio' in text or
                'aiohttp' in text
            )
        except Exception as e:
            self.logger.warning(f"Error checking async code: {e}")
            return False
                
    def _process_node(self, node: Node, context: ChunkingContext) -> List[str]:
        """Process a node and generate appropriate chunks with semantic context."""
        chunks = []
        current_chunk = []

        def add_chunk_to_context(content: str) -> None:
            """Helper to safely add chunk to context."""
            try:
                if content.strip():  # Only process non-empty chunks
                    chunk_id = self._get_chunk_id_for_code(content)
                    if chunk_id:
                        context.add_chunk(chunk_id, content)
                        # Add basic semantic context immediately
                        context.add_semantic_context(
                            chunk_id,
                            "Python code block"  # Default context, will be enriched later
                        )
            except Exception as e:
                self.logger.warning(f"Failed to add chunk to context: {e}")

        def should_start_new_chunk(current_node: Node) -> bool:
            return (
                self._is_significant_python_node(current_node) or
                self._is_complex_node(current_node)
            )

        def process_children(current_node: Node):
            for child in current_node.children:
                try:
                    if should_start_new_chunk(child):
                        # Handle current chunk if exists
                        if current_chunk:
                            chunk_content = '\n'.join(current_chunk)
                            add_chunk_to_context(chunk_content)
                            chunks.append(chunk_content)
                            current_chunk.clear()
                        
                        # Handle new chunk
                        chunk_content = child.text.decode('utf8')
                        add_chunk_to_context(chunk_content)
                        chunks.append(chunk_content)
                    else:
                        if child.text:
                            current_chunk.append(child.text.decode('utf8'))
                    
                    process_children(child)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing node: {e}")

        try:
            process_children(node)
            
            # Handle any remaining chunk
            if current_chunk:
                chunk_content = '\n'.join(current_chunk)
                add_chunk_to_context(chunk_content)
                chunks.append(chunk_content)
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Failed to process node: {e}")
            return []
        
    def _generate_semantic_context(self, node: Node) -> str:
        """Generate semantic description for a node."""
        try:
            node_type = node.type
            text = node.text.decode('utf8')
            
            if node_type == "class_definition":
                name_node = node.child_by_field_name("name")
                class_name = name_node.text.decode('utf8') if name_node else "Unknown"
                bases = self._extract_base_classes(node)
                base_desc = f" inheriting from {', '.join(bases)}" if bases else ""
                return f"This is a Python class named '{class_name}'{base_desc}"
                
            elif node_type in ["function_definition", "async_function_definition"]:
                name_node = node.child_by_field_name("name")
                func_name = name_node.text.decode('utf8') if name_node else "Unknown"
                is_async = "async" in node_type
                decorators = self._extract_decorators_text(node)
                dec_desc = f" with decorators: {decorators}" if decorators else ""
                async_desc = "async " if is_async else ""
                return f"This is a {async_desc}Python function named '{func_name}'{dec_desc}"
                
            elif self._has_api_decorators(node):
                route = self._extract_route_info(node)
                return f"This is a FastAPI endpoint {route}"
                
            elif "import" in node_type:
                return "This section contains Python import statements"
                
            return f"This is a Python code block containing {node_type.replace('_', ' ')}"
            
        except Exception as e:
            self.logger.warning(f"Error generating semantic context: {e}")
            return "This is a Python code block"

    def _extract_decorators_text(self, node: Node) -> str:
        """Extract decorator information as text."""
        decorators = []
        for child in node.children:
            if child.type == "decorator":
                decorators.append(child.text.decode('utf8').strip())
        return ', '.join(decorators)

    def _extract_route_info(self, node: Node) -> str:
        """Extract API route information."""
        for child in node.children:
            if child.type == "decorator":
                text = child.text.decode('utf8')
                if "@app." in text or "@router." in text:
                    method = next((m for m in ["get", "post", "put", "delete"] 
                                 if m in text.lower()), "")
                    if method:
                        path = text.split('("')[1].split('")')[0] if '("' in text else ""
                        return f"using {method.upper()} method at path {path}"
        return ""

    
    def _determine_code_type(self, node: Node) -> str:
        """Determine detailed Python code type."""
        try:
            if node.type == "class_definition":
                if self._is_pydantic_model(node):
                    return "pydantic_model"
                elif self._is_exception_class(node):
                    return "exception_class"
                elif self._is_test_class(node):
                    return "test_class"
                return "class_definition"
                
            elif node.type in ["function_definition", "async_function_definition"]:
                if self._has_api_decorators(node):
                    return "api_endpoint"
                elif self._is_test_function(node):
                    return "test_function"
                elif "async" in node.type:
                    return "async_function"
                return "function_definition"
                
            return "code_block"
            
        except Exception as e:
            self.logger.warning(f"Error determining code type: {e}")
            return "unknown"

    def _extract_language_features(self, node: Node) -> List[str]:
        """Extract Python language features used in the code."""
        features = set()
        
        def visit_node(current_node: Node):
            try:
                node_type = current_node.type
                if node_type == "await":
                    features.add("async_await")
                elif node_type == "with_statement":
                    features.add("context_manager")
                elif node_type == "list_comprehension":
                    features.add("list_comprehension")
                elif node_type == "generator_expression":
                    features.add("generator")
                elif node_type == "decorator":
                    features.add("decorator")
                elif node_type == "type_annotation":
                    features.add("type_hints")
                    
                for child in current_node.children:
                    visit_node(child)
                    
            except Exception:
                pass
        
        visit_node(node)
        return list(features)

    def _contains_tests(self, node: Node) -> bool:
        """Check if node contains test code."""
        text = node.text.decode('utf8')
        return any(marker in text for marker in [
            "pytest",
            "unittest",
            "test_",
            "@test",
            "assert"
        ])
        
    def _is_significant_python_node(self, node: Node) -> bool:
        """
        Determine if a Python node is significant for chunking.
        
        Args:
            node: Tree-sitter node to analyze
            
        Returns:
            Boolean indicating if node is significant
        """
        try:
            # Check node type
            significant_types = {
                'class_definition',
                'function_definition',
                'async_function_definition',
                'decorated_definition',
                'if_statement',
                'for_statement',
                'while_statement',
                'try_statement',
                'with_statement',
                'match_statement'  # Python 3.10+ pattern matching
            }
            
            if node.type in significant_types:
                return True
                
            # Check for decorators
            if node.children:
                for child in node.children:
                    if child.type == "decorator":
                        return True
                        
            # Check for significant size
            content = node.text.decode('utf-8')
            if content.count('\n') > self.min_chunk_size:
                return True
                
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking node significance: {e}")
            return False
            
    def _get_chunk_id_for_code(self, code: str) -> str:
        """
        Generate a unique ID for a code chunk.
        
        Args:
            code: The code content
            
        Returns:
            Unique chunk identifier
        """
        try:
            import hashlib
            # Create hash from content
            content_hash = hashlib.md5(code.encode('utf-8')).hexdigest()[:8]
            chunk_id = f"chunk_{content_hash}"
            if not chunk_id:
                raise ValueError("Empty chunk ID generated")
            return chunk_id
        except Exception as e:
            self.logger.error(f"Error generating chunk ID: {e}")
            # Fallback to simple counter if hashing fails
            self._chunk_counter = getattr(self, '_chunk_counter', 0) + 1
            return f"chunk_{self._chunk_counter}"