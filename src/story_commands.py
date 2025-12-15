"""CLI commands for story clustering features."""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .clustering import StoryEvolutionTracker, batch_process_articles
from .llm_providers import get_best_provider
from .storage import Storage

console = Console(force_terminal=True, legacy_windows=True)


def cluster_command(
    storage: Storage,
    limit: int = 20,
    enable_news: bool = True,
):
    """
    Cluster articles into stories and extract news items.

    Args:
        storage: Storage instance
        limit: Number of articles to cluster
        enable_news: Whether to extract news items
    """
    provider, is_llm = get_best_provider()

    if not is_llm:
        console.print("[yellow]LLM required for story clustering.[/yellow]")
        console.print("Run 'rss setup' to configure an LLM provider.")
        raise typer.Exit(1)

    console.print(f"[bold]Clustering articles using {provider.name}...[/bold]")

    # Get unclustered articles
    articles = storage.get_articles(limit=limit)
    unclustered = [a for a in articles if not a.story_id]

    if not unclustered:
        console.print("[yellow]No unclustered articles found.[/yellow]")
        return

    console.print(f"[dim]Processing {len(unclustered)} articles...[/dim]\n")

    # Process clustering
    stats = batch_process_articles(unclustered, provider, storage, enable_news)

    # Display results
    console.print(f"[green]Processed {stats['processed']} articles[/green]")
    console.print(f"  New stories created: {stats['stories_created']}")
    console.print(f"  Added to existing stories: {stats['articles_added_to_existing']}")
    if enable_news:
        console.print(f"  News items extracted: {stats['total_news_items']}")

    if stats["errors"]:
        console.print(f"\n[yellow]Errors: {len(stats['errors'])}[/yellow]")
        for error in stats["errors"][:5]:
            console.print(f"  [dim]{error}[/dim]")


def stories_command(
    storage: Storage,
    limit: int = 20,
    lifecycle: Optional[str] = None,
):
    """
    List stories with their articles and news items.

    Args:
        storage: Storage instance
        limit: Number of stories to show
        lifecycle: Filter by lifecycle state
    """
    # Get stories
    if lifecycle:
        story_list = storage.get_all_stories(limit=limit, lifecycle_state=lifecycle)
    else:
        story_list = storage.get_all_stories(limit=limit)

    if not story_list:
        console.print("[yellow]No stories found.[/yellow]")
        return

    table = Table(title="Stories")
    table.add_column("#", style="dim", width=3)
    table.add_column("Story Title", style="cyan", max_width=40)
    table.add_column("State", width=12)
    table.add_column("Articles", justify="right", width=8)
    table.add_column("News Items", justify="right", width=10)
    table.add_column("Last Updated", width=12)

    for i, story in enumerate(story_list, 1):
        title = story.title[:40] + "..." if len(story.title) > 40 else story.title

        # Color code lifecycle state
        state_colors = {
            "emerging": "yellow",
            "developing": "green",
            "peaked": "blue",
            "declining": "magenta",
            "resolved": "dim",
        }
        state_color = state_colors.get(story.lifecycle_state, "white")
        state_str = f"[{state_color}]{story.lifecycle_state}[/{state_color}]"

        last_updated = str(story.last_updated)[:10] if story.last_updated else "-"

        table.add_row(
            str(i),
            title,
            state_str,
            str(len(story.article_ids)),
            str(len(story.news_item_ids)),
            last_updated,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(story_list)} stories[/dim]")


def story_detail_command(
    storage: Storage,
    story_index: int,
    show_items: bool = True,
):
    """
    Show detailed view of a specific story.

    Args:
        storage: Storage instance
        story_index: Story number from list
        show_items: Whether to show news items
    """
    # Get all stories and select by index
    story_list = storage.get_all_stories(limit=1000)

    if story_index < 1 or story_index > len(story_list):
        console.print(f"[red]Invalid story index. Must be 1-{len(story_list)}[/red]")
        return

    story_obj = story_list[story_index - 1]

    # Show story details
    console.print(Panel(
        f"[bold]{story_obj.title}[/bold]\n\n{story_obj.description}\n\n"
        f"[dim]State: {story_obj.lifecycle_state}[/dim]\n"
        f"[dim]Keywords: {', '.join(story_obj.keywords[:10])}[/dim]",
        title="Story Details",
        border_style="cyan",
    ))

    # Show articles
    console.print(f"\n[bold]Articles ({len(story_obj.article_ids)}):[/bold]")
    for aid in story_obj.article_ids[:10]:
        article = storage.get_article(aid)
        if article:
            console.print(f"  - {article.title[:70]}")

    if len(story_obj.article_ids) > 10:
        console.print(f"  [dim]... and {len(story_obj.article_ids) - 10} more[/dim]")

    # Show news items
    if show_items and story_obj.news_item_ids:
        news_items = storage.get_news_items(story_obj.id)
        console.print(f"\n[bold]News Items ({len(news_items)}):[/bold]")

        for item in news_items[:10]:
            type_colors = {
                "new_info": "green",
                "recap": "yellow",
                "analysis": "blue",
                "opinion": "magenta",
            }
            type_color = type_colors.get(item.item_type, "white")
            type_badge = f"[{type_color}]{item.item_type}[/{type_color}]"

            console.print(Panel(
                f"{item.description}\n\n"
                f"[dim]First reported by: {item.first_reported_by}[/dim]\n"
                f"[dim]Confidence: {item.confidence:.2f}[/dim]",
                title=f"{type_badge} {item.title}",
                border_style="dim",
            ))

        if len(news_items) > 10:
            console.print(f"[dim]... and {len(news_items) - 10} more news items[/dim]")


def evolution_command(storage: Storage):
    """
    Show story evolution statistics and trends.

    Args:
        storage: Storage instance
    """
    tracker = StoryEvolutionTracker(storage)

    # Update all stories first
    console.print("[bold]Updating story lifecycle states...[/bold]")
    update_stats = tracker.update_all_stories()

    console.print(f"[green]Updated {update_stats['updated']} stories[/green]\n")

    # Get evolution stats
    stats = tracker.get_evolution_stats()

    # Display state distribution
    table = Table(title="Story Lifecycle Distribution")
    table.add_column("State", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Bar")

    state_counts = stats.get("by_state", {})
    max_count = max(state_counts.values()) if state_counts else 1

    state_order = ["emerging", "developing", "peaked", "declining", "resolved"]
    for state in state_order:
        count = state_counts.get(state, 0)
        if count > 0:
            bar_width = int((count / max_count) * 20)
            bar = "[green]" + "#" * bar_width + "[/green]"
            table.add_row(state.capitalize(), str(count), bar)

    console.print(table)

    # Display summary stats
    console.print()
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  Total stories: {stats['total_stories']}")
    console.print(f"  Avg articles per story: {stats['avg_articles_per_story']:.1f}")
    console.print(f"  Avg news items per story: {stats['avg_news_items_per_story']:.1f}")
