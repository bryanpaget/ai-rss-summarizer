# Codebase Documentation

Generated: 2026-01-18 13:57:03
Directory: ./src
Files processed: 10

---

## System Architecture Document: RSS Summarizer

This document outlines the architecture of the RSS summarizer system.

### Module Overview & Dependencies

**1. CLI (cli.py)**

*   **Purpose:** Provides the command-line interface for interacting with the system, handling user commands like fetching, summarizing, analyzing trends, and managing knowledge graphs.
*   **Exports:** Typer CLI application (`app`), functions for setup checks (`is_setup_complete`, `require_setup`), core functionality commands (fetch, summarize, trends, list, stats, add\_feed, update, report, setup, providers, discover, query, contradictions, graph\_stats, graph, graph\_path, knowledge\_stats, context commands, emerging).
*   **Dependencies:** `storage`, `rss`, `summarizer`, `trends`, `emergence`, `knowledge`, `cli_perspectives`, `cli_constitution`, `cli_signal_tags`, `cli_context`, `cli_cross_source`, `cli_daemon`
*   **Dependent Modules:** None

**2. CLI Perspectives (cli_perspectives.py)**

*   **Purpose:** Provides commands for managing perspectives on stories.
*   **Exports:** Function `add_perspective_commands`.
*   **Dependencies:** `typer`, `storage`, `knowledge`
*   **Dependent Modules:** `CLI`

**3. CLI Constitution (cli_constitution.py)**

*   **Purpose:** Provides commands for managing the system's constitution file.
*   **Exports:** Function `add_constitution_commands`.
*   **Dependencies:** `typer`, `storage`, `knowledge`
*   **Dependent Modules:** `CLI`

**4. CLI Signal Tags (cli_signal_tags.py)**

*   **Purpose:** Provides commands for managing signal tags.
*   **Exports:** Typer app object (`app`).
*   **Dependencies:** `typer`, `storage`, `knowledge`
*   **Dependent Modules:** `CLI`

**5. CLI Context (cli_context.py)**

*   **Purpose:** Provides commands for managing user contexts and feeds.
*   **Exports:** Typer app object (`app`), functions related to context management.
*   **Dependencies:** `typer`, `storage`, `knowledge`, `questionary`
*   **Dependent Modules:** `CLI`

**6. CLI Cross-Source (cli_cross_source.py)**

*   **Purpose:** Provides commands for cross-source analysis and comparison.
*   **Exports:** Typer app object (`app`), functions for source comparison and balance.
*   **Dependencies:** `typer`, `storage`, `knowledge`
*   **Dependent Modules:** `CLI`

**7. CLI Daemon (cli_daemon.py)**

*   **Purpose:**  Provides a daemon mode for automated background processing.
*   **Exports:** Typer app object (`app`), functions related to daemon control and pipeline execution.
*   **Dependencies:** `typer`, `storage`, `knowledge`, `llm_providers`
*   **Dependent Modules:** `CLI`

**8. CLI Stories (cli_stories.py)**

*   **Purpose:** Provides commands for managing stories, including listing and fixing titles.
*   **Exports:** Typer app object (`app`), functions related to story management.
*   **Dependencies:** `typer`, `storage`, `knowledge`
*   **Dependent Modules:** `CLI`

**9. Storage (storage.py)**

*   **Purpose:** Manages the storage and retrieval of data, including feeds, articles, stories, and knowledge graph information.
*   **Exports:** Class `Storage`, functions for database interaction.
*   **Dependencies:**  SQLAlchemy or similar ORM library
*   **Dependent Modules:** All CLI modules, Clustering, Knowledge

**10. RSS (rss.py)**

*   **Purpose:** Handles fetching and parsing of RSS feeds.
*   **Exports:** Functions to fetch and load RSS feeds (`fetch_all_feeds`, `load_feeds`).
*   **Dependencies:**  `requests` or similar HTTP client library, XML/RSS parsing libraries.
*   **Dependent Modules:** `CLI`

**11. Summarizer (summarizer.py)**

*   **Purpose:** Responsible for summarizing articles using an LLM provider.
*   **Exports:** Function to summarize articles (`summarize_articles`).
*   **Dependencies:** LLM Provider Interface, `storage`
*   **Dependent Modules:** `CLI`

**12. Trends (trends.py)**

*   **Purpose:** Analyzes trends within the collected data.
*   **Exports:** Functions to analyze and retrieve articles by trend (`analyze_trends`, `get_articles_by_trend`).
*   **Dependencies:**  Data analysis libraries, potentially LLMs for trend extraction.
*   **Dependent Modules:** `CLI`

**13. Emergence (emergence.py)**

*   **Purpose:** Detects emerging trends from the analyzed data and formats them for display.
*   **Exports:** Functions to detect emerging trends and format their display (`detect_emerging_trends`, `format_emerging_trend`).
*   **Dependencies:**  `trends`
*   **Dependent Modules:** `CLI`

**14. Knowledge (knowledge.py)**

