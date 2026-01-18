# Codebase Documentation

Generated: 2026-01-18 14:22:19
Directory: ./src
Files processed: 1

---



---

# File-by-File Documentation
## ers\jpswi\personal projects\RSSsummarizer\src\cli_cross_source.py

**Lines:** 381 | **Estimated tokens:** ~3472

- Lines 1-2: global `module_docstring` - Module docstring
- Lines 3-23: function `typer.Typer` - Initialize the typer application with a name and help message.
- Lines 24-25: constant `console` - Create a Rich Console object for outputting formatted text to the terminal.
- Lines 27-123: function `compare_sources` - Compare how different sources cover the same story, showing perspectives, framing, and emphasized facts.
- Lines 27-43: class `compare_sources` - Command to compare stories across multiple sources.
- Lines 44-64: function `compare_sources` - Implementation of the compare_sources command.
- Lines 69-123: function `compare_story_coverage` - Compare coverage of a given story across different sources, including bias indicators, framing, and key claims.
- Lines 127-140: function `list_multi_source_stories` - List stories covered by multiple sources, providing a summary of their coverage.
- Lines 140-170: class `list_multi_source_stories` - Command to list stories with multiple source coverage.
- Lines 175-240: function `suggest_sources` - Suggest diverse news sources based on the specified category, considering existing feeds and avoiding duplicates.
- Lines 244-294: class `suggest_sources` - Command to suggest diverse news sources to add to the user's feeds.
- Lines 299-360: function `add_suggested_sources` - Add suggested diverse sources to the user's feeds, with an option for dry-run mode.
- Lines 364-381: function `list_diverse_sources` - List all available diverse news sources in the database, categorized by political leaning.

---


