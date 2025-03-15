from typing import Any, Dict, List
from ..base_types import BaseLanguageParser, CodeEntity, CodeLocation, StringLiteral
# Import direct logging functions
from config.logging_config import info, error, warning, debug

class JavaScriptParser(BaseLanguageParser):
    def get_language_name(self) -> str:
        return "javascript"

    def parse(self, content: bytes) -> Any:
        """Parse code content using tree-sitter"""
        return self.parser.parse(content)

    def parse_file(self, file_path: str) -> List[CodeEntity]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.code = content 
            tree = self.parse(bytes(content, 'utf-8'))
            entities = self.extract_entities(tree.root_node)
            return entities
        except Exception as e:
            # Replace self.logger.error with direct error function
            error(f"Error parsing JavaScript file {file_path}: {e}")
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
            # Function-related
            'function': [
                'function_declaration',
                'arrow_function',
                'function_expression',
                'generator_function_declaration',
                'async_function_declaration',
                'async_function_expression',
                'method_definition'
            ],
            
            # Class-related
            'class': [
                'class_declaration',
                'class_expression'
            ],
            
            # Method-related
            'method': [
                'method_definition',
                'generator_method',
                'async_method',
                'getter',
                'setter'
            ],
            
            # Variable declarations
            'variable': [
                'variable_declaration',
                'variable_declarator',
                'const_declaration',
                'let_declaration'
            ],
            
            # Object-related
            'object': [
                'object',
                'object_pattern',
                'object_expression'
            ],
            
            # Property-related
            'property': [
                'property_identifier',
                'property',
                'shorthand_property_identifier',
                'computed_property_name'
            ],
            
            # Import/Export
            'import': [
                'import_declaration',
                'import_specifier',
                'import_clause'
            ],
            'export': [
                'export_statement',
                'export_clause'
            ],
            
            # Array-related
            'array': [
                'array_pattern',
                'array'
            ],
            
            # Control structures
            'loop': [
                'for_statement',
                'for_in_statement',
                'for_of_statement',
                'while_statement',
                'do_statement'
            ],
            
            # Promises and async
            'promise': [
                'await_expression',
                'yield_expression'
            ],
            
            # Misc
            'literal': [
                'string',
                'template_string',
                'number',
                'regex',
                'boolean',
                'null'
            ]
        }

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        metadata = {
            # Function attributes
            'is_async': False,
            'is_generator': False,
            'is_arrow': False,
            
            # Export attributes
            'is_export': False,
            'is_default_export': False,
            
            # Method attributes
            'is_getter': False,
            'is_setter': False,
            'is_constructor': False,
            'is_static': False,
            
            # Variable attributes
            'is_const': False,
            'is_let': False,
            'is_var': False,
            
            # Additional metadata
            'decorators': [],
            'parameters': [],
            'super_class': None,
            'computed': False
        }
        
        try:
            # Check node type specifics
            metadata.update({
                'is_async': 'async' in node.type or any(child.type == 'async' for child in node.children),
                'is_generator': 'generator' in node.type or any(child.type == '*' for child in node.children),
                'is_arrow': node.type == 'arrow_function',
                'is_getter': node.type == 'getter' or any(child.type == 'get' for child in node.children),
                'is_setter': node.type == 'setter' or any(child.type == 'set' for child in node.children),
                'is_constructor': node.type == 'method_definition' and any(
                    child.type == 'property_identifier' and child.text.decode('utf-8') == 'constructor'
                    for child in node.children
                ),
                'is_static': any(child.type == 'static' for child in node.children),
                'computed': any(child.type == 'computed_property_name' for child in node.children)
            })
            
            # Variable declaration type
            if node.type == 'variable_declaration':
                kind = next((child.type for child in node.children if child.type in ['const', 'let', 'var']), None)
                if kind:
                    metadata[f'is_{kind}'] = True
            
            # Check for exports
            parent = node.parent
            while parent:
                if parent.type == 'export_statement':
                    metadata['is_export'] = True
                    metadata['is_default_export'] = any(
                        child.type == 'default' for child in parent.children
                    )
                    break
                parent = parent.parent
            
            # Extract parameters for functions
            params = self.get_child_by_field_name(node, "parameters")
            if params:
                metadata['parameters'] = [
                    param.text.decode('utf-8')
                    for param in params.children
                    if param.type == "identifier"
                ]
            
            # Extract super class for class declarations
            super_class = self.get_child_by_field_name(node, "super_class")
            if super_class:
                metadata['super_class'] = super_class.text.decode('utf-8')
                
            return metadata
                
        except Exception as e:
            # Replace self.logger.warning with direct warning function
            warning(f"Error extracting metadata: {e}")
            return metadata

    def get_child_by_field_name(self, node: Any, field_name: str) -> Any:
        for child in node.children:
            if child.type == field_name:
                return child
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