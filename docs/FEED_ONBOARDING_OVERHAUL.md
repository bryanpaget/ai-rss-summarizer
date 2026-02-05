# Feed Onboarding Overhaul

## Problem
Current feed suggestion uses LLM to generate URLs. LLMs hallucinate - they don't know what RSS feeds actually exist. The UX is confusing with no guidance on input format.

## Solution

Replace with real options:

### Option 1: Import OPML
- Standard format used by all RSS readers (Feedly, Inoreader, NewsBlur, etc.)
- User exports from existing reader, imports here
- Parse with xml.etree.ElementTree (no extra dependencies)
- Preserves categories/folders

### Option 2: Browse Curated Categories
- Maintain a real database of verified, working feeds
- Organized by category: Tech, News, Science, Business, Entertainment, etc.
- Each feed verified to actually work
- User picks categories, sees feeds in each, selects which to add

### Option 3: Enter URL Directly
- Single URL entry (keep existing)
- Validate URL actually returns RSS/Atom before adding
- Show feed title and item count on success

### Option 4: Paste Multiple URLs
- Paste a list of URLs (one per line)
- Validate each
- Report which worked, which failed

## Implementation

### Step 1: Create curated feed database
File: `src/data/curated_feeds.py`

```python
CURATED_FEEDS = {
    "Tech": [
        {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "description": "Tech community news"},
        {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "description": "Tech news and analysis"},
        {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "description": "Tech, science, art"},
        # ... more verified feeds
    ],
    "News": [
        {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "description": "World news"},
        {"name": "Reuters", "url": "https://www.reutersagency.com/feed/", "description": "Global news"},
        # ... more
    ],
    "Science": [
        {"name": "Nature", "url": "https://www.nature.com/nature.rss", "description": "Scientific research"},
        {"name": "Quanta Magazine", "url": "https://api.quantamagazine.org/feed/", "description": "Science journalism"},
        # ... more
    ],
    # ... more categories
}
```

### Step 2: OPML parser
File: `src/opml.py`

```python
def parse_opml(file_path: str) -> list[dict]:
    """Parse OPML file, return list of {title, url, category}."""
    import xml.etree.ElementTree as ET

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
                    'category': category
                })
            elif len(outline) > 0:
                # This is a folder
                new_category = outline.get('text') or outline.get('title')
                process_outlines(outline, new_category)

    body = root.find('body')
    if body is not None:
        process_outlines(body)

    return feeds

def export_opml(feeds: list[dict], title: str = "RSS Subscriptions") -> str:
    """Export feeds to OPML format."""
    # For future use - allow users to export their feeds
    pass
```

### Step 3: Feed validator
```python
def validate_feed(url: str) -> tuple[bool, str, int]:
    """
    Validate a feed URL actually works.
    Returns: (success, title, item_count)
    """
    import feedparser

    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        return False, "", 0

    title = feed.feed.get('title', url)
    return True, title, len(feed.entries)
```

### Step 4: Rewrite _setup_feeds()

```python
def _setup_feeds() -> None:
    """Guide user through adding RSS feeds."""
    console.print()
    console.print("[bold]Add RSS Feeds[/bold]")
    console.print()
    console.print("  [bold]1[/bold] - Import from OPML file (from Feedly, Inoreader, etc.)")
    console.print("  [bold]2[/bold] - Browse curated feeds by category")
    console.print("  [bold]3[/bold] - Enter feed URL directly")
    console.print("  [bold]4[/bold] - Paste multiple URLs")
    console.print("  [bold]s[/bold] - Skip for now")
    console.print()

    choice = console.input("[bold]Choice [2]: [/bold]").strip() or "2"

    if choice == "1":
        _import_opml()
    elif choice == "2":
        _browse_curated_feeds()
    elif choice == "3":
        _add_single_feed()
    elif choice == "4":
        _paste_multiple_urls()
```

### Step 5: Implement each option

#### _import_opml()
- Prompt for file path
- Parse OPML
- Show summary: "Found X feeds in Y categories"
- Ask to import all or select categories
- Validate each feed (with progress bar)
- Report results

#### _browse_curated_feeds()
- Show categories
- User picks one or more
- Show feeds in selected categories
- User picks which to add
- All feeds pre-validated (they're curated)

#### _add_single_feed()
- Prompt for URL
- Validate immediately
- Show "✓ Found: [Feed Title] (X articles)" or "✗ Invalid feed URL"
- Add if valid

#### _paste_multiple_urls()
- Open multiline input or prompt for file
- Parse URLs (one per line)
- Validate each with progress
- Report: "Added X feeds, Y failed"

## UX Improvements

1. Clear prompts with examples
2. Validation feedback (checkmarks, error messages)
3. Progress indicators for bulk operations
4. Confirmation before adding
5. Summary after completion

## Testing

1. Import known-good OPML file
2. Import malformed OPML (graceful error)
3. Browse categories, select feeds
4. Enter valid URL - success
5. Enter invalid URL - clear error
6. Paste mix of valid/invalid URLs
