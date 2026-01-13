"""CLI commands for background fetch scheduling."""

import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="schedule",
    help="Background fetch scheduling commands",
    invoke_without_command=True,
)
console = Console(force_terminal=True, legacy_windows=True)

# Schedule config file location
SCHEDULE_CONFIG = Path("config/schedule.json")


def _get_script_path() -> str:
    """Get the path to run rss fetch."""
    return f'"{sys.executable}" -m src.cli fetch'


def _parse_interval(interval: str) -> Optional[int]:
    """Parse interval string like '3d', '12h', '30m' into minutes."""
    interval = interval.lower().strip()

    if interval.endswith('d'):
        try:
            days = int(interval[:-1])
            return days * 24 * 60
        except ValueError:
            return None
    elif interval.endswith('h'):
        try:
            hours = int(interval[:-1])
            return hours * 60
        except ValueError:
            return None
    elif interval.endswith('m'):
        try:
            minutes = int(interval[:-1])
            return minutes
        except ValueError:
            return None
    else:
        try:
            return int(interval)
        except ValueError:
            return None


def _save_schedule_config(enabled: bool, interval_minutes: int = 0) -> None:
    """Save schedule configuration."""
    import json

    SCHEDULE_CONFIG.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "enabled": enabled,
        "interval_minutes": interval_minutes,
    }

    with open(SCHEDULE_CONFIG, "w") as f:
        json.dump(config, f, indent=2)


def _load_schedule_config() -> dict:
    """Load schedule configuration."""
    import json

    if not SCHEDULE_CONFIG.exists():
        return {"enabled": False, "interval_minutes": 0}

    try:
        with open(SCHEDULE_CONFIG) as f:
            return json.load(f)
    except Exception:
        return {"enabled": False, "interval_minutes": 0}


def _create_windows_task(interval_minutes: int, working_dir: str) -> tuple[bool, str]:
    """Create Windows Task Scheduler task."""
    task_name = "RSSFeedFetch"
    script_path = _get_script_path()

    # Delete existing task if present
    subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
    )

    # Determine schedule type based on interval
    if interval_minutes >= 1440:  # 1+ days
        days = interval_minutes // 1440
        schedule_type = "DAILY"
        modifier = str(days)
    elif interval_minutes >= 60:  # 1+ hours
        hours = interval_minutes // 60
        schedule_type = "HOURLY"
        modifier = str(hours)
    else:
        schedule_type = "MINUTE"
        modifier = str(interval_minutes)

    # Create new task
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'cmd /c "cd /d {working_dir} && {script_path}"',
        "/sc", schedule_type,
        "/mo", modifier,
        "/f",  # Force overwrite
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        return True, f"Task '{task_name}' created successfully"
    else:
        return False, f"Failed to create task: {result.stderr}"


def _delete_windows_task() -> tuple[bool, str]:
    """Delete Windows Task Scheduler task."""
    task_name = "RSSFeedFetch"

    result = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, f"Task '{task_name}' deleted successfully"
    else:
        if "cannot find" in result.stderr.lower() or "does not exist" in result.stderr.lower():
            return True, "No scheduled task was active"
        return False, f"Failed to delete task: {result.stderr}"


