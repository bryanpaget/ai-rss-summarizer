"""Tests for feed_discovery module - feed discovery and validation utilities."""

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch, Mock

import pytest
import httpx

from src.feed_discovery import (
    FeedInfo,
    validate_feed,
    discover_feed,
    _extract_feed_from_html,
    transform_url,
    parse_opml,
    detect_input_type,
    search_feeds_online,
)


# =============================================================================
# Fixtures for Temporary Files and Directories
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_opml_file(temp_dir):
    """Create a temporary OPML file path."""
    return os.path.join(temp_dir, "feeds.opml")


@pytest.fixture
def temp_invalid_opml_file(temp_dir):
    """Create a temporary path for an invalid OPML file."""
    return os.path.join(temp_dir, "invalid.opml")


# =============================================================================
# Fixtures for FeedInfo Objects
# =============================================================================


@pytest.fixture
def feed_info_basic():
    """Create a basic FeedInfo with minimal data."""
    return FeedInfo(
        url="https://example.com/feed",
        title="Example Feed",
        description="An example feed for testing",
        item_count=5,
        latest_items=[
            {"title": "Article 1", "link": "https://example.com/1", "date": "2024-01-01"},
        ],
    )


@pytest.fixture
def feed_info_full():
    """Create a FeedInfo with full data."""
    return FeedInfo(
        url="https://techblog.example.com/rss.xml",
        title="Tech Blog RSS Feed",
        description="A comprehensive technology blog covering AI, programming, and more",
        item_count=100,
        latest_items=[
            {"title": "Breaking: AI Breakthrough", "link": "https://techblog.example.com/ai-news", "date": "2024-01-15"},
            {"title": "Python 4.0 Released", "link": "https://techblog.example.com/python-news", "date": "2024-01-14"},
            {"title": "Web Dev Trends 2024", "link": "https://techblog.example.com/webdev", "date": "2024-01-13"},
            {"title": "Security Alert", "link": "https://techblog.example.com/security", "date": "2024-01-12"},
            {"title": "Open Source Update", "link": "https://techblog.example.com/oss", "date": "2024-01-11"},
        ],
    )


@pytest.fixture
def feed_info_empty_items():
    """Create a FeedInfo with no items."""
    return FeedInfo(
        url="https://empty.example.com/feed",
        title="Empty Feed",
        description="A feed with no items",
        item_count=0,
        latest_items=[],
    )


@pytest.fixture
def feed_info_no_description():
    """Create a FeedInfo without description."""
    return FeedInfo(
        url="https://nodesc.example.com/feed",
        title="Feed Without Description",
        description="",
        item_count=3,
        latest_items=[
            {"title": "Item 1", "link": "https://nodesc.example.com/1", "date": ""},
        ],
    )


@pytest.fixture
def feed_info_unicode():
    """Create a FeedInfo with unicode characters."""
    return FeedInfo(
        url="https://unicode.example.com/feed",
        title="Unicode Feed - Tecnologia e Notcias",
        description="Notcias sobre tecnologia, cincia e arte",
        item_count=10,
        latest_items=[
            {"title": "Articulo sobre AI", "link": "https://unicode.example.com/1", "date": "2024-01-01"},
        ],
    )


@pytest.fixture
def feed_info_long_description():
    """Create a FeedInfo with a very long description."""
    return FeedInfo(
        url="https://long.example.com/feed",
        title="Feed with Long Description",
        description="A" * 500,
        item_count=5,
        latest_items=[
            {"title": "Long Article Title " * 10, "link": "https://long.example.com/1", "date": "2024-01-01"},
        ],
    )


@pytest.fixture
def feed_info_special_chars():
    """Create a FeedInfo with special characters."""
    return FeedInfo(
        url="https://special.example.com/feed?param=1&other=2",
        title="Feed <with> 'special' \"chars\" & symbols",
        description="Description with <html> tags & entities",
        item_count=2,
        latest_items=[
            {"title": "Title with <b>bold</b>", "link": "https://special.example.com/1?a=1&b=2", "date": ""},
        ],
    )


