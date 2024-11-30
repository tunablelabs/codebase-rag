# Code Analysis Platform

A comprehensive platform for analyzing code repositories using Tree-sitter parsing, vector embeddings, and an interactive chat interface. This system processes multiple programming languages, chunks code intelligently, and provides a searchable interface through a vector database.

## Project Structure

### Source Code (`src/`)

#### 1. Git Parser (`git_parser/`)
- `repo_parser.py`: Handles cloning and basic repository operations
- `language_detector.py`: Identifies programming languages in the repository

#### 2. Tree-sitter Handlers (`tree_sitter_handlers/`)
- `parser_factory.py`: Creates language-specific parsers
- `java_parser.py`: Java-specific AST parsing and analysis
- `javascript_parser.py`: JavaScript-specific parsing
- `python_parser.py`: Python-specific parsing

#### 3. Code Chunking (`code_chunking/`)
- `chunker.py`: Splits code into meaningful segments
- `chunk_processor.py`: Processes and cleanses code chunks for analysis

#### 4. Vector Store (`vector_store/`)
- `embeddings.py`: Generates embeddings for code chunks
- `vector_db.py`: Manages vector database operations
- `query_handler.py`: Handles similarity searches

#### 5. API (`api/`)
- `routes.py`: API endpoint definitions
- `middleware.py`: Request/response processing

#### 6. Utilities (`utils/`)
- `file_utils.py`: File operation helpers
- `text_processors.py`: Text processing utilities

### Tests (`tests/`)
Contains test suites for all major components:
- Git parser tests
- Tree-sitter parsing tests
- Chunking logic tests
- Vector store operations tests
- API endpoint tests

### Configuration (`config/`)
- `tree_sitter_config.yaml`: Tree-sitter parser configurations
- `chunking_rules.yaml`: Rules for code segmentation
- `vector_db_config.yaml`: Vector database settings
- `api_config.yaml`: API configurations

### Tree-sitter Libraries (`tree_sitter_libs/`)
Contains language-specific Tree-sitter grammars:
- Java grammar
- JavaScript grammar
- Python grammar

### Documentation (`docs/`)
- `API.md`: API documentation
- `SETUP.md`: Setup instructions
- `architecture/`: Detailed system design documents

### Install Scripts (`install_scripts/`)
- `install_tree_sitter.sh`: Installs required Tree-sitter libraries
- `setup_vector_db.sh`: Sets up vector database

## Configuration

1. Tree-sitter Configuration:
   - Edit `config/tree_sitter_config.yaml` to modify parsing rules
   - Add new language support in `tree_sitter_handlers/`

2. Vector Database:
   - Configure database settings in `config/vector_db_config.yaml`
   - Adjust embedding parameters as needed

3. API Settings:
   - Modify endpoints in `config/api_config.yaml`
   - Configure authentication if required
