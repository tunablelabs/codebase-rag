from typing import Any, Dict, List
from ..base_types import BaseLanguageParser, CodeEntity, CodeLocation

class TypeScriptParser(BaseLanguageParser):
    def get_language_name(self) -> str:
        return "typescript"

    def parse(self, content: bytes) -> Any:
        """Parse code content using tree-sitter"""
        return self.parser.parse(content)

    def get_entity_patterns(self) -> Dict[str, Any]:
        """Required method from BaseLanguageParser"""
        return {
            # Class-related
            'class': [
                'class_declaration',
                'abstract_class_declaration',
                'export_default_declaration',
                'class_expression'
            ],
            
            # Function-related
            'function': [
                'function_declaration',
                'arrow_function',
                'function_expression',
                'generator_function_declaration',
                'async_function_declaration',
                'method_signature',
                'function_signature'
            ],
            
            # Method-related
            'method': [
                'method_definition',
                'constructor_declaration',
                'get_accessor',
                'set_accessor'
            ],
            
            # Property-related
            'property': [
                'property_definition',
                'public_field_definition',
                'private_field_definition',
                'property_signature',
                'property_declaration',
                'property_identifier',
                'index_signature'
            ],
            
            # Interface & Types
            'interface': ['interface_declaration'],
            'type': [
                'type_alias_declaration',
                'type_parameter',
                'mapped_type'
            ],
            
            # Variables
            'variable': [
                'variable_declaration',
                'const_declaration',
                'let_declaration'
            ],
            
            # Modules & Namespaces
            'module': ['module_declaration'],
            'namespace': ['namespace_declaration'],
            
            # Enums
            'enum': [
                'enum_declaration',
                'const_enum_declaration'
            ],
            'enum_member': ['enum_member'],
            
            # Decorators
            'decorator': ['decorator', 'decorator_factory'],
            
            # Import/Export
            'import': [
                'import_declaration',
                'import_require_clause'
            ],
            'export': [
                'export_declaration',
                'export_assignment'
            ]
        }

    def parse_file(self, file_path: str) -> List[CodeEntity]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.code = content 
            tree = self.parse(bytes(content, 'utf-8'))
            entities = []
            if tree and tree.root_node:
                entities = self.extract_entities(tree.root_node)
            return entities
        except Exception as e:
            self.logger.error(f"Error parsing TypeScript file {file_path}: {e}")
            return []

    def extract_entities(self, node: Any) -> List[CodeEntity]:
        entities = []
        
        # Process current node if it matches any patterns
        for pattern, node_types in self.get_entity_patterns().items():
            if not isinstance(node_types, list):
                node_types = [node_types]
                
            if node.type in node_types:
                name = self._extract_name(node)
                if name:
                    metadata = self.extract_metadata(node)
                    content = self.code[node.start_byte:node.end_byte]
                    entities.append(CodeEntity(
                        name=name,
                        type=pattern,
                        content=content,
                        metadata=metadata,
                        location=self.create_code_location(node),
                        language=self.get_language_name()
                    ))
        
        # Process children recursively
        for child in node.children:
            entities.extend(self.extract_entities(child))
            
        return entities

    def _extract_name(self, node: Any) -> str:
        """Extract name from any type of node"""
        try:
            # For export default declaration, look for the class/function name
            if node.type == 'export_default_declaration':
                for child in node.children:
                    if child.type in ['class_declaration', 'function_declaration']:
                        name_node = self.get_child_by_field_name(child, "name")
                        if name_node:
                            return name_node.text.decode('utf-8')
            
            # Direct name field
            name_node = self.get_child_by_field_name(node, "name")
            if name_node:
                return name_node.text.decode('utf-8')
            
            # Property and method identifiers
            if node.type in ['property_definition', 'public_field_definition', 'private_field_definition', 
                           'method_definition', 'property_identifier']:
                for child in node.children:
                    if child.type in ['property_identifier', 'identifier']:
                        return child.text.decode('utf-8')
            
            # Variable declarations
            if node.type in ['variable_declaration', 'const_declaration', 'let_declaration']:
                declarator = self.get_child_by_field_name(node, "declarator")
                if declarator:
                    name_node = self.get_child_by_field_name(declarator, "name")
                    if name_node:
                        return name_node.text.decode('utf-8')
            
            return ""
            
        except Exception as e:
            self.logger.warning(f"Error extracting name from {node.type}: {e}")
            return ""

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        """Extract comprehensive metadata from node"""
        metadata = {
            'is_export': False,
            'is_default_export': False,
            'is_static': False,
            'is_private': False,
            'is_public': False,
            'is_protected': False,
            'is_readonly': False,
            'is_async': False,
            'is_abstract': False,
            'is_constructor': node.type == 'constructor_declaration',
            'decorators': [],
            'modifiers': [],
            'type_parameters': [],
            'return_type': None
        }

        try:
            # Check export status
            current = node
            while current:
                if current.type == 'export_default_declaration':
                    metadata['is_export'] = True
                    metadata['is_default_export'] = True
                    break
                elif current.type == 'export_statement':
                    metadata['is_export'] = True
                    break
                current = current.parent

            # Process children for modifiers and info
            for child in node.children:
                if child.type == 'decorator':
                    metadata['decorators'].append(self.code[child.start_byte:child.end_byte])
                elif child.type in ['public', 'private', 'protected', 'static', 'readonly', 'abstract', 'async']:
                    metadata['modifiers'].append(child.type)
                    if child.type == 'private':
                        metadata['is_private'] = True
                    elif child.type == 'public':
                        metadata['is_public'] = True
                    elif child.type == 'protected':
                        metadata['is_protected'] = True
                    elif child.type == 'static':
                        metadata['is_static'] = True
                    elif child.type == 'readonly':
                        metadata['is_readonly'] = True
                    elif child.type == 'abstract':
                        metadata['is_abstract'] = True
                    elif child.type == 'async':
                        metadata['is_async'] = True

            # Extract type parameters
            type_params = self.get_child_by_field_name(node, "type_parameters")
            if type_params:
                metadata['type_parameters'] = [
                    param.text.decode('utf-8')
                    for param in type_params.children
                    if param.type == "type_identifier"
                ]

            # Extract return type
            return_type = self.get_child_by_field_name(node, "return_type")
            if return_type:
                metadata['return_type'] = return_type.text.decode('utf-8')

            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error extracting metadata: {e}")
            return metadata

    def get_child_by_field_name(self, node: Any, field_name: str) -> Any:
        """Get child node by field name"""
        try:
            result = node.child_by_field_name(field_name)
            if result:
                return result
            
            for child in node.children:
                if child.type == field_name:
                    return child
            return None
            
        except Exception:
            return None

    def create_code_location(self, node: Any) -> CodeLocation:
        """Create location information for the node"""
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point
        return CodeLocation(
            start_line=start_line,
            start_col=start_col,
            end_line=end_line,
            end_col=end_col
        )