# =============================================================================
# Fixtures for Sample RSS/Atom Feed Content
# =============================================================================


@pytest.fixture
def sample_rss_content():
    """Create sample RSS 2.0 feed content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test RSS Feed</title>
        <link>https://example.com</link>
        <description>A test RSS feed for unit testing</description>
        <item>
            <title>Article One</title>
            <link>https://example.com/article1</link>
            <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Article Two</title>
            <link>https://example.com/article2</link>
            <pubDate>Sun, 14 Jan 2024 09:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Article Three</title>
            <link>https://example.com/article3</link>
            <pubDate>Sat, 13 Jan 2024 08:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>"""


@pytest.fixture
def sample_atom_content():
    """Create sample Atom feed content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Test Atom Feed</title>
    <subtitle>An Atom feed for testing</subtitle>
    <link href="https://example.com"/>
    <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>
    <updated>2024-01-15T10:00:00Z</updated>
    <entry>
        <title>Atom Entry One</title>
        <link href="https://example.com/atom1"/>
        <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
        <updated>2024-01-15T10:00:00Z</updated>
        <summary>Summary of atom entry one</summary>
    </entry>
    <entry>
        <title>Atom Entry Two</title>
        <link href="https://example.com/atom2"/>
        <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6b</id>
        <updated>2024-01-14T09:00:00Z</updated>
        <summary>Summary of atom entry two</summary>
    </entry>
</feed>"""


@pytest.fixture
def sample_rss_no_items():
    """Create RSS feed content with no items."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Empty Feed</title>
        <link>https://empty.example.com</link>
        <description>A feed with no items</description>
    </channel>
</rss>"""


@pytest.fixture
def sample_rss_single_item():
    """Create RSS feed content with a single item."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Single Item Feed</title>
        <link>https://single.example.com</link>
        <description>A feed with just one item</description>
        <item>
            <title>The Only Article</title>
            <link>https://single.example.com/only</link>
            <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>"""


@pytest.fixture
def sample_rss_many_items():
    """Create RSS feed content with many items."""
    items = "\n".join([
        f"""<item>
            <title>Article {i}</title>
            <link>https://many.example.com/article{i}</link>
            <pubDate>Mon, {i:02d} Jan 2024 10:00:00 GMT</pubDate>
        </item>"""
        for i in range(1, 21)
    ])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Many Items Feed</title>
        <link>https://many.example.com</link>
        <description>A feed with many items</description>
        {items}
    </channel>
</rss>"""


@pytest.fixture
def sample_rss_unicode():
    """Create RSS feed content with unicode characters."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Unicode Feed - Tecnologia</title>
        <link>https://unicode.example.com</link>
        <description>Notcias sobre tecnologia</description>
        <item>
            <title>Articulo en Espaol</title>
            <link>https://unicode.example.com/es1</link>
            <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
        </item>
        <item>
            <title></title>
            <link>https://unicode.example.com/jp1</link>
            <pubDate>Sun, 14 Jan 2024 09:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>"""


@pytest.fixture
def sample_invalid_xml():
    """Create invalid XML content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Broken Feed</title>
        <item>
            <title>Unclosed tag
        </item>
    </channel>
</rss>"""


@pytest.fixture
def sample_not_a_feed():
    """Create HTML content (not a feed)."""
    return """<!DOCTYPE html>
