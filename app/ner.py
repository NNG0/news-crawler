import spacy
import json
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
from tqdm import tqdm


class NERPipeline:
    """Named Entity Recognition pipeline for processing feed data"""
    
    def __init__(self, model_name: str = "de_core_news_sm", verbose: bool = True):
        """
        Initialize NER pipeline with spaCy model
        
        Args:
            model_name: spaCy model to use
                - German: 'de_core_news_sm', 'de_core_news_md', 'de_core_news_lg'
                - English: 'en_core_web_sm', 'en_core_web_md', 'en_core_web_lg'
                - Transformer (more accurate): 'de_dep_news_trf'
            verbose: Print progress information
        """
        self.model_name = model_name
        self.verbose = verbose
        self.nlp = None
        self.feeds_data = None
        self.processed_data = None
        
    def load_model(self):
        """Load spaCy model"""
        try:
            if self.verbose:
                print(f"Loading spaCy model: {self.model_name}")
            self.nlp = spacy.load(self.model_name)
            if self.verbose:
                print("Model loaded successfully")
        except OSError:
            raise OSError(
                f"Model '{self.model_name}' not found. Install with:\n"
                f"python -m spacy download {self.model_name}"
            )
    
    def load_feeds(self, feed_path: str):
        """Load feeds from JSON file"""
        feed_path = Path(feed_path)
        if not feed_path.exists():
            raise FileNotFoundError(f"Feed file not found: {feed_path}")
        
        with open(feed_path, 'r', encoding='utf-8') as json_file:
            self.feeds_data = json.load(json_file)
        
        if self.verbose:
            total_items = sum(len(feed['items']) for feed in self.feeds_data['feeds'])
            print(f"Loaded {len(self.feeds_data['feeds'])} feeds with {total_items} items")
    
    def process_text(self, text: str) -> List[Dict]:
        """
        Process a single text and extract entities
        
        Returns:
            List of entity dictionaries with text, label, start, and end positions
        """
        if not text or not text.strip():
            return []
        
        doc = self.nlp(text)
        
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            })
        
        return entities
    
    def process_feeds(self, fields: List[str] = None):
        """
        Process all feeds and extract entities
        
        Args:
            fields: List of fields to process (default: ['title', 'content'])
        """
        if not self.nlp:
            self.load_model()
        
        if not self.feeds_data:
            raise ValueError("No feeds loaded. Call load_feeds() first.")
        
        if fields is None:
            fields = ['title', 'content']
        
        # Create a copy of the feeds data to add entities to
        self.processed_data = {
            'feeds': [],
            'failed_feeds': self.feeds_data.get('failed_feeds', []),
            'timestamp': self.feeds_data.get('timestamp'),
            'total_feeds': self.feeds_data.get('total_feeds'),
            'total_items': self.feeds_data.get('total_items')
        }
        
        total_items = sum(len(feed['items']) for feed in self.feeds_data['feeds'])
        
        if self.verbose:
            print(f"\nProcessing {total_items} items...")
        
        with tqdm(total=total_items, desc="Extracting entities", disable=not self.verbose) as pbar:
            for feed in self.feeds_data['feeds']:
                processed_feed = {
                    'url': feed['url'],
                    'items': []
                }
                
                for item in feed['items']:
                    # Combine text from specified fields
                    texts = []
                    for field in fields:
                        if field in item and item[field]:
                            texts.append(item[field])
                    
                    combined_text = " ".join(texts)
                    
                    # Extract entities
                    entities = self.process_text(combined_text)
                    
                    # Add entities to item
                    processed_item = item.copy()
                    processed_item['entities'] = entities
                    
                    processed_feed['items'].append(processed_item)
                    pbar.update(1)
                
                self.processed_data['feeds'].append(processed_feed)
        
        if self.verbose:
            total_entities = self.count_total_entities()
            print(f"\nExtracted {total_entities} entities from {total_items} items")
    
    def count_total_entities(self) -> int:
        """Count total number of entities extracted"""
        if not self.processed_data:
            return 0
        
        total = 0
        for feed in self.processed_data['feeds']:
            for item in feed['items']:
                if 'entities' in item:
                    total += len(item['entities'])
        return total
    
    def get_entity_statistics(self) -> Dict[str, int]:
        """Get statistics about entity types"""
        if not self.processed_data:
            return {}
        
        entity_counts = Counter()
        
        for feed in self.processed_data['feeds']:
            for item in feed['items']:
                if 'entities' in item:
                    for entity in item['entities']:
                        entity_counts[entity['label']] += 1
        
        return dict(entity_counts)
    
    def get_top_entities(self, label: Optional[str] = None, top_n: int = 10) -> List[tuple]:
        """
        Get most common entities
        
        Args:
            label: Filter by entity label (e.g., 'PER', 'ORG', 'LOC')
            top_n: Number of top entities to return
        
        Returns:
            List of (entity_text, count) tuples
        """
        if not self.processed_data:
            return []
        
        entity_texts = []
        
        for feed in self.processed_data['feeds']:
            for item in feed['items']:
                if 'entities' in item:
                    for entity in item['entities']:
                        if label is None or entity['label'] == label:
                            entity_texts.append(entity['text'])
        
        return Counter(entity_texts).most_common(top_n)
    
    def save_results(self, output_path: str):
        """Save processed data with entities to JSON file"""
        if not self.processed_data:
            raise ValueError("No processed data to save. Call process_feeds() first.")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.processed_data, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"Results saved to: {output_path.absolute()}")
    
    def print_entity_statistics(self):
        """Print statistics about extracted entities"""
        stats = self.get_entity_statistics()
        
        if not stats:
            print("No entities found")
            return
        
        print("\n=== Entity Statistics ===")
        print(f"{'Label':<15} {'Count':>8}")
        print("-" * 25)
        
        for label, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            print(f"{label:<15} {count:>8}")
        
        print(f"\n{'Total':<15} {sum(stats.values()):>8}")
    
    def print_example_entities(self, num_items: int = 3, max_entities: int = 5):
        """Print example entities from first few items"""
        if not self.processed_data or not self.processed_data['feeds']:
            print("No data to display")
            return
        
        print(f"\n=== Example Entities (first {num_items} items) ===\n")
        
        count = 0
        for feed in self.processed_data['feeds']:
            for item in feed['items']:
                if count >= num_items:
                    return
                
                print(f"Title: {item['title']}")
                
                if 'entities' in item and item['entities']:
                    print(f"Entities ({len(item['entities'])} total):")
                    for ent in item['entities'][:max_entities]:
                        print(f"  • {ent['text']:<30} => {ent['label']}")
                    
                    if len(item['entities']) > max_entities:
                        print(f"  ... and {len(item['entities']) - max_entities} more")
                else:
                    print("  No entities found")
                
                print()
                count += 1


