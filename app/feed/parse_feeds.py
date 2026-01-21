from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.request import Request, urlopen

import feedparser


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0"


@dataclass
class FeedItem:
    title: str
    content: str
    url: str
    published: datetime
    guid: str

    def validate(self) -> None:
        if not self.url:
            raise ValueError("missing url")
        if not self.guid:
            self.guid = self.url

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published"] = self.published.isoformat()
        return d


@dataclass
class Feed:
    url: str
    items: List[FeedItem]

    def to_dict(self) -> dict:
        return {"url": self.url, "items": [item.to_dict() for item in self.items]}


def load_feed_urls(path: str | Path) -> List[str]:
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


def _format_day_go_style(day: datetime) -> str:
    # Go uses time.Format("2-1-2006") -> no leading zeros for day/month.
    return f"{day.day}-{day.month}-{day.year}"


def _fetch_bytes(url: str, *, timeout_s: int = 20) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def parse_feeds(
    feeds_file: str | Path = "data/feeds_de.txt",
    *,
    day: Optional[datetime] = None,
) -> tuple[List[Feed], List[str]]:
    """
    Parse RSS/Atom feeds from a file (one URL per line).

    Returns: (feeds, failed_feed_urls)
    - If `day` is provided, keeps only items published on that day (by date).
    """
    sources = load_feed_urls(feeds_file)

    target_date = day.date() if day else None
    feeds: List[Feed] = []
    failed: List[str] = []

    for url in sources:
        try:
            raw = _fetch_bytes(url)
            parsed = feedparser.parse(raw)
            entries = getattr(parsed, "entries", []) or []
            items: List[FeedItem] = []

            for entry in entries:
                published = None
                published_parsed = getattr(entry, "published_parsed", None)
                updated_parsed = getattr(entry, "updated_parsed", None)
                if published_parsed:
                    published = datetime(*published_parsed[:6])
                elif updated_parsed:
                    published = datetime(*updated_parsed[:6])
                if not published:
                    continue

                if target_date and published.date() != target_date:
                    continue

                content = ""
                content_obj = getattr(entry, "content", None)
                if content_obj:
                    try:
                        content = content_obj[0].value
                    except Exception:
                        content = ""
                if not content:
                    content = str(getattr(entry, "summary", "") or "")

                item = FeedItem(
                    title=str(getattr(entry, "title", "") or ""),
                    content=content,
                    url=str(getattr(entry, "link", "") or ""),
                    published=published,
                    guid=str(getattr(entry, "id", "") or ""),
                )
                try:
                    item.validate()
                except ValueError:
                    continue
                items.append(item)

            feeds.append(Feed(url=url, items=items))
        except Exception:
            failed.append(url)

    return feeds, failed


def store_feeds(
    feeds: Iterable[Feed],
    *,
    lang: str,
    day: datetime,
    out_dir: str | Path = "out/feeds",
    failures: Optional[Iterable[str]] = None,
) -> Path:
    """
    Store feeds in the same overall shape as the Go crawler:
    a JSON list of {"url": ..., "items": [...]}.
    """
    out_root = Path(out_dir) / lang
    out_root.mkdir(parents=True, exist_ok=True)

    out_path = out_root / f"{_format_day_go_style(day)}.json"
    out_path.write_text(
        json.dumps([f.to_dict() for f in feeds], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if failures:
        failures_path = out_root / "failures.log"
        with failures_path.open("a", encoding="utf-8") as f:
            for url in failures:
                f.write(url + "\n")

    return out_path