*   **Purpose:** Provides functions for extracting knowledge from articles, creating a knowledge graph, and querying it.
*   **Exports:** Class `KnowledgeBase`, functions for extraction (`extract_insights_from_article`, `extract_triples_from_article`, etc.), query functions (`query_knowledge_base`).
*   **Dependencies:**  LLM Provider Interface, NLP libraries (e.g., spaCy), Graph database library.
*   **Dependent Modules:** `CLI`

**15. Clustering (clustering.py)**

*   **Purpose:** Groups articles into stories and extracts news items from them.
*   **Exports:** Classes `StoryClusterer`, `NewsItemExtractor`, `StoryEvolutionTracker`, Functions for processing clustering tasks.
*   **Dependencies:** LLM Provider Interface, `storage`, `knowledge`
*   **Dependent Modules:** `CLI`, `Knowledge`

### Data Flow Diagram (Text-Based)

```
[RSS Feeds] --> [RSS (rss.py)] --> [Storage (storage.py)]
[Storage (storage.py)] --> [Summarizer (summarizer.py)] --> [Storage (storage.py)]
[Storage (storage.py)] --> [Knowledge (knowledge.py)] --> [Storage (storage.py)]
[Storage (storage.py)] --> [Trends (trends.py)] --> [Emergence (emergence.py)] --> [CLI (cli.py)]
[Storage (storage.py)] --> [Clustering(clustering.py)] --> [Knowledge(knowledge.py)] --> [Storage(storage.py)]
[CLI (cli.py)] --> [User Interface]
```

### Entry Points (CLI Commands)

*   `--setup`: Configure LLM provider.
*   `fetch`: Fetch articles from configured feeds.
*   `summarize`: Summarize fetched articles.
*   `trends`: Analyze trends in articles.
*   `list`: List articles with filtering options.
*   `add_feed`: Add a new RSS feed.
*   `update`: Update the system (fetch and summarize).
*   `query`: Query the knowledge graph.
*   `graph`: Explore the knowledge graph around an entity.
*   `emerging`: Detect emerging trends.

### Shared Utilities

*   **Logging:**  A central logging module for consistent logging across all modules.
*   **Configuration Management:** A centralized configuration management system to handle LLM provider settings and other parameters.
*   **Error Handling:** Standardized error handling throughout the application.
*   **LLM Provider Interface:** Common interface for interacting with different LLM providers.



---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\cli.py

**Lines:** 1237 | **Estimated tokens:** ~10404

