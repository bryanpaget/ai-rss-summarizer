# Codebase Documentation

Generated: 2026-01-18 13:47:01
Directory: ./src
Files processed: 1

---



---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\cli_perspectives.py

**Lines:** 248 | **Estimated tokens:** ~2440

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-4: import-block `typing.Optional` - Imports Optional type from the typing module
- Lines 5-7: import-block `rich.console.Console` - Imports Console class from rich.console module
- Lines 8-11: global `console` - Initializes a Console object with specific settings
- Lines 12-12: function `add_perspective_commands` - Adds perspective-related commands to the CLI app
- Lines 16-38: function `perspectives` - Views synthesized perspectives on stories, taking arguments for story ID, categories, limit, update clusters, and database path
- Lines 17-18: argument `story_id` - Specifies a specific story cluster ID (optional)
- Lines 19-23: argument `categories` - Defines perspective categories to show (optional)
- Lines 24-27: argument `limit` - Sets the number of stories to display when no story ID is provided (defaults to 10)
- Lines 28-32: argument `update_clusters` - Updates story clusters before showing them (can be slow)
- Lines 34-38: argument `db_path` - Specifies the path to the database file (defaults to "articles.db")
- Lines 49-56: function `synthesize_perspectives` - Synthesizes perspectives for a given story ID, categories and storage object
- Lines 50-51: function `get_best_provider` - Retrieves the best LLM provider based on configuration
- Lines 53-54: function `get_user_perspective_config` - Gets user's perspective configuration from storage.
- Lines 63-68: global variable `cluster_stats` - Statistics of cluster update process
- Lines 75-78: argument `categories` - Splits comma separated categories string into a list. If none, uses default category config.
- Lines 80-84: global variable `invalid` - List of invalid categories based on available categories
- Lines 86-91: conditional statement `story_id` - Handles the scenario where a specific story ID is provided
- Lines 89-90: conditional statement `cluster` - Checks if the specified story cluster exists.
- Lines 95-97: conditional statement `articles` - Checks if there are any articles in the given cluster.
- Lines 101-121: global variable `perspectives` - Synthesizes perspectives for the specified story and categories, uses best LLM provider
- Lines 107-110: conditional statement `category not in perspectives` - Handles cases where a requested category does not have associated data.
- Lines 112-114: variable `perspective` - Retrieves the perspective content for the current category.
- Lines 115-116: global variable `conf_width`, `conf_bar` - Creates a confidence bar using ASCII characters based on the perspective's confidence level.
- Lines 123-135: conditional statement `story_id` - Handles the scenario where no specific story ID is provided
- Lines 124-127: conditional statement `clusters` - Checks if any stories are found
- Lines 131-134: conditional statement `articles` - Checks for articles in a cluster.
- Lines 136-139: global variable `perspectives` - Synthesizes perspectives for the specified story and categories, uses best LLM provider
- Lines 147-152: global variable `first_cat` - Gets perspective content of first requested category
- Lines 153-159: global variables `conf_width`, `conf_bar` - Creates confidence bar for the first category.
- Lines 160-161: function `cluster['id']` - Provides a link to view all perspectives for a specific story cluster.
- Lines 162-164: global variable `console` - Prints a final message and provides instructions on configuring perspective settings
- Lines 165-173: function `configure_perspectives` - Configures default perspective categories
- Lines 168-171: argument `db_path` - Specifies the path to the database file (defaults to "articles.db")
- Lines 174-179: global variable `config`, `current_defaults` - Gets current configuration from storage
- Lines 191-204: conditional statement `config.get('default_categories', DEFAULT_CATEGORIES)` - Uses configured default perspectives or provides defaults if no config exists
- Lines 206-207: global variable `current_defaults` - Provides example for using specific categories via command line arguments
- Lines 208-239: function `cluster_stories` - Clusters articles into story groups, with options to force re-clustering.
- Lines 211-214: argument `force` - Forces re-clustering of all articles (defaults to False)
- Lines 215-219: argument `db_path` - Specifies the path to the database file (defaults to "articles.db")
- Lines 223-226: function `update_story_clusters` - Updates story clusters in the database
- Lines 233-241: global variables `stats` - Stores and prints statistics about the clustering process.
- Lines 237-239: variable `stats` - Prints statistics after cluster stories is complete

---


