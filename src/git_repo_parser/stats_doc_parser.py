from pathlib import Path
import os
from collections import defaultdict
from typing import Dict, Set, Tuple
from transformers import pipeline
import logging

class StatsDocParser:
    LANGUAGE_EXTENSIONS = {'.py': 'Python','.js': 'JavaScript','.java': 'Java','.cpp': 'C++',
                           '.c': 'C','.html': 'HTML','.css': 'CSS','.rs': 'Rust','.go': 'Go',
                           '.rb': 'Ruby','.php': 'PHP','.ts': 'TypeScript','.swift': 'Swift',
                           '.kt': 'Kotlin'}
    
    DOC_PATTERNS = ['README.md', 'README.txt', '**/*.md', '**/*.txt', '**/*.rst']

    def __init__(self, repo_path: str, model_name: str = "facebook/bart-large-cnn"):
        self.repo_path = Path(repo_path)
        self.excluded_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist'}
        self.logger = logging.getLogger(__name__)
        self.code_files, self.doc_files = self._scan_repository()

    def _scan_repository(self) -> Tuple[Set[Path], Set[Path]]:
        code_files = set()
        doc_files = set()
        
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                
                if ext in self.LANGUAGE_EXTENSIONS:
                    code_files.add(file_path)
                    
                if any(file_path.match(pattern) for pattern in self.DOC_PATTERNS):
                    doc_files.add(file_path)
                    
        return code_files, doc_files
    
    async def get_stats(self) -> Dict:
        language_stats = defaultdict(int)
        code_metrics = {'total_lines': 0, 'type_counts': defaultdict(int)}
        total_size = 0

        # Process code files
        for file_path in self.code_files:
            ext = file_path.suffix.lower()
            size = os.path.getsize(file_path)
            language = self.LANGUAGE_EXTENSIONS[ext]
            
            language_stats[language] += size
            total_size += size
            code_metrics['type_counts'][ext] += 1
                
        if total_size > 0:
            language_distribution = {}
            for language, size in language_stats.items():
                percentage = (size / total_size) * 100
                language_distribution[language] = f"{percentage:.2f}%"
        else:
            language_distribution = {}

        return {
            'stats': {
                'language_distribution': language_distribution,
                'total_files': len(self.code_files),
                'total_size': total_size,
                'languages': list(language_stats.keys()),
                'file_types': dict(code_metrics['type_counts'])
            }
        }