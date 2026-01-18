# Codebase Documentation

Generated: 2026-01-18 10:13:42
Directory: src
Files processed: 1

---

```markdown
# System Architecture Document: RSS Summarizer

## Module: utils

**1. Primary Purpose:** Provides utility functions for data formatting and manipulation.  Specifically focuses on handling durations.

**2. Key Functions/Classes Exported:**

*   `format_duration(seconds)`: Converts seconds into a human-readable duration string (e.g., "2 minutes", "1 hour 30 minutes", "2 days").

**3. Dependencies:** None

**4. Dependents:**  (Assumed - needs more information from other file summaries) Likely depends on modules that handle data processing or display information to the user.


## Data Flow Diagram (Text-Based)

```
+-----------------+       +---------------------+
|  Data Source    |------>|     Core Logic      |
+-----------------+       +---------------------+
                                    |
                                    | (Data Processing & Summarization)
                                    |
                                    v
                           +---------------------+
                           |        utils        |
                           +---------------------+
                                    |  format_duration()
                                    |
                                    v
                           +---------------------+
                           |      User Interface |
                           +---------------------+

```

## Entry Points

*   **CLI Commands:** (Assumed - needs more information from other file summaries). Potentially used by CLI commands to display durations.
*   **Main Functions:**  (Assumed - needs more information from other file summaries). Possibly called internally by the core logic for formatting output.



## Shared Utilities

*   `format_duration()`: (Defined in `utils.py`)  Used across modules that need to present time-related information to the user (e.g., display summary generation times, processing durations).
```


---

# File-by-File Documentation
## Users\jpswi\personal projects\RSSsummarizer\src\utils.py

**Lines:** 46 | **Estimated tokens:** ~307

- Lines 1-5: import-block `imports` - Standard library (math)
- Lines 7-38: function `format_duration` - Formats a duration in seconds into a human-readable string (seconds, minutes, hours, or days). It handles negative inputs and provides clear formatting for different time ranges.

---


