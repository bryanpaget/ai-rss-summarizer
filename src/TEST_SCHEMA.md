# Codebase Documentation

Generated: 2026-01-18 10:17:42
Directory: src
Files processed: 1

---

```markdown
# System Architecture Document: RSS Summarizer

This document outlines the system architecture for an RSS summarizer, based on the provided file summaries.

## Module Breakdown

### 1. Extraction Module

*   **Primary Purpose:** Extracts structured information (insights, triples, entity relationships, signal tags) from article content.
*   **Key Functions/Classes:**
    *   `ExtractedEntity`: Represents an extracted entity with name and type.
    *   `ExtractedInsight`: Represents a single insight with content, type, confidence, reason, and associated entities.
    *   `ExtractedTriple`: Represents an RDF-style triple with subject, predicate, object, types, and confidence.
    *   `ExtractedEntityRelationship`: Represents relationships between entities.
    *   `SignalTag`: Represents a signal tag with tag, confidence level, and optional reason.
    *   `SemanticChunk`: Represents semantically coherent chunks containing content, insights, and triples.
    *   `CombinedExtractionResult`: Represents the complete extraction from an article (chunks, insights, triples, tags, summary, headline, keywords).
*   **Dependencies:**
    *   `schema.py` (for data classes)
*   **Dependents:**
    *   Parsing Modules

### 2. Parsing Module

*   **Primary Purpose:** Parses the structured data extracted by the Extraction Module from LLM responses in various formats.
*   **Key Functions/Classes:**
    * `parse_json_response`: Parses JSON data with fallback for markdown and direct JSON formats.
    * `parse_insights`: Parses insights, validating them against `ExtractedInsight` schema.
    * `parse_triples`: Parses triples, validating them against `ExtractedTriple` schema.
    * `parse_signal_tags`: Parses signal tags, validating them against `SignalTagResult` schema.
    * `parse_combined_extraction`: Parses the combined extraction result, validating it against `CombinedExtractionResult` schema.

*   **Dependencies:**
    *   `schema.py` (for data classes)
*   **Dependents:** None (it's a utility layer).



## Data Flow Diagram (Text-Based)

```
[RSS Feed] --> [Fetcher Module] --> [Extraction Module]
                                      |
                                      v
                                 [Parsing Module] --> [Data Storage/Processing] 
                                      |
                                      v
                         [Presentation Layer / User Interface]
```

## Entry Points

*   **CLI Command:** `rss_summarizer.py --feed <url> --output <file>` (Example) - This would initiate the entire process, fetching from an RSS feed and saving the results to a file.  The specific command will depend on how it's implemented in the overall application.
*   **Main Function:** `main()` or equivalent within the main execution file of the application.  This function orchestrates the workflow: fetch, extract, parse, and present/store the data.

## Shared Utilities

*   **JSON Handling:** Utilizes standard library `json` for JSON serialization and deserialization (used in `schema.py`, `extract_json_from_response`, `parse_json_response`).
*   **Regular Expressions:**  Utilizes standard library `re` for pattern matching (used in `schema.py`, `extract_json_from_response`).
*   **Pydantic Validation**: Uses Pydantic to validate data against the defined schemas (`ExtractedEntity`, etc.) ensuring data integrity.

```python

```


---

# File-by-File Documentation
## Users\jpswi\personal projects\RSSsummarizer\src\schema.py

**Lines:** 303 | **Estimated tokens:** ~2487

- Lines 1-3: import-block `imports` - Imports standard library modules (json, re) and third-party libraries (typing, pydantic).
- Lines 5-35: class `ExtractedEntity` - Represents an entity mentioned in an insight, containing its name and type.
- Lines 37-57: class `ExtractedInsight` - Represents a single insight extracted from an article, including content, type, confidence, reason, and associated entities.
- Lines 59-77: class `InsightExtractionResult` - Represents the result of extracting insights from an article, containing a list of ExtractedInsight objects.
- Lines 79-97: class `ExtractedTriple` - Represents an RDF-style triple extracted from text, containing subject, predicate, object, and their types, along with confidence.
- Lines 99-117: class `TripleExtractionResult` - Represents the result of extracting triples from an article chunk, containing a list of ExtractedTriple objects.
- Lines 119-137: class `ExtractedEntityRelationship` - Represents a relationship between two entities, specifying source, target, relationship type, and properties.
- Lines 139-157: class `EntityRelationshipResult` - Represents the result of extracting entity relationships, containing a list of ExtractedEntityRelationship objects.
- Lines 159-177: class `SignalTag` - Represents a signal tag for an article, including the tag itself, confidence level, and optional reason.
- Lines 179-197: class `SignalTagResult` - Represents the result of extracting signal tags from an article, containing a list of SignalTag objects and a boolean indicating whether the article is an advertisement.
- Lines 199-236: class `SemanticChunk` - Represents a semantically coherent chunk of an article, containing content, insights, and triples.
- Lines 238-266: class `CombinedExtractionResult` - Represents the complete extraction from a single article in one LLM call, including chunks, insights, triples, tags, summary, headline, and keywords.
- Lines 268-357: function `extract_json_from_response` - Extracts JSON data from an LLM response, handling markdown wrappers.
- Lines 359-410: function `parse_json_response` - Parses JSON data from an LLM response, with fallback to handle markdown and direct JSON formats.
- Lines 412-460: function `parse_insights` - Parses insights from an LLM response, validating them against the ExtractedInsight schema.
- Lines 462-511: function `parse_triples` - Parses triples from an LLM response, validating them against the ExtractedTriple schema.
- Lines 513-562: function `parse_signal_tags` - Parses signal tags from an LLM response, validating them against the SignalTagResult schema.
- Lines 564-632: function `parse_combined_extraction` - Parses the combined extraction result from an LLM response, validating it against the CombinedExtractionResult schema.

---


