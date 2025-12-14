"""Tests for summarizer module."""

import pytest

from src.summarizer import SimpleSummarizer, get_summarizer


class TestSimpleSummarizer:
    def test_short_text_returned_as_is(self):
        """Test that short text is returned unchanged."""
        summarizer = SimpleSummarizer()
        text = "This is a short sentence."
        result = summarizer.summarize(text, max_length=100)
        assert result == text

    def test_long_text_truncated(self):
        """Test that long text is truncated."""
        summarizer = SimpleSummarizer()
        text = "This is sentence one. This is sentence two. This is sentence three. " * 10
        result = summarizer.summarize(text, max_length=100)
        assert len(result) <= 100

    def test_empty_text(self):
        """Test handling of empty text."""
        summarizer = SimpleSummarizer()
        result = summarizer.summarize("", max_length=100)
        assert result == ""

    def test_respects_sentence_boundaries(self):
        """Test that summarizer tries to respect sentence boundaries."""
        summarizer = SimpleSummarizer()
        text = "First sentence here. Second sentence here. Third sentence is quite long."
        result = summarizer.summarize(text, max_length=50)
        # Should end with a complete sentence or truncation marker
        assert result.endswith(".") or result.endswith("...")


class TestGetSummarizer:
    def test_default_is_simple(self):
        """Test that default summarizer is SimpleSummarizer."""
        summarizer = get_summarizer(use_llm=False)
        assert isinstance(summarizer, SimpleSummarizer)

    def test_llm_flag(self):
        """Test that LLM flag returns TransformerSummarizer."""
        # Note: This will fail if transformers not installed,
        # which is expected behavior
        summarizer = get_summarizer(use_llm=True)
        assert summarizer is not None
        assert hasattr(summarizer, "summarize")
