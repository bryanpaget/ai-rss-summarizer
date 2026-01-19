# Project Documentation

Generated: 2026-01-18 16:52:04

**Stats:** 39 files, 259 functions, 93 classes, ~22831 lines

**Cache:** 462 cached, 13 new, 1 changed

**Timing:** 21.3s total LLM time, 1.52s avg per function

---

## System Overview

## Architecture Overview

**1. Purpose:** This Python project is a comprehensive news and information processing system designed for advanced analysis, including clustering, summarization, knowledge extraction, and trend identification. It aims to provide insights from diverse sources by leveraging LLMs, vector embeddings, and structured data management.

**2. Key Modules:**

*   **`commands.py`**:  This module houses the core command-line interface (CLI) logic, orchestrating various functionalities like updating data, managing contexts, and triggering specific processing tasks. It acts as the primary entry point for user interaction.
*   **`knowledge.py`**: This module is responsible for extracting structured knowledge from news articles, including entities, relationships, and insights.  It leverages LLMs to parse text and build a knowledge graph.
*   **`clustering.py`**: Handles the clustering of news articles based on semantic similarity, enabling the identification of emerging trends and topic evolution. It uses embeddings and clustering algorithms for this purpose.
*    **`llm_providers.py`**:  Manages interactions with various Large Language Models (LLMs) like OpenAI, LMStudio, Ollama, etc., providing a flexible abstraction layer for LLM integration. 
*   **`storage.py`**: Manages the persistence and retrieval of news articles, stories, and associated metadata using a custom storage mechanism.

**3. Entry Points:** The project's execution begins with `cli.py`, which parses command-line arguments and dispatches requests to the appropriate functions within other modules (primarily those defined in `commands.py`).

**4. Data Flow:**  The user initiates a task through the CLI (`cli.py`). This triggers operations that often involve fetching data from various sources (`feed_catalog.py`, `rss.py`), processing articles for knowledge extraction and clustering (`knowledge.py`, `clustering.py`), leveraging LLMs via `llm_providers.py` for summarization, analysis, and prompt generation, and storing/retrieving processed information using the `storage.py` module.  The results of these operations are then presented to the user or used for further analysis.





---

## Timing Summary

| File | Functions | Wall (s) | Tokens |
|------|-----------|----------|--------|
| cli_schedule.py | 4 | 53.5 | 2241 |
| knowledge.py | 2 | 27.7 | 2066 |
| context_commands.py | 1 | 17.0 | 108 |
| llm_providers.py | 1 | 16.9 | 476 |
| commands.py | 1 | 12.9 | 290 |
| cli_context.py | 1 | 12.8 | 139 |
| model_manager.py | 1 | 8.6 | 23 |
| perspectives.py | 1 | 8.6 | 45 |
| report.py | 1 | 8.5 | 869 |
| vector_index.py | 1 | 8.4 | 9 |

---

## File Documentation

### __init__.py

**Lines:** 3

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-3: constant `__version__` - Specifies the software's current version number.

---

### cli.py

**Lines:** 1237

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 4-33: import-block `imports` - Module imports
- Lines 35-39: constant `app` - Creates a Typer application named "rss" for an AI-powered RSS feed summarizer with trend prediction.
- Lines 41-41: constant `console` - Creates a Console object configured for terminal output and legacy Windows compatibility.
- Lines 68-70: function `is_setup_complete` - Checks if the LLM provider configuration file exists to determine if setup is complete.
- Lines 73-77: function `require_setup` - Handles missing setup by displaying an error message and exiting if the required setup is not complete.
- Lines 80-82: function `get_storage` - Creates a Storage instance using the provided database path, defaulting to "articles.db" if none is specified.
- Lines 86-138: function `fetch` - Fetches articles from configured RSS feeds, displaying a table summarizing the results including fetched and new articles per feed.
- Lines 142-189: function `summarize` - Summarizes up to a specified number of articles, optionally using an LLM and assigning signal tags, then reports the number of processed, tagged, and erroneous articles.
- Lines 193-249: function `trends` - Analyzes article trends from a database, displaying top categories, emerging tags, and declining tags with visual bar representations.
- Lines 253-322: function `list_articles` - Retrieves and displays a list of articles from a database, optionally filtering by trend, limiting the number of articles, and including summaries.
- Lines 326-367: function `stats` - Displays database statistics, including the total number of articles and a breakdown of articles by feed with counts and latest article information.
- Lines 371-397: function `add_feed` - Adds a new RSS feed URL to a specified feeds file, creating the file if it doesn't exist and preventing duplicate entries.
- Lines 406-464: function `update` - Fetches and displays the latest articles, optionally filtering by topic, limit, and relevance, and controlling personalization.
- Lines 468-519: function `report` - Generates a comprehensive report analyzing articles, embeddings, clusters, and stories with configurable limits, skipping already-summarized articles, and optionally forcing a setup wizard run.
- Lines 523-536: function `setup` - Configures an LLM provider (LM Studio, Ollama, Claude, or OpenAI) for AI-powered summarization using a setup wizard.
- Lines 540-636: function `discover` - Discovers RSS feeds relevant to a given topic by prompting an LLM to identify and return URLs and descriptions of suitable sources.
- Lines 640-713: function `help_cmd` - Displays help information for the RSS Summarizer, either for a specific command or a comprehensive overview of available commands and setup status.
- Lines 717-738: function `providers` - Lists available LLM providers and their current status (available or not) in a formatted table.
- Lines 742-823: function `extract_knowledge` - Extracts knowledge insights from a specified number of articles, processing each article to detect relationships, extract triples, and identify entity relationships, then updates a knowledge base and displays relevant statistics.
- Lines 827-848: function `query` - Queries a knowledge base using a natural language query and displays the summary of the results.
- Lines 852-880: function `contradictions` - Identifies and displays contradictions within a knowledge base by retrieving and presenting conflicting insights and their associated confidence levels.
- Lines 884-908: function `knowledge_stats` - Retrieves and displays key statistics about a knowledge base, including insights, entities, relationships, and contradictions.
- Lines 912-956: function `graph` - Explores the knowledge graph around a given entity, displaying its outgoing and incoming relationships, and listing connected entities within a specified depth.
- Lines 960-989: function `graph_path` - Finds and prints a path between two entities in a knowledge graph, displaying the path steps and its length.
- Lines 993-1030: function `graph_stats` - Retrieves and displays key statistics about a knowledge graph, including insights, entities, triples, and predicate information.
- Lines 1034-1058: function `context_add` - Adds a new user context (project, interest, or watching) to the knowledge base with a unique ID, name, type, and optional description.
- Lines 1062-1089: function `context_list` - Lists all user contexts from a knowledge base, displaying their type, name, status, and description in a formatted table.
- Lines 1093-1132: function `main` - Documents the commands available for an AI RSS summarizer, including updating feeds, generating summaries, and querying a knowledge base.
- Lines 1140-1237: function `emerging` - Detects and displays emerging trends based on confidence level and a specified limit, retrieving them from a database and presenting them with confidence-level headers.

---

### cli_constitution.py

**Lines:** 171

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-12: import-block `imports` - Module imports
- Lines 20-20: constant `console` - Creates a Console object configured for terminal output and compatibility with legacy Windows systems.
- Lines 23-76: function `add_constitution_commands` - Creates a new constitution file from an example template, prompting the user to customize analysis principles.
- Lines 79-107: function `_view_constitution` - Displays the current analysis constitution, including its path and markdown content, or provides instructions for creating one if none is configured.
- Lines 110-134: function `_edit_constitution` - Opens the constitution file in the default editor, creating a template if the file doesn't exist and handling potential errors during the opening process.
- Lines 137-153: function `_get_editor` - Returns the user's preferred text editor based on environment variables and platform defaults.
- Lines 156-171: function `_show_example` - Displays an example constitution template and instructions on how to use it with the `rss constitution-create` and `rss constitution edit` commands.

---

### cli_context.py

