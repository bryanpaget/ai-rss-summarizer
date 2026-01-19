# Project Documentation

Generated: 2026-01-18 23:39:56

**Stats:** 5 files, 89 functions, 6 classes, ~4353 lines

**Cache:** 0 cached, 96 new, 0 changed

**Timing:** 360.9s LLM time

---

## System Overview

## Architecture Overview

**1. Purpose:** This project focuses on extracting information from code files using a Large Language Model (LLM), with an emphasis on quality assessment and caching for efficiency. It includes tools for loading/saving LLM interactions, extracting code elements, running quality tests, and managing the execution environment.

**2. Key Modules:**

*   **`document-by-function.py`**:  This module handles core logic related to interacting with an LLM to extract information from code. It manages caching of LLM responses and provides functions for hashing code and calling the LLM.
*   **`local-codebase-explorer.py`**: This module likely acts as a central hub, orchestrating the extraction process.  It handles logging, caching, and determining the appropriate language for processing files within a codebase.
*   **`quality_test_harness.py`**: This module is responsible for defining and executing quality tests on extracted data. It includes classes to manage test runs, extract different types of information (single/combined tasks), and calculate quality metrics.
*   **`safe-model-load.sh`**:  This shell script manages the loading and execution of the LLM model, including logging and error handling.

**3. Entry Points:** The execution likely begins with the `safe-model-load.sh` script, which sets up the environment for running the LLM and potentially invokes other Python modules to perform extraction or testing.  The exact entry point depends on how the scripts are invoked.

**4. Languages/Stack:**

*   **Python:** Primarily used for core logic, data processing, and interacting with the LLM.
*   **Bash:** Used for shell scripting, specifically managing the LLM model loading and execution environment (`safe-model-load.sh`).





---

## File Documentation

### document-by-function.py

**Lines:** 770

- Lines 27-32: function `load_cache` - Loads cached function descriptions from a JSON file if it exists, otherwise returns an empty dictionary.
- Lines 35-39: function `save_cache` - Saves the provided cache data to a JSON file in a designated directory.
- Lines 42-44: function `hash_code` - Generates an 8-character MD5 hash of the input code string for change detection.
- Lines 47-119: function `extract_functions` - Extracts information about functions, classes, imports, and assignments from a Python file by parsing its Abstract Syntax Tree (AST), including line numbers for each element.
- Lines 122-124: class `LLMError` - Handles errors that occur when an LLM call fails after multiple retry attempts.
- Lines 127-156: function `call_llm` - Handles calling an LLM via a gateway with retry logic and exponential backoff, returning the response and LLM processing time upon success.
- Lines 159-161: function `estimate_tokens` - Estimates the number of tokens in a given text by dividing the text length by approximately 4 characters per token.
- Lines 164-193: function `extract_nested_functions` - Extracts nested functions from a given code string, excluding the parent function itself, and returns a list of dictionaries containing information about each nested function's name, type, location, and code.
- Lines 196-259: function `describe_function` - Parses a Python function's code using a sandwich prompt to generate a concise, one-sentence description of its functionality.
- Lines 262-333: function `process_file` - Processes a file by extracting functions, determining their status (new, changed, or cached), and updating a cache with their hashes and descriptions.
- Lines 336-349: function `find_python_files` - Finds all Python files within a specified directory and its subdirectories, excluding specified patterns, and returns them in sorted order.
- Lines 352-422: function `generate_overview` - Generates a system architecture overview prompt for a large language model, including project statistics and file summaries, to facilitate the creation of a concise architectural document.
- Lines 425-723: function `process_item` - Processes Python files in a directory by extracting functions, building a work queue for LLM processing, and executing the LLM calls concurrently to generate descriptions.
- Lines 497-504: function `process_item` - Handles a function item by measuring its execution time and returning the filepath, function, description, and timing information.
- Lines 726-770: function `main` - Processes Python files or directories to generate documentation, including function names, descriptions, and status, optionally saving the output to a file.

---

### local-codebase-explorer.py

**Lines:** 1184

