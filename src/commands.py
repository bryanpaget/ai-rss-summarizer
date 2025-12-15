"""User-friendly commands for RSS summarizer."""

from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from .storage import Storage
from .rss import fetch_all_feeds, load_feeds
from .trends import analyze_article, TREND_CATEGORIES
from .llm_providers import get_best_provider, get_setup_instructions
from .user_context import UserContextStore, RelevanceEngine, sort_by_relevance

console = Console(force_terminal=True, legacy_windows=True)


def update(
    feeds_file: str = "config/feeds.txt",
    db_path: str = "articles.db",
    topic_filter: Optional[str] = None,
    limit: int = 10,
    show_all: bool = False,
    use_context: bool = True,
    show_scores: bool = False,
    min_relevance: float = 0.0,
) -> dict:
    """
    Fetch new articles, summarize them, and present what's new.

    This is the main user-facing command that:
    1. Fetches latest articles from all feeds
    2. Generates summaries using the best available LLM
    3. Analyzes trends
    4. Presents a digest of what's new, optionally filtered by topic

    Args:
        feeds_file: Path to feeds configuration
        db_path: Path to database
        topic_filter: Optional topic to filter by (e.g., "tech", "politics")
        limit: Max articles to show
        show_all: Show all articles, not just new ones

    Returns:
        Dict with update statistics
    """
    storage = Storage(db_path)
    stats = {"fetched": 0, "new": 0, "summarized": 0, "displayed": 0}

    # Load user context if enabled
    context_store = None
    user_profile = None
    if use_context:
        try:
            context_store = UserContextStore(db_path=db_path)
            user_profile = context_store.load_profile()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load user context: {e}[/yellow]")
            use_context = False

    # Step 1: Fetch new articles
    console.print("[dim]Checking for new articles...[/dim]")
    feeds = load_feeds(feeds_file)

    if not feeds:
        console.print("[yellow]No feeds configured. Run 'rss add-feed URL' to add one.[/yellow]")
        return stats

    fetch_results = fetch_all_feeds(feeds_file, storage)

    for result in fetch_results:
        stats["fetched"] += result["fetched"]
        stats["new"] += result["new"]

    if stats["new"] == 0 and not show_all:
        console.print("[dim]No new articles since last check.[/dim]")
        # Still show recent if user wants
        articles = storage.get_articles(limit=limit)
        if articles:
            console.print(f"[dim]Showing {len(articles)} recent articles instead.[/dim]\n")
    else:
        console.print(f"[green]Found {stats['new']} new articles![/green]\n")

    # Step 2: Get the best LLM provider
    provider, is_llm = get_best_provider()

    if is_llm:
        console.print(f"[dim]Using {provider.name} for summaries[/dim]")
    else:
        console.print("[dim]Using basic summaries (set up an LLM for better results)[/dim]")

    # Step 3: Get articles to display
    articles = storage.get_articles(limit=limit * 2)  # Get more to filter

    # Apply personalized relevance scoring if context enabled
    if use_context and user_profile and context_store:
        articles = sort_by_relevance(articles, user_profile, context_store)
        # Filter by minimum relevance if specified
        if min_relevance > 0:
            articles = [a for a in articles if getattr(a, 'relevance_score', 0) >= min_relevance]

    # Filter by topic if specified
    if topic_filter:
        topic_filter_lower = topic_filter.lower()
        filtered = []
        for article in articles:
            # Check if article matches the topic filter
            if not article.trend_tags:
                tags = analyze_article(article)
                storage.update_trends(article.id, tags)
                article.trend_tags = tags

            if topic_filter_lower in article.trend_tags.lower():
                filtered.append(article)
            elif _matches_topic_keywords(article, topic_filter_lower):
                filtered.append(article)

        articles = filtered[:limit]
        console.print(f"[dim]Filtered to {len(articles)} articles matching '{topic_filter}'[/dim]\n")
    else:
        articles = articles[:limit]

    if not articles:
        console.print("[yellow]No articles found matching your criteria.[/yellow]")
        return stats

    # Step 4: Summarize articles that need it
    cached_count = 0
    for article in articles:
        if not article.summary:
            summary = provider.summarize(article.content)
            storage.update_summary(article.id, summary)
            article.summary = summary
            stats["summarized"] += 1
        else:
            cached_count += 1

        if not article.trend_tags:
            tags = analyze_article(article)
            storage.update_trends(article.id, tags)
            article.trend_tags = tags

    # Step 5: Present the digest
    _display_digest(articles, topic_filter, provider, cached_count, show_scores=show_scores)
    stats["displayed"] = len(articles)

    return stats


