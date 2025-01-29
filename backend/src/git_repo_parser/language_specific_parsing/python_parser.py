from typing import Any, Dict, List, Tuple
from ..base_types import BaseLanguageParser, CodeEntity, CodeLocation, StringLiteral
from tree_sitter import Node


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
            self.logger.error(f"Error parsing Python file {file_path}: {e}")
            return []

    def extract_entities(self, node: Any) -> List[CodeEntity]:
        entities = []
        for pattern, node_type in self.get_entity_patterns().items():
            for entity_node in node.children:
                if entity_node.type == node_type:
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
            'function': 'function_definition',
            'class': 'class_definition',
            'method': 'function_definition'
        }

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        metadata = {
            'is_async': node.type == 'async_function_definition',
            'decorators': []
        }

        # Extract decorators
        for child in node.children:
            if child.type == 'decorator':
                decorator_node = self.get_child_by_field_name(child, 'name')
                if decorator_node:
                    metadata['decorators'].append(decorator_node.text.decode('utf-8'))

        # Extract docstring
        for child in node.children:
            if child.type == 'expression_statement':
                string_child = child.children[0] if child.children else None
                if string_child and string_child.type in ('string', 'string_content'):
                    metadata['docstring'] = string_child.text.decode('utf-8').strip('"\' \n\t')
                    break

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