- Lines 1-1: global `"""Command-line interface for the RSS summarizer."""` - Module docstring
- Lines 4-4: import-block `from pathlib import Path` - Imports the `Path` class from the `pathlib` module for file path manipulation.
- Lines 5-5: import-block `from typing import Optional` - Imports the `Optional` type hint for function arguments that can be None.
- Lines 7-7: import-block `import typer` - Imports the Typer library for creating command-line interfaces.
- Lines 8-8: import-block `from rich.console import Console` - Imports the `Console` class from the Rich library for styled terminal output.
- Lines 9-9: import-block `from rich.table import Table` - Imports the `Table` class from the Rich library for creating formatted tables in the console.
- Lines 10-10: import-block `from rich.panel import Panel` - Imports the `Panel` class from the Rich library to create panels with borders and titles.
- Lines 12-12: import-block `from .storage import Storage` - Imports the `Storage` class from the local module for database interaction.
- Lines 13-13: import-block `from .rss import fetch_all_feeds, load_feeds` - Imports functions related to RSS feed fetching and loading.
- Lines 14-14: import-block `from .summarizer import summarize_articles` - Imports the `summarize_articles` function for summarizing articles.
- Lines 15-15: import-block `from .trends import analyze_trends, get_articles_by_trend` - Imports functions related to trend analysis and article filtering by trends.
- Lines 16-16: import-block `from .emergence import detect_emerging_trends, format_emerging_trend` - Imports functions for detecting emerging trends and formatting their display.
- Lines 18-25: import-block `from .knowledge import (KnowledgeBase, extract_insights_from_article, extract_triples_from_article, extract_entity_relationships_from_article, detect_connections, format_relationship, query_knowledge_base)` - Imports functions and classes related to knowledge extraction and querying.
- Lines 26-27: import-block `from .cli_perspectives import add_perspective_commands` - Imports the function for adding perspective commands to the CLI.
- Lines 28-29: import-block `from .cli_constitution import add_constitution_commands` - Imports the function for adding constitution commands to the CLI.
- Lines 30-31: import-block `from .cli_signal_tags import app as signal_tags_app` - Imports the `app` object from the `cli_signal_tags` module, aliased as `signal_tags_app`.
- Lines 32-33: import-block `from .cli_schedule import app as schedule_app` - Imports the `app` object from the `cli_schedule` module, aliased as `schedule_app`.
- Lines 34-35: import-block `from .cli_context import app as context_app` - Imports the `app` object from the `cli_context` module, aliased as `context_app`.
- Lines 35-41: class `app` - Creates a Typer CLI application instance for managing RSS summaries.
- Lines 36-37: import-block `from .cli_stories import app as stories_app` - Imports the `app` object from the `cli_stories` module, aliased as `stories_app`.
- Lines 38-39: import-block `from .cli_cross_source import app as cross_source_app` - Imports the `app` object from the `cli_cross_source` module, aliased as `cross_source_app`.
- Lines 40-41: import-block `from .cli_daemon import app as daemon_app` - Imports the `app` object from the `cli_daemon` module, aliased as `daemon_app`.
- Lines 42-42: constant `console` - Initializes a Rich Console with force terminal and legacy windows enabled.
- Lines 43-44: method `ClassName.add_perspective_commands` - Registers perspective commands to the CLI app.
- Lines 46-47: method `ClassName.add_constitution_commands` - Registers constitution commands to the CLI app.
- Lines 49-51: method `ClassName.add_typer` - Adds a sub-app (signal tags) as a subcommand group named "tag".
- Lines 53-55: method `ClassName.add_typer` - Adds a sub-app (schedule) as a subcommand group named "schedule".
- Lines 56-58: method `ClassName.add_typer` - Adds a sub-app (context) as a subcommand group named "context".
- Lines 59-61: method `ClassName.add_typer` - Adds a sub-app (stories) as a subcommand group named "stories".
- Lines 62-64: method `ClassName.add_typer` - Adds a sub-app (cross source) as a subcommand group named "sources".
- Lines 65-67: method `ClassName.add_typer` - Adds a sub-app (daemon) as a subcommand group named "daemon".
- Lines 68-70: function `is_setup_complete` - Checks if the LLM provider has been configured by checking for the existence of the llm.json file.
- Lines 73-75: function `require_setup` - Exits the program with an error message if the setup is not complete.
- Lines 80-82: function `get_storage` - Creates and returns a Storage instance using the provided database path.
- Lines 86-110: command `fetch` - Fetches articles from RSS feeds based on configuration, displays results in a table. Requires setup.
- Lines 142-187: command `summarize` - Summarizes articles, optionally using an LLM and assigning signal tags.  Requires setup.
- Lines 193-250: command `trends` - Analyzes trends within fetched articles and displays top trends. Requires setup.
- Lines 256-314: command `list` - Lists articles with filtering options (trend, summary). Requires setup.
- Lines 327-341: command `stats` - Displays statistics about the database, including feed counts. Requires setup.
- Lines 370-398: command `add_feed` - Adds a new RSS feed to the feeds file.
- Lines 406-453: command `update` -  Fetches and summarizes articles with filtering options; a primary user command. Requires setup.
- Lines 472-501: command `report` - Generates a comprehensive report of LLM processing, offering live progress display. Requires setup.
- Lines 509-536: command `setup` - Guides the user through configuring an LLM provider.
- Lines 538-572: command `providers` - Displays available LLM providers and their status.
- Lines 574-611: command `discover` - Uses AI to suggest relevant RSS feeds based on a query string. Requires setup.
- Lines 619-665: command `help` - Shows help information, customized with setup status.
- Lines 680-723: function `extract_knowledge` - Extracts insights from articles and stores them in the knowledge base. Requires setup.
- Lines 730-754: command `query` - Queries the knowledge graph using natural language input.  Requires setup.
- Lines 759-801: command `contradictions` - Displays contradictions detected within the knowledge graph. Requires setup.
- Lines 806-829: command `graph_stats` - Shows statistics about the knowledge graph, including entity relationships and predicates. Requires setup.
- Lines 835-904: command `graph` - Explores the knowledge graph around a given entity.  Requires setup.
- Lines 910-976: command `graph_path` - Finds a path between two entities in the knowledge graph. Requires setup.
- Lines 983-1018: command `knowledge_stats` - Displays statistics about the knowledge base, including insights and relationships.  Requires setup.
- Lines 1024-1067: command `context_add` - Adds a new user context (project/interest) to the knowledge base. Requires setup.
- Lines 1073-1098: command `context_list` - Lists configured user contexts.  Requires setup.
- Lines 1102-1155: command `main` - The main entry point for the CLI, prints help message if no arguments are provided.
- Lines 1134-1169: command `emerging` - Identifies and displays emerging trends based on confidence level filtering. Requires setup.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_constitution.py

**Lines:** 171 | **Estimated tokens:** ~1394

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-6: import-block - Imports necessary modules for CLI functionality
- Lines 7-9: import-block - Imports rich console and panel elements
- Lines 10-11: import-block - Imports rich markdown element
- Lines 12-18: import-block - Imports constitution related functions from .constitution module
- Lines 20-21: global `console` - Creates a Rich Console instance with specific settings.
- Lines 23-24: function `add_constitution_commands` - Adds constitution commands to the CLI application
- Lines 26-51: function `constitution` - Defines a command to view, edit, or show example constitution. Accepts action argument.
- Lines 52-60: function `constitution_create` - Creates a new constitution file from template with overwrite option.
- Lines 61-77: docstring of `constitution_create` - Describes the purpose and usage of the create constitution command.
- Lines 79-107: function `_view_constitution` - Displays the current constitution content using rich markdown rendering or a message if none exists.
- Lines 110-116: function `_edit_constitution` - Opens the constitution file in the user's default editor, creating one if it doesn't exist.
- Lines 117-135: docstring of `_edit_constitution` - Explains how to open the current constitution for editing.
- Lines 121-146: function `_get_editor` - Determines and returns the user's preferred text editor based on environment variables or platform defaults.
- Lines 147-153: docstring of `_get_editor` - Describes how it detects a default editor.
- Lines 156-170: function `_show_example` - Displays the example constitution template using rich markdown rendering.
- Lines 171-178: docstring of `_show_example` - Explains the use case of showing an example constitution file.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_context.py

