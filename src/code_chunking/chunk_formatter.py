from typing import Dict, List, Optional
import logging
from pathlib import Path

class ChunkFormatter:
    """Formats code chunks for vector database storage."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def format_for_vector_db(self, chunk: Dict) -> Dict:
        """Format a single chunk for vector database storage."""
        try:
            return {
                "id": chunk["chunk_id"],
                "content": chunk["content"],
                "metadata": self._prepare_metadata(chunk),
                "relationships": self._prepare_relationships(chunk),
                "embedding_context": self._generate_embedding_context(chunk)
            }
        except Exception as e:
            self.logger.error(f"Error formatting chunk {chunk.get('chunk_id')}: {e}")
            raise
    
    def _prepare_metadata(self, chunk: Dict) -> Dict:
        """Prepare chunk metadata."""
        metadata = chunk.get("metadata", {})
        return {
            "file_path": metadata.get("file_path", ""),
            "language": metadata.get("language", ""),
            "type": self._determine_chunk_type(chunk),
            "entities": self._extract_entity_names(chunk),
            "dependencies": metadata.get("dependencies", []),
            "api_info": self._extract_api_info(chunk),
            "line_range": self._get_line_range(chunk),
            "is_api_component": metadata.get("api_components", False),
            "is_async": metadata.get("async_code", False)
        }
    
    def _determine_chunk_type(self, chunk: Dict) -> str:
        """Determine the type of code in the chunk."""
        content = chunk.get("content", "")
        if "class " in content:
            return "class_definition"
        elif "def " in content:
            return "function_definition"
        elif "import " in content or "from " in content:
            return "imports"
        elif "@app" in content or "@router" in content:
            return "api_endpoint"
        return "code_block"
    
    def _extract_entity_names(self, chunk: Dict) -> List[str]:
        """Extract names of entities defined in the chunk."""
        entities = []
        metadata = chunk.get("metadata", {})
        
        # Extract from different entity types
        for entity_type in ['functions', 'classes', 'api_endpoints']:
            if entity_type in metadata.get("entities", {}):
                entities.extend(e.get("name", "") for e in metadata["entities"][entity_type])
        
        return [e for e in entities if e]
    
    def _extract_api_info(self, chunk: Dict) -> Dict:
        """Extract API-related information if present."""
        metadata = chunk.get("metadata", {})
        if not metadata.get("api_components"):
            return {}
            
        api_info = {}
        content = chunk.get("content", "")
        
        # Extract route information
        for line in content.split("\n"):
            if "@app." in line or "@router." in line:
                method = next((m for m in ["get", "post", "put", "delete"] if m in line.lower()), "")
                if method:
                    api_info["method"] = method.upper()
                    # Extract route path
                    if '("' in line:
                        path = line.split('("')[1].split('")')[0]
                        api_info["path"] = path
                    
        return api_info
    
    def _get_line_range(self, chunk: Dict) -> str:
        """Get the line range of the chunk."""
        metadata = chunk.get("metadata", {})
        start = metadata.get("start_line", 0)
        end = metadata.get("end_line", 0)
        return f"{start}-{end}"
    
    def _prepare_relationships(self, chunk: Dict) -> Dict:
        """Prepare relationship information."""
        metadata = chunk.get("metadata", {})
        return {
            "dependencies": metadata.get("dependencies", []),
            "type_dependencies": metadata.get("type_dependencies", []),
            "imports": metadata.get("imports", []),
            "dependents": []  # Will be filled by relationship analyzer
        }
    
    def _generate_embedding_context(self, chunk: Dict) -> str:
        """Generate natural language context for embedding."""
        context_parts = []
        
        # Add file context
        metadata = chunk.get("metadata", {})
        context_parts.append(f"This code is from {metadata.get('file_path', 'unknown file')}")
        
        # Add code type context
        chunk_type = self._determine_chunk_type(chunk)
        context_parts.append(f"This is a {chunk_type.replace('_', ' ')}")
        
        # Add entity context
        entities = self._extract_entity_names(chunk)
        if entities:
            context_parts.append(f"It defines: {', '.join(entities)}")
        
        # Add API context
        api_info = self._extract_api_info(chunk)
        if api_info:
            context_parts.append(
                f"This is an API endpoint using {api_info.get('method', '')} "
                f"method at path {api_info.get('path', '')}"
            )
        
        # Add dependency context
        deps = metadata.get("dependencies", [])
        if deps:
            context_parts.append(f"It depends on: {', '.join(deps)}")
        
        return " ".join(context_parts)