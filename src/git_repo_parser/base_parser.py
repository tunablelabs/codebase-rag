from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import tree_sitter

from .base_types import (
    CodeLocation, 
    StringLiteral, 
    CodeEntity, 
    BaseLanguageParser
)
from .java_parser import JavaParser
from .javascript_parser import JavaScriptParser
from .python_parser import PythonParser
from chunking.chunk_manager import ChunkManager
from chunking.strategies import ChunkInfo

class CodeParser:
    """Main parser that integrates all language parsers"""
    
    LANGUAGE_MAPPING = {
        '.py': ('python', PythonParser),
        '.js': ('javascript', JavaScriptParser),
        '.java': ('java', JavaParser)
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parsers = self._initialize_parsers()
        self.chunk_manager = ChunkManager(self.parsers) 
    
    def _initialize_parsers(self) -> Dict[str, BaseLanguageParser]:
        parsers = {}
        build_dir = Path("build")
        build_dir.mkdir(exist_ok=True)
        
        for ext, (lang, parser_class) in self.LANGUAGE_MAPPING.items():
            try:
                build_path = str(build_dir / f"{lang}.so")
                vendor_path = f"tree_sitter_libs/tree-sitter-{lang}"
                parsers[ext] = parser_class(build_path, vendor_path)
            except Exception as e:
                self.logger.error(f"Failed to initialize {lang} parser: {e}")
        
        return parsers

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a single file and create chunks"""
        try:
            ext = Path(file_path).suffix
            parser = self.parsers.get(ext)
            if not parser:
                raise ValueError(f"Unsupported file type: {ext}")
            
            # Parse entities
            entities = parser.parse_file(file_path)
            
            # Get appropriate chunker
            chunker = self.chunk_manager.chunkers.get(ext)
            if not chunker:
                raise ValueError(f"No chunker available for {ext} files")
            
            # Create chunks from the parsed entities first
            chunks = chunker.create_chunks_from_entities(entities, file_path)
            
            # Add import chunks and enrich with dependencies
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Get import chunks
            import_chunks = chunker.import_strategy.chunk(content, file_path)
            chunks.extend(import_chunks)
            
            # Enrich all chunks with dependencies
            tree = chunker.parser.parse(bytes(content, 'utf-8'))
            if tree:
                chunker._enrich_chunks(chunks, tree.root_node, content)
            
            return {
                'file_path': file_path,
                'language': self.LANGUAGE_MAPPING[ext][0],
                'entities': entities,
                'chunks': chunks
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing file {file_path}: {e}")
            return {}
    
    def parse_directory(self, directory_path: str) -> Dict[str, Any]:
        """Parse all supported files in a directory"""
        results = {}
        directory = Path(directory_path)
        
        try:
            for ext in self.parsers:
                for file_path in directory.rglob(f"*{ext}"):
                    file_result = self.parse_file(str(file_path))
                    if file_result:
                        results[str(file_path)] = file_result
            
            # Add summary
            results['summary'] = self._generate_summary(results)
            return results
            
        except Exception as e:
            self.logger.error(f"Error parsing directory {directory_path}: {e}")
            return results

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of parsing results"""
        summary = {
            'total_files': len(results) - 1,  # Subtract 1 for summary key
            'by_language': {},
            'total_entities': 0,
            'total_chunks': 0,
            'by_type': {
                'entities': {},
                'chunks': {}
            }
        }

        for file_data in results.values():
            if isinstance(file_data, dict) and 'language' in file_data:
                lang = file_data['language']
                summary['by_language'][lang] = summary['by_language'].get(lang, 0) + 1
                
                entities = file_data.get('entities', [])
                chunks = file_data.get('chunks', [])
                
                summary['total_entities'] += len(entities)
                summary['total_chunks'] += len(chunks)
                
                # Count by type
                for entity in entities:
                    summary['by_type']['entities'][entity.type] = \
                        summary['by_type']['entities'].get(entity.type, 0) + 1
                
                for chunk in chunks:
                    summary['by_type']['chunks'][chunk.type] = \
                        summary['by_type']['chunks'].get(chunk.type, 0) + 1

        return summary