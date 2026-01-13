"""CLI commands for constitution/analysis policy management."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .constitution import (
    get_constitution_path,
    get_constitution_content,
    constitution_exists,
    create_constitution,
    get_example_constitution,
)

console = Console(force_terminal=True, legacy_windows=True)


def add_constitution_commands(app: typer.Typer):
    """Add constitution-related commands to the CLI app."""

    @app.command()
    def constitution(
        action: str = typer.Argument(
            None,
            help="Action: 'edit' to open editor, 'example' to show template, or omit to view current",
        ),
    ):
        """
        View or edit your analysis constitution.

        The constitution defines principles that guide ALL analysis.
        These principles are injected into LLM prompts to personalize
        how articles are analyzed, insights extracted, and perspectives synthesized.

        Examples:
            rss constitution              # View current constitution
            rss constitution edit         # Open in editor
            rss constitution example      # Show example template
        """
        if action == "edit":
            _edit_constitution()
        elif action == "example":
            _show_example()
        else:
            _view_constitution()

    @app.command("constitution-create")
    def constitution_create(
        force: bool = typer.Option(
            False,
            "--force", "-f",
            help="Overwrite existing constitution",
        ),
    ):
        """
        Create a new constitution from the example template.

        Use this to get started with a default set of analysis principles.
        Edit the file afterward to customize for your needs.
        """
        path = get_constitution_path()

        if path.exists() and not force:
            console.print(f"[yellow]Constitution already exists at {path}[/yellow]")
            console.print("[dim]Use --force to overwrite, or 'rss constitution edit' to modify[/dim]")
            raise typer.Exit(1)

        create_constitution()
        console.print(f"[green]Created constitution at {path}[/green]")
        console.print("[dim]Edit this file to customize your analysis principles.[/dim]")
        console.print("[dim]Run 'rss constitution' to view it.[/dim]")


def _view_constitution():
    """Display the current constitution."""
    content = get_constitution_content()

    if not content:
        console.print("[yellow]No constitution configured.[/yellow]")
        console.print()
        console.print("A constitution defines principles that guide ALL analysis.")
        console.print("These are injected into LLM prompts to personalize how")
        console.print("articles are analyzed and insights extracted.")
        console.print()
        console.print("[bold]To get started:[/bold]")
        console.print("  rss constitution-create    # Create from template")
        console.print("  rss constitution example   # View example template")
        return

    path = get_constitution_path()
    console.print(Panel(
        f"[bold]Your Analysis Constitution[/bold]\n[dim]{path}[/dim]",
        style="blue",
    ))
    console.print()

    # Render as markdown
    md = Markdown(content)
    console.print(md)

    console.print()
    console.print("[dim]Edit: rss constitution edit[/dim]")


def _edit_constitution():
    """Open constitution in default editor."""
    path = get_constitution_path()

    if not path.exists():
        console.print("[yellow]No constitution file exists. Creating from template...[/yellow]")
        create_constitution()
        console.print(f"[green]Created {path}[/green]")
        console.print()

    # Try to open in editor
    editor = _get_editor()

    console.print(f"[dim]Opening {path} in {editor}...[/dim]")

    try:
        if sys.platform == "win32":
            # Windows: use start command
            subprocess.run(["cmd", "/c", "start", "", str(path)], check=True)
        else:
            # Unix: use the editor
            subprocess.run([editor, str(path)], check=True)
    except Exception as e:
        console.print(f"[red]Failed to open editor: {e}[/red]")
        console.print(f"[dim]Manually edit: {path}[/dim]")


def _get_editor() -> str:
    """Get the user's preferred editor."""
    import os

    # Check common editor environment variables
    for var in ["VISUAL", "EDITOR"]:
        editor = os.environ.get(var)
        if editor:
            return editor

    # Platform defaults
    if sys.platform == "win32":
        return "notepad"
    elif sys.platform == "darwin":
        return "open -t"  # TextEdit on macOS
    else:
        return "nano"  # Common on Linux


def _show_example():
    """Show the example constitution template."""
    console.print(Panel(
        "[bold]Example Constitution Template[/bold]",
        style="blue",
    ))
    console.print()

    example = get_example_constitution()
    md = Markdown(example)
    console.print(md)

    console.print()
    console.print("[bold]To use this template:[/bold]")
    console.print("  rss constitution-create    # Create from this template")
    console.print("  rss constitution edit      # Then customize it")