<html>
<head><title>Not a Feed</title></head>
<body>
<h1>This is HTML, not a feed</h1>
<p>Regular webpage content</p>
</body>
</html>"""


@pytest.fixture
def sample_empty_content():
    """Create empty content."""
    return ""


@pytest.fixture
def sample_json_content():
    """Create JSON content (not XML feed)."""
    return """{"title": "JSON data", "items": [{"name": "item1"}]}"""


# =============================================================================
# Fixtures for HTML with Feed Links
# =============================================================================


@pytest.fixture
def html_with_rss_link():
    """Create HTML with RSS feed link."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/feed.xml">
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_with_atom_link():
    """Create HTML with Atom feed link."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link rel="alternate" type="application/atom+xml" title="Atom Feed" href="/atom.xml">
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_with_absolute_feed_link():
    """Create HTML with absolute feed URL."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link rel="alternate" type="application/rss+xml" href="https://feeds.example.com/main.rss">
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_with_multiple_feed_links():
    """Create HTML with multiple feed links."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="/rss.xml">
    <link rel="alternate" type="application/atom+xml" title="Atom" href="/atom.xml">
    <link rel="alternate" type="application/rss+xml" title="Comments" href="/comments/rss">
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_without_feed_link():
    """Create HTML without any feed links."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>No Feed Site</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_with_relative_path_feed():
    """Create HTML with relative path feed link (no leading slash)."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link rel="alternate" type="application/rss+xml" href="feeds/main.xml">
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_reversed_attributes():
    """Create HTML with attributes in reversed order."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link href="/feed.xml" type="application/rss+xml" rel="alternate">
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_single_quotes():
    """Create HTML with single-quoted attributes."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Example Site</title>
    <link rel='alternate' type='application/rss+xml' href='/feed.xml'>
</head>
<body>
<h1>Welcome</h1>
</body>
</html>"""


@pytest.fixture
def html_uppercase_tags():
    """Create HTML with uppercase tags and attributes."""
    return """<!DOCTYPE html>
<HTML>
<HEAD>
    <TITLE>Example Site</TITLE>
    <LINK REL="ALTERNATE" TYPE="APPLICATION/RSS+XML" HREF="/FEED.XML">
</HEAD>
<BODY>
<H1>Welcome</H1>
</BODY>
</HTML>"""


# =============================================================================
# Fixtures for OPML Content
# =============================================================================


@pytest.fixture
def sample_opml_basic():
    """Create basic OPML content with feeds."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>My Feed Subscriptions</title>
    </head>
    <body>
        <outline text="Tech News" title="Tech News" xmlUrl="https://tech.example.com/rss"/>
        <outline text="Science Daily" title="Science Daily" xmlUrl="https://science.example.com/feed"/>
    </body>
</opml>"""


@pytest.fixture
def sample_opml_with_categories():
    """Create OPML content with categorized feeds."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>Organized Feeds</title>
    </head>
    <body>
        <outline text="Technology" title="Technology">
            <outline text="Hacker News" xmlUrl="https://news.ycombinator.com/rss"/>
            <outline text="Ars Technica" xmlUrl="https://feeds.arstechnica.com/arstechnica/index"/>
        </outline>
        <outline text="Science" title="Science">
            <outline text="Nature" xmlUrl="https://www.nature.com/nature.rss"/>
        </outline>
        <outline text="Uncategorized" xmlUrl="https://blog.example.com/feed"/>
    </body>
</opml>"""


@pytest.fixture
def sample_opml_empty():
    """Create OPML with no feeds."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>Empty Subscriptions</title>
    </head>
    <body>
    </body>
</opml>"""


@pytest.fixture
def sample_opml_nested_categories():
    """Create OPML with deeply nested categories."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>Nested Feeds</title>
    </head>
    <body>
        <outline text="News" title="News">
            <outline text="Tech News" title="Tech News">
                <outline text="AI News" title="AI News">
                    <outline text="Deep AI" xmlUrl="https://deep.ai/feed"/>
                </outline>
                <outline text="General Tech" xmlUrl="https://tech.example.com/rss"/>
            </outline>
            <outline text="World News" xmlUrl="https://world.example.com/rss"/>
        </outline>
    </body>
</opml>"""


@pytest.fixture
def sample_opml_invalid():
    """Create invalid OPML content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>Broken OPML</title>
    </head>
    <body>
        <outline text="Broken" xmlUrl="https://broken.example.com/rss"
    </body>
</opml>"""


@pytest.fixture
def sample_opml_no_body():
    """Create OPML without body element."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>No Body OPML</title>
    </head>
</opml>"""


@pytest.fixture
def sample_opml_many_feeds():
    """Create OPML with many feeds."""
    feeds = "\n".join([
        f'        <outline text="Feed {i}" title="Feed {i}" xmlUrl="https://feed{i}.example.com/rss"/>'
        for i in range(1, 51)
    ])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>Many Feeds</title>
    </head>
    <body>
{feeds}
    </body>
