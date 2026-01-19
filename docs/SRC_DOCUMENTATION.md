# Project Documentation

Generated: 2026-01-18 23:04:42

**Stats:** 56 files, 609 functions, 94 classes, ~24797 lines

**Cache:** 0 cached, 721 new, 0 changed

**Timing:** 987.3s LLM time

---

## System Overview

## Architecture Overview

**1. Purpose:** This project is a command-line tool designed for managing and analyzing news content, with a focus on clustering stories, creating constitutions (sets of rules), and providing various data processing utilities. It aims to help users organize, understand, and extract insights from large volumes of news articles.

**2. Key Modules:**

*   **`cli.py`**:  The core command-line interface, handling argument parsing, configuration loading, and orchestrating other modules to perform user-requested actions like fetching, summarizing, and managing contexts.
*   **`clustering.py`**: Contains the logic for clustering news stories based on similarity, including embedding generation, story extraction, and cluster management.  It also defines classes related to the clustering process.
*   **`commands.py`**: Provides a set of command functions that implement specific functionalities like updating data, displaying digests, and matching articles to keywords. It acts as a central hub for various operations.
*    **`cli_context.py`**: Manages contexts within the application, allowing users to organize stories based on different criteria.

**3. Entry Points:** Execution begins with `cli.py`.  It parses command-line arguments and calls appropriate functions from other modules (e.g., `commands.py`, `clustering.py`) to execute the requested task.

**4. Languages/Stack:** Python 3.x. The codebase leverages standard Python libraries for file I/O, argument parsing, and potentially external libraries for data processing (though specifics are not explicitly evident from the provided files).  It relies heavily on command-line interaction.





---

## File Documentation

### TEST_10FILES.md

**Lines:** 516

- Lines 1-516: markdown_file `TEST_10FILES.md` - Handles user commands for fetching, summarizing, and analyzing RSS feeds through a command-line interface.

---

### TEST_5FILES.md

**Lines:** 312

- Lines 1-312: markdown_file `TEST_5FILES.md` - Handles user-defined contexts for organizing and filtering RSS feeds.

---

### TEST_CLI_PERSPECTIVES.md

**Lines:** 109

- Lines 1-109: markdown_file `TEST_CLI_PERSPECTIVES.md` - Handles command-line interaction for viewing and configuring story perspectives by leveraging embedding models from LM Studio.

---

### TEST_CLI_PERSPECTIVES2.md

**Lines:** 158

- Lines 1-158: markdown_file `TEST_CLI_PERSPECTIVES2.md` - Handles persistent storage of articles, stories, and related data using a database.

---

### TEST_CROSS_A.md

**Lines:** 55

- Lines 1-55: markdown_file `TEST_CROSS_A.md` - Compares story coverage across multiple sources, retrieving stories from the database and printing common facts, coverage gaps, and a separator for each.

---

### TEST_CROSS_A2.md

**Lines:** 35

- Lines 1-35: markdown_file `TEST_CROSS_A2.md` - Compares how different RSS feeds cover the same stories, enabling analysis of story coverage across multiple sources.

---

### TEST_CROSS_B.md

**Lines:** 46

- Lines 1-46: markdown_file `TEST_CROSS_B.md` - Compares how different RSS feeds cover the same stories by retrieving stories with multiple sources from a database and presenting a detailed analysis.

---

### TEST_CROSS_D.md

**Lines:** 35

- Lines 1-35: markdown_file `TEST_CROSS_D.md` - Compares news coverage across multiple sources to reveal differing perspectives, framing, and emphasized facts.

---

### TEST_DOC.md

**Lines:** 140

- Lines 1-140: markdown_file `TEST_DOC.md` - Fetches RSS feeds, parses their content, generates summaries, and stores them for retrieval by a user interface.

---

### TEST_FUNC_APPROACH.md

**Lines:** 13

- Lines 1-13: markdown_file `TEST_FUNC_APPROACH.md` - Compares story coverage across multiple sources, retrieving the story and comparing its coverage using a dedicated function before presenting formatted results.

---

### TEST_TOOL2.md

**Lines:** 65

- Lines 1-65: markdown_file `TEST_TOOL2.md` - Views synthesized perspectives on stories, allowing specification of story ID, categories, a display limit, cluster updates, and database path.

---

### TEST_UTILS_AUDIT.md

**Lines:** 75

- Lines 1-75: markdown_file `TEST_UTILS_AUDIT.md` - Formats a duration in seconds into a human-readable string (e.g., "5 minutes") using predefined formatting rules.

---

### TEST_UTILS_AUDIT2.md

**Lines:** 78

- Lines 1-78: markdown_file `TEST_UTILS_AUDIT2.md` - Formats duration values in seconds into human-readable strings like "10s" or "2m30s", handling negative inputs by returning "0s".

---

### TEST_UTILS_AUDIT3.md

**Lines:** 71

- Lines 1-71: markdown_file `TEST_UTILS_AUDIT3.md` - Formats a given number of seconds into a human-readable duration string, handling various time units from seconds to days.

---

### TEST_UTILS_AUDIT4.md

**Lines:** 77

- Lines 1-77: markdown_file `TEST_UTILS_AUDIT4.md` - Formats a given number of seconds into human-readable duration strings (e.g., "2 days, 3 hours, 15 minutes").

---

### TEST_UTILS_AUDIT5.md

**Lines:** 102

- Lines 1-102: markdown_file `TEST_UTILS_AUDIT5.md` - Generates concise summaries of RSS feed items by extracting key information and potentially employing abstractive summarization techniques.

---

### TEST_UTILS_AUDIT6.md

**Lines:** 78

- Lines 1-78: markdown_file `TEST_UTILS_AUDIT6.md` - Formats time durations in seconds into human-readable strings, using predefined units for clarity.

---

### __init__.py

**Lines:** 4

- Lines 1-4: file `__init__.py` - Handles RSS feed URLs, fetching content and extracting key information for summarization.

---

### cli.py

**Lines:** 1237

- Lines 68-70: function `is_setup_complete` - Validates the existence of the LLM configuration file at "config/llm.json".
- Lines 73-77: function `require_setup` - Validates if the system setup is complete and exits with an error message if not.
- Lines 80-82: function `get_storage` - Handles database path to instantiate a Storage object.
- Lines 86-138: function `fetch` - Fetches articles from configured RSS feeds, displaying results including fetched count, new articles, and status.
- Lines 142-189: function `summarize` - Summarizes up to a specified number of articles, optionally using an LLM and assigning signal tags, and reports the number of processed, tagged, and erroneous articles.
- Lines 193-249: function `trends` - Analyzes trends across a specified number of articles from a database, displaying top categories and highlighting emerging or declining tags.
- Lines 253-322: function `list_articles` - Lists articles fetched from a database, optionally filtering by trend, displaying summaries, and controlling the number of articles shown.
- Lines 326-367: function `stats` - Calculates and displays database statistics, including total articles and a detailed breakdown of articles by feed with counts and latest article information.
- Lines 371-397: function `add_feed` - Adds an RSS feed URL to a specified feeds file, creating the file if it doesn't exist and preventing duplicate entries.
- Lines 406-464: function `update` - Handles fetching and displaying the latest articles, optionally filtering by topic, limit, and relevance.
- Lines 468-519: function `report` - Generates a comprehensive report with live progress, processing articles, generating summaries, and extracting knowledge.
- Lines 523-536: function `setup` - Configures an LLM provider (LM Studio, Ollama, Claude, OpenAI) to enable AI-powered RSS summarization.
- Lines 540-636: function `discover` - Discoveres RSS feeds relevant to a user's specified topics using an LLM and displays the results in a formatted panel.
- Lines 640-713: function `help_cmd` - Displays help information for the RSS Summarizer, including usage examples and available commands categorized by functionality.
- Lines 717-738: function `providers` - Lists available LLM providers and their current status (available or not), along with a brief description.
- Lines 742-823: function `extract_knowledge` - Extracts knowledge insights from a specified number of articles, processing each article to identify and extract insights, detect relationships between them, and extract knowledge graph triples and entity relationships.
- Lines 827-848: function `query` - Queries the knowledge base using a natural language query and returns a summary of the findings.
- Lines 852-880: function `contradictions` - Identifies and displays contradictions within the knowledge base by retrieving conflicting relationships and presenting the associated insights with their confidence levels.
- Lines 884-908: function `knowledge_stats` - Retrieves and displays key statistics about the knowledge base, including insight counts, confidence levels, entities, relationships, and contradictions.
- Lines 912-956: function `graph` - Explores the knowledge graph around a given entity, displaying outgoing and incoming relationships up to a specified depth.
- Lines 960-989: function `graph_path` - Finds a path between two entities in a knowledge graph, printing the path and its length if a path exists.
- Lines 993-1030: function `graph_stats` - Calculates and displays key statistics about a knowledge graph, including insights, entities, triples, relationships, predicates, and embeddings.
- Lines 1034-1058: function `context_add` - Adds a new user context (project, interest, watching) to the knowledge base with specified type, name, and optional description.
- Lines 1062-1089: function `context_list` - Lists available user contexts, displaying their type, name, status, and description in a formatted table.
- Lines 1093-1132: function `main` - Summarizes articles from RSS feeds using AI, providing concise overviews of current events and trending topics.
- Lines 1140-1237: function `emerging` - Detects emerging trends by filtering articles based on confidence level and limiting the number of trends displayed.

---

### cli_constitution.py

**Lines:** 171

- Lines 23-76: function `add_constitution_commands` - Creates a new constitution file from the example template, allowing users to start with a set of default analysis principles.
- Lines 27-50: function `constitution` - Handles requests to view, edit, or display an example of the analysis constitution.
- Lines 53-76: function `constitution_create` - Creates a new constitution file at the default path, prompting the user to edit it for their specific analysis principles.
- Lines 79-107: function `_view_constitution` - Displays the current analysis constitution, including its path and content rendered as markdown, or provides instructions for creating or viewing example constitutions if none are configured.
- Lines 110-134: function `_edit_constitution` - Opens the constitution file in the default editor, creating a template if the file doesn't exist.
- Lines 137-153: function `_get_editor` - Handles user's preferred text editor from environment variables, defaulting to notepad on Windows, TextEdit on macOS, and nano on Linux.
- Lines 156-171: function `_show_example` - Displays an example constitution template with instructions for creating and customizing a new constitution.

---

### cli_context.py

**Lines:** 846

- Lines 22-47: function `_add_feeds_to_config` - Adds new feed URLs to the configuration file, returning the number of feeds successfully added.
- Lines 58-101: function `context_main` - Handles user context management, allowing users to add, list, remove, and view contexts for personalized article relevance.
- Lines 105-155: function `add_context` - Creates a new user context with the specified type, name, and description, saving it to the knowledge base.
- Lines 159-214: function `list_contexts` - Lists user contexts, filtering by type and activity status, and displays them in a table format.
- Lines 218-260: function `remove_context` - Removes a user context from the knowledge base by finding the matching context name and either deleting it or deactivating it if deletion is unavailable.
- Lines 264-309: function `show_context` - Displays detailed information about a specified context, including its type, status, description, creation date, and keywords.
- Lines 492-499: function `_show_selection_summary` - Returns a concise summary of selected feeds and topics, indicating the number of each if any are selected, otherwise stating "nothing selected".
- Lines 502-510: function `_show_cli_help` - Displays quick command reminders for managing RSS contexts and feeds.
- Lines 513-681: function `_run_tree_wizard` - Selects feeds and topics from a hierarchical taxonomy, returning the selected items as lists.
- Lines 684-734: function `run_setup_wizard_inline` - Runs the setup wizard inline, adding selected topics and feeds to the user's profile and configuration.
- Lines 738-798: function `setup_wizard` - Configures user interests and RSS feed subscriptions through an interactive tree-based wizard.
- Lines 802-821: function `watch_topic` - Handles adding a specified topic to the user's watch list, preventing duplicates and updating the profile.
- Lines 825-846: function `unwatch_topic` - Removes a specified topic from the user's watch list, saving the updated profile and confirming the action.

---

### cli_cross_source.py

**Lines:** 381

- Lines 28-122: function `compare_sources` - Compares how different sources cover the same story, highlighting perspectives, framing, emphasized facts, and common/missing information.
- Lines 126-168: function `list_multi_source_stories` - Retrieves stories covered by a specified minimum number of unique sources, up to a limit, from a database.
- Lines 172-238: function `show_balance` - Analyzes subscribed feeds to display their political spectrum distribution as a table with counts and percentages for each category.
- Lines 242-293: function `suggest_sources` - Suggests diverse sources based on the specified category to balance feed mix.
- Lines 297-357: function `add_suggested_sources` - Adds recommended diverse sources to the specified categories in your RSS feeds, with an option for a dry run to preview changes.
- Lines 361-381: function `list_diverse_sources` - Lists diverse sources categorized by political leaning, displaying their names, leanings, and URLs.

---

### cli_daemon.py

**Lines:** 302

