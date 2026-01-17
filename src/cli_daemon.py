"""CLI command for foreground daemon mode.

Runs continuous processing at configurable intervals with
granular control over which pipeline steps execute.

Pipeline steps (cumulative):
  1: Fetch only
  2: Fetch + LLM processing
  3: Fetch + LLM + Embeddings
  4: Fetch + LLM + Embeddings + Stories
  5: Full pipeline (all steps including connections)
"""

import sys
import time
import threading
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .utils import format_duration

app = typer.Typer(
    name="daemon",
    help="Run continuous processing in foreground",
)
console = Console(force_terminal=True, legacy_windows=True)

# Global flag for graceful shutdown
_stop_requested = False
_input_thread: Optional[threading.Thread] = None


def _parse_interval(interval: str) -> Optional[int]:
    """Parse interval string like '5m', '1h', '3d' into seconds."""
    interval = interval.lower().strip()

    try:
        if interval.endswith('s'):
            return int(interval[:-1])
        elif interval.endswith('m'):
            return int(interval[:-1]) * 60
        elif interval.endswith('h'):
            return int(interval[:-1]) * 3600
        elif interval.endswith('d'):
            return int(interval[:-1]) * 86400
        else:
            # Assume minutes if no suffix
            return int(interval) * 60
    except ValueError:
        return None


def _format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins}m"
    elif seconds < 86400:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        if mins:
            return f"{hours}h {mins}m"
        return f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours:
            return f"{days}d {hours}h"
        return f"{days}d"


def _input_listener():
    """Background thread to listen for 'q' to quit."""
    global _stop_requested
    while not _stop_requested:
        try:
            line = input()
            if line.lower().strip() in ('q', 'quit', 'exit', 'stop'):
                _stop_requested = True
                console.print("\n[yellow]Stop requested - finishing current cycle...[/yellow]")
                break
        except EOFError:
            break
        except Exception:
            break


def _run_pipeline_step(step: int, limit: int = 0) -> dict:
    """
    Run pipeline up to specified step level.

    Steps are cumulative:
      1: Fetch only
      2: Fetch + LLM
      3: Fetch + LLM + Embed
      4: Fetch + LLM + Embed + Stories
      5: Full pipeline
    """
    from .storage import Storage
    from .rss import fetch_all_feeds, load_feeds
    from .knowledge import KnowledgeBase
    from .embeddings import EmbeddingService
    from .llm_providers import get_best_provider

    storage = Storage()
    kb = KnowledgeBase()

    stats = {
        "fetched": 0,
        "new": 0,
        "processed": 0,
        "errors": 0,
    }

    # Step 1: Fetch
    feeds_file = "config/feeds.txt"
    feeds = load_feeds(feeds_file)
    if feeds:
        results = fetch_all_feeds(feeds_file, storage)
        for result in results:
            stats["fetched"] += result.get("fetched", 0)
            stats["new"] += result.get("new", 0)

    if step == 1:
        return stats

    # For steps 2+, we need providers and embedding service
    provider = get_best_provider()
    embedding_service = EmbeddingService(kb)

    if not provider:
        console.print("[yellow]No LLM provider available - stopping at fetch[/yellow]")
        return stats

    # Get articles to process
    MIN_CONTENT_LENGTH = 100
    articles = storage.get_unanalyzed_articles(
        exclude_spam=True,
        min_content_length=MIN_CONTENT_LENGTH
    )

    if limit > 0:
        articles = articles[:limit]

    if not articles:
        return stats

    # Step 2: LLM processing
    if step >= 2:
        from .report import _run_llm_phase
        llm_stats = {
            "processed": 0, "insights": 0, "triples": 0,
            "triples_new": 0, "triples_existing": 0,
            "connections": 0, "errors": 0,
        }
        _run_llm_phase(articles, storage, kb, provider, llm_stats, embedding_service, limit)
        stats["processed"] = llm_stats["processed"]
        stats["errors"] += llm_stats["errors"]

    # Step 3: Embeddings
    if step >= 3:
        from .report import _run_embedding_phase
        embed_stats = {"errors": 0}
        _run_embedding_phase(articles, storage, kb, embed_stats, embedding_service, limit)
        stats["errors"] += embed_stats.get("errors", 0)

    # Step 4: Story matching
    if step >= 4:
        from .report import _run_story_matching
        story_stats = {"errors": 0, "stories_matched": 0, "stories_created": 0}
        _run_story_matching(articles, storage, kb, provider, story_stats, embedding_service, limit)
        stats["stories_matched"] = story_stats.get("stories_matched", 0)
        stats["stories_created"] = story_stats.get("stories_created", 0)
        stats["errors"] += story_stats.get("errors", 0)

    # Step 5: Connection detection
    if step >= 5:
        from .report import _run_connection_detection
        conn_stats = {"errors": 0, "connections": 0}
        # Need processed_articles format - simplified for daemon
        processed_articles = [{"article": a, "insights": []} for a in articles]
        _run_connection_detection(processed_articles, kb, provider, conn_stats, embedding_service, limit)
        stats["connections"] = conn_stats.get("connections", 0)
        stats["errors"] += conn_stats.get("errors", 0)

    return stats