</opml>"""


@pytest.fixture
def sample_opml_unicode():
    """Create OPML with unicode content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>International Feeds</title>
    </head>
    <body>
        <outline text="Tecnologia" title="Tecnologia" xmlUrl="https://tech.es.example.com/rss"/>
        <outline text="" title="" xmlUrl="https://tech.jp.example.com/rss"/>
    </body>
</opml>"""


@pytest.fixture
def sample_opml_text_only():
    """Create OPML that uses 'text' attribute but no 'title' attribute."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>Text Only OPML</title>
    </head>
    <body>
        <outline text="Feed Name" xmlUrl="https://text.example.com/rss"/>
    </body>
</opml>"""


@pytest.fixture
def sample_opml_title_only():
    """Create OPML that uses 'title' attribute but no 'text' attribute."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>Title Only OPML</title>
    </head>
    <body>
        <outline title="Feed Name" xmlUrl="https://title.example.com/rss"/>
    </body>
</opml>"""


@pytest.fixture
def sample_opml_url_as_title():
    """Create OPML with no text/title attributes (fallback to URL)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <head>
        <title>URL Fallback OPML</title>
    </head>
    <body>
        <outline xmlUrl="https://urlonly.example.com/rss"/>
    </body>
</opml>"""


# =============================================================================
# Fixtures for Written OPML Files
# =============================================================================


@pytest.fixture
def opml_file_basic(temp_opml_file, sample_opml_basic):
    """Create a basic OPML file on disk."""
    with open(temp_opml_file, "w", encoding="utf-8") as f:
        f.write(sample_opml_basic)
    return temp_opml_file


@pytest.fixture
def opml_file_with_categories(temp_opml_file, sample_opml_with_categories):
    """Create an OPML file with categories on disk."""
    with open(temp_opml_file, "w", encoding="utf-8") as f:
        f.write(sample_opml_with_categories)
    return temp_opml_file


@pytest.fixture
def opml_file_empty(temp_opml_file, sample_opml_empty):
    """Create an empty OPML file on disk."""
    with open(temp_opml_file, "w", encoding="utf-8") as f:
        f.write(sample_opml_empty)
    return temp_opml_file


@pytest.fixture
def opml_file_invalid(temp_invalid_opml_file, sample_opml_invalid):
    """Create an invalid OPML file on disk."""
    with open(temp_invalid_opml_file, "w", encoding="utf-8") as f:
        f.write(sample_opml_invalid)
    return temp_invalid_opml_file


@pytest.fixture
def opml_file_nested(temp_opml_file, sample_opml_nested_categories):
    """Create an OPML file with nested categories on disk."""
    with open(temp_opml_file, "w", encoding="utf-8") as f:
        f.write(sample_opml_nested_categories)
    return temp_opml_file


@pytest.fixture
def opml_file_many_feeds(temp_opml_file, sample_opml_many_feeds):
    """Create an OPML file with many feeds on disk."""
    with open(temp_opml_file, "w", encoding="utf-8") as f:
        f.write(sample_opml_many_feeds)
    return temp_opml_file


@pytest.fixture
def opml_file_nonexistent(temp_dir):
    """Return path to a nonexistent OPML file."""
    return os.path.join(temp_dir, "nonexistent.opml")


# =============================================================================
# Fixtures for URL Test Data
# =============================================================================


@pytest.fixture
def url_valid_feed():
    """Return a valid RSS feed URL."""
    return "https://example.com/rss.xml"


@pytest.fixture
def url_valid_domain():
    """Return a valid domain without protocol."""
    return "example.com"


@pytest.fixture
def url_valid_domain_www():
    """Return a valid domain with www prefix."""
    return "www.example.com"


@pytest.fixture
def url_valid_https():
    """Return a valid HTTPS URL."""
    return "https://secure.example.com/feed"


@pytest.fixture
def url_valid_http():
    """Return a valid HTTP URL."""
    return "http://legacy.example.com/feed"


@pytest.fixture
def url_with_path():
    """Return a URL with a path."""
    return "https://blog.example.com/posts/feed.xml"


@pytest.fixture
def url_with_query_params():
    """Return a URL with query parameters."""
    return "https://example.com/feed?format=rss&version=2"


@pytest.fixture
def url_with_port():
    """Return a URL with a port number."""
    return "https://example.com:8080/feed"


@pytest.fixture
def url_with_auth():
    """Return a URL with authentication (not typically used for feeds)."""
    return "https://user:pass@example.com/feed"


@pytest.fixture
def url_unicode():
    """Return a URL with unicode characters."""
    return "https://example.com/feeds/notcias"


@pytest.fixture
def url_special_chars():
    """Return a URL with special characters that need encoding."""
    return "https://example.com/feed?q=test&name=foo bar"


# =============================================================================
# Fixtures for Platform URLs (YouTube, Reddit, Substack, Medium)
# =============================================================================


@pytest.fixture
def url_youtube_channel_id():
    """Return a YouTube channel URL with channel ID."""
    return "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"


@pytest.fixture
def url_youtube_channel_c():
    """Return a YouTube channel URL with /c/ format."""
    return "https://www.youtube.com/c/GoogleDevelopers"


@pytest.fixture
def url_youtube_channel_handle():
    """Return a YouTube channel URL with @ handle."""
    return "https://www.youtube.com/@GoogleDevelopers"


@pytest.fixture
def url_youtube_video():
    """Return a YouTube video URL (not a channel)."""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def url_reddit_subreddit():
    """Return a Reddit subreddit URL."""
    return "https://www.reddit.com/r/technology"


@pytest.fixture
def url_reddit_post():
    """Return a Reddit post URL (not a subreddit)."""
    return "https://www.reddit.com/r/technology/comments/abc123/title"


@pytest.fixture
def url_substack_publication():
    """Return a Substack publication URL."""
    return "https://techwriter.substack.com"


@pytest.fixture
def url_substack_post():
    """Return a Substack post URL."""
    return "https://techwriter.substack.com/p/article-title"


@pytest.fixture
def url_medium_user():
    """Return a Medium user URL."""
    return "https://medium.com/@techwriter"


@pytest.fixture
def url_medium_publication():
    """Return a Medium publication URL (not transformable)."""
    return "https://medium.com/towards-data-science"


@pytest.fixture
def platform_urls_transformable():
    """Return a list of platform URLs that can be transformed to RSS."""
    return [
        ("https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw", "youtube"),
        ("https://www.reddit.com/r/python", "reddit"),
        ("https://techwriter.substack.com", "substack"),
        ("https://medium.com/@techwriter", "medium"),
    ]


@pytest.fixture
def platform_urls_not_transformable():
    """Return a list of platform URLs that cannot be transformed."""
    return [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/@NonChannelID",  # @ format requires scraping
        "https://twitter.com/user",  # Not supported
        "https://facebook.com/page",  # Not supported
    ]


# =============================================================================
# Fixtures for Mock HTTP Responses
# =============================================================================


@pytest.fixture
def mock_response_success(sample_rss_content):
    """Create a mock successful HTTP response with RSS content."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = sample_rss_content
    mock.url = "https://example.com/feed"
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_response_atom(sample_atom_content):
    """Create a mock successful HTTP response with Atom content."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = sample_atom_content
    mock.url = "https://example.com/atom.xml"
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_response_html(html_with_rss_link):
    """Create a mock HTTP response with HTML content."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = html_with_rss_link
    mock.url = "https://example.com"
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_response_redirect():
    """Create a mock HTTP response that represents a redirect."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Redirected Feed</title>
        <link>https://new.example.com</link>
        <description>Feed after redirect</description>
    </channel>
</rss>"""
    mock.url = "https://new.example.com/feed"  # Different from request URL
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_response_404():
    """Create a mock 404 Not Found response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 404
    mock.text = "Not Found"
    mock.url = "https://example.com/feed"
    mock.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock
    ))
    return mock


@pytest.fixture
def mock_response_500():
    """Create a mock 500 Internal Server Error response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 500
    mock.text = "Internal Server Error"
    mock.url = "https://example.com/feed"
    mock.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=mock
    ))
    return mock


