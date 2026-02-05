"""Tests for LLM output schema validation."""

import pytest
from src.schema import (
    ExtractedInsight,
    ExtractedTriple,
    SignalTag,
    SignalTagResult,
    CombinedExtractionResult,
    extract_json_from_response,
    parse_json_response,
    parse_insights,
    parse_triples,
    parse_signal_tags,
)


class TestExtractJsonFromResponse:
    """Tests for JSON extraction from LLM responses."""

    def test_plain_json_array(self):
        """Test extraction from plain JSON array."""
        response = '[{"key": "value"}]'
        assert extract_json_from_response(response) == '[{"key": "value"}]'

    def test_plain_json_object(self):
        """Test extraction from plain JSON object."""
        response = '{"key": "value"}'
        assert extract_json_from_response(response) == '{"key": "value"}'

    def test_markdown_code_block(self):
        """Test extraction from markdown code block."""
        response = '```json\n{"key": "value"}\n```'
        assert extract_json_from_response(response) == '{"key": "value"}'

    def test_markdown_code_block_no_lang(self):
        """Test extraction from markdown code block without language."""
        response = '```\n[{"key": "value"}]\n```'
        assert extract_json_from_response(response) == '[{"key": "value"}]'

    def test_json_with_commentary_before(self):
        """Test extraction when there's text before JSON."""
        response = 'Here is the data:\n[{"key": "value"}]'
        result = extract_json_from_response(response)
        assert result == '[{"key": "value"}]'

    def test_json_with_commentary_after(self):
        """Test extraction when there's text after JSON."""
        response = '{"key": "value"}\nLet me know if you need more!'
        result = extract_json_from_response(response)
        assert result == '{"key": "value"}'

    def test_json_with_commentary_both_sides(self):
        """Test extraction with text on both sides."""
        response = 'Result:\n[1, 2, 3]\nDone.'
        result = extract_json_from_response(response)
        assert result == '[1, 2, 3]'


