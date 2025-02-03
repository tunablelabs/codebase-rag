from typing import Any, Dict, List, Tuple
from ..base_types import BaseLanguageParser, CodeEntity, CodeLocation, StringLiteral

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
            # Class-related patterns
            'class': [
                'class_declaration',
                'enum_declaration',
                'record_declaration'
            ],
            
            # Interface-related patterns
            'interface': [
                'interface_declaration',
                'annotation_type_declaration'
            ],
            
            # Method-related patterns
            'method': [
                'method_declaration',
                'constructor_declaration',
                'compact_constructor_declaration',
                'annotation_method_declaration'
            ],
            
            # Field-related patterns
            'field': [
                'field_declaration',
                'enum_constant',
                'constant_declaration'
            ],
            
            # Variable declarations
            'variable': [
                'local_variable_declaration',
                'variable_declarator'
            ],
            
            # Generic type patterns
            'type_parameter': [
                'type_parameter',
                'type_bound',
                'wildcard_type'
            ],
            
            # Exception handling
            'exception': [
                'catches',
                'catch_clause',
                'try_statement',
                'throw_statement'
            ],
            
            # Control flow
            'control': [
                'if_statement',
                'for_statement',
                'enhanced_for_statement',
                'while_statement',
                'do_statement',
                'switch_expression',
                'switch_block'
            ],
            
            # Annotations
            'annotation': [
                'annotation',
                'marker_annotation',
                'single_element_annotation',
                'normal_annotation'
            ],
            
            # Package and Import
            'package': ['package_declaration'],
            'import': [
                'import_declaration',
                'static_import_declaration'
            ],
            
            # Lambda and Method Reference
            'lambda': [
                'lambda_expression',
                'method_reference'
            ],

            # Comments and Documentation
            'comment': [
                'block_comment',
                'line_comment',
                'javadoc_comment'
            ]
        }

    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        metadata = {
            # Access modifiers
            'is_public': False,
            'is_private': False,
            'is_protected': False,
            'is_package_private': False,
            
            # Non-access modifiers
            'is_static': False,
            'is_final': False,
            'is_abstract': False,
            'is_synchronized': False,
            'is_volatile': False,
            'is_transient': False,
            'is_native': False,
            'is_strictfp': False,
            
            # Method-specific
            'is_constructor': False,
            'return_type': None,
            'throws': [],
            'parameters': [],
            'type_parameters': [],
            
            # Class-specific
            'super_class': None,
            'interfaces': [],
            'is_record': False,
            'is_enum': False,
            
            # Annotation-specific
            'annotations': [],
            
            # Generic
            'modifiers': [],
            'javadoc': None
        }

        try:
            # Process node specific metadata
            if node.type == 'constructor_declaration':
                metadata['is_constructor'] = True
            
            # Extract modifiers
            modifiers_node = next((child for child in node.children if child.type == 'modifiers'), None)
            if modifiers_node:
                for modifier in modifiers_node.children:
                    mod_text = modifier.text.decode('utf-8')
                    metadata['modifiers'].append(mod_text)
                    if mod_text in ['public', 'private', 'protected', 'static', 'final', 
                                  'abstract', 'synchronized', 'volatile', 'transient', 
                                  'native', 'strictfp']:
                        metadata[f'is_{mod_text}'] = True
            
            # Extract return type for methods
            if node.type == 'method_declaration':
                return_type_node = next((child for child in node.children 
                                      if child.type in ['type_identifier', 'void_type']), None)
                if return_type_node:
                    metadata['return_type'] = return_type_node.text.decode('utf-8')
            
            # Extract throws clause
            throws_node = next((child for child in node.children if child.type == 'throws'), None)
            if throws_node:
                metadata['throws'] = [
                    child.text.decode('utf-8')
                    for child in throws_node.children
                    if child.type == 'type_identifier'
                ]
            
            # Extract parameters
            parameters_node = next((child for child in node.children if child.type == 'formal_parameters'), None)
            if parameters_node:
                for param in parameters_node.children:
                    if param.type == 'formal_parameter':
                        param_name = next((child.text.decode('utf-8') 
                                        for child in param.children 
                                        if child.type == 'identifier'), None)
                        if param_name:
                            metadata['parameters'].append(param_name)
            
            # Extract type parameters
            type_parameters_node = next((child for child in node.children if child.type == 'type_parameters'), None)
            if type_parameters_node:
                metadata['type_parameters'] = [
                    child.text.decode('utf-8')
                    for child in type_parameters_node.children
                    if child.type == 'type_parameter'
                ]
            
            # Extract superclass and interfaces for classes
            if node.type == 'class_declaration':
                superclass_node = next((child for child in node.children if child.type == 'superclass'), None)
                if superclass_node:
                    metadata['super_class'] = superclass_node.children[0].text.decode('utf-8')
                
                interfaces_node = next((child for child in node.children if child.type == 'super_interfaces'), None)
                if interfaces_node:
                    metadata['interfaces'] = [
                        child.text.decode('utf-8')
                        for child in interfaces_node.children
                        if child.type == 'type_identifier'
                    ]
            
            # Extract annotations
            for child in node.children:
                if child.type in ['annotation', 'marker_annotation', 'single_element_annotation']:
                    metadata['annotations'].append(child.text.decode('utf-8'))
            
            # Extract Javadoc if present
            javadoc = next((child for child in node.children if child.type == 'javadoc_comment'), None)
            if javadoc:
                metadata['javadoc'] = javadoc.text.decode('utf-8')
            
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error extracting metadata: {e}")
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