**Lines:** 846

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-19: import-block `imports` - Module imports
- Lines 22-47: function `_add_feeds_to_config` - Adds new feed URLs to a configuration file, avoiding duplicates and returning the number of feeds newly added.
- Lines 49-53: constant `app` - Creates a Typer application named "context" for managing user context commands.
- Lines 54-54: constant `console` - Creates a Console object configured for terminal output and legacy Windows compatibility.
- Lines 58-101: function `context_main` - Presents interactive help and command options for managing user contexts, including project, interest, and watching topics.
- Lines 105-155: function `add_context` - Creates a new user context in the knowledge base with the specified type, name, and optional description.
- Lines 159-214: function `list_contexts` - Lists user contexts, optionally filtered by type and status, from a specified knowledge base and displays them in a table.
- Lines 218-260: function `remove_context` - Removes a specified user context from the knowledge base by deleting its ID or deactivating it if deletion is unavailable.
- Lines 264-309: function `show_context` - Displays detailed information about a specific context from the knowledge base, including its type, status, description, and keywords.
- Lines 314-483: constant `FEED_TAXONOMY` - Organizes news sources by category and subcategory, providing URLs for each.
- Lines 486-489: constant `SETUP_CATEGORIES` - Creates a dictionary mapping categories to lists of subjects based on the FEED_TAXONOMY data.
- Lines 492-499: function `_show_selection_summary` - Returns a comma-separated string summarizing the number of selected feeds and topics, or "nothing selected" if no items are chosen.
- Lines 502-510: function `_show_cli_help` - Displays helpful command reminders for interacting with the RSS context feature.
- Lines 513-681: function `_run_tree_wizard` - Parses the tree taxonomy, allowing users to navigate categories, subjects, and feeds to select desired items.
- Lines 684-734: function `run_setup_wizard_inline` - Runs an interactive setup wizard to allow users to select topics and feeds, then updates the user's profile and configuration accordingly.
- Lines 738-798: function `setup_wizard` - Configures user interests and RSS feed subscriptions through an interactive wizard, allowing navigation and selection of categories, subjects, and feeds.
- Lines 802-821: function `watch_topic` - Adds a specified topic to the user's watch list by loading the profile, checking if the topic is already being watched, and saving the updated profile.
- Lines 825-846: function `unwatch_topic` - Removes a specified topic from the user's watch list by updating the profile and displaying confirmation.

---

### cli_cross_source.py

**Lines:** 381

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-10: import-block `imports` - Module imports
- Lines 20-23: constant `app` - Creates a Typer application named "sources" for cross-source comparison and diverse source management.
- Lines 24-24: constant `console` - Creates a Console object configured for terminal output and legacy Windows compatibility.
- Lines 28-122: function `compare_sources` - Compares coverage of a story across multiple sources, highlighting perspectives, framing, key claims, common facts, and coverage gaps.
- Lines 126-168: function `list_multi_source_stories` - Retrieves and displays a table of stories covered by a specified minimum number of news sources, up to a limit, using a provided database.
- Lines 172-238: function `show_balance` - Analyzes subscribed feeds to display their political distribution across left, center, and right categories, providing a balance assessment.
- Lines 242-293: function `suggest_sources` - Suggests diverse sources from specified categories to balance a user's feed mix, displaying them with their leaning and URLs.
- Lines 297-357: function `add_suggested_sources` - Adds suggested diverse sources to the specified category in the feeds file, or previews the changes if dry-run is enabled.
- Lines 361-381: function `list_diverse_sources` - Lists pre-curated news sources categorized by political leaning, displaying their names, leanings, and URLs.

---

### cli_daemon.py

**Lines:** 302

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 14-25: import-block `imports` - Module imports
- Lines 27-30: constant `app` - Creates a Typer application named "daemon" to run continuous processing in the foreground.
- Lines 31-31: constant `console` - Creates a Console object configured to force terminal output and support legacy Windows compatibility.
- Lines 34-34: constant `_stop_requested` - Handles a flag indicating whether the program should stop execution.
- Lines 38-55: function `_parse_interval` - Parses interval strings (e.g., '5m', '1h') into seconds, handling optional suffixes for minutes, hours, and days, and returns None for invalid input.
- Lines 58-71: function `_input_listener` - Handles user input for quitting the program by listening for commands like 'q', 'quit', 'exit', or 'stop' in a background thread.
- Lines 74-172: function `_run_pipeline_step` - Runs pipeline steps up to a specified level, fetching data, processing with an LLM, generating embeddings, matching stories, and detecting connections.
- Lines 176-302: function `daemon_main` - Runs a continuous processing pipeline at a specified interval, with configurable step levels and a maximum number of articles per cycle.

---

### cli_perspectives.py

**Lines:** 248

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-6: import-block `imports` - Module imports
- Lines 9-9: constant `console` - Creates a Console object configured for terminal output and legacy Windows compatibility.
- Lines 12-248: function `add_perspective_commands` - Displays synthesized perspectives on stories, allowing users to specify story IDs, categories, and the number of stories to show.

---

### cli_schedule.py

**Lines:** 578

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-12: import-block `imports` - Module imports
- Lines 14-18: constant `app` - Creates a Typer application named "schedule" for background fetch scheduling commands.
- Lines 19-19: constant `console` - Creates a Console object configured for terminal output and compatibility with legacy Windows systems.
- Lines 22-22: constant `SCHEDULE_CONFIG` - Defines the path to the schedule configuration file, used for storing and retrieving scheduling parameters.
- Lines 25-27: function `_get_script_path` - Returns a string representing the command to execute the `fetch` script using the current Python interpreter.
- Lines 30-56: function `_parse_interval` - Parses an interval string (e.g., '3d', '12h', '30m') into minutes, returning None if the input is invalid.
- Lines 59-71: function `_save_schedule_config` - Saves the schedule configuration to a JSON file, including whether the schedule is enabled and the specified interval in minutes.
- Lines 74-85: function `_load_schedule_config` - Loads schedule configuration from a JSON file, defaulting to a disabled state with a zero-minute interval if the file doesn't exist or loading fails.
- Lines 88-127: function `_create_windows_task` - Creates a Windows Task Scheduler task to run a script at a specified interval, handling schedule type and overwriting existing tasks.
- Lines 130-145: function `_delete_windows_task` - Deletes a Windows Task Scheduler task with the specified name and returns True if successful, otherwise indicates failure with the error message.
- Lines 148-168: function `_get_windows_task_status` - Retrieves the status of a specified Windows Task Scheduler task by querying the task and parsing its output into a dictionary.
- Lines 171-210: function `_create_cron_job` - Creates a cron job for a specified interval and working directory by updating the system's crontab file.
- Lines 213-235: function `_delete_cron_job` - Handles the deletion of cron jobs by reading the current crontab, removing specified entries, and updating the crontab file.
- Lines 239-274: function `schedule_main` - Handles background feed fetching schedule management through interactive commands like enable, disable, and status.
- Lines 278-332: function `enable` - Enables scheduled background fetching by setting up an OS scheduler to run the 'rss fetch' command at the specified interval.
- Lines 336-360: function `disable` - Disables scheduled background fetching by removing the task from the operating system scheduler and updating the schedule configuration.
- Lines 364-447: function `status` - Displays the current status of background fetching, including whether it's enabled, the next scheduled run time, and the configured interval.
- Lines 451-578: function `configure` - Configures background scheduling by prompting the user for an interval and confirming the setup.

---

### cli_signal_tags.py

**Lines:** 240

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-9: import-block `imports` - Module imports
- Lines 11-15: constant `app` - Creates a Typer application named "tag" for managing signal tags.
- Lines 16-16: constant `console` - Creates a Console object configured for terminal output and compatibility with legacy Windows systems.
- Lines 20-55: function `tag_main` - Displays interactive help for managing signal tags, including available commands and examples.
- Lines 59-110: function `tag_articles_cmd` - Tags a specified number of articles using either an LLM or rule-based methods, updating the database with the assigned signal tags.
- Lines 114-165: function `tag_stats_cmd` - Analyzes tagged articles from a database to display statistics on the most frequent tags, including total articles, tagged articles, and a table of the top 15 tags with their counts and percentages.
- Lines 169-240: function `filter_by_tags` - Filters articles based on specified inclusion and exclusion tags, limiting the results to a maximum number and displaying them in a formatted table.