class TestParseJsonResponse:
    """Tests for robust JSON parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_in_markdown(self):
        """Test parsing JSON wrapped in markdown."""
        result = parse_json_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_invalid_json_raises(self):
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Could not parse JSON"):
            parse_json_response("not json at all")

    def test_parse_array(self):
        """Test parsing JSON array."""
        result = parse_json_response('[1, 2, 3]')
        assert result == [1, 2, 3]


class TestParseInsights:
    """Tests for insight parsing."""

    def test_parse_insight_array(self):
        """Test parsing array of insights."""
        response = '''[
            {"content": "AI improves productivity", "type": "technical", "confidence": "high"},
            {"content": "Python is popular", "type": "statistic", "confidence": "medium"}
        ]'''
        insights = parse_insights(response)

        assert len(insights) == 2
        assert insights[0].content == "AI improves productivity"
        assert insights[0].type == "technical"
        assert insights[0].confidence == "high"

    def test_parse_insight_with_entities(self):
        """Test parsing insight with entities."""
        response = '''[{
            "content": "GPT-4 is powerful",
            "type": "technical",
            "confidence": "high",
            "reason": "Benchmarks show this",
            "entities": [{"name": "GPT-4", "type": "tool"}]
        }]'''
        insights = parse_insights(response)

        assert len(insights) == 1
        assert len(insights[0].entities) == 1
        assert insights[0].entities[0].name == "GPT-4"

    def test_parse_insight_with_defaults(self):
        """Test that missing fields get defaults."""
        response = '[{"content": "Some insight"}]'
        insights = parse_insights(response)

        assert insights[0].type == "technical"
        assert insights[0].confidence == "medium"

    def test_parse_insight_in_markdown(self):
        """Test parsing insights wrapped in markdown."""
        response = '''```json
        [{"content": "Test insight"}]
        ```'''
        insights = parse_insights(response)
        assert len(insights) == 1


class TestParseTriples:
    """Tests for triple parsing."""

    def test_parse_triple_array(self):
        """Test parsing array of triples."""
        response = '''[
            {"subject": "GPT-4", "predicate": "developed_by", "object": "OpenAI"},
            {"subject": "Python", "predicate": "is_a", "object": "programming language"}
        ]'''
        triples = parse_triples(response)

        assert len(triples) == 2
        assert triples[0].subject == "GPT-4"
        assert triples[0].predicate == "developed_by"
        assert triples[0].object == "OpenAI"

    def test_parse_triple_with_types(self):
        """Test parsing triple with type annotations."""
        response = '''[{
            "subject": "Microsoft",
            "predicate": "acquired",
            "object": "Activision",
            "subject_type": "entity",
            "object_type": "entity",
            "confidence": "high"
        }]'''
        triples = parse_triples(response)

        assert triples[0].subject_type == "entity"
        assert triples[0].confidence == "high"

    def test_parse_triple_with_defaults(self):
        """Test that missing fields get defaults."""
        response = '[{"subject": "A", "predicate": "rel", "object": "B"}]'
        triples = parse_triples(response)

        assert triples[0].subject_type == "entity"
        assert triples[0].object_type == "entity"
        assert triples[0].confidence == "medium"


class TestParseSignalTags:
    """Tests for signal tag parsing."""

    def test_parse_tag_array(self):
        """Test parsing array of tags."""
        response = '''[
            {"tag": "technology", "confidence": 0.9},
            {"tag": "AI", "confidence": 0.85}
        ]'''
        result = parse_signal_tags(response)

        assert len(result.tags) == 2
        assert result.tags[0].tag == "technology"
        assert result.tags[0].confidence == 0.9

    def test_parse_tags_with_is_ad(self):
        """Test parsing tags with is_ad field."""
        response = '''{
            "tags": [{"tag": "sponsored", "confidence": 0.95}],
            "is_ad": true
        }'''
        result = parse_signal_tags(response)

        assert result.is_ad is True
        assert len(result.tags) == 1

    def test_parse_tags_defaults(self):
        """Test default confidence value."""
        response = '[{"tag": "news"}]'
        result = parse_signal_tags(response)

        assert result.tags[0].confidence == 0.8  # Default


class TestPydanticModels:
    """Tests for Pydantic model validation."""

    def test_insight_validation(self):
        """Test ExtractedInsight validation."""
        insight = ExtractedInsight(content="Test", type="technical", confidence="high")
        assert insight.content == "Test"

    def test_triple_validation(self):
        """Test ExtractedTriple validation."""
        triple = ExtractedTriple(subject="A", predicate="rel", object="B")
        assert triple.subject == "A"

    def test_signal_tag_confidence_bounds(self):
        """Test that confidence must be 0-1."""
        # Valid
        tag = SignalTag(tag="test", confidence=0.5)
        assert tag.confidence == 0.5

        # Invalid - should raise
        with pytest.raises(Exception):  # Pydantic ValidationError
            SignalTag(tag="test", confidence=1.5)

    def test_combined_extraction_result(self):
        """Test CombinedExtractionResult model."""
        result = CombinedExtractionResult(
            chunks=[],
            signal_tags=[SignalTag(tag="test")],
            is_ad=False,
            summary="Test summary"
        )
        assert result.summary == "Test summary"
        assert result.is_ad is False


class TestCombinedExtraction:
    """Tests for combined extraction parsing."""

    def test_parse_full_combined_result(self):
        """Test parsing a complete combined extraction response."""
        from src.schema import parse_combined_extraction

        response = '''{
            "chunks": [
                {
                    "content": "AI is transforming industries.",
                    "insights": [
                        {"content": "AI adoption is accelerating", "type": "technical", "confidence": "high", "reason": "Multiple sources confirm"}
                    ],
                    "triples": [
                        {"subject": "AI", "predicate": "transforms", "object": "industries", "subject_type": "entity", "object_type": "entity", "confidence": "high"}
                    ]
                }
            ],
            "signal_tags": [
                {"tag": "artificial-intelligence", "confidence": 0.95, "reason": "Main topic"}
            ],
            "is_ad": false,
            "summary": "This article discusses AI's impact on various industries."
        }'''

        result = parse_combined_extraction(response)

        assert len(result.chunks) == 1
        assert len(result.chunks[0].insights) == 1
        assert len(result.chunks[0].triples) == 1
        assert result.chunks[0].insights[0].content == "AI adoption is accelerating"
        assert result.signal_tags[0].tag == "artificial-intelligence"
        assert result.is_ad is False
        assert "AI" in result.summary

    def test_parse_combined_with_markdown(self):
        """Test parsing combined extraction wrapped in markdown."""
        from src.schema import parse_combined_extraction

        response = '''Here's the analysis:

```json
{
    "chunks": [],
    "signal_tags": [{"tag": "test", "confidence": 0.8}],
    "is_ad": false,
    "summary": "Test summary"
}
```

Let me know if you need more.'''

        result = parse_combined_extraction(response)
        assert result.summary == "Test summary"
        assert len(result.signal_tags) == 1

    def test_parse_combined_empty_chunks(self):
        """Test parsing with empty chunks still works."""
        from src.schema import parse_combined_extraction

        response = '''{
            "chunks": [],
            "signal_tags": [],
            "is_ad": true,
            "summary": "This is an ad."
        }'''

        result = parse_combined_extraction(response)
        assert result.is_ad is True
        assert result.summary == "This is an ad."
