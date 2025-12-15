"""CLI commands for personal context management."""

import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console(force_terminal=True, legacy_windows=True)


def context_init():
    """Initialize your personal context profile."""
    from .user_context import UserContextStore

    store = UserContextStore()
    profile = store.load_profile()

    console.print(Panel("[bold]Personal Context Setup[/bold]", style="blue"))
    console.print()
    console.print("Let's set up your personal context for better recommendations.")
    console.print()

    # Get role
    role = console.input("[bold]Your role (e.g., 'ML engineer at fintech startup'): [/bold]").strip()
    if role:
        profile.role = role

    # Get current projects
    console.print()
    console.print("[bold]Current projects (comma-separated):[/bold]")
    projects = console.input("").strip()
    if projects:
        profile.current_projects = [p.strip() for p in projects.split(",")]

    # Get watching topics
    console.print()
    console.print("[bold]Topics to watch (comma-separated):[/bold]")
    watching = console.input("").strip()
    if watching:
        profile.watching = [t.strip() for t in watching.split(",")]

    # Get ignore topics
    console.print()
    console.print("[bold]Topics to ignore (comma-separated, optional):[/bold]")
    ignore = console.input("").strip()
    if ignore:
        profile.ignore = [t.strip() for t in ignore.split(",")]

    # Save profile
    store.save_profile(profile)

    console.print()
    console.print("[green]Profile saved successfully![/green]")
    console.print()
    console.print("[dim]Run 'rss update --show-scores' to see personalized relevance scores.[/dim]")


def context_show():
    """Show your current personal context."""
    from .user_context import UserContextStore

    store = UserContextStore()
    profile = store.load_profile()

    console.print(Panel("[bold]Your Personal Context[/bold]", style="blue"))
    console.print()

    if profile.role:
        console.print(f"[bold]Role:[/bold] {profile.role}")
        console.print()

    if profile.current_projects:
        console.print("[bold]Current Projects:[/bold]")
        for project in profile.current_projects:
            console.print(f"  - {project}")
        console.print()

    if profile.watching:
        console.print("[bold]Watching:[/bold]")
        for topic in profile.watching:
            console.print(f"  - {topic}")
        console.print()

    if profile.pinned:
        console.print("[bold]Pinned (never decay):[/bold]")
        for topic in profile.pinned:
            console.print(f"  - {topic}")
        console.print()

    if profile.ignore:
        console.print("[bold]Ignoring:[/bold]")
        for topic in profile.ignore:
            console.print(f"  - {topic}")
        console.print()

    console.print(f"[dim]Personalization strength: {profile.personalization_strength:.0%}[/dim]")
    console.print(f"[dim]Last updated: {profile.last_updated}[/dim]")


def context_edit():
    """Edit your personal context interactively."""
    from .user_context import UserContextStore

    store = UserContextStore()
    profile = store.load_profile()

    console.print("[bold]Edit Personal Context[/bold]")
    console.print("[dim](Press Enter to keep current value)[/dim]")
    console.print()

    # Edit role
    current_role = profile.role or ""
    role = console.input(f"[bold]Role [{current_role}]: [/bold]").strip()
    if role:
        profile.role = role

    # Edit projects
    current_projects = ", ".join(profile.current_projects)
    projects = console.input(f"[bold]Projects [{current_projects}]: [/bold]").strip()
    if projects:
        profile.current_projects = [p.strip() for p in projects.split(",")]

    # Edit watching
    current_watching = ", ".join(profile.watching)
    watching = console.input(f"[bold]Watching [{current_watching}]: [/bold]").strip()
    if watching:
        profile.watching = [t.strip() for t in watching.split(",")]

    # Edit ignore
    current_ignore = ", ".join(profile.ignore)
    ignore = console.input(f"[bold]Ignore [{current_ignore}]: [/bold]").strip()
    if ignore:
        profile.ignore = [t.strip() for t in ignore.split(",")]

    store.save_profile(profile)
    console.print("[green]Profile updated![/green]")


def context_pin(topic: str):
    """Pin a topic to prevent relevance decay."""
    from .user_context import UserContextStore

    store = UserContextStore()
    profile = store.load_profile()

    if topic not in profile.pinned:
        profile.pinned.append(topic)
        store.save_profile(profile)
        console.print(f"[green]Pinned: {topic}[/green]")
    else:
        console.print(f"[yellow]Already pinned: {topic}[/yellow]")


def context_unpin(topic: str):
    """Unpin a topic to allow relevance decay."""
    from .user_context import UserContextStore

    store = UserContextStore()
    profile = store.load_profile()

    if topic in profile.pinned:
        profile.pinned.remove(topic)
        store.save_profile(profile)
        console.print(f"[green]Unpinned: {topic}[/green]")
    else:
        console.print(f"[yellow]Not pinned: {topic}[/yellow]")


def context_watch(topic: str):
    """Add a topic to your watching list."""
    from .user_context import UserContextStore

    store = UserContextStore()
    profile = store.load_profile()

    if topic not in profile.watching:
        profile.watching.append(topic)
        store.save_profile(profile)
        console.print(f"[green]Now watching: {topic}[/green]")
    else:
        console.print(f"[yellow]Already watching: {topic}[/yellow]")


def context_ignore(topic: str):
    """Add a topic to your ignore list."""
    from .user_context import UserContextStore

    store = UserContextStore()
    profile = store.load_profile()

    if topic not in profile.ignore:
        profile.ignore.append(topic)
        store.save_profile(profile)
        console.print(f"[green]Now ignoring: {topic}[/green]")
    else:
        console.print(f"[yellow]Already ignoring: {topic}[/yellow]")


def context_stats():
    """Show engagement statistics."""
    from .user_context import UserContextStore

    store = UserContextStore()

    # Get topic engagement
    engagement = store.get_topic_engagement(days=30)

    if not engagement:
        console.print("[yellow]No engagement history yet.[/yellow]")
        console.print("[dim]Start reading articles to build your profile![/dim]")
        return

    console.print(Panel("[bold]Engagement Statistics (last 30 days)[/bold]", style="blue"))
    console.print()

    table = Table(title="Topic Engagement")
    table.add_column("Topic", style="cyan")
    table.add_column("Engagement Rate", justify="right", style="green")
    table.add_column("Bar")

    # Sort by engagement rate
    sorted_topics = sorted(engagement.items(), key=lambda x: x[1], reverse=True)

    for topic, rate in sorted_topics[:15]:  # Top 15
        bar_width = int(rate * 20)
        bar = "[green]" + "#" * bar_width + "[/green]"
        table.add_row(topic, f"{rate:.1%}", bar)

    console.print(table)


def context_export(output: str):
    """Export all personal context data."""
    from .user_context import UserContextStore

    store = UserContextStore()
    data = store.export_data()

    with open(output, "w") as f:
        json.dump(data, f, indent=2)

    console.print(f"[green]Exported context data to: {output}[/green]")


def context_import(input_file: str):
    """Import personal context data."""
    from .user_context import UserContextStore

    with open(input_file) as f:
        data = json.load(f)

    store = UserContextStore()
    store.import_data(data)

    console.print(f"[green]Imported context data from: {input_file}[/green]")


def context_clear(confirm: bool = False):
    """Clear all personal context data."""
    from .user_context import UserContextStore

    if not confirm:
        console.print("[yellow]This will delete all personal context data![/yellow]")
        console.print("Add --confirm to proceed.")
        return

    store = UserContextStore()
    deleted = store.clear_history()

    console.print(f"[green]Cleared {deleted} interaction records.[/green]")
    console.print("[dim]Profile retained. Use 'rss context init' to reset it.[/dim]")
