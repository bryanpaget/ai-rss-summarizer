# Codebase Documentation

Generated: 2026-01-18 14:10:20
Directory: ./src
Files processed: 1

---



---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\cli_cross_source.py

**Lines:** 381 | **Estimated tokens:** ~3472

- Lines 1-2: global `module_docstring` - Module docstring
- Lines 3-4: function `example_function_xyz` - Example function
- Lines 8-10: import-block `typer` - Typer library for creating command-line interfaces.
- Lines 10-19: import-block `cross_source` - Imports functions related to cross-source analysis and feeds.
- Lines 20-23: class `sources.sources` - Typer application for managing RSS feeds and performing comparisons.
- Lines 24-25: class `sources.sources` - Console instance for rich output.
- Lines 27-29: function `sources.compare_sources` - Compare how different sources cover the same story, allowing for detailed analysis and identification of potential bias.
- Lines 30-31: function `sources.compare_sources` - Argument for specifying the database path.
- Lines 31-32: function `sources.compare_sources` - Option for specifying the database path.
- Lines 32-43: function `sources.compare_sources` - Arguments and docstring for the compare_sources command.
- Lines 44-45: class `sources.Storage` - Class for interacting with the database storage.
- Lines 46-451: function `sources.compare_sources` - Initializes the storage and knowledge base, then handles story comparison and output.
- Lines 49-51: function `sources.compare_sources` - Retrieves a specific story from the database, handling cases where the story is not found.
- Lines 56-57: function `sources.compare_sources` - Retrieves stories with multiple sources from the database, limiting the number of results.
- Lines 59-61: function `sources.compare_sources` - Handles the case where no stories with multiple sources are found, providing instructions on how to add feeds and run reports.
- Lines 68-123: function `sources.compare_sources` - Prints a panel title for the comparison output.
- Lines 78-101: function `sources.compare_sources` - Iterates through each story and compares its coverage across different sources, presenting detailed information about each source's perspective.
- Lines 109-112: function `sources.compare_sources` - Displays common facts agreed upon by multiple sources.
- Lines 114-119: function `sources.compare_sources` - Displays coverage gaps, highlighting information mentioned by some but not all sources.
- Lines 121-123: function `sources.compare_sources` - Prints a separator line.
- Lines 125-170: function `sources.suggest_sources` - Suggests diverse sources to balance the user's feed mix, considering different categories of political leaning.
- Lines 175-284: function `sources.suggest_sources` - Handles the logic for suggesting diverse sources based on category and provides instructions for adding suggested feeds.
- Lines 290-310: function `sources.add_suggested_sources` - Adds suggested diverse sources to the user's feeds, providing a dry-run option.
- Lines 315-380: function `sources.add_suggested_sources` - Handles the logic for adding suggested feeds and provides instructions for fetching articles from new feeds.

---


