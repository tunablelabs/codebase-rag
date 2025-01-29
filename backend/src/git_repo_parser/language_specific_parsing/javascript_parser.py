from typing import Any, Dict, List
from ..base_types import BaseLanguageParser, CodeEntity, CodeLocation, StringLiteral

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
            self.logger.error(f"Error parsing JavaScript file {file_path}: {e}")
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
            'function': ['function_declaration', 'arrow_function'],
            'class': 'class_declaration',
            'method': 'method_definition'
        }

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        metadata = {
            'is_async': 'async' in node.type,
            'is_arrow': node.type == 'arrow_function',
            'is_export': False,
            'is_default_export': False
        }

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