def _matches_topic_keywords(article, topic: str) -> bool:
    """Check if article matches topic keywords."""
    # Map common topic names to trend categories
    topic_map = {
        "tech": "AI & Technology",
        "technology": "AI & Technology",
        "ai": "AI & Technology",
        "politics": "Politics & Government",
        "political": "Politics & Government",
        "business": "Business & Economy",
        "economy": "Business & Economy",
        "finance": "Business & Economy",
        "science": "Science & Research",
        "health": "Health & Medicine",
        "medical": "Health & Medicine",
        "climate": "Climate & Environment",
        "environment": "Climate & Environment",
        "entertainment": "Entertainment & Culture",
        "culture": "Entertainment & Culture",
        "world": "World & International",
        "international": "World & International",
    }

    # Check mapped categories
    if topic in topic_map:
        category = topic_map[topic]
        if category.lower() in (article.trend_tags or "").lower():
            return True

    # Check content directly
    text = f"{article.title} {article.content}".lower()
    return topic in text


def _display_digest(articles: list, topic_filter: Optional[str] = None, provider=None, cached_count: int = 0, show_scores: bool = False) -> None:
    """Display a formatted digest of articles."""
    title = "What's New"
    if topic_filter:
        title += f" in {topic_filter.title()}"

    console.print(Panel(f"[bold]{title}[/bold]", style="blue"))
    console.print()

    for i, article in enumerate(articles, 1):
        # Format the article
        pub_date = ""
        if article.published:
            pub_date = f" [dim]({str(article.published)[:10]})[/dim]"

        # Title with relevance score if requested
        title_line = f"[bold cyan]{i}. {article.title}[/bold cyan]{pub_date}"
        if show_scores and hasattr(article, 'relevance_score'):
            score = article.relevance_score
            score_color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "dim"
            title_line += f" [{score_color}][{score:.2f}][/{score_color}]"
        console.print(title_line)

        # Summary
        summary = article.summary or "[dim]No summary available[/dim]"
        console.print(f"   {summary}")

        # Tags
        if article.trend_tags and article.trend_tags != "Uncategorized":
            console.print(f"   [dim]Tags: {article.trend_tags}[/dim]")

        # Link
        console.print(f"   [dim underline]{article.link}[/dim underline]")
        console.print()

    # Provider transparency footer - always show full info
    console.print("-" * 60)

    if provider:
        # Get model name - try to get the actual discovered model
        model = "unknown"
        if hasattr(provider, '_discovered_model') and provider._discovered_model:
            model = provider._discovered_model
        elif hasattr(provider, 'model_name'):
            model = provider.model_name

        # Get usage stats
        usage = getattr(provider, 'session_usage', {"calls": 0, "total_tokens": 0})
        summarized_count = usage.get("calls", 0)
        total_tokens = usage.get("total_tokens", 0)

        # Build transparent footer
        footer_parts = [f"[dim]Provider: {provider.name}[/dim]"]
        footer_parts.append(f"[dim]| Model: {model}[/dim]")
        footer_parts.append(f"[dim]| Articles: {len(articles)} ({summarized_count} summarized, {cached_count} cached)[/dim]")

        if total_tokens > 0:
            footer_parts.append(f"[dim]| Tokens: ~{total_tokens:,}[/dim]")
        elif cached_count > 0 and summarized_count == 0:
            footer_parts.append(f"[dim]| Tokens: 0 (all cached)[/dim]")

        console.print(" ".join(footer_parts))
    else:
        console.print("[dim]Provider: None[/dim]")


