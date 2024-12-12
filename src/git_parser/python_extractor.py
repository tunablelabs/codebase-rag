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
        
    def _extract_function(self, node: Node) -> Optional[Function]:
        """Extract function definition details."""
        try:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return None
                
            func = Function(
                id=str(uuid.uuid4()),
                name=name_node.text.decode('utf8'),
                location=self._get_location(node),
                docstring=self._extract_docstring(node),
                is_async='async' in node.type,
                decorators=self._extract_decorators(node),
                parameters=self._extract_parameters(node),
                return_value=self._extract_return_value(node),
                body=self._get_node_text(node),
                chunk_id=self._current_chunk_id
            )
            return func
        except Exception as e:
            self.logger.warning(f"Error extracting function: {e}")
            return None
    
    def _get_location(self, node: Node) -> Location:
        """Get source location information for a node."""
        return Location(
            file_path=self.file_path,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            start_column=node.start_point[1],
            end_column=node.end_point[1],
            chunk_id=self._current_chunk_id
        )

    def _extract_docstring(self, node: Node) -> Optional[str]:
        """Extract docstring from a node."""
        try:
            for child in node.children:
                if child.type == "expression_statement":
                    string_node = child.children[0]
                    if string_node.type in ("string", "string_content"):
                        return string_node.text.decode('utf8').strip('"\' \n\t')
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting docstring: {e}")
            return None

    def _extract_decorators(self, node: Node) -> List[Decorator]:
        """Extract decorators from a node."""
        decorators = []
        try:
            for child in node.children:
                if child.type == "decorator":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        decorator = Decorator(
                            id=str(uuid.uuid4()),
                            name=name_node.text.decode('utf8'),
                            location=self._get_location(child),
                            target_type=node.type
                        )
                        decorators.append(decorator)
            return decorators
        except Exception as e:
            self.logger.warning(f"Error extracting decorators: {e}")
            return []

    def _extract_parameters(self, node: Node) -> List[Parameter]:
        """Extract function parameters."""
        parameters = []
        try:
            params_node = node.child_by_field_name("parameters")
            if not params_node:
                return parameters

            for param_node in params_node.children:
                if param_node.type == "identifier":
                    param = Parameter(
                        name=param_node.text.decode('utf8'),
                        type_hint=self._extract_type_hint_from_param(param_node)
                    )
                    parameters.append(param)
                elif param_node.type == "typed_parameter":
                    name_node = param_node.child_by_field_name("name")
                    if name_node:
                        param = Parameter(
                            name=name_node.text.decode('utf8'),
                            type_hint=self._extract_type_hint_from_param(param_node),
                            default_value=self._extract_default_value(param_node)
                        )
                        parameters.append(param)

            return parameters
        except Exception as e:
            self.logger.warning(f"Error extracting parameters: {e}")
            return []

    def _extract_type_hint_from_param(self, node: Node) -> Optional[str]:
        """Extract type hint from a parameter node."""
        try:
            type_node = node.child_by_field_name("type")
            if type_node:
                return type_node.text.decode('utf8')
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting type hint: {e}")
            return None

    def _extract_default_value(self, node: Node) -> Optional[str]:
        """Extract default value from a parameter node."""
        try:
            default_node = node.child_by_field_name("default")
            if default_node:
                return default_node.text.decode('utf8')
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting default value: {e}")
            return None

    def _extract_return_value(self, node: Node) -> ReturnValue:
        """Extract function return value information."""
        try:
            return_node = node.child_by_field_name("return_type")
            return ReturnValue(
                type_hint=return_node.text.decode('utf8') if return_node else None,
                is_generator='yield' in self._get_node_text(node),
                is_coroutine='async' in node.type
            )
        except Exception as e:
            self.logger.warning(f"Error extracting return value: {e}")
            return ReturnValue()

    def _get_node_text(self, node: Node) -> str:
        """Get text content of a node."""
        try:
            return node.text.decode('utf8')
        except Exception as e:
            self.logger.warning(f"Error getting node text: {e}")
            return ""
        
    def _extract_class(self, node: Node) -> Optional[Class]:
        """Extract class definition details."""
        try:
            name_node = node.child_by_field_name("name")
            if not name_node:
                return None

            self._current_class_name = name_node.text.decode('utf8')
            
            cls = Class(
                id=str(uuid.uuid4()),
                name=self._current_class_name,
                location=self._get_location(node),
                docstring=self._extract_docstring(node),
                methods=self._extract_methods(node),
                attributes=self._extract_attributes(node),
                base_classes=self._extract_base_classes(node),
                decorators=self._extract_decorators(node),
                chunk_id=self._current_chunk_id
            )
            
            self._current_class_name = None
            return cls
        except Exception as e:
            self.logger.warning(f"Error extracting class: {e}")
            self._current_class_name = None
            return None

    def _extract_methods(self, node: Node) -> List[Function]:
        """Extract class methods."""
        methods = []
        try:
            for child in node.children:
                if child.type == "function_definition":
                    method = self._extract_function(child)
                    if method:
                        methods.append(method)
            return methods
        except Exception as e:
            self.logger.warning(f"Error extracting methods: {e}")
            return []

    def _extract_attributes(self, node: Node) -> List[ClassAttribute]:
        """Extract class attributes."""
        attributes = []
        try:
            for child in node.children:
                if child.type == "expression_statement":
                    attr = self._extract_attribute(child)
                    if attr:
                        attributes.append(attr)
            return attributes
        except Exception as e:
            self.logger.warning(f"Error extracting attributes: {e}")
            return []

    def _extract_attribute(self, node: Node) -> Optional[ClassAttribute]:
        """Extract a single class attribute."""
        try:
            name_node = node.child_by_field_name("name")
            if name_node:
                return ClassAttribute(
                    name=name_node.text.decode('utf8'),
                    type_hint=self._extract_type_hint_from_attr(node),
                    default_value=self._extract_default_value(node),
                    access_level=self._determine_access_level(name_node.text.decode('utf8'))
                )
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting attribute: {e}")
            return None

    def _extract_base_classes(self, node: Node) -> List[str]:
        """Extract base classes."""
        bases = []
        try:
            bases_node = node.child_by_field_name("bases")
            if bases_node:
                for base in bases_node.children:
                    if base.type == "identifier":
                        bases.append(base.text.decode('utf8'))
            return bases
        except Exception as e:
            self.logger.warning(f"Error extracting base classes: {e}")
            return []

    def _determine_access_level(self, name: str) -> AccessLevel:
        """Determine access level from name."""
        if name.startswith('__'):
            return AccessLevel.PRIVATE
        elif name.startswith('_'):
            return AccessLevel.PROTECTED
        return AccessLevel.PUBLIC
    
    def _extract_api_endpoint(self, node: Node, func: Function) -> Optional[APIEndpoint]:
        """Extract API endpoint information."""
        try:
            for decorator in func.decorators:
                if any(http_method in decorator.name.lower() for http_method in ['get', 'post', 'put', 'delete']):
                    return APIEndpoint(
                        id=str(uuid.uuid4()),
                        name=func.name,
                        path=self._extract_path_from_decorator(decorator),
                        method=self._extract_http_method(decorator),
                        handler=func,
                        location=func.location,
                        chunk_id=self._current_chunk_id
                    )
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting API endpoint: {e}")
            return None

    def _extract_api_router(self, node: Node, cls: Class) -> Optional[APIRouter]:
        """Extract API router information."""
        try:
            if any('APIRouter' in base for base in cls.base_classes):
                return APIRouter(
                    id=str(uuid.uuid4()),
                    name=cls.name,
                    prefix=self._extract_router_prefix(cls),
                    location=cls.location,
                    chunk_id=self._current_chunk_id
                )
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting API router: {e}")
            return None

    def _extract_path_from_decorator(self, decorator: Decorator) -> str:
        """Extract path from API decorator."""
        try:
            if decorator.arguments:
                return decorator.arguments[0].strip('"\'')
            return ""
        except Exception as e:
            self.logger.warning(f"Error extracting path: {e}")
            return ""

    def _extract_http_method(self, decorator: Decorator) -> str:
        """Extract HTTP method from decorator."""
        try:
            method = decorator.name.upper()
            if any(http_method in method for http_method in ['GET', 'POST', 'PUT', 'DELETE']):
                return method
            return "GET"
        except Exception as e:
            self.logger.warning(f"Error extracting HTTP method: {e}")
            return "GET"

    def _extract_router_prefix(self, cls: Class) -> str:
        """Extract router prefix."""
        try:
            for decorator in cls.decorators:
                if 'prefix' in decorator.keywords:
                    return decorator.keywords['prefix']
            return ""
        except Exception as e:
            self.logger.warning(f"Error extracting router prefix: {e}")
            return ""