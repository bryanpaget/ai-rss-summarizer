# Project Documentation

Generated: 2026-01-19 01:22:33

**Stats:** 2 files, 41 functions, 2 classes, ~2314 lines

**Cache:** 0 cached, 43 new, 0 changed

**Timing:** 50.3s LLM time

---

## System Overview

## Architecture Overview: Local Codebase Explorer

**1. Purpose:** This project automates the exploration and documentation of local Python codebases. It leverages static analysis and large language models (LLMs) to extract information about code structure, functions, classes, and their functionalities, ultimately generating a comprehensive overview of the project.

**2. Key Modules:**

*   **`local-codebase-explorer.py`**: This is the core module responsible for orchestrating the codebase analysis process. It likely handles parsing, data extraction from the codebase, and interaction with the LLM.
*   **`document-by-function.py`**:  This module focuses on generating documentation by extracting details about individual functions, classes, imports, and assignments within the code. It's a key component in building the overall project overview.
*   *(Assuming other files exist but are less significant based on file size)*: Other files likely contain helper functions for parsing specific code elements (e.g., AST parsing), LLM interaction utilities, or data processing routines.

**3. Entry Points:** The entry point is likely `local-codebase-explorer.py`. This script probably initiates the analysis process by specifying the codebase to be explored and orchestrating the calls to other modules for parsing, documentation generation, and LLM integration.

