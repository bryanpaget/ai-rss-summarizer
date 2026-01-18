# Codebase Documentation

Generated: 2026-01-18 13:51:55
Directory: ./src
Files processed: 5

---

## System Architecture Document: RSS Summarizer

This document outlines the architecture of the RSS Summarizer application, detailing module dependencies, data flow, entry points, and shared utilities.

### Module Descriptions

**1. `cli` (Command-Line Interface)**

*   **Purpose:** Provides the primary command-line interface for interacting with the RSS summarization system.  Handles user input, CLI argument parsing, and displays results.
*   **Key Functions/Classes:**
    *   `app`: Typer application instance.
    *   Commands: `fetch`, `summarize`, `trends`, `list`, `stats`, `add_feed`, `update`, `report`, `setup`, `discover`, `providers`, `extract_knowledge`, `query`, `graph_path`, `graph_stats`, `context_add`, `context_list`, `emerging`, `graph`.
*   **Dependencies:** `.storage`, `.rss`, `.summarizer`, `.knowledge`, `.cli_perspectives`,  `.cli_constitution`, `.cli_signal_tags`, `.cli_schedule`, `.cli_context`, `.cli_stories`, `.cli_cross_source`, `.cli_daemon`
*   **Dependent Modules:** None. (Root CLI)

**2. `cli_constitution.py`**

*   **Purpose:** Provides commands for managing the "analysis constitution" - a configuration file that defines analysis parameters.
*   **Key Functions/Classes:**
    *   `add_constitution_commands`: Registers constitution-related CLI commands.
    *   `constitution`, `constitution_create`:  Commands to view and edit the constitution.
    *   `_view_constitution`, `_edit_constitution`, `_show_example`: Helper functions for managing the constitution file.
*   **Dependencies:** `typer`, `rich.console`, `.knowledge`
*   **Dependent Modules:** None

**3. `cli_context.py`**

*   **Purpose:** Provides commands to manage user contexts (projects, interests).
*   **Key Functions/Classes:**
    *   `add_context`: Command for adding a user context.
    *   `list_contexts`, `remove_context`, `show_context`: Commands for managing user contexts.
    *   `_run_tree_wizard`: Wizard to select feed topics.
*   **Dependencies:** `typer`, `knowledge`
*   **Dependent Modules:** None

**4. `cli_cross_source.py`**

*   **Purpose:** Provides commands for comparing coverage across different sources and suggesting diverse source feeds.
*   **Key Functions/Classes:**
    *   `compare_sources`: Compares how different sources cover the same story
    *   `list_multi_source_stories`: Lists stories covered by multiple sources
    *   `show_balance`:  Displays political balance of feeds.
    *   `suggest_diverse_sources`: Suggests diverse source feeds.
*   **Dependencies:** `typer`, `storage`, `knowledge`
*   **Dependent Modules:** None

**5. `cli_daemon.py`**

*   **Purpose:**  Provides the background daemon process for automated RSS summarization and knowledge graph updates.
*   **Key Functions/Classes:**
    *   `_parse_interval`: Parses time intervals (e.g., "1h").
    *   `_input_listener`: Monitors user input to gracefully stop the daemon.
    *   `_run_pipeline_step`: Executes a single pipeline step (fetch, summarize, etc.).
    *   `daemon_main`:  Main daemon entry point and scheduling loop.
*   **Dependencies:** `typer`, `storage`, `rss`, `summarizer`, `knowledge`
*   **Dependent Modules:** None

### Data Flow Diagram (Text-Based)

```
User <--> CLI --> Storage <--> RSS --> Summarizer --> Knowledge Base
                                    ^        |
                                    |        v
                                     .CLI_Context, .CLI_CrossSource, ...
```

*   The User interacts with the `CLI`.
*   The `CLI` uses `Storage` to manage feeds and articles.
*   The `CLI` utilizes `RSS` module for fetching RSS content.
*   Fetched content is processed by the `Summarizer` module.
*   Summarized information and extracted knowledge are stored in the `Knowledge Base`.
*  Other CLI modules provide specialized commands which interact with these core components.