- Lines 38-55: function `_parse_interval` - Parses interval strings like '5m' or '1h' into seconds, returning None for invalid formats.
- Lines 58-71: function `_input_listener` - Handles user input from the console, terminating the listener thread upon receiving 'q', 'quit', 'exit', or 'stop'.
- Lines 74-172: function `_run_pipeline_step` - Handles pipeline execution up to a specified step level, performing fetching, LLM processing, embedding, story matching, and connection detection.
- Lines 176-302: function `daemon_main` - Parses the provided interval string into seconds, returning None if the input is invalid.

---

### cli_perspectives.py

**Lines:** 248

- Lines 12-248: function `add_perspective_commands` - View synthesized perspectives on stories by combining multiple sources, optionally specifying categories and limiting the number of stories displayed.
- Lines 16-163: function `perspectives` - Displays synthesized perspectives on stories, allowing filtering by categories and specifying a limit for the number of stories to show.
- Lines 166-206: function `configure_perspectives` - Configures default perspective categories for stories by displaying current settings and available options.
- Lines 209-248: function `cluster_stories` - Clusters articles into story groups based on proximity and recency, optionally forcing a re-clustering of all articles.

---

### cli_schedule.py

**Lines:** 578

- Lines 25-27: function `_get_script_path` - Creates a command to fetch data using the `src.cli fetch` module.
- Lines 30-56: function `_parse_interval` - Parses interval strings like '5m' or '1h' into minutes.
- Lines 59-71: function `_save_schedule_config` - Saves schedule configuration to a JSON file in the designated directory.
- Lines 74-85: function `_load_schedule_config` - Loads schedule configuration from the SCHEDULE_CONFIG file, returning a dictionary containing enabled status and interval in minutes.
- Lines 88-127: function `_create_windows_task` - Creates a Windows Task Scheduler task to run a script at a specified interval.
- Lines 130-145: function `_delete_windows_task` - Deletes a scheduled task named "RSSFeedFetch" using the Windows Task Scheduler.
- Lines 148-168: function `_get_windows_task_status` - Retrieves the status of a Windows Task Scheduler task by querying its information.
- Lines 171-210: function `_create_cron_job` - Creates a cron job for Unix systems by constructing a cron expression and updating the crontab file.
- Lines 213-235: function `_delete_cron_job` - Deletes cron jobs associated with RSS summarization from the user's crontab.
- Lines 239-274: function `schedule_main` - Manages the scheduling of automatic feed fetching intervals.
- Lines 278-332: function `enable` - Sets up the OS scheduler to run 'rss fetch' at the specified interval, ensuring articles accumulate even when the app is not in use.
- Lines 336-360: function `disable` - Disables scheduled background fetching by removing the task from the operating system scheduler.
- Lines 364-447: function `status` - Displays the current status of the RSS schedule, including whether background fetching is enabled and the next scheduled run time.
- Lines 451-578: function `configure` - Parses user-provided interval strings (e.g., "30m", "1h") into seconds to determine the frequency of background feed fetching.

---

### cli_signal_tags.py

**Lines:** 240

- Lines 20-55: function `tag_main` - Manages signal tags for articles, enabling categorization by content type, tone, and source.
- Lines 59-110: function `tag_articles_cmd` - Tags a specified number of articles with signal tags, either using an LLM or rule-based methods, and updates the database with the results.
- Lines 114-165: function `tag_stats_cmd` - Calculates the frequency of signal tags in tagged articles and displays the most common tags with their counts and percentages.
- Lines 169-240: function `filter_by_tags` - Filters articles based on specified inclusion and exclusion tags, limiting the number of results displayed.

---

### cli_stories.py

**Lines:** 324

- Lines 17-19: function `get_storage` - Retrieves a database storage instance specified by the provided database path.
- Lines 23-73: function `backfill_embeddings` - Embeds stories missing embeddings from the database to enable accurate duplicate detection.
- Lines 55-58: function `update_progress` - Handles progress updates by displaying the current progress and title in a formatted string.
- Lines 77-146: function `list_stories` - Retrieves story clusters with their title, lifecycle state, article count, and last updated time.
- Lines 150-258: function `fix_titles` - Finds stories with problematic titles and regenerates them using an LLM, optionally limiting the number of stories fixed.
- Lines 262-324: function `stats` - Calculates and displays story statistics, including the total number of stories, the number with embeddings, and a breakdown by lifecycle state.

---

### clustering.py

**Lines:** 1079

- Lines 15-17: class `ClusteringError` - Handles errors during clustering operations by raising a `ClusteringError` exception.
- Lines 20-352: class `StoryClusterer` - Clusters an article into an existing story by comparing its vector embedding to the embeddings of active stories, prioritizing similarity above a defined threshold.
- Lines 27-39: function `__init__` - Initializes the object with specified LLM provider, storage, optional knowledge base, and embedding service, setting a similarity threshold for knowledge retrieval.
- Lines 42-44: function `embedding_service` - Returns the embedded service instance.
- Lines 46-59: function `cluster_article` - Clusters an article into an existing story or creates a new story if no match is found.
- Lines 61-92: function `find_matching_story` - Compares an article embedding with active story embeddings to find the best match based on vector similarity, returning the closest story if the score exceeds a defined threshold.
- Lines 94-120: function `find_matching_story_with_embedding` - Compares a given embedding against the embeddings of active stories to find the best matching story within a specified similarity threshold.
- Lines 122-141: function `_get_or_create_article_embedding` - Generates an article embedding if one doesn't exist, and returns the embedding vector; otherwise, retrieves the existing embedding.
- Lines 143-181: function `_calculate_similarity` - Calculates the cosine similarity between an article embedding and a story embedding, prioritizing chunk-based matching if an article ID is provided for fine-grained results.
- Lines 183-202: function `_find_matching_story_keywords` - Finds a matching story from active stories based on keyword similarity, returning the best match if the score is above 0.5, otherwise returns None.
- Lines 204-228: function `_generate_comparison_prompt` - Generates a prompt for an LLM to compare an article with an existing story, requesting a JSON response indicating whether they are about the same ongoing story, along with a confidence score and reasoning.
- Lines 230-247: function `_parse_similarity_response` - Parses an LLM response for a JSON object indicating story similarity, falling back to keyword analysis if JSON parsing fails.
- Lines 249-259: function `_keyword_similarity` - Calculates keyword similarity between an article and a story by counting matching keywords from the story within the article text, returning a similarity score.
- Lines 261-313: function `create_new_story` - Creates a new Story object from an Article, utilizing extracted metadata and default values if necessary, then saves the story to the database and links it to the original article.
- Lines 315-347: function `update_story_with_article` - Updates a story by adding an article, updating keywords, and saving the changes to storage.
- Lines 355-559: class `NewsItemExtractor` - Extracts new information from an article within the context of a story by generating a prompt, parsing the LLM response, deduplicating items, and saving new findings.
- Lines 361-377: function `__init__` - Initializes the object with specified LLM provider, storage, and optional embedding service and knowledge base.
- Lines 379-412: function `extract_news_items` - Extracts new news items from an article within a story's context by generating a prompt, parsing the LLM response, deduplicating with existing items, and saving confident new items.
- Lines 414-447: function `_generate_extraction_prompt` - Generates a prompt for extracting new information from an article, considering existing news items and classifying extracted information by type.
- Lines 449-498: function `_parse_news_items` - Parses a JSON response from an LLM to extract and structure news items, including title, description, publication time, and source information.
- Lines 500-522: function `deduplicate_items` - Removes duplicate news items from a list by comparing titles against existing items and updating article IDs if necessary.
- Lines 524-545: function `_items_similar` - Calculates the similarity between two news items by embedding their combined title and description and comparing the cosine similarity to a predefined threshold, returning True if the similarity is above the threshold.
- Lines 547-559: function `_get_embedding` - Retrieves a text embedding from the cache if available, otherwise calls an external service and caches the result, returning None if embedding fails.
- Lines 562-672: class `StoryEvolutionTracker` - Calculates article velocity (articles per day) for a story within a specified time window.
- Lines 565-566: function `__init__` - Initializes the object with a storage component to manage data persistence.
- Lines 568-591: function `update_all_stories` - Updates the lifecycle states of all active stories by retrieving them, comparing their current and new states, and updating the storage accordingly.
- Lines 593-618: function `calculate_velocity` - Calculates article velocity (articles per day) by counting recently published articles within a specified window and dividing by the window duration in hours.
- Lines 620-646: function `update_lifecycle_state` - Determines a story's lifecycle state ("emerging", "developing", "peaked", "declining", or "resolved") based on activity metrics like time since last update, article count, and velocity.
- Lines 648-672: function `get_evolution_stats` - Calculates and returns statistics about story evolution, including the number of stories in each lifecycle state, average articles and news items per story.
- Lines 675-732: function `process_article_clustering` - Processes an article by clustering it into a story and optionally extracting news items, returning statistics on the process.
- Lines 735-817: function `update_story_clusters` - Updates story clusters by processing unclustered articles within a specified lookback window using an LLM provider.
- Lines 820-884: function `backfill_story_embeddings` - Embeds stories without existing embeddings using an embedding service and saves the resulting embeddings to the knowledge base.
- Lines 891-924: function `build_news_extraction_prompt` - Constructs a prompt for extracting novel information from an article, considering existing knowledge and requiring classification of extracted items.
- Lines 927-978: function `parse_news_extraction_response` - Parses a JSON response from an LLM to extract and save news items to storage, filtering by confidence level.
- Lines 987-1079: function `batch_process_articles` - Processes a batch of articles by clustering them and extracting news items, providing statistics on the operation's progress and any encountered errors.

---

### commands.py

**Lines:** 1557

- Lines 45-408: function `update` - Updates article data by fetching new articles, summarizing them with an LLM, tagging them, extracting knowledge, and applying personalized relevance scoring.
- Lines 411-492: function `_display_full_digest` - Displays a comprehensive digest of stories, perspectives, and emerging trends, including story titles, article summaries, signal tags, consensus/contested perspectives, relevance scores, emerging trend terms, and knowledge base statistics.
- Lines 495-526: function `_matches_topic_keywords` - Checks if an article's topic keywords match the provided topic string by mapping common topics to trend categories and then verifying keyword presence in the article's title and content.
- Lines 529-592: function `_display_digest` - Displays a formatted digest of articles, including title, publication date, summary, tags, and link, with optional filtering by topic, relevance score display, and provider information.
- Lines 595-698: function `setup_wizard` - Checks the status of available LLM providers and presents options for setup or selection.
- Lines 701-728: function `_save_provider_config` - Saves provider configuration to a JSON file, enabling the LLM Studio to safely auto-load the provider.
- Lines 731-839: function `_setup_lm_studio_config` - Configures LM Studio for safe auto-loading by checking model availability and prompting the user for a lightweight model name.
- Lines 842-870: function `_onboard_feeds` - Guides the user through adding initial RSS feeds by presenting options to either maintain existing feeds or start with a fresh configuration.
- Lines 873-894: function `_setup_feeds` - Adds an RSS feed based on user selection from options like importing from OPML, adding a URL, pasting multiple URLs, or browsing curated feeds.
- Lines 897-966: function `_import_opml` - Validates feeds from an OPML file, then adds valid feeds to a configuration file.
- Lines 969-1030: function `_add_feed_smart` - Validates a URL, website URL, or domain to discover and optionally add a feed to the configuration file.
- Lines 1033-1077: function `_paste_multiple_urls` - Validates a list of URLs by attempting to discover and add them as feeds to a configuration file, reporting success or failure for each URL.
- Lines 1080-1095: function `_browse_curated_feeds` - Browses curated feeds by category or searches for feeds based on user selection.
- Lines 1098-1135: function `_show_curated_categories` - Displays curated feed categories and their associated feed counts, prompting the user to select a category for browsing.
- Lines 1138-1198: function `_show_category_feeds` - Validates a list of feeds based on user selection and writes valid feed information to a configuration file.
- Lines 1201-1230: function `_parse_selection` - Parses a comma-separated selection string, including ranges like "1-5", into a sorted list of integer indices within the specified maximum number of items.
- Lines 1233-1297: function `_search_feeds` - Searches for feeds online based on user-provided keywords and displays the results in a table, allowing the user to select feeds to add to a configuration file.
- Lines 1304-1310: function `_finish_onboarding` - Displays a completion message indicating setup is complete and the next step is to update RSS feeds for article summarization.
- Lines 1313-1431: function `_setup_new_provider` - Configures the selected cloud provider by prompting the user for an API key and saving it to the environment.
- Lines 1434-1473: function `_show_local_setup_instructions` - Explains the differences between cloud and local LLM providers, detailing the automatic model loading and unloading process for local LLMs.
- Lines 1476-1505: function `_select_provider` - Selects a provider from a list of available options based on user input, configuring the chosen provider and initiating the onboarding process if available.
- Lines 1508-1557: function `get_digest_summary` - Generates a text summary of recent articles, optionally filtered by topic and time window.

---

### constitution.py

**Lines:** 109

- Lines 39-41: function `get_constitution_path` - Returns the path to the constitution file using a predefined default path.
- Lines 44-46: function `constitution_exists` - Validates if a constitution file exists by checking the path returned by the `get_constitution_path()` function.
- Lines 49-65: function `get_constitution_content` - Loads the constitution content from the specified path, returning None if the file doesn't exist or is empty.
- Lines 68-86: function `get_constitution_context` - Formats user-defined constitutional principles into a context string for use with LLM prompts, returning an empty string if no constitution is available.
- Lines 89-104: function `create_constitution` - Creates a constitution file at a specified path, using a default template if no content is provided.
- Lines 107-109: function `get_example_constitution` - Returns the example constitution template as a string.

