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
from .emergence import detect_emerging_trends, format_emerging_trend
from .knowledge import (
    KnowledgeBase,
    extract_insights_from_article,
    extract_triples_from_article,
    extract_entity_relationships_from_article,
    detect_connections,
    format_relationship,
    query_knowledge_base,
)
from .cli_perspectives import add_perspective_commands
from .cli_constitution import add_constitution_commands
from .cli_signal_tags import app as signal_tags_app
from .cli_schedule import app as schedule_app
from .cli_context import app as context_app
from .cli_stories import app as stories_app
from .cli_cross_source import app as cross_source_app

app = typer.Typer(
    name="rss",
    help="AI-powered RSS feed summarizer with trend prediction.",
    add_completion=False,
)
# Use force_terminal to avoid Windows console encoding issues
console = Console(force_terminal=True, legacy_windows=True)

# Register perspective commands (perspectives, perspective-config, cluster-stories)
add_perspective_commands(app)

# Register constitution commands (constitution, constitution-create)
add_constitution_commands(app)

# Register signal tagging commands as subcommand group
app.add_typer(signal_tags_app, name="tag", help="Signal tag management commands")

# Register schedule commands as subcommand group
app.add_typer(schedule_app, name="schedule", help="Background fetch scheduling")

# Register context commands as subcommand group
app.add_typer(context_app, name="context", help="User context management")

# Register stories commands as subcommand group
app.add_typer(stories_app, name="stories", help="Story management commands")

# Register cross-source comparison commands
app.add_typer(cross_source_app, name="sources", help="Cross-source comparison and diverse feeds")


def is_setup_complete() -> bool:
    """Check if LLM provider has been configured."""
    return Path("config/llm.json").exists()


