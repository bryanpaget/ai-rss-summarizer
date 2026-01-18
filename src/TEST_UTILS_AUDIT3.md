# Codebase Documentation

Generated: 2026-01-18 13:11:29
Directory: ./src
Files processed: 1

---

```markdown
# System Architecture Document

## Module: utils

**1. Primary Purpose:** Provides utility functions for formatting durations and handling basic file operations.

**2. Key Functions/Classes it Exports:**
* `format_duration(seconds)`: Formats a given number of seconds into a human-readable duration string (e.g., "1m 30s", "2d").

**3. Dependencies:**
* `httpx`: Used for making HTTP requests (likely for fetching data from RSS feeds).
* `os`: For interacting with the operating system (file operations).
* `sys`:  For accessing system-specific parameters and functions.
* `json`: For working with JSON data.
* `dataclasses`: For creating data classes.

**4. Dependents:**
* Other modules that need to format durations from RSS feed entries or other data sources.


## Data Flow Diagram (Text-Based)

```
[RSS Feed Fetcher] --> [utils.format_duration(seconds)] --> [Data Processing Module]
                                                        ^
                                                        |
                                                        [HTTP Request]
```

## Entry Points

*   **CLI Command:**  Not directly exposed as a CLI command. Functionality is used internally by other modules. 
*   **Main Function:** No direct main function; functions are imported and utilized within other modules.

## Shared Utilities

*   `format_duration(seconds)`: Duration formatting logic.



---
```

---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\utils.py

**Lines:** 46 | **Estimated tokens:** ~307

- Lines 1-1: import-block `imports` - Standard library (os, sys, json) and third-party (httpx, dataclasses)
- Lines 3-13: function `format_duration` - Format seconds into human-readable duration, handling values under a minute, hour, day, and beyond.
- Lines 16-22: function `format_duration` - Returns "0s" if seconds are negative.
- Lines 22-24: function `format_duration` - If seconds are less than 60, return formatted string with decimal seconds.
- Lines 24-28: function `format_duration` - If seconds are less than 3600, return formatted string with minutes and seconds.
- Lines 28-29: function `format_duration` - If seconds are less than 86400, return formatted string with hours and minutes.
- Lines 29-31: function `format_duration` - If seconds are greater or equal to 86400, return formatted string with days and hours.

---