---

### cli_stories.py

**Lines:** 324

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-11: import-block `imports` - Module imports
- Lines 13-13: constant `app` - Creates a Typer application object for managing story-related commands.
- Lines 14-14: constant `console` - Creates a Console object configured for terminal output and legacy Windows compatibility.
- Lines 17-19: function `get_storage` - Creates a Storage instance using the provided database path, defaulting to "articles.db" if none is specified.
- Lines 23-73: function `backfill_embeddings` - Embeds stories missing embeddings from a database to enable accurate duplicate detection.
- Lines 77-146: function `list_stories` - Displays story clusters with their titles, lifecycle states, article counts, and last updated times, optionally filtered by limit and state.
- Lines 150-258: function `fix_titles` - Fixes story titles by regenerating them using an LLM for stories containing common phrases indicating poor titles, up to a specified limit.
- Lines 262-324: function `stats` - Analyzes story statistics, including the number of stories with and without embeddings, and counts stories by their lifecycle state.

---

### clustering.py

**Lines:** 1079

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-12: import-block `imports` - Module imports
- Lines 15-17: class `ClusteringError` - Handles errors that occur during clustering operations.
- Lines 20-347: class `StoryClusterer` - Clusters an article into an existing story or creates a new story based on vector similarity using embeddings and optionally leveraging an LLM for metadata generation.
- Lines 355-559: class `NewsItemExtractor` - Extracts new information from an article by generating a prompt, parsing the LLM response, deduplicating items, and saving new findings to storage.
- Lines 562-672: class `StoryEvolutionTracker` - Tracks story lifecycle by updating states based on activity, calculating velocity, and determining the next state transition.
- Lines 675-732: function `process_article_clustering` - Processes an article by clustering it into a story, optionally extracting news items, and returns a dictionary of processing statistics.
- Lines 735-817: function `update_story_clusters` - Updates story clusters by processing unclustered articles from the last `lookback_hours` hours using a language model provider.
- Lines 820-884: function `backfill_story_embeddings` - Backfills story embeddings for stories missing them by embedding the stories and saving the results, returning statistics on the process.
- Lines 891-924: function `build_news_extraction_prompt` - Creates a prompt for extracting new information from an article by incorporating existing news items and specifying the desired JSON output format.
- Lines 927-978: function `parse_news_extraction_response` - Parses a JSON response for news items, extracts relevant information, and saves high-confidence items to storage.
- Lines 987-1079: function `batch_process_articles` - Processes a list of articles by clustering them and optionally extracting news items using an LLM provider, returning a dictionary of batch processing statistics.

---

### commands.py

**Lines:** 1557

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-21: import-block `imports` - Module imports
- Lines 42-42: constant `console` - Creates a Console object configured for terminal output and compatibility with legacy Windows systems.
- Lines 45-408: function `update` - Processes new articles from configured feeds by summarizing, tagging, extracting knowledge, and generating insights, then updates a database with the results and statistics.
- Lines 411-492: function `_display_full_digest` - Displays a comprehensive digest of stories, perspectives, and emerging trends, including article summaries, signal tags, consensus/contested perspectives, relevance scores, and knowledge base statistics.
- Lines 495-526: function `_matches_topic_keywords` - Checks if an article's content or trend tags match the provided topic keyword, returning True if a match is found.
- Lines 529-592: function `_display_digest` - Displays a formatted digest of articles, including title, publication date, summary, tags, and link, with optional filtering by topic, relevance scores, and provider information.
- Lines 595-698: function `setup_wizard` - Parses and displays a list of available LLM providers, indicating their status and providing options for setup or selection.
- Lines 701-728: function `_save_provider_config` - Saves the configuration for a given provider to a JSON file, ensuring specific settings for LM Studio and informing the user of the save location.
- Lines 731-839: function `_setup_lm_studio_config` - Configures LM Studio for safe auto-loading of a specified model, checking for availability and resource requirements before creating an LLMConfig object.
- Lines 842-870: function `_onboard_feeds` - Guides the user through the process of setting up initial RSS feeds, either by modifying existing ones or starting fresh.
- Lines 873-894: function `_setup_feeds` - Handles user input to select a method for adding RSS feeds, including importing from OPML, adding URLs, pasting multiple URLs, or browsing curated feeds.
- Lines 897-966: function `_import_opml` - Handles OPML files by parsing feeds, categorizing them, and optionally validating and adding them to a feeds.txt file.
- Lines 969-1030: function `_add_feed_smart` - Handles user input (URL, domain, or platform URL) to validate and discover feeds, then adds the feed to a configuration file if the user confirms.
- Lines 1033-1077: function `_paste_multiple_urls` - Validates a list of URLs, attempts to create feed entries from them, and appends successful entries to a feeds.txt file while reporting validation results.
- Lines 1080-1095: function `_browse_curated_feeds` - Presents a menu for browsing curated feeds by category or searching for feeds based on user input.
- Lines 1098-1135: function `_show_curated_categories` - Displays a table of curated feed categories with their corresponding feed counts, allowing the user to select a category and view its feeds.
- Lines 1138-1198: function `_show_category_feeds` - Validates and adds selected feeds from a list to a configuration file, displaying a table of available feeds and prompting the user for selection.
- Lines 1201-1230: function `_parse_selection` - Parses a comma-separated selection string, including ranges like "1-5", into a sorted list of integer indices within the specified maximum number of items.
- Lines 1233-1297: function `_search_feeds` - Searches for feeds online based on user input and allows the user to select and add them to a configuration file.
- Lines 1304-1310: function `_finish_onboarding` - Displays a completion message indicating setup is complete and the next step is to update RSS feeds.
- Lines 1313-1431: function `_setup_new_provider` - Configures a new language model provider by prompting the user for an API key and saving the configuration to a file.
- Lines 1434-1473: function `_show_local_setup_instructions` - Informs the user about setting up local LLM providers, including instructions for LM Studio and Ollama, and explains how the application automatically loads and unloads models.
- Lines 1476-1505: function `_select_provider` - Handles user selection of a provider from a list, configuring the chosen provider if available or prompting setup if not.
- Lines 1508-1557: function `get_digest_summary` - Generates a text summary of recent articles, optionally filtered by topic and time range.

---

### constitution.py

**Lines:** 109

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 7-9: import-block `imports` - Module imports
- Lines 12-12: constant `DEFAULT_CONSTITUTION_PATH` - Specifies the default path to the constitution configuration file.
- Lines 14-36: constant `EXAMPLE_CONSTITUTION` - Captures a multi-line string containing analysis principles, source evaluation guidelines, focus areas, and red flags to watch for.
- Lines 39-41: function `get_constitution_path` - Returns the path to the default constitution file.
- Lines 44-46: function `constitution_exists` - Checks if the constitution file exists by verifying the path returned by get_constitution_path().
- Lines 49-65: function `get_constitution_content` - Retrieves and returns the constitution content as a string, or None if the file is not found or is empty.
- Lines 68-86: function `get_constitution_context` - Formats the user's constitution into a context string to guide LLM prompts, returning an empty string if no constitution is available.
- Lines 89-104: function `create_constitution` - Creates a constitution file at a specified path, using provided content or a default template if none is given.
- Lines 107-109: function `get_example_constitution` - Returns a string containing the example constitution template.

---

### content_filter.py

**Lines:** 300

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 11-16: import-block `imports` - Module imports
- Lines 20-25: class `FilterResult` - Creates a structured result containing information about content filtering, including whether the content is promotional, the confidence level of the filter, the reason for the result, and the matched patterns.
- Lines 29-79: constant `TITLE_PATTERNS` - Identifies promotional patterns in text to determine the discount or offer type, assigning a relevance score based on the pattern.
- Lines 82-97: constant `PROMOTIONAL_DOMAINS` - Identifies a list of promotional domains commonly used for coupon and deal websites.
- Lines 100-109: constant `CONTENT_PATTERNS` - Identifies patterns in text related to coupon codes, discounts, and calls to action, assigning a relevance score to each.
- Lines 112-172: function `is_promotional_content` - Detects whether an article is promotional content based on title, link, and content patterns, returning a confidence score and reasons for the classification.
- Lines 175-180: function `add_spam_support` - Handles legacy spam column addition, but does nothing as schema is now managed by Storage schema migrations.
- Lines 183-205: function `flag_as_spam` - Flags an article as spam by updating its status, reason, and timestamp in the database.
- Lines 208-244: function `get_spam_articles` - Retrieves a specified number of articles flagged as spam from the storage, ordered by the most recent spam flagging time.
- Lines 247-268: function `cleanup_old_spam` - Deletes spam articles from storage that are older than a specified number of days.
- Lines 271-300: function `filter_articles` - Filters a list of articles into clean and spam categories based on a promotional content detection threshold.

