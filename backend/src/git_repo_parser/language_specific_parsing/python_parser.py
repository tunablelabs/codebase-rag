from typing import Any, Dict, List, Tuple
from ..base_types import BaseLanguageParser, CodeEntity, CodeLocation, StringLiteral
from tree_sitter import Node
# Import direct logging functions
from config.logging_config import info, error, warning, debug


class PythonParser(BaseLanguageParser):
    def get_language_name(self) -> str:
        return "python"
    
    def parse(self, content: bytes) -> Node:
        """Parse code content using tree-sitter"""
        return self.parser.parse(content)

    def parse_file(self, file_path: str) -> List[CodeEntity]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.code = content 
            tree = self.parser.parse(bytes(content, 'utf-8'))
            entities = self.extract_entities(tree.root_node)
            return entities
        except Exception as e:
            # Replace self.logger.error with direct error function
            error(f"Error parsing Python file {file_path}: {e}")
            return []

    def extract_entities(self, node: Any) -> List[CodeEntity]:
        entities = []
        for pattern, node_types in self.get_entity_patterns().items():
            if not isinstance(node_types, list):
                node_types = [node_types]
            for entity_node in node.children:
                if entity_node.type in node_types:
                    name_node = self.get_child_by_field_name(entity_node, "name")
                    name = name_node.text.decode("utf-8") if name_node else ""
                    metadata = self.extract_metadata(entity_node)
                    start_byte = entity_node.start_byte
                    end_byte = entity_node.end_byte
                    content = self.code[start_byte:end_byte]
                    entities.append(CodeEntity(
                        name=name,
                        type=pattern,
                        content=content,
                        metadata=metadata,
                        location=self.create_code_location(entity_node),
                        language=self.get_language_name()
                    ))
                    
                    # Recursively process children for nested entities
                    entities.extend(self.extract_entities(entity_node))
        return entities

    def get_entity_patterns(self) -> Dict[str, Any]:
        return {
            # Function-related patterns
            'function': [
                'function_definition',
                'async_function_definition',
                'lambda'
            ],
            
            # Class-related patterns
            'class': [
                'class_definition',
                'dataclass_definition'  # For @dataclass
            ],
            
            # Method patterns (including special methods)
            'method': [
                'function_definition',
                'async_function_definition'
            ],
            
            # Variable declarations
            'variable': [
                'assignment',
                'annotated_assignment',
                'global_statement',
                'nonlocal_statement'
            ],
            
            # Import statements
            'import': [
                'import_statement',
                'import_from_statement',
                'aliased_import'
            ],
            
            # Decorators
            'decorator': [
                'decorator',
                'decorated_definition'
            ],
            
            # Type definitions
            'type': [
                'type_alias_statement',
                'type_parameter',
                'type_annotation'
            ],
            
            # Exception handling
            'exception': [
                'try_statement',
                'except_clause',
                'raise_statement',
                'finally_clause'
            ],
            
            # Context managers
            'context_manager': [
                'with_statement',
                'async_with_statement'
            ],
            
            # Comprehensions and generators
            'comprehension': [
                'list_comprehension',
                'dictionary_comprehension',
                'set_comprehension',
                'generator_expression'
            ],
            
            # Control flow
            'control_flow': [
                'if_statement',
                'for_statement',
                'while_statement',
                'async_for_statement',
                'break_statement',
                'continue_statement',
                'match_statement',  # Python 3.10+
                'case_clause'
            ],
            
            # OOP specific
            'property': [
                'property_decorator',
                'class_variable',
                'instance_variable'
            ],
            
            # Documentation
            'docstring': [
                'expression_statement'  # Will filter for string literals in metadata
            ],
            
            # Constants
            'constant': [
                'constant_definition',
                'enum_definition'  # For Enum classes
            ]
        }

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        metadata = {
            # Function/Method attributes
            'is_async': False,
            'is_generator': False,
            'is_lambda': False,
            'is_method': False,
            'is_class_method': False,
            'is_static_method': False,
            'is_property': False,
            'is_abstract': False,
            
            # Class attributes
            'is_dataclass': False,
            'bases': [],
            'metaclass': None,
            
            # Variable attributes
            'is_class_var': False,
            'is_type_annotated': False,
            'type_annotation': None,
            'is_final': False,
            
            # Documentation
            'docstring': None,
            'decorators': [],
            
            # Function/Method specifics
            'parameters': [],
            'return_annotation': None,
            'yields': False,
            'awaits': False,
            
            # Import specifics
            'is_relative_import': False,
            'import_level': 0,
            'aliases': {},
            
            # Context
            'is_nested': False,
            'parent_type': None
        }
        
        try:
            # Basic type checks
            metadata.update({
                'is_async': 'async' in node.type,
                'is_lambda': node.type == 'lambda',
                'is_generator': any(child.type == 'yield_expression' for child in node.children),
            })
            
            # Process decorators
            decorators = []
            for child in node.children:
                if child.type == 'decorator':
                    decorator_text = self.code[child.start_byte:child.end_byte].strip('@')
                    decorators.append(decorator_text)
                    
                    # Check for special decorators
                    if decorator_text in ['classmethod', 'staticmethod', 'property', 'abstractmethod']:
                        metadata[f'is_{decorator_text}'] = True
                    elif decorator_text == 'dataclass':
                        metadata['is_dataclass'] = True
                    elif decorator_text == 'final':
                        metadata['is_final'] = True
                        
            metadata['decorators'] = decorators
            
            # Extract parameters for functions/methods
            if node.type in ['function_definition', 'async_function_definition']:
                parameters = self.get_child_by_field_name(node, "parameters")
                if parameters:
                    metadata['parameters'] = [
                        param.text.decode('utf-8')
                        for param in parameters.children
                        if param.type == "identifier"
                    ]
                    
                    # Check if it's a method by looking for 'self' or 'cls'
                    if metadata['parameters'] and metadata['parameters'][0] in ['self', 'cls']:
                        metadata['is_method'] = True
            
            # Extract type annotations
            type_annotation = self.get_child_by_field_name(node, "annotation")
            if type_annotation:
                metadata['is_type_annotated'] = True
                metadata['type_annotation'] = type_annotation.text.decode('utf-8')
            
            # Extract return annotation
            return_annotation = self.get_child_by_field_name(node, "return_annotation")
            if return_annotation:
                metadata['return_annotation'] = return_annotation.text.decode('utf-8')
            
            # Extract class bases
            if node.type == 'class_definition':
                bases = self.get_child_by_field_name(node, "bases")
                if bases:
                    metadata['bases'] = [
                        base.text.decode('utf-8')
                        for base in bases.children
                        if base.type == "identifier"
                    ]
            
            # Check for docstring
            for child in node.children:
                if child.type == 'expression_statement':
                    string_child = child.children[0] if child.children else None
                    if string_child and string_child.type in ('string', 'string_content'):
                        metadata['docstring'] = string_child.text.decode('utf-8').strip('"\' \n\t')
                        break
            
            # Check for nested definition
            parent = node.parent
            if parent and parent.type in ['class_definition', 'function_definition']:
                metadata['is_nested'] = True
                metadata['parent_type'] = parent.type
            
            # Import specific metadata
            if node.type in ['import_from_statement', 'import_statement']:
                metadata['is_relative_import'] = any(child.type == 'relative_import' for child in node.children)
                if metadata['is_relative_import']:
                    metadata['import_level'] = len([c for c in node.children if c.type == '.'])
            
            return metadata
            
        except Exception as e:
            # Replace self.logger.warning with direct warning function
            warning(f"Error extracting metadata: {e}")
            return metadata

    def get_child_by_field_name(self, node: Any, field_name: str) -> Any:
        try:
            # Try direct field access first
            result = node.child_by_field_name(field_name)
            if result:
                return result
            
            # Fallback to type matching
            for child in node.children:
                if child.type == field_name:
                    return child
            return None
            
        except Exception:
            return None

    def create_code_location(self, node: Any) -> CodeLocation:
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        return CodeLocation(
            start_line=start_line,
            start_col=start_col,
            end_line=end_line,
            end_col=end_col
        )