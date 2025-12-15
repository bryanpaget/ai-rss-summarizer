"""Feed discovery and validation utilities."""

import re
from typing import Optional
from dataclasses import dataclass

import httpx
import feedparser


@dataclass
class FeedInfo:
    """Information about a discovered/validated feed."""
    url: str
    title: str
    description: str
    item_count: int
    latest_items: list[dict]  # [{title, link, date}]

    def preview(self, max_items: int = 3) -> str:
        """Return a preview string for display."""
        lines = [f"  Title: {self.title}"]
        if self.description:
            lines.append(f"  Description: {self.description[:100]}")
        lines.append(f"  Items: {self.item_count}")
        if self.latest_items:
            lines.append("  Recent:")
            for item in self.latest_items[:max_items]:
                lines.append(f"    • {item['title'][:60]}")
        return "\n".join(lines)


def validate_feed(url: str, timeout: float = 10.0) -> tuple[bool, Optional[FeedInfo], str]:
    """
    Validate a feed URL and return info about it.

    Returns: (success, feed_info, error_message)
    """
    try:
        # Fetch with proper headers
        headers = {
            "User-Agent": "RSS-Summarizer/1.0 (Feed Validator)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        }

        response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        response.raise_for_status()

        # Parse feed
        feed = feedparser.parse(response.text)

        # Check if it's actually a feed
        if feed.bozo and not feed.entries:
            # feedparser sets bozo for any parsing issues
            bozo_exception = getattr(feed, 'bozo_exception', None)
            if bozo_exception:
                return False, None, f"Parse error: {type(bozo_exception).__name__}"
            return False, None, "Not a valid RSS/Atom feed"

        # Extract info
        title = feed.feed.get('title', url)
        description = feed.feed.get('description', '') or feed.feed.get('subtitle', '')

        latest_items = []
        for entry in feed.entries[:5]:
            latest_items.append({
                'title': entry.get('title', 'Untitled'),
                'link': entry.get('link', ''),
                'date': entry.get('published', entry.get('updated', '')),
            })

        info = FeedInfo(
            url=response.url,  # Use final URL after redirects
            title=title,
            description=description,
            item_count=len(feed.entries),
            latest_items=latest_items,
        )

        return True, info, ""

    except httpx.TimeoutException:
        return False, None, "Timeout - feed took too long to respond"
    except httpx.HTTPStatusError as e:
        return False, None, f"HTTP error: {e.response.status_code}"
    except httpx.RequestError as e:
        return False, None, f"Connection error: {type(e).__name__}"
    except Exception as e:
        return False, None, f"Error: {str(e)}"


def discover_feed(domain: str, timeout: float = 10.0) -> tuple[bool, Optional[FeedInfo], str]:
    """
    Given a domain or URL, try to discover the RSS feed.

    Checks:
    1. Common feed paths (/feed, /rss, /atom.xml, etc.)
    2. HTML <link rel="alternate"> tags

    Returns: (success, feed_info, error_message)
    """
    # Normalize to base URL
    if not domain.startswith('http'):
        domain = f"https://{domain}"

    # Remove trailing path for discovery
    from urllib.parse import urlparse
    parsed = urlparse(domain)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Common feed paths to check
    common_paths = [
        "/feed",
        "/rss",
        "/rss.xml",
        "/atom.xml",
        "/feed.xml",
        "/index.xml",
        "/feeds/posts/default",  # Blogger
        "/?feed=rss2",  # WordPress
        "/feed/",
    ]

    headers = {
        "User-Agent": "RSS-Summarizer/1.0 (Feed Discovery)",
    }

    # First, try to find feed link in HTML
    try:
        response = httpx.get(domain, headers=headers, timeout=timeout, follow_redirects=True)
        if response.status_code == 200:
            feed_url = _extract_feed_from_html(response.text, base_url)
            if feed_url:
                success, info, error = validate_feed(feed_url, timeout)
                if success:
                    return True, info, ""
    except Exception:
        pass

    # Try common paths
    for path in common_paths:
        url = base_url + path
        success, info, error = validate_feed(url, timeout)
        if success:
            return True, info, ""

    return False, None, f"No RSS feed found for {domain}"


def _extract_feed_from_html(html: str, base_url: str) -> Optional[str]:
    """Extract RSS/Atom feed URL from HTML link tags."""
    # Look for <link rel="alternate" type="application/rss+xml" href="...">
    patterns = [
        r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            href = match.group(1)
            # Handle relative URLs
            if href.startswith('/'):
                return base_url + href
            elif not href.startswith('http'):
                return base_url + '/' + href
            return href

    return None


def transform_url(url: str) -> Optional[str]:
    """
    Transform platform URLs to their RSS feed equivalents.

    Supports: YouTube channels, Reddit, Substack

    Returns: RSS feed URL or None if not a transformable URL
    """
    # YouTube channel
    youtube_patterns = [
        r'youtube\.com/channel/([^/?\s]+)',
        r'youtube\.com/c/([^/?\s]+)',
        r'youtube\.com/@([^/?\s]+)',
    ]
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            identifier = match.group(1)
            # For @username and /c/name, we'd need to resolve to channel ID
            # For now, return the channel ID format if it looks like one
            if identifier.startswith('UC') and len(identifier) == 24:
                return f"https://www.youtube.com/feeds/videos.xml?channel_id={identifier}"
            # Otherwise, we'd need to scrape to find channel ID - skip for now
            return None

    # Reddit subreddit
    reddit_match = re.search(r'reddit\.com/r/([^/?\s]+)', url)
    if reddit_match:
        subreddit = reddit_match.group(1)
        return f"https://www.reddit.com/r/{subreddit}/.rss"

    # Substack
    substack_match = re.search(r'([^/]+)\.substack\.com', url)
    if substack_match:
        name = substack_match.group(1)
        return f"https://{name}.substack.com/feed"

    # Medium
    medium_match = re.search(r'medium\.com/@([^/?\s]+)', url)
    if medium_match:
        username = medium_match.group(1)
        return f"https://medium.com/feed/@{username}"

    return None


def parse_opml(file_path: str) -> tuple[list[dict], str]:
    """
    Parse OPML file and return list of feeds.

    Returns: (feeds, error_message)
    Where feeds is list of {title, url, category}
    """
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        feeds = []

        def process_outlines(outlines, category=None):
            for outline in outlines:
                xml_url = outline.get('xmlUrl')
                if xml_url:
                    feeds.append({
                        'title': outline.get('text') or outline.get('title') or xml_url,
                        'url': xml_url,
                        'category': category,
                    })
                elif len(outline) > 0:
                    # This is a folder/category
                    new_category = outline.get('text') or outline.get('title')
                    process_outlines(outline, new_category)

        body = root.find('body')
        if body is None:
            return [], "Invalid OPML: no <body> element"

        process_outlines(body)
        return feeds, ""

    except ET.ParseError as e:
        return [], f"XML parse error: {e}"
    except FileNotFoundError:
        return [], f"File not found: {file_path}"
    except Exception as e:
        return [], f"Error reading OPML: {e}"


def detect_input_type(text: str) -> str:
    """
    Detect what type of input the user provided.

    Returns: 'opml', 'single_url', 'multiple_urls', 'domain', 'platform_url', 'unknown'
    """
    text = text.strip()

    # Check for OPML content (starts with XML declaration or <opml>)
    if text.startswith('<?xml') or text.startswith('<opml'):
        return 'opml'

    # Check for file path to OPML
    if text.endswith('.opml') or text.endswith('.xml'):
        return 'opml_file'

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    if len(lines) > 1:
        return 'multiple_urls'

    # Single line
    line = lines[0] if lines else ''

    # Check for platform URL that can be transformed
    if transform_url(line):
        return 'platform_url'

    # Check for full URL
    if line.startswith('http://') or line.startswith('https://'):
        return 'single_url'

    # Check if it looks like a domain
    if '.' in line and ' ' not in line:
        return 'domain'

    return 'unknown'


def search_feeds_online(query: str, timeout: float = 10.0) -> list[dict]:
    """
    Search for RSS feeds using Feedsearch.dev API.

    This uses a free, public API that searches for feeds on websites.
    Returns already-validated feed information.

    Args:
        query: Search query (website URL, domain, or topic)
        timeout: Request timeout in seconds

    Returns:
        List of feed dicts with 'title', 'url', 'description', 'score'
    """
    # Normalize query to URL format
    search_url = query
    if not query.startswith('http'):
        # If it looks like a domain, add https
        if '.' in query and ' ' not in query:
            search_url = f"https://{query}"
        else:
            # For topic searches, try common news/tech sites
            # This is a fallback - feedsearch works best with URLs
            search_url = None

    if not search_url:
        return []

    try:
        # Call Feedsearch.dev API
        api_url = f"https://feedsearch.dev/api/v1/search?url={search_url}"
        headers = {
            "User-Agent": "RSS-Summarizer/1.0 (Feed Search)",
        }

        response = httpx.get(api_url, headers=headers, timeout=timeout, follow_redirects=True)
        response.raise_for_status()

        data = response.json()

        # Parse results
        feeds = []
        for feed_data in data:
            feeds.append({
                "title": feed_data.get("title", "Unknown Feed"),
                "url": feed_data.get("url", ""),
                "description": feed_data.get("description", "")[:100],
                "score": feed_data.get("score", 0),
            })

        # Sort by score (relevance)
        feeds.sort(key=lambda x: x["score"], reverse=True)

        return feeds

    except httpx.TimeoutException:
        return []
    except httpx.HTTPStatusError:
        return []
    except httpx.RequestError:
        return []
    except Exception:
        return []