def setup_wizard() -> None:
    """
    Interactive setup wizard to help users configure an LLM provider.
    """
    import os

    console.print(Panel("[bold]RSS Summarizer Setup[/bold]", style="blue"))
    console.print()

    from .llm_providers import (
        list_providers, LLMConfig, ProviderType, get_provider,
        auto_detect_provider
    )

    # Check what's available
    console.print("[bold]Checking available providers...[/bold]\n")
    providers = list_providers()

    # Build table
    table = Table(title="Provider Status")
    table.add_column("#", style="dim")
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("Description")

    available_providers = []
    setup_providers = []  # Providers that could be set up with API key

    for i, p in enumerate(providers, 1):
        if p["available"] and p["type"] != ProviderType.SIMPLE:
            status = "[green]Ready[/green]"
            available_providers.append((i, p))
        elif p["type"] in [ProviderType.GEMINI, ProviderType.CLAUDE, ProviderType.GROK, ProviderType.OPENAI]:
            status = "[yellow]Needs API Key[/yellow]"
            setup_providers.append((i, p))
        elif p["type"] == ProviderType.CLAUDE_CODE:
            status = "[yellow]Needs SDK[/yellow]"
            setup_providers.append((i, p))
        elif p["type"] in [ProviderType.LM_STUDIO, ProviderType.OLLAMA]:
            status = "[yellow]Not Running[/yellow]"
            setup_providers.append((i, p))
        else:
            status = "[red]Not Available[/red]"

        table.add_row(str(i), p["name"], status, p["description"])

    console.print(table)
    console.print()

    # Show recommendations
    if available_providers:
        console.print("[green]Ready to use:[/green]")
        for num, p in available_providers:
            console.print(f"  {num}. {p['name']}")
        console.print()

        # Auto-detect best
        auto_provider = auto_detect_provider()
        if auto_provider:
            console.print(f"[bold green]Recommended:[/bold green] {auto_provider.name}")
            console.print()
            console.print("Options:")
            console.print("  [bold]1[/bold] - Use recommended provider")
            console.print("  [bold]2[/bold] - Choose a different provider")
            console.print("  [bold]3[/bold] - Set up a new provider (API key)")
            console.print("  [bold]q[/bold] - Quit setup")
            console.print()

            choice = console.input("[bold]Choice [1]: [/bold]").strip() or "1"

            if choice == "q":
                console.print("[dim]Setup cancelled[/dim]")
                return
            elif choice == "1":
                _save_provider_config(auto_provider, providers)
                return
            elif choice == "3":
                _setup_new_provider(providers)
                return
            # else fall through to provider selection

    else:
        console.print("[yellow]No LLM providers are currently ready.[/yellow]")
        console.print()
        console.print("Options:")
        console.print("  [bold]1[/bold] - Set up a cloud provider (API key)")
        console.print("  [bold]2[/bold] - Set up a local provider (LM Studio/Ollama)")
        console.print("  [bold]3[/bold] - Use basic summarizer (no AI)")
        console.print("  [bold]q[/bold] - Quit setup")
        console.print()

        choice = console.input("[bold]Choice [1]: [/bold]").strip() or "1"

        if choice == "q":
            console.print("[dim]Setup cancelled[/dim]")
            return
        elif choice == "3":
            config = LLMConfig(provider=ProviderType.SIMPLE)
            config.save()
            console.print("[green]Configured to use basic (extractive) summarizer.[/green]")
            return
        elif choice == "2":
            _show_local_setup_instructions()
            return
        else:
            _setup_new_provider(providers)
            return

    # Provider selection
    _select_provider(providers, available_providers + setup_providers)


def _save_provider_config(provider, providers_list) -> None:
    """Save provider configuration."""
    from .llm_providers import LLMConfig, ProviderType

    # Find the provider type
    provider_type = ProviderType.SIMPLE
    for p in providers_list:
        if p["name"] == provider.name or provider.name.startswith(p["name"]):
            provider_type = p["type"]
            break

    config = LLMConfig(provider=provider_type)
    config.save()
    console.print(f"[green]Saved {provider.name} as default provider.[/green]")
    console.print(f"[dim]Configuration saved to config/llm.json[/dim]")
    console.print()
    _onboard_feeds()


