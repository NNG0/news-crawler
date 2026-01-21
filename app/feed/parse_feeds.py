from __future__ import annotations

import json
import re
import bz2
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.request import Request, urlopen
from html import unescape

import feedparser


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0"


def strip_html_tags(text: str) -> str:
    """Remove HTML tags and clean text"""
    if not text:
        return ""
    
    text = unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', ' ', text)
    text = re.sub(r'style\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'class\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    if not text:
        return []
    
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])', text)
    
    cleaned = []
    for sent in sentences:
        sent = sent.strip()
        if sent:
            cleaned.append(sent)
    
    return cleaned


def normalize_sentence(text: str) -> str:
    """Collapse whitespace and remove pipes"""
    text = " ".join(text.split())
    return text.replace("|", " ")


def should_keep(text: str) -> bool:
    """Filter sentences by length (20-256 characters)"""
    return 20 <= len(text) <= 256


@dataclass
class SentenceRecord:
    """A single sentence with metadata"""
    text: str
    url: str
    day: date
    
    def to_tuple(self) -> Tuple[str, str, str]:
        """Convert to tuple format (text, url, day_str)"""
        return (self.text, self.url, self.day.strftime("%Y%m%d"))


def load_feed_urls(path: str | Path) -> List[str]:
    """Load feed URLs from file"""
    feed_path = Path(path)
    if not feed_path.is_absolute():
        feed_path = (Path.cwd() / feed_path).resolve()
    
    lines = feed_path.read_text(encoding="utf-8").splitlines()
    urls: List[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def _fetch_bytes(url: str, *, timeout_s: int = 20) -> bytes:
    """Fetch URL content as bytes"""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def parse_feeds_to_sentences(
    feeds_file: str | Path = "data/feeds_de.txt",
    *,
    day: Optional[datetime] = None,
    verbose: bool = False,
) -> Tuple[List[SentenceRecord], List[str]]:
    """
    Parse RSS/Atom feeds and extract sentence records directly.
    
    Args:
        feeds_file: Path to file with feed URLs (one per line)
        day: Only keep items published on this day (optional)
        verbose: Print progress information
    
    Returns:
        (sentence_records, failed_feed_urls)
    """
    sources = load_feed_urls(feeds_file)
    
    if verbose:
        print(f"Loaded {len(sources)} feed URLs")
    
    target_date = day.date() if day else None
    sentences: List[SentenceRecord] = []
    failed: List[str] = []
    
    for i, url in enumerate(sources, 1):
        if verbose and i % 10 == 0:
            print(f"Processing feed {i}/{len(sources)}...")
        
        try:
            raw = _fetch_bytes(url)
            parsed = feedparser.parse(raw)
            entries = getattr(parsed, "entries", []) or []
            
            for entry in entries:
                # Get published date
                published = None
                published_parsed = getattr(entry, "published_parsed", None)
                updated_parsed = getattr(entry, "updated_parsed", None)
                
                if published_parsed:
                    published = datetime(*published_parsed[:6])
                elif updated_parsed:
                    published = datetime(*updated_parsed[:6])
                
                if not published:
                    continue
                
                # Filter by day if specified
                if target_date and published.date() != target_date:
                    continue
                
                article_url = str(getattr(entry, "link", "") or "")
                if not article_url:
                    continue
                
                article_date = published.date()
                
                # Extract and clean title
                title = str(getattr(entry, "title", "") or "")
                title = strip_html_tags(title)
                
                # Extract and clean content
                content = ""
                content_obj = getattr(entry, "content", None)
                if content_obj:
                    try:
                        content = content_obj[0].value
                    except Exception:
                        content = ""
                if not content:
                    content = str(getattr(entry, "summary", "") or "")
                
                content = strip_html_tags(content)
                
                # Split title into sentences
                if title:
                    for sent in split_into_sentences(title):
                        normalized = normalize_sentence(sent)
                        if should_keep(normalized):
                            sentences.append(SentenceRecord(
                                text=normalized,
                                url=article_url,
                                day=article_date
                            ))
                
                # Split content into sentences
                if content:
                    for sent in split_into_sentences(content):
                        normalized = normalize_sentence(sent)
                        if should_keep(normalized):
                            sentences.append(SentenceRecord(
                                text=normalized,
                                url=article_url,
                                day=article_date
                            ))
        
        except Exception as e:
            if verbose:
                print(f"Failed to fetch {url}: {e}")
            failed.append(url)
    
    if verbose:
        print(f"\nExtracted {len(sentences)} sentences from {len(sources) - len(failed)} feeds")
        print(f"Failed feeds: {len(failed)}")
    
    return sentences, failed


def write_nod_corpus(
    sentences: List[SentenceRecord],
    lang: str,
    out_root: Path = Path("out/nod"),
    verbose: bool = False,
) -> List[Path]:
    """
    Write sentences to NoDCore format: one YYYYMMDD.bz2 file per day.
    
    Args:
        sentences: List of sentence records
        lang: Language code (de, en, etc.)
        out_root: Output directory root
        verbose: Print progress information
    
    Returns:
        List of created file paths
    """
    out_dir = out_root / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Group sentences by day
    by_day = {}
    for rec in sentences:
        by_day.setdefault(rec.day, []).append(rec)
    
    if verbose:
        print(f"\nWriting to {out_dir}")
        print(f"Sentences across {len(by_day)} day(s):")
        for day in sorted(by_day.keys()):
            print(f"  {day}: {len(by_day[day])} sentences")
    
    created_files = []
    
    for day, records in by_day.items():
        filename = day.strftime("%Y%m%d") + ".bz2"
        out_path = out_dir / filename
        
        with bz2.open(out_path, "wt", encoding="utf-8") as f:
            for rec in records:
                # Format: text\turl\n
                f.write(f"{rec.text}\t{rec.url}\n")
        
        created_files.append(out_path)
        
        if verbose:
            print(f"  Wrote {out_path.name} ({len(records)} sentences)")
    
    return created_files


def store_failures(
    failed_urls: List[str],
    lang: str,
    out_root: Path = Path("out/nod"),
) -> None:
    """Store failed feed URLs to a log file"""
    if not failed_urls:
        return
    
    out_dir = out_root / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    
    failures_path = out_dir / "failures.log"
    with failures_path.open("a", encoding="utf-8") as f:
        for url in failed_urls:
            f.write(url + "\n")


def parse_and_export(
    feeds_file: str | Path = "data/feeds_de.txt",
    lang: str = "de",
    out_root: str | Path = "out/nod",
    day: Optional[datetime] = None,
    verbose: bool = False,
) -> List[Path]:
    """
    Complete pipeline: parse feeds and export to NoDCore format.
    
    Args:
        feeds_file: Path to feeds file
        lang: Language code
        out_root: Output directory
        day: Filter by day (optional)
        verbose: Print progress
    
    Returns:
        List of created .bz2 files
    """
    # Parse feeds to sentences
    sentences, failed = parse_feeds_to_sentences(
        feeds_file=feeds_file,
        day=day,
        verbose=verbose
    )
    
    # Write to NoDCore format
    created_files = write_nod_corpus(
        sentences=sentences,
        lang=lang,
        out_root=Path(out_root),
        verbose=verbose
    )
    
    # Store failures
    if failed:
        store_failures(failed, lang, Path(out_root))
        if verbose:
            print(f"\nLogged {len(failed)} failed feeds to failures.log")
    
    return created_files


if __name__ == "__main__":
    created = parse_and_export(
        feeds_file="data/feeds_de.txt",
        lang="de",
        out_root="out/nod",
        day=datetime.now(),
        verbose=True
    )
    
    print(f"\n✓ Created {len(created)} file(s)")
    
    if created:
        print(f"\nSample from {created[0].name}:")
        with bz2.open(created[0], "rt", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                parts = line.strip().split('\t')
                if len(parts) == 2:
                    text, url = parts
                    print(f"  {text[:60]}...")
                    print(f"  {url}\n")