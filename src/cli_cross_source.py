"""CLI commands for cross-source comparison and diverse source management."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .storage import Storage
from .knowledge import KnowledgeBase
from .cross_source import (
    get_stories_with_multiple_sources,
    compare_story_coverage,
    format_comparison,
    get_current_feed_leanings,
    suggest_diverse_sources,
    get_source_name,
    DIVERSE_FEEDS,
)

app = typer.Typer(
    name="sources",
    help="Cross-source comparison and diverse source management.",
)
console = Console(force_terminal=True, legacy_windows=True)


@app.command("compare")
def compare_sources(
    story_id: str = typer.Argument(None, help="Story ID to compare (or omit for auto-select)"),
    db_path: str = typer.Option("articles.db", "--db", "-d", help="Database path"),
    kb_path: str = typer.Option("knowledge.db", "--kb", "-k", help="Knowledge base path"),
):
    """
    Compare how different sources cover the same story.

    Shows different perspectives, framing, and what facts each source
    emphasizes or omits. Useful for detecting bias and getting a
    complete picture.

    Examples:
        rss sources compare                    # Auto-select best story
        rss sources compare abc123             # Compare specific story
    """
    storage = Storage(db_path)
    kb = KnowledgeBase(kb_path)

    if story_id:
        # Get specific story
        story = storage.get_story(story_id)
        if not story:
            console.print(f"[red]Story not found: {story_id}[/red]")
            raise typer.Exit(1)
        stories = [story]
    else:
        # Find stories with multiple sources
        stories = get_stories_with_multiple_sources(storage, min_sources=2, limit=5)

    if not stories:
        console.print("[yellow]No stories found with multiple source coverage.[/yellow]")
        console.print()
        console.print("To enable cross-source comparison:")
        console.print("  1. Add feeds from different sources: rss sources suggest")
        console.print("  2. Run a report to cluster articles: rss report")
        raise typer.Exit(0)

    console.print(Panel("[bold]CROSS-SOURCE COMPARISON[/bold]", style="blue"))
    console.print()

    for story in stories:
        comparison = compare_story_coverage(story, storage, kb)

        # Header
        source_count = len(comparison.sources)
        console.print(f"[bold cyan]{story.title}[/bold cyan]")
        console.print(f"[dim]Covered by {source_count} sources[/dim]")
        console.print()

        # Show each source's take
        for perspective in comparison.sources:
            leaning = comparison.bias_indicators.get(perspective.source_name, "")
            leaning_color = {
                "left": "blue",
                "left-center": "cyan",
                "center-left": "cyan",
                "center": "white",
                "center-right": "yellow",
                "right": "red",
                "far-left": "blue",
                "far-right": "red",
            }.get(leaning, "dim")

            leaning_str = f" [{leaning_color}]({leaning})[/{leaning_color}]" if leaning else ""

            console.print(f"  [bold]{perspective.source_name}[/bold]{leaning_str}")
            console.print(f"    Framing: {perspective.framing}")

            if perspective.emphasis:
                console.print(f"    Focus: {', '.join(perspective.emphasis)}")

            if perspective.key_claims:
                console.print("    Claims:")
                for claim in perspective.key_claims[:3]:
                    console.print(f"      - {claim}")

            console.print()

        # Common ground
        if comparison.common_facts:
            console.print("[green]Common facts (agreed by multiple sources):[/green]")
            for fact in comparison.common_facts[:5]:
                console.print(f"  - {fact}")
            console.print()

        # Coverage gaps
        if comparison.coverage_gap:
            console.print("[yellow]Coverage gaps (mentioned by some, not all):[/yellow]")
            for gap in comparison.coverage_gap[:5]:
                console.print(f"  - {gap}")
            console.print()

        console.print("-" * 60)
        console.print()


@app.command("multi")
def list_multi_source_stories(
    min_sources: int = typer.Option(2, "--min", "-m", help="Minimum sources required"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum stories to show"),
    db_path: str = typer.Option("articles.db", "--db", "-d", help="Database path"),
):
    """
    List stories covered by multiple sources.

    Shows stories that have been covered by different news outlets,
    which are good candidates for cross-source comparison.
    """
    storage = Storage(db_path)

    stories = get_stories_with_multiple_sources(storage, min_sources=min_sources, limit=limit)

    if not stories:
        console.print("[yellow]No stories found with multiple source coverage.[/yellow]")
        console.print(f"[dim]Required: {min_sources}+ unique sources per story[/dim]")
        raise typer.Exit(0)

    table = Table(title="Multi-Source Stories")
    table.add_column("Story", style="cyan", max_width=50)
    table.add_column("Sources", justify="center")
    table.add_column("Articles", justify="center")
    table.add_column("ID", style="dim")

    for story in stories:
        articles = storage.get_articles_by_ids(story.article_ids)
        unique_sources = set()
        for article in articles:
            from .cross_source import extract_domain
            unique_sources.add(extract_domain(article.feed_url))

        table.add_row(
            story.title[:50],
            str(len(unique_sources)),
            str(len(story.article_ids)),
            story.id[:8],
        )

    console.print(table)
    console.print()
    console.print("[dim]Use 'rss sources compare <ID>' for detailed comparison[/dim]")


@app.command("balance")
def show_balance(
    feeds_file: str = typer.Option("config/feeds.txt", "--feeds", "-f", help="Feeds file"),
):
    """
    Show the political balance of your current feeds.

    Analyzes your subscribed feeds and shows how they're distributed
    across the political spectrum.
    """
    distribution = get_current_feed_leanings(feeds_file)

    console.print(Panel("[bold]FEED BALANCE ANALYSIS[/bold]", style="blue"))
    console.print()

    total = sum(len(v) for v in distribution.values())

    if total == 0:
        console.print("[yellow]No feeds configured yet.[/yellow]")
        console.print("Add feeds with: rss add-feed <URL>")
        console.print("Or get suggestions: rss sources suggest")
        raise typer.Exit(0)

    # Show distribution
    table = Table(show_header=True)
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="center")
    table.add_column("Percentage", justify="center")
    table.add_column("Sources")

    colors = {"left": "blue", "center": "white", "right": "red", "unknown": "dim"}

    for category in ["left", "center", "right", "unknown"]:
        sources = distribution[category]
        count = len(sources)
        pct = (count / total * 100) if total > 0 else 0
        color = colors[category]

        sources_str = ", ".join(get_source_name(s) for s in sources[:3])
        if len(sources) > 3:
            sources_str += f" (+{len(sources) - 3} more)"

        table.add_row(
            f"[{color}]{category.title()}[/{color}]",
            str(count),
            f"{pct:.0f}%",
            sources_str or "-",
        )

    console.print(table)
    console.print()

    # Assessment
    left_count = len(distribution["left"])
    right_count = len(distribution["right"])
    center_count = len(distribution["center"])

    if left_count > right_count * 2:
        console.print("[yellow]Your feeds lean left. Consider adding right-leaning sources.[/yellow]")
        console.print("Run 'rss sources suggest' for suggestions.")
    elif right_count > left_count * 2:
        console.print("[yellow]Your feeds lean right. Consider adding left-leaning sources.[/yellow]")
        console.print("Run 'rss sources suggest' for suggestions.")
    elif center_count < (left_count + right_count) // 2:
        console.print("[yellow]Consider adding more centrist sources for balance.[/yellow]")
        console.print("Run 'rss sources suggest' for suggestions.")
    else:
        console.print("[green]Your feed mix appears relatively balanced.[/green]")


@app.command("suggest")
def suggest_sources(
    category: str = typer.Option(
        "all",
        "--category", "-c",
        help="Category: left, center, right, or all",
    ),
    feeds_file: str = typer.Option("config/feeds.txt", "--feeds", "-f", help="Feeds file"),
):
    """
    Suggest diverse sources to balance your feed mix.

    Analyzes your current feeds and recommends sources from
    underrepresented perspectives.
    """
    console.print(Panel("[bold]DIVERSE SOURCE SUGGESTIONS[/bold]", style="blue"))
    console.print()

    if category == "all":
        suggestions = suggest_diverse_sources(feeds_file)
    else:
        if category not in DIVERSE_FEEDS:
            console.print(f"[red]Unknown category: {category}[/red]")
            console.print("Valid categories: left, center, right, all")
            raise typer.Exit(1)
        suggestions = {category: DIVERSE_FEEDS[category]}

    has_suggestions = False
    for cat, feeds in suggestions.items():
        if not feeds:
            continue
        has_suggestions = True

        color = {"left": "blue", "center": "white", "right": "red"}[cat]
        console.print(f"[bold {color}]{cat.upper()} SOURCES[/bold {color}]")

        for url, name, leaning in feeds:
            console.print(f"  {name} [{leaning}]")
            console.print(f"    [dim]{url}[/dim]")
            console.print()

    if not has_suggestions:
        console.print("[green]Your feeds are already well-balanced![/green]")
        console.print()
        console.print("To see all available diverse sources:")
        console.print("  rss sources suggest --category left")
        console.print("  rss sources suggest --category center")
        console.print("  rss sources suggest --category right")
        return

    console.print()
    console.print("[dim]To add a feed: rss add-feed <URL>[/dim]")
    console.print("[dim]To add all suggestions: rss sources add-suggested[/dim]")


@app.command("add-suggested")
def add_suggested_sources(
    category: str = typer.Option(
        "all",
        "--category", "-c",
        help="Category: left, center, right, or all",
    ),
    feeds_file: str = typer.Option("config/feeds.txt", "--feeds", "-f", help="Feeds file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be added without adding"),
):
    """
    Add suggested diverse sources to your feeds.

    Adds the recommended sources to balance your feed mix.
    Use --dry-run to preview without making changes.
    """
    from pathlib import Path
    from .rss import load_feeds

    suggestions = suggest_diverse_sources(feeds_file)

    if category != "all":
        if category not in suggestions:
            console.print(f"[yellow]No suggestions for category: {category}[/yellow]")
            raise typer.Exit(0)
        suggestions = {category: suggestions.get(category, [])}

    existing = set(load_feeds(feeds_file))
    to_add = []

    for cat, feeds in suggestions.items():
        for url, name, leaning in feeds:
            if url not in existing:
                to_add.append((url, name, leaning))

    if not to_add:
        console.print("[green]All suggested sources are already in your feeds![/green]")
        raise typer.Exit(0)

    if dry_run:
        console.print("[bold]Would add these feeds:[/bold]")
        for url, name, leaning in to_add:
            console.print(f"  + {name} [{leaning}]")
            console.print(f"    [dim]{url}[/dim]")
        console.print()
        console.print("[dim]Run without --dry-run to add these feeds[/dim]")
        return

    # Actually add the feeds
    feeds_path = Path(feeds_file)
    feeds_path.parent.mkdir(parents=True, exist_ok=True)

    with open(feeds_path, "a") as f:
        for url, name, leaning in to_add:
            f.write(f"\n# {name} ({leaning})\n{url}\n")

    console.print(f"[green]Added {len(to_add)} feeds:[/green]")
    for url, name, leaning in to_add:
        console.print(f"  + {name} [{leaning}]")

    console.print()
    console.print("[dim]Run 'rss fetch' to get articles from new feeds[/dim]")


@app.command("list-diverse")
def list_diverse_sources():
    """
    List all available diverse sources in the database.

    Shows the full catalog of pre-curated sources across
    the political spectrum.
    """
    console.print(Panel("[bold]DIVERSE SOURCE CATALOG[/bold]", style="blue"))
    console.print()

    for category in ["left", "center", "right"]:
        color = {"left": "blue", "center": "white", "right": "red"}[category]
        console.print(f"[bold {color}]{category.upper()}[/bold {color}]")

        for url, name, leaning in DIVERSE_FEEDS[category]:
            console.print(f"  {name}")
            console.print(f"    Leaning: {leaning}")
            console.print(f"    [dim]{url}[/dim]")
        console.print()

    console.print("[dim]Use 'rss sources suggest' for personalized recommendations[/dim]")