---

### context_commands.py

**Lines:** 273

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-7: import-block `imports` - Module imports
- Lines 10-10: constant `console` - Creates a Console object configured for terminal output and compatibility with legacy Windows systems.
- Lines 13-57: function `context_init` - Initializes a personal context profile by prompting the user for their role, projects, topics to watch/ignore, and then saving the profile to a store.
- Lines 60-99: function `context_show` - Displays the user's personal context, including role, current projects, watched topics, pinned topics, ignored topics, personalization strength, and last updated timestamp.
- Lines 102-138: function `context_edit` - Handles interactive editing of a user's personal context, allowing modification of role, projects, watching, and ignore lists before saving the updated profile.
- Lines 141-153: function `context_pin` - Pins a given topic to a user's profile to prevent its relevance from decaying, printing a message indicating whether the topic was successfully pinned or was already pinned.
- Lines 156-168: function `context_unpin` - Unpins a specified topic from a user's profile, allowing for relevance decay and providing console feedback.
- Lines 171-183: function `context_watch` - Adds a given topic to the user's watching list, updating the profile and providing feedback on the action.
- Lines 186-198: function `context_ignore` - Adds a specified topic to the user's ignore list, updating the profile and providing feedback to the console.
- Lines 201-231: function `context_stats` - Displays the top 15 topics with the highest engagement rates over the last 30 days in a formatted table.
- Lines 234-244: function `context_export` - Exports all personal context data to a specified file in JSON format.
- Lines 247-257: function `context_import` - Imports personal context data from a JSON file and stores it in the UserContextStore.
- Lines 260-273: function `context_clear` - Clears all personal context data, confirming with the user before proceeding and informing them of the number of records deleted.

---

### cross_source.py

**Lines:** 402

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 7-13: import-block `imports` - Module imports
- Lines 17-24: class `SourcePerspective` - Creates a representation of a news article from a specific source, including its name, domain, content, key claims, framing, and emphasized aspects.
- Lines 28-35: class `CrossSourceComparison` - Analyzes multiple source perspectives on a story to identify common facts, divergent claims, coverage gaps, and potential bias indicators.
- Lines 38-48: function `extract_domain` - Extracts the domain name from a URL string, removing the "www." prefix if present, and returns the original URL if parsing fails.
- Lines 51-90: function `get_source_name` - Returns a human-readable source name for a given domain, using a predefined dictionary and falling back to a title-cased version of the domain if no match is found.
- Lines 94-124: constant `SOURCE_LEANINGS` - Returns a dictionary mapping news source domains to their political leanings, with values ranging from far-right to far-left.
- Lines 127-129: function `get_source_leaning` - Returns the political leaning of a given domain from a predefined dictionary, defaulting to "unknown" if the domain is not found.
- Lines 132-170: function `get_stories_with_multiple_sources` - Finds stories covered by at least a specified number of unique sources, sorted by source count, and returns up to a specified limit.
- Lines 173-273: function `compare_story_coverage` - Compares how different sources cover a given story by extracting claims, analyzing framing and emphasis, identifying common facts and coverage gaps, and determining bias indicators.
- Lines 276-312: function `format_comparison` - Formats a CrossSourceComparison object into a human-readable string containing story details, source perspectives, common ground, and coverage gaps.
- Lines 320-342: constant `DIVERSE_FEEDS` - Creates a dictionary mapping political affiliations ("left", "center", "right") to lists of RSS feed URLs, publication names, and associated political labels.
- Lines 345-368: function `get_current_feed_leanings` - Analyzes the political leaning of feeds from a specified file and returns a dictionary categorizing each feed URL as left, center, right, or unknown.
- Lines 371-402: function `suggest_diverse_sources` - Suggests diverse feed sources by category, prioritizing underrepresented categories and ensuring at least one suggestion from each category.

---

### embedding_providers.py

**Lines:** 467

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 13-16: import-block `imports` - Module imports
- Lines 19-21: class `EmbeddingProviderError` - Handles errors that occur when an embedding provider is unavailable.
- Lines 24-26: class `NoProviderAvailableError` - Defines a custom exception to signal that an embedding provider is unavailable.
- Lines 30-34: class `ProviderConfig` - Creates a configuration object for an embedding provider, specifying the API endpoint URL, model name, and request timeout.
- Lines 37-85: class `EmbeddingProvider` - Creates an abstract base class for embedding providers, defining methods to check availability and generate embeddings for single texts or batches of texts.
- Lines 88-287: class `LMStudioProvider` - Handles embedding requests by communicating with an LM Studio API, managing model loading and batch processing for efficient performance.
- Lines 290-396: class `OllamaProvider` - Handles generating embeddings for given text using Ollama's API, checking for Ollama's availability and handling potential connection or error issues.
- Lines 399-467: class `EmbeddingProviderManager` - Manages embedding providers, automatically selecting one from a list based on availability and a preferred provider.

---

### embeddings.py

**Lines:** 519

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 9-21: import-block `imports` - Module imports
- Lines 25-29: class `EmbeddingResult` - Creates a data structure to store the vector output, model name, and dimensionality of an embedding operation.
- Lines 32-34: class `EmbeddingError` - Handles errors that occur during embedding operations by raising a custom exception.
- Lines 37-475: class `EmbeddingService` - Generates embeddings for text, handling long texts by chunking and averaging to preserve information, and provides options for generating individual chunk embeddings as well.
- Lines 478-497: function `embed_and_store_article` - Embeds an article using an embedding service and stores the resulting embedding in a knowledge base.
- Lines 500-519: function `embed_and_store_story` - Embeds a story using an embedding service and stores the resulting embedding in a knowledge base.

---

### emergence.py

**Lines:** 433

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-9: import-block `imports` - Module imports
- Lines 13-24: constant `EMERGENCE_CONFIG` - Defines configuration parameters for identifying emerging trends, including thresholds for mentions, velocity changes, and comparison windows.
- Lines 28-40: class `EmergingTrend` - Represents an emerging trend with attributes like mentions, velocity, confidence, and related domains to provide insights into its current state and potential trajectory.
- Lines 43-109: function `extract_terms` - Extracts potential emerging terms from text by identifying capitalized multi-word phrases, technical terminology patterns, and acronyms with expansions, then filters the results based on length and stopword exclusion.
- Lines 112-126: function `calculate_velocity` - Calculates the percentage change in a quantity between two counts, handling division by zero by returning 100% if the previous count is zero and the current count is positive, or 0% if both are zero.
- Lines 129-175: function `classify_trajectory` - Classifies a term's trajectory based on historical counts and domains, categorizing it as Research → Blogs → Mainstream, Technical → Business adoption, or Niche → Widespread.
- Lines 178-201: function `assign_confidence` - Assigns a confidence level ("High", "Medium", "Low", or "Watch") to an emerging trend prediction based on velocity, current mentions, domain count, and weeks of data.
- Lines 204-220: function `generate_action_recommendation` - Returns an actionable recommendation based on the provided confidence level, velocity, and trajectory.
- Lines 223-377: function `detect_emerging_trends` - Detects emerging trends by analyzing term mentions in recent articles, considering historical data, velocity, and confidence levels to identify promising topics.
- Lines 380-433: function `format_emerging_trend` - Formats an emerging trend into a human-readable string containing information about its mentions, velocity, trajectory, domains, and recent articles.

---

### feed_catalog.py

