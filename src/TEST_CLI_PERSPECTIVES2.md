# Codebase Documentation

Generated: 2026-01-18 13:40:52
Directory: ./src
Files processed: 1

---

```markdown
## System Architecture Document: RSS Summarizer

This document outlines the architecture of the RSS Summarizer system, based on the provided file summaries.

### Module Overview

Here's a breakdown of each module, including its purpose, key exports, dependencies, and dependents.

**1. `cli_perspectives.py` (CLI Perspective Management)**

*   **Primary Purpose:** Provides CLI commands for managing and displaying synthesized perspectives on stories.
*   **Key Functions/Classes Exported:**
    *   `add_perspective_commands`: Adds perspective-related commands to a Typer app.
    *   `perspectives` (CLI command): Displays story perspectives.  Handles both specific story IDs and overall top stories.
    *   `configure_perspectives` (CLI command): Allows interactive configuration of default perspective categories.
    *   `cluster_stories` (CLI command): Clusters articles into stories.
*   **Dependencies:**
    *   `typer`: For CLI framework.
    *   `.storage`:  For storage interaction (`Storage` class).
    *   `perspectives` module:  For perspective synthesis functions (`synthesize_perspectives`, `get_user_perspective_config`, `PERSPECTIVE_CATEGORIES`).
    *   `storage_perspectives.add_perspective_methods`: For adding methods to the Storage class.
    *   `get_best_provider`:  (Likely) for selecting a perspective synthesis provider.
*   **Dependents:** None (This is the entry point for user interaction).

**2. `.storage` (Data Storage)**

*   **Primary Purpose:** Handles persistent storage of articles, stories, and other related data. The `Storage` class manages this.
*   **Key Functions/Classes Exported:**
    *  `Storage`: Class responsible for interacting with the database. Provides methods to retrieve and store data.
*   **Dependencies:** (Likely) Database library (e.g., SQLite, PostgreSQL - not explicitly stated in summary).
*   **Dependents:**
    *   `cli_perspectives.py`:  Uses `Storage` for retrieving story clusters, articles, user configurations etc.

**3. `perspectives` module (Perspective Synthesis)**

*   **Primary Purpose:** Synthesizes perspectives on stories based on categories and provider.
*   **Key Functions/Classes Exported:**
    *   `synthesize_perspectives`: Generates perspective text for a given story, category and provider.
    *   `get_user_perspective_config`: Retrieves the user's configured perspective settings.
    *   `PERSPECTIVE_CATEGORIES`: A constant defining available perspective categories.
*   **Dependencies:**  (Likely)  External Perspective Synthesis Provider (not explicitly mentioned).
*   **Dependents:**
    *   `cli_perspectives.py`: Uses `synthesize_perspectives`, `get_user_perspective_config`, and `PERSPECTIVE_CATEGORIES`.

**4. `storage_perspectives` module (Storage Perspective Methods)**

*   **Primary Purpose:** Provides methods to add perspective-related functionality to the Storage class.
*   **Key Functions/Classes Exported:**
    *   `add_perspective_methods`:  A function that configures and extends the `Storage` class with perspective-specific features.
*   **Dependencies:**
    *   `.storage`: Extends the `Storage` class.
*   **Dependents:**
    *   `cli_perspectives.py`: Uses `add_perspective_methods`.

### System Map (Conceptual)

```
+---------------------+      Uses       +----------------------+     Uses        +-----------------------+
|  cli_perspectives.py |--------------->|       .storage         |-------------->| perspectives module    |
|  (CLI Interaction)   |                 |  (Data Storage)       |                | (Perspective Synthesis)|
+---------------------+      Provides    +----------------------+     Provides +-----------------------+
                                                            ^                    |
                                                            | Depends on             |
                                                            |                         v
                                                          +-----------------------+
                                                          | storage_perspectives   |
                                                          |  (Storage Extensions) |
                                                          +-----------------------+