**Lines:** 850 | **Estimated tokens:** ~8064

- Lines 1-1: global `module_docstring` - CLI commands for user context management.
- Lines 3-5: import-block `uuid` - Imports the uuid module for generating unique identifiers.
- Lines 7-9: import-block `typer` - Imports the typer library for creating command-line interfaces.
- Lines 13-16: import-block `questionary` - Attempts to import the questionary library, used for interactive prompts; defines QUESTIONARY_AVAILABLE based on success.
- Lines 18-20: import-block `knowledge` - Imports the KnowledgeBase class from knowledge.py.
- Lines 22-47: function `_add_feeds_to_config` - Adds feeds to a config file, handling existing entries and creating the file if it doesn't exist; returns count of newly added feeds.
- Lines 49-53: global `app` - Creates a typer.Typer application named "context" with specified help text and invoke behavior.
- Lines 57-102: decorator `@app.callback` `context_main` - Defines the callback function for the CLI application's main entry point; displays help and usage information when no subcommand is provided.
- Lines 58-64: method `ClassName.context_main` - The callback function for the typer app, displaying a welcome message and context management instructions.
- Lines 105-155: decorator `@app.command` `add_context` - Defines the "add" command for adding user contexts; handles validation, creates new UserContext objects, saves them to the knowledge base, and provides feedback.
- Lines 106-154: method `ClassName.add_context` - Implements the add context command, validates input, and adds a new context to the knowledge base.
- Lines 159-213: decorator `@app.command` `list_contexts` - Defines the "list" command for displaying user contexts; filters by type and activity status.
- Lines 160-212: method `ClassName.list_contexts` - Implements the list context command, retrieves and displays contexts based on filtering criteria.
- Lines 218-261: decorator `@app.command` `remove_context` - Defines the "remove" command for deleting user contexts; handles cases where context is not found or cannot be deleted directly.
- Lines 219-260: method `ClassName.remove_context` - Implements the remove context command, removes a context from the knowledge base.
- Lines 264-310: decorator `@app.command` `show_context` - Defines the "show" command for displaying details of a specific user context.
- Lines 265-309: method `ClassName.show_context` - Implements the show context command, displays detailed information about a specified context.
- Lines 313-483: constant `FEED_TAXONOMY` - A nested dictionary representing the RSS feed taxonomy structure for various categories and subjects.
- Lines 385-397: function `_show_selection_summary` - Generates a summary string of selected feeds and topics during wizard navigation.
- Lines 402-481: function `_run_tree_wizard` - Implements the tree navigation wizard for selecting RSS feeds and topics, using questionary prompts.
- Lines 484-735: global `run_setup_wizard_inline` -  Defines a function to run the setup wizard inline; used when called from within report flow.
- Lines 736-798: decorator `@app.command` `setup` - Defines the "setup" command, which runs interactive tree navigation to configure user interests and feeds.
- Lines 737-797: method `ClassName.setup` - Implements the setup wizard, guiding users through a hierarchical selection of topics and RSS feeds.
- Lines 802-824: decorator `@app.command` `watch` - Defines the "watch" command to add a topic to the user's watch list.
- Lines 803-823: method `ClassName.watch` - Adds a specified topic to the user's watch list.
- Lines 827-850: decorator `@app.command` `unwatch` - Defines the "unwatch" command for removing topics from the userâ€™s watch list.
- Lines 828-850: method `ClassName.unwatch` - Removes a specified topic from the user's watch list.
- Lines 850-850: global `app` - Executes the typer application.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_cross_source.py