@pytest.fixture
def mock_response_403():
    """Create a mock 403 Forbidden response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 403
    mock.text = "Forbidden"
    mock.url = "https://example.com/feed"
    mock.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "Forbidden", request=MagicMock(), response=mock
    ))
    return mock


@pytest.fixture
def mock_response_invalid_xml(sample_invalid_xml):
    """Create a mock response with invalid XML."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = sample_invalid_xml
    mock.url = "https://example.com/broken"
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_response_empty():
    """Create a mock response with empty body."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = ""
    mock.url = "https://example.com/empty"
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_response_json(sample_json_content):
    """Create a mock response with JSON content (not a feed)."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = sample_json_content
    mock.url = "https://api.example.com/data"
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_response_html_no_feed(html_without_feed_link):
    """Create a mock HTML response without feed link."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = 200
    mock.text = html_without_feed_link
    mock.url = "https://example.com"
    mock.raise_for_status = MagicMock()
    return mock


# =============================================================================
# Fixtures for Mock HTTP Client (httpx)
# =============================================================================


@pytest.fixture
def mock_httpx_get_success(mock_response_success):
    """Create a mock httpx.get that returns success."""
    with patch("httpx.get", return_value=mock_response_success) as mock:
        yield mock


@pytest.fixture
def mock_httpx_get_timeout():
    """Create a mock httpx.get that raises timeout."""
    with patch("httpx.get", side_effect=httpx.TimeoutException("Timeout")) as mock:
        yield mock


@pytest.fixture
def mock_httpx_get_connection_error():
    """Create a mock httpx.get that raises connection error."""
    with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")) as mock:
        yield mock


@pytest.fixture
def mock_httpx_get_dns_error():
    """Create a mock httpx.get that raises DNS error."""
    request = MagicMock()
    with patch("httpx.get", side_effect=httpx.RequestError("DNS lookup failed", request=request)) as mock:
        yield mock


@pytest.fixture
def mock_httpx_get_404(mock_response_404):
    """Create a mock httpx.get that returns 404."""
    with patch("httpx.get", return_value=mock_response_404) as mock:
        yield mock


@pytest.fixture
def mock_httpx_get_500(mock_response_500):
    """Create a mock httpx.get that returns 500."""
    with patch("httpx.get", return_value=mock_response_500) as mock:
        yield mock


# =============================================================================
# Fixtures for Search API Responses
# =============================================================================


@pytest.fixture
def search_api_response_success():
    """Create a successful search API response."""
    return [
        {
            "title": "Tech Blog RSS",
            "url": "https://techblog.example.com/rss.xml",
            "description": "A technology blog covering AI, programming, and more",
            "score": 95,
        },
        {
            "title": "Tech Blog Atom",
            "url": "https://techblog.example.com/atom.xml",
            "description": "Atom feed for Tech Blog",
            "score": 85,
        },
        {
            "title": "Comments Feed",
            "url": "https://techblog.example.com/comments/feed",
            "description": "Blog comments feed",
            "score": 60,
        },
    ]


@pytest.fixture
def search_api_response_empty():
    """Create an empty search API response."""
    return []


@pytest.fixture
def search_api_response_single():
    """Create a search API response with single result."""
    return [
        {
            "title": "Only Feed",
            "url": "https://single.example.com/feed",
            "description": "The only feed found",
            "score": 90,
        },
    ]


@pytest.fixture
def search_api_response_no_scores():
    """Create a search API response without scores."""
    return [
        {"title": "Feed A", "url": "https://a.example.com/feed", "description": "Feed A"},
        {"title": "Feed B", "url": "https://b.example.com/feed", "description": "Feed B"},
    ]


@pytest.fixture
def search_api_response_unicode():
    """Create a search API response with unicode content."""
    return [
        {
            "title": "Feed de Tecnologia",
            "url": "https://tech.example.es/rss",
            "description": "Noticias de tecnologa en espaol",
            "score": 80,
        },
    ]


@pytest.fixture
def mock_search_api_success(search_api_response_success):
    """Create a mock for search API returning success."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = search_api_response_success
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_search_api_empty(search_api_response_empty):
    """Create a mock for search API returning empty results."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = search_api_response_empty
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_search_api_error():
    """Create a mock for search API returning error."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    ))

    with patch("httpx.get", return_value=mock_response) as mock:
        yield mock


