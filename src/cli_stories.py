"""Stories CLI subcommand group."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .storage import Storage
from .knowledge import KnowledgeBase

app = typer.Typer(help="Story management commands")
console = Console(force_terminal=True, legacy_windows=True)


def get_storage(db_path: str = "articles.db") -> Storage:
    """Get storage instance."""
    return Storage(db_path)


@app.command(name="backfill-embeddings")
def backfill_embeddings(
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
    Backfill embeddings for stories that don't have them.

    Stories created before the embedding phase was added won't have embeddings,
    causing duplicate detection to fail (new articles about the same topic
    create new stories instead of matching existing ones).

    This command embeds all stories that are missing embeddings so they can
    be matched in future runs.

    Example:
        rss stories backfill-embeddings
    """
    from .clustering import backfill_story_embeddings

    storage = get_storage(db_path)
    kb = KnowledgeBase(kb_path)

    console.print("[bold]Backfilling story embeddings...[/bold]\n")

    def update_progress(current, total, title):
        # Truncate title if too long
        display_title = title[:50] + "..." if len(title) > 50 else title
        console.print(f"  [{current}/{total}] {display_title}")

    stats = backfill_story_embeddings(
        storage=storage,
        kb=kb,
        progress_callback=update_progress,
    )

    console.print()
    console.print(f"[green]Embedded {stats['embedded']} stories[/green]")
    console.print(f"[dim]Already had embeddings: {stats['already_embedded']}[/dim]")

    if stats['errors']:
        console.print(f"[yellow]Errors: {len(stats['errors'])}[/yellow]")
        for error in stats['errors'][:5]:
            console.print(f"  [dim]{error}[/dim]")


@app.command(name="list")
def list_stories(
    limit: int = typer.Option(
        20,
        "--limit", "-n",
        help="Number of stories to show",
    ),
    state: Optional[str] = typer.Option(
        None,
        "--state", "-s",
        help="Filter by lifecycle state: emerging, developing, peaked, declining, resolved",
    ),
    db_path: str = typer.Option(
        "articles.db",
        "--db", "-d",
        help="Path to database file",
    ),
):
    """
    List story clusters.

    Shows stories (groups of related articles) with their lifecycle state
    and article counts.

    Examples:
        rss stories list                    # Show all stories
        rss stories list --state developing # Only developing stories
    """
    storage = get_storage(db_path)

    stories = storage.get_all_stories(limit=limit, lifecycle_state=state)

    if not stories:
        console.print("[yellow]No stories found.[/yellow]")
        console.print("Run 'rss report' to create story clusters.")
        raise typer.Exit(1)

    table = Table(title="Story Clusters")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="cyan", max_width=45)
    table.add_column("State", width=12)
    table.add_column("Articles", justify="right", width=8)
    table.add_column("Updated", width=12)

    state_colors = {
        "emerging": "green",
        "developing": "yellow",
        "peaked": "blue",
        "declining": "dim",
        "resolved": "dim italic",
    }

    for i, story in enumerate(stories, 1):
        state_color = state_colors.get(story.lifecycle_state, "white")
        state_display = f"[{state_color}]{story.lifecycle_state}[/{state_color}]"

        title = story.title
        if len(title) > 45:
            title = title[:42] + "..."

        updated = str(story.last_updated)[:10] if story.last_updated else "-"

        table.add_row(
            str(i),
            title,
            state_display,
            str(len(story.article_ids)),
            updated,
        )

    console.print(table)