**Lines:** 381 | **Estimated tokens:** ~3472

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-3: import-block `typer` - Imports the typer library for creating command-line interfaces.
- Lines 4-4: import-block `rich.console` - Imports the Console class from rich for printing formatted output to the console.
- Lines 5-5: import-block `rich.table` - Imports the Table class from rich for displaying data in a table format.
- Lines 6-6: import-block `rich.panel` - Imports the Panel class from rich for creating visually distinct panels.
- Lines 8-8: import-block `ers.jpswi.personal projects.RSSsummarizer.src.storage` - Imports the Storage class from the storage module.
- Lines 9-9: import-block `ers.jpswi.personal projects.RSSsummarizer.src.knowledge` - Imports the KnowledgeBase class from the knowledge module.
- Lines 10-18: import-block `ers.jpswi.personal projects.RSSsummarizer.src.cross_source` - Imports functions and constants related to cross-source analysis.
- Lines 20-23: global `app` - Creates a typer.Typer object for the 'sources' CLI group.
- Lines 24-24: global `console` - Initializes a rich Console object for formatted output.
- Lines 27-27: decorator `@app.command("compare")` - Decorates the compare_sources function to register it as a command under the "compare" subcommand of the 'sources' CLI group.
- Lines 28-50: function `compare_sources` - Compares how different sources cover the same story, or selects stories with multiple sources for comparison. Takes story ID, database path, and knowledge base path as arguments.
- Lines 73-122: global `comparison` - The result of comparing a story across sources. Includes data on framing, emphasis, key claims, common facts, and coverage gaps.
- Lines 125-125: decorator `@app.command("multi")` - Decorates the list_multi_source_stories function to register it as a command under the "multi" subcommand of the 'sources' CLI group.
- Lines 126-170: function `list_multi_source_stories` - Lists stories covered by multiple sources, displaying details in a table format. Takes min_sources and limit as arguments.
- Lines 173-189: decorator `@app.command("balance")` - Decorates the show_balance function to register it as a command under the "balance" subcommand of the 'sources' CLI group.
- Lines 174-202: function `show_balance` - Analyzes and displays the political balance of current feeds, providing insights into feed distribution. Takes feeds file path as an argument.
- Lines 206-219: global `distribution` - A dictionary mapping political leanings to lists of feeds.
- Lines 242-258: decorator `@app.command("suggest")` - Decorates the suggest_sources function to register it as a command under the "suggest" subcommand of the 'sources' CLI group.
- Lines 243-294: function `suggest_sources` - Suggests diverse sources based on category (left, center, right, or all), providing recommendations for feed balance. Takes category and feeds file path as arguments.
- Lines 297-305: decorator `@app.command("add-suggested")` - Decorates the add_suggested_sources function to register it as a command under the "add-suggested" subcommand of the 'sources' CLI group.
- Lines 298-358: function `add_suggested_sources` - Adds suggested diverse sources to feeds, either with or without a dry run mode for previewing changes. Takes category, feeds file path, and dry-run flag as arguments.
- Lines 361-370: decorator `@app.command("list-diverse")` - Decorates the list_diverse_sources function to register it as a command under the "list-diverse" subcommand of the 'sources' CLI group.
- Lines 362-380: function `list_diverse_sources` - Lists all available diverse sources in the database, categorized by political leaning.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_daemon.py

**Lines:** 302 | **Estimated tokens:** ~2487

- Lines 1-2: global `module_docstring` - Module docstring
- Lines 3-12: global `module_docstring` - Module docstring describing the CLI daemon's functionality and pipeline steps
- Lines 14-17: import-block `sys, time, threading, datetime, typing` - Imports standard library modules for system interaction, time management, multithreading, date/time handling, and type hinting.
- Lines 18-19: import-block `ers.utils, typer, rich.console, rich.panel, rich.table` - Imports custom utility functions and third-party libraries for CLI argument parsing, console output formatting, and table display.
- Lines 27-30: constant `app` - Creates a Typer app instance named "daemon" with a description of its functionality.
- Lines 31-32: constant `console` - Initializes a rich Console object with specific terminal settings.
- Lines 34-36: global `_stop_requested, _input_thread` - Declares global variables for graceful shutdown and input thread tracking.
- Lines 38-56: function `_parse_interval` - Parses an interval string (e.g., "5m", "1h") into seconds, handling different suffixes ('s', 'm', 'h', 'd') and returning None if invalid.
- Lines 58-72: function `_input_listener` - Listens for user input on a separate thread to request graceful shutdown of the daemon.
- Lines 74-213: function `_run_pipeline_step` - Executes a specified pipeline step (fetch, LLM processing, embeddings, story matching, connection detection), accumulating statistics and returning them as a dictionary. It depends on multiple modules like storage, RSS feed fetching, KnowledgeBase, EmbeddingService, and LLM providers.
- Lines 174-213: method `_run_pipeline_step` - Runs the pipeline up to a specified step level, performing various tasks such as fetching feeds, processing articles with an LLM, generating embeddings, matching stories, and detecting connections.
- Lines 176-293: function `daemon_main` - The main entry point for the daemon CLI command, handling argument parsing, interval scheduling, pipeline execution, and graceful shutdown. It utilizes typer options to configure intervals, steps, and limits.
- Lines 180-181: constant `every` - Defines a default processing interval of "10m" using a typer option.
- Lines 184-185: constant `step` - Defines the default pipeline step level as 5 (full pipeline) using a typer option.
- Lines 189-190: constant `limit` - Defines a default limit for articles processed per cycle as 0 (unlimited) using a typer option.
- Lines 217-218: global `_stop_requested, _input_thread` - Declares global variables for graceful shutdown and input thread tracking within daemon_main function.
- Lines 225-236: constant `interval_seconds` - Parses the interval string provided as a command line argument into seconds using the helper function `_parse_interval`. Returns None if the interval is invalid.
- Lines 240-241: method `daemon_main` - Provides a formatted description of the CLI daemon.
- Lines 246-253: constant `cycle_count` - Initializes a counter to track the number of cycles completed by the daemon.
- Lines 254-257: method `daemon_main` - Starts a background thread (`_input_thread`) that listens for user input (q, quit, exit) to gracefully shut down the daemon.
- Lines 263-289: method `daemon_main` - Executes the pipeline steps in a loop, displaying progress and error messages.
- Lines 290-291: constant `sleep_until` - Calculates when the next cycle should start based on the configured interval.
- Lines 294-300: global `KeyboardInterrupt` - Handles keyboard interrupts (Ctrl+C) to gracefully terminate the daemon loop and print a message indicating interruption.
- Lines 301-302: constant `cycle_count` - Prints a final message indicating that the daemon has stopped and displaying the number of cycles completed.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_perspectives.py