@pytest.fixture
def mock_search_api_timeout():
    """Create a mock for search API timing out."""
    with patch("httpx.get", side_effect=httpx.TimeoutException("Timeout")) as mock:
        yield mock


# =============================================================================
# Fixtures for Input Detection Test Cases
# =============================================================================


@pytest.fixture
def input_opml_content():
    """Return OPML content for detect_input_type."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0"><body></body></opml>"""


@pytest.fixture
def input_opml_start():
    """Return content starting with <opml> tag."""
    return "<opml><body></body></opml>"


@pytest.fixture
def input_opml_file():
    """Return an OPML file path."""
    return "/path/to/feeds.opml"


@pytest.fixture
def input_xml_file():
    """Return an XML file path (could be OPML)."""
    return "/path/to/subscriptions.xml"


@pytest.fixture
def input_single_url():
    """Return a single URL."""
    return "https://example.com/feed.xml"


@pytest.fixture
def input_multiple_urls():
    """Return multiple URLs on separate lines."""
    return """https://example1.com/feed
https://example2.com/rss.xml
https://example3.com/atom.xml"""


@pytest.fixture
def input_domain():
    """Return a domain (not full URL)."""
    return "techblog.example.com"


@pytest.fixture
def input_domain_with_subdomain():
    """Return a domain with subdomain."""
    return "blog.news.example.com"