---

### content_filter.py

**Lines:** 300

- Lines 20-25: class `FilterResult` - Validates content against promotional filters, returning a result object with details about promotional status, confidence, reasons, and matched patterns.
- Lines 112-172: function `is_promotional_content` - Detects promotional content in an article by analyzing title, content, and link patterns against predefined lists and confidence thresholds.
- Lines 175-180: function `add_spam_support` - Handles legacy spam column additions by noting that schema migrations now manage these additions centrally.
- Lines 183-205: function `flag_as_spam` - Flags an article as spam by updating its status, reason, and timestamp in the database.
- Lines 208-244: function `get_spam_articles` - Retrieves a limited number of articles flagged as spam from storage, ordered by the timestamp of their spam flagging.
- Lines 247-268: function `cleanup_old_spam` - Deletes spam articles older than a specified number of days from the storage, returning the number of deleted articles.
- Lines 271-300: function `filter_articles` - Filters articles based on a promotional content threshold, separating clean articles from those flagged as spam and storing spam information.

---

### context_commands.py

**Lines:** 273

- Lines 13-57: function `context_init` - Initializes a user context profile by prompting for role, projects, topics to watch/ignore, and saving the profile to a store.
- Lines 60-99: function `context_show` - Loads and displays a user's personal context, including role, current projects, watched topics, pinned items, ignored topics, personalization strength, and last updated timestamp.
- Lines 102-138: function `context_edit` - Updates the user's personal context by prompting for and saving changes to their role, projects, watching list, and ignore list.
- Lines 141-153: function `context_pin` - Pins a specified topic to a user's profile to prevent its relevance from decaying.
- Lines 156-168: function `context_unpin` - Unpins a specified topic from the user's pinned topics, saving the updated profile and confirming the action.
- Lines 171-183: function `context_watch` - Handles adding a specified topic to the user's watching list, displaying confirmation or a message if already watching.
- Lines 186-198: function `context_ignore` - Adds a specified topic to the user's ignore list, printing confirmation if successful or if the topic is already ignored.
- Lines 201-231: function `context_stats` - Retrieves and displays the top 15 most engaging topics from the last 30 days, showing their engagement rates as bars in a table.
- Lines 234-244: function `context_export` - Exports personal context data from the UserContextStore to a specified file in JSON format.
- Lines 247-257: function `context_import` - Imports personal context data from a JSON file and stores it in the UserContextStore.
- Lines 260-273: function `context_clear` - Clears all personal context data, confirming with the user before proceeding and displaying a message upon completion.

---

### cross_source.py

**Lines:** 402

- Lines 17-24: class `SourcePerspective` - Captures a source's perspective on an article, including its name, domain, key claims, framing, and emphasized aspects.
- Lines 28-35: class `CrossSourceComparison` - Analyzes story and source perspectives to identify common facts, divergent claims, coverage gaps, and bias indicators.
- Lines 38-48: function `extract_domain` - Extracts the domain name from a URL by parsing it and removing the "www." prefix, returning the original URL if parsing fails.
- Lines 51-90: function `get_source_name` - Retrieves a human-readable source name from a domain, using a predefined dictionary and falling back to a title-cased domain replacement if the domain is not found.
- Lines 127-129: function `get_source_leaning` - Retrieves the political leaning of a given domain from a predefined dictionary, returning "unknown" if the domain is not found.
- Lines 132-170: function `get_stories_with_multiple_sources` - Finds stories covered by at least `min_sources` unique sources from the `storage`, limiting the results to `limit` stories and sorting them by source count in descending order.
- Lines 173-273: function `compare_story_coverage` - Compares how different sources cover a story by extracting claims, analyzing framing and emphasis, identifying common facts and coverage gaps, and determining bias indicators.
- Lines 276-312: function `format_comparison` - Formats a cross-source comparison into a human-readable string, detailing story information, source perspectives, common ground, and coverage gaps.
- Lines 345-368: function `get_current_feed_leanings` - Analyzes political leaning distribution of feeds from a specified file, returning a dictionary with lists of domains categorized as left, center, right, or unknown.
- Lines 371-402: function `suggest_diverse_sources` - Suggests diverse feeds by category, prioritizing underrepresented areas to balance the user's feed mix.

---

### embedding_providers.py

**Lines:** 467

- Lines 19-21: class `EmbeddingProviderError` - Handles errors originating from the embedding provider by raising an EmbeddingProviderError exception.
- Lines 24-26: class `NoProviderAvailableError` - Handles the case where no embedding provider is available, raising an exception to signal the failure.
- Lines 30-34: class `ProviderConfig` - Handles embedding provider configuration with URL, model name, and timeout settings.
- Lines 37-85: class `embed_batch` - Generates embedding vectors for single texts and batches of texts, returning an embedding as a list of floats.
- Lines 41-43: function `is_available` - Handles provider availability by checking reachability and readiness.
- Lines 46-58: function `embed` - Generates an embedding vector from a given text string.
- Lines 61-73: function `embed_batch` - Generates embedding vectors for a list of texts by processing each text individually.
- Lines 77-79: function `name` - Handles requests for the provider name, returning a string for logging and display purposes.
- Lines 83-85: function `model_name` - Returns the name of the embedding model used in the system.
- Lines 88-287: class `embed` - Generates embeddings for multiple texts by making a single API call to the LM Studio gateway, enabling efficient batch processing.
- Lines 97-109: function `__init__` - Initializes the object with optional URL, model name, timeout duration, and a flag to automatically load the model.
- Lines 112-113: function `name` - Returns the name "LM Studio" as a string.
- Lines 116-138: function `model_name` - Retrieves the model name from local cache or LM Studio API, returning "unknown" if not found.
- Lines 140-164: function `is_available` - Checks connectivity to the LM Studio gateway by attempting to retrieve the list of available models and returns True if successful, False otherwise.
- Lines 172-190: function `_win_to_msys_path` - Converts Windows paths to MSYS/Git Bash paths by replacing backslashes with forward slashes and handling drive letters, ensuring compatibility with Git Bash subprocess calls.
- Lines 192-200: function `_msys_to_win_path` - Converts MSYS/Git Bash paths to Windows paths by converting the leading `/c/` to `C:/`.
- Lines 202-220: function `embed` - Generates an embedding for a given text string by utilizing a gateway that handles model loading, queue management, and model switching.
- Lines 222-287: function `embed_batch` - Generates embeddings for a list of texts by sending them in a single API request to the LM Studio server.
- Lines 290-396: class `model_name` - Generates an embedding for a given text using Ollama's API, handling potential connection errors and response issues.
- Lines 300-308: function `__init__` - Initializes the object with an optional URL, model, and timeout value, using default values if not provided.
- Lines 311-312: function `name` - Returns the string "Ollama".
- Lines 315-316: function `model_name` - Returns the model name stored in the `_model` attribute as a string.
- Lines 318-342: function `is_available` - Validates if Ollama is running and the specified model is available by checking the API response for model tags.
- Lines 344-388: function `embed` - Generates an embedding from the provided text using Ollama, returning a list of floats representing the embedding.
- Lines 390-396: function `embed_batch` - Generates embeddings for a list of text strings by sequentially calling the embed method for each text.
- Lines 399-467: class `get_provider` - Gets the active embedding provider, prioritizing a preferred provider and falling back to auto-detection from a list of available providers.
- Lines 406-418: function `__init__` - Initializes the provider manager with a dictionary of embedding providers, a preferred provider setting, and an active provider initialized to None.
- Lines 420-456: function `get_provider` - Retrieves an available embedding provider, prioritizing a cached provider, a preferred provider, and then attempting each provider in order, raising an error if none are available.
- Lines 458-463: function `list_available` - Returns a list of provider names whose corresponding providers have the `is_available()` method returning True.
- Lines 465-467: function `add_provider` - Adds a new EmbeddingProvider to the registry, associating it with a given name.

---

### embeddings.py

**Lines:** 519

- Lines 25-29: class `EmbeddingResult` - Creates an EmbeddingResult object containing the vector, model name, and dimensionality of the generated embedding.
- Lines 32-34: class `EmbeddingError` - Handles errors during embedding operations by raising an EmbeddingError exception.
- Lines 37-475: class `get_provider_info` - Generates embeddings for text, handling long texts by chunking and averaging to preserve information.
- Lines 44-58: function `__init__` - Initializes the embedding service with an optional knowledge base and preferred provider, creating a new knowledge base if none is provided.
- Lines 60-69: function `_get_provider` - Handles retrieval of the active embedding provider, raising an EmbeddingError if no provider is available.
- Lines 71-109: function `embed_text` - Embeds text by chunking long passages, averaging the embeddings, and returning a vector representation with model details and dimensions.
- Lines 111-172: function `embed_text_with_chunks` - Generates an embedding for the input text and preserves individual chunk embeddings for fine-grained matching.
- Lines 174-204: function `_chunk_at_sentences` - Splits text into chunks at sentence boundaries to ensure compatibility with embedding model input limits.
- Lines 206-221: function `_average_vectors` - Calculates the average of multiple embedding vectors by summing corresponding elements and dividing by the number of vectors.
- Lines 223-289: function `embed_batch` - Generates embeddings for a list of texts by batching short texts and chunking/averaging long texts, returning a list of EmbeddingResult objects.
- Lines 291-301: function `embed_article` - Combines an article's title and content, chunks long content, and averages embeddings to generate a complete representation.
- Lines 303-313: function `embed_story` - Generates an embedding for a story by combining its title, description, and up to 20 keywords into a single text string.
- Lines 315-359: function `save_embedding` - Saves an embedding to the knowledge base and FAISS index, ensuring FAISS availability for searchable embeddings.
- Lines 361-374: function `get_embedding` - Retrieves a stored embedding for a given target ID and type ('article', 'story', or 'insight') as a list of floats, or returns None if the embedding is not found.
- Lines 376-399: function `cosine_similarity` - Calculates the cosine similarity between two vectors by computing their dot product and dividing by the product of their magnitudes, handling unequal vector lengths by padding with zeros.
- Lines 401-448: function `find_similar` - Finds similar items by vector similarity using FAISS, returning a list of target IDs and their corresponding similarity scores.
- Lines 450-456: function `is_available` - Handles embedding provider availability by attempting to retrieve the provider and returning True if successful, and False if an EmbeddingError occurs.
- Lines 458-475: function `get_provider_info` - Retrieves information about the active provider, including name and model, or returns an error message if retrieval fails.
- Lines 478-497: function `embed_and_store_article` - Embeds an article using the provided knowledge base and saves its embedding to the knowledge base.
- Lines 500-519: function `embed_and_store_story` - Embeds a story using the provided knowledge base (or creates one if none is given), then saves the story's ID and its embedding to a storage service.

---

### emergence.py

**Lines:** 433

- Lines 28-40: class `EmergingTrend` - Handles emerging trend data, storing term, mention counts across time, velocity, confidence, trajectory, relevant domains, action recommendations, recent article IDs, and related trends.
- Lines 43-109: function `extract_terms` - Extracts potential emerging terms from text by identifying capitalized multi-word phrases, technical terminology patterns, and acronyms with expansions.
- Lines 112-126: function `calculate_velocity` - Calculates velocity (rate of change) between two counts, returning a percentage change and handling division by zero.
- Lines 129-175: function `classify_trajectory` - Classifies a term's trajectory as "Research → Blogs → Mainstream", "Technical → Business adoption", or "Blogs → Mainstream" if it shows consistent growth across research, technology, and business domains.
- Lines 178-201: function `assign_confidence` - Assigns a confidence level ("High", "Medium", "Low", or "Watch") to an emerging trend prediction based on velocity, current mentions, domain count, and weeks of data.
- Lines 204-220: function `generate_action_recommendation` - Analyzes confidence, velocity, and trajectory to generate a tailored action recommendation for the user.
- Lines 223-377: function `detect_emerging_trends` - Detects emerging trends from stored articles by analyzing term mentions across time windows and domains, calculating velocity, and assigning confidence levels.
- Lines 380-433: function `format_emerging_trend` - Formats an emerging trend into a human-readable string containing its term, mentions, velocity, trajectory, domains, action recommendation, and recent article titles.

---

### feed_catalog.py

**Lines:** 124

- Lines 102-104: function `get_feeds_by_category` - Retrieves all feeds associated with a given category from the curated categories dictionary, returning an empty list if the category is not found.
- Lines 107-109: function `get_all_categories` - Returns a list of all available categories from the CURATED_CATEGORIES dictionary.
- Lines 112-124: function `search_curated_feeds` - Searches curated feeds for titles or descriptions matching the provided query, returning a list of dictionaries containing the matching feeds.

---

### feed_discovery.py

**Lines:** 364