@app.callback(invoke_without_command=True)
def daemon_main(
    ctx: typer.Context,
    every: str = typer.Option(
        "10m",
        "--every", "-e",
        help="Processing interval (e.g., 5m, 1h, 30s)",
    ),
    step: int = typer.Option(
        5,
        "--step", "-s",
        min=1, max=5,
        help="Pipeline step level (1=fetch, 2=+LLM, 3=+embed, 4=+stories, 5=full)",
    ),
    limit: int = typer.Option(
        0,
        "--max", "-m",
        help="Max articles per cycle (0=unlimited)",
    ),
):
    """
    Run continuous processing in foreground.

    Pipeline step levels (cumulative):

      1: Fetch only - just download new articles

      2: Fetch + LLM - generate summaries, tags, insights

      3: Fetch + LLM + Embed - add semantic embeddings

      4: Fetch + LLM + Embed + Stories - match to story threads

      5: Full pipeline - all steps including connection detection

    Examples:

      rss daemon --every 5m --step 1    # Fetch every 5 minutes

      rss daemon --every 1h --step 3    # Full processing hourly

      rss daemon -e 30m -s 5 -m 10      # Full pipeline, 10 articles max
    """
    global _stop_requested, _input_thread

    interval_seconds = _parse_interval(every)
    if interval_seconds is None:
        console.print(f"[red]Invalid interval: {every}[/red]")
        console.print("[dim]Use format: 30s, 5m, 1h, 3d[/dim]")
        raise typer.Exit(1)

    if interval_seconds < 30:
        console.print("[yellow]Warning: Very short interval may cause issues[/yellow]")

    # Step descriptions
    step_names = {
        1: "Fetch only",
        2: "Fetch + LLM",
        3: "Fetch + LLM + Embed",
        4: "Fetch + LLM + Embed + Stories",
        5: "Full pipeline",
    }

    # Show startup info
    console.print()
    console.print(Panel("[bold]RSS Daemon Mode[/bold]", style="blue"))
    console.print()
    console.print(f"  Interval:  {_format_duration(interval_seconds)}")
    console.print(f"  Step:      {step} ({step_names[step]})")
    console.print(f"  Limit:     {limit if limit > 0 else 'unlimited'}")
    console.print()
    console.print("[dim]Type 'q' + Enter to stop gracefully, or Ctrl+C to force quit[/dim]")
    console.print()

    # Start input listener thread
    _stop_requested = False
    _input_thread = threading.Thread(target=_input_listener, daemon=True)
    _input_thread.start()

    cycle_count = 0

    try:
        while not _stop_requested:
            cycle_count += 1
            cycle_start = time.time()

            console.print(f"[bold]Cycle {cycle_count}[/bold] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            try:
                stats = _run_pipeline_step(step, limit)

                # Show results
                result_parts = []
                if stats.get("new", 0) > 0:
                    result_parts.append(f"{stats['new']} new")
                if stats.get("processed", 0) > 0:
                    result_parts.append(f"{stats['processed']} processed")
                if stats.get("stories_matched", 0) + stats.get("stories_created", 0) > 0:
                    result_parts.append(f"{stats.get('stories_matched', 0) + stats.get('stories_created', 0)} stories")
                if stats.get("errors", 0) > 0:
                    result_parts.append(f"[red]{stats['errors']} errors[/red]")

                cycle_time = time.time() - cycle_start
                if result_parts:
                    console.print(f"  Result: {', '.join(result_parts)} ({cycle_time:.1f}s)")
                else:
                    console.print(f"  [dim]No changes ({cycle_time:.1f}s)[/dim]")

            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")

            if _stop_requested:
                break

            # Wait for next cycle
            console.print(f"  [dim]Next cycle in {_format_duration(interval_seconds)}...[/dim]")
            console.print()

            # Sleep in small increments to check for stop request
            sleep_until = time.time() + interval_seconds
            while time.time() < sleep_until and not _stop_requested:
                time.sleep(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")

    console.print()
    console.print(f"[green]Daemon stopped after {cycle_count} cycles[/green]")