@app.command(name="fix-titles")
def fix_titles(
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
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be fixed without making changes",
    ),
    limit: int = typer.Option(
        0,
        "--limit", "-n",
        help="Maximum number of titles to fix (0 = unlimited)",
    ),
):
    """
    Fix stories with bad/broken titles.

    Finds stories where the LLM returned garbage (like "Here are a few concise
    story titles...") and regenerates proper titles.

    Example:
        rss stories fix-titles              # Fix bad titles
        rss stories fix-titles --dry-run    # Preview what would change
    """
    from .clustering import StoryClusterer
    from .llm_providers import get_provider

    storage = get_storage(db_path)
    kb = KnowledgeBase(kb_path)

    # Find stories with bad titles
    all_stories = storage.get_all_stories(limit=1000)
    bad_patterns = ["here are a few", "here is a", "concise story title", "focus on"]

    bad_stories = []
    for story in all_stories:
        title_lower = story.title.lower()
        if any(pattern in title_lower for pattern in bad_patterns):
            bad_stories.append(story)

    if not bad_stories:
        console.print("[green]All story titles look good![/green]")
        return

    total_bad = len(bad_stories)
    if limit > 0:
        bad_stories = bad_stories[:limit]

    console.print(f"[bold]Found {total_bad} stories with bad titles[/bold]")
    if limit > 0 and total_bad > limit:
        console.print(f"[dim]Processing {limit} (use --limit 0 for all)[/dim]")
    console.print()

    if dry_run:
        console.print("[yellow]DRY RUN - no changes will be made[/yellow]\n")
        for story in bad_stories[:20]:
            console.print(f"  Would fix: {story.title[:60]}...")
        if len(bad_stories) > 20:
            console.print(f"  ...and {len(bad_stories) - 20} more")
        return

    # Initialize LLM for title generation
    try:
        provider = get_provider()
        clustering = StoryClusterer(storage, provider, kb)
    except Exception as e:
        console.print(f"[red]Failed to initialize LLM: {e}[/red]")
        raise typer.Exit(1)

    fixed = 0
    errors = []

    for i, story in enumerate(bad_stories, 1):
        # Get first article in story to regenerate title from
        if not story.article_ids:
            errors.append(f"Story {story.id}: no articles")
            continue

        article = storage.get_article(story.article_ids[0])
        if not article:
            errors.append(f"Story {story.id}: article not found")
            continue

        try:
            new_title = clustering._generate_story_title(article)
            if new_title and new_title != story.title:
                # Update in database
                storage.update_story_title(story.id, new_title)
                console.print(f"  [{i}/{len(bad_stories)}] {new_title[:50]}...")
                fixed += 1
            else:
                console.print(f"  [{i}/{len(bad_stories)}] [dim]kept: {article.title[:50]}...[/dim]")
        except Exception as e:
            errors.append(f"{story.id}: {e}")

    console.print()
    console.print(f"[green]Fixed {fixed} story titles[/green]")
    if errors:
        console.print(f"[yellow]Errors: {len(errors)}[/yellow]")
        for err in errors[:5]:
            console.print(f"  [dim]{err}[/dim]")


@app.command(name="stats")
def stats(
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
    Show story statistics including embedding coverage.

    Displays stats about story clusters and how many have embeddings
    for similarity matching.
    """
    storage = get_storage(db_path)
    kb = KnowledgeBase(kb_path)

    # Get all stories
    all_stories = storage.get_all_stories(limit=1000)

    # Get embedding coverage
    embedded_ids = kb.get_target_ids_with_embeddings("story")

    # Count by state
    by_state = {}
    embedded_count = 0
    for story in all_stories:
        state = story.lifecycle_state
        by_state[state] = by_state.get(state, 0) + 1
        if story.id in embedded_ids:
            embedded_count += 1

    console.print(Panel("[bold]Story Statistics[/bold]", style="blue"))
    console.print()

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Total Stories", str(len(all_stories)))
    table.add_row("With Embeddings", str(embedded_count))
    table.add_row("Missing Embeddings", str(len(all_stories) - embedded_count))

    console.print(table)
    console.print()

    if by_state:
        console.print("[bold]By Lifecycle State:[/bold]")
        for state, count in sorted(by_state.items(), key=lambda x: -x[1]):
            console.print(f"  {state}: {count}")

    # Warn if many stories missing embeddings
    missing = len(all_stories) - embedded_count
    if missing > 0:
        console.print()
        console.print(
            f"[yellow]Warning: {missing} stories missing embeddings - duplicate detection may fail[/yellow]"
        )
        console.print("[dim]Run 'rss stories backfill-embeddings' to fix[/dim]")