def _get_windows_task_status() -> Optional[dict]:
    """Get Windows Task Scheduler task status."""
    task_name = "RSSFeedFetch"

    result = subprocess.run(
        ["schtasks", "/query", "/tn", task_name, "/fo", "LIST", "/v"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return None

    # Parse the output
    info = {}
    for line in result.stdout.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            info[key.strip()] = value.strip()

    return info


def _create_cron_job(interval_minutes: int, working_dir: str) -> tuple[bool, str]:
    """Create cron job for Unix systems."""
    script_path = _get_script_path()

    # Build cron expression
    if interval_minutes >= 1440:  # Daily or more
        days = interval_minutes // 1440
        cron_expr = f"0 0 */{days} * *"
    elif interval_minutes >= 60:  # Hourly or more
        hours = interval_minutes // 60
        cron_expr = f"0 */{hours} * * *"
    else:
        cron_expr = f"*/{interval_minutes} * * * *"

    cron_line = f'{cron_expr} cd "{working_dir}" && {script_path} >> /tmp/rss_fetch.log 2>&1'
    cron_marker = "# RSS Summarizer auto-fetch"

    # Get existing crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    # Remove old RSS entries
    lines = [l for l in existing.split("\n") if cron_marker not in l and "src.cli fetch" not in l]

    # Add new entry
    lines.append(f"{cron_line} {cron_marker}")

    # Install new crontab
    new_crontab = "\n".join(lines).strip() + "\n"
    result = subprocess.run(
        ["crontab", "-"],
        input=new_crontab,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, "Cron job created successfully"
    else:
        return False, f"Failed to create cron job: {result.stderr}"


def _delete_cron_job() -> tuple[bool, str]:
    """Delete cron job for Unix systems."""
    cron_marker = "# RSS Summarizer auto-fetch"

    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return True, "No cron jobs configured"

    # Remove RSS entries
    lines = [l for l in result.stdout.split("\n") if cron_marker not in l and "src.cli fetch" not in l]

    new_crontab = "\n".join(lines).strip() + "\n"
    result = subprocess.run(
        ["crontab", "-"],
        input=new_crontab,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return True, "Cron job removed successfully"
    else:
        return False, f"Failed to remove cron job: {result.stderr}"


@app.callback(invoke_without_command=True)
def schedule_main(ctx: typer.Context):
    """
    Manage background feed fetching schedule.

    Examples:
        rss schedule enable --every 3d    # Fetch every 3 days
        rss schedule enable --every 12h   # Fetch every 12 hours
        rss schedule disable              # Remove scheduled task
        rss schedule status               # Show current schedule
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided - show interactive help
        console.print()
        console.print(Panel("[bold]Background Fetch Scheduling[/bold]", style="blue"))
        console.print()
        console.print("Schedule automatic feed fetching so articles accumulate")
        console.print("even when you're not running the app.")
        console.print()
        console.print("[bold]Commands:[/bold]")
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        table.add_row("enable", "Set up automatic fetching")
        table.add_row("disable", "Turn off automatic fetching")
        table.add_row("status", "Check current schedule")

        console.print(table)
        console.print()
        console.print("[dim]Examples:[/dim]")
        console.print("  rss schedule enable --every 3d    [dim]# Every 3 days[/dim]")
        console.print("  rss schedule enable --every 12h   [dim]# Every 12 hours[/dim]")
        console.print("  rss schedule enable --every 30m   [dim]# Every 30 minutes[/dim]")
        console.print()


@app.command()
def enable(
    every: str = typer.Option(
        "1d",
        "--every", "-e",
        help="Fetch interval (e.g., 3d, 12h, 30m)",
    ),
):
    """
    Enable scheduled background fetching.

    Sets up the OS scheduler to run 'rss fetch' at the specified interval.
    This ensures articles accumulate even when you're not using the app.

    Examples:
        rss schedule enable --every 3d    # Every 3 days
        rss schedule enable --every 12h   # Every 12 hours
        rss schedule enable --every 30m   # Every 30 minutes
    """
    interval_minutes = _parse_interval(every)

    if interval_minutes is None:
        console.print(f"[red]Invalid interval: {every}[/red]")
        console.print("[dim]Use format like: 3d (days), 12h (hours), 30m (minutes)[/dim]")
        raise typer.Exit(1)

    if interval_minutes < 5:
        console.print("[yellow]Warning: Intervals less than 5 minutes may be excessive.[/yellow]")

    # Get working directory
    working_dir = str(Path.cwd())

    console.print(f"[bold]Setting up scheduled fetch every {every}...[/bold]")
    console.print(f"[dim]Working directory: {working_dir}[/dim]")
    console.print()

    # Create OS-specific scheduled task
    system = platform.system()

    if system == "Windows":
        success, message = _create_windows_task(interval_minutes, working_dir)
    elif system in ("Linux", "Darwin"):
        success, message = _create_cron_job(interval_minutes, working_dir)
    else:
        console.print(f"[red]Unsupported platform: {system}[/red]")
        raise typer.Exit(1)

    if success:
        _save_schedule_config(True, interval_minutes)
        console.print(f"[green]{message}[/green]")
        console.print()
        console.print(f"[dim]Feed fetching will run every {every}[/dim]")
        console.print("[dim]Run 'rss schedule status' to verify[/dim]")
    else:
        console.print(f"[red]{message}[/red]")
        raise typer.Exit(1)


@app.command()
def disable():
    """
    Disable scheduled background fetching.

    Removes the scheduled task from the OS scheduler.
    """
    console.print("[bold]Disabling scheduled fetch...[/bold]")
    console.print()

    system = platform.system()

    if system == "Windows":
        success, message = _delete_windows_task()
    elif system in ("Linux", "Darwin"):
        success, message = _delete_cron_job()
    else:
        console.print(f"[red]Unsupported platform: {system}[/red]")
        raise typer.Exit(1)

    if success:
        _save_schedule_config(False)
        console.print(f"[green]{message}[/green]")
    else:
        console.print(f"[red]{message}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """
    Show current schedule status.

    Displays whether background fetching is enabled and when
    the next fetch will occur.
    """
    console.print(Panel("[bold]Schedule Status[/bold]", style="blue"))
    console.print()

    config = _load_schedule_config()
    system = platform.system()

    # Check OS scheduler
    if system == "Windows":
        task_info = _get_windows_task_status()

        if task_info:
            console.print("[green]Scheduled fetching is ENABLED[/green]")
            console.print()

            table = Table(show_header=False, box=None)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            if "Status" in task_info:
                table.add_row("Status", task_info["Status"])
            if "Next Run Time" in task_info:
                table.add_row("Next Run", task_info["Next Run Time"])
            if "Last Run Time" in task_info:
                table.add_row("Last Run", task_info["Last Run Time"])
            if "Last Result" in task_info:
                result = task_info["Last Result"]
                result_str = "Success" if result == "0" else f"Error ({result})"
                table.add_row("Last Result", result_str)

            if config.get("interval_minutes"):
                mins = config["interval_minutes"]
                if mins >= 1440:
                    interval_str = f"{mins // 1440} day(s)"
                elif mins >= 60:
                    interval_str = f"{mins // 60} hour(s)"
                else:
                    interval_str = f"{mins} minute(s)"
                table.add_row("Interval", interval_str)

            console.print(table)
        else:
            console.print("[yellow]Scheduled fetching is DISABLED[/yellow]")
            console.print()
            console.print("[dim]Run 'rss schedule enable --every 1d' to enable[/dim]")

    elif system in ("Linux", "Darwin"):
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)

        if result.returncode == 0 and "src.cli fetch" in result.stdout:
            console.print("[green]Scheduled fetching is ENABLED[/green]")
            console.print()

            # Find the RSS line
            for line in result.stdout.split("\n"):
                if "src.cli fetch" in line:
                    console.print(f"[dim]Cron: {line[:60]}...[/dim]")
                    break

            if config.get("interval_minutes"):
                mins = config["interval_minutes"]
                if mins >= 1440:
                    interval_str = f"{mins // 1440} day(s)"
                elif mins >= 60:
                    interval_str = f"{mins // 60} hour(s)"
                else:
                    interval_str = f"{mins} minute(s)"
                console.print(f"[dim]Interval: {interval_str}[/dim]")
        else:
            console.print("[yellow]Scheduled fetching is DISABLED[/yellow]")
            console.print()
            console.print("[dim]Run 'rss schedule enable --every 1d' to enable[/dim]")

    else:
        console.print(f"[yellow]Platform {system} - cannot check scheduler[/yellow]")

        if config.get("enabled"):
            console.print("[dim]Config shows enabled, but cannot verify[/dim]")
