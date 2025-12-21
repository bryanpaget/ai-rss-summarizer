"""Command-line interface for the RSS summarizer."""


from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .storage import Storage
from .rss import fetch_all_feeds, load_feeds
from .summarizer import summarize_articles
from .trends import analyze_trends, get_articles_by_trend
from .llm_providers import get_best_provider

app = typer.Typer(
    name="rss",
    help="AI-powered RSS feed summarizer with trend prediction.",
    add_completion=False,
)
# Use force_terminal to avoid Windows console encoding issues
console = Console(force_terminal=True, legacy_windows=True)


def get_storage(db_path: str = "articles.db") -> Storage:
    """Get storage instance."""
    return Storage(db_path)


@app.command()
def fetch(
    feeds_file: str = typer.Option(
        "config/feeds.txt",
        "--feeds", "-f",
        help="Path to feeds file",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Fetch articles from all configured RSS feeds."""
    storage = get_storage(db_path)
    feeds = load_feeds(feeds_file)

    if not feeds:
        console.print(f"[red]No feeds found in {feeds_file}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Fetching from {len(feeds)} feeds...[/bold]\n")

    results = fetch_all_feeds(feeds_file, storage)

    # Display results
    table = Table(title="Fetch Results")
    table.add_column("Feed", style="cyan", max_width=50)
    table.add_column("Fetched", justify="right")
    table.add_column("New", justify="right", style="green")
    table.add_column("Status")

    total_fetched = 0
    total_new = 0

    for result in results:
        status = "[green]OK[/green]" if not result["errors"] else "[yellow]Warnings[/yellow]"
        # Truncate long URLs
        url = result["url"]
        if len(url) > 50:
            url = url[:47] + "..."

        table.add_row(
            url,
            str(result["fetched"]),
            str(result["new"]),
            status,
        )
        total_fetched += result["fetched"]
        total_new += result["new"]

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {total_fetched} articles fetched, {total_new} new")


@app.command()
def summarize(
    limit: int = typer.Option(
        10,
        "--limit", "-n",
        help="Maximum number of articles to summarize",
    ),
    use_llm: bool = typer.Option(
        False,
        "--llm",
        help="Use LLM for summarization (requires transformers or configured provider)",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Summarize articles that haven't been summarized yet."""
    storage = get_storage(db_path)

    console.print(f"[bold]Summarizing up to {limit} articles...[/bold]")

    if use_llm:
        # Use the configured LLM provider
        provider, is_llm_available = get_best_provider()
        if is_llm_available:
            console.print(f"[dim]Using {provider.name} for summaries[/dim]\n")

            # Get unsummarized articles
            articles = storage.get_articles(limit=limit, unsummarized_only=True)

            stats = {"processed": 0, "errors": []}

            for article in articles:
                try:
                    summary = provider.summarize(article.content)
                    storage.update_summary(article.id, summary)
                    stats["processed"] += 1
                except Exception as e:
                    stats["errors"].append(f"Error summarizing {article.id}: {str(e)}")
        else:
            console.print("[yellow]No LLM provider available. Using simple summarizer.[/yellow]")
            stats = summarize_articles(storage, limit=limit, use_llm=False)
    else:
        console.print("[dim]Using simple extractive summarizer[/dim]\n")
        stats = summarize_articles(storage, limit=limit, use_llm=False)

    console.print(f"[green]Summarized {stats['processed']} articles[/green]")

    if stats["errors"]:
        console.print(f"[yellow]Errors: {len(stats['errors'])}[/yellow]")
        for error in stats["errors"][:5]:
            console.print(f"  [dim]{error}[/dim]")


@app.command()
def trends(
    limit: int = typer.Option(
        100,
        "--limit", "-n",
        help="Number of articles to analyze",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Analyze trends across fetched articles."""
    storage = get_storage(db_path)

    console.print(f"[bold]Analyzing trends across up to {limit} articles...[/bold]\n")

    stats = analyze_trends(storage, limit=limit)

    if not stats["top_trends"]:
        console.print("[yellow]No articles found to analyze.[/yellow]")
        console.print("Run 'rss fetch' first to fetch some articles.")
        raise typer.Exit(1)

    table = Table(title="Top Trends")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Bar")

    max_count = stats["top_trends"][0][1] if stats["top_trends"] else 1

    for category, count in stats["top_trends"]:
        bar_width = int((count / max_count) * 20)
        bar = "[green]" + "#" * bar_width + "[/green]"
        table.add_row(category, str(count), bar)

    console.print(table)
    console.print(f"\n[dim]Analyzed {stats['processed']} articles[/dim]")


@app.command("list")
def list_articles(
    limit: int = typer.Option(
        20,
        "--limit", "-n",
        help="Number of articles to show",
    ),
    trend: Optional[str] = typer.Option(
        None,
        "--trend", "-t",
        help="Filter by trend category",
    ),
    show_summary: bool = typer.Option(
        False,
        "--summary", "-s",
        help="Show article summaries",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """List fetched articles."""
    storage = get_storage(db_path)

    if trend:
        articles = get_articles_by_trend(storage, trend, limit=limit)
        title = f"Articles: {trend}"
    else:
        articles = storage.get_articles(limit=limit)
        title = "Recent Articles"

    if not articles:
        console.print("[yellow]No articles found.[/yellow]")
        if not trend:
            console.print("Run 'rss fetch' first to fetch some articles.")
        raise typer.Exit(1)

    table = Table(title=title)
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Published", width=12)
    table.add_column("Trends", style="green", max_width=25)

    for i, article in enumerate(articles, 1):
        pub_date = ""
        if article.published:
            pub_date = str(article.published)[:10]

        trends_str = article.trend_tags or "[dim]-[/dim]"
        if len(trends_str) > 25:
            trends_str = trends_str[:22] + "..."

        title_str = article.title
        if len(title_str) > 50:
            title_str = title_str[:47] + "..."

        table.add_row(str(i), title_str, pub_date, trends_str)

    console.print(table)

    if show_summary:
        console.print("\n[bold]Summaries:[/bold]")
        for i, article in enumerate(articles[:5], 1):
            summary = article.summary or "[dim]No summary yet[/dim]"
            console.print(Panel(
                summary,
                title=f"[cyan]{i}. {article.title[:60]}[/cyan]",
                border_style="dim",
            ))


@app.command()
def stats(
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Show statistics about the database."""
    storage = get_storage(db_path)

    total = storage.get_article_count()
    feed_stats = storage.get_feed_stats()

    console.print(Panel(
        f"[bold]Total Articles:[/bold] {total}",
        title="Database Statistics",
    ))

    if feed_stats:
        table = Table(title="Articles by Feed")
        table.add_column("Feed", style="cyan", max_width=50)
        table.add_column("Articles", justify="right")
        table.add_column("Summarized", justify="right", style="green")
        table.add_column("Latest")

        for stat in feed_stats:
            url = stat["feed_url"]
            if len(url) > 50:
                url = url[:47] + "..."

            latest = stat["latest_article"] or "-"
            if len(str(latest)) > 10:
                latest = str(latest)[:10]

            table.add_row(
                url,
                str(stat["article_count"]),
                str(stat["summarized_count"]),
                latest,
            )

        console.print(table)


@app.command()
def add_feed(
    url: str = typer.Argument(..., help="RSS feed URL to add"),
    feeds_file: str = typer.Option(
        "config/feeds.txt",
        "--feeds", "-f",
        help="Path to feeds file",
    ),
):
    """Add a new RSS feed to the feeds file."""
    feeds_path = Path(feeds_file)

    # Create file if it doesn't exist
    if not feeds_path.exists():
        feeds_path.parent.mkdir(parents=True, exist_ok=True)
        feeds_path.touch()

    # Check if already exists
    existing = load_feeds(feeds_file)
    if url in existing:
        console.print(f"[yellow]Feed already exists: {url}[/yellow]")
        raise typer.Exit(1)

    # Append to file
    with open(feeds_path, "a") as f:
        f.write(f"\n{url}")

    console.print(f"[green]Added feed: {url}[/green]")


# =============================================================================
# USER-FRIENDLY COMMANDS
# =============================================================================


@app.command()
def update(
    topic: Optional[str] = typer.Argument(
        None,
        help="Filter by topic (e.g., 'tech', 'politics', 'health')",
    ),
    limit: int = typer.Option(
        10,
        "--limit", "-n",
        help="Number of articles to show",
    ),
    all_articles: bool = typer.Option(
        False,
        "--all", "-a",
        help="Show all articles, not just new ones",
    ),
):
    """
    Check what's new in your feeds.

    Fetches latest articles, generates summaries, and shows you what's new.
    Optionally filter by topic like 'tech', 'politics', 'health', etc.

    Examples:
        rss update              # Show all new articles
        rss update tech         # Show only tech-related articles
        rss update --all        # Show recent articles even if not new
    """
    from .commands import update as do_update

    do_update(
        topic_filter=topic,
        limit=limit,
        show_all=all_articles,
    )


@app.command()
def setup():
    """
    Set up the RSS summarizer with an LLM provider.

    Detects available LLM providers and helps you configure one for
    AI-powered summaries. Supports:
    - LM Studio (local, free)
    - Ollama (local, free)
    - Claude (for Claude Code users)
    - OpenAI (requires API key)
    """
    from .commands import setup_wizard

    setup_wizard()


@app.command()
def discover(
    query: str = typer.Argument(
        ...,
        help="What topics or sources are you interested in?",
    ),
):
    """
    Discover new RSS feeds based on your interests.

    Uses AI to find relevant RSS feeds for topics you're interested in.

    Examples:
        rss discover "AI and machine learning news"
        rss discover "Python programming"
        rss discover "climate change and environment"
    """
    from .llm_providers import get_best_provider, get_setup_instructions

    provider, is_llm = get_best_provider()

    if not is_llm:
        console.print("[yellow]LLM required for feed discovery.[/yellow]")
        console.print(get_setup_instructions())
        raise typer.Exit(1)

    console.print(f"[bold]Searching for feeds about: {query}[/bold]")
    console.print(f"[dim]Using {provider.name}...[/dim]\n")

    # Use the LLM to suggest feeds
    prompt = f"""Find RSS feeds for someone interested in: {query}

Return a list of 5-10 real, working RSS feed URLs with their descriptions.
Focus on well-known, reliable sources.

Format each as:
- [Source Name]: [URL]
  Description of what this feed covers.

Only include feeds you're confident are real and active."""

    try:
        # Use the provider's underlying API for this
        if hasattr(provider, '_get_client'):
            # Claude provider
            client = provider._get_client()
            message = client.messages.create(
                model=provider.model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            response = message.content[0].text
        elif hasattr(provider, 'base_url'):
            # OpenAI-compatible provider
            import httpx

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider.api_key}",
            }
            payload = {
                "model": provider._get_model(),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }
            resp = httpx.post(
                f"{provider.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            data = resp.json()
            response = data["choices"][0]["message"]["content"]
        else:
            console.print("[yellow]Feed discovery not supported with this provider.[/yellow]")
            raise typer.Exit(1)

        # Display results
        console.print(Panel("[bold]Suggested Feeds[/bold]", style="green"))
        console.print(response)
        console.print()
        console.print("[dim]To add a feed, use: rss add-feed <URL>[/dim]")

    except Exception as e:
        console.print(f"[red]Error discovering feeds: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def providers():
    """
    Show available LLM providers and their status.

    Lists all supported providers and whether they're currently available.
    """
    from .llm_providers import list_providers, ClaudeProvider, ProviderType

    all_providers = list_providers()

    # Add Claude
    claude = ClaudeProvider()
    all_providers.append({
        "type": ProviderType.CLAUDE,
        "name": "Claude",
        "available": claude.is_available(),
        "description": "Claude API (for Claude Code users)",
    })

    table = Table(title="LLM Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status")
    table.add_column("Description")

    for p in all_providers:
        status = "[green]Available[/green]" if p["available"] else "[dim]Not Available[/dim]"
        table.add_row(p["name"], status, p["description"])

    console.print(table)
    console.print()
    console.print("[dim]Run 'rss setup' to configure a provider.[/dim]")


@app.callback()
def main():
    """
    AI RSS Summarizer - Stay updated with AI-powered RSS summaries.

    Quick start:

        rss update              # See what's new across all feeds
        rss update tech         # See only tech news
        rss discover "topic"    # Find new feeds to follow

    Setup:

        rss setup               # Configure an LLM provider
        rss add-feed URL        # Add a new RSS feed

    Advanced:

        rss fetch               # Fetch articles (runs automatically)
        rss summarize           # Generate summaries (runs automatically)
        rss trends              # See trending topics
        rss list                # List all articles
    """
    pass


if __name__ == "__main__":
    app()