- Lines 12-30: class `preview` - Returns a formatted string containing key information about the feed, including title, description, item count, and a preview of recent items.
- Lines 20-30: function `preview` - Returns a formatted string containing key information about the object, including title, description, item count, and recent items, limited to a specified number of items.
- Lines 33-89: function `validate_feed` - Validates a feed URL by fetching it, parsing the content, and extracting information such as title, description, and latest items.
- Lines 92-148: function `discover_feed` - DiscoverFeed attempts to locate an RSS feed URL by checking common paths and extracting links from the HTML content of a given domain.
- Lines 151-171: function `_extract_feed_from_html` - Extracts RSS/Atom feed URLs from HTML by searching for link tags with specific rel and type attributes, handling relative URLs by prepending the base URL.
- Lines 174-217: function `transform_url` - Transforms platform URLs into corresponding RSS feed URLs for YouTube channels, Reddit subreddits, and Substack publications.
- Lines 220-260: function `process_outlines` - Parses an OPML file, extracting feed information including title, URL, and category, and returns the data as a list of dictionaries along with any error message encountered.
- Lines 234-246: function `process_outlines` - Creates a list of feed dictionaries from outlines, extracting title, URL, and category information.
- Lines 263-299: function `detect_input_type` - Detects the type of input provided (OPML, single URL, multiple URLs, domain, platform URL, or unknown) based on its content and format.
- Lines 302-364: function `search_feeds_online` - Retrieves RSS feeds from a given URL or domain using the Feedsearch.dev API, returning a list of dictionaries containing feed information like title, URL, description, and score.

---

### gateway.py

**Lines:** 556

- Lines 26-28: class `GatewayError` - Handles errors originating from gateway operations by raising a GatewayError exception.
- Lines 31-33: class `GatewayUnavailableError` - Handles gateway unavailability by raising a GatewayUnavailableError exception.
- Lines 37-41: class `GatewayResponse` - Creates a GatewayResponse object with content, request type, and response path attributes to represent the outcome of a gateway request.
- Lines 44-544: class `_submit_request` - Handles automatic model loading, queue management, and batching for all local LLM requests.
- Lines 69-78: function `__init__` - Initializes the gateway interface by setting the timeout value and locating the gateway path.
- Lines 80-101: function `_find_gateway` - Raises a GatewayUnavailableError if the project's `scripts/safe-model-load.sh` gateway script is not found, indicating a broken project setup.
- Lines 103-110: function `_win_to_msys_path` - Converts Windows paths to MSYS2 paths by translating drive letters and backslashes, while preserving the original path if it's not a Windows path.
- Lines 112-119: function `_msys_to_win_path` - Converts MSYS2 paths to Windows paths by translating the `/c/Users/...` format to `C:\Users\...` and replacing forward slashes with backslashes.
- Lines 121-135: function `is_available` - Handles gateway availability by executing a status command and returning True if LM Studio is running, False otherwise.
- Lines 137-151: function `get_queue_depth` - Returns the number of pending requests in the gateway queue, or -1 if the queue file is missing or an error occurs.
- Lines 153-219: function `_submit_request` - Submits a request to the gateway, handling prompt formatting and optional system prompts and temperature overrides, and returns the path to the generated response file.
- Lines 221-267: function `_wait_for_response` - Waits for a response file to exist and be non-empty, then parses its JSON content, cleaning up the file upon success or raising an error if the response is invalid or the timeout is reached.
- Lines 269-292: function `is_response_ready` - Validates if a response file exists, has content, and is valid JSON before considering it ready.
- Lines 294-305: function `try_collect_text` - Collects text from a response file if the response is ready, otherwise returns None.
- Lines 311-336: function `request_text` - Generates text by submitting a request with a prompt, optional system prompt, and temperature, then returns the extracted text from the chat completion response.
- Lines 338-348: function `submit_text` - Submits a text request to the model without waiting, returning the response file path for later retrieval.
- Lines 350-357: function `collect_text` - Parses a text response to extract the generated text content from a specified path, returning the text if found and raising an error otherwise.
- Lines 363-381: function `request_embedding` - Retrieves an embedding vector from a server by submitting an "embedding" request with the provided text and handling potential format variations in the response.
- Lines 383-388: function `submit_embedding` - Submits an embedding request without waiting and returns the response file path for later retrieval.
- Lines 390-399: function `collect_embedding` - Collects an embedding from a submitted request, extracting the embedding value from either the "data" field or the top-level "embedding" field of the response.
- Lines 405-453: function `batch_text` - Collects generated texts from submitted prompts, ensuring the order matches the original request list.
- Lines 455-496: function `batch_embedding` - Collects embedding vectors for a list of texts by submitting requests to a gateway and then retrieving the results.
- Lines 502-522: function `clear_queue` - Handles the clearing of the gateway queue by executing a bash command and returns True on success or False on failure.
- Lines 524-544: function `unload` - Handles unloading all models and clearing the queue to free VRAM by executing a bash command, returning True on success and False otherwise.
- Lines 551-556: function `get_gateway` - Creates a LocalLLMGateway singleton, ensuring a single instance for accessing the local LLM.

---

### graph_cleanup.py

**Lines:** 305

- Lines 21-28: class `DuplicateCandidate` - Calculates the similarity between a canonical entity and its duplicate based on cosine similarity, considering their counts and entity type.
- Lines 32-37: class `CleanupResult` - Handles cleanup operations by reporting the number of candidates found, duplicates merged, triples updated, and any encountered errors.
- Lines 40-155: function `find_duplicate_entities` - Finds semantically similar entities within the knowledge base to identify potential duplicate entries based on a specified similarity threshold and entity type.
- Lines 158-200: function `merge_entity` - Merges a duplicate entity into the canonical form by updating triples referencing the duplicate to use the canonical name, ensuring data consistency within the knowledge base.
- Lines 203-256: function `run_cleanup` - Finds duplicate entities in the knowledge base based on embedding similarity and optionally merges high-confidence duplicates.
- Lines 259-305: function `get_cleanup_report` - Generates a human-readable report of potential duplicate entities based on similarity and a specified threshold, limiting the output to a defined number of candidates.

---

### knowledge.py

**Lines:** 2986

- Lines 27-36: class `Insight` - Creates an Insight object with details about a knowledge extraction from an article, including its ID, source, content, type, and confidence level.
- Lines 40-47: class `Entity` - Creates an Entity object with an ID, name, entity type, initial sighting date, and a count of mentions.
- Lines 51-59: class `Relationship` - Creates a Relationship object representing a connection between two insights, specifying their IDs, relationship type, and strength.
- Lines 63-80: class `Triple` - Creates an RDF-style triple object with specified subject, predicate, and object, along with associated metadata like types, source, and confidence.
- Lines 84-97: class `EntityRelationship` - Captures direct relationships between entities, such as acquisitions or partnerships, using IDs and a relationship type.
- Lines 101-113: class `Embedding` - Creates an Embedding object to store vector representations of insights, entities, or articles, including metadata like the embedding model and creation timestamp.
- Lines 117-126: class `UserContext` - Creates a user context object with an ID, context type, name, description, active status, and creation/update timestamps.
- Lines 129-1122: class `save_insight` - Initializes the database and creates tables for storing knowledge insights, entities, relationships, user context, and RDF-style triples.
- Lines 132-134: function `__init__` - Initializes the database path and calls the internal database initialization method.
- Lines 136-317: function `_init_db` - Initializes the database schema for storing knowledge insights, entities, relationships, user context, and RDF-style triples.
- Lines 320-327: function `_connect` - Handles database connections by opening a connection, setting row factory, yielding the connection, and ensuring the connection is closed in a `finally` block.
- Lines 329-351: function `save_insight` - Saves an insight to the database by inserting data into the `knowledge_insights` table, committing the changes, and returning True upon success.
- Lines 353-361: function `get_insight` - Retrieves a knowledge insight by its ID from the database, returning the Insight object if found, and None otherwise.
- Lines 363-400: function `get_insights` - Retrieves knowledge insights from a database, optionally filtering by insight type, confidence level, and source article, ordered by extraction time in descending order.
- Lines 402-428: function `save_entity` - Saves or updates an entity in the database by inserting if it doesn't exist or incrementing its mention count if it does.
- Lines 430-438: function `get_entity` - Retrieves an entity from the database by its ID, returning the entity object if found and None otherwise.
- Lines 440-449: function `get_entity_by_name` - Retrieves a knowledge entity by its name and type from the database, returning the entity if found and None otherwise.
- Lines 451-464: function `link_insight_to_entity` - Links an insight to an entity in the `insight_entities` table, optionally specifying relevance.
- Lines 466-488: function `save_relationship` - Saves a relationship between insights by inserting data into the knowledge_relationships table, committing the changes to the database and returning True on success, or False if a conflict occurs.
- Lines 490-522: function `get_relationships` - Retrieves knowledge relationships from a database, filtering by insight ID, relationship type, and detection time.
- Lines 524-545: function `save_context` - Saves user context to the database by inserting a new record with the provided context details and returning True on success, False if a conflict occurs.
- Lines 547-559: function `get_contexts` - Retrieves user contexts from the database, optionally filtering for active contexts and ordering by creation date.
- Lines 561-572: function `update_context_active` - Updates the active status of a context in the database, ensuring the `user_context` record for the specified `context_id` is updated with the provided `active` value and current timestamp.
- Lines 574-609: function `get_stats` - Retrieves knowledge base statistics including counts of insights, entities, relationships, contradictions, and high-confidence insights.
- Lines 611-621: function `_row_to_insight` - Converts a database row to an Insight object, extracting data such as ID, article ID, content, and confidence level.
- Lines 623-631: function `_row_to_entity` - Converts a database row to an Entity object using the provided column names for attributes like id, name, and mention count.
- Lines 633-642: function `_row_to_relationship` - Converts a database row to a Relationship object containing information about the relationship's ID, source and target insights, type, strength, and detection time.
- Lines 644-654: function `_row_to_context` - Converts a database row to a UserContext object, extracting data for ID, context type, name, description, active status, and timestamps.
- Lines 656-668: function `_row_to_triple` - Converts a database row to a Triple object, extracting data such as ID, subject, predicate, and confidence scores.
- Lines 670-680: function `_row_to_entity_relationship` - Converts a database row to an EntityRelationship object, mapping column values to corresponding attributes.
- Lines 686-731: function `save_triple` - Saves an RDF-style triple to the database after validating it against tautologies, circular reasoning, vague predicates, and integrity constraints.
- Lines 733-759: function `get_triples` - Queries knowledge triples with optional filters for subject, predicate, and object, ordering by extracted_at in descending order and limiting the results.
- Lines 761-779: function `query_triples_pattern` - Queries triples using LIKE patterns for subject and predicate, ordering by extracted_at in descending order and limiting to 200 results.
- Lines 781-795: function `get_triples_by_article` - Retrieves triples extracted from a specified article, ordered by extraction time, and limits the results to a defined number.
- Lines 801-824: function `save_entity_relationship` - Saves an entity-to-entity relationship by inserting data into the `entity_relationships` table, committing the transaction upon successful insertion and returning True, or False if a conflict occurs.
- Lines 826-846: function `get_entity_relationships` - Retrieves entity relationships from a database, optionally filtering by entity ID and relationship type, ordered by detection time.
- Lines 852-909: function `get_connected_entities` - Retrieves all entities connected to a given entity within a specified depth using knowledge triples, returning a dictionary of entities and their relationships.
- Lines 911-957: function `find_path` - Finds a path between two entities in the knowledge graph using breadth-first search, returning the path as a list of relationship dictionaries or None if no path exists within the specified maximum depth.
- Lines 959-1000: function `get_entity_neighborhood` - Retrieves the immediate connections (1-hop neighbors) of a given entity by querying outgoing and incoming relationships in a knowledge graph.
- Lines 1006-1027: function `save_embedding` - Saves a vector embedding to the knowledge_embeddings table, handling potential database errors and returning True on success or False on failure.
- Lines 1029-1048: function `get_embedding` - Retrieves an embedding for a given target ID and type from the knowledge_embeddings table, returning an Embedding object if found, otherwise None.
- Lines 1050-1056: function `has_embeddings` - Queries the database to determine if any knowledge embeddings exist.
- Lines 1058-1072: function `get_target_ids_with_embeddings` - Retrieves all target IDs associated with embeddings of the specified type from the knowledge_embeddings table.
- Lines 1078-1122: function `get_graph_stats` - Retrieves comprehensive statistics about the knowledge graph, including triple counts, entity relationships, embeddings, unique predicates, and top connected entities.
- Lines 1126-1147: class `ConsolidatedExtractionResult` - Creates a consolidated extraction result containing insights, triples, summary, headline, and keywords from a single LLM call.
- Lines 1145-1147: function `__post_init__` - Initializes the object by setting the `keywords` attribute to an empty list if it is initially None.
- Lines 1150-1324: function `extract_all_from_article` - Extracts comprehensive insights and factual relationships from an article using a single LLM call, consolidating previous multi-step processes.
- Lines 1327-1468: function `extract_insights_from_article` - Extracts key learnings from an article using a language model and saves them to a knowledge base with associated metadata.
- Lines 1475-1510: function `build_insight_prompt` - Builds a prompt for insight extraction by incorporating constitution context and instructions for identifying key learnings, their types, confidence levels, reasoning, and entities, formatted as a JSON array.
- Lines 1513-1590: function `parse_insight_response` - Parses LLM response, extracts insights, and saves them to the knowledge base, including entity linking and error handling.
- Lines 1594-1606: class `TripleExtractionResult` - Extracts new, existing, and updated triples from a knowledge base based on triple extraction results.
- Lines 1601-1602: function `total_extracted` - Calculates the total number of extracted triples by summing the lengths of new, existing, and updated triple lists.
- Lines 1605-1606: function `actually_new` - Calculates the number of new triples to return a count of newly generated data.
- Lines 1609-1666: function `_correct_inverted_predicate` - Corrects inverted "_by" predicates by swapping the subject and object when the subject appears to be a person acting upon an entity.
- Lines 1669-1728: function `_semantic_chunk` - Splits article text into semantically coherent chunks for embedding and knowledge extraction by prompting an LLM to identify natural boundaries.
- Lines 1731-1771: function `_find_similar_triple` - Checks for exact and case-insensitive matching triples in the knowledge base to prevent duplicate entries.
- Lines 1774-1798: function `extract_triples_from_article` - Extracts RDF-style triples from an article by chunking, using an LLM for extraction and a knowledge base for comparison to identify new triples.
- Lines 1801-1934: function `extract_triples_with_comparison` - Extracts factual relationships from article text as subject-predicate-object triples, categorizing them as new, existing, or updated facts.
- Lines 1937-2039: function `extract_entity_relationships_from_article` - Extracts entity relationships from an article by prompting a language model to identify connections between organizations, people, and products, then saving these relationships to a knowledge base.
- Lines 2042-2063: function `build_chunk_prompt` - Divides an article into semantically coherent chunks for embedding and knowledge extraction, returning None if the article's content is insufficient.
- Lines 2066-2082: function `parse_chunk_response` - Parses an LLM response string to extract a list of text chunks enclosed in square brackets, returning the full article content as a single chunk if parsing fails.
- Lines 2085-2129: function `get_connection_candidates` - Retrieves candidate insights for connection detection by finding similar insights in the knowledge base based on embedding similarity, filtering out self-matches and limiting results to the top 10.
- Lines 2132-2155: function `build_connection_prompt` - Constructs a prompt for classifying relationships between insights, detailing each pair's content and requesting a JSON array of relationship labels (confirms, contradicts, refines, extends, none).
- Lines 2158-2199: function `parse_connection_response` - Parses an LLM response to extract relationship types and save them to the knowledge base, handling potential parsing errors gracefully.
- Lines 2202-2234: function `build_triple_prompt` - Constructs a detailed prompt for extracting subject-predicate-object triples from a text chunk, emphasizing proper noun usage and specific relationship types, formatted as a JSON array.
- Lines 2237-2307: function `parse_triple_response` - Parses a JSON string containing triples from an LLM response and saves new triples to the knowledge base while identifying existing ones.
- Lines 2310-2336: function `build_entity_rel_prompt` - Generates a detailed prompt for entity relationship extraction from an article, specifying relationship types and desired JSON output format.
- Lines 2339-2398: function `parse_entity_rel_response` - Parses a JSON string containing entity relationships from an LLM response and saves them to the knowledge base.
- Lines 2401-2541: function `detect_connections` - Detects relationships between a new insight and existing knowledge by leveraging FAISS for efficient similarity search and an LLM for relationship classification.
- Lines 2544-2567: function `format_relationship` - Formats a relationship by retrieving target insight content and displaying the relationship type, strength, and target insight preview.
- Lines 2570-2625: function `query_knowledge_base` - Queries the knowledge base using a natural language query and an LLM to filter relevant insights, then returns a structured summary of the results.
- Lines 2633-2647: class `CombinedExtractionOutput` - Creates a combined output containing insights, new and existing triples, signal tags, summary, headline, keywords, and an indicator of whether the input was identified as an advertisement.
- Lines 2650-2820: function `extract_all_from_article` - Extracts comprehensive information from an article in a single LLM call, including insights, triples, signal tags, and a structured summary.
- Lines 2823-2888: function `build_extraction_prompt` - Builds a prompt for extracting structured information from an article by specifying analysis instructions and desired JSON output format.
- Lines 2891-2986: function `process_extraction_response` - Processes a raw LLM response string by parsing it with schema validation and extracting insights and triples to be saved to the knowledge base.

