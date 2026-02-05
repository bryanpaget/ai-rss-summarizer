"""RSS feed fetching and parsing."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from time import mktime

import feedparser

from .storage import Article, Storage


def load_feeds(feeds_file: str = "config/feeds.txt") -> list[str]:
    """Load feed URLs from a file."""
    feeds_path = Path(feeds_file)
    if not feeds_path.exists():
        return []

    feeds = []
    with open(feeds_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                feeds.append(line)
    return feeds


def generate_article_id(link: str) -> str:
    """Generate a unique ID for an article based on its link."""
    return hashlib.sha256(link.encode()).hexdigest()[:16]


def parse_published_date(entry: dict) -> Optional[datetime]:
    """Parse the published date from a feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime.fromtimestamp(mktime(entry.published_parsed))
        except (ValueError, OverflowError) as e:
            import sys
            entry_title = getattr(entry, 'title', 'unknown')[:30]
            print(f"Date parsing failed for '{entry_title}': {e}", file=sys.stderr)

    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime.fromtimestamp(mktime(entry.updated_parsed))
        except (ValueError, OverflowError) as e:
            import sys
            entry_title = getattr(entry, 'title', 'unknown')[:30]
            print(f"Date parsing failed for '{entry_title}': {e}", file=sys.stderr)

    return None


def get_entry_content(entry: dict) -> str:
    """Extract the best available content from a feed entry."""
    # Try content field first (often has full article)
    if hasattr(entry, "content") and entry.content:
        return entry.content[0].get("value", "")

    # Fall back to summary
    if hasattr(entry, "summary") and entry.summary:
        return entry.summary

    # Last resort: title
    return entry.get("title", "")


def fetch_feed(feed_url: str, storage: Storage) -> dict:
    """
    Fetch and parse a single RSS feed.
    Returns statistics about the fetch operation, including IDs of newly saved articles.
    """
    stats = {"url": feed_url, "fetched": 0, "new": 0, "errors": [], "new_article_ids": []}

    try:
        feed = feedparser.parse(feed_url)

        if feed.bozo and feed.bozo_exception:
            stats["errors"].append(f"Parse warning: {feed.bozo_exception}")

        for entry in feed.entries:
            stats["fetched"] += 1

            link = entry.get("link", "")
            if not link:
                stats["errors"].append(f"Entry missing link: {entry.get('title', 'unknown')}")
                continue

            article = Article(
                id=generate_article_id(link),
                feed_url=feed_url,
                title=entry.get("title", "Untitled"),
                link=link,
                published=parse_published_date(entry),
                content=get_entry_content(entry),
            )

            if storage.save_article(article):
                stats["new"] += 1
                stats["new_article_ids"].append(article.id)

    except Exception as e:
        stats["errors"].append(f"Fetch error: {str(e)}")

    return stats


def fetch_all_feeds(
    feeds_file: str = "config/feeds.txt",
    storage: Optional[Storage] = None,
) -> list[dict]:
    """
    Fetch all feeds from the feeds file.
    Returns list of statistics for each feed.
    """
    if storage is None:
        storage = Storage()

    feeds = load_feeds(feeds_file)
    results = []

    for feed_url in feeds:
        result = fetch_feed(feed_url, storage)
        results.append(result)

    return results
