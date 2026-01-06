import feedparser


import json
import logging
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0"


@dataclass
class FeedItem:
    """Stores info of feed entry"""
    title: str
    content: str
    url: str
    published: datetime
    guid: str

    def validate(self) -> None:
        """Validate feed item data"""
        if not self.url:
            raise ValueError(f"Feed item contains no url: {self}")
        if not self.guid:
            self.guid = self.url

    def to_dict(self):
        """Convert to dictionary with datetime as ISO string"""
        d = asdict(self)
        d['published'] = self.published.isoformat()
        return d


@dataclass
class Feed:
    """Represent an RSS/Atom feed"""
    url: str
    items: List[FeedItem]

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'url': self.url,
            'items': [item.to_dict() for item in self.items]
        }


class FeedReader:
    """RSS/Atom feed reader with concurrent fetching"""

    def __init__(self, feeds_file: str, verbose: bool = False):
        self.sources: List[str] = []
        self.feeds: List[Feed] = []
        self.failed_feeds: List[str] = []
        self.day: Optional[datetime] = None
        self.verbose = verbose
        self._load_sources(feeds_file)

    def _load_sources(self, feeds_file: str) -> None:
        """Load feed URLs from file"""
        try:
            feed_path = Path(feeds_file)
            
            # If path is not absolute, resolve relative to current working directory
            if not feed_path.is_absolute():
                feed_path = Path.cwd() / feed_path
            
            feed_path = feed_path.resolve()
            
            if not feed_path.exists():
                raise FileNotFoundError(f"Feeds file not found: {feed_path}")
            
            with open(feed_path, 'r') as f:
                self.sources = [line.strip() for line in f if line.strip()]
                
            if self.verbose:
                logging.info(f"Loaded {len(self.sources)} feed sources from {feed_path}")
                
        except Exception as e:
            raise Exception(f"Failed to load feeds file: {e}")

    def fetch(self, concurrency_limit: int = 100) -> None:
        """Fetch feed items concurrently"""
        feeds = []
        failed_feeds = []

        with ThreadPoolExecutor(max_workers=concurrency_limit) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self._fetch_feed, url): url 
                for url in self.sources
            }

            # Process completed tasks with progress bar
            with tqdm(total=len(self.sources), desc="Fetching feeds") as pbar:
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        items = future.result()
                        if items is not None:
                            feeds.append(Feed(url=url, items=items))
                        else:
                            failed_feeds.append(url)
                    except Exception as e:
                        if self.verbose:
                            logging.error(f"Failed to fetch feed {url}: {e}")
                        failed_feeds.append(url)
                    pbar.update(1)

        self.feeds = feeds
        self.failed_feeds = failed_feeds

    def fetch_serial(self) -> None:
        """Fetch feed items serially (for debugging)"""
        for url in self.sources:
            try:
                items = self._fetch_feed(url)
                if items is not None:
                    self.feeds.append(Feed(url=url, items=items))
                else:
                    self.failed_feeds.append(url)
            except Exception as e:
                if self.verbose:
                    logging.error(f"Failed to fetch feed {url}: {e}")
                self.failed_feeds.append(url)

    def _fetch_feed(self, url: str) -> Optional[List[FeedItem]]:
        """Fetch and parse a single feed"""
        try:
            # Set up session with custom user agent
            session = requests.Session()
            session.headers.update({'User-Agent': USER_AGENT})
            
            # Fetch feed with timeout
            response = session.get(url, timeout=20)
            response.raise_for_status()
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            if not feed.entries:
                return []

            # Filter items by day if specified
            items = []
            day_filter = None
            if self.day:
                # Use date() for comparison to avoid time zone issues
                day_filter = self.day.date()

            for entry in feed.entries:
                # Get published date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                
                if not published:
                    continue

                # Filter by day if specified (compare dates only, ignore time)
                if day_filter and published.date() != day_filter:
                    continue

                # Extract content
                content = ""
                if hasattr(entry, 'content') and entry.content:
                    content = entry.content[0].value
                elif hasattr(entry, 'summary'):
                    content = entry.summary

                # Create feed item
                item = FeedItem(
                    title=entry.get('title', ''),
                    content=content,
                    url=entry.get('link', ''),
                    published=published,
                    guid=entry.get('id', '')
                )

                # Validate and add
                try:
                    item.validate()
                    items.append(item)
                except ValueError:
                    continue

            return items

        except Exception as e:
            if self.verbose:
                logging.error(f"Error fetching {url}: {e}")
            return None


if __name__ == "__main__":
   
    reader = FeedReader("news-crawler/app/data/feeds_de.txt", verbose=True)
    reader.day = datetime.now()
    reader.fetch()
    
    print(f"\nSuccessfully fetched: {len(reader.feeds)} feeds")
    print(f"Failed feeds: {len(reader.failed_feeds)}")
    
    output = {
        'feeds': [feed.to_dict() for feed in reader.feeds],
        'failed_feeds': reader.failed_feeds
    }
    
    with open('news-crawler/app/data/feeds_output.json', 'w') as f:
        json.dump(output, f, indent=2)