### Entry Points (CLI Commands/Main Functions)

*   **`cli.py`**: All Typer commands defined within this file (`fetch`, `summarize`, `trends`, etc.)
*   **`cli_daemon.py`**:  `daemon_main` - Starts the background daemon process.

### Shared Utilities

*   **`.storage`:** Provides database access and storage management functions/classes. (Storage class)
*   **`.rss`:** Contains functions for fetching and parsing RSS feeds. (`fetch_all_feeds`, `load_feeds`)
*   **`.summarizer`:**  Provides summarization functionality. (`summarize_articles`)
*   **`.knowledge`:** Defines classes and functions related to the knowledge base (e.g., `KnowledgeBase`, `UserContext`).
* **`.utils`**: A utility module used within `cli_daemon.py` for common helper methods.

---

This architecture document provides a high-level overview of the RSS Summarizer application's components and their interactions.  More detailed design specifications would be required for implementation.

---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\cli.py

**Lines:** 1237 | **Estimated tokens:** ~10404

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 4-4: import-block `Path` - Imports the `Path` class from the `pathlib` module.
- Lines 5-5: import-block `Optional` - Imports the `Optional` type from the `typing` module.
- Lines 7-7: import-block `typer` - Imports the `typer` library for command-line interface creation.
- Lines 8-9: import-block `rich.console.Console` - Imports the `Console` class from the `rich.console` module for console output.
- Lines 10-10: import-block `rich.table.Table` - Imports the `Table` class from the `rich.table` module for creating tables in the console.
- Lines 11-11: import-block `rich.panel.Panel` - Imports the `Panel` class from the `rich.panel` module for creating panels in the console.
- Lines 12-13: import-block `.storage` - Imports the `Storage` class from the local `storage` module.
- Lines 14-15: import-block `.rss` - Imports the `fetch_all_feeds` and `load_feeds` functions from the local `rss` module.
- Lines 16-17: import-block `.summarizer` - Imports the `summarize_articles` function from the local `summarizer` module.
- Lines 18-25: import-block `.knowledge` - Imports several classes and functions related to knowledge extraction and management.
- Lines 26-27: import-block `.cli_perspectives` - Imports CLI perspective commands.
- Lines 28-29: import-block `.cli_constitution` - Imports CLI constitution commands.
- Lines 30-31: import-block `.cli_signal_tags` - Imports the `app` from the signal tags CLI module.
- Lines 32-33: import-block `.cli_schedule` - Imports the `app` from the schedule CLI module.
- Lines 34-35: import-block `.cli_context` - Imports the `app` from the context CLI module.
- Lines 36-37: import-block `.cli_stories` - Imports the `app` from the stories CLI module.
- Lines 38-39: import-block `.cli_cross_source` - Imports the `app` from the cross-source CLI module.
- Lines 40-41: import-block `.cli_daemon` - Imports the `app` from the daemon CLI module.
- Lines 43-43: constant `console` - Console object with force terminal enabled for encoding issues.
- Lines 68-70: function `is_setup_complete` - Checks if LLM provider has been configured by checking for a file's existence.
- Lines 73-75: function `require_setup` - Exits the program if setup is not complete.
- Lines 80-82: function `get_storage` - Creates and returns a storage instance with the given database path.
- Lines 85-139: @app.command `fetch` - Fetches articles from RSS feeds, displays results in a table, and handles errors.
- Lines 142-186: @app.command `summarize` - Summarizes articles using either a simple summarizer or an LLM provider, optionally with signal tagging.
- Lines 190-250: @app.command `trends` - Analyzes trends from fetched articles and displays top categories along with emerging/declining trends.
- Lines 253-314: @app.command `list` - Lists fetched articles, optionally filtered by trend category or showing summaries.
- Lines 317-343: @app.command `stats` - Displays statistics about the database and feeds.
- Lines 346-398: @app.command `add_feed` - Adds a new RSS feed URL to the configuration file.
- Lines 375-410: @app.callback `main` - Defines the main CLI application and its entry point, also provides help information.
- Lines 412-468: @app.command `update` - Fetches articles and generates summaries based on user input parameters.
- Lines 473-519: @app.command `report` - Generates a comprehensive report with live progress using the LLM for analysis.
- Lines 522-570: @app.command `setup` - Initiates the setup wizard for configuring an LLM provider.
- Lines 574-638: @app.command `discover` - Discovers new RSS feeds based on user interests using an LLM.
- Lines 642-714: @app.command `providers` - Lists available LLM providers and their statuses.
- Lines 717-810: @app.command `extract_knowledge` - Extracts knowledge insights from articles and stores them in the knowledge base.
- Lines 813-890: @app.command `query` - Queries the knowledge base using natural language input.
- Lines 893-957: @app.command `graph_path` - Finds a path between two entities in the knowledge graph.
- Lines 961-1007: @app.command `graph_stats` - Displays statistics about the knowledge graph, including entity counts and relationships.
- Lines 1010-1072: @app.command `context_add` - Adds a user context (project, interest, or watching) to the knowledge base.
- Lines 1075-1134: @app.command `context_list` - Lists available user contexts and their status.
- Lines 1138-1209: @app.command `emerging` - Detects emerging trends in articles based on confidence levels.
- Lines 1213-1279: @app.command `graph` - Explores the knowledge graph around an entity and displays connections.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_constitution.py

