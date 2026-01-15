"""CLI commands for perspective synthesis."""

from typing import Optional

import typer
from rich.console import Console

# Initialize
console = Console(force_terminal=True, legacy_windows=True)


def add_perspective_commands(app: typer.Typer):
    """Add perspective-related commands to the CLI app."""

    @app.command()
    def perspectives(
        story_id: Optional[str] = typer.Argument(None, help="Specific story cluster ID"),
        categories: Optional[str] = typer.Option(
            None,
            "--categories", "-c",
            help="Comma-separated list of perspective categories",
        ),
        limit: int = typer.Option(
            10,
            "--limit", "-n",
            help="Number of stories to show (if no story_id)",
        ),
        update_clusters: bool = typer.Option(
            False,
            "--update", "-u",
            help="Update story clusters before showing (can be slow)",
        ),
        db_path: str = typer.Option(
            "articles.db",
            "--db", "-d",
            help="Path to database file",
        ),
    ):
        """
        View synthesized perspectives on stories.

        Shows different angles on stories by combining multiple sources.

        Examples:
            rss perspectives                    # Show top stories with default perspectives
            rss perspectives --categories consensus,spiciest-takes
            rss perspectives story_abc123       # Show specific story
        """
        from .storage import Storage
        from .llm_providers import get_best_provider
        from .perspectives import (
            synthesize_perspectives,
            get_user_perspective_config,
            PERSPECTIVE_CATEGORIES
        )
        from .storage_perspectives import add_perspective_methods
        from .clustering import update_story_clusters

        provider, is_llm = get_best_provider()
        storage = Storage(db_path)
        add_perspective_methods(storage)

        # Update clusters only if requested (can be slow)
        if update_clusters:
            console.print("[dim]Updating story clusters...[/dim]")
            cluster_stats = update_story_clusters(storage)
            console.print(
                f"[dim]Clustered {cluster_stats['processed']} articles into "
                f"{cluster_stats['new_clusters']} new stories[/dim]\n"
            )

        # Get configuration
        config = get_user_perspective_config(storage)
        if categories:
            requested_categories = [c.strip() for c in categories.split(',')]
        else:
            requested_categories = config.get('default_categories', ['consensus', 'contested', 'gaps'])

        # Validate categories
        invalid = [c for c in requested_categories if c not in PERSPECTIVE_CATEGORIES]
        if invalid:
            console.print(f"[red]Invalid categories: {', '.join(invalid)}[/red]")
            console.print(f"[dim]Available: {', '.join(PERSPECTIVE_CATEGORIES.keys())}[/dim]")
            raise typer.Exit(1)

        if story_id:
            # Show specific story
            cluster = storage.get_story_cluster(story_id)
            if not cluster:
                console.print(f"[red]Story cluster not found: {story_id}[/red]")
                raise typer.Exit(1)

            articles = storage.get_articles_by_cluster(story_id)
            if not articles:
                console.print(f"[yellow]No articles in this story cluster.[/yellow]")
                raise typer.Exit(1)

            console.print(f"[bold]Story:[/bold] {cluster['title']}")
            console.print(f"[dim]Sources: {len(articles)} articles[/dim]\n")

            perspectives = synthesize_perspectives(
                story_id,
                requested_categories,
                storage,
                provider if is_llm else None
            )

            for category in requested_categories:
                if category not in perspectives:
                    continue

                perspective = perspectives[category]
                cat_info = PERSPECTIVE_CATEGORIES[category]

                # Confidence bar (ASCII safe for Windows)
                conf_width = int(perspective.confidence * 16)
                conf_bar = "[green]" + "#" * conf_width + "-" * (16 - conf_width) + "[/green]"

                console.print(f"\n[bold cyan][{cat_info['name']}][/bold cyan] {conf_bar}")
                console.print(perspective.content)

        else:
            # Show top stories
            clusters = storage.get_story_clusters()[:limit]

            if not clusters:
                console.print("[yellow]No story clusters found.[/yellow]")
                console.print("Run 'rss fetch' to fetch articles first.")
                raise typer.Exit(1)

            for cluster in clusters:
                articles = storage.get_articles_by_cluster(cluster['id'])
                if len(articles) < 2:
                    continue  # Skip single-article clusters

                console.print(f"\n[bold]Story:[/bold] {cluster['title']}")
                console.print(f"[dim]Sources: {len(articles)} articles[/dim]")

                perspectives = synthesize_perspectives(
                    cluster['id'],
                    requested_categories,
                    storage,
                    provider if is_llm else None
                )

                # Show first perspective only for overview
                if perspectives and requested_categories:
                    first_cat = requested_categories[0]
                    if first_cat in perspectives:
                        perspective = perspectives[first_cat]
                        cat_info = PERSPECTIVE_CATEGORIES[first_cat]

                        conf_width = int(perspective.confidence * 8)
                        conf_bar = "#" * conf_width + "-" * (8 - conf_width)

                        console.print(f"[cyan][{cat_info['name']}][/cyan] {conf_bar}")
                        # Full content - wraps naturally
                        console.print(f"[dim]{perspective.content}[/dim]")

                console.print(f"[dim]View all: rss perspectives {cluster['id']}[/dim]")

        console.print()
        console.print("[dim]Configure: rss perspective-config[/dim]")

    @app.command("perspective-config")
    def configure_perspectives(
        db_path: str = typer.Option(
            "articles.db",
            "--db", "-d",
            help="Path to database file",
        ),
    ):
        """
        Configure which perspective categories to show by default.

        Interactive configuration of default perspectives.
        """
        from .storage import Storage
        from .perspectives import (
            get_user_perspective_config,
            PERSPECTIVE_CATEGORIES,
            DEFAULT_CATEGORIES
        )
        from .storage_perspectives import add_perspective_methods

        storage = Storage(db_path)
        add_perspective_methods(storage)

        config = get_user_perspective_config(storage)
        current_defaults = config.get('default_categories', DEFAULT_CATEGORIES)

        console.print("[bold]Current perspective settings:[/bold]\n")
        console.print("Default categories (shown for all stories):")
        for cat in current_defaults:
            cat_info = PERSPECTIVE_CATEGORIES.get(cat, {})
            name = cat_info.get('name', cat)
            desc = cat_info.get('description', '')
            console.print(f"  [green]✓[/green] {name} - {desc}")

        console.print("\nAvailable categories:")
        for cat, info in PERSPECTIVE_CATEGORIES.items():
            if cat not in current_defaults:
                console.print(f"  □ {info['name']} - {info['description']}")

        console.print("\n[dim]To use specific categories for one query:[/dim]")
        console.print("[dim]  rss perspectives --categories consensus,spiciest-takes[/dim]")

    @app.command("cluster-stories")
    def cluster_stories(
        force: bool = typer.Option(
            False,
            "--force", "-f",
            help="Force re-clustering of all articles",
        ),
        db_path: str = typer.Option(
            "articles.db",
            "--db", "-d",
            help="Path to database file",
        ),
    ):
        """
        Cluster articles into story groups.

        Groups related articles about the same underlying story.
        """
        from .storage import Storage
        from .clustering import update_story_clusters
        from .storage_perspectives import add_perspective_methods

        storage = Storage(db_path)
        add_perspective_methods(storage)

        console.print("[bold]Clustering articles into stories...[/bold]\n")

        stats = update_story_clusters(storage, lookback_hours=168 if force else 72)

        console.print(f"[green]Processed {stats['processed']} articles[/green]")
        console.print(f"  Created {stats['new_clusters']} new story clusters")
        console.print(f"  Added {stats['added_to_existing']} articles to existing clusters")
        console.print(f"  Skipped {stats['skipped']} articles")

        # Show top clusters
        clusters = storage.get_story_clusters()[:10]
        if clusters:
            console.print("\n[bold]Top story clusters:[/bold]")
            for cluster in clusters:
                articles = storage.get_articles_by_cluster(cluster['id'])
                console.print(f"  {cluster['title'][:60]} ({len(articles)} articles)")
