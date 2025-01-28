from typing import Any, Dict, List
from ..base_types import BaseLanguageParser, CodeEntity, CodeLocation, StringLiteral

class TypeScriptParser(BaseLanguageParser):
    def get_language_name(self) -> str:
        return "typescript"

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
            self.logger.error(f"Error parsing TypeScript file {file_path}: {e}")
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
        return entities

    def get_entity_patterns(self) -> Dict[str, Any]:
        return {
            'function': [
                'function_declaration',
                'arrow_function',
                'function_signature',
                'ambient_declaration'
            ],
            'class': [
                'class_declaration',
                'abstract_class_declaration',
                'ambient_declaration'
            ],
            'interface': 'interface_declaration',
            'type': 'type_alias_declaration',
            'enum': 'enum_declaration',
            'method': [
                'method_definition',
                'method_signature',
                'abstract_method_signature'
            ],
            'property': [
                'property_signature',
                'property_declaration',
                'abstract_property_declaration'
            ]
        }

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        metadata = {
            'is_async': 'async' in node.type,
            'is_arrow': node.type == 'arrow_function',
            'is_export': False,
            'is_default_export': False,
            'is_abstract': 'abstract' in node.type,
            'is_interface': node.type == 'interface_declaration',
            'is_ambient': node.type == 'ambient_declaration',
            'type_parameters': [],
            'return_type': None,
            'modifiers': []
        }

        # Extract type parameters if present
        type_params_node = self.get_child_by_field_name(node, "type_parameters")
        if type_params_node:
            metadata['type_parameters'] = [
                param.text.decode('utf-8') 
                for param in type_params_node.children 
                if param.type == "type_identifier"
            ]

        # Extract return type if present
        return_type_node = self.get_child_by_field_name(node, "return_type")
        if return_type_node:
            metadata['return_type'] = return_type_node.text.decode('utf-8')

        # Extract modifiers (public, private, protected, readonly, etc.)
        for child in node.children:
            if child.type in ['public', 'private', 'protected', 'readonly', 'static']:
                metadata['modifiers'].append(child.type)

        # Check for exports
        parent = node.parent
        while parent:
            if parent.type == 'export_statement':
                metadata['is_export'] = True
                metadata['is_default_export'] = any(
                    child.type == 'default' 
                    for child in parent.children
                )
                break
            parent = parent.parent

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