def pipeline(feed_path: str = 'news-crawler/app/data/feeds_output.json',
             model: str = "de_core_news_sm",
             output_path: str = 'news-crawler/app/data/feeds_with_ner.json'):
    """
    Main NER pipeline
    
    Args:
        feed_path: Path to input JSON file from feedreader
        model: spaCy model to use for NER
        output_path: Path to save results
    """
    # Initialize pipeline
    ner = NERPipeline(model_name=model, verbose=True)
    
    # Load feeds
    ner.load_feeds(feed_path)
    
    # Process feeds and extract entities
    ner.process_feeds(fields=['title', 'content'])
    
    # Print statistics
    ner.print_entity_statistics()
    
    # Print examples
    ner.print_example_entities(num_items=3)
    
    # Show top entities by type
    print("\n=== Top 10 Persons (PER) ===")
    for entity, count in ner.get_top_entities(label='PER', top_n=10):
        print(f"  {entity:<30} ({count})")
    
    print("\n=== Top 10 Organizations (ORG) ===")
    for entity, count in ner.get_top_entities(label='ORG', top_n=10):
        print(f"  {entity:<30} ({count})")
    
    print("\n=== Top 10 Locations (LOC) ===")
    for entity, count in ner.get_top_entities(label='LOC', top_n=10):
        print(f"  {entity:<30} ({count})")
    
    # Save results
    ner.save_results(output_path)
    
    return ner


if __name__ == "__main__":
    # Run pipeline with German model
    ner = pipeline(
        feed_path='news-crawler/app/data/feeds_output.json',
        model='de_core_news_sm',
        output_path='news-crawler/app/data/feeds_with_ner.json'
    )