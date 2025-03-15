from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import logging
from config.logging_config import info, warning, debug, error

@dataclass
class ChunkInfo:
    """Represents a code chunk with metadata"""
    content: str
    language: str  # 'python', 'javascript', etc.
    chunk_id: str
    type: str  # 'function', 'class', 'api', etc.
    start_line: int
    end_line: int
    metadata: Dict = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)

class BaseChunkingStrategy(ABC):
    """Base class for all chunking strategies"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        info(f"Initializing {self.__class__.__name__}")
        
    @abstractmethod
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        """Create chunks from code"""
        pass
    
    def _generate_chunk_id(self, content: str, file_path: str) -> str:
        """Generate unique chunk ID"""
        import hashlib
        content = f"{file_path}:{content}".encode('utf-8')
        return f"chunk_{hashlib.md5(content).hexdigest()[:8]}"

class ApiChunkingStrategy(BaseChunkingStrategy):
    """Strategy for API code chunks"""
    
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        info(f"Chunking API code in {file_path}")
        chunks = []
        current_lines = []
        in_api_block = False
        start_line = 0
        
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            
            # Detect API patterns
            if any(pattern in stripped for pattern in ['@app.', '@router.', 'app.get', 'app.post']):
                if current_lines:  # Save previous non-API chunk
                    content = '\n'.join(current_lines)
                    chunks.append(ChunkInfo(
                        content=content,
                        language='python',
                        chunk_id=self._generate_chunk_id(content, file_path),
                        type='code',
                        start_line=start_line,
                        end_line=i-1
                    ))
                    current_lines = []
                
                in_api_block = True
                start_line = i
                current_lines = [line]
                
            elif in_api_block:
                current_lines.append(line)
                if stripped == '' and len(current_lines) > 2:  # End of API block
                    content = '\n'.join(current_lines)
                    chunks.append(ChunkInfo(
                        content=content,
                        language='python',
                        chunk_id=self._generate_chunk_id(content, file_path),
                        type='api',
                        start_line=start_line,
                        end_line=i,
                        metadata={'api_type': 'endpoint'}
                    ))
                    current_lines = []
                    in_api_block = False
                    start_line = i + 1
                    
            else:
                current_lines.append(line)
        
        # Handle remaining lines
        if current_lines:
            content = '\n'.join(current_lines)
            chunks.append(ChunkInfo(
                content=content,
                language='python',
                chunk_id=self._generate_chunk_id(content, file_path),
                type='code',
                start_line=start_line,
                end_line=len(code.splitlines())
            ))
            
        info(f"Created {len(chunks)} API chunks for {file_path}")
        return chunks

class LogicalChunkingStrategy(BaseChunkingStrategy):
    """Strategy for logical code blocks (functions, classes)"""
    
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        info(f"Chunking logical code blocks in {file_path}")
        chunks = []
        current_lines = []
        start_line = 1
        
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            
            # Detect new logical block
            if stripped.startswith(('def ', 'class ', 'async def ')):
                if current_lines:  # Save previous chunk
                    content = '\n'.join(current_lines)
                    chunk_type = self._determine_type(current_lines[0])
                    chunks.append(ChunkInfo(
                        content=content,
                        language='python',
                        chunk_id=self._generate_chunk_id(content, file_path),
                        type=chunk_type,
                        start_line=start_line,
                        end_line=i-1
                    ))
                
                current_lines = [line]
                start_line = i
            else:
                current_lines.append(line)
        
        # Handle remaining lines
        if current_lines:
            content = '\n'.join(current_lines)
            chunk_type = self._determine_type(current_lines[0])
            chunks.append(ChunkInfo(
                content=content,
                language='python',
                chunk_id=self._generate_chunk_id(content, file_path),
                type=chunk_type,
                start_line=start_line,
                end_line=len(code.splitlines())
            ))
        
        info(f"Created {len(chunks)} logical chunks for {file_path}")
        return chunks
    
    def _determine_type(self, first_line: str) -> str:
        stripped = first_line.strip()
        if stripped.startswith('class '):
            return 'class'
        elif stripped.startswith(('def ', 'async def ')):
            return 'function'
        return 'code'

class ImportChunkingStrategy(BaseChunkingStrategy):
    """Strategy for import statements"""
    
    def chunk(self, code: str, file_path: str) -> List[ChunkInfo]:
        info(f"Chunking import statements in {file_path}")
        imports = []
        current_imports = []
        other_lines = []
        start_line = 1
        in_imports = False
        
        for i, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            
            if stripped.startswith(('import ', 'from ')):
                if not in_imports and current_imports:
                    # Save previous import block
                    content = '\n'.join(current_imports)
                    imports.append(ChunkInfo(
                        content=content,
                        language='python',
                        chunk_id=self._generate_chunk_id(content, file_path),
                        type='import',
                        start_line=start_line,
                        end_line=i-1,
                        imports=set(imp.strip() for imp in current_imports)
                    ))
                
                in_imports = True
                if not current_imports:
                    start_line = i
                current_imports.append(line)
                
            elif in_imports and stripped == '':
                # Empty line after imports
                current_imports.append(line)
                
            else:
                if in_imports:
                    # End of import block
                    content = '\n'.join(current_imports)
                    imports.append(ChunkInfo(
                        content=content,
                        language='python',
                        chunk_id=self._generate_chunk_id(content, file_path),
                        type='import',
                        start_line=start_line,
                        end_line=i-1,
                        imports=set(imp.strip() for imp in current_imports)
                    ))
                    current_imports = []
                    in_imports = False
                    
                other_lines.append(line)
        
        # Handle remaining imports
        if current_imports:
            content = '\n'.join(current_imports)
            imports.append(ChunkInfo(
                content=content,
                language='python',
                chunk_id=self._generate_chunk_id(content, file_path),
                type='import',
                start_line=start_line,
                end_line=len(code.splitlines()),
                imports=set(imp.strip() for imp in current_imports)
            ))
        
        info(f"Created {len(imports)} import chunks for {file_path}")
        return imports