**Lines:** 248 | **Estimated tokens:** ~2440

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-4: import-block `typing` - Imports the typing module for type hints
- Lines 5-7: import-block `typer` - Imports the typer library for CLI creation
- Lines 8-9: global `console` - Creates a Console object with specific formatting options.
- Lines 12-38: function `add_perspective_commands` - Adds perspective-related commands to the Typer app. Accepts a Typer app instance as an argument.
- Lines 16-17: decorator `@app.command()` - Decorates the 'perspectives' function, registering it as a CLI command.
- Lines 18-30: parameter `story_id`, `categories`, `limit`, `update_clusters`, `db_path` - Defines arguments for the 'perspectives' command with default values and help messages.
- Lines 40-115: function `perspectives` - Implements the "perspectives" CLI command to view synthesized perspectives on stories, taking story ID, categories, limit, update clusters, and database path as input.
- Lines 49-53: import-block `storage` - Imports Storage class from storage module.
- Lines 50-51: import-block `get_best_provider` - Imports get_best_provider function from llm_providers module.
- Lines 52-57: import-block `synthesize_perspectives`, `get_user_perspective_config`, `PERSPECTIVE_CATEGORIES` - Imports functions and constants related to perspective synthesis from the perspectives module.
- Lines 58-59: import-block `add_perspective_methods` - Imports add_perspective_methods function from storage_perspectives module.
- Lines 60-61: import-block `update_story_clusters` - Imports update_story_clusters function from clustering module.
- Lines 63-67: block `if update_clusters:` - Conditional block to update story clusters if the --update flag is provided, printing status messages to console.
- Lines 65-66: method `update_story_clusters` - Calls the update_story_clusters function with the storage object and updates clusters.
- Lines 72-74: block `config = get_user_perspective_config(storage)` - Retrieves user perspective configuration from the database.
- Lines 75-81: block `if categories:` - Processes category input if provided, splitting into a list.
- Lines 80-84: block `if invalid:` - Handles validation of requested categories against available perspectives. Raises typer.Exit(1) if there are invalid categories.
- Lines 86-92: block `if story_id:` - Conditional block to handle the case where a specific story ID is provided, retrieving and displaying its perspective.
- Lines 87-89: method `storage.get_story_cluster` - Retrieves the cluster corresponding to the specified story ID from storage.
- Lines 90-92: block `if not cluster:` - Handles cases when no cluster with given id exists.
- Lines 93-95: method `storage.get_articles_by_cluster` - Retrieves articles for a specific story cluster.
- Lines 96-98: block `if not articles:` - Checks if any articles are present in the specified story cluster.
- Lines 100-121: block `synthesize_perspectives` - Calls synthesize_perspectives function to get perspectives and display them with confidence bars.
- Lines 123-137: block `else:` - Conditional block that runs when a specific story ID is not provided, showing top stories instead.
- Lines 124-125: method `storage.get_story_clusters` - Retrieves the list of story clusters from storage.
- Lines 126-130: block `if not clusters:` - Handles cases where there are no story clusters available.
- Lines 133-134: method `storage.get_articles_by_cluster` - Retrieves articles for a specific story cluster.
- Lines 137-145: block `synthesize_perspectives` - Calls synthesize_perspectives function to get perspectives and display them with confidence bars, limited to the first perspective category.
- Lines 162-164: method `console.print` - Prints a message encouraging configuration of default perspective categories.
- Lines 165-173: function `configure_perspectives` - Defines a CLI command for configuring user perspective preferences.
- Lines 170-173: parameter `db_path` - Specifies the database path as an argument with a default value.
- Lines 174-208: block description of configure_perspectives function - Describes the purpose and usage of the configuration command.
- Lines 186-188: method `add_perspective_methods` - Calls add_perspective_methods to extend storage capabilities.
- Lines 190-203: loop over current configurations - Iterates through existing perspective categories, displaying their status.
- Lines 204-207: Loop over available perspectives - Iterates over the available perspective categories, showing them as unavailable in the configuration.
- Lines 208-221: function `cluster_stories` - Defines a CLI command for clustering articles into story groups.
- Lines 209-214: parameter `force`, `db_path` - Defines parameters for the 'cluster-stories' command with default values and help messages.
- Lines 213-214: decorator `@app.command()` - Decorates the cluster_stories function, registering it as a CLI command.
- Lines 225-228: import-block `Storage`, `update_story_clusters` - Imports Storage class and update_story_clusters from modules.
- Lines 231-232: method `add_perspective_methods` - Calls add_perspective_methods to extend storage capabilities.
- Lines 233-240: block execution of cluster stories command - Executes the clustering process, printing status messages to console.
- Lines 235-236: method `update_story_clusters` - Updates story clusters based on provided parameters.
- Lines 243-248: loop through top story clusters - Iterates over top story clusters and prints information about each cluster.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_schedule.py

