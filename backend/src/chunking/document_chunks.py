import os
from pathlib import Path
import logging
from config.logging_config import info, warning, debug, error
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chunking.strategies import ChunkInfo

logger = logging.getLogger(__name__)

class DocumentChunker:
    
    def __init__(self):
        # File patterns for documentation  files
        self.doc_pattern = ['**/*.md', '**/*.txt', '**/*.rst']
        self.excluded_dirs = ['.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist']
        info("DocumentChunker initialized")
        
    def scan_files(self, repo_path):
        """
        Scan repository for files matching given patterns.
        Args:
            patterns: List of file patterns to match
        Returns:
            Set of matched file paths
        """
        info(f"Scanning repository for documentation files: {repo_path}")
        matched_files = set()
        repo_path = Path(repo_path) 
        
        try:
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    if any(file_path.match(pattern) for pattern in self.doc_pattern):
                        matched_files.add(file_path)
            
            info(f"Found {len(matched_files)} documentation files")
            return matched_files
        except Exception as e:
            error(f"Error scanning repository files: {e}")
            return set()
    
    def create_chunks(self, text, metadata, file_path,
                    chunk_size = 1000, 
                    chunk_overlap = 200):
        """
        Create chunks from text with metadata.
        Args:
            text: Text to chunk
            metadata: Metadata for the chunks
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
        Returns:
            List of chunks with metadata
        """
        info(f"Creating chunks for file: {file_path}")
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            
            chunks = text_splitter.create_documents(
                texts=[text],
                metadatas=[metadata]
            )
            info(f"Created {len(chunks)} chunks from file")
            
            formatted_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_info = ChunkInfo(
                content=chunk.page_content,
                language="text",
                chunk_id=f"{file_path}:chunk_{i}",
                type="text_chunk",
                start_line=0,  # Changed from None since dataclass expects int
                end_line=0,    # Changed from None since dataclass expects int
                metadata={
                    **chunk.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                },
                dependencies=set(),  # Empty set since not specified in input
                imports=set()       # Empty set since not specified in input
                )
                formatted_chunks.append(chunk_info)
                
            return {
                    "file_path": file_path,
                    "language": "text",
                    "file_type": "text_file",
                    "entities": [],  
                    "chunks": formatted_chunks
                }
        except Exception as e:
            error(f"Error creating chunks for {file_path}: {e}")
            return None
        
           
    def parse_directory(self, repo_path):
        """
        Process repository documentation files.
        Args:
            repo_path: Git Repository
        Returns:
            List of processed documents
        """
        info(f"Parsing documentation files in directory: {repo_path}")
        try:
            doc_matched_files = self.scan_files(repo_path)
            repo_path = Path(repo_path) 
            info(f"Processing {len(doc_matched_files)} documentation files")
            
            doc_chunks = {}
            # Common encodings in priority order
            encodings = ['utf-8-sig', 'utf-8', 'windows-1252', 'latin-1', 'ascii']
            
            for file_path in doc_matched_files:
                text = None
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            text = f.read()
                            break
                    except UnicodeDecodeError:
                        continue
                                   
                if text is not None: 
                    chunk_result = self.create_chunks(
                        text,
                        {
                            'doc_type': 'document_file',
                            'source': str(file_path.relative_to(repo_path)),
                            'filename': file_path.name,
                            'file_type': file_path.suffix
                        }, str(file_path)
                    )
                    if chunk_result:
                        doc_chunks[str(file_path)] = chunk_result
                    else:
                        warning(f"No chunks created for {file_path}")
                else:
                    warning(f"Could not read file {file_path} with any of the supported encodings")
                        
            info(f"Completed parsing with {len(doc_chunks)} files processed")
            return doc_chunks
            
        except Exception as e:
            error(f"Error parsing directory {repo_path}: {e}")
            return {}