**Lines:** 171 | **Estimated tokens:** ~1394

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-6: import-block - Imports modules for CLI functionality and path manipulation
- Lines 7-11: import-block - Imports rich library components for console output
- Lines 12-19: import-block - Imports constitution related functions from the .constitution module
- Lines 20-21: global `console` - Creates a rich console instance with specific formatting options.
- Lines 23-25: function `add_constitution_commands` - Adds constitution-related commands to the typer CLI application. Takes a typer.Typer object as input.
- Lines 23-51: decorator `@app.command` - Decorates the 'constitution' command to add it to the typer application.
- Lines 26-51: decorator `@app.command` - Decorates the 'constitution' function, adding it as a command to the CLI app.
- Lines 27-44: function `constitution` - Defines the 'constitution' command, which allows viewing or editing the constitution. Takes an action argument.
- Lines 52-66: decorator `@app.command("constitution-create")` - Decorates constitution_create function for CLI usage.
- Lines 52-60: decorator `@app.command("constitution-create")` - Decorates the 'constitution_create' function to add it as a CLI command.
- Lines 53-66: function `constitution_create` - Creates a new constitution file based on an example template, prompting if one already exists. Takes a force flag.
- Lines 67-72: constant `path` - Gets the path to the constitution file.
- Lines 73-77: global console - Prints messages about successful constitution creation and editing instructions.
- Lines 79-107: function `_view_constitution` - Displays the current analysis constitution in the terminal using rich formatting.
- Lines 111-135: function `_edit_constitution` - Opens the constitution file in a default editor. Creates it if it doesn't exist, and attempts to open with subprocess.
- Lines 121-126: constant `editor` - Gets the userâ€™s preferred text editor.
- Lines 137-154: function `_get_editor` - Determines the appropriate default editor based on the operating system.
- Lines 157-171: function `_show_example` - Displays the example constitution template in a formatted panel using rich markdown rendering.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_context.py

**Lines:** 850 | **Estimated tokens:** ~8064