---

### llm_providers.py

**Lines:** 1593

- Lines 14-29: class `ProviderType` - Validates an LLM provider type string against a predefined list of supported values.
- Lines 33-91: class `LLMConfig` - Loads LLM configuration from either environment variables or a JSON file, prioritizing environment variables if available.
- Lines 44-53: function `from_env` - Loads LLM configuration from environment variables, using provided values for provider, base URL, API key, and model name.
- Lines 56-73: function `from_file` - Loads LLM configuration from a JSON file, providing default values if the file doesn't exist.
- Lines 75-91: function `save` - Saves the LLM configuration to a JSON file at the specified path, ensuring the parent directory exists and securely handling API keys.
- Lines 95-106: class `UsageStats` - Calculates the total number of tokens generated by a summarization call by summing input and output token counts.
- Lines 104-106: function `__post_init__` - Calculates the total number of tokens by summing the input and output token counts.
- Lines 109-162: class `_estimate_tokens` - Generates a summary of the input text, with an optional maximum length, for use in summarization tasks.
- Lines 112-116: function `__init__` - Initializes the object by tracking previous usage and setting up session-level usage statistics.
- Lines 119-121: function `summarize` - Generates a summary of the input text, limited to a maximum length of 150 characters.
- Lines 123-129: function `generate` - Generates a response to a given prompt by summarizing it with a specified maximum length.
- Lines 132-134: function `is_available` - Handles provider availability by returning True if the provider is available, and False otherwise.
- Lines 138-140: function `name` - Handles the retrieval of a provider's display name.
- Lines 143-145: function `model_name` - Returns the model name as a string, defaulting to "unknown" if the name is not specified.
- Lines 147-149: function `_estimate_tokens` - Estimates token count from text by dividing the text length by 4, providing a rough approximation of tokens.
- Lines 151-162: function `_record_usage` - Records usage statistics, including input and output token counts, model name, and provider, to track summarization call performance.
- Lines 165-332: class `__init__` - Generates a concise summary of the input text using the specified OpenAI-compatible model and parameters.
- Lines 171-183: function `__init__` - Initializes the object with a base URL, API key, model name, and provider name, configuring internal attributes for subsequent operations.
- Lines 186-187: function `name` - Returns the name of the provider associated with the object.
- Lines 190-194: function `model_name` - Returns the discovered model name if available, otherwise returns the configured model name or "auto".
- Lines 196-202: function `is_available` - Handles endpoint reachability by attempting a GET request and returning True if the status code is 200, False otherwise.
- Lines 204-224: function `_get_model` - Retrieves the model ID to use, prioritizing a specified model and falling back to "default" if discovery from the API fails.
- Lines 226-284: function `summarize` - Summarizes text within a specified character limit using an OpenAI-compatible API, ensuring conciseness and key point capture.
- Lines 286-332: function `generate` - Generates a text response to a given prompt using a specified language model, handling API requests and tracking token usage.
- Lines 335-575: class `_auto_load_model` - Loads a specified language model using the LM Studio CLI, checking for resource availability and ensuring sufficient headroom before unloading.
- Lines 338-344: function `__init__` - Initializes the object with a base URL, model name, and provider name, and sets a flag to track auto-load attempts.
- Lines 346-415: function `_auto_load_model` - Loads a specified language model using LM Studio, checking for availability and sufficient resources before loading and setting a time-to-live for automatic unloading.
- Lines 417-460: function `_check_post_load_headroom` - Verifies sufficient memory headroom after model loading, unloading the model and returning False if system resources are insufficient.
- Lines 462-523: function `MEMORYSTATUSEX` - Retrieves the available system memory in MB, using platform-specific methods to read from Windows or Linux/macOS.
- Lines 476-487: class `MEMORYSTATUSEX` - Retrieves memory statistics from a system structure, providing details about memory usage and availability.
- Lines 525-548: function `_make_request` - Handles text requests through the gateway, managing model loading, queueing, and coordination, raising an error if the gateway is unavailable.
- Lines 550-569: function `summarize` - Summarizes the input text within a specified character limit by prompting a language model to be concise and capture key points.
- Lines 571-575: function `generate` - Generates a response using LM Studio based on the provided prompt and maximum token limit.
- Lines 578-586: class `OllamaProvider` - Initializes the OllamaProvider with a specified model and base URL for accessing the local LLM endpoint.
- Lines 581-586: function `__init__` - Initializes the client with a base URL, model name (defaulting to "llama2"), and provider name ("Ollama").
- Lines 589-635: class `model_name` - Summarizes input text using a pre-loaded Hugging Face Transformers model, returning the generated summary.
- Lines 592-595: function `__init__` - Initializes the object with a specified language model, storing it for use in subsequent operations.
- Lines 598-599: function `name` - Returns a string describing the Transformers model name.
- Lines 602-603: function `model_name` - Returns the model name stored as the value of the `_model` attribute.
- Lines 605-612: function `is_available` - Handles availability by attempting to import transformers and torch, returning True if successful and False otherwise.
- Lines 614-619: function `_load_pipeline` - Creates a summarization pipeline using the specified model if one doesn't already exist.
- Lines 621-635: function `summarize` - Generates a concise summary of the input text using a pre-loaded transformer pipeline, ensuring the summary's length falls within a specified range.
- Lines 638-712: function `get_provider` - Selects and returns the appropriate LLM provider based on the provided configuration, prioritizing explicit settings, environment variables, config files, and auto-detection.
- Lines 715-787: function `list_providers` - Returns a list of dictionaries detailing available language model providers, including their type, name, status, and description.
- Lines 790-866: class `model_name` - Summarizes the provided text within a specified character limit, ensuring conciseness and capturing key points.
- Lines 799-802: function `__init__` - Initializes the object with a specified language model and sets up the client connection.
- Lines 805-806: function `name` - Returns the name "Claude" as a string.
- Lines 809-810: function `model_name` - Returns the model name stored as the value of the `_model` attribute.
- Lines 812-821: function `is_available` - Validates Anthropic SDK availability by checking for the presence of an API key in the environment.
- Lines 823-828: function `_get_client` - Initializes an Anthropic client if one doesn't already exist, ensuring availability for AI interactions.
- Lines 830-866: function `summarize` - Summarizes the input text within a specified character limit by sending a prompt to the Claude model and returning the generated summary.
- Lines 869-937: class `__init__` - Generates a concise summary of the input text, constrained to a specified character length using the Claude Code CLI.
- Lines 876-878: function `__init__` - Initializes the object with a specified model, storing the model name for later use.
- Lines 881-882: function `name` - Returns the string "Claude Code".
- Lines 885-886: function `model_name` - Returns the model name stored as the value of the `_model` attribute.
- Lines 888-891: function `is_available` - Checks if the Claude Code CLI is available by searching for the "claude" executable in the system's PATH and returning True if found, False otherwise.
- Lines 893-937: function `summarize` - Summarizes a given text within a specified character limit using the Claude Code CLI, returning an empty string if the input is empty.
- Lines 940-1039: class `is_available` - Generates a summary of the input text within a specified character limit using the Claude Agent SDK.
- Lines 953-955: function `__init__` - Initializes the object with a specified model, storing the model name for later use.
- Lines 958-959: function `name` - Returns the name of the Claude Agent SDK.
- Lines 962-963: function `model_name` - Returns the model name stored as the value of the `_model` attribute.
- Lines 965-981: function `is_available` - Validates Claude Agent SDK availability and authentication by checking for the SDK import and the existence of a configuration file.
- Lines 983-999: function `_run_async` - Handles asynchronous coroutines by running them synchronously within a thread pool if an event loop is active, otherwise executing them directly.
- Lines 1001-1012: function `_query_claude` - Queries Claude using the Agent SDK, extracting and concatenating text blocks from the assistant's response.
- Lines 1014-1031: function `summarize` - Summarizes text within a specified character limit using the Claude Agent SDK, ensuring the summary is concise and directly addresses the input.
- Lines 1033-1039: function `generate` - Generates a response using the Claude Agent SDK, returning the stripped text if the SDK is available.
- Lines 1042-1114: class `name` - Summarizes a given text within a specified character limit by constructing a prompt and utilizing the Gemini API.
- Lines 1048-1051: function `__init__` - Initializes the object with a specified language model name, storing it for later use.
- Lines 1054-1055: function `name` - Returns the string "Gemini" when called.
- Lines 1058-1059: function `model_name` - Returns the model name stored in the `_model` attribute as a string.
- Lines 1061-1070: function `is_available` - Checks if the Gemini SDK is importable and a valid API key is set.
- Lines 1072-1079: function `_get_client` - Handles client initialization by retrieving a GenerativeModel instance from a cache or creating a new one using the provided API key and model name.
- Lines 1081-1114: function `summarize` - Summarizes the given text within a specified character limit, ensuring conciseness and capturing key points.
- Lines 1119-1178: class `is_available` - Generates a concise summary of the input text using the Gemini CLI, limiting the output to a specified character length.
- Lines 1127-1129: function `__init__` - Initializes the object with a specified language model, storing it for subsequent use.
- Lines 1132-1133: function `name` - Returns the name of the Gemini CLI.
- Lines 1136-1137: function `model_name` - Returns the model name stored as the value of the `_model` attribute.
- Lines 1139-1142: function `is_available` - Checks if the Gemini CLI is installed and authenticated by verifying the presence of the "gemini" executable.
- Lines 1144-1178: function `summarize` - Generates a concise summary of the input text within a specified character limit using the Gemini CLI.
- Lines 1181-1251: class `model_name` - Generates a concise summary of the input text using the Codex CLI, limiting the output to a specified character length.
- Lines 1188-1190: function `__init__` - Initializes the object with a specified language model, storing the model name for later use.
- Lines 1193-1194: function `name` - Returns the name of the Codex CLI.
- Lines 1197-1198: function `model_name` - Returns the model name stored in the `_model` attribute as a string.
- Lines 1200-1203: function `is_available` - Validates if the Codex CLI is installed by checking for its presence in the system's PATH.
- Lines 1205-1251: function `summarize` - Generates a concise summary of the input text, limited to a specified character length, using the Codex CLI.
- Lines 1254-1273: class `__init__` - Initializes the Grok API provider using the specified model and API key from environment variables.
- Lines 1261-1268: function `__init__` - Initializes the Grok API client with a specified model and API key, setting the base URL for API requests.
- Lines 1270-1273: function `is_available` - Validates if either the XAI_API_KEY or GROK_API_KEY environment variable is set, returning True if at least one is defined and False otherwise.
- Lines 1276-1297: class `__init__` - Initializes the Groq API provider with the specified model, API key, and base URL.
- Lines 1286-1293: function `__init__` - Initializes the Groq client with a specified model, API key, and base URL for accessing the OpenAI API.
- Lines 1295-1297: function `is_available` - Validates if the Groq API key is set by checking the value of the "GROQ_API_KEY" environment variable.
- Lines 1300-1370: class `is_available` - Summarizes text using an OpenAI Agent with specified length constraints and tracks token usage.
- Lines 1307-1309: function `__init__` - Initializes the object with a specified model string, storing it for later use.
- Lines 1312-1313: function `name` - Returns the string "OpenAI Agents" when called.
- Lines 1316-1317: function `model_name` - Returns the model name stored in the `_model` attribute as a string.
- Lines 1319-1324: function `is_available` - Validates OpenAI API key from the environment, returning True if present and False otherwise.
- Lines 1326-1370: function `summarize` - Summarizes the input text within a specified character limit using a language model, returning only the generated summary.
- Lines 1372-1433: function `auto_detect_provider` - Detects the best available LLM provider by prioritizing local options like LM Studio and Ollama, followed by cloud-based services such as Gemini and Claude.
- Lines 1436-1447: function `get_best_provider` - Detects the best available provider and returns it along with a boolean indicating whether a real LLM was found.
- Lines 1450-1491: function `get_setup_instructions` - Returns detailed setup instructions for various LLM providers, including local and cloud options, along with installation and configuration steps.
- Lines 1494-1573: function `validate_llm_ready` - Validates if an LLM provider is available and ready for use, providing specific instructions if a required LLM is not configured or the provider is unavailable.
- Lines 1576-1593: function `ensure_llm_or_exit` - Validates LLM readiness and exits if an LLM provider is not ready, displaying instructions for setup.

