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
from .language_specific_parsing.java_parser import JavaParser
from .language_specific_parsing.javascript_parser import JavaScriptParser
from .language_specific_parsing.python_parser import PythonParser
from .language_specific_parsing.typescript_parser import TypeScriptParser
from chunking.chunk_manager import ChunkManager
from chunking.strategies import ChunkInfo

class CodeParser:
    """Main parser that integrates all language parsers"""
      
    def __init__(self):
        self.LANGUAGE_MAPPING = {
        '.py': ('python', PythonParser),
        '.js': ('javascript', JavaScriptParser),
        '.java': ('java', JavaParser),
        '.ts': ('typescript', TypeScriptParser),
        '.tsx': ('typescript', TypeScriptParser)
        }
        self.logger = logging.getLogger(__name__)
        self.base_path = Path(__file__).parent.parent.parent / "tree_sitter_libs"
        self.parsers = self._initialize_parsers()
        self.chunk_manager = ChunkManager(self.parsers) 
    
    def _initialize_parsers(self) -> Dict[str, BaseLanguageParser]:
        parsers = {}
        build_dir = Path(__file__).parent.parent.parent / "tree_build"
        build_dir.mkdir(exist_ok=True)
        
        for ext, (lang, parser_class) in self.LANGUAGE_MAPPING.items():
            try:
                build_path = str(build_dir / f"{lang}.so")
                vendor_path = str(self.base_path / f"tree-sitter-{lang}")
                if not Path(vendor_path).exists():
                    self.logger.error(f"Vendor path not found: {vendor_path}")
                    continue
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
            
            return {
                'file_path': file_path,
                'language': self.LANGUAGE_MAPPING[ext][0],
                'file_type': "code_file",
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
