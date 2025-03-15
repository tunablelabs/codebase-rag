from pathlib import Path
import os
from collections import defaultdict
from typing import Dict, Set, Tuple
from transformers import pipeline
# Replace standard logging with our custom logging
from config.logging_config import info, error, warning, debug


class StatsParser:
    
    def __init__(self, repo_path: str):
        self.LANGUAGE_EXTENSIONS = {'.py': 'Python','.js': 'JavaScript','.java': 'Java','.cpp': 'C++',
                                    '.c': 'C','.html': 'HTML','.css': 'CSS','.rs': 'Rust','.go': 'Go',
                                    '.rb': 'Ruby','.php': 'PHP','.ts': 'TypeScript','.swift': 'Swift',
                                    '.kt': 'Kotlin','.txt':'Text File'}
        self.repo_path = Path(repo_path)
        self.excluded_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist'}
        # Remove the logger initialization
        self.code_files = self._scan_repository()
        
    def _scan_repository(self) -> Set[Path]:
        code_files = set()
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                if ext in self.LANGUAGE_EXTENSIONS:
                    code_files.add(file_path)   
        return code_files
    
    async def get_stats(self) -> Dict:
        language_stats = defaultdict(int)
        total_size = 0
        # Process code files
        for file_path in self.code_files:
            ext = file_path.suffix.lower()
            size = os.path.getsize(file_path)
            language = self.LANGUAGE_EXTENSIONS[ext]
            language_stats[language] += size
            total_size += size
                
        if total_size > 0:
            language_distribution = {}
            for language, size in language_stats.items():
                percentage = (size / total_size) * 100
                language_distribution[language] = f"{percentage:.2f}%"
                
        else:
            language_distribution = {}

        return {
            'stats': {
                'total_code_files': len(self.code_files),
                'language_distribution': language_distribution
            }
        }