from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import tree_sitter
import logging
from pathlib import Path

@dataclass
class CodeLocation:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

@dataclass
class StringLiteral:
    """Represents a code chunk with metadata"""
    id: str
    content: str
    type: str  # 'function', 'class', 'api', 'import'
    location: CodeLocation
    entities: List['CodeEntity'] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CodeEntity:
    name: str
    type: str
    content: str
    location: CodeLocation
    language: str
    chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseLanguageParser(ABC):
    def __init__(self, build_path: str, vendor_path: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parser = self._initialize_parser(build_path, vendor_path)
        
    def _initialize_parser(self, build_path: str, vendor_path: str) -> tree_sitter.Parser:
        try:
            build_path_obj = Path(build_path)
            if not build_path_obj.exists():
                tree_sitter.Language.build_library(
                    str(build_path_obj),
                    [vendor_path]
                )
            
            parser = tree_sitter.Parser()
            language = tree_sitter.Language(build_path, self.get_language_name())
            parser.set_language(language)
            return parser
            
        except Exception as e:
            self.logger.error(f"Failed to initialize parser: {e}")
            raise
    
    @abstractmethod
    def get_language_name(self) -> str:
        """Return the language name for tree-sitter"""
        pass
    
    @abstractmethod
    def get_entity_patterns(self) -> Dict[str, Any]:
        """Return patterns for entity detection"""
        pass
    
    @abstractmethod
    def extract_metadata(self, node: Any) -> Dict[str, Any]:
        """Extract language-specific metadata"""
        pass