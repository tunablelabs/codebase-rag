from typing import Any, Dict, List, Set, Optional, Tuple, TypeVar, Generic
from dataclasses import dataclass
from collections import defaultdict
import networkx as nx
from pathlib import Path
import logging

from .schemas import BaseEntity, Function, Class, APIEndpoint, APIRouter, DependencyNode, DependencyEdge


class CodeRelationshipAnalyzer:
    """Analyzes code relationships with enhanced tracking and vector DB support."""
    
    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.module_graph = nx.DiGraph()
        self._nodes: Dict[str, DependencyNode] = {}
        self._import_cache: Dict[str, Set[str]] = {}
        self._chunk_cache: Dict[str, Dict] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # New: Track relationship types for vector DB
        self.relationship_types = {
            'calls': 'function call dependency',
            'inherits': 'class inheritance',
            'implements': 'interface implementation',
            'uses': 'variable usage',
            'defines': 'entity definition',
            'contains': 'scope containment',
            'imports': 'module import',
            'overrides': 'method override'
        }
        
        # New: Relationship strength tracking
        self.relationship_strengths: Dict[Tuple[str, str], float] = {}
        
        # New: Semantic relationship cache
        self.semantic_relationships: Dict[str, Dict[str, List[str]]] = {}
        
    def _find_highly_coupled_entities(self) -> List[Dict]:
        """
        Find entities with high coupling.
        
        Returns:
            List of dictionaries containing highly coupled entity information
        """
        try:
            threshold = 5  # Configurable threshold for "highly coupled"
            highly_coupled = []
            
            for node_id in self.dependency_graph.nodes():
                coupling_score = self._calculate_coupling_score(node_id)
                if coupling_score > threshold:
                    if node_id in self._nodes:
                        node = self._nodes[node_id]
                        highly_coupled.append({
                            'entity': node.name,
                            'type': node.type,
                            'coupling_score': coupling_score,
                            'dependencies': len(list(self.dependency_graph.successors(node_id))),
                            'dependents': len(list(self.dependency_graph.predecessors(node_id))),
                            'path': node.path
                        })
            
            # Sort by coupling score in descending order
            return sorted(highly_coupled, key=lambda x: x['coupling_score'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding highly coupled entities: {e}")
            return []

    def _calculate_coupling_score(self, node_id: str) -> float:
        """
        Calculate coupling score for a node.
        
        Args:
            node_id: Node identifier
        
        Returns:
            Coupling score
        """
        try:
            # Get incoming and outgoing dependencies
            in_degree = self.dependency_graph.in_degree(node_id)
            out_degree = self.dependency_graph.out_degree(node_id)
            
            # Basic coupling score is average of in and out degrees
            base_score = (in_degree + out_degree) / 2
            
            # Adjust score based on relationship types
            relationship_weight = 0
            for _, _, data in self.dependency_graph.edges(node_id, data=True):
                rel_type = data.get('type', 'unknown')
                weight = {
                    'inherits': 2.0,  # Inheritance coupling is weighted more
                    'implements': 1.5,
                    'uses': 1.0,
                    'calls': 0.8,
                    'imports': 0.5
                }.get(rel_type, 1.0)
                relationship_weight += weight
                
            return base_score * (1 + (relationship_weight / 10))  # Adjust based on relationship types
            
        except Exception as e:
            self.logger.warning(f"Error calculating coupling score: {e}")
            return 0.0

    def _generate_module_stats(self) -> Dict:
        """Generate statistics about module dependencies."""
        try:
            return {
                'total_modules': self.module_graph.number_of_nodes(),
                'module_dependencies': self.module_graph.number_of_edges(),
                'isolated_modules': list(nx.isolates(self.module_graph)),
                'strongly_connected_components': list(nx.strongly_connected_components(self.module_graph)),
                'average_dependencies': (self.module_graph.number_of_edges() / 
                                    self.module_graph.number_of_nodes() 
                                    if self.module_graph.number_of_nodes() > 0 else 0)
            }
        except Exception as e:
            self.logger.error(f"Error generating module stats: {e}")
            return {
                'total_modules': 0,
                'module_dependencies': 0,
                'isolated_modules': [],
                'strongly_connected_components': [],
                'average_dependencies': 0
            }

    def _count_dependency_types(self) -> Dict[str, int]:
        """Count occurrences of each dependency type."""
        try:
            counts = defaultdict(int)
            for _, _, data in self.dependency_graph.edges(data=True):
                rel_type = data.get('type', 'unknown')
                counts[rel_type] += 1
            return dict(counts)
        except Exception as e:
            self.logger.error(f"Error counting dependency types: {e}")
            return {}

    def _generate_chunk_stats(self) -> Dict:
        """Generate statistics about chunk dependencies."""
        try:
            stats = {
                'total_chunks': len(set(node.chunk_id for node in self._nodes.values() if node.chunk_id)),
                'cross_chunk_dependencies': 0,
                'internal_dependencies': 0,
                'isolated_chunks': set(),
                'highly_connected_chunks': []
            }
            
            # Count dependencies
            for _, _, data in self.dependency_graph.edges(data=True):
                source_chunk = data.get('source_chunk')
                target_chunk = data.get('target_chunk')
                if source_chunk and target_chunk:
                    if source_chunk != target_chunk:
                        stats['cross_chunk_dependencies'] += 1
                    else:
                        stats['internal_dependencies'] += 1
            
            # Find isolated and highly connected chunks
            chunk_connections = defaultdict(int)
            for _, _, data in self.dependency_graph.edges(data=True):
                source_chunk = data.get('source_chunk')
                target_chunk = data.get('target_chunk')
                if source_chunk and target_chunk:
                    chunk_connections[source_chunk] += 1
                    chunk_connections[target_chunk] += 1
            
            stats['isolated_chunks'] = {
                chunk_id for chunk_id, count in chunk_connections.items()
                if count == 0
            }
            
            stats['highly_connected_chunks'] = [
                {'chunk_id': chunk_id, 'connections': count}
                for chunk_id, count in chunk_connections.items()
                if count > 5  # Threshold for "highly connected"
            ]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to generate chunk stats: {e}")
            return {
                'total_chunks': 0,
                'cross_chunk_dependencies': 0,
                'internal_dependencies': 0,
                'isolated_chunks': set(),
                'highly_connected_chunks': []
            }
            
    def find_cycles(self) -> List[List[str]]:
        """
        Find circular dependencies in the codebase.
        
        Returns:
            List of lists containing node IDs that form cycles
        """
        try:
            import networkx as nx
            
            # Find all simple cycles in the dependency graph
            cycles = list(nx.simple_cycles(self.dependency_graph))
            
            # Convert node IDs in cycles to readable names
            readable_cycles = []
            for cycle in cycles:
                cycle_names = []
                for node_id in cycle:
                    if node_id in self._nodes:
                        node = self._nodes[node_id]
                        cycle_names.append({
                            'id': node_id,
                            'name': node.name,
                            'type': node.type,
                            'path': node.path
                        })
                if cycle_names:
                    readable_cycles.append(cycle_names)
            
            # Log found cycles
            if readable_cycles:
                self.logger.warning(f"Found {len(readable_cycles)} dependency cycles")
                for cycle in readable_cycles:
                    cycle_str = ' -> '.join(node['name'] for node in cycle)
                    self.logger.warning(f"Cycle: {cycle_str}")
            
            return readable_cycles
            
        except Exception as e:
            self.logger.error(f"Error finding cycles: {e}")
            return []

    def analyze_entities(self, entities: Dict[str, List[BaseEntity]], chunk_id: Optional[str] = None) -> None:
        """
        Analyze relationships with enhanced tracking.
        
        Args:
            entities: Dictionary of entities by type
            chunk_id: Optional chunk identifier
        """
        try:
            # Group by chunks if chunk_id provided
            if chunk_id:
                chunks = {chunk_id: entities}
            else:
                chunks = self._group_by_chunks(entities)
            
            # First pass: Analyze within chunks
            for chunk_id, chunk_entities in chunks.items():
                self._analyze_chunk_entities(chunk_id, chunk_entities)
                
            # Second pass: Analyze cross-chunk relationships
            self._analyze_cross_chunk_relationships(chunks)
            
            # Generate semantic relationships
            self._generate_semantic_relationships(chunks)
            
        except Exception as e:
            self.logger.error(f"Entity analysis failed: {e}")
            raise
        
    def get_file_relationships(self, file_path: str) -> Dict[str, Any]:
        """
        Get relationships for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing relationship information
        """
        try:
            relationships = {
                'dependencies': [],
                'dependents': [],
                'internal_relationships': [],
                'external_relationships': []
            }
            
            # Get all nodes for this file
            file_nodes = [
                node for node in self._nodes.values()
                if node.path == file_path
            ]
            
            for node in file_nodes:
                # Get dependencies (outgoing edges)
                deps = self.get_dependencies(node.id)
                for dep in deps:
                    if dep.path == file_path:
                        relationships['internal_relationships'].append({
                            'source': node.name,
                            'target': dep.name,
                            'type': self.dependency_graph.edges[node.id, dep.id].get('type', 'unknown')
                        })
                    else:
                        relationships['dependencies'].append({
                            'source': node.name,
                            'target': dep.name,
                            'file': dep.path,
                            'type': self.dependency_graph.edges[node.id, dep.id].get('type', 'unknown')
                        })
                
                # Get dependents (incoming edges)
                deps = self.get_dependents(node.id)
                for dep in deps:
                    if dep.path != file_path:
                        relationships['dependents'].append({
                            'source': dep.name,
                            'target': node.name,
                            'file': dep.path,
                            'type': self.dependency_graph.edges[dep.id, node.id].get('type', 'unknown')
                        })
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error getting file relationships for {file_path}: {e}")
            return {
                'dependencies': [],
                'dependents': [],
                'internal_relationships': [],
                'external_relationships': []
            }

    def _generate_semantic_relationships(self, chunks: Dict[str, Dict[str, List[BaseEntity]]]) -> None:
        """Generate natural language descriptions of relationships."""
        try:
            for chunk_id, entities in chunks.items():
                chunk_relationships = {
                    'dependencies': [],
                    'provides': [],
                    'extends': [],
                    'uses': []
                }
                
                for entity_type, entity_list in entities.items():
                    for entity in entity_list:
                        desc = self._generate_entity_relationship_description(entity)
                        if desc:
                            for key, value in desc.items():
                                chunk_relationships[key].extend(value)
                                
                self.semantic_relationships[chunk_id] = chunk_relationships
                
        except Exception as e:
            self.logger.warning(f"Error generating semantic relationships: {e}")

    def _generate_entity_relationship_description(self, entity: BaseEntity) -> Dict[str, List[str]]:
        """Generate semantic descriptions of entity relationships."""
        descriptions = {
            'dependencies': [],
            'provides': [],
            'extends': [],
            'uses': []
        }
        
        try:
            entity_type = type(entity).__name__
            
            if isinstance(entity, Function):
                if entity.called_functions:
                    descriptions['dependencies'].append(
                        f"Function '{entity.name}' calls: {', '.join(entity.called_functions)}"
                    )
                if entity.raises:
                    descriptions['uses'].append(
                        f"Function '{entity.name}' may raise: {', '.join(entity.raises)}"
                    )
                    
            elif isinstance(entity, Class):
                if entity.base_classes:
                    descriptions['extends'].append(
                        f"Class '{entity.name}' extends: {', '.join(entity.base_classes)}"
                    )
                if entity.interfaces:
                    descriptions['implements'].append(
                        f"Class '{entity.name}' implements: {', '.join(entity.interfaces)}"
                    )
                    
            elif isinstance(entity, APIEndpoint):
                descriptions['provides'].append(
                    f"API endpoint '{entity.path}' handled by: {entity.handler.name}"
                )
                
        except Exception as e:
            self.logger.warning(f"Error generating relationship description: {e}")
            
        return descriptions

    def get_chunk_relationships(self, chunk_id: str) -> Dict[str, Any]:
        """Get comprehensive relationship information for a chunk."""
        try:
            relationships = {
                'dependencies': [],
                'dependents': [],
                'semantic_descriptions': self.semantic_relationships.get(chunk_id, {}),
                'relationship_strengths': {}
            }
            
            # Get direct dependencies
            for _, target, data in self.dependency_graph.out_edges(chunk_id, data=True):
                rel_type = data.get('type', 'unknown')
                relationships['dependencies'].append({
                    'target': target,
                    'type': rel_type,
                    'description': self.relationship_types.get(rel_type, ''),
                    'strength': self.relationship_strengths.get((chunk_id, target), 0.0)
                })
            
            # Get dependents
            for source, _, data in self.dependency_graph.in_edges(chunk_id, data=True):
                rel_type = data.get('type', 'unknown')
                relationships['dependents'].append({
                    'source': source,
                    'type': rel_type,
                    'description': self.relationship_types.get(rel_type, ''),
                    'strength': self.relationship_strengths.get((source, chunk_id), 0.0)
                })
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error getting chunk relationships: {e}")
            return {}

    def _calculate_relationship_strength(
        self,
        source: str,
        target: str,
        rel_type: str,
        metadata: Optional[Dict] = None
    ) -> float:
        """Calculate relationship strength based on type and usage."""
        try:
            base_strength = {
                'inherits': 1.0,
                'implements': 0.8,
                'calls': 0.6,
                'uses': 0.4,
                'imports': 0.3
            }.get(rel_type, 0.5)
            
            # Adjust based on metadata
            if metadata:
                # Increase strength for multiple calls
                if rel_type == 'calls' and metadata.get('call_count', 0) > 1:
                    base_strength *= min(2.0, 1.0 + (metadata['call_count'] - 1) * 0.1)
                    
                # Increase for direct dependencies
                if metadata.get('is_direct', False):
                    base_strength *= 1.2
                    
                # Adjust for scope
                if metadata.get('scope') == 'local':
                    base_strength *= 1.1
                    
            return min(1.0, base_strength)
            
        except Exception as e:
            self.logger.warning(f"Error calculating relationship strength: {e}")
            return 0.5

    def generate_dependency_report(self) -> Dict:
        """Generate comprehensive dependency report with semantic information."""
        try:
            report = {
                'statistics': {
                    'total_entities': len(self._nodes),
                    'total_dependencies': self.dependency_graph.number_of_edges(),
                    'total_modules': self.module_graph.number_of_nodes()
                },
                'relationships': {
                    'cyclic_dependencies': self.find_cycles(),
                    'highly_coupled_entities': self._find_highly_coupled_entities(),
                    'semantic_relationships': self.semantic_relationships
                },
                'modules': {
                    'stats': self._generate_module_stats(),
                    'dependencies': self._count_dependency_types()
                },
                'chunks': self._generate_chunk_stats()
            }
            
            # Add natural language summary
            report['summary'] = self._generate_report_summary(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            return {}

    def _generate_report_summary(self, report: Dict) -> str:
        """Generate natural language summary of the dependency report."""
        try:
            parts = []
            
            # Overall statistics
            stats = report['statistics']
            parts.append(
                f"Analysis found {stats['total_entities']} entities with "
                f"{stats['total_dependencies']} dependencies across "
                f"{stats['total_modules']} modules."
            )
            
            # Significant findings
            cycles = len(report['relationships']['cyclic_dependencies'])
            if cycles:
                parts.append(f"Detected {cycles} cyclic dependencies that might need attention.")
                
            highly_coupled = len(report['relationships']['highly_coupled_entities'])
            if highly_coupled:
                parts.append(
                    f"Found {highly_coupled} highly coupled entities that "
                    "might benefit from refactoring."
                )
            
            # Module information
            module_stats = report['modules']['stats']
            isolated_modules = len(module_stats['isolated_modules'])
            if isolated_modules:
                parts.append(f"Found {isolated_modules} isolated modules.")
                
            return " ".join(parts)
            
        except Exception as e:
            self.logger.warning(f"Error generating report summary: {e}")
            return "Error generating summary"

    def clear_cache(self) -> None:
        """Clear all caches and reset state."""
        self._import_cache.clear()
        self._chunk_cache.clear()
        self.semantic_relationships.clear()
        self.relationship_strengths.clear()
        self.logger.debug("Cleared analyzer caches")