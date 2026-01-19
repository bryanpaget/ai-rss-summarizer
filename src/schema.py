"""Pydantic schemas for LLM output validation.

Ensures structured data from LLMs is reliably parseable and type-safe.
Includes robust parsing with fallback for markdown-wrapped JSON.
"""

import json
import re
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, model_validator


# ============================================================================
# Insight Extraction Schemas
# ============================================================================

class ExtractedEntity(BaseModel):
    """Entity mentioned in an insight."""
    name: str
    type: str = Field(default="concept", description="entity type: tool, person, company, concept")


class ExtractedInsight(BaseModel):
    """Single insight extracted from an article."""
    content: str = Field(..., description="The insight text")
    type: str = Field(default="technical", description="technical, tool, statistic, opinion")
    confidence: str = Field(default="medium", description="high, medium, low")
    reason: Optional[str] = Field(default=None, description="Reason for confidence level")
    entities: list[ExtractedEntity] = Field(default_factory=list)


class InsightExtractionResult(BaseModel):
    """Result of insight extraction from an article."""
    insights: list[ExtractedInsight] = Field(default_factory=list)


# ============================================================================
# Triple Extraction Schemas
# ============================================================================

class ExtractedTriple(BaseModel):
    """RDF-style triple extracted from text."""
    subject: str
    predicate: str
    object: str
    subject_type: str = Field(default="entity", description="entity or literal")
    object_type: str = Field(default="entity", description="entity or literal")
    confidence: str = Field(default="medium", description="high, medium, low")


class TripleExtractionResult(BaseModel):
    """Result of triple extraction from an article chunk."""
    triples: list[ExtractedTriple] = Field(default_factory=list)


# ============================================================================
# Entity Relationship Schemas
# ============================================================================

class ExtractedEntityRelationship(BaseModel):
    """Relationship between two entities."""
    source: str
    target: str
    relationship: str
    properties: Optional[dict] = None


class EntityRelationshipResult(BaseModel):
    """Result of entity relationship extraction."""
    relationships: list[ExtractedEntityRelationship] = Field(default_factory=list)


# ============================================================================
# Signal Tag Schemas
# ============================================================================

class SignalTag(BaseModel):
    """Signal tag for an article."""
    tag: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    reason: Optional[str] = None


class SignalTagResult(BaseModel):
    """Result of signal tag extraction."""
    tags: list[SignalTag] = Field(default_factory=list)
    is_ad: bool = Field(default=False, description="Whether article is advertisement/sponsored")


# ============================================================================
# Combined Extraction Schema (for Issue 7)
# ============================================================================

class SemanticChunk(BaseModel):
    """Semantically coherent chunk of an article."""
    content: str
    insights: list[ExtractedInsight] = Field(default_factory=list)
    triples: list[ExtractedTriple] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def filter_invalid_triples(cls, data):
        """Filter out triples with None values (LLM sometimes returns incomplete triples)."""
        if isinstance(data, dict) and 'triples' in data:
            valid_triples = []
            for t in data['triples']:
                if isinstance(t, dict):
                    # Keep only triples where subject, predicate, object are all non-None strings
                    if (t.get('subject') is not None and 
                        t.get('predicate') is not None and 
                        t.get('object') is not None):
                        valid_triples.append(t)
            data['triples'] = valid_triples
        return data


class CombinedExtractionResult(BaseModel):
    """Complete extraction from a single article in ONE LLM call.

    This is the target schema for Issue 7 - extract everything at once.
    Process once, use many times: headline/summary/keywords are used
    for story creation without additional LLM calls.
    """
    chunks: list[SemanticChunk] = Field(default_factory=list)
    signal_tags: list[SignalTag] = Field(default_factory=list)
    is_ad: bool = Field(default=False)
    summary: str = Field(default="")
    headline: str = Field(default="")  # Rewritten title for story creation
    keywords: list[str] = Field(default_factory=list)  # Key terms for story


# ============================================================================
# Robust JSON Parsing
# ============================================================================