def _onboard_feeds() -> None:
    """Guide user through adding initial feeds."""
    from pathlib import Path
    from .rss import load_feeds

    feeds_file = "config/feeds.txt"
    existing_feeds = load_feeds(feeds_file)

    console.print("[bold]Step 2: Set up your feeds[/bold]")
    console.print()

    if existing_feeds:
        console.print(f"[dim]You have {len(existing_feeds)} feeds configured.[/dim]")
        console.print()
        console.print("  [bold]1[/bold] - Keep existing and add more")
        console.print("  [bold]2[/bold] - Start fresh")
        console.print("  [bold]3[/bold] - Done (keep existing)")
        console.print()
        choice = console.input("[bold]Choice [3]: [/bold]").strip() or "3"

        if choice == "3":
            _finish_onboarding()
            return
        elif choice == "2":
            Path(feeds_file).parent.mkdir(parents=True, exist_ok=True)
            Path(feeds_file).write_text("# RSS Feeds\n")

    _setup_feeds()
    _finish_onboarding()


def _setup_feeds() -> None:
    """Guide user through adding RSS feeds."""
    console.print()
    console.print("[bold]Add RSS Feeds[/bold]")
    console.print()
    console.print("  [bold]1[/bold] - Import from OPML file (from Feedly, Inoreader, etc.)")
    console.print("  [bold]2[/bold] - Add feed URL or website")
    console.print("  [bold]3[/bold] - Paste multiple URLs")
    console.print("  [bold]4[/bold] - Browse curated feeds by category")
    console.print("  [bold]s[/bold] - Skip for now")
    console.print()

    choice = console.input("[bold]Choice [2]: [/bold]").strip() or "2"

    if choice == "1":
        _import_opml()
    elif choice == "2":
        _add_feed_smart()
    elif choice == "3":
        _paste_multiple_urls()
    elif choice == "4":
        _browse_curated_feeds()


def _import_opml() -> None:
    """Import feeds from OPML file."""
    from pathlib import Path
    from .feed_discovery import parse_opml, validate_feed

    console.print()
    console.print("[dim]OPML files can be exported from most RSS readers.[/dim]")
    file_path = console.input("[bold]OPML file path: [/bold]").strip()

    if not file_path:
        return

    file_path = file_path.strip('"').strip("'")
    file_path = str(Path(file_path).expanduser())

    feeds, error = parse_opml(file_path)

    if error:
        console.print(f"[red]Error: {error}[/red]")
        return

    if not feeds:
        console.print("[yellow]No feeds found in OPML file.[/yellow]")
        return

    categories = {}
    for feed in feeds:
        cat = feed.get('category') or 'Uncategorized'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(feed)

    console.print()
    console.print(f"[green]Found {len(feeds)} feeds in {len(categories)} categories:[/green]")
    for cat, cat_feeds in categories.items():
        console.print(f"  - {cat}: {len(cat_feeds)} feeds")

    console.print()
    choice = console.input("[bold]Import all? (y/n) [y]: [/bold]").strip().lower() or "y"

    if choice != "y":
        return

    feeds_path = Path("config/feeds.txt")
    feeds_path.parent.mkdir(parents=True, exist_ok=True)

    console.print()
    console.print("[dim]Validating feeds...[/dim]")

    added = 0
    failed = 0

    with open(feeds_path, "a") as f:
        for feed in feeds:
            url = feed['url']
            title = feed['title']
            success, info, err = validate_feed(url, timeout=5.0)
            status = "[green]OK[/green]" if success else "[red]FAIL[/red]"
            console.print(f"  {status} {title[:40]}")
            if success:
                f.write(f"\n# {info.title}\n{info.url}\n")
                added += 1
            else:
                failed += 1

    console.print()
    if failed:
        console.print(f"[green]Added {added} feeds.[/green] [yellow]({failed} failed)[/yellow]")
    else:
        console.print(f"[green]Added {added} feeds.[/green]")