- Lines 1-1: global `module_docstring` - CLI commands for user context management.
- Lines 3-5: import-block `uuid` - Imports the uuid module for generating unique identifiers.
- Lines 12-16: constant `QUESTIONARY_AVAILABLE` - Flag indicating whether the 'questionary' library is available, used for interactive prompts.
- Lines 18-19: import-block `knowledge` - Imports KnowledgeBase and UserContext classes from the knowledge module.
- Lines 22-47: function `_add_feeds_to_config` - Adds a list of feeds to a configuration file, avoiding duplicates and returning the number of newly added feeds.
- Lines 49-53: constant `app` - Creates a typer application instance for managing user contexts.
- Lines 57-103: decorator `app.callback` - Decorates the context_main function to be executed when no subcommand is provided, displaying help information.
- Lines 58-103: method `context_main` - Displays interactive help and navigation instructions when invoked without a subcommand.
- Lines 104-156: decorator `app.command` - Decorates the add_context function as a command for adding user contexts.
- Lines 105-156: function `add_context` - Adds a new user context, validates input, and saves it to the knowledge base.
- Lines 159-215: decorator `app.command` - Decorates the list_contexts function as a command for listing user contexts.
- Lines 160-215: function `list_contexts` - Lists all or filtered user contexts, displaying their details in a formatted table.
- Lines 218-261: decorator `app.command` - Decorates the remove_context function as a command for removing user contexts.
- Lines 219-261: function `remove_context` - Removes a user context by name, handling cases where the context is not found or cannot be deleted directly.
- Lines 264-310: decorator `app.command` - Decorates the show_context function as a command for displaying details of a specific user context.
- Lines 265-310: function `show_context` - Displays detailed information about a user context, including its attributes and status.
- Lines 313-483: constant `FEED_TAXONOMY` - A nested dictionary representing the taxonomy of RSS feeds, categorized by subject and containing feed URLs.
- Lines 486-490: constant `SETUP_CATEGORIES` - Creates a dictionary mapping category names to their corresponding subjects for setup wizard purposes.
- Lines 493-512: function `_show_selection_summary` - Generates a summary string of selected feeds and topics.
- Lines 513-779: function `_run_tree_wizard` - Runs the interactive tree navigation wizard to allow users to select RSS feeds and topics.
- Lines 780-824: decorator `app.command` - Decorates the watch_topic function as a command for adding a topic to the user's watchlist.
- Lines 783-846: decorator `app.command` - Decorates the unwatch_topic function as a command for removing a topic from the user's watchlist.
- Lines 849-850: global `app()` - Initializes and runs the Typer application, making the CLI commands available.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_cross_source.py

