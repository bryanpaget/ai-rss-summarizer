# Codebase Documentation

Generated: 2026-01-18 10:16:06
Directory: src
Files processed: 1

---

```markdown
# System Architecture Document: RSS Summarizer

## Overview

This document outlines the system architecture for an RSS summarizer, based on provided file summaries. The system focuses on extracting information from articles (likely obtained via RSS feeds), processing it using LLMs, and generating summaries, signal tags, and entity relationships. 



## Module Descriptions

### 1. Schema Module (schema.py)

*   **Primary Purpose:** Defines data structures for representing extracted information from articles.  Provides schemas for entities, insights, relationships, and overall extraction results.
*   **Key Functions/Classes:**
    *   `ExtractedEntity`: Represents an entity mentioned in an insight.
    *   `ExtractedInsight`: Represents a single insight extracted from an article.
    *   `EntityRelationshipResult`:  Represents the result of entity relationship extraction.
    *   `SignalTag`: Represents a signal tag for an article (confidence score, reason).
    *   `SignalTagResult`: Represents the result of signal tag extraction (tags, advertising status, summary, etc.).
    *   `CombinedExtractionResult`: Represents the complete extraction from a single article.
*   **Dependencies:** `typing`, `pydantic`
*   **Dependents:**  All other modules that need to store or manipulate extracted data.

### 2. LM Studio Provider Module

*   **Primary Purpose:** Provides an interface for interacting with the LM Studio API for embedding generation and potentially other text generation tasks.
*   **Key Functions/Classes:**
    *   `LMStudioProvider`:  Handles communication with the LM Studio API.
    *   `get_provider`: Factory function to create the appropriate provider instance.
    *   `embed`: Generates embeddings using the LM Studio API.
    *   `embed_batch`: Performs batch embedding using the LM Studio API. 
*   **Dependencies:** `json`, `re`, `typing`, `pydantic`.
*   **Dependents:** Modules that need to generate text embeddings or perform other tasks via the LM Studio API (likely the main processing module).

### 3. Data Parsing Module (Functions: extract_json_from_response, parse_json_response, parse_insights, parse_triples, parse_signal_tags, parse_combined_extraction)

*   **Primary Purpose:**  Parses JSON responses received from LLMs, handling different formats and validating the extracted data against predefined schemas.
*   **Key Functions/Classes:**
    *   `extract_json_from_response`: Extracts JSON data from LLM responses (handles markdown).
    *   `parse_json_response`: Parses JSON data (handles direct JSON and markdown-wrapped JSON).
    *   `parse_insights`: Parses insights, validating against the `ExtractedInsight` schema.
    *   `parse_triples`: Parses triples, validating against an assumed `ExtractedTriple` schema (not defined in summaries).
    *    `parse_signal_tags`: Parses signal tags, validating against the `SignalTagResult` schema.
    *   `parse_combined_extraction`: Parses combined extraction results, validating against the `CombinedExtractionResult` schema.
*   **Dependencies:** `json`, `re`.
*   **Dependents:** The main processing module that calls LLMs and receives responses.

### 4.  Main Processing Module (Implicit - Assumed to exist)

*   **Primary Purpose:** Orchestrates the entire process: fetching articles, sending them to an LLM, receiving responses, parsing those responses, and storing/using the extracted data. This is not explicitly defined but is implied by the other modules.
*   **Key Functions/Classes:** (Not specified in summaries - these are inferred)
    *  Handles article retrieval from RSS feeds.
    *  Sends articles to the LLM with appropriate prompts.
    *  Calls the `LMStudioProvider` to generate embeddings or perform other tasks.
    * Calls the data parsing functions (`parse_insights`, etc.) to process LLM responses.
    *   Stores extracted data in a suitable format (e.g., database).

## Data Flow Diagram (Text-Based)

```
[RSS Feed] --> [Main Processing Module]
[Main Processing Module] --> [LLM (via LMStudioProvider)]
[LLM] --> [Main Processing Module]
[Main Processing Module] --> [Data Parsing Module]
[Data Parsing Module] --> [Schema Module]
[Schema Module] --> [Main Processing Module]
[Main Processing Module] --> [Storage (e.g., Database)]
```

## Entry Points

*   **CLI Commands:**  (Assumed) Likely commands to:
    *   Fetch articles from an RSS feed.
    *   Process a single article.
    *   Generate embeddings for a text input.
    *   View/Query stored results.
*   **Main Functions:** (Assumed within the Main Processing Module)
    * `main()`: The primary function that starts the process, fetching articles, processing them, and saving the data.
    *  `process_article(article_url)`: Processes a single article from an RSS feed, including LLM interaction, parsing, and storage.


## Shared Utilities

*   **JSON Parsing:** `json` module (for handling JSON data).
*   **Regular Expressions:** `re` module (for text processing, e.g., extracting information from markdown responses).
*    **Typing**: `typing` (for type hinting)
*   **Pydantic**: `pydantic` (for data validation and schema definition).
```
```


---

# File-by-File Documentation
## Users\jpswi\personal projects\RSSsummarizer\src\schema.py

**Lines:** 303 | **Estimated tokens:** ~2487

- Lines 1-3: import-block `imports` - Imports standard library modules (json, re) and third-party libraries (typing, pydantic).
- Lines 5-14: class `ExtractedEntity` - Represents an entity mentioned in an insight, containing its name and type.
- Lines 14-45: class `ExtractedInsight` - Represents a single insight extracted from an article, containing its content, type, confidence, reason, and associated entities.
- Lines 16-25: method `ExtractedEntity.embed` - Abstract method for generating embedding vectors for a single text input.
- Lines 27-35: method `ExtractedEntity.embed_batch` - Abstract method for batch embedding, returning a list of vectors.
- Lines 47-120: class `LMStudioProvider` - A concrete provider using the LM Studio API at localhost:1234 for text generation tasks.
- Lines 49-58: method `LMStudioProvider.__init__` - Initializes the provider with the API URL, model name, and timeout value, enabling model loading.
- Lines 60-75: method `LMStudioProvider.embed` - Generates an embedding vector for a single text input using the LM Studio API; raises EmbeddingProviderError on failure.
- Lines 77-120: method `LMStudioProvider.embed_batch` - Performs batch embedding by sending a single API request for multiple texts, optimizing performance.
- Lines 122-140: function `get_provider` - A factory function that returns the appropriate embedding provider based on availability.
- Lines 140-165: class `EntityRelationshipResult` - Represents the result of entity relationship extraction, containing a list of extracted relationships.
- Lines 165-187: class `SignalTag` - Represents a signal tag for an article, including the tag itself, confidence score, and an optional reason.
- Lines 187-213: class `SignalTagResult` - Represents the result of signal tag extraction, containing a list of signal tags, a boolean indicating if the article is an advertisement, and summary/headline/keywords.
- Lines 213-265: class `CombinedExtractionResult` - Represents the complete extraction from a single article in one LLM call, including semantic chunks, signal tags, advertising status, summary, headline, and keywords.
- Lines 269-348: function `extract_json_from_response` - Extracts JSON data from an LLM response, handling markdown code blocks and direct JSON structures.
- Lines 351-401: function `parse_json_response` - Parses JSON data from an LLM response, attempting to handle both direct JSON and JSON within markdown wrappers, raising ValueError on failure.
- Lines 405-442: function `parse_insights` - Parses insights from an LLM response, validating the data against the ExtractedInsight schema, and raising ValueError on failure.
- Lines 446-483: function `parse_triples` - Parses triples from an LLM response, validating the data against the ExtractedTriple schema, and raising ValueError on failure.
- Lines 487-523: function `parse_signal_tags` - Parses signal tags from an LLM response, validating the data against the SignalTagResult schema, and raising ValueError on failure.
- Lines 527-574: function `parse_combined_extraction` - Parses the combined extraction result from an LLM response, validating it against the CombinedExtractionResult schema, and raising ValueError on failure.

---


