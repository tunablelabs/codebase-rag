import os
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
        
        self.doc_pattern = ['**/*.md', '**/*.txt', '**/*.rst']
        self.processed_files = set()
    
    def _initialize_parsers(self) -> Dict[str, BaseLanguageParser]:
        parsers = {}
        build_dir = Path(__file__).parent.parent.parent / "tree_build"
        build_dir.mkdir(exist_ok=True)
        
        for ext, (lang, parser_class) in self.LANGUAGE_MAPPING.items():
            try:
                build_path = str(build_dir / f"{lang}.so")
                if ext in [".ts",".tsx"]:
                    vendor_path = str(self.base_path / f"tree-sitter-{lang}/{lang}")
                else:
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
            # First process files with known parsers
            for ext in self.parsers:
                for file_path in directory.rglob(f"*{ext}"):
                    file_result = self.parse_file(str(file_path))
                    if file_result:
                        results[str(file_path)] = file_result
                    self.processed_files.add(file_path)
            
            excluded_dirs = {
                            "node_modules", "venv", "env", "__pycache__", ".git", 
                            "dist", "build", "target", "bin", "obj",
                            "packages", "vendor", "bower_components", ".idea",
                            ".vscode", ".ipynb_checkpoints"
                        }
            # Then process remaining files without specific parsers
            for file_path in directory.rglob("*.*"):
                # Skip already processed files
                if file_path in self.processed_files:
                    continue
                
                # Skip files in excluded directories
                if any(excluded_dir in str(file_path).lower() for excluded_dir in excluded_dirs):
                    continue
                    
                if file_path.is_file():
                    if os.path.splitext(file_path)[1] in [".txt",".md",".rst",".rtf",".yaml",".json"]:
                        continue
                    file_result = self.process_file_as_text(str(file_path))
                    
                    if file_result:
                        results[str(file_path)] = file_result        
                        
            # Add summary
            results['summary'] = self._generate_summary(results)
            return results
                        
        except Exception as e:
            self.logger.error(f"Error parsing directory {directory_path}: {e}")
            return results
        
    def process_file_as_text(self, file_path: str) -> Dict[str, Any]:
        """Process a file as plain text and chunk it for vector DB"""
        try:
            # Try to read file as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Skip binary files
                return None
            
            # Get file extension
            ext = Path(file_path).suffix.lower()
            
            # Create chunks for vector DB
            chunks = self.create_chunks_nonparser(content)
            
            # Return structured data for vector DB
            return {
                'file_path': file_path,
                'file_type': "code_file",
                'chunks': chunks
            }
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return None
        
    # create Chunks for Non parser files like we not yet implimented html, kotlin like that we pasre those files as text files
    def create_chunks_nonparser(self, content: str, filename: str = "", max_chunk_size: int = 700, overlap: int = 200) -> List[Dict[str, Any]]:
        """Split content into chunks with metadata for vector DB"""
        if not content.strip():
            return []
            
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_id = 0
        last_chunk_end = 0
        
        # Extract potential title from first line
        document_title = lines[0] if lines else ""
        
        for i, line in enumerate(lines):
            line_size = len(line)
            
            # If adding this line would exceed max chunk size, create a new chunk
            if current_size + line_size > max_chunk_size and current_chunk:
                chunk_text = '\n'.join(current_chunk)
                
                # Find section headers in chunk for better metadata
                section_headers = [l for l in current_chunk if l.strip() and (l.isupper() or l.endswith(':'))]
                section_title = section_headers[0] if section_headers else ""
                
                chunks.append({
                    'chunk_id': f"{filename}_{chunk_id}" if filename else chunk_id,
                    'content': chunk_text,
                    'start_line': last_chunk_end,
                    'end_line': i - 1,
                    'document_title': document_title,
                    'section_title': section_title,
                    'filename': filename
                })
                chunk_id += 1
                
                # Calculate overlap based on character count
                overlap_size = 0
                overlap_lines = []
                for prev_line in reversed(current_chunk):
                    if overlap_size + len(prev_line) > overlap:
                        break
                    overlap_lines.insert(0, prev_line)
                    overlap_size += len(prev_line)
                    
                current_chunk = overlap_lines.copy()
                current_size = sum(len(l) for l in current_chunk)
                last_chunk_end = i - len(overlap_lines)
                    
            current_chunk.append(line)
            current_size += line_size
            
        # Add the last chunk if not empty
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            
            section_headers = [l for l in current_chunk if l.strip() and (l.isupper() or l.endswith(':'))]
            section_title = section_headers[0] if section_headers else ""
            
            chunks.append({
                'chunk_id': f"{filename}_{chunk_id}" if filename else chunk_id,
                'content': chunk_text,
                'start_line': last_chunk_end,
                'end_line': len(lines) - 1,
                'document_title': document_title,
                'section_title': section_title,
                'filename': filename
            })
            
        return chunks

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