@pytest.fixture
def input_platform_youtube():
    """Return a YouTube URL for detection."""
    return "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"


@pytest.fixture
def input_platform_reddit():
    """Return a Reddit URL for detection."""
    return "https://www.reddit.com/r/technology"


@pytest.fixture
def input_platform_substack():
    """Return a Substack URL for detection."""
    return "https://techwriter.substack.com"


@pytest.fixture
def input_platform_medium():
    """Return a Medium URL for detection."""
    return "https://medium.com/@techwriter"


@pytest.fixture
def input_unknown():
    """Return unknown input."""
    return "this is not a url or domain or file"


@pytest.fixture
def input_empty():
    """Return empty input."""
    return ""


@pytest.fixture
def input_whitespace():
    """Return whitespace-only input."""
    return "   \n\t  \n  "


# =============================================================================
# Fixtures for Edge Cases
# =============================================================================


@pytest.fixture
def edge_case_very_long_url():
    """Return a very long URL."""
    return f"https://example.com/feed?{'x' * 2000}"


@pytest.fixture
def edge_case_special_chars_url():
    """Return a URL with special characters."""
    return "https://example.com/feed?q=test<>&name=foo\"bar'"


@pytest.fixture
def edge_case_unicode_domain():
    """Return a domain with unicode characters."""
    return "tecnologa.example.com"


@pytest.fixture
def edge_case_ip_address():
    """Return an IP address as domain."""
    return "192.168.1.1"


@pytest.fixture
def edge_case_localhost():
    """Return localhost URL."""
    return "http://localhost:8080/feed"


@pytest.fixture
def edge_case_ipv6():
    """Return an IPv6 URL."""
    return "http://[::1]:8080/feed"


# =============================================================================
# Fixtures for Integration Testing
# =============================================================================


@pytest.fixture
def full_discovery_setup(mock_response_html, sample_rss_content):
    """Set up mocks for a full feed discovery flow."""
    html_response = mock_response_html

    feed_response = MagicMock(spec=httpx.Response)
    feed_response.status_code = 200
    feed_response.text = sample_rss_content
    feed_response.url = "https://example.com/feed.xml"
    feed_response.raise_for_status = MagicMock()

    def get_side_effect(url, **kwargs):
        if url == "https://example.com" or url == "https://example.com/":
            return html_response
        else:
            return feed_response

    with patch("httpx.get", side_effect=get_side_effect) as mock:
        yield mock


