import time
from tree_sitter import Language, Parser, Node
from typing import Dict, Optional, List, Any
from pathlib import Path
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from code_chunking.context import ChunkingContext
from code_chunking.chunk_manager import ChunkManager
from .python_relationships import CodeRelationshipAnalyzer
from .schemas import BaseEntity, ChunkMetadata, Location
from .python_extractor import CodeExtractor

class CodeParser:
    """Parser that integrates enhanced code chunking and relationship analysis."""
    
    DEFAULT_BUILD_PATH = 'build/my-languages.so'
    DEFAULT_VENDOR_PATH = 'tree_sitter_libs/tree-sitter-python'
    
    def __init__(self, 
                 build_path: str = DEFAULT_BUILD_PATH, 
                 vendor_path: str = DEFAULT_VENDOR_PATH,
                 max_workers: int = 4):
        """
        Initialize the parser with Tree-sitter and chunking support.
        
        Args:
            build_path: Path to build the language library
            vendor_path: Path to the tree-sitter grammar
            max_workers: Maximum number of worker threads
        """
        self.build_path = build_path
        self.vendor_path = vendor_path
        self.max_workers = max_workers
        
        # Initialize logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self._initialize_parser()
        self.relationship_analyzer = CodeRelationshipAnalyzer()
        self.chunk_manager = ChunkManager(self.parser, self.relationship_analyzer)
        
        # Cache for parsed results
        self.parse_cache: Dict[str, Any] = {}
        
        # Statistics tracking
        self.stats = {
            'files_processed': 0,
            'total_chunks': 0,
            'total_entities': 0,
            'processing_time': 0
        }
        
    def _initialize_parser(self) -> None:
        """Initialize and configure the tree-sitter parser."""
        try:
            build_path = Path(self.build_path)
            if not build_path.exists():
                build_path.parent.mkdir(parents=True, exist_ok=True)
                Language.build_library(
                    str(build_path),
                    [self.vendor_path]
                )
            
            PY_LANGUAGE = Language(self.build_path, 'python')
            self.parser = Parser()
            self.parser.set_language(PY_LANGUAGE)
            self.logger.info("Successfully initialized Tree-sitter parser")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize parser: {str(e)}")
            raise RuntimeError(f"Parser initialization failed: {str(e)}") from e
        
    def _extract_entities(self, node: 'Node', content: str, file_path: str, chunk_id: str) -> List[BaseEntity]:
        """
        Extract code entities from a tree-sitter node.
        
        Args:
            node: Tree-sitter AST node
            content: Source code content
            file_path: Path to source file
            chunk_id: ID of current chunk
            
        Returns:
            List of extracted code entities
        """
        try:
            # Create or get code extractor instance
            extractor = CodeExtractor()
            extractor.set_source(content, file_path, chunk_id)
            
            # Process the code chunk and extract entities
            extracted_data = extractor.process_file(content, file_path, chunk_id)
            
            # Combine all entities into a single list
            entities = []
            entities.extend(extracted_data.get('functions', []))
            entities.extend(extracted_data.get('classes', []))
            entities.extend(extracted_data.get('api_endpoints', []))
            entities.extend(extracted_data.get('api_routers', []))
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Error extracting entities from chunk {chunk_id}: {e}")
            return []

    def _extract_language_features(self, node: 'Node') -> Dict[str, bool]:
        """
        Extract Python language features used in the code.
        
        Args:
            node: Tree-sitter AST node
            
        Returns:
            Dict of language features and their presence
        """
        features = {
            'has_async': False,
            'has_decorators': False,
            'has_type_hints': False,
            'has_context_managers': False,
            'has_generators': False,
            'has_comprehensions': False
        }
        
        def visit_node(current_node: 'Node'):
            if current_node.type == 'async_function_definition':
                features['has_async'] = True
            elif current_node.type == 'decorator':
                features['has_decorators'] = True
            elif current_node.type == 'type':
                features['has_type_hints'] = True
            elif current_node.type == 'with_statement':
                features['has_context_managers'] = True
            elif current_node.type == 'yield_expression':
                features['has_generators'] = True
            elif current_node.type in ['list_comprehension', 'dictionary_comprehension', 'set_comprehension']:
                features['has_comprehensions'] = True
                
            for child in current_node.children:
                visit_node(child)
        
        visit_node(node)
        return features

    def _calculate_chunk_complexity(self, node: 'Node') -> int:
        """
        Calculate cyclomatic complexity of a code chunk.
        
        Args:
            node: Tree-sitter AST node
            
        Returns:
            Complexity score as integer
        """
        complexity = 1  # Base complexity
        
        def count_complexity_increasing_nodes(current_node: 'Node'):
            nonlocal complexity
            
            # Nodes that increase complexity
            complexity_nodes = {
                'if_statement',
                'elif_clause',
                'else_clause',
                'for_statement',
                'while_statement',
                'try_statement',
                'except_clause',
                'with_statement',
                'boolean_operator',  # and, or operators
                'match_statement',   # Python 3.10+ match-case
                'case_clause'
            }
            
            # Increment complexity for specific node types
            if current_node.type in complexity_nodes:
                complexity += 1
                
            # Check for boolean operators (and, or)
            if current_node.type == 'boolean_operator':
                complexity += len(current_node.children) - 1
                
            # Recursively process child nodes
            for child in current_node.children:
                count_complexity_increasing_nodes(child)
        
        count_complexity_increasing_nodes(node)
        return complexity


    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a Python file with enhanced chunking support.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dict containing parsed data, chunks, and analysis
        """
        start_time = time.time()
        try:
            # Check cache first
            if file_path in self.parse_cache:
                return self.parse_cache[file_path]
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create chunking context
            context = ChunkingContext(file_path)
            
            # Create chunks with enhanced metadata
            chunks = self.chunk_manager.create_chunks(content, file_path, context)
            
            # Process each chunk
            processed_chunks = []
            entities_found = 0
            
            for chunk in chunks:
                try:
                    chunk_result = self._process_chunk(chunk, context)
                    if chunk_result is not None and chunk_result.get('chunk_id') is not None:
                        processed_chunks.append(chunk_result)
                        entities_found += len(chunk_result.get('entities', []))
                    else:
                        self.logger.warning(f"Skipping chunk with None chunk_id: {chunk}")
                except Exception as e:
                    self.logger.warning(f"Failed to process chunk: {e}")
                    continue
                
            # Update stats
            self.stats['files_processed'] += 1
            self.stats['total_chunks'] += len(chunks)
            self.stats['total_entities'] += entities_found
            
            # Prepare final result
            result = {
                'file_path': file_path,
                'chunks': processed_chunks,
                'context': context,
                'analysis': {
                    'num_chunks': len(chunks),
                    'num_entities': entities_found,
                    'complexity_score': self._calculate_file_complexity(chunks),
                    'relationships': self.relationship_analyzer.get_file_relationships(file_path),
                    'processing_time': time.time() - start_time
                }
            }
            
            # Cache the result
            self.parse_cache[file_path] = result
            
            return result
            
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error parsing file {file_path}: {e}")
            raise RuntimeError(f"Failed to parse {file_path}: {e}") from e
        finally:
            processing_time = time.time() - start_time
            self.stats['processing_time'] += processing_time

    def _process_chunk(self, chunk: Dict, context: ChunkingContext) -> Dict:
        """Process a single chunk with enhanced analysis."""
        try:
            chunk_id = chunk.get('chunk_id')
            if chunk_id is None:
                self.logger.warning(f"Chunk ID is None for chunk: {chunk}")
                return None
            
            content = chunk['content']
            
            # Parse chunk
            tree = self.parser.parse(bytes(content, 'utf8'))
            
            # Extract entities with enhanced metadata
            entities = self._extract_entities(
                tree.root_node, 
                content, 
                chunk['metadata']['file_path'], 
                chunk_id
            )
            
            # Update relationship analyzer
            self.relationship_analyzer.analyze_entities(entities)
            
            # Get enhanced metadata
            metadata = context.get_chunk_summary(chunk_id)
            
            # Prepare vector DB metadata
            vector_db_metadata = {
                'code_type': metadata['type'],
                'semantic_context': context.semantic_contexts.get(chunk_id, ''),
                'entities': [e.name for e in entities],
                'language_features': self._extract_language_features(tree.root_node),
                'complexity': self._calculate_chunk_complexity(tree.root_node)
            }
            
            return {
                'tree': tree,
                'content': content,
                'chunk_id': chunk_id,
                'metadata': metadata,
                'entities': entities,
                'vector_db_metadata': vector_db_metadata,
                'relationships': self.relationship_analyzer.get_chunk_relationships(chunk_id)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing chunk {chunk.get('chunk_id')}: {e}")
            raise

    def _calculate_file_complexity(self, chunks: List[Dict]) -> float:
        """Calculate overall file complexity score."""
        total_complexity = 0
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            total_complexity += metadata.get('complexity', 0)
        return total_complexity / len(chunks) if chunks else 0

    def parse_directory(self, directory_path: str, batch_size: int = 10) -> Dict[str, Dict]:
        """
        Parse all Python files in a directory with enhanced parallel processing.
        
        Args:
            directory_path: Path to directory
            batch_size: Number of files per batch
            
        Returns:
            Dict mapping file paths to their parsed content
        """
        start_time = time.time()
        directory_path = Path(directory_path)
        parsed_files = {}
        python_files = list(directory_path.rglob("*.py"))
        
        self.logger.info(f"Found {len(python_files)} Python files to parse")
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.parse_file, str(file_path)): file_path 
                    for file_path in python_files
                }
                
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        parsed_files[str(file_path)] = future.result()
                    except Exception as e:
                        self.logger.warning(f"Failed to parse {file_path}: {str(e)}")
                        continue
            
            # Prepare directory analysis
            analysis = {
                'total_files': len(python_files),
                'successful_parses': len(parsed_files),
                'total_chunks': self.stats['total_chunks'],
                'total_entities': self.stats['total_entities'],
                'processing_time': time.time() - start_time,
                'average_chunks_per_file': self.stats['total_chunks'] / len(parsed_files) if parsed_files else 0,
                'relationships': self.relationship_analyzer.generate_dependency_report()
            }
            
            return {
                'files': parsed_files,
                'analysis': analysis
            }
            
        except Exception as e:
            self.logger.error(f"Directory parsing failed: {e}")
            raise RuntimeError(f"Failed to parse directory: {e}") from e
        finally:
            # Clear cache after directory processing
            self.parse_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        return {
            'files_processed': self.stats['files_processed'],
            'total_chunks': self.stats['total_chunks'],
            'total_entities': self.stats['total_entities'],
            'average_chunks_per_file': self.stats['total_chunks'] / self.stats['files_processed'] 
                                     if self.stats['files_processed'] else 0,
            'total_processing_time': self.stats['processing_time'],
            'average_processing_time': self.stats['processing_time'] / self.stats['files_processed']
                                     if self.stats['files_processed'] else 0
        }

    def clear_cache(self) -> None:
        """Clear the parser's cache."""
        self.parse_cache.clear()
        self.logger.debug("Cleared parser cache")

    def reset_stats(self) -> None:
        """Reset parsing statistics."""
        self.stats = {
            'files_processed': 0,
            'total_chunks': 0,
            'total_entities': 0,
            'processing_time': 0
        }
        self.logger.debug("Reset parsing statistics")