**Lines:** 124

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 9-99: constant `CURATED_CATEGORIES` - Organizes news sources into categories like Technology, Programming, and Business, each containing a list of websites with their titles, URLs, and descriptions.
- Lines 102-104: function `get_feeds_by_category` - Returns a list of feed dictionaries for the specified category from a predefined category mapping.
- Lines 107-109: function `get_all_categories` - Returns a list of all available categories from the CURATED_CATEGORIES dictionary.
- Lines 112-124: function `search_curated_feeds` - Returns a list of curated feeds that match the given query in their title, description, or category.

---

### feed_discovery.py

**Lines:** 364

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-8: import-block `imports` - Module imports
- Lines 12-30: class `FeedInfo` - Returns a formatted string containing a preview of the feed's title, description, item count, and recent items, up to a specified maximum number.
- Lines 33-89: function `validate_feed` - Validates a feed URL by fetching, parsing, and extracting information such as title, description, and latest items, returning success status and feed details or an error message.
- Lines 92-148: function `discover_feed` - Discovers an RSS feed URL for a given domain by checking common feed paths and HTML links, returning success, feed information, and any error message.
- Lines 151-171: function `_extract_feed_from_html` - Extracts an RSS/Atom feed URL from an HTML string by searching for link tags with the appropriate rel and type attributes, handling relative URLs by prepending the base URL.
- Lines 174-217: function `transform_url` - Transforms URLs from YouTube channels, Reddit subreddits, and Substack into their corresponding RSS feed URLs.
- Lines 220-260: function `parse_opml` - Parses an OPML file, extracting feed information (title, URL, and category) from the XML structure.
- Lines 263-299: function `detect_input_type` - Detects the type of input provided (OPML, single URL, multiple URLs, domain, platform URL, or unknown) based on its content and format.
- Lines 302-364: function `search_feeds_online` - Retrieves and validates RSS feed information from the Feedsearch.dev API based on a provided search query and timeout duration.

---

### gateway.py

**Lines:** 556

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 13-21: import-block `imports` - Module imports
- Lines 23-23: constant `logger` - Creates a logger with a name derived from the current module, used for recording log messages.
- Lines 26-28: class `GatewayError` - Handles errors that occur during gateway operations by raising a custom exception.
- Lines 31-33: class `GatewayUnavailableError` - Defines a custom exception, GatewayUnavailableError, to signal that the gateway script is not accessible.
- Lines 37-41: class `GatewayResponse` - Creates a response object containing the content, request type, and response path from a gateway request.
- Lines 44-544: class `LocalLLMGateway` - Handles all local LLM requests by loading the appropriate model, managing queues, and preventing concurrent requests to the same model.
- Lines 551-556: function `get_gateway` - Creates and returns a LocalLLMGateway singleton, ensuring it exists before use.

---

### graph_cleanup.py

**Lines:** 305

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 10-15: import-block `imports` - Module imports
- Lines 17-17: constant `logger` - Creates a logger with a name derived from the current module, enabling structured logging of messages.
- Lines 21-28: class `DuplicateCandidate` - Handles a pair of entities or triples by storing their canonical forms, similarity scores, and counts to determine potential duplication.
- Lines 32-37: class `CleanupResult` - Creates a result object containing the number of candidates found, duplicates merged, triples updated, and any errors encountered during a cleanup operation.
- Lines 40-155: function `find_duplicate_entities` - Finds semantically similar entities within a knowledge base using embeddings and FAISS, returning a list of potential duplicate entity pairs with their similarity scores and counts.
- Lines 158-200: function `merge_entity` - Merges a duplicate entity in a knowledge base to the canonical form by updating triples referencing the duplicate, and returns the number of updated triples.
- Lines 203-256: function `run_cleanup` - Identifies and optionally merges duplicate entities in a knowledge base based on similarity scores and a specified threshold.
- Lines 259-305: function `get_cleanup_report` - Generates a report detailing potential duplicate entities within a knowledge base, based on similarity scores and a specified threshold, limiting the report to a defined number of candidates.

---

### knowledge.py

**Lines:** 2986

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 7-18: import-block `imports` - Module imports
- Lines 23-23: constant `logger` - Creates a logger instance with a name derived from the current module.
- Lines 27-36: class `Insight` - Creates a representation of a knowledge insight extracted from an article, including its ID, source article, content, type, confidence level, and extraction timestamp.
- Lines 40-47: class `Entity` - Creates a representation of an entity with attributes like ID, name, type, first appearance, and mention count.
- Lines 51-59: class `Relationship` - Represents a relationship between two insights, storing details like their IDs, type, and strength.
- Lines 63-80: class `Triple` - Creates a representation of an RDF-style triple, storing the subject, predicate, and object along with their types, source, confidence, and extraction timestamp.
- Lines 84-97: class `EntityRelationship` - Handles direct relationships between entities, capturing actions like acquisitions or partnerships with associated properties and timestamps.
- Lines 101-113: class `Embedding` - Creates a vector embedding with associated metadata for semantic search of insights, entities, or articles.
- Lines 117-126: class `UserContext` - Creates a user context object to store information about a user's projects, interests, and other relevant details.
- Lines 129-1122: class `KnowledgeBase` - Contains 36 methods: __init__; _init_db; _connect; save_insight; get_insight
- Lines 1126-1147: class `ConsolidatedExtractionResult` - Creates a consolidated extraction result containing insights, triples, a summary, a headline, and keywords derived from a single LLM call.
- Lines 1150-1324: function `extract_all_from_article` - Extracts insights and triples from an article using a single LLM call by consolidating previous extraction steps into a unified prompt.
- Lines 1327-1468: function `extract_insights_from_article` - Extracts insights from an article using a language model, parsing the article content to generate structured data including insights, types, confidence levels, and related entities.
- Lines 1475-1510: function `build_insight_prompt` - Constructs a prompt for extracting key insights from an article, specifying the desired JSON output format and analysis guidelines.
- Lines 1513-1590: function `parse_insight_response` - Parses a JSON response from an LLM, extracts insights, and saves them along with associated entities to a knowledge base.
- Lines 1594-1606: class `TripleExtractionResult` - Creates a result object containing lists of new, existing, and updated triples extracted from a knowledge base.
- Lines 1609-1666: function `_correct_inverted_predicate` - Corrects inverted "_by" predicates by swapping the subject and object when the subject appears to be a person acting on a company or product.
- Lines 1669-1728: function `_semantic_chunk` - Parses article text using an LLM to identify and return semantically coherent chunks for embedding.
- Lines 1731-1771: function `_find_similar_triple` - Finds a matching triple in the knowledge base, prioritizing exact matches and then case-insensitive pattern matches to avoid duplicates.
- Lines 1774-1798: function `extract_triples_from_article` - Extracts new RDF-style triples from an article by chunking, using an LLM, and comparing them against a knowledge base to identify novel information.
- Lines 1801-1934: function `extract_triples_with_comparison` - Extracts and categorizes triples from an article by prompting an LLM, checking for existing facts in a knowledge base, and saving new ones.
- Lines 1937-2039: function `extract_entity_relationships_from_article` - Extracts entity relationships from an article by prompting an LLM, parsing the JSON response, and saving the relationships to a knowledge base.
- Lines 2042-2063: function `build_chunk_prompt` - Creates a prompt for semantic chunking of an article, instructing the model to divide the content into coherent chunks and return them as a JSON array.
- Lines 2066-2082: function `parse_chunk_response` - Parses an LLM response string to extract a list of text chunks enclosed in square brackets, falling back to the article's content if parsing fails.
- Lines 2085-2129: function `get_connection_candidates` - Retrieves candidate insights for connection detection by finding similar insights in the knowledge base using FAISS, filtering out self-matches and limiting the results to the top 10.
- Lines 2132-2155: function `build_connection_prompt` - Generates a prompt for classifying relationships between insight pairs, including details about each pair and instructions for the classification task.
- Lines 2158-2199: function `parse_connection_response` - Parses an LLM response to extract relationship types and saves the identified relationships with their strength to a knowledge base.
- Lines 2202-2234: function `build_triple_prompt` - Creates a prompt for extracting subject-predicate-object triples from a given text chunk, specifying constraints on entity types and output format.
- Lines 2237-2307: function `parse_triple_response` - Parses a JSON string containing triples from an LLM response and saves new triples to a knowledge base while identifying existing ones.
- Lines 2310-2336: function `build_entity_rel_prompt` - Creates a prompt for entity relationship extraction, instructing the model to identify relationships between organizations, people, and products within a given article.
- Lines 2339-2398: function `parse_entity_rel_response` - Parses a JSON string containing entity relationships from an article and saves them to the knowledge base.
- Lines 2401-2541: function `detect_connections` - Detects relationships between a new insight and existing knowledge by finding similar insights using FAISS and then classifying the relationships using an LLM.
- Lines 2544-2567: function `format_relationship` - Formats a relationship into a human-readable string including the relationship type, target insight content, and similarity score.
- Lines 2570-2625: function `query_knowledge_base` - Queries a knowledge base using a natural language query and an LLM to generate a summary of relevant insights.
- Lines 2633-2647: class `CombinedExtractionOutput` - Handles the combined extraction process, returning a structured output containing insights, new and existing triples, signal tags, a summary, headline, keywords, and an indication of whether the content is advertising.
- Lines 2650-2820: function `extract_all_from_article` - Extracts comprehensive information from an article using a single LLM call, parsing the JSON response to yield insights, triples, signal tags, and other metadata.
- Lines 2823-2888: function `build_extraction_prompt` - Builds a prompt string for extracting information from an article, including instructions for chunking, insight extraction, triple identification, and structured JSON output.
- Lines 2891-2986: function `process_extraction_response` - Processes an LLM response string by parsing it with schema validation, extracting insights and triples, and saving them to a knowledge base.

