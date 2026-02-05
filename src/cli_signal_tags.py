"""CLI commands for signal tag management."""

from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .storage import Storage

app = typer.Typer(
    name="tag",
    help="Signal tag management commands",
    invoke_without_command=True,
)
console = Console(force_terminal=True, legacy_windows=True)


@app.callback(invoke_without_command=True)
def tag_main(ctx: typer.Context):
    """
    Manage signal tags for articles.

    Signal tags identify article characteristics like:
    - Content type: breaking, analysis, opinion, how-to
    - Tone: urgent, neutral, positive, negative
    - Source type: official, expert, user-generated
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided - show interactive help
        console.print()
        console.print(Panel("[bold]Signal Tag Management[/bold]", style="blue"))
        console.print()
        console.print("Signal tags identify article characteristics like content type,")
        console.print("tone, and source credibility.")
        console.print()
        console.print("[bold]Commands:[/bold]")
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        table.add_row("articles", "Assign signal tags to articles")
        table.add_row("stats", "Show tag distribution statistics")
        table.add_row("filter", "Filter articles by tags")

        console.print(table)
        console.print()
        console.print("[dim]Examples:[/dim]")
        console.print("  rss tag articles           [dim]# Tag untagged articles[/dim]")
        console.print("  rss tag articles --llm     [dim]# Use LLM for better accuracy[/dim]")
        console.print("  rss tag filter -i breaking [dim]# Show breaking news[/dim]")
        console.print("  rss tag stats              [dim]# View tag distribution[/dim]")
        console.print()


@app.command("articles")
def tag_articles_cmd(
    limit: int = typer.Option(
        50,
        "--limit", "-n",
        help="Maximum number of articles to tag",
    ),
    use_llm: bool = typer.Option(
        False,
        "--llm",
        help="Use LLM for tagging (more accurate)",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Assign signal tags to articles."""
    storage = Storage(db_path)

    console.print(f"[bold]Tagging up to {limit} articles...[/bold]")
    if use_llm:
        console.print("[dim]Using LLM backend (more accurate, slower)[/dim]\n")
    else:
        console.print("[dim]Using rule-based tagging (fast)[/dim]\n")

    from .signal_tagger import SignalTagger, tag_articles_batch

    try:
        tagger = SignalTagger(use_llm=use_llm)
    except Exception as e:
        console.print(f"[red]Error initializing tagger: {e}[/red]")
        raise typer.Exit(1)

    # Get articles without signal tags
    articles = storage.get_articles(limit=limit)
    untagged = [a for a in articles if not a.signal_tags]

    if not untagged:
        console.print("[yellow]No untagged articles found.[/yellow]")
        return

    console.print(f"Found {len(untagged)} untagged articles\n")

    # Tag articles
    results = tag_articles_batch(untagged, tagger, show_progress=True)

    # Update storage
    for article_id, tags in results.items():
        storage.update_signal_tags(article_id, tags.to_json())

    console.print(f"\n[green]Successfully tagged {len(results)} articles[/green]")


@app.command("stats")
def tag_stats_cmd(
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Show signal tag distribution statistics."""
    storage = Storage(db_path)
    articles = storage.get_articles(limit=1000)

    # Filter tagged articles
    tagged_articles = [a for a in articles if a.signal_tags]

    if not tagged_articles:
        console.print("[yellow]No tagged articles found.[/yellow]")
        console.print("Run 'rss tag articles' to tag some articles.")
        raise typer.Exit(1)

    from collections import Counter
    import json

    # Count tag occurrences
    tag_counts = Counter()

    for article in tagged_articles:
        try:
            tags_data = json.loads(article.signal_tags)
            for category, tags_list in tags_data.items():
                for tag in tags_list:
                    tag_counts[tag] += 1
        except (json.JSONDecodeError, TypeError):
            continue

    # Display statistics
    console.print(Panel(
        f"[bold]Total Articles:[/bold] {len(articles)}\n"
        f"[bold]Tagged Articles:[/bold] {len(tagged_articles)}",
        title="Signal Tag Statistics",
    ))

    # Show top tags
    table = Table(title="Most Common Tags")
    table.add_column("Tag", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Percentage", justify="right")

    for tag, count in tag_counts.most_common(15):
        percentage = (count / len(tagged_articles)) * 100
        table.add_row(tag, str(count), f"{percentage:.1f}%")

    console.print(table)


@app.command("filter")
def filter_by_tags(
    include: Optional[str] = typer.Option(
        None,
        "--include", "-i",
        help="Comma-separated tags to include",
    ),
    exclude: Optional[str] = typer.Option(
        None,
        "--exclude", "-e",
        help="Comma-separated tags to exclude",
    ),
    limit: int = typer.Option(
        20,
        "--limit", "-n",
        help="Number of articles to show",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """Filter articles by signal tags."""
    storage = Storage(db_path)

    include_tags = [t.strip() for t in include.split(",")] if include else None
    exclude_tags = [t.strip() for t in exclude.split(",")] if exclude else None

    console.print("[bold]Filtering articles by tags...[/bold]")
    if include_tags:
        console.print(f"  Include: {', '.join(include_tags)}")
    if exclude_tags:
        console.print(f"  Exclude: {', '.join(exclude_tags)}")
    console.print()

    articles = storage.get_articles_by_signal_tags(
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        limit=limit,
    )

    if not articles:
        console.print("[yellow]No articles match the specified tags.[/yellow]")
        return

    # Display results
    table = Table(title=f"Filtered Articles ({len(articles)} results)")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Tags", style="green", max_width=35)

    for i, article in enumerate(articles, 1):
        # Parse and display tags
        import json
        try:
            tags_data = json.loads(article.signal_tags)
            all_tags = []
            for category, tags_list in tags_data.items():
                all_tags.extend(tags_list)
            tags_str = ", ".join(all_tags[:5])
            if len(all_tags) > 5:
                tags_str += "..."
        except (json.JSONDecodeError, TypeError):
            tags_str = article.signal_tags[:35] if article.signal_tags else ""

        title_str = article.title
        if len(title_str) > 50:
            title_str = title_str[:47] + "..."

        table.add_row(str(i), title_str, tags_str)

    console.print(table)


if __name__ == "__main__":
    app()