```

### Data Flow Diagram (Text-Based)

1.  User interacts with CLI (`cli_perspectives.py`).
2.  `cli_perspectives.py` calls `storage.get_story_cluster()`.
3.  `storage` retrieves data from the database.
4.  `cli_perspectives.py` calls `synthesize_perspectives()` with story and category information.
5.  `synthesize_perspectives()` generates perspective text, potentially using an external provider.
6.  `cli_perspectives.py` displays results to the user.
7. If clustering is requested, `cli_perspectives.py` calls methods related to article processing and storage for re-clustering.

### Entry Points

*   **CLI Commands:**
    *   `typer CLI`: Initiates the application and exposes commands defined in `cli_perspectives.py`.  Specifically:
        *   `rsssummarizer perspectives [story_id] [categories] [limit] [update_clusters]`
        *   `rsssummarizer configure-perspectives`
        *   `rsssummarizer cluster-stories [force]`
*   **Main Function:** (Implicit)  The main execution flow within `cli_perspectives.py`.

### Shared Utilities

Based on the summaries, these are likely shared utilities:

*   Logging/Error Handling (not explicitly mentioned but essential for a robust system).
*   Configuration Management (for database paths, API keys, etc.).
*   Possibly some basic data transformation functions within `storage_perspectives` module.
```

---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\cli_perspectives.py

**Lines:** 248 | **Estimated tokens:** ~2440

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-4: import-block `typing.Optional` - Imports Optional type from the typing module
- Lines 5-7: import-block `typer` - Imports typer library
- Lines 8-9: constant `console` - Console instance for displaying output
- Lines 12-12: function `add_perspective_commands` - Adds perspective-related commands to the CLI app, taking a Typer app object as input.
- Lines 16-28: decorator `@app.command()` - Decorates the 'perspectives' function as a CLI command
- Lines 17-18: argument `story_id` - Optional string representing a specific story cluster ID
- Lines 19-22: argument `categories` - Optional comma-separated list of perspective categories
- Lines 24-27: argument `limit` - The number of stories to show, defaults to 10 if no story_id is provided.
- Lines 29-32: argument `update_clusters` - Boolean flag to update story clusters before showing (can be slow)
- Lines 34-38: argument `db_path` - Path to the database file
- Lines 40-67: function body of `perspectives` - Implements the logic for displaying synthesized perspectives on stories.
- Lines 49-51: import-block `storage` - Imports Storage class from .storage module
- Lines 52-54: import-block `synthesize_perspectives, get_user_perspective_config, PERSPECTIVE_CATEGORIES` - imports functions/constants from the perspectives module
- Lines 56-57: import-block `add_perspective_methods` - Imports add_perspective_methods function from storage_perspectives
- Lines 59-60: import-block `get_best_provider` - Imports get_best_provider function
- Lines 62-63: method body of `add_perspective_methods` - Calls the Storage constructor and sets up other dependencies.
- Lines 64-71: code block - Updates story clusters if requested, displaying progress information to the console.
- Lines 73-74: code block - Gets user perspective configuration
- Lines 75-78: code block - Determines perspective categories based on user config or defaults.
- Lines 79-85: code block - Validates the specified categories against available options, and raises an error if invalid
- Lines 86-91: code block - Handles showing perspectives for a specific story ID.
- Lines 88-89: method `storage.get_story_cluster` - Retrieves the cluster associated with a given story ID from storage.
- Lines 89-95: code block - Gets articles by cluster and handles edge cases when no stories are present in that cluster.
- Lines 97-100: code block - Prints information about the current story.
- Lines 102-116: method body of `synthesize_perspectives` - Synthesizes perspectives for a given story, category and provider.
- Lines 118-120: code block - Generates confidence bar using ASCII characters based on perspective confidence value.
- Lines 123-137: code block - Handles displaying perspectives for top stories.
- Lines 146-159: code block - Shows a limited view of the first perspective category for an overview.
- Lines 163-165: decorator `@app.command()` - Decorates `configure_perspectives` as a CLI command.
- Lines 170-174: function body of `configure_perspectives` - Configures default perspective categories via interactive prompts, using storage and user configuration.
- Lines 185-186: method body of `add_perspective_methods` - Calls the Storage constructor and sets up other dependencies.
- Lines 193-204: code block - Displays current perspective settings and available options for configuration.
- Lines 207-209: decorator `@app.command()` - Decorates cluster_stories as a CLI command.
- Lines 212-215: argument `force` - Boolean flag to force re-clustering of all articles
- Lines 223-238: function body of `cluster_stories` - Clusters articles into stories, providing progress information and stats.
- Lines 237-240: code block - Displays statistics about the clustering process.
- Lines 243-248: code block - Shows top story clusters after clustering.

---