def require_setup():
    """Exit with message if setup not complete."""
    if not is_setup_complete():
        console.print("[yellow]Setup required.[/yellow] Run [bold]rss setup[/bold] first.")
        raise typer.Exit(1)


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
    require_setup()
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
        help="Use LLM for summarization (requires transformers)",
    ),
    tag: bool = typer.Option(
        False,
        "--tag",
        help="Also assign signal tags to articles",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Summarize articles that haven't been summarized yet."""
    require_setup()
    storage = get_storage(db_path)

    console.print(f"[bold]Summarizing up to {limit} articles...[/bold]")
    if use_llm:
        console.print("[dim]Using LLM backend (this may take a while)[/dim]")
    else:
        console.print("[dim]Using simple extractive summarizer[/dim]")

    if tag:
        console.print("[dim]Signal tagging enabled[/dim]\n")
    else:
        console.print()

    stats = summarize_articles(storage, limit=limit, use_llm=use_llm, tag_articles=tag)

    console.print(f"[green]Summarized {stats['processed']} articles[/green]")

    if tag and stats.get('tagged', 0) > 0:
        console.print(f"[green]Tagged {stats['tagged']} articles[/green]")

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
    require_setup()
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

    # Show emerging trends if any
    if stats.get("emerging"):
        console.print()
        console.print("[bold green]Emerging Trends[/bold green] (gaining traction)")
        for tag, velocity in stats["emerging"]:
            if velocity == 100:
                console.print(f"  [green]+[/green] {tag} [dim](new)[/dim]")
            else:
                console.print(f"  [green]+{velocity:.0f}%[/green] {tag}")

    # Show declining trends if any
    if stats.get("declining"):
        console.print()
        console.print("[bold red]Declining Trends[/bold red] (losing traction)")
        for tag, velocity in stats["declining"]:
            console.print(f"  [red]{velocity:.0f}%[/red] {tag}")

    console.print(f"\n[dim]Analyzed {stats['processed']} articles (last {stats.get('hours', 24)}h window)[/dim]")


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
    topic_words: Optional[list[str]] = typer.Argument(
        None,
        help="Filter by topic (e.g., 'tech', 'AI news', 'politics')",
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
    show_scores: bool = typer.Option(
        False,
        "--show-scores",
        help="Show relevance scores for each article",
    ),
    min_relevance: float = typer.Option(
        0.0,
        "--min-relevance",
        help="Filter articles below this relevance score (0-1)",
    ),
    no_context: bool = typer.Option(
        False,
        "--no-context",
        help="Disable personalization",
    ),
):
    """
    Check what's new in your feeds.

    Fetches latest articles, generates summaries, and shows you what's new.
    Optionally filter by topic like 'tech', 'politics', 'health', etc.

    Examples:
        rss update              # Show all new articles
        rss update tech         # Show only tech-related articles
        rss update AI news      # Multiple words work without quotes
        rss update --all        # Show recent articles even if not new
        rss update --show-scores        # Show relevance scores
        rss update --min-relevance 0.7  # Only high-relevance articles
    """
    require_setup()
    from .commands import update as do_update

    # Concatenate topic words into single string
    topic = " ".join(topic_words) if topic_words else None

    do_update(
        topic_filter=topic,
        limit=limit,
        show_all=all_articles,
        use_context=not no_context,
        show_scores=show_scores,
        min_relevance=min_relevance,
    )


@app.command()
def report(
    limit: int = typer.Option(
        20,
        "--limit", "-n",
        help="Maximum number of articles to process",
    ),
    max_per_step: int = typer.Option(
        0,
        "--max-per-step", "-m",
        help="Limit items per step (0=unlimited). Use -m 5 to process incrementally when catching up on a large backlog.",
    ),
    skip_summarized: bool = typer.Option(
        True,
        "--skip-summarized/--reprocess",
        help="Skip already-summarized articles",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    Generate a comprehensive report with live progress.

    This is the full LLM-powered analysis workflow. Watch as each article
    is processed - summaries generated, knowledge extracted, connections found.

    The live display shows you what's happening in real-time, like watching
    over someone's shoulder as they read and analyze the news.

    Examples:
        rss report              # Process up to 20 articles
        rss report --limit 50   # Process more articles
        rss report --reprocess  # Re-analyze already-summarized articles
    """
    require_setup()
    from .report import generate_report

    generate_report(
        limit=limit,
        skip_summarized=skip_summarized,
        db_path=db_path,
        kb_path=kb_path,
        max_per_step=max_per_step,
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
    require_setup()
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

Return real, working RSS feed URLs with their descriptions.
Focus on well-known, reliable sources. Include as many relevant feeds as you can identify.

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


@app.command(name="help")
def help_cmd(
    command: Optional[str] = typer.Argument(None, help="Command to get help for"),
):
    """
    Show help information.

    Examples:
        rss help            # Show all commands
        rss help update     # Show help for update command
    """
    import subprocess
    import sys

    if command:
        # Show help for specific command
        subprocess.run([sys.executable, "-m", "src.cli", command, "--help"])
        return

    # Custom help showing setup status
    setup_done = is_setup_complete()
    
    console.print("[bold]RSS Summarizer[/bold] - AI-powered RSS feed summaries")
    console.print()
    
    if not setup_done:
        console.print("[yellow]Run 'rss setup' to get started[/yellow]")
        console.print()
    
    # Commands that work without setup
    console.print("[bold]Setup Commands:[/bold]")
    console.print("  setup       Set up LLM provider (run this first!)")
    console.print("  providers   Show available LLM providers")
    console.print("  add-feed    Add a new RSS feed")
    console.print()
    
    # Commands that require setup
    style = "" if setup_done else "dim"
    console.print("[bold]Main Commands:[/bold]" + ("" if setup_done else " [dim](requires setup)[/dim]"))
    if setup_done:
        console.print("  update      Check what's new in your feeds")
        console.print("  report      Full analysis with live progress display")
        console.print("  discover    Find new feeds based on interests")
        console.print("  trends      Analyze trending topics")
    else:
        console.print("  [dim]update      Check what's new in your feeds[/dim]")
        console.print("  [dim]report      Full analysis with live progress display[/dim]")
        console.print("  [dim]discover    Find new feeds based on interests[/dim]")
        console.print("  [dim]trends      Analyze trending topics[/dim]")
    console.print()

    console.print("[bold]Info Commands:[/bold]")
    console.print("  list        List fetched articles")
    console.print("  stats       Show database statistics")
    console.print("  help        Show this help")
    console.print()

    console.print("[bold]Automation:[/bold]")
    console.print("  schedule enable   Set up automatic background fetching")
    console.print("  schedule disable  Turn off automatic fetching")
    console.print("  schedule status   Check current schedule")
    console.print()

    console.print("[bold]Advanced Analysis:[/bold]")
    console.print("  perspectives      View multi-source perspectives on stories")
    console.print("  cluster-stories   Group articles into story clusters")
    console.print("  emerging          Detect emerging trends early")
    console.print("  tag               Signal tag management (articles, filter, stats)")
    console.print("  context           User context management (add, list, remove)")
    console.print()
    console.print("[bold]Cross-Source Comparison:[/bold]")
    console.print("  sources compare   Compare how different outlets cover a story")
    console.print("  sources balance   Show political balance of your feeds")
    console.print("  sources suggest   Get suggestions for diverse sources")
    console.print("  sources multi     List stories covered by multiple sources")


@app.command()
def providers():
    """
    Show available LLM providers and their status.

    Lists all supported providers and whether they're currently available.
    """
    from .llm_providers import list_providers

    all_providers = list_providers()

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


@app.command()
def extract_knowledge(
    limit: int = typer.Option(
        10,
        "--limit", "-n",
        help="Number of articles to process",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to articles database",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Extract knowledge insights from recent articles."""
    require_setup()
    from .llm_providers import get_best_provider, ensure_llm_or_exit

    provider = ensure_llm_or_exit(require_llm=True)
    storage = get_storage(db_path)
    kb = KnowledgeBase(kb_path)

    console.print(f"[bold]Extracting knowledge from up to {limit} articles...[/bold]\n")

    # Get articles without insights extracted yet
    articles = storage.get_articles(limit=limit)

    if not articles:
        console.print("[yellow]No articles found.[/yellow]")
        console.print("Run 'rss fetch' first to fetch some articles.")
        raise typer.Exit(1)

    extracted_count = 0
    total_insights = 0

    for article in articles:
        console.print(f"[dim]Processing: {article.title[:60]}...[/dim]")

        try:
            insights = extract_insights_from_article(article, provider, kb)

            if insights:
                extracted_count += 1
                total_insights += len(insights)

                # Detect connections between insights
                for insight in insights:
                    relationships = detect_connections(insight, kb, provider)
                    if relationships:
                        for rel in relationships:
                            formatted = format_relationship(rel, kb)
                            console.print(f"  [green]→ {formatted}[/green]")

            # Extract knowledge graph triples
            triples = extract_triples_from_article(article, provider, kb)
            if triples:
                console.print(f"  [cyan]Extracted {len(triples)} triples[/cyan]")

            # Extract entity relationships
            entity_rels = extract_entity_relationships_from_article(article, provider, kb)
            if entity_rels:
                console.print(f"  [cyan]Found {len(entity_rels)} entity relationships[/cyan]")

        except Exception as e:
            console.print(f"  [red]Error: {str(e)}[/red]")

    console.print()
    console.print(
        f"[green]Extracted {total_insights} insights from {extracted_count} articles[/green]"
    )

    # Show stats
    stats = kb.get_stats()
    console.print(f"[dim]Knowledge base now contains {stats['total_insights']} insights[/dim]")

    if stats["contradictions"] > 0:
        console.print(
            f"[yellow]Found {stats['contradictions']} contradictions[/yellow] - run 'rss contradictions' to view"
        )


@app.command()
def query(
    query_text: str = typer.Argument(..., help="Natural language query"),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Query the knowledge base using natural language."""
    require_setup()
    from .llm_providers import get_best_provider, ensure_llm_or_exit

    provider = ensure_llm_or_exit(require_llm=True)
    kb = KnowledgeBase(kb_path)

    console.print(f"[bold]Query:[/bold] {query_text}\n")

    result = query_knowledge_base(query_text, kb, provider)

    console.print(Panel(result["summary"], title="Answer", border_style="blue"))
    console.print()
    console.print(f"[dim]Based on {result['total_insights']} insights in knowledge base[/dim]")


@app.command()
def contradictions(
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Show contradictions found in the knowledge base."""
    kb = KnowledgeBase(kb_path)

    relationships = kb.get_relationships(relationship_type="contradicts")

    if not relationships:
        console.print("[green]No contradictions found in knowledge base.[/green]")
        return

    console.print(f"[bold]Found {len(relationships)} contradictions:[/bold]\n")

    for rel in relationships:
        source = kb.get_insight(rel.source_insight_id)
        target = kb.get_insight(rel.target_insight_id)

        if source and target:
            console.print("[yellow]CONTRADICTION:[/yellow]")
            console.print(f"  A: {source.content}")
            console.print(f"     [dim]({source.confidence} confidence)[/dim]")
            console.print(f"  B: {target.content}")
            console.print(f"     [dim]({target.confidence} confidence)[/dim]")
            console.print()


@app.command(name="knowledge-stats")
def knowledge_stats(
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Show knowledge base statistics."""
    kb = KnowledgeBase(kb_path)
    stats = kb.get_stats()

    console.print(Panel("[bold]Knowledge Base Statistics[/bold]", style="blue"))
    console.print()

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Total Insights", str(stats["total_insights"]))
    table.add_row("High Confidence", str(stats["high_confidence_insights"]))
    table.add_row("Entities Tracked", str(stats["total_entities"]))
    table.add_row("Relationships", str(stats["total_relationships"]))
    table.add_row("Contradictions", str(stats["contradictions"]))

    console.print(table)


@app.command()
def graph(
    entity: str = typer.Argument(..., help="Entity name to explore"),
    depth: int = typer.Option(2, "--depth", "-d", help="Max traversal depth"),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Explore the knowledge graph around an entity."""
    kb = KnowledgeBase(kb_path)

    # First, get the entity neighborhood (1-hop)
    neighborhood = kb.get_entity_neighborhood(entity)

    if not neighborhood["outgoing"] and not neighborhood["incoming"]:
        console.print(f"[yellow]No relationships found for '{entity}'[/yellow]")
        console.print("[dim]Try running 'rss update' to extract knowledge from articles.[/dim]")
        return

    console.print(Panel(f"[bold]Knowledge Graph: {entity}[/bold]", style="blue"))
    console.print()

    # Show outgoing relationships
    if neighborhood["outgoing"]:
        console.print("[bold cyan]Outgoing relationships:[/bold cyan]")
        for rel in neighborhood["outgoing"][:15]:
            console.print(f"  {entity} --[{rel['predicate']}]--> {rel['target']}")
        if len(neighborhood["outgoing"]) > 15:
            console.print(f"  [dim]... and {len(neighborhood['outgoing']) - 15} more[/dim]")
        console.print()

    # Show incoming relationships
    if neighborhood["incoming"]:
        console.print("[bold magenta]Incoming relationships:[/bold magenta]")
        for rel in neighborhood["incoming"][:15]:
            console.print(f"  {rel['source']} --[{rel['predicate']}]--> {entity}")
        if len(neighborhood["incoming"]) > 15:
            console.print(f"  [dim]... and {len(neighborhood['incoming']) - 15} more[/dim]")
        console.print()

    # Get connected entities at depth
    if depth > 1:
        connected = kb.get_connected_entities(entity, max_depth=depth)
        console.print(f"[dim]Found {len(connected['entities'])} connected entities within {depth} hops[/dim]")


@app.command(name="graph-path")
def graph_path(
    start: str = typer.Argument(..., help="Starting entity"),
    end: str = typer.Argument(..., help="Ending entity"),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Find a path between two entities in the knowledge graph."""
    kb = KnowledgeBase(kb_path)

    path = kb.find_path(start, end)

    if path is None:
        console.print(f"[yellow]No path found between '{start}' and '{end}'[/yellow]")
        return

    if not path:
        console.print(f"[green]'{start}' and '{end}' are the same entity[/green]")
        return

    console.print(Panel(f"[bold]Path: {start} -> {end}[/bold]", style="green"))
    console.print()

    for i, step in enumerate(path):
        console.print(f"  {step['from']} --[{step['predicate']}]--> {step['to']}")

    console.print()
    console.print(f"[dim]Path length: {len(path)} hop(s)[/dim]")


@app.command(name="graph-stats")
def graph_stats(
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Show knowledge graph statistics."""
    kb = KnowledgeBase(kb_path)
    stats = kb.get_graph_stats()

    console.print(Panel("[bold]Knowledge Graph Statistics[/bold]", style="blue"))
    console.print()

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Total Insights", str(stats["total_insights"]))
    table.add_row("Total Entities", str(stats["total_entities"]))
    table.add_row("Total Triples", str(stats["total_triples"]))
    table.add_row("Entity Relationships", str(stats["total_entity_relationships"]))
    table.add_row("Unique Predicates", str(stats["unique_predicates"]))
    table.add_row("Embeddings", str(stats["total_embeddings"]))

    console.print(table)

    if stats["predicate_types"]:
        console.print()
        console.print("[bold]Predicate types:[/bold]")
        for pred in stats["predicate_types"][:20]:
            console.print(f"  - {pred}")

    if stats["top_connected_entities"]:
        console.print()
        console.print("[bold]Most connected entities:[/bold]")
        for ent in stats["top_connected_entities"]:
            console.print(f"  - {ent['entity']}: {ent['connections']} connections")


@app.command()
def context_add(
    context_type: str = typer.Argument(..., help="Type: project/interest/watching"),
    name: str = typer.Argument(..., help="Context name"),
    description: str = typer.Option(None, "--desc", "-d", help="Description"),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """Add user context (project, interest, watching)."""
    import uuid
    from .knowledge import UserContext

    kb = KnowledgeBase(kb_path)

    context = UserContext(
        id=str(uuid.uuid4()),
        context_type=context_type,
        name=name,
        description=description,
    )

    kb.save_context(context)
    console.print(f"[green]Added {context_type}: {name}[/green]")


@app.command()
def context_list(
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """List user contexts."""
    kb = KnowledgeBase(kb_path)
    contexts = kb.get_contexts(active_only=False)

    if not contexts:
        console.print("[yellow]No contexts configured.[/yellow]")
        console.print("Add one with: rss context-add project 'Project Name'")
        return

    table = Table(title="User Contexts")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status")
    table.add_column("Description")

    for ctx in contexts:
        status = "[green]Active[/green]" if ctx.active else "[dim]Inactive[/dim]"
        desc = ctx.description or ""
        table.add_row(ctx.context_type, ctx.name, status, desc[:50])

    console.print(table)


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

    Story Analysis:

        rss perspectives        # View multi-source perspectives on stories
        rss cluster-stories     # Group articles into story clusters
        rss emerging            # Detect emerging trends early
        rss tag articles        # Assign signal tags to articles
        rss tag filter          # Filter articles by tags

    Knowledge Base:

        rss extract-knowledge   # Extract insights from articles
        rss query "question"    # Query knowledge base
        rss contradictions      # View contradictions
        rss knowledge-stats     # Show KB statistics
        rss context-add         # Add user context
        rss context-list        # List contexts
    """
    pass


if __name__ == "__main__":
    app()


@app.command()
def emerging(
    confidence: str = typer.Option(
        "all",
        "--confidence", "-c",
        help="Filter by confidence level: high, medium, low, watch, all",
    ),
    limit: int = typer.Option(
        10,
        "--limit", "-n",
        help="Maximum number of trends to show",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """
    Show emerging trends before they go mainstream.

    Detects weak signals and terminology that's gaining traction
    before it becomes widespread. Useful for staying ahead of trends.

    Examples:
        rss emerging                    # Show all emerging trends
        rss emerging --confidence high  # Only high-confidence trends
        rss emerging --limit 5          # Show top 5
    """
    require_setup()
    storage = get_storage(db_path)

    console.print("[bold]Detecting emerging trends...[/bold]\n")

    # Map confidence filter
    confidence_map = {
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "watch": "Watch",
        "all": "Watch",  # Show all, starting from "Watch" level
    }

    min_confidence = confidence_map.get(confidence.lower(), "Low")

    try:
        trends = detect_emerging_trends(
            storage,
            limit=1000,
            min_confidence=min_confidence,
        )
    except Exception as e:
        console.print(f"[red]Error detecting emerging trends: {e}[/red]")
        console.print("[yellow]Note: Emergence detection requires at least 4 weeks of article history.[/yellow]")
        raise typer.Exit(1)

    if not trends:
        console.print("[yellow]No emerging trends detected.[/yellow]")
        console.print("\nPossible reasons:")
        console.print("  - Not enough historical data (need 4+ weeks)")
        console.print("  - No terms meeting emergence criteria")
        console.print("  - Articles need trend tags (run 'rss trends' first)")
        raise typer.Exit(0)

    # Group by confidence
    by_confidence = {"High": [], "Medium": [], "Low": [], "Watch": []}
    for trend in trends[:limit]:
        by_confidence[trend.confidence].append(trend)

    # Display each confidence level
    for conf_level in ["High", "Medium", "Low", "Watch"]:
        level_trends = by_confidence[conf_level]
        if not level_trends:
            continue

        # Styling by confidence
        if conf_level == "High":
            header = "[bold green]HIGH CONFIDENCE EMERGING[/bold green]"
        elif conf_level == "Medium":
            header = "[bold yellow]MEDIUM CONFIDENCE EMERGING[/bold yellow]"
        elif conf_level == "Low":
            header = "[bold blue]LOW CONFIDENCE EMERGING[/bold blue]"
        else:
            header = "[bold dim]WATCH LIST (Early Signals)[/bold dim]"

        console.print(header)
        console.print("=" * 60)
        console.print()

        for trend in level_trends:
            formatted = format_emerging_trend(trend, storage)
            console.print(formatted)
            console.print()

    total_shown = sum(len(by_confidence[c]) for c in by_confidence)
    console.print(f"[dim]Showing {total_shown} of {len(trends)} emerging trends detected[/dim]")

    if len(trends) > limit:
        console.print(f"[dim]Use --limit {len(trends)} to see all trends[/dim]")