---

### model_manager.py

**Lines:** 451

- Lines 19-21: class `ModelManagerError` - Handles errors during model management operations, providing a specific exception type for debugging and error handling.
- Lines 24-26: class `LMStudioNotReachableError` - Handles the error condition when the LM Studio server is unreachable, indicating a failure to connect.
- Lines 29-31: class `ModelLoadError` - Handles errors during model loading by raising a ModelLoadError when the process fails.
- Lines 34-36: class `ModelUnloadError` - Handles errors during model unloading by raising a ModelUnloadError.
- Lines 40-104: class `ModelConfig` - Loads model configuration from a project-local JSON file, prioritizing explicit paths and creating a default configuration if none is found.
- Lines 50-76: function `from_file` - Loads model configuration from a project-local JSON file, falling back to creating a default configuration if the file doesn't exist.
- Lines 79-104: function `create_default` - Creates a default configuration file at the specified path, populating it with placeholder model paths and settings for the user to customize.
- Lines 110-412: class `ModelManager` - Loads a model into LM Studio using the provided path and configuration.
- Lines 119-126: function `__init__` - Initializes the model manager, loading configuration from the provided `config` or the default location if no configuration is specified.
- Lines 129-134: function `config` - Loads the model configuration from a file if it hasn't already been loaded.
- Lines 136-147: function `_has_lms_command` - Checks if the 'lms' command is available by attempting to execute 'lms help' and verifying a successful return code.
- Lines 149-164: function `check_lm_studio` - Verifies LM Studio server reachability by attempting a GET request to the `/models` endpoint and returning True if the request is successful within a 5-second timeout.
- Lines 166-210: function `get_loaded_model` - Retrieves the path or identifier of the currently loaded language model, prioritizing the LMS command and falling back to the API if the command fails.
- Lines 212-236: function `get_loaded_model_identifier` - Retrieves the model identifier from the LMS command, returning the identifier string if successful, otherwise falls back to using the loaded model path.
- Lines 238-250: function `get_model_type` - Determines the model type ("embedding", "vision", or "text") based on the provided model path and configuration.
- Lines 252-278: function `unload_model` - Unloads the model identified by the given identifier using the LMS command, raising an error if the command is unavailable or unloading fails.
- Lines 280-295: function `wait_for_unload` - Waits for the model to be fully unloaded for a specified maximum duration, returning True if unloaded and False if the timeout is reached.
- Lines 297-339: function `load_model` - Loads a specified model from the given path into LM Studio, handling potential errors during the loading process and waiting for the model to be ready.
- Lines 341-412: function `ensure_model_for_request` - Ensures the correct model is loaded for a given request type by checking LM Studio availability, determining the target model based on the request, and switching models if necessary.
- Lines 419-424: function `get_model_manager` - Creates a singleton instance of the ModelManager, ensuring a single instance is available throughout the application.
- Lines 427-433: function `ensure_embedding_model` - Handles loading the embedding model for a request and returns the loaded model path.
- Lines 436-442: function `ensure_text_model` - Loads the text model and returns its path, ensuring it's available for the current request.
- Lines 445-451: function `ensure_vision_model` - Loads the vision model and returns its path, ensuring it's ready for a request.

---

### perspectives.py

**Lines:** 737

- Lines 104-110: class `Perspective` - Creates a synthesized perspective on a story by combining category, content, source articles, confidence, and generation timestamp.
- Lines 113-115: class `PerspectiveError` - Handles perspective errors by raising a specific exception when issues arise during perspective synthesis.
- Lines 118-120: class `InsufficientSourcesError` - Handles the case where insufficient articles are available to generate a perspective by raising an InsufficientSourcesError.
- Lines 123-125: class `CategoryNotApplicableError` - Creates a CategoryNotApplicableError when a requested category doesn't apply to the current story.
- Lines 128-130: class `LLMProviderError` - Handles errors originating from the LLM provider when a perspective cannot be generated.
- Lines 133-349: function `build_perspective_prompt` - Builds an LLM prompt for generating a specific perspective by assembling article information and category-specific instructions.
- Lines 352-424: function `estimate_confidence` - Estimates confidence in a synthesized perspective based on article count, recency, synthesis quality, and category-specific requirements, returning a score between 0 and 1.
- Lines 427-460: function `generate_fallback_perspective` - Generates a fallback perspective with limited information from articles, including titles and summaries when available, or just titles if only one article is provided.
- Lines 463-542: function `synthesize_perspective` - Generates a single perspective for a story cluster by synthesizing information from articles, prioritizing LLM synthesis with caching and falling back to a rule-based approach if necessary.
- Lines 545-670: function `synthesize_perspectives` - Generates multiple perspectives for a story cluster by leveraging LLMs and caching results, prioritizing batched processing when a gateway is available.
- Lines 673-688: function `is_cache_fresh` - Checks if a cached perspective is still fresh by comparing the time elapsed since generation to the specified time-to-live.
- Lines 691-708: function `get_user_perspective_config` - Retrieves the user's perspective configuration from storage, returning a dictionary containing enabled categories, default categories, and category order.
- Lines 711-737: function `update_user_perspective_config` - Updates a user's perspective configuration in storage by applying provided enabled categories, default categories, and category order.

---

### report.py

**Lines:** 2061

- Lines 53-70: function `_cosine_similarity` - Computes the cosine similarity between two vectors by calculating their dot product and magnitudes, handling cases of zero magnitude vectors and differing vector lengths.
- Lines 73-153: class `_get_eta` - Handles batch processing by iterating over items in chunks, providing progress updates and ETA predictions.
- Lines 86-95: function `__init__` - Initializes the object with total items, batch size, and a label, calculating the number of batches and initializing internal variables for batch processing.
- Lines 97-106: function `_get_eta` - Calculates and returns an estimated time of arrival string based on the average batch time and remaining batches.
- Lines 108-115: function `iterate` - Yields (batch number, batch) tuples for iterating over a list of items in batches.
- Lines 117-125: function `start_batch` - Starts a batch by recording the start time and displaying progress information with an estimated time of arrival.
- Lines 127-143: function `end_batch` - Calculates the duration of a batch by subtracting the current batch start time from the current time and appending it to a list of batch durations.
- Lines 145-153: function `summary` - Prints a final summary including total time, custom messages, processed counts, and error information.
- Lines 163-171: function `_cleanup_gateway` - Handles gateway cleanup by clearing the queue and unloading models to free VRAM.
- Lines 174-178: function `_signal_handler` - Handles interrupt signals by cleaning up resources and exiting the program.
- Lines 181-195: function `_register_cleanup` - Registers cleanup handlers, including an atexit handler and signal handlers for SIGINT and SIGTERM, ensuring they are executed only once.
- Lines 202-208: function `_make_progress_bar` - Creates a text-based progress bar displaying the completion ratio using '#' characters, with green color and dim gray for the remaining portion.
- Lines 211-390: function `show_step_progress` - Calculates the state of the corpus, identifying gaps in data like summaries, trends, signals, and embeddings for both existing and new articles.
- Lines 330-340: function `show_step_progress` - Displays progress information for a given label, completed tasks, and total tasks, including a progress bar, count, and percentage.
- Lines 397-537: function `story_to_text` - Embeds existing stories and insights using the specified embedding service, prioritizing insights for connection detection and initializing trend category embeddings.
- Lines 509-511: function `story_to_text` - Formats a story into a readable text string including title, description, and a comma-separated list of keywords.
- Lines 544-764: function `process_completed` - Generates summaries, insights, facts, and tags for articles by pipelining LLM requests to maintain concurrency and handle errors.
- Lines 592-604: function `submit_next` - Submits the next article from the processing queue for extraction, handling the submission and recording its status.
- Lines 606-731: function `process_completed` - Extracts insights and facts from an article's response, updating associated metadata and tracking processing statistics.
- Lines 771-806: function `_create_semantic_card` - Creates a structured text card for embedding by combining the article's title, summary, trend categories, and signal type information.
- Lines 809-943: function `_run_embedding_phase` - Embeds new articles using semantic cards, saving both averaged and chunk embeddings to the storage.
- Lines 950-1015: function `_cluster_insights_by_similarity` - Clusters insights based on embedding similarity using a greedy approach, grouping similar insights above a specified threshold into lists of (insight, embedding) tuples.
- Lines 1018-1057: function `build_cluster_analysis_prompt` - Builds a prompt for an LLM to analyze a cluster of insights, extracting themes, subcategories, and relationships in JSON format.
- Lines 1060-1170: function `parse_cluster_analysis_response` - Parses a cluster analysis response, extracts information about themes, subcategories, and relationships, and saves the extracted triples and connections to the knowledge base.
- Lines 1173-1201: function `_analyze_cluster_for_triples` - Analyzes a cluster of insights using a prompt to extract theme/relationship triples and saves them to the knowledge base.
- Lines 1204-1374: function `_run_connection_detection` - Detects connections by embedding new insights, clustering them by similarity, and analyzing each cluster with a text model to generate knowledge graph triples.
- Lines 1381-1477: function `_run_story_matching` - Matches articles to existing stories using semantic embeddings and creates new stories from articles lacking matches.
- Lines 1484-1703: function `generate_report` - Generates a comprehensive report by fetching articles, performing verification, leveraging an LLM for summaries and tags, embedding semantic cards, and matching articles to stories.
- Lines 1706-1955: function `_show_final_report` - Generates a concise intelligence briefing based on processed articles, user context, and knowledge graph updates, organized into sections for priority items, user interests, discovered connections, and knowledge graph changes.
- Lines 1958-2034: function `_score_articles_for_briefing` - Scores articles based on signal strength, user interest, novelty, and cross-referencing, providing a relevance reason for each score.
- Lines 2037-2051: function `_explain_relevance` - Matches article content to the user's tracked topics or current projects, providing a personalized relevance explanation.
- Lines 2054-2061: function `_article_matches_topic` - Checks if an article matches a given topic by searching the title, trend tags, and the first 500 characters of the content.

---

### rss.py

**Lines:** 127

