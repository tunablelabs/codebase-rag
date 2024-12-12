from typing import List, Dict, Optional, Any, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from tree_sitter import Node
import uuid
import re
import logging

from .schemas import (BaseEntity, Function, Class, APIEndpoint, APIRouter,
                     Decorator, Parameter, ReturnValue, ClassAttribute,
                     Location, ChunkMetadata, AccessLevel, TypeHint, TypeDefinition)

class CodeExtractor:
    """Extracts Python code entities with enhanced metadata support."""
    
    def __init__(self):
        self.tree: Optional[Node] = None
        self.source_lines: List[str] = []
        self.file_path: str = ""
        self._current_class_name: Optional[str] = None
        self._current_chunk_id: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Cache for extracted data
        self._docstring_cache: Dict[str, str] = {}
        self._type_hint_cache: Dict[str, TypeHint] = {}
        self._decorator_cache: Dict[str, List[Decorator]] = {}
    
    def set_source(self, source_code: str, file_path: str, chunk_id: Optional[str] = None) -> None:
        """Set source code and context for extraction."""
        self.source_lines = source_code.splitlines()
        self.file_path = file_path
        self._current_chunk_id = chunk_id
        
        # Clear caches on new source
        self._docstring_cache.clear()
        self._type_hint_cache.clear()
        self._decorator_cache.clear()
    
    def process_file(self, source_code: str, file_path: str, chunk_id: Optional[str] = None) -> Dict[str, List[Any]]:
        """Process Python source file with enhanced metadata."""
        try:
            self.set_source(source_code, file_path, chunk_id)
            
            results = {
                'functions': [],
                'classes': [],
                'api_endpoints': [],
                'api_routers': [],
                'context_managers': [],
                'exception_handlers': [],
                'custom_exceptions': [],
                'type_definitions': []  # New: Track type definitions
            }
            
            # Parse the code
            tree = self.parser.parse(bytes(source_code, 'utf8'))
            
            def process_node(node: Node):
                try:
                    if node.type == "function_definition":
                        func = self._extract_function(node)
                        results['functions'].append(func)
                        
                        # Check if it's also an API endpoint
                        endpoint = self._extract_api_endpoint(node, func)
                        if endpoint:
                            results['api_endpoints'].append(endpoint)
                            
                    elif node.type == "class_definition":
                        cls = self._extract_class(node)
                        results['classes'].append(cls)
                        
                        # Check for API router
                        router = self._extract_api_router(node, cls)
                        if router:
                            results['api_routers'].append(router)
                            
                        # Check for custom exception
                        if self._is_exception_class(node):
                            exception = self._extract_custom_exception(node, cls)
                            if exception:
                                results['custom_exceptions'].append(exception)
                                
                    elif node.type == "with_statement":
                        ctx_manager = self._extract_context_manager(node)
                        if ctx_manager:
                            results['context_managers'].append(ctx_manager)
                            
                    elif node.type == "try_statement":
                        handler = self._extract_exception_handler(node)
                        if handler:
                            results['exception_handlers'].append(handler)
                            
                    elif node.type == "type_definition":
                        type_def = self._extract_type_definition(node)
                        if type_def:
                            results['type_definitions'].append(type_def)
                            
                    for child in node.children:
                        process_node(child)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing node: {e}")
                    
            process_node(tree.root_node)
            
            # Enrich results with vector DB metadata
            self._enrich_results_for_vector_db(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            raise
    
    def _enrich_results_for_vector_db(self, results: Dict[str, List[Any]]) -> None:
        """Add vector DB specific metadata to extracted entities."""
        try:
            for entity_type, entities in results.items():
                for entity in entities:
                    if hasattr(entity, 'metadata'):
                        entity.metadata['vector_db'] = {
                            'semantic_context': self._generate_semantic_context(entity),
                            'code_type': self._determine_entity_type(entity),
                            'complexity': self._calculate_entity_complexity(entity),
                            'relationships': self._extract_entity_relationships(entity)
                        }
        except Exception as e:
            self.logger.warning(f"Error enriching results: {e}")
    
    def _generate_semantic_context(self, entity: Any) -> str:
        """Generate natural language description of entity."""
        try:
            if isinstance(entity, Function):
                return self._generate_function_context(entity)
            elif isinstance(entity, Class):
                return self._generate_class_context(entity)
            elif isinstance(entity, APIEndpoint):
                return self._generate_api_context(entity)
            else:
                return self._generate_generic_context(entity)
        except Exception as e:
            self.logger.warning(f"Error generating semantic context: {e}")
            return ""
    
    def _generate_function_context(self, func: Function) -> str:
        """Generate context for function entity."""
        parts = [f"This is a Python {'async ' if func.is_async else ''}function named '{func.name}'"]
        
        if func.decorators:
            dec_names = [d.name for d in func.decorators]
            parts.append(f"decorated with {', '.join(dec_names)}")
            
        if func.parameters:
            param_desc = [f"{p.name}: {p.type_hint or 'Any'}" for p in func.parameters]
            parts.append(f"It takes parameters: {', '.join(param_desc)}")
            
        if func.return_value.type_hint:
            parts.append(f"It returns {func.return_value.type_hint}")
            
        if func.docstring:
            parts.append(f"Documentation: {func.docstring}")
            
        return " ".join(parts)
    
    def _generate_class_context(self, cls: Class) -> str:
        """Generate context for class entity."""
        parts = [f"This is a Python class named '{cls.name}'"]
        
        if cls.base_classes:
            parts.append(f"inheriting from {', '.join(cls.base_classes)}")
            
        if cls.methods:
            method_names = [m.name for m in cls.methods]
            parts.append(f"It defines methods: {', '.join(method_names)}")
            
        if cls.attributes:
            attr_names = [a.name for a in cls.attributes]
            parts.append(f"It has attributes: {', '.join(attr_names)}")
            
        if cls.docstring:
            parts.append(f"Documentation: {cls.docstring}")
            
        return " ".join(parts)
    
    def _generate_api_context(self, api: APIEndpoint) -> str:
        """Generate context for API endpoint."""
        parts = [
            f"This is a {api.method} API endpoint at path '{api.path}'",
            f"handled by function '{api.handler.name}'"
        ]
        
        if api.query_params:
            params = [f"{k}: {v}" for k, v in api.query_params.items()]
            parts.append(f"It accepts query parameters: {', '.join(params)}")
            
        if api.request_body:
            parts.append(f"It expects request body of type {api.request_body}")
            
        if api.response_model:
            parts.append(f"It returns response of type {api.response_model}")
            
        return " ".join(parts)
    
    def _generate_generic_context(self, entity: Any) -> str:
        """Generate context for other entity types."""
        parts = [f"This is a {type(entity).__name__} named '{getattr(entity, 'name', 'unknown')}'"]
        
        if hasattr(entity, 'docstring') and entity.docstring:
            parts.append(f"Documentation: {entity.docstring}")
            
        return " ".join(parts)
    
    def _determine_entity_type(self, entity: Any) -> str:
        """Determine specific entity type for vector DB."""
        if isinstance(entity, Function):
            if entity.is_async:
                return "async_function"
            elif entity.is_property:
                return "property"
            elif entity.is_classmethod:
                return "classmethod"
            elif entity.is_staticmethod:
                return "staticmethod"
            return "function"
        elif isinstance(entity, Class):
            if any('Exception' in base for base in entity.base_classes):
                return "exception_class"
            elif any('APIRouter' in base for base in entity.base_classes):
                return "api_router"
            return "class"
        elif isinstance(entity, APIEndpoint):
            return "api_endpoint"
        return type(entity).__name__.lower()
    
    def _calculate_entity_complexity(self, entity: Any) -> int:
        """Calculate complexity score for entity."""
        try:
            if isinstance(entity, Function):
                return self._calculate_function_complexity(entity)
            elif isinstance(entity, Class):
                return self._calculate_class_complexity(entity)
            return 1
        except Exception as e:
            self.logger.warning(f"Error calculating complexity: {e}")
            return 1
    
    def _extract_entity_relationships(self, entity: Any) -> Dict[str, List[str]]:
        """Extract relationship information for entity."""
        relationships = {
            'depends_on': [],
            'used_by': [],
            'inherits_from': [],
            'implements': []
        }
        
        try:
            if isinstance(entity, Function):
                relationships['depends_on'] = list(entity.called_functions)
            elif isinstance(entity, Class):
                relationships['inherits_from'] = entity.base_classes
                relationships['implements'] = entity.interfaces
            elif isinstance(entity, APIEndpoint):
                relationships['depends_on'] = [entity.handler.name]
                
        except Exception as e:
            self.logger.warning(f"Error extracting relationships: {e}")
            
        return relationships

    def _extract_type_definition(self, node: Node) -> Optional[TypeDefinition]:
        """Extract type definition information."""
        try:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return None
                
            return TypeDefinition(
                id=str(uuid.uuid4()),
                name=name_node.text.decode('utf8'),
                location=self._get_location(node),
                type_hint=self._extract_type_hint(node),
                docstring=self._extract_docstring(node),
                chunk_id=self._current_chunk_id
            )
        except Exception as e:
            self.logger.warning(f"Error extracting type definition: {e}")
            return None