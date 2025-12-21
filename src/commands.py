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

console = Console(force_terminal=True, legacy_windows=True)


def update(
    feeds_file: str = "config/feeds.txt",
    db_path: str = "articles.db",
    topic_filter: Optional[str] = None,
    limit: int = 10,
    show_all: bool = False,
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
    for article in articles:
        if not article.summary:
            summary = provider.summarize(article.content)
            storage.update_summary(article.id, summary)
            article.summary = summary
            stats["summarized"] += 1

        if not article.trend_tags:
            tags = analyze_article(article)
            storage.update_trends(article.id, tags)
            article.trend_tags = tags

    # Step 5: Present the digest
    _display_digest(articles, topic_filter)
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


def _display_digest(articles: list, topic_filter: Optional[str] = None) -> None:
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

        # Title
        console.print(f"[bold cyan]{i}. {article.title}[/bold cyan]{pub_date}")

        # Summary
        summary = article.summary or "[dim]No summary available[/dim]"
        console.print(f"   {summary}")

        # Tags
        if article.trend_tags and article.trend_tags != "Uncategorized":
            console.print(f"   [dim]Tags: {article.trend_tags}[/dim]")

        # Link
        console.print(f"   [dim underline]{article.link}[/dim underline]")
        console.print()


def setup_wizard() -> None:
    """
    Interactive setup wizard to help users configure an LLM provider.
    """
    console.print(Panel("[bold]RSS Summarizer Setup[/bold]", style="blue"))
    console.print()

    # Check what's available
    console.print("[bold]Checking available providers...[/bold]\n")

    from .llm_providers import list_providers, LLMConfig, ProviderType, ClaudeProvider

    # Extended provider list including Claude
    providers = list_providers()

    # Add Claude check
    claude = ClaudeProvider()
    providers.append({
        "type": ProviderType.CLAUDE,
        "name": "Claude",
        "available": claude.is_available(),
        "description": "Claude API (for Claude Code users)",
    })

    table = Table(title="Provider Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("Description")

    available_providers = []
    for p in providers:
        status = "[green]Available[/green]" if p["available"] else "[red]Not Available[/red]"
        table.add_row(p["name"], status, p["description"])
        if p["available"] and p["type"] != ProviderType.SIMPLE:
            available_providers.append(p)

    console.print(table)
    console.print()

    if available_providers:
        best = available_providers[0]
        console.print(f"[green]Recommended:[/green] {best['name']} is ready to use!")
        console.print()

        # Save config
        config = LLMConfig(provider=best["type"])
        config.save()
        console.print(f"[dim]Saved configuration to config/llm.json[/dim]")
    else:
        console.print("[yellow]No LLM providers detected.[/yellow]")
        console.print()
        console.print(get_setup_instructions())


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
