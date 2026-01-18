# Codebase Documentation

Generated: 2026-01-18 14:08:14
Directory: ./src
Files processed: 1

---



---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\cli_cross_source.py

**Lines:** 381 | **Estimated tokens:** ~3472

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-4: function `add` - Adds two numbers
- Lines 8-10: import-block `typer` - Typer library for creating command-line interfaces.
- Lines 11-19: import-block `cross_source` - Imports functions related to cross-source analysis.
- Lines 21-23: function `compare_sources` - Compare how different sources cover the same story.
- Lines 25-25: variable `app` - Typer application instance.
- Lines 27-43: function `compare_sources` - Compare how different sources cover the same story.
- Lines 44-45: variable `storage` - Storage instance for database operations.
- Lines 45-46: variable `kb` - KnowledgeBase instance for knowledge base operations.
- Lines 48-52: function `compare_sources` - Retrieves a specific story from the database if a story ID is provided, or finds stories with multiple sources.
- Lines 56-57: function `compare_sources` - Finds stories covered by multiple sources.
- Lines 59-61: function `compare_sources` - Handles the case where no stories with multiple sources are found.
- Lines 67-71: function `compare_sources` - Prints a title and starts iterating through stories with multiple sources.
- Lines 72-101: function `compare_sources` - For each story, compares its coverage across different sources and prints the results.
- Lines 102-105: function `compare_sources` - Prints common facts, coverage gaps, and a separator.
- Lines 107-123: function `list_multi_source_stories` - List stories covered by multiple sources.
- Lines 127-129: function `list_multi_source_stories` - Takes minimum sources and limit as arguments.
- Lines 138-140: variable `storage` - Storage instance for database operations.
- Lines 140-142: function `list_multi_source_stories` - Retrieves stories covered by multiple sources.
- Lines 142-144: function `list_multi_source_stories` - Handles the case where no stories with multiple sources are found.
- Lines 146-151: function `list_multi_source_stories` - Creates a table to display the list of stories and their sources.
- Lines 151-169: function `list_multi_source_stories` - Populates the table with story titles, source counts, article IDs, and provides instructions for detailed comparison.
- Lines 171-173: function `suggest_sources` - Suggest diverse sources to balance feed mix.
- Lines 173-174: function `suggest_sources` - Takes a category and feeds file as arguments.
- Lines 175-285: function `suggest_sources` - Analyzes current feeds and recommends sources from underrepresented perspectives based on the given category.
- Lines 286-292: function `suggest_sources` - Provides instructions for adding suggested feeds.
- Lines 297-305: function `add_suggested_sources` - Add suggested diverse sources to your feeds.
- Lines 305-306: function `add_suggested_sources` - Takes category, feeds file, and a dry-run flag as arguments.
- Lines 306-358: function `add_suggested_sources` - Adds suggested sources to the specified feeds file, with an option for a dry run.
- Lines 360-362: function `list_diverse_sources` - List all available diverse sources in the database.
- Lines 362-363: function `list_diverse_sources` - No arguments.
- Lines 363-381: function `list_diverse_sources` - Lists diverse sources categorized by left, center, and right political leanings.
- Lines 381-387: function `list_diverse_sources` - Provides instructions for using the suggested sources feature.

---