---

### llm_providers.py

**Lines:** 1593

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-11: import-block `imports` - Module imports
- Lines 14-29: class `ProviderType` - Defines a set of string constants representing different language model providers, each associated with a specific API or local implementation.
- Lines 33-91: class `LLMConfig` - Creates an LLMConfig object by loading configuration from environment variables or a JSON file, allowing specification of provider, base URL, API key, model, and default settings.
- Lines 95-106: class `UsageStats` - Creates a UsageStats object to store token counts and model/provider information from a summarization call, calculating total tokens if not already provided.
- Lines 109-162: class `LLMProvider` - Handles LLM summarization and generation requests, tracking usage statistics and providing a default implementation for generating responses from prompts.
- Lines 165-332: class `OpenAICompatibleProvider` - Generates text summaries or completions using an OpenAI-compatible API, handling model discovery and API interaction.
- Lines 335-575: class `LMStudioProvider` - Handles auto-loading of a local LLM model using LM Studio, checking for resource availability and ensuring the model is loaded before making requests.
- Lines 578-586: class `OllamaProvider` - Creates an Ollama local LLM provider using an OpenAI-compatible endpoint, defaulting to the "llama2" model.
- Lines 589-635: class `TransformersProvider` - Handles text summarization using a Hugging Face transformer model, loading the model pipeline if it's not already loaded.
- Lines 638-712: function `get_provider` - Returns an LLMProvider object based on the provided configuration, environment variables, config file, or auto-detection, raising a ValueError if no provider is available.
- Lines 715-787: function `list_providers` - Returns a list of dictionaries, each describing an available language model provider with its type, name, and availability status.
- Lines 790-866: class `ClaudeProvider` - Handles summarization of text using the Anthropic Claude model, ensuring the API key is available and recording usage statistics.
- Lines 869-937: class `ClaudeCodeProvider` - Generates a summary of a given text using the Claude Code CLI, ensuring the CLI is available and handling potential errors during the process.
- Lines 940-1039: class `ClaudeAgentSDKProvider` - Generates summaries and responses using the Claude Agent SDK, leveraging existing Claude CLI authentication for direct interaction without API keys.
- Lines 1042-1114: class `GeminiProvider` - Handles text summarization using the Google Gemini API, ensuring availability and recording usage statistics.
- Lines 1119-1178: class `GeminiCLIProvider` - Generates a summary of the input text using the Gemini CLI, ensuring the CLI is available and handling potential errors during the summarization process.
- Lines 1181-1251: class `CodexCLIProvider` - Generates a summary of a given text using the OpenAI Codex CLI, ensuring the CLI is installed and handling potential errors during execution.
- Lines 1254-1273: class `GrokProvider` - Creates a Grok API provider using an OpenAI-compatible interface, requiring an XAI or GROK API key to access the xAI Grok API.
- Lines 1276-1297: class `GroqProvider` - Creates a Groq API provider using an OpenAI-compatible API format, requiring a GROQ API key and allowing specification of the model.
- Lines 1300-1370: class `OpenAIAgentsProvider` - Handles text summarization using the OpenAI Agents SDK, allowing for customization of summary length and tracking of API usage.
- Lines 1372-1433: function `auto_detect_provider` - Detects the best available LLM provider based on local availability and API key configuration, prioritizing free options like LM Studio and Ollama.
- Lines 1436-1447: function `get_best_provider` - Returns the best available LLM provider and a boolean indicating if a real LLM was detected, or (None, False) if no provider is found.
- Lines 1450-1491: function `get_setup_instructions` - Returns setup instructions for various LLM providers, including local and cloud options with installation and configuration details.
- Lines 1494-1573: function `validate_llm_ready` - Validates an LLM provider's availability and readiness, returning the provider, readiness status, and an error message if necessary.
- Lines 1576-1593: function `ensure_llm_or_exit` - Handles LLM availability by validating a provider and exiting if one is not ready, prompting the user to configure it.

---

### model_manager.py

**Lines:** 451

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 9-16: import-block `imports` - Module imports
- Lines 19-21: class `ModelManagerError` - Handles errors that occur during model management operations.
- Lines 24-26: class `LMStudioNotReachableError` - Handles the error condition when the LM Studio server is unreachable, indicating a failure to connect for model management.
- Lines 29-31: class `ModelLoadError` - Handles errors that occur when attempting to load a machine learning model.
- Lines 34-36: class `ModelUnloadError` - Handles errors that occur when attempting to unload a model from the model manager.
- Lines 40-104: class `ModelConfig` - Loads model configuration from a project-local JSON file, falling back to creating a default configuration if the file doesn't exist.
- Lines 107-107: constant `RequestType` - Defines a string literal representing the allowed types of requests: text, vision, or embedding.
- Lines 110-412: class `ModelManager` - Manages LM Studio model loading and unloading, ensuring the correct model is loaded based on the configured request type.
- Lines 419-424: function `get_model_manager` - Returns the singleton instance of the ModelManager, creating it if it doesn't already exist.
- Lines 427-433: function `ensure_embedding_model` - Loads the embedding model and returns its path.
- Lines 436-442: function `ensure_text_model` - Loads the text model and returns its path.
- Lines 445-451: function `ensure_vision_model` - Loads the vision model and returns its path.

---

### perspectives.py

**Lines:** 737

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-8: import-block `imports` - Module imports
- Lines 12-97: constant `PERSPECTIVE_CATEGORIES` - Defines a dictionary mapping perspective categories to their names and minimum source requirements.
- Lines 100-100: constant `DEFAULT_CATEGORIES` - Defines a list of predefined categories used for classifying data.
- Lines 104-110: class `Perspective` - Creates a structured representation of a story's perspective, including its category, content, source articles, confidence level, and generation timestamp.
- Lines 113-115: class `PerspectiveError` - Defines a custom exception to handle errors that occur during perspective synthesis.
- Lines 118-120: class `InsufficientSourcesError` - Defines a custom exception to signal when insufficient articles are available to generate a perspective.
- Lines 123-125: class `CategoryNotApplicableError` - Defines a custom exception, CategoryNotApplicableError, to signal when a requested category is not applicable to a given story.
- Lines 128-130: class `LLMProviderError` - Handles errors that occur when an LLM provider fails to generate a perspective.
- Lines 133-349: function `build_perspective_prompt` - Builds an LLM prompt tailored to a specific perspective category by formatting a list of articles with category-specific instructions.
- Lines 352-424: function `estimate_confidence` - Estimates the confidence in a synthesized perspective based on article count, recency, synthesis quality, and category-specific requirements, returning a score between 0 and 1.
- Lines 427-460: function `generate_fallback_perspective` - Generates a fallback perspective with basic text extraction and aggregation from a list of articles, providing a message indicating the number of sources available.
- Lines 463-542: function `synthesize_perspective` - Generates a perspective for a story cluster by synthesizing articles using an LLM if available, falling back to a rule-based approach if not.
- Lines 545-670: function `synthesize_perspectives` - Generates perspectives for a story cluster by leveraging LLMs, prioritizing batched processing via a gateway if available and using sequential processing otherwise.
- Lines 673-688: function `is_cache_fresh` - Checks if a cached perspective is still within its time-to-live (TTL) by comparing the age of the cached data to the specified TTL in hours.
- Lines 691-708: function `get_user_perspective_config` - Retrieves the user's perspective configuration from storage, returning default values if no configuration is found.
- Lines 711-737: function `update_user_perspective_config` - Updates a user's perspective configuration in storage by applying provided settings for enabled categories, default categories, and category order.