def _add_feed_smart() -> None:
    """Smart feed addition - handles URLs, domains, platform URLs."""
    from pathlib import Path
    from .feed_discovery import validate_feed, discover_feed, transform_url, detect_input_type

    console.print()
    console.print("[dim]Enter a feed URL, website URL, or domain.[/dim]")
    console.print("[dim]Examples: https://example.com/feed.xml, example.com, youtube.com/@channel[/dim]")
    console.print()

    while True:
        user_input = console.input("[bold]URL: [/bold]").strip()
        if not user_input:
            break

        input_type = detect_input_type(user_input)
        feed_info = None
        error = ""

        if input_type == 'platform_url':
            feed_url = transform_url(user_input)
            if feed_url:
                console.print(f"[dim]Transformed to: {feed_url}[/dim]")
                success, feed_info, error = validate_feed(feed_url)
            else:
                console.print("[yellow]Could not transform this URL.[/yellow]")
                continue

        elif input_type == 'single_url':
            console.print("[dim]Validating...[/dim]")
            success, feed_info, error = validate_feed(user_input)
            if not success:
                console.print("[dim]Not a feed, searching site...[/dim]")
                success, feed_info, error = discover_feed(user_input)

        elif input_type == 'domain':
            console.print(f"[dim]Searching for feeds on {user_input}...[/dim]")
            success, feed_info, error = discover_feed(user_input)

        else:
            console.print("[yellow]Could not understand input.[/yellow]")
            continue

        if feed_info:
            console.print()
            console.print(f"[green]Found feed:[/green]")
            console.print(feed_info.preview())
            console.print()
            add = console.input("[bold]Add this feed? (y/n) [y]: [/bold]").strip().lower() or "y"
            if add == "y":
                feeds_path = Path("config/feeds.txt")
                feeds_path.parent.mkdir(parents=True, exist_ok=True)
                with open(feeds_path, "a") as f:
                    f.write(f"\n# {feed_info.title}\n{feed_info.url}\n")
                console.print("[green]Added![/green]")
        else:
            console.print(f"[red]Not found: {error}[/red]")

        console.print()
        cont = console.input("[dim]Add another? (y/n) [y]: [/dim]").strip().lower() or "y"
        if cont != "y":
            break


def _paste_multiple_urls() -> None:
    """Paste multiple URLs at once."""
    from pathlib import Path
    from .feed_discovery import validate_feed

    console.print()
    console.print("[dim]Paste URLs (one per line), blank line when done:[/dim]")
    console.print()

    urls = []
    while True:
        line = console.input("").strip()
        if not line:
            break
        if line.startswith("http"):
            urls.append(line)

    if not urls:
        return

    console.print()
    console.print(f"[dim]Validating {len(urls)} URLs...[/dim]")

    feeds_path = Path("config/feeds.txt")
    feeds_path.parent.mkdir(parents=True, exist_ok=True)

    added = 0
    failed = 0

    with open(feeds_path, "a") as f:
        for url in urls:
            success, info, error = validate_feed(url, timeout=5.0)
            if success:
                console.print(f"  [green]OK[/green] {info.title[:50]}")
                f.write(f"\n# {info.title}\n{info.url}\n")
                added += 1
            else:
                console.print(f"  [red]FAIL[/red] {url[:50]}")
                failed += 1

    console.print()
    if failed:
        console.print(f"[green]Added {added} feeds.[/green] [yellow]({failed} failed)[/yellow]")
    else:
        console.print(f"[green]Added {added} feeds.[/green]")


def _browse_curated_feeds() -> None:
    """Browse curated feeds by category or search for feeds."""
    console.print()
    console.print("[bold]Feed Discovery[/bold]")
    console.print()
    console.print("  [bold]1[/bold] - Browse popular feeds by category")
    console.print("  [bold]2[/bold] - Search for feeds on a topic or website")
    console.print("  [bold]b[/bold] - Back")
    console.print()

    choice = console.input("[bold]Choice [1]: [/bold]").strip() or "1"

    if choice == "1":
        _show_curated_categories()
    elif choice == "2":
        _search_feeds()