- Lines 14-26: function `load_feeds` - Loads feed URLs from a specified file, returning an empty list if the file does not exist.
- Lines 29-31: function `generate_article_id` - Generates a 16-character SHA256 hash from an article link to create a unique article ID.
- Lines 34-52: function `parse_published_date` - Parses published or updated date information from a feed entry's parsed timestamp, handling potential errors and returning a datetime object or None if parsing fails.
- Lines 55-66: function `get_entry_content` - Extracts the most comprehensive text from a feed entry, prioritizing the 'content' field and falling back to the 'summary' or 'title' if necessary.
- Lines 69-106: function `fetch_feed` - Fetches and parses an RSS feed from a given URL, returning statistics about the operation including fetched articles, new articles saved, and any errors encountered.
- Lines 109-127: function `fetch_all_feeds` - Fetches all feeds from a specified file, loads them, and returns a list of dictionaries containing statistics for each feed.

---

### schema.py

**Lines:** 303

- Lines 18-21: class `ExtractedEntity` - Creates an ExtractedEntity object with a specified name and type, defaulting to "concept" if no type is provided.
- Lines 24-30: class `ExtractedInsight` - Creates an ExtractedInsight object with specified content, type, confidence, reason, and entities.
- Lines 33-35: class `InsightExtractionResult` - Handles article text to extract a list of insights, each containing specific information about the article's content.
- Lines 42-49: class `ExtractedTriple` - Extracts RDF-style triples from text, providing subject, predicate, and object components along with their types and confidence levels.
- Lines 52-54: class `TripleExtractionResult` - Extracts subject-predicate-object triples from an article chunk, returning a list of extracted triples.
- Lines 61-66: class `ExtractedEntityRelationship` - Creates a relationship object with source, target, and relationship details, optionally including associated properties.
- Lines 69-71: class `EntityRelationshipResult` - Creates a structured result containing a list of extracted entity relationships from input data.
- Lines 78-82: class `SignalTag` - Validates that the provided `tag` is a string and the `confidence` is a float between 0.0 and 1.0 (inclusive), with an optional `reason` string.
- Lines 85-88: class `SignalTagResult` - Validates signal tags and indicates whether an article is an advertisement or sponsored.
- Lines 95-99: class `SemanticChunk` - Creates a semantically coherent chunk of an article with content, insights, and triples.
- Lines 102-114: class `CombinedExtractionResult` - Creates a structured result containing semantic chunks, signal tags, and metadata like ad status, summary, headline, and keywords extracted from a single article.
- Lines 121-177: function `extract_json_from_response` - Extracts JSON from LLM responses by identifying and removing markdown code blocks or directly extracting JSON arrays/objects.
- Lines 180-203: function `parse_json_response` - Parses a JSON response string, attempting direct parsing and fallback extraction from markdown before raising a ValueError if parsing fails.
- Lines 206-231: function `parse_insights` - Parses a JSON response containing insights from an LLM, validating each insight and returning a list of ExtractedInsight objects.
- Lines 234-258: function `parse_triples` - Parses a JSON response containing triples into a list of validated `ExtractedTriple` objects, handling both array and dictionary formats.
- Lines 261-284: function `parse_signal_tags` - Parses a JSON response to extract and validate signal tags, handling both lists of tags and dictionaries containing an `is_ad` field.
- Lines 287-303: function `parse_combined_extraction` - Parses a raw LLM response containing chunks, insights, triples, tags, and a summary into a validated CombinedExtractionResult object.

---

### signal_tagger.py

**Lines:** 641

- Lines 23-90: class `SignalTags` - Formats signal tags into JSON and display-friendly strings, handling legacy data and providing methods to check for tag presence.
- Lines 33-35: function `to_json` - Serializes the object's attributes into a JSON string for persistent storage.
- Lines 38-44: function `from_json` - Deserializes a JSON string into a SignalTags object, handling legacy data by defaulting to 'is_ad' as False if the field is missing.
- Lines 46-55: function `to_display_string` - Formats tags for display by joining primary, well-sourced, balanced, reasoning, tone, and actionability attributes with square brackets.
- Lines 57-68: function `to_compact_string` - Formats tags into a compact, comma-separated string by removing duplicates while preserving order.
- Lines 70-79: function `has_any_tag` - Checks if any of the provided tags are present in the combined string of source type, evidence, reasoning, tone, and actionability.
- Lines 81-90: function `has_all_tags` - Validates if all provided tags are present within the combined string of source type, evidence, reasoning, tone, and actionability.
- Lines 93-600: class `SignalTagger` - Assigns signal tags to an article by analyzing its content for source type, evidence handling, reasoning quality, tone, actionability, and promotional intent.
- Lines 96-119: function `__init__` - Initializes the signal tagger with options for using a language model and specifying an LLM provider.
- Lines 121-134: function `tag_article` - Assigns signal tags to an article using either a language model or predefined rules, depending on the `use_llm` flag.
- Lines 136-168: function `_tag_with_rules` - Detects source type, evidence handling, reasoning quality, tone, actionability, and ad status from an article's title and content.
- Lines 170-220: function `_detect_source_type` - Detects source type by identifying patterns associated with satire, press releases, primary sources, secondary sources, aggregators, and speculation.
- Lines 222-262: function `_detect_evidence` - Detects evidence handling quality in text by analyzing source counts, documentation, links to primary sources, and mentions of anonymous or unverified claims, returning a list of relevant tags.
- Lines 264-293: function `_detect_reasoning` - Detects reasoning quality by identifying balanced perspectives, logical reasoning, and cherry-picking indicators in the input text.
- Lines 295-356: function `_detect_tone` - Detects tone and style by identifying patterns related to sensationalism, opinion, analytical depth, spiciness, and unhinged content.
- Lines 358-379: function `_detect_actionability` - Detects actionability in text by identifying patterns related to how-to guides, deadlines, recommendations, and actionable advice, or noise indicators like celebrity gossip and social media trends.
- Lines 381-416: function `_detect_is_ad` - Detects advertising content by searching for patterns related to product roundups, discounts, and sponsored content in both the title and text.
- Lines 418-431: function `_tag_with_llm` - Uses an LLM to generate context-aware tags for articles, falling back to rule-based tagging if the LLM call fails.
- Lines 433-480: function `tag_articles_batch` - Handles tagging multiple articles by submitting prompts to an LLM gateway in a batch and returning a list of corresponding SignalTags objects.
- Lines 482-515: function `_build_llm_prompt` - Constructs a JSON-formatted prompt for an LLM to analyze an article and assign relevant tags across categories like source type, evidence, reasoning, tone, actionability, and advertising status.
- Lines 517-576: function `_call_llm` - Handles user prompts by calling the configured LLM provider, attempting to utilize a gateway for LM Studio and falling back to a direct API call for other compatible providers.
- Lines 578-600: function `_parse_llm_response` - Parses an LLM JSON response to extract and structure SignalTags representing source type, evidence, reasoning, tone, actionability, and advertising status.
- Lines 603-641: function `tag_articles_batch` - Tags a batch of articles using a provided tagger, returning a dictionary mapping article IDs to their corresponding SignalTags.

---

### storage.py

**Lines:** 1091

- Lines 17-30: class `ArticleChunk` - Creates ArticleChunk objects with details like ID, article ID, chunk index, text, and an optional JSON-serialized embedding.
- Lines 34-49: class `Article` - Creates an Article object representing an RSS feed entry with attributes for its ID, URL, title, link, publication date, content, and optional summary, headline, keywords, trend tags, signal tags, and story ID.
- Lines 53-65: class `Story` - Handles story clusters by storing information such as ID, title, description, keywords, and associated article/news item IDs.
- Lines 69-81: class `NewsItem` - Creates a NewsItem object representing a piece of news information with attributes like ID, story ID, title, and confidence level.
- Lines 84-1091: class `Storage` - Initializes the SQLite database storage with a specified path and creates the necessary schema, including version tracking and migrations for articles, stories, news items, perspective cache, and user configuration tables.
- Lines 87-89: function `__init__` - Initializes the database path and calls the internal database initialization method.
- Lines 91-115: function `_init_db` - Initializes the database schema by creating a version tracking table and applying migrations if the current schema version is outdated.
- Lines 117-132: function `_run_migrations` - Runs schema migrations from a specified starting version to the current SCHEMA_VERSION, executing each migration idempotently.
- Lines 134-245: function `_migrate_to_v1` - Creates the initial database schema for articles, stories, news items, perspective cache, and user perspective configuration tables.
- Lines 247-264: function `_migrate_to_v2` - Migrates the database schema to version 2 by adding 'headline' and 'keywords' columns to the 'articles' table.
- Lines 266-289: function `_migrate_to_v3` - Creates an `article_chunks` table to store individual chunk embeddings for fine-grained subtopic analysis within articles.
- Lines 292-299: function `_connect` - Handles database connections by opening a connection, setting row factory, yielding the connection, and ensuring it is closed in a `finally` block.
- Lines 301-326: function `save_article` - Saves an article to the database, returning True upon successful insertion and False if the article already exists.
- Lines 328-336: function `get_article` - Retrieves an article by its ID from the database, returning the Article object if found, and None otherwise.
- Lines 338-359: function `get_articles_by_ids` - Retrieves multiple articles from the database by their IDs, preserving the order of the provided IDs and skipping any missing articles.
- Lines 361-388: function `get_articles` - Retrieves articles from a database, optionally filtering by feed URL, summarization status, and limiting the number of results.
- Lines 390-424: function `get_unanalyzed_articles` - Retrieves all unanalyzed articles from the database, optionally filtered by feed URL, spam status, and minimum content length, ordered by publication date.
- Lines 426-433: function `mark_as_analyzed` - Marks an article as analyzed by updating the `analyzed_at` field with the current timestamp for the given article ID.
- Lines 435-450: function `mark_short_articles_as_skipped` - Marks articles with insufficient content as analyzed by updating their `analyzed_at` field, returning the number of articles updated.
- Lines 452-467: function `get_articles_needing_embeddings` - Retrieves articles lacking embeddings, ordered by publication date, excluding those flagged as spam.
- Lines 469-476: function `save_embedding` - Saves a pre-computed embedding for a given article by updating the article's embedding in the database with the provided embedding and article ID.
- Lines 478-487: function `get_embedding` - Retrieves the pre-computed embedding for a given article ID from the database, returning the embedding as a list of floats if found, and None otherwise.
- Lines 491-529: function `save_chunk_embeddings` - Saves article chunk embeddings to a database, handling idempotency by deleting existing chunks for the given article ID before inserting new ones.
- Lines 531-546: function `get_chunk_embeddings` - Retrieves all article chunk embeddings for a given article ID, ordered by their chunk index.
- Lines 548-558: function `get_articles_with_chunks` - Retrieves distinct article IDs from the `article_chunks` table where an embedding is present.
- Lines 560-569: function `_row_to_chunk` - Converts a database row to an ArticleChunk object, extracting data like ID, article ID, chunk text, and embedding.
- Lines 571-586: function `get_articles_with_embeddings_not_analyzed` - Retrieves articles with embeddings that have not yet been analyzed, excluding spam articles if specified.
- Lines 588-595: function `update_summary` - Updates an article's summary in the database with the provided summary for the given article ID.
- Lines 597-604: function `update_trends` - Updates an article's trend tags in the database based on the provided article ID and trend tags.
- Lines 606-613: function `update_signal_tags` - Updates an article's signal tags in the database for the specified article ID using the provided signal tags.
- Lines 615-622: function `update_headline` - Updates an article's headline in the database with the provided headline for the given article ID.
- Lines 624-637: function `update_keywords` - Updates an article's keywords in the database by storing a JSON representation of the provided keyword list for the given article ID.
- Lines 639-681: function `get_articles_by_signal_tags` - Retrieves articles matching specified signal tags, including or excluding tags as provided, up to a defined limit.
- Lines 683-687: function `get_article_count` - Retrieves the total number of articles from the database by executing a SQL query and returning the count.
- Lines 689-702: function `get_feed_stats` - Retrieves article statistics (article count, summarized count, and latest publication date) for each feed URL by querying the articles table and grouping by feed URL.
- Lines 704-727: function `safe_get` - Converts a database row to an Article object, safely handling missing columns and providing default values where necessary.
- Lines 707-711: function `safe_get` - Handles column lookups in a row, returning the value if the column exists and is within bounds, otherwise returns None.
- Lines 729-736: function `update_article_story` - Updates an article's story association by setting the `story_id` in the `articles` table for the given `article_id`.
- Lines 740-767: function `save_story` - Saves a story to the database, returning True if the story is successfully inserted and False if a story with the same ID already exists.
- Lines 769-777: function `get_story` - Retrieves a story from the database by its ID, returning the Story object if found, otherwise returns None.
- Lines 779-804: function `get_active_stories` - Retrieves a list of active stories (not resolved), ordered by the most recent update, up to a specified limit.
- Lines 806-829: function `get_all_stories` - Retrieves stories from the database, optionally filtering by lifecycle state and limiting the number of results returned.
- Lines 831-853: function `update_story` - Updates a story's title, description, keywords, last updated timestamp, lifecycle state, article IDs, and news item IDs in the database based on the provided story object and its ID.
- Lines 855-862: function `update_story_title` - Updates the title of a story with the provided ID to the new title, ensuring data consistency.
- Lines 864-877: function `_row_to_story` - Converts a database row to a Story object, extracting data for id, title, description, keywords, timestamps, and IDs.
- Lines 881-908: function `save_news_item` - Saves a news item to the database, returning True upon successful insertion and False if the item already exists.
- Lines 910-921: function `get_news_items` - Retrieves all news items associated with a given story ID, sorted by their first seen timestamp.
- Lines 923-942: function `update_news_item` - Updates a news item in the database with the provided title, description, article IDs, item type, and confidence, using the item's ID to identify the record.
- Lines 944-957: function `_row_to_news_item` - Creates a NewsItem object from a database row containing information about a news item.
- Lines 961-1026: function `save_term_mention` - Updates or inserts a record in the term history table to track term mentions, article IDs, and categories for a given week bucket.
- Lines 1028-1051: function `get_term_history` - Retrieves historical mention counts for a specified term, limiting the results to the last `weeks_back` weeks.
- Lines 1053-1075: function `get_all_terms_with_history` - Retrieves all terms from the term_history table that have appeared in at least min_weeks distinct weeks.
- Lines 1077-1091: function `get_term_categories` - Retrieves all categories associated with a given term from the term history table.

