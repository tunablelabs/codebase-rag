# Code Repository Parser Documentation

## 1. Project Structure
```
src/
├── git_repo_parser/
│   ├── __init__.py
│   ├── base_parser.py              # Main parser orchestrator
│   ├── base_types.py              # Core data structures
│   ├── python_parser.py
│   ├── javascript_parser.py
│   └── java_parser.py
├── chunking/
│   ├── __init__.py
│   ├── chunk_manager.py           # Chunk orchestrator
│   ├── strategies.py              # Chunking strategies
│   └── language_specific_chunk/   # Language-specific chunkers
│       ├── __init__.py
│       ├── python_chunker.py
│       ├── javascript_chunker.py
│       └── java_chunker.py
```

## 2. Core Components Breakdown

### 2.1 Base Types (base_types.py)
```python
# Entity representation
class CodeEntity:
    name: str
    type: str
    content: str
    location: CodeLocation
    language: str
    metadata: Dict

```

### 2.2 Base Parser (base_parser.py)
- Main orchestrator for code parsing
- Manages language parsers
- Integrates with chunk manager

### 2.3 Language Parsers
Each parser (Python/JavaScript/Java) implements:
```python
class LanguageParser:
    def parse(self, content: bytes) -> Any:
        # Raw tree-sitter parsing
        
    def parse_file(self, file_path: str) -> List[CodeEntity]:
        # File parsing and entity extraction
        
    def extract_entities(self, node: Any) -> List[CodeEntity]:
        # Entity extraction from AST
```

### 2.4 Chunk Manager (chunk_manager.py)
- Manages chunking process
- Routes to appropriate language chunker
- Handles file processing

### 2.5 Language Chunkers
Each chunker implements:
```python
class LanguageChunker:
    def create_chunks(self, code: str, file_path: str) -> List[ChunkInfo]:
        # Direct code chunking
        
    def create_chunks_from_entities(self, entities: List[CodeEntity], file_path: str) -> List[ChunkInfo]:
        # Entity-based chunking
```

## 3. Code Flow

### 3.1 Initialization Flow
1. Create CodeParser instance
2. CodeParser initializes language parsers
3. CodeParser initializes ChunkManager
4. ChunkManager initializes language chunkers

```python
parser = CodeParser()  # Initializes entire system
```

### 3.2 File Processing Flow
1. File received by CodeParser
2. Extension checked to select appropriate parser
3. Parser creates AST and extracts entities
4. Entities passed to ChunkManager
5. ChunkManager routes to appropriate chunker
6. Chunker processes entities and creates chunks

```python
# Processing example
result = parser.parse_and_chunk_file("example.py")
```

### 3.3 Chunk Creation Flow
1. Read file content
2. Extract imports
3. Process code entities
4. Create chunks
5. Analyze dependencies
6. Return final chunks

## 4. Example Usage

```python
# Initialize system
from git_repo_parser.base_parser import CodeParser
parser = CodeParser()

# Process single file
result = parser.parse_and_chunk_file("example.py")

# Access results
print(f"Language: {result['language']}")
print(f"Entities found: {len(result['entities'])}")
print(f"Chunks created: {len(result['chunks'])}")

# Examine chunks
for chunk in result['chunks']:
    print(f"\nChunk Type: {chunk.type}")
    print(f"Lines: {chunk.start_line}-{chunk.end_line}")
    print(f"Dependencies: {chunk.dependencies}")
```

## 5. Data Flow Diagram
1. Input: Source code file
2. CodeParser selects appropriate parser
3. Parser creates AST and entities
4. ChunkManager receives entities
5. Language-specific chunker processes entities
6. Output: Structured chunks with metadata

## 6. Implementation Details

### 6.1 Parser Selection
```python
LANGUAGE_MAPPING = {
    '.py': ('python', PythonParser),
    '.js': ('javascript', JavaScriptParser),
    '.java': ('java', JavaParser)
}
```

### 6.2 Chunk Types
- Imports
- Functions/Methods
- Classes
- API endpoints
- Interfaces (Java)

### 6.3 Metadata Tracked
- Line numbers
- Dependencies
- Imports
- Language-specific features
- Modifiers
- Return types

### 6.4 Error Handling
- File reading errors
- Parsing errors
- Chunking errors
- Invalid file types

## 7. Testing Code

```python
# Test file
test_code = """
import pandas as pd

class DataProcessor:
    def process(self, data):
        return pd.DataFrame(data)
"""

# Process
parser = CodeParser()
result = parser.parse_and_chunk_file("test.py")

# Verify results
assert len(result['entities']) > 0
assert len(result['chunks']) > 0
assert result['language'] == 'python'
```