def _show_curated_categories() -> None:
    """Show curated feed categories and let user browse."""
    from .feed_catalog import CURATED_CATEGORIES, get_feeds_by_category
    from pathlib import Path

    console.print()
    console.print("[bold]Popular Feed Categories[/bold]")
    console.print("[dim]Curated from awesome-rss-feeds[/dim]")
    console.print()

    table = Table(show_header=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")

    categories = list(CURATED_CATEGORIES.keys())
    for i, category in enumerate(categories, 1):
        count = len(CURATED_CATEGORIES[category])
        table.add_row(str(i), category, str(count))

    console.print(table)
    console.print()

    choice = console.input("[bold]Select category (number or 'b' to go back): [/bold]").strip()

    if choice == "b" or not choice:
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(categories):
            category = categories[idx]
            feeds = get_feeds_by_category(category)
            _show_category_feeds(category, feeds)
        else:
            console.print("[red]Invalid selection[/red]")
    except ValueError:
        console.print("[red]Invalid selection[/red]")


def _show_category_feeds(category: str, feeds: list[dict]) -> None:
    """Show feeds in a category and let user add them."""
    from pathlib import Path
    from .feed_discovery import validate_feed

    console.print()
    console.print(f"[bold]{category}[/bold]")
    console.print()

    table = Table(show_header=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Feed", style="cyan")
    table.add_column("Description")

    for i, feed in enumerate(feeds, 1):
        desc = feed.get("description", "")[:60]
        table.add_row(str(i), feed["title"], desc)

    console.print(table)
    console.print()
    console.print("[dim]Enter numbers to add (e.g., '1,3,5' or '1-5' or 'all'), or 'b' to go back[/dim]")
    console.print()

    choice = console.input("[bold]Selection: [/bold]").strip()

    if choice == "b" or not choice:
        return

    selected_indices = _parse_selection(choice, len(feeds))
    if not selected_indices:
        console.print("[red]Invalid selection[/red]")
        return

    console.print()
    console.print(f"[dim]Validating {len(selected_indices)} feeds...[/dim]")

    feeds_path = Path("config/feeds.txt")
    feeds_path.parent.mkdir(parents=True, exist_ok=True)

    added = 0
    failed = 0

    with open(feeds_path, "a") as f:
        for idx in selected_indices:
            feed = feeds[idx]
            url = feed["url"]
            title = feed["title"]
            success, info, error = validate_feed(url, timeout=5.0)
            if success:
                console.print(f"  [green]OK[/green] {title[:50]}")
                f.write(f"\n# {info.title}\n{info.url}\n")
                added += 1
            else:
                console.print(f"  [red]FAIL[/red] {title[:50]} ({error})")
                failed += 1

    console.print()
    if failed:
        console.print(f"[green]Added {added} feeds.[/green] [yellow]({failed} failed)[/yellow]")
    else:
        console.print(f"[green]Added {added} feeds.[/green]")


def _parse_selection(selection: str, max_items: int) -> list[int]:
    """Parse user selection string into list of indices."""
    if selection.lower() == "all":
        return list(range(max_items))

    indices = set()
    parts = selection.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            # Range like "1-5"
            try:
                start, end = part.split("-")
                start_idx = int(start.strip()) - 1
                end_idx = int(end.strip()) - 1
                if 0 <= start_idx < max_items and 0 <= end_idx < max_items:
                    indices.update(range(start_idx, end_idx + 1))
            except ValueError:
                pass
        else:
            # Single number
            try:
                idx = int(part) - 1
                if 0 <= idx < max_items:
                    indices.add(idx)
            except ValueError:
                pass

    return sorted(list(indices))


def _search_feeds() -> None:
    """Search for feeds using Feedsearch.dev API."""
    from .feed_discovery import validate_feed, search_feeds_online
    from pathlib import Path

    console.print()
    console.print("[dim]Enter a topic, website, or domain to search for feeds.[/dim]")
    console.print("[dim]Examples: 'python programming', 'nytimes.com', 'machine learning'[/dim]")
    console.print()

    query = console.input("[bold]Search: [/bold]").strip()

    if not query:
        return

    console.print()
    console.print(f"[dim]Searching for feeds about '{query}'...[/dim]")

    feeds = search_feeds_online(query)

    if not feeds:
        console.print("[yellow]No feeds found. Try a different search term or website.[/yellow]")
        return

    console.print()
    console.print(f"[green]Found {len(feeds)} feeds:[/green]")
    console.print()

    table = Table(show_header=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Feed", style="cyan")
    table.add_column("URL")

    for i, feed in enumerate(feeds, 1):
        table.add_row(str(i), feed["title"][:40], feed["url"][:50])

    console.print(table)
    console.print()
    console.print("[dim]Enter numbers to add (e.g., '1,3' or '1-3'), or 'b' to cancel[/dim]")
    console.print()

    choice = console.input("[bold]Selection: [/bold]").strip()

    if choice == "b" or not choice:
        return

    selected_indices = _parse_selection(choice, len(feeds))
    if not selected_indices:
        console.print("[red]Invalid selection[/red]")
        return

    console.print()
    feeds_path = Path("config/feeds.txt")
    feeds_path.parent.mkdir(parents=True, exist_ok=True)

    added = 0
    with open(feeds_path, "a") as f:
        for idx in selected_indices:
            feed = feeds[idx]
            console.print(f"[green]Adding[/green] {feed['title']}")
            f.write(f"\n# {feed['title']}\n{feed['url']}\n")
            added += 1

    console.print()
    console.print(f"[green]Added {added} feeds.[/green]")






def _finish_onboarding() -> None:
    """Show completion message."""
    console.print()
    console.print("[bold green]Setup complete![/bold green]")
    console.print()
    console.print("Next: [bold]rss update[/bold] to fetch and summarize articles")
    console.print()


def _setup_new_provider(providers) -> None:
    """Guide user through setting up a new provider with API key."""
    import os
    from .llm_providers import LLMConfig, ProviderType

    console.print()
    console.print("[bold]Cloud Provider Setup[/bold]")
    console.print()
    console.print("Available cloud providers:")
    console.print("  [bold]1[/bold] - Gemini (FREE tier - recommended)")
    console.print("  [bold]2[/bold] - Claude Code (uses Claude Code auth)")
    console.print("  [bold]3[/bold] - Claude API (separate API key)")
    console.print("  [bold]4[/bold] - Grok (xAI)")
    console.print("  [bold]5[/bold] - OpenAI")
    console.print("  [bold]q[/bold] - Cancel")
    console.print()

    choice = console.input("[bold]Choice: [/bold]").strip()

    if choice == "q":
        return

    if choice == "1":
        console.print()
        console.print("[bold]Gemini Setup[/bold]")
        console.print("1. Get a free API key at: [link]https://aistudio.google.com/apikey[/link]")
        console.print("2. Install SDK: [bold]pip install google-generativeai[/bold]")
        console.print()
        api_key = console.input("Enter your Gemini API key (or 'skip' to set later): ").strip()
        if api_key and api_key != "skip":
            os.environ["GOOGLE_API_KEY"] = api_key
            console.print("[yellow]Note: Set GOOGLE_API_KEY in your environment for persistence[/yellow]")
            config = LLMConfig(provider=ProviderType.GEMINI, api_key=api_key)
            config.save()
            console.print("[green]Gemini configured![/green]")

    elif choice == "2":
        console.print()
        console.print("[bold]Claude Code Setup[/bold]")
        console.print("This uses your Claude Code authentication - no separate API key needed!")
        console.print()
        console.print("1. Install SDK: [bold]pip install claude-agent-sdk[/bold]")
        console.print("2. Make sure Claude Code is authenticated (run 'claude' in terminal)")
        console.print()
        confirm = console.input("Have you installed claude-agent-sdk? [y/N]: ").strip().lower()
        if confirm == "y":
            config = LLMConfig(provider=ProviderType.CLAUDE_CODE)
            config.save()
            console.print("[green]Claude Code configured![/green]")

    elif choice == "3":
        console.print()
        console.print("[bold]Claude API Setup[/bold]")
        console.print("[yellow]Note: A Claude subscription is NOT an API key![/yellow]")
        console.print("Get an API key at: [link]https://console.anthropic.com/[/link]")
        console.print()
        api_key = console.input("Enter your Anthropic API key (or 'skip'): ").strip()
        if api_key and api_key != "skip":
            os.environ["ANTHROPIC_API_KEY"] = api_key
            console.print("[yellow]Note: Set ANTHROPIC_API_KEY in your environment for persistence[/yellow]")
            config = LLMConfig(provider=ProviderType.CLAUDE, api_key=api_key)
            config.save()
            console.print("[green]Claude API configured![/green]")

    elif choice == "4":
        console.print()
        console.print("[bold]Grok Setup[/bold]")
        console.print("Get an API key at: [link]https://console.x.ai/[/link]")
        console.print()
        api_key = console.input("Enter your xAI API key (or 'skip'): ").strip()
        if api_key and api_key != "skip":
            os.environ["XAI_API_KEY"] = api_key
            console.print("[yellow]Note: Set XAI_API_KEY in your environment for persistence[/yellow]")
            config = LLMConfig(provider=ProviderType.GROK, api_key=api_key)
            config.save()
            console.print("[green]Grok configured![/green]")

    elif choice == "5":
        console.print()
        console.print("[bold]OpenAI Setup[/bold]")
        console.print("Get an API key at: [link]https://platform.openai.com/api-keys[/link]")
        console.print()
        api_key = console.input("Enter your OpenAI API key (or 'skip'): ").strip()
        if api_key and api_key != "skip":
            os.environ["OPENAI_API_KEY"] = api_key
            console.print("[yellow]Note: Set OPENAI_API_KEY in your environment for persistence[/yellow]")
            config = LLMConfig(provider=ProviderType.OPENAI, api_key=api_key)
            config.save()
            console.print("[green]OpenAI configured![/green]")


def _show_local_setup_instructions() -> None:
    """Show instructions for setting up local LLM providers."""
    console.print()
    console.print("[bold]Local LLM Setup[/bold]")
    console.print()
    console.print("[cyan]LM Studio (recommended for GPU users):[/cyan]")
    console.print("  1. Download from https://lmstudio.ai")
    console.print("  2. Load any model (e.g., Llama 2, Mistral)")
    console.print("  3. Click 'Start Server' in the Local Server tab")
    console.print("  4. Run 'rss setup' again - it will auto-detect")
    console.print()
    console.print("[cyan]Ollama (simpler setup):[/cyan]")
    console.print("  1. Install from https://ollama.ai")
    console.print("  2. Run: ollama pull llama2")
    console.print("  3. Run: ollama serve")
    console.print("  4. Run 'rss setup' again - it will auto-detect")


def _select_provider(all_providers, selectable) -> None:
    """Let user select from available providers."""
    from .llm_providers import LLMConfig

    console.print()
    console.print("[bold]Select a provider:[/bold]")
    for num, p in selectable:
        status = "[green]Ready[/green]" if p["available"] else "[yellow]Needs Setup[/yellow]"
        console.print(f"  {num}. {p['name']} - {status}")
    console.print()

    choice = console.input("Enter number (or 'q' to quit): ").strip()
    if choice == "q":
        return

    try:
        idx = int(choice)
        for num, p in selectable:
            if num == idx:
                if p["available"]:
                    config = LLMConfig(provider=p["type"])
                    config.save()
                    console.print(f"[green]Configured {p['name']} as default provider.[/green]")
                    _onboard_feeds()
                else:
                    console.print(f"[yellow]{p['name']} needs to be set up first.[/yellow]")
                    _setup_new_provider(all_providers)
                return
    except ValueError:
        console.print("[red]Invalid selection[/red]")


def get_digest_summary(
    storage: Storage,
    topic_filter: Optional[str] = None,
    hours: int = 24,
) -> str:
    """
    Generate a text summary of recent articles for a digest.

    Args:
        storage: Storage instance
        topic_filter: Optional topic to filter by
        hours: How many hours back to look

    Returns:
        Formatted text summary
    """
    cutoff = datetime.now() - timedelta(hours=hours)
    articles = storage.get_articles(limit=100)

    # Filter by time
    recent = [a for a in articles if a.published and a.published > cutoff]

    if topic_filter:
        topic_lower = topic_filter.lower()
        recent = [a for a in recent if _matches_topic_keywords(a, topic_lower)]

    if not recent:
        return f"No new articles in the last {hours} hours."

    # Build summary
    lines = [f"## {len(recent)} articles in the last {hours} hours\n"]

    # Group by trend
    by_trend = {}
    for article in recent:
        trend = article.trend_tags.split(",")[0].strip() if article.trend_tags else "Uncategorized"
        if trend not in by_trend:
            by_trend[trend] = []
        by_trend[trend].append(article)

    for trend, articles_in_trend in sorted(by_trend.items(), key=lambda x: -len(x[1])):
        lines.append(f"### {trend} ({len(articles_in_trend)})")
        for article in articles_in_trend[:3]:
            summary = article.summary or article.title
            lines.append(f"- {summary}")
        if len(articles_in_trend) > 3:
            lines.append(f"  ... and {len(articles_in_trend) - 3} more")
        lines.append("")

    return "\n".join(lines)