@pytest.fixture
def full_discovery_no_feed_found():
    """Set up mocks for discovery that finds no feeds."""
    html_response = MagicMock(spec=httpx.Response)
    html_response.status_code = 200
    html_response.text = """<!DOCTYPE html>
<html><head><title>No Feed Site</title></head><body>Hello</body></html>"""
    html_response.url = "https://nofeed.example.com"
    html_response.raise_for_status = MagicMock()

    def get_side_effect(url, **kwargs):
        if "nofeed.example.com" in url:
            return html_response
        # All feed attempts fail with 404
        mock_404 = MagicMock(spec=httpx.Response)
        mock_404.status_code = 404
        mock_404.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_404
        ))
        return mock_404

    with patch("httpx.get", side_effect=get_side_effect) as mock:
        yield mock


@pytest.fixture
def full_validate_and_parse_setup(sample_rss_content, sample_opml_basic, temp_opml_file):
    """Set up for testing validate_feed and parse_opml together."""
    # Write OPML file
    with open(temp_opml_file, "w", encoding="utf-8") as f:
        f.write(sample_opml_basic)

    # Mock HTTP for validation
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = sample_rss_content
    mock_response.url = "https://tech.example.com/rss"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response) as mock:
        yield {
            "opml_file": temp_opml_file,
            "http_mock": mock,
        }


# =============================================================================
# Fixtures for Common Paths Discovery
# =============================================================================


@pytest.fixture
def common_feed_paths():
    """Return the list of common feed paths to check during discovery."""
    return [
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


@pytest.fixture
def mock_common_path_discovery(sample_rss_content):
    """Set up mock for testing common path discovery.

    Returns 404 for homepage, success for /rss.xml.
    """
    def get_side_effect(url, **kwargs):
        if "/rss.xml" in url:
            mock = MagicMock(spec=httpx.Response)
            mock.status_code = 200
            mock.text = sample_rss_content
            mock.url = url
            mock.raise_for_status = MagicMock()
            return mock

        # Homepage without feed link
        if url.endswith(".com") or url.endswith(".com/"):
            mock = MagicMock(spec=httpx.Response)
            mock.status_code = 200
            mock.text = "<html><head></head><body>Hello</body></html>"
            mock.url = url
            mock.raise_for_status = MagicMock()
            return mock

        # All other paths return 404
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = 404
        mock.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock
        ))
        return mock

    with patch("httpx.get", side_effect=get_side_effect) as mock:
        yield mock


# =============================================================================
# Fixtures for FeedInfo Preview Testing
# =============================================================================


@pytest.fixture
def feed_info_for_preview():
    """Create FeedInfo suitable for preview testing."""
    return FeedInfo(
        url="https://preview.example.com/feed",
        title="Preview Test Feed",
        description="A feed for testing the preview functionality with enough content to verify truncation",
        item_count=10,
        latest_items=[
            {"title": "First Article with a reasonably long title that might need truncation", "link": "https://preview.example.com/1", "date": "2024-01-15"},
            {"title": "Second Article", "link": "https://preview.example.com/2", "date": "2024-01-14"},
            {"title": "Third Article", "link": "https://preview.example.com/3", "date": "2024-01-13"},
            {"title": "Fourth Article", "link": "https://preview.example.com/4", "date": "2024-01-12"},
            {"title": "Fifth Article", "link": "https://preview.example.com/5", "date": "2024-01-11"},
        ],
    )


@pytest.fixture
def feed_info_preview_no_desc():
    """Create FeedInfo without description for preview testing."""
    return FeedInfo(
        url="https://nodesc.example.com/feed",
        title="No Description Feed",
        description="",
        item_count=2,
        latest_items=[
            {"title": "Article One", "link": "https://nodesc.example.com/1", "date": "2024-01-15"},
        ],
    )


@pytest.fixture
def feed_info_preview_no_items():
    """Create FeedInfo without items for preview testing."""
    return FeedInfo(
        url="https://noitems.example.com/feed",
        title="Empty Items Feed",
        description="A feed with no items",
        item_count=0,
        latest_items=[],
    )
