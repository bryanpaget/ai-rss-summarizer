"""Shared utility functions."""


def format_duration(seconds: float) -> str:
    """
    Format seconds into human-readable duration.

    Examples:
        45.2 -> "45.2s"
        90 -> "1m 30s"
        3661 -> "1h 1m"
        90000 -> "1d 1h"

    Use this ONE function for ALL time display in the codebase.
    Do not create local formatting logic.
    """
    if seconds < 0:
        return "0s"

    if seconds < 60:
        # Under a minute: show decimal seconds
        return f"{seconds:.1f}s"

    elif seconds < 3600:
        # Under an hour: show minutes and seconds
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        if secs == 0:
            return f"{mins}m"
        return f"{mins}m {secs}s"

    elif seconds < 86400:
        # Under a day: show hours and minutes
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"

    else:
        # Days and hours
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        if hours == 0:
            return f"{days}d"
        return f"{days}d {hours}h"