**Lines:** 578 | **Estimated tokens:** ~4753

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-7: import-block `platform` - Imports the platform module for OS information.
- Lines 9-13: import-block `typer` - Imports the typer library for creating command-line interfaces.
- Lines 14-18: global `app` - Creates a typer application instance named 'app' with name "schedule" and help text.
- Lines 19-20: global `console` - Creates a rich Console object for printing formatted output.
- Lines 21-23: constant `SCHEDULE_CONFIG` - Defines the path to the schedule configuration file.
- Lines 25-27: function `_get_script_path` - Returns the script execution command line.
- Lines 30-56: function `_parse_interval` - Parses a time interval string (e.g., "3d", "12h") into minutes.
- Lines 58-69: function `_save_schedule_config` - Saves the schedule configuration to a JSON file.
- Lines 74-85: function `_load_schedule_config` - Loads schedule configuration from a JSON file, returns default if not found or error occurs.
- Lines 87-127: function `_create_windows_task` - Creates a scheduled task in Windows Task Scheduler.
- Lines 131-146: function `_delete_windows_task` - Deletes a Windows Task Scheduler task.
- Lines 149-168: function `_get_windows_task_status` - Retrieves status and information about the Windows Task Scheduler task.
- Lines 172-209: function `_create_cron_job` - Creates a cron job for Unix systems.
- Lines 213-234: function `_delete_cron_job` - Deletes a cron job for Unix systems.
- Lines 236-238: decorator `@app.callback` - Decorates the `schedule_main` function as a Typer callback.
- Lines 239-276: function `schedule_main` - Main entry point when no subcommand is provided, displays help information.
- Lines 278-304: function `enable` - Enables scheduled background fetching with a specified interval.
- Lines 306-335: function `disable` - Disables the currently configured background fetch schedule.
- Lines 337-371: function `status` - Displays the current status of the scheduled background tasks.
- Lines 373-402: function `configure` - Interactive wizard to configure the background scheduling settings.
- Lines 453-473: method `typer.Typer.command` - Registers a command with typer CLI, provides help string and parameter definitions.
- Lines 475-569: method `typer.MainApp.prompt` - Prompts the user for input using Typer's prompt function.
- Lines 483-488: method `typer.MainApp.confirm` - Asks the user to confirm an action, returning a boolean value.
- Lines 567-575: method `typer.MainApp.exit` - Exits the typer application with a specified status code.

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_signal_tags.py

**Lines:** 244 | **Estimated tokens:** ~1971

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-4: import-block `typing` - Imports the typing module for type hints
- Lines 5-8: import-block `rich.console` - Imports Console class from rich library
- Lines 9-10: import-block `storage` - Imports Storage class from storage module
- Lines 11-15: global `app` - Creates a Typer CLI application instance for managing signal tags
- Lines 16-17: global `console` - Initializes a Console object with specific formatting options
- Lines 19-29: decorator `tag_main` - Decorates the tag_main function to handle top-level command invocation and help display
- Lines 20-29: function `tag_main` - Manages signal tags for articles; displays interactive help if no subcommand is provided
- Lines 58-77: function `tag_articles_cmd` - Assigns signal tags to articles based on specified limit, LLM usage and database path
- Lines 77-78: method `Storage.get_articles` - Retrieves articles from the storage (database) with a given limit
- Lines 94-95: method `Storage.get_articles` - Retrieves articles from the storage (database) with a given limit
- Lines 107-108: method `Storage.update_signal_tags` - Updates signal tags for an article in the storage
- Lines 113-121: function `tag_stats_cmd` - Displays tag distribution statistics from the specified database file
- Lines 123-124: method `Storage.get_articles` - Retrieves articles from the storage (database) with a given limit
- Lines 126-127: method `Storage.get_articles` - Retrieves articles from the storage (database) with a given limit
- Lines 138-145: function `Counter` - Counts occurrences of tags in tagged articles, used for statistics calculation
- Lines 140-144: method `Counter.most_common` - Returns a list of the n most common elements and their counts from dictionary
- Lines 168-211: function `filter_by_tags` - Filters articles based on included and excluded signal tags, displaying results in a table
- Lines 194-201: method `Storage.get_articles_by_signal_tags` - Retrieves articles filtered by signal tags
- Lines 208-209: method `Storage.get_articles` - Retrieves articles from the storage (database) with a given limit
- Lines 234-237: method `Storage.title` - Gets article title and truncates if too long
- Lines 243-244: global `app()` - Entry point for running the Typer CLI application

---

## ers\jpswi\personal projects\RSSsummarizer\src\cli_stories.py

