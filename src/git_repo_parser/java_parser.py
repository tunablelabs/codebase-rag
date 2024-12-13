from typing import Any, Dict, List, Tuple
from .base_types import BaseLanguageParser, CodeEntity, CodeLocation, StringLiteral

class JavaParser(BaseLanguageParser):
    def get_language_name(self) -> str:
        return "java"
    
    def parse(self, content: bytes) -> Any:
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
            self.logger.error(f"Error parsing Java file {file_path}: {e}")
            return [], []

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

    def extract_string_literals(self, node: Any) -> List[StringLiteral]:
        string_literals = []
        for child in node.children:
            if child.type == "string_literal":
                text = child.text.decode("utf-8").strip('"')
                if len(text) >= 5:  # Adjust the minimum length as needed
                    string_literals.append(StringLiteral(
                        id=f"string_literal_{len(string_literals)}",
                        content=text,
                        type="string",
                        location=self.create_code_location(child)
                    ))
        return string_literals

    def get_entity_patterns(self) -> Dict[str, Any]:
        return {
            'class': 'class_declaration',
            'method': 'method_declaration',
            'interface': 'interface_declaration'
        }

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        metadata = {
            'modifiers': [],
            'is_public': False,
            'is_static': False,
            'is_final': False,
            'return_type': None
        }

        for child in node.children:
            # Extract modifiers
            if child.type == 'modifiers':
                for modifier in child.children:
                    mod_text = modifier.text.decode('utf-8')
                    metadata['modifiers'].append(mod_text)
                    metadata[f'is_{mod_text}'] = True
            
            # Extract return type for methods
            elif child.type == 'type_identifier' and node.type == 'method_declaration':
                metadata['return_type'] = child.text.decode('utf-8')

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