- Lines 64-76: function `_log_llm_exchange` - Logs the timestamp, timing, prompt (truncated if necessary), and response to a file for debugging purposes.
- Lines 211-216: function `load_cache` - Loads cached function descriptions from a JSON file if it exists, otherwise returns an empty dictionary.
- Lines 219-223: function `save_cache` - Saves the provided cache data to a JSON file in a designated directory, ensuring the directory exists.
- Lines 226-228: function `hash_code` - Generates an 8-character MD5 hash of the input code string for change detection.
- Lines 235-238: function `get_language_for_file` - Returns the tree-sitter language name for a given file path based on its extension, or None if the extension is not supported.
- Lines 241-342: function `extract_with_treesitter` - Parses a code file using tree-sitter, extracting code units with their name, type, start and end lines, and the code itself.
- Lines 349-423: function `extract_with_python_ast` - Extracts information about functions, classes, imports, and assignments from a Python file by parsing its Abstract Syntax Tree (AST), including line numbers for precise location.
- Lines 430-432: class `LLMError` - Handles errors that occur when an LLM call fails after multiple retry attempts.
- Lines 440-450: function `configure_llm` - Configures the LLM backend by setting the backend type and any associated configuration parameters.
- Lines 453-491: function `_detect_llm_backend` - Detects the available LLM backend (gateway, LM Studio, or OpenAI) by attempting to import necessary libraries or connect to specific endpoints.
- Lines 494-498: function `_call_gateway` - Calls an LLM via the project gateway using the provided prompt and returns the generated text.
- Lines 501-514: function `_call_lmstudio` - Calls the LM Studio API with a given prompt to generate text, returning the model's response.
- Lines 517-531: function `_call_openai` - Calls the OpenAI API with a given prompt to generate a text completion, using the configured API key, model, and temperature.
- Lines 534-577: function `call_llm` - Handles calling an LLM with retry logic and exponential backoff, selecting the appropriate call function based on the configured backend.
- Lines 580-582: function `estimate_tokens` - Estimates the number of tokens in a given text by dividing the text length by approximately 4 characters per token.
- Lines 585-636: function `describe_code_unit` - Generates a concise description of a code unit by prompting an LLM to summarize its functionality.
- Lines 639-724: function `analyze_text_file_with_llm` - Analyzes a text file using an LLM to identify sections and their corresponding line numbers, returning a list of dictionaries describing each section.
- Lines 731-775: function `extract_from_file` - Extracts code units from a file by attempting tree-sitter parsing, falling back to AST parsing for Python files and LLM analysis for other text-based files, returning the results and the extraction method used.
- Lines 778-793: function `is_text_file` - Validates whether a file is likely a text file by checking for null bytes and attempting UTF-8 decoding.
- Lines 800-824: function `find_files` - Finds all processable files within a specified directory, excluding specified patterns and prioritizing files with known extensions or text-like content.
- Lines 831-1047: function `process_directory` - Processes files in a directory by extracting code units, building a work queue for LLM descriptions, and concurrently generating descriptions while managing caching and error handling.
- Lines 919-927: function `process_item` - Processes a code unit by measuring its execution time and returning the filepath, unit, description, and timing information.
- Lines 1050-1115: function `generate_overview` - Generates a system architecture overview prompt for a codebase, including project statistics and file summaries, to guide a language model in creating a concise architectural description.
- Lines 1118-1149: function `write_output` - Writes project documentation to a specified output file, including statistics, overview, and detailed file-level information with line-by-line annotations.
- Lines 1152-1184: function `main` - Processes a directory to extract functions and classes from files, optionally writing the results to an output file and controlling processing parameters like concurrency and verbosity.

---

### quality_test_harness.py

**Lines:** 377