def extract_json_from_response(response: str) -> str:
    """Extract JSON from LLM response, handling markdown wrappers.

    LLMs often return JSON wrapped in markdown code blocks like:
    ```json
    {"key": "value"}
    ```

    Or with commentary before/after. This function extracts just the JSON.

    Args:
        response: Raw LLM response string

    Returns:
        Extracted JSON string (may still be invalid JSON)
    """
    response = response.strip()

    # Try to find JSON in markdown code block
    # Pattern: ```json ... ``` or ``` ... ```
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(code_block_pattern, response)
    if match:
        return match.group(1).strip()

    # Try to find JSON array or object directly
    # Find first [ or { and last ] or }
    array_start = response.find('[')
    object_start = response.find('{')

    if array_start == -1 and object_start == -1:
        return response  # No JSON markers found, return as-is

    # Determine which comes first
    if array_start == -1:
        start = object_start
        end_char = '}'
    elif object_start == -1:
        start = array_start
        end_char = ']'
    elif array_start < object_start:
        start = array_start
        end_char = ']'
    else:
        start = object_start
        end_char = '}'

    # Find matching end
    if end_char == ']':
        end = response.rfind(']')
    else:
        end = response.rfind('}')

    if end > start:
        return response[start:end + 1]

    return response


def parse_json_response(response: str) -> dict | list:
    """Parse JSON from LLM response with robust fallback handling.

    Args:
        response: Raw LLM response string

    Returns:
        Parsed JSON (dict or list)

    Raises:
        ValueError: If JSON cannot be parsed after all fallback attempts
    """
    # First try direct parsing
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown/commentary
    extracted = extract_json_from_response(response)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse JSON from response: {e}") from e


def parse_insights(response: str) -> list[ExtractedInsight]:
    """Parse insights from LLM response.

    Args:
        response: Raw LLM response (should be JSON array of insights)

    Returns:
        List of validated ExtractedInsight objects

    Raises:
        ValueError: If parsing fails
    """
    try:
        data = parse_json_response(response)

        # Handle both array and wrapped object formats
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "insights" in data:
            items = data["insights"]
        else:
            items = [data]

        return [ExtractedInsight.model_validate(item) for item in items]
    except (ValidationError, ValueError) as e:
        raise ValueError(f"Failed to parse insights: {e}") from e


def parse_triples(response: str) -> list[ExtractedTriple]:
    """Parse triples from LLM response.

    Args:
        response: Raw LLM response (should be JSON array of triples)

    Returns:
        List of validated ExtractedTriple objects

    Raises:
        ValueError: If parsing fails
    """
    try:
        data = parse_json_response(response)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "triples" in data:
            items = data["triples"]
        else:
            items = [data]

        return [ExtractedTriple.model_validate(item) for item in items]
    except (ValidationError, ValueError) as e:
        raise ValueError(f"Failed to parse triples: {e}") from e


def parse_signal_tags(response: str) -> SignalTagResult:
    """Parse signal tags from LLM response.

    Args:
        response: Raw LLM response

    Returns:
        Validated SignalTagResult object

    Raises:
        ValueError: If parsing fails
    """
    try:
        data = parse_json_response(response)

        if isinstance(data, list):
            # Just tags, no is_ad field
            return SignalTagResult(tags=[SignalTag.model_validate(t) for t in data])
        elif isinstance(data, dict):
            return SignalTagResult.model_validate(data)
        else:
            raise ValueError(f"Unexpected data format: {type(data)}")
    except (ValidationError, ValueError) as e:
        raise ValueError(f"Failed to parse signal tags: {e}") from e


def parse_combined_extraction(response: str) -> CombinedExtractionResult:
    """Parse combined extraction result from LLM response.

    Args:
        response: Raw LLM response with chunks, insights, triples, tags, summary

    Returns:
        Validated CombinedExtractionResult object

    Raises:
        ValueError: If parsing fails
    """
    try:
        data = parse_json_response(response)
        return CombinedExtractionResult.model_validate(data)
    except (ValidationError, ValueError) as e:
        raise ValueError(f"Failed to parse combined extraction: {e}") from e
