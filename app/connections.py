import json
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from itertools import combinations


@dataclass
class Entity:
    """Represents an entity with its label"""
    text: str
    label: str
    
    def __hash__(self):
        return hash((self.text.lower(), self.label))
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.text.lower() == other.text.lower() and self.label == other.label
    
    def to_dict(self):
        return {'text': self.text, 'label': self.label}


@dataclass
class Connection:
    """Represents a connection between two entities"""
    entity1: Entity
    entity2: Entity
    weight: int  # Number of co-occurrences
    articles: List[str]  # URLs where they co-occur
    
    def to_dict(self):
        return {
            'entity1': self.entity1.to_dict(),
            'entity2': self.entity2.to_dict(),
            'weight': self.weight,
            'articles': self.articles
        }


class EntityConnectionGraph:
    """Build and analyze entity co-occurrence networks"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.feeds_data = None
        self.entities: Set[Entity] = set()
        self.connections: Dict[Tuple[Entity, Entity], Connection] = {}
        self.entity_article_map: Dict[Entity, List[str]] = defaultdict(list)
        
    def load_ner_results(self, ner_path: str):
        """Load NER results from JSON file"""
        ner_path = Path(ner_path)
        if not ner_path.exists():
            raise FileNotFoundError(f"NER file not found: {ner_path}")
        
        with open(ner_path, 'r', encoding='utf-8') as f:
            self.feeds_data = json.load(f)
        
        if self.verbose:
            total_items = sum(len(feed['items']) for feed in self.feeds_data['feeds'])
            print(f"Loaded {len(self.feeds_data['feeds'])} feeds with {total_items} items")
    
    def build_graph(self, min_weight: int = 1, entity_types: Optional[List[str]] = None):
        """
        Build entity co-occurrence graph
        
        Args:
            min_weight: Minimum number of co-occurrences to create a connection
            entity_types: Filter by entity types (e.g., ['PER', 'ORG']). None = all types
        """
        if not self.feeds_data:
            raise ValueError("No data loaded. Call load_ner_results() first.")
        
        if self.verbose:
            print("\nBuilding entity connection graph...")
        
        # Process each article
        for feed in self.feeds_data['feeds']:
            for item in feed['items']:
                if 'entities' not in item or not item['entities']:
                    continue
                
                article_url = item.get('url', 'unknown')
                
                # Extract entities from this article
                article_entities = set()
                for ent_data in item['entities']:
                    # Filter by entity type if specified
                    if entity_types and ent_data['label'] not in entity_types:
                        continue
                    
                    entity = Entity(text=ent_data['text'], label=ent_data['label'])
                    article_entities.add(entity)
                    
                    # Track which articles each entity appears in
                    self.entity_article_map[entity].append(article_url)
                
                # Add all entities to the global set
                self.entities.update(article_entities)
                
                # Create connections between all pairs of entities in this article
                for entity1, entity2 in combinations(sorted(article_entities, key=lambda e: e.text), 2):
                    # Create ordered pair (alphabetically) to avoid duplicates
                    pair = (entity1, entity2) if entity1.text < entity2.text else (entity2, entity1)
                    
                    if pair in self.connections:
                        # Increment existing connection
                        self.connections[pair].weight += 1
                        if article_url not in self.connections[pair].articles:
                            self.connections[pair].articles.append(article_url)
                    else:
                        # Create new connection
                        self.connections[pair] = Connection(
                            entity1=pair[0],
                            entity2=pair[1],
                            weight=1,
                            articles=[article_url]
                        )
        
        # Filter by minimum weight
        if min_weight > 1:
            self.connections = {
                pair: conn for pair, conn in self.connections.items() 
                if conn.weight >= min_weight
            }
        
        if self.verbose:
            print(f"Found {len(self.entities)} unique entities")
            print(f"Created {len(self.connections)} connections (min_weight={min_weight})")
    
    def get_entity_connections(self, entity_text: str, top_n: int = 10) -> List[Connection]:
        """
        Get top connections for a specific entity
        
        Args:
            entity_text: The entity text to search for
            top_n: Number of top connections to return
        
        Returns:
            List of Connection objects sorted by weight
        """
        entity_text_lower = entity_text.lower()
        related_connections = []
        
        for conn in self.connections.values():
            if (conn.entity1.text.lower() == entity_text_lower or 
                conn.entity2.text.lower() == entity_text_lower):
                related_connections.append(conn)
        
        # Sort by weight (descending)
        related_connections.sort(key=lambda c: c.weight, reverse=True)
        
        return related_connections[:top_n]
    
    def get_top_connections(self, top_n: int = 20) -> List[Connection]:
        """Get the strongest connections overall"""
        sorted_connections = sorted(
            self.connections.values(), 
            key=lambda c: c.weight, 
            reverse=True
        )
        return sorted_connections[:top_n]
    
    def get_entity_degree(self, entity_text: str) -> int:
        """Get the number of connections an entity has (degree centrality)"""
        entity_text_lower = entity_text.lower()
        degree = 0
        
        for conn in self.connections.values():
            if (conn.entity1.text.lower() == entity_text_lower or 
                conn.entity2.text.lower() == entity_text_lower):
                degree += 1
        
        return degree
    
    def get_most_connected_entities(self, top_n: int = 10) -> List[Tuple[Entity, int]]:
        """Get entities with the most connections"""
        entity_degrees = {}
        
        for entity in self.entities:
            degree = self.get_entity_degree(entity.text)
            if degree > 0:
                entity_degrees[entity] = degree
        
        sorted_entities = sorted(
            entity_degrees.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return sorted_entities[:top_n]
    
    def export_to_json(self, output_path: str):
        """Export graph to JSON format"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to JSON-serializable format
        graph_data = {
            'entities': [
                {
                    'text': e.text,
                    'label': e.label,
                    'article_count': len(self.entity_article_map[e]),
                    'connection_count': self.get_entity_degree(e.text)
                }
                for e in self.entities
            ],
            'connections': [
                conn.to_dict() for conn in self.connections.values()
            ],
            'statistics': {
                'total_entities': len(self.entities),
                'total_connections': len(self.connections),
                'avg_connections_per_entity': len(self.connections) * 2 / len(self.entities) if self.entities else 0
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"Graph exported to: {output_path.absolute()}")
    
    def export_to_networkx_format(self, output_path: str):
        """Export graph in format suitable for NetworkX/visualization"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create nodes list
        nodes = [
            {
                'id': i,
                'text': e.text,
                'label': e.label,
                'size': len(self.entity_article_map[e])
            }
            for i, e in enumerate(self.entities)
        ]
        
        # Create entity to ID mapping
        entity_to_id = {e: i for i, e in enumerate(self.entities)}
        
        # Create edges list
        edges = [
            {
                'source': entity_to_id[conn.entity1],
                'target': entity_to_id[conn.entity2],
                'weight': conn.weight
            }
            for conn in self.connections.values()
        ]
        
        graph_data = {
            'nodes': nodes,
            'edges': edges
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"NetworkX format exported to: {output_path.absolute()}")
    
    def print_statistics(self):
        """Print graph statistics"""
        if not self.entities:
            print("No graph data available")
            return
        
        print("\n=== Entity Connection Graph Statistics ===")
        print(f"Total unique entities: {len(self.entities)}")
        print(f"Total connections: {len(self.connections)}")
        
        if self.entities:
            avg_connections = len(self.connections) * 2 / len(self.entities)
            print(f"Average connections per entity: {avg_connections:.2f}")
        
        # Entity type distribution
        entity_type_counts = Counter(e.label for e in self.entities)
        print("\nEntity type distribution:")
        for label, count in sorted(entity_type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {label}: {count}")
        
        # Connection strength distribution
        if self.connections:
            weights = [c.weight for c in self.connections.values()]
            print(f"\nConnection weights:")
            print(f"  Min: {min(weights)}")
            print(f"  Max: {max(weights)}")
            print(f"  Average: {sum(weights) / len(weights):.2f}")
    
    def print_top_connections(self, top_n: int = 10):
        """Print the strongest connections"""
        top_conns = self.get_top_connections(top_n)
        
        print(f"\n=== Top {top_n} Entity Connections ===")
        for i, conn in enumerate(top_conns, 1):
            print(f"\n{i}. {conn.entity1.text} ({conn.entity1.label}) <--> "
                  f"{conn.entity2.text} ({conn.entity2.label})")
            print(f"   Co-occurrences: {conn.weight}")
            print(f"   Articles: {len(conn.articles)}")
    
    def print_most_connected_entities(self, top_n: int = 10):
        """Print entities with most connections"""
        top_entities = self.get_most_connected_entities(top_n)
        
        print(f"\n=== Top {top_n} Most Connected Entities ===")
        for i, (entity, degree) in enumerate(top_entities, 1):
            article_count = len(self.entity_article_map[entity])
            print(f"{i}. {entity.text} ({entity.label})")
            print(f"   Connections: {degree} | Articles: {article_count}")


def pipeline(ner_path: str = 'news-crawler/app/data/feeds_with_ner.json',
             output_path: str = 'news-crawler/app/data/entity_graph.json',
             networkx_path: str = 'news-crawler/app/data/entity_graph_nx.json',
             min_weight: int = 2,
             entity_types: Optional[List[str]] = None):
    """
    Main connections pipeline
    
    Args:
        ner_path: Path to NER results JSON
        output_path: Path to save graph JSON
        networkx_path: Path to save NetworkX-compatible format
        min_weight: Minimum co-occurrences to create connection
        entity_types: Filter by entity types (e.g., ['PER', 'ORG'])
    """
    # Initialize graph builder
    graph = EntityConnectionGraph(verbose=True)
    
    # Load NER results
    graph.load_ner_results(ner_path)
    
    # Build the graph
    graph.build_graph(min_weight=min_weight, entity_types=entity_types)
    
    if graph.verbose :
        graph.print_statistics()
        graph.print_top_connections(top_n=10)
        graph.print_most_connected_entities(top_n=10)
    
    # Export results
    graph.export_to_json(output_path)
    graph.export_to_networkx_format(networkx_path)
    
    return graph


if __name__ == "__main__":
    graph = pipeline(
        ner_path='news-crawler/app/data/feeds_with_ner.json',
        output_path='news-crawler/app/data/entity_graph.json',
        networkx_path='news-crawler/app/data/entity_graph_nx.json',
        min_weight=2,  # At least 2 co-occurrences
        entity_types=None  # All entity types
    )