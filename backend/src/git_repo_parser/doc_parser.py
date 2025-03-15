from pathlib import Path
from typing import Set
import os
# Replace standard logging with our custom logging
from config.logging_config import info, error, warning, debug


class DocParser:
    DOC_PATTERNS = ['README.md', 'README.txt', '**/*.md', '**/*.txt', '**/*.rst']
    
    def __init__(self, repo_path: str, model_name: str = "facebook/bart-large-cnn"):
        self.repo_path = Path(repo_path)
        self.excluded_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist'}
        # Remove the logger initialization
        self.doc_files = self._scan_repository()
        
    def _scan_repository(self) -> Set[Path]:
        doc_files = set()
        
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                file_path = Path(root) / file
                if any(file_path.match(pattern) for pattern in self.DOC_PATTERNS):
                    doc_files.add(file_path)
                    
        return doc_files