**Lines:** 381 | **Estimated tokens:** ~3472

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-3: import-block `typer` - Imports the typer library for creating command-line interfaces.
- Lines 4-4: import-block `rich.console` - Imports the Console class from rich for displaying formatted output.
- Lines 5-5: import-block `rich.table` - Imports the Table class from rich for creating tables.
- Lines 6-6: import-block `rich.panel` - Imports the Panel class from rich for creating panels with titles and styles.
- Lines 8-8: import-block `storage` - Imports the Storage class from .storage module.
- Lines 9-9: import-block `knowledge` - Imports the KnowledgeBase class from .knowledge module.
- Lines 10-18: import-block `get_stories_with_multiple_sources`, `compare_story_coverage`, `format_comparison`, `get_current_feed_leanings`, `suggest_diverse_sources`, `get_source_name`, `DIVERSE_FEEDS` - Imports functions and constants from .cross_source module.
- Lines 20-23: global `app` - Defines a Typer app object for command-line interface management.
- Lines 24-24: global `console` - Creates a Console object for displaying output with formatting options.
- Lines 27-27: decorator `@app.command("compare")` - Decorates the compare_sources function as a Typer command named "compare".
- Lines 28-51: function `compare_sources` - Compares how different sources cover the same story, taking Story ID, database path and knowledge base path as input arguments.
- Lines 47-51: function `get_story` - Retrieves a specific story from the storage based on its ID.
- Lines 52-53: function `not found` - Raises an exception when a story is not found.
- Lines 55-60: function `get_stories_with_multiple_sources` - Gets stories with multiple sources.
- Lines 64-65: function `Exit` - Exits the program with an error code if no stories are found.
- Lines 66-71: function `compare_story_coverage` - Compares how different sources cover a given story and returns comparison results.
- Lines 73-74: variable `source_count` - Calculates the number of sources covering the current story.
- Lines 79-105: loop `for perspective in comparison.sources:` - Iterates through each source's perspective on the story.
- Lines 80-82: variable `leaning` - Retrieves the political leaning associated with a given source.
- Lines 81-93: variable `leaning_color` - Assigns a color based on the political leaning of the source.
- Lines 94-95: variable `perspective.source_name` - Prints the name of each perspective for the story being compared.
- Lines 96-100: loop `if perspective.emphasis:` - Iterates through emphasized points from a particular source's perspective.
- Lines 97-98: variable `perspective.emphasis` - Retrieves and prints emphasis points made by the perspective.
- Lines 100-102: loop `for claim in perspective.key_claims[:3]:` - Iterates through key claims from a particular source's perspective.
- Lines 101-103: variable `claim` - Retrieves and prints each of three key claims.
- Lines 107-109: block `if comparison.common_facts:` - Checks if there are any common facts across the sources.
- Lines 110-112: loop `for fact in comparison.common_facts[:5]:` - Iterates through common facts.
- Lines 113-116: block `if comparison.coverage_gap:` - Checks for gaps in coverage from different sources.
- Lines 117-119: loop `for gap in comparison.coverage_gap[:5]:` - Iterates through coverage gaps.
- Lines 120-122: variable `comparison.coverage_gap` - Prints out the identified coverage gaps for a story.
- Lines 123-124: function `compare_sources` - Defines a CLI command to compare stories from different sources.
- Lines 125-131: decorator `@app.command("multi")` - Decorates list_multi_source_stories as a Typer command named "multi".
- Lines 127-139: function `list_multi_source_stories` - Lists stories covered by multiple sources, taking minimum sources and limit as input arguments.
- Lines 137-140: function `Storage` - Creates an instance of the Storage class to interact with database.
- Lines 139-140: function `get_stories_with_multiple_sources` - Retrieves stories covered by multiple sources, filtering based on minimum source count and limit.
- Lines 142-144: function `Exit` - Exits the program if no stories found with multiple coverage.
- Lines 146-150: variable `Table` - Creates a table for displaying multi-source stories.
- Lines 153-163: loop `for story in stories:` - Iterates through each story to display information about it.
- Lines 153-157: function `get_articles_by_ids` - Retrieves articles associated with a given story ID's.
- Lines 157-160: function `extract_domain` - Extracts domain from URL, used to identify unique source domains.
- Lines 157-158: variable `unique_sources` - Creates unique sources for the article set being compared.
- Lines 160-164: table row creation - Adds a row of data for each story to the table with Story Title, number of sources, article count and ID.
- Lines 165-169: function `get_source_name` - Retrieves name based on source identifier (domain).
- Lines 170-172: decorator `@app.command("balance")` - Decorates show_balance as a Typer command named "balance".
- Lines 173-185: function `show_balance` - Shows the political balance of feeds, taking file path as input argument.
- Lines 181-182: function `get_current_feed_leanings` - Retrieves current feed leanings based on the provided file path.
- Lines 186-193: variable `total` - Calculates total number of articles for balance calculation.
- Lines 194-200: variable distribution - Iterates through various political categories (left, center, right) to determine their representation in feed balance.
- Lines 200-203: variable colors - Defines a dictionary mapping political leanings to corresponding color codes used for visual display.
- Lines 204-219: loop `for category in ["left", "center", "right", "unknown"]:` - Iterates through different categories and prints their distribution.
- Lines 217-218: variable `pct` - Calculates percentage of sources within a given political leaning group.
- Lines 219-223: table row creation - Adds data for each category (political leaning) to the table, displaying count, percentage, and source names.
- Lines 224-230: block `if left_count > right_count * 2:` - Checks if feeds lean heavily towards a political direction.
- Lines 231-236: conditional assessments - Provides assessment based on the overall feed balance to suggest improvements in source diversity.
- Lines 237-240: assessment of balancedness - Provides an encouraging message when feed mix appears relatively balanced.
- Lines 241-245: decorator `@app.command("suggest")` - Decorates `suggest_sources` as a Typer command named "suggest".
- Lines 246-267: function `suggest_diverse_sources` - Suggests sources based on the input category and feeds file, providing diverse source recommendations.
- Lines 258-293: loop `for category in ["left", "center", "right"]:` - Iterates through different categories to display suggested sources for each.
- Lines 267-270: variable `has_suggestions` - Tracks whether any suggestions are found for the current category.
- Lines 284-290: conditional output of all diverse source list - Provides an option to see complete list of available sources across categories.
- Lines 291-295: function `add_suggested_sources` - Adds suggested diverse sources, taking a category and feeds file as input arguments, with dry run feature for previewing changes.
- Lines 297-304: function parameters - Defines the parameters of add_suggested_sources function.
- Lines 313-336: variable `load_feeds` - Loads existing feeds from a file to determine which sources have already been added.
- Lines 338-342: conditional dry run execution - Checks if dry run is enabled and prints what would be added, without making changes.
- Lines 345-351: variable `Path` - Creates a path object representing the feeds file to add new sources.
- Lines 346-350: variable `open` - Opens feed file in append mode to add suggested diverse sources to it.
- Lines 352-357: variable `rss fetch` - Prints message encouraging user to run `rss fetch`.
- Lines 358-360: function `list_diverse_sources` - Lists all available diverse sources, categorizing by political leanings.
- Lines 361-370: function parameters - Defines the parameters of list_diverse_sources functions.
- Lines 372-379: loop and conditional execution to display diverse source information based on categories.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_daemon.py