---

### storage_perspectives.py

**Lines:** 213

- Lines 10-183: class `get_story_clusters` - Retrieves story clusters sorted by article count, with a minimum number of articles specified.
- Lines 17-18: function `__init__` - Initializes the object with a storage component to manage data persistence.
- Lines 20-39: function `get_story_clusters` - Retrieves story clusters from storage, filtering by minimum article count and sorting them by article count in descending order.
- Lines 41-51: function `get_story_cluster` - Retrieves a story cluster by ID, returning a dictionary containing its ID, title, creation date, and last updated date if found, otherwise returns None.
- Lines 53-66: function `create_story_cluster` - Creates a new Story object with the provided cluster ID and title, then saves it to storage.
- Lines 68-75: function `assign_to_cluster` - Assigns an article to a specified story cluster by updating the article's and story's data in the storage.
- Lines 77-82: function `update_cluster_timestamp` - Updates the `last_updated` timestamp of a specified cluster in the storage by retrieving the story, setting the timestamp to the current time, and updating the story in storage.
- Lines 84-91: function `get_articles_by_cluster` - Retrieves all articles associated with a given cluster ID from the database, ordered by publication date.
- Lines 93-102: function `delete_story_cluster` - Deletes a story cluster by unassigning articles, removing perspectives and the story itself from the database.
- Lines 104-111: function `get_old_story_clusters` - Retrieves story clusters with a creation date before the specified cutoff date.
- Lines 113-131: function `cache_perspective` - Inserts or replaces a synthesized perspective in the perspective_cache table with cluster ID, category, content, source articles, confidence, and generated timestamp.
- Lines 133-149: function `get_cached_perspective` - Retrieves a cached perspective based on the provided cluster ID and category, returning a Perspective object if found, otherwise returns None.
- Lines 151-155: function `invalidate_perspective_cache` - Invalidates all cached perspectives for a specified cluster by deleting entries from the `perspective_cache` table associated with that cluster's ID.
- Lines 157-167: function `get_perspective_config` - Retrieves the user's perspective configuration from the database, parsing enabled categories, default categories, and category order into dictionaries.
- Lines 169-183: function `save_perspective_config` - Saves the user's perspective configuration by inserting or replacing the configuration data in the database with enabled categories, default categories, and category order.
- Lines 187-213: function `add_perspective_methods` - Adds perspective-related methods to a Storage instance, enabling operations like retrieving story clusters, assigning items to clusters, and managing perspective caches.

---

### story_commands.py

**Lines:** 235

- Lines 17-62: function `cluster_command` - Clusters articles into stories and extracts news items from a specified number of unclustered articles using a chosen provider.
- Lines 65-122: function `stories_command` - Retrieves a list of stories with their associated articles and news items, optionally filtered by lifecycle state and limited in number.
- Lines 125-190: function `story_detail_command` - Retrieves and displays detailed information about a specific story, including its title, description, state, keywords, articles, and associated news items.
- Lines 193-235: function `evolution_command` - Updates story lifecycle states and retrieves evolution statistics to display state distributions and summary metrics.

---

### summarizer.py

**Lines:** 164

- Lines 6-11: class `SummarizerBackend` - Generates a summary of the input text, limiting the output to a maximum length of 150 characters.
- Lines 9-11: function `summarize` - Generates a summary of the input text, limited to a maximum length of 150 characters.
- Lines 14-54: class `summarize` - Extracts the first few sentences from a text string up to a specified maximum length, prioritizing sentence boundaries and truncating if necessary.
- Lines 20-54: function `summarize` - Extracts the first sentences from a text string up to a specified maximum length, prioritizing sentence boundaries and truncating if necessary.
- Lines 57-97: class `TransformerSummarizer` - Generates a concise summary of the input text using a pre-trained transformer model, handling potential errors and ensuring appropriate length constraints.
- Lines 63-65: function `__init__` - Initializes the model with a specified name and sets the pipeline to None.
- Lines 67-79: function `_load_pipeline` - Loads a summarization pipeline from Hugging Face Transformers, using the specified model name and raising an ImportError if the required libraries are missing.
- Lines 81-97: function `summarize` - Generates a concise summary of the input text using a transformer model, respecting a specified maximum length and ensuring a minimum length for coherence.
- Lines 100-109: function `get_summarizer` - Returns a summarizer backend, either a transformer-based model or a simple summarizer, based on the `use_llm` parameter.
- Lines 112-164: function `summarize_articles` - Summarizes unsummarized articles from storage, optionally using an LLM and assigning signal tags, and returns statistics on the processing, tagging, and errors encountered.

---

### trends.py

**Lines:** 391

- Lines 46-92: function `ensure_categories_initialized` - Initializes category embeddings in FAISS by retrieving existing embeddings or seeding new ones from text descriptions.
- Lines 95-119: function `_get_category_embeddings` - Retrieves category embeddings from a cache, fetching them from an embedding service if they don't already exist.
- Lines 122-150: function `categorize_by_stored_embedding` - Categorizes an article based on pre-computed category embeddings by finding categories with a cosine similarity above a threshold.
- Lines 153-181: function `categorize_text` - Logs a warning and returns "Uncategorized" if `categorize_text` is called, as it creates new embeddings instead of using pre-computed ones.
- Lines 184-225: function `analyze_article` - Retrieves an article's pre-computed embedding from storage and categorizes it using a provided embedding service.
- Lines 228-350: function `analyze_trends` - Analyzes article trends within a specified time window to identify popular categories, emerging topics, and declining trends.
- Lines 353-368: function `get_articles_by_trend` - Retrieves articles from storage that belong to a specified trend category, limiting the result to a maximum of 20 articles.
- Lines 371-391: function `llm_categorize` - Categorizes an article into one of the predefined categories by prompting an LLM with the article's title and content, returning "Uncategorized" if categorization fails.

---

### user_context.py

**Lines:** 683

- Lines 20-73: class `UserContextProfile` - Creates a UserContextProfile object with default timestamps if none are provided during initialization.
- Lines 42-47: function `__post_init__` - Initializes the `created_at` and `last_updated` attributes with the current timestamp if they are not already set.
- Lines 49-59: function `to_dict` - Converts the object's attributes to a dictionary, ensuring datetime objects are formatted as ISO strings for JSON serialization.
- Lines 62-73: function `from_dict` - Creates a UserContextProfile object from a dictionary, converting ISO formatted date strings to datetime objects.
- Lines 77-92: class `ArticleInteraction` - Records user interactions with an article, including expansion, time spent, saving, sharing, skipping, and feedback.
- Lines 95-353: class `clear_history` - Records user interactions with articles, including timestamps, engagement metrics, and preferences, for personalized recommendations and analysis.
- Lines 100-105: function `__init__` - Initializes the database connection using provided profile and database paths.
- Lines 107-132: function `_init_db` - Creates a database table for tracking user interactions with articles, including timestamps, engagement metrics, and article IDs.
- Lines 135-142: function `_connect` - Handles database connections by opening a connection, setting row factory to sqlite3.Row, yielding the connection, and ensuring the connection is closed in a `finally` block.
- Lines 144-165: function `load_profile` - Loads a user profile from a file, handling version migrations and errors to return a UserContextProfile object.
- Lines 167-180: function `save_profile` - Saves the user profile to a file on disk, creating necessary directories and handling versioning.
- Lines 182-186: function `_migrate_profile` - Migrates a profile from an older version to the current version by returning the input data unchanged.
- Lines 188-210: function `record_interaction` - Records user interactions with articles by inserting or replacing data in the `user_interactions` table with details like timestamp, engagement metrics, and user actions.
- Lines 212-246: function `get_interactions` - Retrieves user interaction history, optionally filtered by article ID and time range, and returns a list of ArticleInteraction objects.
- Lines 248-282: function `get_topic_engagement` - Calculates the engagement rate per topic over a specified number of days by querying user interactions and articles, then returns a dictionary mapping topics to their engagement rates.
- Lines 284-306: function `clear_history` - Clears user interaction history, optionally filtering by age, and returns the number of deleted records.
- Lines 308-330: function `export_data` - Exports user data, including profile and interaction history, to a dictionary format for backup and portability.
- Lines 332-353: function `import_data` - Imports user data from an exported dictionary, creating a UserContextProfile and recording article interactions.
- Lines 356-613: class `RelevanceEngine` - Calculates a relevance score for an article by weighing topic match, historical engagement, recency, and diversity, considering user personalization strength.
- Lines 367-374: function `__init__` - Initializes the object with a user context store and an optional embedding service, storing the provided dependencies for later use.
- Lines 376-419: function `calculate_relevance` - Calculates a relevance score for an article based on topic match, historical engagement, recency, and diversity, weighted by personalization strength and clamped to the range of 0 to 1.
- Lines 421-436: function `_extract_topics` - Extracts topics from an article by combining trend tags and keyword extraction from the title, returning a list of strings.
- Lines 438-507: function `_calculate_topic_match` - Calculates the relevance of a list of topics to a user profile by comparing embeddings against watching topics, current projects, pinned topics, and ignored topics, returning a similarity score between 0 and 1.
- Lines 509-520: function `_get_embedding` - Retrieves a pre-computed embedding for the given text from the cache if available, otherwise embeds the text using the embedding service and caches the result.
- Lines 522-563: function `_calculate_engagement_score` - Calculates an engagement score for a list of topics by finding similar historical topics and weighting their engagement rates by cosine similarity.
- Lines 565-575: function `_calculate_recency_boost` - Calculates a recency boost for topics based on recent user interactions, returning 0.5 if no recent interactions are found.
- Lines 577-598: function `_calculate_diversity_score` - Calculates a diversity score for topics by considering the novelty of each topic to prevent filter bubbles.
- Lines 600-613: function `apply_relevance_decay` - Applies decay to user context profile topics based on the number of days since the last interaction.
- Lines 616-646: function `sort_by_relevance` - Sorts articles by relevance score using a RelevanceEngine, prioritizing semantic similarity if an embedding service is available and falling back to substring matching otherwise.
- Lines 649-683: function `apply_diversity_filter` - Applies a diversity filter to a list of articles, ensuring a specified fraction of the recommendations are diverse content.

---

### utils.py

**Lines:** 46

- Lines 4-46: function `format_duration` - Formats a duration in seconds into a human-readable string representation, displaying seconds, minutes, hours, or days as appropriate.

---

### vector_index.py

**Lines:** 291

- Lines 21-24: class `SearchResult` - Creates a SearchResult object containing the target ID and the cosine similarity score.
- Lines 27-259: class `__init__` - Adds a vector to the specified target type's index, associating it with a unique ID and updating internal mappings.
- Lines 36-57: function `__init__` - Initializes the vector index with specified embedding dimensions and an optional directory for persisting indices.
- Lines 59-69: function `_get_or_create_index` - Creates a FAISS index for a given target type if one doesn't exist, using IndexFlatIP with the specified dimensions and storing its ID map.
- Lines 71-76: function `_normalize` - Normalizes a vector by dividing it by its L2 norm, ensuring a unit vector for cosine similarity calculations.
- Lines 78-130: function `add` - Adds a vector to the specified index, handling dimension mismatches and updating existing entries while maintaining reverse mappings.
- Lines 132-188: function `search` - Searches for similar vectors within a specified index, returning a list of ranked search results based on similarity scores and a defined threshold.
- Lines 190-195: function `contains` - Validates if a given target ID exists within the reverse map of a specified target type in the index.
- Lines 197-204: function `size` - Calculates the number of vectors within a specified index, returning 0 if the index doesn't exist.
- Lines 206-242: function `load_from_db` - Loads vectors from the SQLite knowledge_embeddings table for a specified target type, updating the FAISS index and dimensions as needed.
- Lines 244-259: function `clear` - Clears index data (indices, ID maps, reverse maps, next ID, and initialized types) based on the provided target type.
- Lines 267-282: function `get_vector_index` - Creates a global VectorIndex instance with the specified embedding dimensions if one doesn't already exist.
- Lines 285-291: function `reset_vector_index` - Resets the global vector index to None, ensuring a clean state for testing.

---