---

### report.py

**Lines:** 2061

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 15-44: import-block `imports` - Module imports
- Lines 46-46: constant `console` - Creates a Console object configured for terminal output and legacy Windows compatibility.
- Lines 53-70: function `_cosine_similarity` - Computes the cosine similarity between two vectors by calculating their dot product and dividing by the product of their magnitudes, handling vectors of different lengths by padding the shorter one.
- Lines 73-153: class `BatchProgress` - Handles batch processing by dividing items into batches, tracking time, and predicting the estimated time remaining.
- Lines 160-160: constant `_cleanup_registered` - Handles whether to perform cleanup operations on registered resources.
- Lines 163-171: function `_cleanup_gateway` - Clears the gateway's queue and unloads models to free VRAM during program exit, attempting cleanup even if errors occur.
- Lines 174-178: function `_signal_handler` - Handles interrupt signals by cleaning up resources and exiting the program with a specific exit code.
- Lines 181-195: function `_register_cleanup` - Registers cleanup handlers, including an atexit handler and signal handlers for SIGINT and SIGTERM, ensuring they are executed upon program termination.
- Lines 202-208: function `_make_progress_bar` - Creates a text-based progress bar string, displaying the completion percentage with filled '#' characters and a corresponding bar of '-' characters.
- Lines 211-390: function `_run_verification_step` - Analyzes the corpus state, identifying gaps in summaries, trends, signals, and embeddings for existing articles and stories/insights, while also tracking new articles fetched during the current session.
- Lines 397-537: function `_run_pre_embedding_phase` - Embeds existing stories and insights using an embedding service, initializing category embeddings and handling batch processing with limit control.
- Lines 544-764: function `_run_llm_phase` - Processes articles in batches using pipelining to generate summaries, insights, facts, and tags, while handling errors and updating storage with the results.
- Lines 771-806: function `_create_semantic_card` - Creates a structured text card for embedding by combining the article's title, summary, trend categories, and signal type information.
- Lines 809-943: function `_run_embedding_phase` - Embeds new articles and stories using semantic cards, saving embeddings and chunk data to storage and updating trend tags as needed.
- Lines 950-1015: function `_cluster_insights_by_similarity` - Clusters insights based on embedding similarity using a greedy approach, grouping similar insights above a specified threshold.
- Lines 1018-1057: function `build_cluster_analysis_prompt` - Generates a prompt for a language model to analyze a cluster of insights and extract structured knowledge in JSON format.
- Lines 1060-1170: function `parse_cluster_analysis_response` - Parses a cluster analysis response, extracts information about themes, subcategories, and relationships, and saves the extracted data as triples and relationships to a knowledge base.
- Lines 1173-1201: function `_analyze_cluster_for_triples` - Analyzes a cluster of insights using a language model to extract theme/relationship triples and saves them to a knowledge base.
- Lines 1204-1374: function `_run_connection_detection` - Detects connections between new insights by embedding them, clustering them based on similarity, and then analyzing each cluster using a text model to extract relationships.
- Lines 1381-1477: function `_run_story_matching` - Matches articles to existing stories using semantic embeddings and creates new stories from articles that don't have a match.
- Lines 1484-1703: function `generate_report` - Generates a comprehensive report by fetching, analyzing, and embedding articles, incorporating self-healing mechanisms and optional setup wizard guidance.
- Lines 1706-1955: function `_show_final_report` - Generates an intelligence briefing with sections on top priorities, user interests, discovered connections, knowledge graph updates, and session statistics.
- Lines 1958-2034: function `_score_articles_for_briefing` - Scores articles based on signal strength, user interests, novelty, and cross-referencing to prioritize them for a briefing.
- Lines 2037-2051: function `_explain_relevance` - Generates a personalized relevance explanation for an article based on the user's tracked topics and current projects.
- Lines 2054-2061: function `_article_matches_topic` - Checks if an article's title, trend tags, or content contains a specified topic (case-insensitive).

---

### rss.py

**Lines:** 127

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-11: import-block `imports` - Module imports
- Lines 14-26: function `load_feeds` - Loads a list of feed URLs from the specified file, skipping empty lines and comments.
- Lines 29-31: function `generate_article_id` - Generates a 16-character SHA256 hash from a given link to create a unique article ID.
- Lines 34-52: function `parse_published_date` - Handles published and updated date information from a feed entry, converting timestamped date objects to datetime objects and logging errors if parsing fails.
- Lines 55-66: function `get_entry_content` - Extracts the best available content from a feed entry, prioritizing the 'content' field, then the 'summary' field, and finally the 'title' field.
- Lines 69-106: function `fetch_feed` - Fetches and parses an RSS feed from a given URL, returning statistics about the operation including the number of fetched articles, new articles saved, and any errors encountered.
- Lines 109-127: function `fetch_all_feeds` - Fetches feed data from a specified file and returns a list of dictionaries containing statistics for each feed.

---

### schema.py

**Lines:** 303

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 7-11: import-block `imports` - Module imports
- Lines 18-21: class `ExtractedEntity` - Creates a structured representation of an entity mentioned in an insight, including its name and type.
- Lines 24-30: class `ExtractedInsight` - Creates a structured representation of an extracted insight from an article, including its content, type, confidence level, reason, and associated entities.
- Lines 33-35: class `InsightExtractionResult` - Creates a structured result containing extracted insights from an article.
- Lines 42-49: class `ExtractedTriple` - Creates a structured representation of an RDF-style triple from text, including subject, predicate, and object, along with their types and confidence level.
- Lines 52-54: class `TripleExtractionResult` - Creates a data structure to hold the extracted subject-predicate-object triples from an article chunk.
- Lines 61-66: class `ExtractedEntityRelationship` - Creates a relationship between two entities, specifying the source, target, and type of relationship, along with optional properties.
- Lines 69-71: class `EntityRelationshipResult` - Creates a data structure to hold the extracted relationships between entities.
- Lines 78-82: class `SignalTag` - Creates a signal tag with a tag, confidence level, and optional reason for an article.
- Lines 85-88: class `SignalTagResult` - Creates a SignalTagResult object containing extracted tags and an indicator of whether the article is an advertisement.
- Lines 95-99: class `SemanticChunk` - Creates a semantic chunk of an article containing text, insights, and triples.
- Lines 102-114: class `CombinedExtractionResult` - Creates a structured result containing semantic chunks, signal tags, and extracted information like headline, summary, and keywords from a single article.
- Lines 121-177: function `extract_json_from_response` - Extracts JSON from a string, prioritizing JSON within markdown code blocks and attempting to isolate JSON arrays or objects directly.
- Lines 180-203: function `parse_json_response` - Parses a JSON string from an LLM response, attempting direct parsing and fallback extraction from markdown/commentary before raising a ValueError if parsing fails.
- Lines 206-231: function `parse_insights` - Parses a JSON response containing insights into a list of validated `ExtractedInsight` objects, handling both array and nested object formats.
- Lines 234-258: function `parse_triples` - Parses a JSON response containing triples into a list of validated `ExtractedTriple` objects.
- Lines 261-284: function `parse_signal_tags` - Parses an LLM response, validating and extracting signal tags from either a list of tags or a dictionary containing tag information.
- Lines 287-303: function `parse_combined_extraction` - Parses a raw LLM response string into a validated CombinedExtractionResult object, handling potential parsing errors.