**Lines:** 302 | **Estimated tokens:** ~2487

- Lines 1-12: global `module_docstring` - Module docstring describing the CLI daemon's functionality and pipeline steps.
- Lines 14-17: import-block `sys`, `time`, `threading`, `datetime` - Imports standard library modules for system interaction, time management, threading, and date/time handling respectively.
- Lines 18-19: import-block `typing` - Imports typing module for type hinting.
- Lines 20-24: import-block `typer`, `rich.console`, `rich.panel`, `rich.table` - Imports libraries for creating command-line interfaces, rich text output and table formatting.
- Lines 26-27: import-block `.utils` - Imports a module containing utility functions used by the daemon.
- Lines 28-31: global `app`, `console` - Initializes a Typer app object named 'app' for command line interface, and a rich console object with specific settings.
- Lines 34-36: global `_stop_requested`, `_input_thread` - Defines global variables used to control graceful shutdown of the daemon process and manage the input listener thread respectively.
- Lines 38-57: function `_parse_interval` - Parses a string representing an interval (e.g., "5m", "1h") into seconds, handles various suffixes ('s', 'm', 'h', 'd'), returns None if parsing fails.
- Lines 59-72: function `_input_listener` - A background thread that listens for user input to quit the daemon process gracefully, checks for 'q' or similar commands and sets a flag to stop processing.
- Lines 74-173: function `_run_pipeline_step` - Executes a specific pipeline step (fetch, LLM processing, embeddings, story matching, connection detection) up to a given level, updates statistics accordingly.
- Lines 176-299: function `daemon_main` - The main entry point for the daemon process, handles command-line arguments, sets up intervals, and runs pipeline steps in a loop until stopped by user.
- Lines 218-225: parameter `every` - Defines the processing interval using Typer's Option feature, provides help text and default value.
- Lines 226-230: parameter `step` - Specifies the pipeline step level with validation constraints and a description of each step level.
- Lines 231-237: parameter `limit` - Allows limiting the number of articles processed per cycle, providing flexibility for testing or resource management.
- Lines 254-256: global `_stop_requested`, `_input_thread` - Initializes and starts a background thread to listen for user input and stop requests during daemon operation.
- Lines 271-283: variable `cycle_count`, `cycle_start` - Tracks the number of cycles completed and start time, used for informational output.
- Lines 286-294: try/except block in _run_pipeline_step - Handles exceptions that might occur during pipeline execution, ensuring continued operation.
- Lines 295-301: KeyboardInterrupt handling - Catches KeyboardInterrupt to allow graceful exit on Ctrl+C and prints a message upon termination.

---