- Lines 34-42: class `ExtractionResult` - Creates a data structure containing the results of a single extraction run, including metrics like insight, triple, and tag counts, along with execution time and raw output.
- Lines 46-52: class `QualityMetrics` - Defines quality metrics for evaluating insights based on specificity, accuracy, relevance, and summary quality, culminating in an overall score.
- Lines 56-61: class `TestRun` - Handles the storage of results and metrics from a complete test run, including article title, timestamp, and extracted data.
- Lines 64-95: function `get_sample_article` - Creates a sample Article object with predefined details for testing purposes.
- Lines 98-152: function `extract_single_task` - Handles a specified extraction task (insights, triples, tags, or summary) from an article using a language model and returns the parsed JSON response.
- Lines 155-185: function `extract_combined` - Handles multiple extraction tasks (insights, triples, tags, summary) on an article using a language model and returns a JSON object containing the extracted information.
- Lines 188-256: function `run_extraction_test` - Runs extraction tasks in a specified mode, collecting insights, triples, tags, and summary results and returning them with timing information.
- Lines 259-350: function `run_quality_test` - Runs a quality test suite on an article, iterating through multiple modes to extract insights, triples, and tags, and optionally saves the results to a file.
- Lines 277-279: class `GatewayWrapper` - Handles text generation by sending a prompt to a gateway and returning the generated text.
- Lines 278-279: function `generate` - Returns text generated by the gateway based on the provided prompt and a specified maximum token limit.
- Lines 353-377: function `main` - Handles quality testing of articles by reading content from a file, then running the test specified number of times and saving results to a JSON file.

---

### safe-model-load.sh

**Lines:** 1860

