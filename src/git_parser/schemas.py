from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Set
from datetime import datetime
from enum import Enum
from pathlib import Path

class AccessLevel(Enum):
    PUBLIC = "public"
    PROTECTED = "_protected"
    PRIVATE = "__private"

@dataclass
class Location:
    """Physical location information for code entities"""
    file_path: str
    start_line: int
    end_line: int
    start_column: Optional[int] = None
    end_column: Optional[int] = None
    chunk_id: Optional[str] = None  # Added to track chunk association

@dataclass
class BaseEntity:
    """Base class for all code entities"""
    id: str
    name: str
    location: Location
    docstring: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    chunk_id: Optional[str] = None  # Added for chunk tracking
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChunkMetadata:
    """Extended metadata for code chunks"""
    chunk_id: str
    entities: Dict[str, List[BaseEntity]] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    api_components: bool = False
    async_code: bool = False
    type_dependencies: List[str] = field(default_factory=list)
    size: int = 0  # Size in bytes
    complexity: int = 0  # Cyclomatic complexity
    lines: int = 0  # Number of lines
    parent_chunk: Optional[str] = None  # For nested chunks
    is_complete: bool = True  # Whether chunk represents complete construct

@dataclass
class Decorator(BaseEntity):
    """Represents a Python decorator"""
    arguments: List[str] = field(default_factory=list)
    keywords: Dict[str, Any] = field(default_factory=dict)
    target_type: str = ""  # 'function', 'class', etc.

@dataclass
class Parameter:
    """Function or method parameter"""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = True
    is_keyword_only: bool = False
    is_positional_only: bool = False
    is_variadic: bool = False

@dataclass
class ReturnValue:
    """Function return value information"""
    type_hint: Optional[str] = None
    is_generator: bool = False
    is_coroutine: bool = False
    possible_values: List[str] = field(default_factory=list)

@dataclass
class Function(BaseEntity):
    """Represents a function or method"""
    parameters: List[Parameter] = field(default_factory=list)
    return_value: ReturnValue = field(default_factory=ReturnValue)
    decorators: List[Decorator] = field(default_factory=list)
    is_async: bool = False
    is_generator: bool = False
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    complexity: int = 0
    called_functions: Set[str] = field(default_factory=set)
    raises: Set[str] = field(default_factory=set)
    variables: List[str] = field(default_factory=list)
    body: str = ""
    dependencies: List[str] = field(default_factory=list)
    chunk_info: Optional[ChunkMetadata] = None  # Added for chunk association

@dataclass
class ClassAttribute:
    """Class attribute/property"""
    name: str
    type_hint: Optional[str] = None
    default_value: Optional[str] = None
    access_level: AccessLevel = AccessLevel.PUBLIC
    is_class_var: bool = False

@dataclass
class Class(BaseEntity):
    """Represents a class definition"""
    methods: List[Function] = field(default_factory=list)
    attributes: List[ClassAttribute] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)
    decorators: List[Decorator] = field(default_factory=list)
    inner_classes: List['Class'] = field(default_factory=list)
    metaclass: Optional[str] = None
    abstract_methods: Set[str] = field(default_factory=set)
    class_methods: Set[str] = field(default_factory=set)
    static_methods: Set[str] = field(default_factory=set)
    properties: Set[str] = field(default_factory=set)
    interfaces: List[str] = field(default_factory=list)
    mixin_classes: List[str] = field(default_factory=list)
    chunk_info: Optional[ChunkMetadata] = None  # Added for chunk association

@dataclass
class APIEndpoint(BaseEntity):
    """Represents an API endpoint"""
    path: str = ""
    method: str = "GET"
    handler: Function = field(default_factory=Function)
    parameters: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    path_params: Dict[str, str] = field(default_factory=dict)
    request_body: Optional[str] = None
    response_model: Optional[str] = None
    status_codes: List[int] = field(default_factory=list)
    middleware: List[str] = field(default_factory=list)
    authentication: Optional[str] = None
    rate_limit: Optional[Dict] = None
    cors_settings: Optional[Dict] = None
    chunk_info: Optional[ChunkMetadata] = None  # Added for chunk association

@dataclass
class APIRouter(BaseEntity):
    """Represents an API router"""
    prefix: str = ""
    endpoints: List[APIEndpoint] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    middleware: List[str] = field(default_factory=list)
    chunk_info: Optional[ChunkMetadata] = None  # Added for chunk association

@dataclass
class DependencyNode:
    """Node in the dependency graph"""
    id: str
    name: str
    type: str
    path: str
    chunk_id: Optional[str] = None  # Added for chunk tracking
    entity: Optional[BaseEntity] = None

@dataclass
class DependencyEdge:
    """Edge in the dependency graph"""
    source_id: str
    target_id: str
    type: str
    weight: float = 1.0
    chunk_relation: bool = False  # Added to indicate chunk-level dependency

@dataclass
class ChunkRelationship:
    """Represents relationships between chunks"""
    source_chunk_id: str
    target_chunk_id: str
    relationship_type: str  # 'imports', 'calls', 'inherits', etc.
    entities_involved: List[str] = field(default_factory=list)
    strength: float = 1.0  # Relationship strength/weight
    
@dataclass
class TypeHint:
    """Represents a Python type hint."""
    id: str
    name: str
    original_type: str = ""
    is_optional: bool = False
    is_union: bool = False
    is_literal: bool = False
    is_generic: bool = False
    union_types: Optional[List[str]] = None
    generic_params: Optional[List[str]] = None
    constraints: Optional[Dict[str, str]] = None

@dataclass
class TypeDefinition:
    """Represents a type definition or alias."""
    id: str
    name: str
    location: Location
    type_hint: Optional[TypeHint] = None
    docstring: Optional[str] = None
    is_public: bool = True
    chunk_id: Optional[str] = None