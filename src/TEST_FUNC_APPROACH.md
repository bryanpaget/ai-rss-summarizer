# Documentation: ./src/cli_cross_source.py

- Lines 1-1: global `module_docstring` - Module docstring
- Lines 3-10: import-block `imports` - Module imports
- Lines 20-23: constant `app` - ```python
- Lines 24-24: constant `console` - `console` is a `Console` object configured to force output to the terminal and maintain compatibility with older Windows console implementations, ensuring consistent display of program output regardless of the environment.
- Lines 28-122: function `compare_sources` - function compares the coverage of a given story from multiple sources (either a specific story ID or stories with multiple sources) by retrieving the story, comparing its coverage across those sources using a `compare_story_coverage` function, and presenting the results in a formatted output.
- Lines 126-168: function `list_multi_source_stories` - function retrieves and displays a list of stories that have been covered by a specified minimum number of unique news sources, showing the story title, number of sources, number of articles, and ID, with an option to perform detailed cross-source comparison for each story.
- Lines 172-238: function `show_balance` - function analyzes a user's subscribed feeds from a specified file, calculates their political leanings (left, center, right, unknown), and displays the distribution as a colorful table with counts and percentages, along with a brief assessment of the overall balance.
- Lines 242-293: function `suggest_sources` - function analyzes a user's current RSS feeds and suggests diverse sources from left, center, or right perspectives to balance their feed mix, displaying the suggested sources with their names, leanings, and URLs.
- Lines 297-357: function `add_suggested_sources` - function adds suggested diverse news sources to a specified category in a feeds file, with an option for a dry run to preview the changes before applying them.
- Lines 361-381: function `list_diverse_sources` - function displays a categorized list of diverse news sources (left, center, and right) with their names, political leanings, and URLs, using color-coded headings for easy navigation.