---

### signal_tagger.py

**Lines:** 641

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-9: import-block `imports` - Module imports
- Lines 13-19: constant `SATIRE_DOMAINS` - Defines a list of domains often associated with satirical or politically charged content.
- Lines 23-90: class `SignalTags` - Handles signal tags for an article by providing methods to serialize to JSON, deserialize from JSON, format for display, create a compact string, and check for the presence of specific tags.
- Lines 93-600: class `SignalTagger` - Assigns signal tags to an article by employing either rule-based pattern matching or a language model, considering source type, evidence handling, reasoning quality, tone, and actionability.
- Lines 603-641: function `tag_articles_batch` - Tags a batch of articles using a provided tagger, returning a dictionary mapping article IDs to their associated signal tags.

---

### storage.py

**Lines:** 1091

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-10: import-block `imports` - Module imports
- Lines 13-13: constant `SCHEMA_VERSION` - Defines the version of the data schema used for data serialization and deserialization.
- Lines 17-30: class `ArticleChunk` - Creates a class to store semantic chunks of an article, including their ID, article ID, index, text, and embedding for fine-grained matching.
- Lines 34-49: class `Article` - Creates a representation of an RSS article with attributes for its ID, feed URL, title, link, publication date, content, and optional summary, headline, keywords, and tags.
- Lines 53-65: class `Story` - Creates a Story object to represent a collection of articles related to a specific topic, including its metadata and associated article IDs.
- Lines 69-81: class `NewsItem` - Creates a news item object containing details such as ID, title, description, and associated metadata.
- Lines 84-1091: class `Storage` - Contains 48 methods: __init__; _init_db; _run_migrations; _migrate_to_v1; _migrate_to_v2

---

### storage_perspectives.py

**Lines:** 213

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-7: import-block `imports` - Module imports
- Lines 10-183: class `PerspectiveStorage` - Handles perspective synthesis by retrieving, creating, caching, and invalidating perspectives for story clusters.
- Lines 187-213: function `add_perspective_methods` - Adds perspective-related methods to a Storage instance by attaching methods from a PerspectiveStorage object.

---

### story_commands.py

**Lines:** 235

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-12: import-block `imports` - Module imports
- Lines 14-14: constant `console` - Creates a Console object configured for terminal output and legacy Windows compatibility.
- Lines 17-62: function `cluster_command` - Clusters articles into stories and extracts news items from a specified number of unclustered articles using a chosen provider.
- Lines 65-122: function `stories_command` - Displays a table of stories, including their titles, lifecycle states, article and news item counts, and last updated timestamps, up to a specified limit.
- Lines 125-190: function `story_detail_command` - Displays detailed information about a specific story, including its title, description, state, keywords, articles, and news items, up to a limit of 10 items for each category.
- Lines 193-235: function `evolution_command` - Displays story lifecycle statistics, including state distribution and summary metrics like total stories and average articles per story.

---

### summarizer.py

**Lines:** 164

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-3: import-block `imports` - Module imports
- Lines 6-11: class `SummarizerBackend` - Generates a summary of the input text, limiting the summary length to a specified maximum.
- Lines 14-54: class `SimpleSummarizer` - Extracts the first few sentences from a text string, up to a specified maximum length, to create a concise summary.
- Lines 57-97: class `TransformerSummarizer` - Generates a summary of a given text using a pre-trained transformer model, handling potential errors during model loading and applying truncation for context length limitations.
- Lines 100-109: function `get_summarizer` - Returns a summarizer backend, either a TransformerSummarizer using a language model or a SimpleSummarizer, based on the `use_llm` parameter.
- Lines 112-164: function `summarize_articles` - Summarizes a limited number of unsummarized articles from storage, optionally using an LLM and assigning signal tags, then returns statistics on the process including processed articles, tagged articles, and errors.

---

### trends.py

**Lines:** 391

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 11-19: import-block `imports` - Module imports
- Lines 21-21: constant `logger` - Creates a logger with a name derived from the current module, used for recording log messages.
- Lines 26-36: constant `TREND_CATEGORY_DESCRIPTIONS` - Returns a dictionary mapping trend categories to associated keywords for improved topic identification.
- Lines 39-39: constant `CATEGORY_SIMILARITY_THRESHOLD` - Defines a similarity threshold of 0.45 for categorizing items as similar.
- Lines 46-92: function `ensure_categories_initialized` - Initializes category embeddings in FAISS by retrieving existing embeddings or creating new ones from category descriptions, ensuring the embedding service is available.
- Lines 95-119: function `_get_category_embeddings` - Retrieves category embeddings from a cache, fetching them from an embedding service if they don't already exist.
- Lines 122-150: function `categorize_by_stored_embedding` - Categorizes an article based on pre-computed category embeddings by finding categories with a cosine similarity above a threshold and returning their names in order of similarity.
- Lines 153-181: function `categorize_text` - Handles text categorization by embedding the input text and using a categorization service, issuing a deprecation warning due to its reliance on generating new embeddings.
- Lines 184-225: function `analyze_article` - Analyzes an article by retrieving its stored embedding from storage, comparing it to category embeddings, and returning a comma-separated list of predicted categories.
- Lines 228-350: function `analyze_trends` - Analyzes article trends within a specified time window, calculating category counts, velocity, and identifying top and emerging trends.
- Lines 353-368: function `get_articles_by_trend` - Retrieves articles from storage that belong to a specified trend category, limiting the results to a maximum of 20 articles.
- Lines 371-391: function `llm_categorize` - Categorizes an article into one of several predefined categories using a language model, prioritizing the first matching category and returning "Uncategorized" if no match is found or an error occurs.

---

### user_context.py

**Lines:** 683

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-11: import-block `imports` - Module imports
- Lines 16-16: constant `logger` - Creates a logger with a name derived from the current module, used for recording log messages.
- Lines 20-73: class `UserContextProfile` - Creates a user profile containing their role, interests, settings, and timestamps, and provides methods to convert it to and from a dictionary.
- Lines 77-92: class `ArticleInteraction` - Records user interactions with an article, including whether the article was expanded, the time spent, if it was saved or shared, and any feedback provided.
- Lines 95-353: class `UserContextStore` - Manages user interaction history by storing and retrieving data about articles viewed, time spent, and engagement actions.
- Lines 356-613: class `RelevanceEngine` - Calculates a relevance score for an article based on topic match, historical engagement, recency, and diversity, considering user preferences and personalization strength.
- Lines 616-646: function `sort_by_relevance` - Sorts a list of articles by their relevance to a user profile, using a relevance engine that can leverage semantic embeddings or fall back to substring matching.
- Lines 649-683: function `apply_diversity_filter` - Applies a diversity filter to a list of articles by interleaving highly relevant and diverse articles based on a specified diversity factor.

---

### utils.py

**Lines:** 46

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 4-46: function `format_duration` - Formats a given number of seconds into a human-readable duration string, representing days, hours, minutes, and seconds as appropriate.

---

### vector_index.py

**Lines:** 291

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 7-15: import-block `imports` - Module imports
- Lines 17-17: constant `logger` - Creates a logger with a name derived from the current module, enabling structured logging for debugging and monitoring.
- Lines 21-24: class `SearchResult` - Creates a search result object containing the target ID and a similarity score representing the cosine similarity between the target and the search query.
- Lines 27-259: class `VectorIndex` - Handles FAISS vector indexing by storing separate indices for different target types and providing methods to add, search, and check for the existence of vectors.
- Lines 264-264: constant `_index_lock` - Handles synchronization to protect shared resources from concurrent access during interval parsing.
- Lines 267-282: function `get_vector_index` - Creates a global VectorIndex instance with the specified embedding dimensions, ensuring thread-safe access.
- Lines 285-291: function `reset_vector_index` - Resets the global vector index to None, clearing any existing data for testing purposes.

---