- Lines 55-61: function `log` - Handles logging messages with a timestamp to a file and optionally to standard error, based on the VERBOSE variable.
- Lines 63-67: function `log_error` - Handles errors by logging a timestamped message to a file and printing it to standard error.
- Lines 70-79: function `log_stderr` - Handles standard error output by logging it with a timestamp to a file and optionally displaying it to the console if verbose mode is enabled.
- Lines 85-115: function `cleanup_old_pipes` - Handles stale pipe files in the specified directory by removing those older than a defined age, logging any errors encountered.
- Lines 117-128: function `create_request_pipe` - Creates a named pipe with a path based on the provided request ID and returns the pipe's path.
- Lines 134-154: function `is_processor_alive` - Verifies if a process is running by checking for a PID file and confirming the process ID is valid.
- Lines 156-182: function `is_heartbeat_stale` - Validates if the heartbeat file has been updated within the specified threshold, returning 0 if stale and 1 if recent.
- Lines 184-213: function `should_spawn_processor` - Determines whether to spawn a new processor by checking if the queue is empty or if the current processor is alive based on heartbeat and PID status.
- Lines 219-232: function `get_config` - Retrieves a configuration value from a file, using a provided default if the key is not found or the read fails.
- Lines 238-249: function `get_embedding_batch_size` - Retrieves the embedding batch size from a file, validating it against a range and returning a default value if the file is not found or contains an invalid size.
- Lines 251-262: function `set_embedding_batch_size` - Handles the setting of the embedding batch size by validating a provided size against minimum and maximum values, then persists the chosen size to a file.
- Lines 264-320: function `get_memory_usage` - Calculates the system's memory usage percentage (0-100) by querying system information on Linux, Windows, or macOS.
- Lines 322-347: function `check_memory_before_batch` - Handles memory usage by reducing the embedding batch size if memory exceeds a critical threshold, returning the adjusted batch size.
- Lines 349-383: function `adjust_batch_size_on_success` - Handles memory usage by adjusting the embedding batch size upwards if memory is available and downwards if memory is critically high.
- Lines 385-401: function `adjust_batch_size_on_failure` - Handles failed embedding batches by decreasing the batch size to a minimum value, logging the change.
- Lines 407-409: function `check_lm_studio` - Handles checking the availability of models from the LM Studio API by retrieving the models list and suppressing output.
- Lines 415-439: function `get_lms_ps_cached` - Retrieves the cached LMS PS result if it's within the specified time-to-live, otherwise refreshes the cache by running the LMS PS command and storing the output in a file.
- Lines 441-443: function `invalidate_lms_ps_cache` - Handles the removal of the LMS PS cache file specified by the LMS_PS_CACHE_FILE variable.
- Lines 445-451: function `get_loaded_model` - Retrieves the path to the loaded language model from `lms` if available, otherwise retrieves the model ID from the cached data.
- Lines 453-459: function `get_loaded_model_identifier` - Retrieves the model identifier from either the `lms` command or the `data.id` field in `get_lms_ps_cached`, prioritizing the `lms` command if available.
- Lines 461-486: function `get_current_model_type` - Determines the current model type (text, vision, or embedding) by checking loaded configuration settings.
- Lines 488-504: function `wait_for_unload` - Waits for a process to unload, checking the process list periodically for a change in loaded processes, and returns 0 if unloading is confirmed or 1 if the timeout is reached.
- Lines 506-523: function `load_model` - Loads a specified language model, logging the process and handling potential failures by invalidating the LMS cache if loading is successful.
- Lines 525-606: function `ensure_model_for_request` - Handles model switching by unloading the current model and loading a new one based on the requested type, ensuring the appropriate model is loaded before proceeding.
- Lines 612-738: function `dispatch_embedding_batch` - Handles a batch of embedding requests by constructing a single API call with an array of prompts and distributing the results to individual response files.
- Lines 740-849: function `dispatch_request_to_lm_studio` - Handles requests by parsing a JSON file, constructing a payload for LM Studio, and dispatching it via curl, optionally writing the output to a file or pipe.
- Lines 850-869: function `process_single_request` - Handles a single request by extracting request ID and type from a JSON string, ensuring a model is available, dispatching the request to LM Studio, and logging the process.
- Lines 871-934: function `sort_queue_by_type` - Sorts a queue of requests by priority (high first) and then by type compatibility to minimize model switches, using `jq` for efficient processing.
- Lines 936-949: function `is_type_compatible` - Validates if a request type is compatible with a specified batch type, allowing text requests for vision batches.
- Lines 951-978: function `pop_queue_item_to_file` - Handles the removal of the first item from a queue file and writes it to a specified target file, then appends the content of the target file to a history file.
- Lines 980-985: function `get_prompt_size` - Parses the prompt length from a JSON request file using `jq`, exiting with an error if the file is not readable or the 'prompt' field is missing.
- Lines 987-1000: function `has_high_priority_waiting` - Determines if the queue file contains any high-priority items by checking for the existence of the queue file and the presence of "priority=high" in any queue entries.
- Lines 1002-1197: function `process_batch` - Handles a batch of requests, either by batching embedding requests for faster API calls or dispatching text/vision requests individually while respecting priority and memory limits.
- Lines 1199-1329: function `process_queue` - Handles the processing of requests from a queue by acquiring an exclusive lock, sorting requests by type, loading the appropriate model, and processing them in batches with prefetch to keep the GPU busy.
- Lines 1335-1337: function `generate_request_id` - Generates a unique request ID incorporating the current timestamp and a random number.
- Lines 1339-1516: function `is_processor_locked` - Parses request parameters like prompt, temperature, and priority, then queues the request for processing by a background process.
- Lines 1466-1481: function `is_processor_locked` - Checks if a lock file is currently held by a live process.
- Lines 1517-1558: function `cmd_stats` - Generates a JSON string containing system statistics like queue size, memory usage, and language model status for dashboard integration.
- Lines 1560-1601: function `cmd_status` - Handles and displays the status of the gateway, including queue size, LM Studio running status, configuration settings, adaptive batch sizing parameters, and memory usage.
- Lines 1603-1614: function `cmd_reset_batch` - Handles resetting the embedding batch size to a specified integer value or the default, validating the input against defined minimum and maximum values.
- Lines 1616-1661: function `cmd_clear_queue` - Clears the message queue, attempts to terminate a stale processor, and removes the heartbeat file, logging the number of discarded requests.
- Lines 1663-1716: function `cmd_unload` - Handles unloading all models and clearing the request queue to free VRAM by killing the processor, removing files, and using the `lms unload --all` command, waiting for completion.
- Lines 1718-1790: function `cmd_help` - Displays usage instructions and available commands for the safe-model-load.sh gateway.
- Lines 1796-1860: function `main` - Handles various commands related to LM Studio, including requesting text, displaying status, viewing logs, and managing queues.

---

### test-gateway-continuous.sh

**Lines:** 162

- Lines 1-162: file `test-gateway-continuous.sh` - Handles a specified number of requests to a gateway, monitoring for continuous throughput by checking response arrival times and detecting significant delays.

---

