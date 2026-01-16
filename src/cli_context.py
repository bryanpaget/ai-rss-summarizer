"""CLI commands for user context management."""

import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    import questionary
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

from .knowledge import KnowledgeBase, UserContext
from .user_context import UserContextStore

app = typer.Typer(
    name="context",
    help="User context management commands",
    invoke_without_command=True,
)
console = Console(force_terminal=True, legacy_windows=True)


@app.callback(invoke_without_command=True)
def context_main(ctx: typer.Context):
    """
    Manage user contexts for personalized relevance.

    User contexts help the system understand what you're interested in,
    so it can prioritize and filter articles that matter to you.

    Context types:
    - project: Current work projects (e.g., "Building a chatbot")
    - interest: General interests (e.g., "Machine learning", "Climate")
    - watching: Topics you're monitoring (e.g., "Company X earnings")
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided - show interactive help
        console.print()
        console.print(Panel("[bold]User Context Management[/bold]", style="blue"))
        console.print()
        console.print("Contexts help personalize article relevance and filtering.")
        console.print()
        console.print("[bold]Context Types:[/bold]")
        console.print("  [cyan]project[/cyan]   - Current work projects")
        console.print("  [cyan]interest[/cyan]  - General interests")
        console.print("  [cyan]watching[/cyan]  - Topics you're monitoring")
        console.print()
        console.print("[bold]Commands:[/bold]")
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        table.add_row("add", "Add a new context")
        table.add_row("list", "List all contexts")
        table.add_row("remove", "Remove a context")
        table.add_row("show", "Show context details")

        console.print(table)
        console.print()
        console.print("[dim]Examples:[/dim]")
        console.print("  rss context add project \"Building chatbot\"")
        console.print("  rss context add interest \"Machine learning\"")
        console.print("  rss context list")
        console.print("  rss context remove \"Building chatbot\"")
        console.print()


@app.command("add")
def add_context(
    context_type: str = typer.Argument(
        ...,
        help="Type: project, interest, or watching",
    ),
    name: str = typer.Argument(
        ...,
        help="Context name",
    ),
    description: str = typer.Option(
        None,
        "--desc", "-d",
        help="Description of the context",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    Add a new user context.

    Contexts help personalize article relevance scoring.

    Examples:
        rss context add project "Building a chatbot"
        rss context add interest "Machine learning" --desc "Deep learning, NLP"
        rss context add watching "OpenAI announcements"
    """
    # Validate context type
    valid_types = ["project", "interest", "watching"]
    if context_type.lower() not in valid_types:
        console.print(f"[red]Invalid context type: {context_type}[/red]")
        console.print(f"[dim]Valid types: {', '.join(valid_types)}[/dim]")
        raise typer.Exit(1)

    kb = KnowledgeBase(kb_path)

    context = UserContext(
        id=str(uuid.uuid4()),
        context_type=context_type.lower(),
        name=name,
        description=description,
    )

    kb.save_context(context)
    console.print(f"[green]Added {context_type}: {name}[/green]")

    if description:
        console.print(f"[dim]Description: {description}[/dim]")


@app.command("list")
def list_contexts(
    context_type: Optional[str] = typer.Option(
        None,
        "--type", "-t",
        help="Filter by context type",
    ),
    active_only: bool = typer.Option(
        False,
        "--active",
        help="Show only active contexts",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    List all user contexts.

    Examples:
        rss context list                # List all contexts
        rss context list --type project # List only projects
        rss context list --active       # List only active contexts
    """
    kb = KnowledgeBase(kb_path)
    contexts = kb.get_contexts(active_only=active_only)

    # Filter by type if specified
    if context_type:
        contexts = [c for c in contexts if c.context_type == context_type.lower()]

    if not contexts:
        console.print("[yellow]No contexts found.[/yellow]")
        console.print()
        console.print("[dim]Add one with:[/dim]")
        console.print("  rss context add project \"Project Name\"")
        console.print("  rss context add interest \"Topic\"")
        return

    table = Table(title="User Contexts")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status")
    table.add_column("Description")

    for ctx in contexts:
        status = "[green]Active[/green]" if ctx.active else "[dim]Inactive[/dim]"
        desc = (ctx.description or "")[:50]
        if ctx.description and len(ctx.description) > 50:
            desc += "..."
        table.add_row(ctx.context_type, ctx.name, status, desc)

    console.print(table)
    console.print()
    console.print(f"[dim]Total: {len(contexts)} context(s)[/dim]")


@app.command("remove")
def remove_context(
    name: str = typer.Argument(
        ...,
        help="Name of the context to remove",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    Remove a user context.

    Examples:
        rss context remove "Building chatbot"
        rss context remove "Machine learning"
    """
    kb = KnowledgeBase(kb_path)
    contexts = kb.get_contexts(active_only=False)

    # Find matching context
    matching = [c for c in contexts if c.name.lower() == name.lower()]

    if not matching:
        console.print(f"[yellow]Context not found: {name}[/yellow]")
        console.print()
        console.print("[dim]Available contexts:[/dim]")
        for ctx in contexts[:5]:
            console.print(f"  - {ctx.name}")
        return

    context = matching[0]

    # Delete context
    try:
        kb.delete_context(context.id)
        console.print(f"[green]Removed: {context.name}[/green]")
    except AttributeError:
        # Fallback if delete_context doesn't exist
        context.active = False
        kb.save_context(context)
        console.print(f"[green]Deactivated: {context.name}[/green]")


@app.command("show")
def show_context(
    name: str = typer.Argument(
        ...,
        help="Name of the context to show",
    ),
    kb_path: str = typer.Option(
        "knowledge.db",
        "--kb", "-k",
        help="Path to knowledge database",
    ),
):
    """
    Show details of a specific context.

    Examples:
        rss context show "Building chatbot"
    """
    kb = KnowledgeBase(kb_path)
    contexts = kb.get_contexts(active_only=False)

    # Find matching context
    matching = [c for c in contexts if c.name.lower() == name.lower()]

    if not matching:
        console.print(f"[yellow]Context not found: {name}[/yellow]")
        return

    context = matching[0]

    console.print(Panel(f"[bold]{context.name}[/bold]", style="blue"))
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Type", context.context_type)
    table.add_row("Status", "Active" if context.active else "Inactive")
    if context.description:
        table.add_row("Description", context.description)
    if hasattr(context, 'created_at') and context.created_at:
        table.add_row("Created", str(context.created_at)[:19])
    if hasattr(context, 'keywords') and context.keywords:
        table.add_row("Keywords", ", ".join(context.keywords[:10]))

    console.print(table)


if __name__ == "__main__":
    app()