**4. Languages/Stack:** Python 3.x.  The project utilizes static analysis techniques (likely leveraging Python's built-in `ast` module or similar) and integrates with Large Language Models (LLMs) for natural language generation and summarization of code functionality.


---

## File Documentation

### document-by-function.py

**Lines:** 770

**Summary:** The `document-by-function.py` module automates the process of generating documentation for Python codebases by extracting information about functions, classes, imports, and assignments. Its primary purpose is to create a comprehensive overview of a project's functionality, leveraging large language models (LLMs) for concise descriptions. The module identifies Python files within a specified directory structure, excluding common project artifacts like virtual environments and version control directories.  It then extracts relevant code snippets from these files using `extract_functions` and `extract_nested_functions`. A key component is the `describe_function` function which uses prompt engineering to generate one-sentence summaries of each function's purpose. The module utilizes a caching mechanism (`load_cache`, `save_cache`) to avoid redundant LLM calls for already processed code, improving efficiency.  It employs an LLM gateway (`call_llm`) with retry logic and exponential backoff to handle potential failures during LLM interactions. Finally, the `process_directory` function orchestrates the entire process, building a work queue for concurrent LLM processing and returning structured data containing filepaths, extracted functions, descriptions, and timing information via `process_item`. The module relies on an external LLM gateway and potentially uses prompt templates to guide the language model's output.

**Functions/Classes:**

- Lines 27-32: function `load_cache` - Loads cached function descriptions from a JSON file if it exists, otherwise returns an empty dictionary.
- Lines 35-39: function `save_cache` - Saves the provided cache data to a JSON file in a designated directory.
- Lines 42-44: function `hash_code` - Generates a short MD5 hash of the input code string for change detection by returning the first 8 characters of the hexadecimal digest.
- Lines 47-119: function `extract_functions` - Extracts information about functions, classes, imports, and assignments from a Python file's source code, including their line numbers and code.
- Lines 122-124: class `LLMError` - Handles errors that occur when an LLM call fails after multiple retry attempts.
- Lines 127-156: function `call_llm` - Handles calling an LLM via a gateway with retry logic and exponential backoff, returning the response and LLM processing time upon success.
- Lines 159-161: function `estimate_tokens` - Estimates the number of tokens in a given text by dividing the text length by approximately 4 characters per token.
- Lines 164-193: function `extract_nested_functions` - Extracts nested functions from a given code string, identifying their name, type (function or method), and line numbers relative to the parent function.
- Lines 196-259: function `describe_function` - Parses a Python function's code using a sandwich prompt to generate a concise, one-sentence description of its functionality.
- Lines 262-333: function `process_file` - Processes a file by extracting functions, determining their status (new, changed, or cached), and updating a cache with their hashes and descriptions.
- Lines 336-349: function `find_python_files` - Finds all Python files within a specified directory and its subdirectories, excluding specified patterns like virtual environments and version control directories, then returns them in sorted order.
- Lines 352-422: function `generate_overview` - Generates a system architecture overview prompt for a large Python project, including statistics and file summaries, to guide a language model in creating a concise architectural document.
- Lines 425-723: function `process_directory` - Handles Python files in a directory by extracting functions, building a work queue for LLM processing, and executing the LLM calls concurrently.
- Lines 497-504: function `process_item` - Returns a filepath, function, description, and timing information including the total execution time of the function.
- Lines 726-770: function `main` - Processes Python files or directories to generate documentation, including function names, descriptions, and status, optionally saving the output to a file.

---

### local-codebase-explorer.py

**Lines:** 1544

**Summary:** The `local-codebase-explorer.py` module is designed to analyze and document a local codebase using a combination of static analysis techniques and large language models (LLMs). Its primary purpose is to automatically extract information about code structure, functions, classes, and their functionalities, ultimately generating comprehensive documentation for the project. The module operates by first identifying processable files within a specified directory, prioritizing those with text-like content or known programming language extensions. It then employs tree-sitter parsing for structured languages like Python and falls back to AST parsing or LLM analysis for other file types.

A core functionality involves extracting code units – individual blocks of code – from these files, along with relevant metadata such as line numbers and type information. The module leverages LLMs through various backends (gateway, LM Studio, OpenAI) to generate descriptions for these code units, aiming to summarize their purpose and functionality. It also analyzes the overall file structure by identifying sections and calculating appropriate summary lengths based on factors like line count and function density. Furthermore, it generates high-level overviews of the codebase by synthesizing information from individual file summaries, function/class counts, and content analysis.

Key components include functions for detecting file types (`is_text_file`, `get_language_for_file`), extracting code units (`extract_with_treesitter`, `extract_with_python_ast`, `extract_from_file`), and interacting with LLM backends (`_call_gateway`, `_call_lmstudio`, `_call_openai`, `call_llm`). The `generate_file_summaries` function is central to this process, creating concise overviews for each file.  The module maintains a cache of previously generated descriptions to improve efficiency and avoid redundant LLM calls. It also incorporates error handling (`LLMError`) and retry mechanisms for robust LLM interactions. Dependencies include libraries like tree-sitter for parsing various programming languages and potentially external APIs for LLM services. The final stage involves writing the collected information, including statistics, overviews, and detailed function/class descriptions, to an output file.  The module's architecture is designed to be extensible, allowing for different LLM backends and customization of documentation generation strategies.

**Functions/Classes:**

- Lines 63-75: function `_log_llm_exchange` - Logs the timestamp, timing, prompt (truncated if necessary), and response to a file for debugging purposes.
- Lines 367-372: function `load_cache` - Loads cached function descriptions from a JSON file, returning an empty dictionary if the file doesn't exist.
- Lines 375-379: function `save_cache` - Saves the provided cache data to a JSON file in a designated directory.
- Lines 382-384: function `hash_code` - Generates an 8-character MD5 hash of the input code string for change detection.
- Lines 391-394: function `get_language_for_file` - Returns the tree-sitter language name for a given file path based on its extension, or None if the extension is not supported.
- Lines 397-498: function `extract_with_treesitter` - Parses a code file using tree-sitter, extracting code units with their name, type, start and end lines, and the code itself.
- Lines 505-579: function `extract_with_python_ast` - Parses a Python file's AST to extract information about module docstrings, imports, functions, classes, and top-level assignments, including their line numbers and code.
- Lines 586-588: class `LLMError` - Handles errors that occur when an LLM call fails after multiple retry attempts.
- Lines 596-606: function `configure_llm` - Configures the LLM backend by setting the backend type and any associated configuration parameters.
- Lines 609-647: function `_detect_llm_backend` - Detects the available LLM backend (gateway, LM Studio, or OpenAI) by attempting to import necessary libraries or connect to specific endpoints, and raises an error if none are found.
- Lines 650-654: function `_call_gateway` - Handles user prompts by calling an LLM through a project gateway and returning the LLM's text response.
- Lines 657-670: function `_call_lmstudio` - Calls the LM Studio API with a given prompt to generate text, returning the model's response.
- Lines 673-687: function `_call_openai` - Calls the OpenAI API with a given prompt to generate a text completion, using the configured API key, model, and temperature.
- Lines 690-733: function `call_llm` - Handles calling an LLM with retry logic and exponential backoff, selecting the appropriate call function based on the configured backend.
- Lines 736-738: function `estimate_tokens` - Estimates the number of tokens in a given text by dividing the text length by approximately 4 characters per token.
- Lines 741-792: function `describe_code_unit` - Generates a concise description of a code unit by prompting an LLM to summarize its functionality, considering the language, type, and code itself.
- Lines 795-885: function `analyze_text_file_with_llm` - Analyzes a text file using an LLM to identify sections and their corresponding line numbers, returning a list of dictionaries describing the file's structure.
- Lines 892-936: function `extract_from_file` - Extracts code units from a file by attempting tree-sitter parsing, falling back to AST parsing for Python files and LLM analysis for other text-based files.
- Lines 939-954: function `is_text_file` - Validates whether a file is likely a text file by checking for null bytes and attempting UTF-8 decoding.
- Lines 961-985: function `find_files` - Finds all processable files within a given directory, excluding specified patterns and prioritizing files with known extensions or text-like content.
- Lines 992-1212: function `process_item` - Processes files in a directory by extracting code units, building a work queue for LLM descriptions, and concurrently generating descriptions while managing a cache.
- Lines 1080-1088: function `process_item` - Processes a code unit by measuring its execution time and returning the filepath, unit, description, and timing information.
- Lines 1215-1234: function `calculate_summary_length` - Calculates a target length range (minimum and maximum sentences) for a file summary based on line count and function density, ensuring reasonable bounds.
- Lines 1237-1308: function `generate_file_summaries` - Generates proportional summaries for each file in a directory by analyzing function descriptions and using a language model to create concise overviews.
- Lines 1311-1391: function `generate_overview` - Generates a system architecture overview by analyzing file summaries, function/class counts, and file content, then uses a language model to create a concise description.
- Lines 1394-1434: function `write_output` - Writes project documentation to a specified file, including statistics, overview, and detailed information about each file's functions and classes.
- Lines 1437-1499: function `file_mode` - Parses a file's structure into units, optionally generating descriptions for each unit in a hook-compatible format.
- Lines 1502-1544: function `main` - Processes a directory of code files, extracting functions and classes and optionally generating descriptions using an LLM.

---