**Lines:** 324 | **Estimated tokens:** ~2555

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-4: import-block `typing` - Imports the typing module for type hinting
- Lines 5-9: import-block `typer`, `rich.console`, `rich.table`, `rich.panel` - Imports various modules from the rich library and typer
- Lines 10-12: import-block `.storage`, `.knowledge` - Relative imports for storage and knowledge base functionality
- Lines 13-14: global `app`, `console` - Initializes a Typer app and a rich console object
- Lines 17-20: function `get_storage` - Creates and returns an instance of the Storage class with the given database path.
- Lines 23-71: function `backfill_embeddings` - Backfills embeddings for stories that don't have them, using a specified database and knowledge base path. It uses a progress callback during the embedding process.
- Lines 54-59: function `update_progress` - Updates the progress display during a long operation; truncates title to fit console width.
- Lines 60-64: global `backfill_story_embeddings`, `storage`, `kb` - Defines and calls backfill_story_embeddings with storage, knowledgebase, and callback.
- Lines 76-118: function `list_stories` - Lists story clusters with their state and article counts, filtering by lifecycle state and limit.  It also creates a rich table to display the stories.
- Lines 150-259: function `fix_titles` - Regenerates titles for stories with broken or default titles using an LLM provider. Includes dry-run mode and title fixing logic.
- Lines 262-318: function `stats` - Displays statistics about the story clusters including embedding coverage, state breakdown, and warning messages if many are missing embeddings.

---

## ers\jpswi\personal projects\RSSsummarizer\src\clustering.py

**Lines:** 1079 | **Estimated tokens:** ~9825

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-5: import-block `json` - Imports the json module for working with JSON data.
- Lines 8-10: import-block `.llm_providers` - Imports the LLM providers module.
- Lines 15-17: class `ClusteringError` - Custom exception raised when clustering operations fail.
- Lines 20-396: class `StoryClusterer` - Handles Level 1 clustering: grouping articles into stories using vector embeddings.
- Lines 24-396: method `StoryClusterer.__init__` - Initializes the StoryClusterer with LLM provider, storage and optional KnowledgeBase and EmbeddingService.
- Lines 51-93: method `StoryClusterer.find_matching_story` - Finds an existing story that matches the given article using vector similarity.
- Lines 94-120: method `StoryClusterer.find_matching_story_with_embedding` - Find matching story based on a precomputed embedding.
- Lines 123-141: method `StoryClusterer._get_or_create_article_embedding` - Gets or creates an embedding for the given article.
- Lines 144-181: method `StoryClusterer._calculate_similarity` - Calculates the similarity between an article and a story using cosine similarity.
- Lines 183-202: method `StoryClusterer._find_matching_story_keywords` - Fallback method to find matching stories based on keywords.
- Lines 204-247: method `StoryClusterer._generate_comparison_prompt` - Generates a prompt for an LLM to compare an article and story.
- Lines 249-260: method `StoryClusterer._keyword_similarity` - Calculates keyword similarity between an article and a story.
- Lines 251-263: method `StoryClusterer._parse_similarity_response` - Parses the response from an LLM when comparing articles/stories.
- Lines 261-314: method `StoryClusterer.create_new_story` - Creates a new story from an article, extracting metadata.
- Lines 315-342: method `StoryClusterer.update_story_with_article` - Adds an article to an existing story and updates the story's information.
- Lines 343-352: method `StoryClusterer._extract_keywords` - Extracts keywords from an article (REMOVED).
- Lines 353-413: class `NewsItemExtractor` - Handles Level 2: extracting news items within stories.
- Lines 361-378: method `NewsItemExtractor.__init__` - Initializes the NewsItemExtractor with LLM provider, storage, and embedding service.
- Lines 380-406: method `NewsItemExtractor.extract_news_items` - Extracts news items from an article within a story.
- Lines 425-467: method `NewsItemExtractor._generate_extraction_prompt` - Generates prompt for extracting news items from an article.
- Lines 469-501: method `NewsItemExtractor._parse_news_items` - Parses news items from LLM response.
- Lines 503-524: method `NewsItemExtractor.deduplicate_items` - Removes duplicate news items.
- Lines 526-547: method `NewsItemExtractor._items_similar` - Checks if two news items are similar using embedding similarity.
- Lines 548-560: method `NewsItemExtractor._get_embedding` - Gets an embedding for a given text, caching results.
- Lines 563-592: class `StoryEvolutionTracker` - Tracks story lifecycle and state transitions.
- Lines 571-577: method `StoryEvolutionTracker.update_all_stories` - Updates the lifecycle states of all active stories.
- Lines 580-618: method `StoryEvolutionTracker.calculate_velocity` - Calculates article velocity for a story.
- Lines 621-646: method `StoryEvolutionTracker.update_lifecycle_state` - Determines story lifecycle state based on activity.
- Lines 651-673: method `StoryEvolutionTracker.get_evolution_stats` - Gets statistics about story evolution.
- Lines 681-736: function `process_article_clustering` - Processes clustering for a single article, handling spam detection and news extraction.
- Lines 737-770: function `update_story_clusters` - Updates story clusters by processing unclustered articles in batch.
- Lines 782-816: method `backfill_story_embeddings` - Backfills embeddings for stories that don't have them.
- Lines 821-845: function `build_news_extraction_prompt` - Builds a prompt to extract new items from an article.
- Lines 847-906: function `parse_news_extraction_response` - Parses the LLM response for news extraction and saves extracted items.
- Lines 912-1006: function `batch_process_articles` - Processes clustering for multiple articles in a batch, using an LLM gateway.

---


