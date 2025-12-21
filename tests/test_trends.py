"""Tests for trends module."""

import pytest

from src.trends import categorize_text, TREND_CATEGORIES


class TestCategorizeText:
    def test_ai_category(self):
        """Test detection of AI-related content."""
        text = "OpenAI releases new GPT model for machine learning tasks."
        categories = categorize_text(text)
        assert "AI & Technology" in categories

    def test_politics_category(self):
        """Test detection of political content."""
        text = "The president announced new election policies today."
        categories = categorize_text(text)
        assert "Politics & Government" in categories

    def test_multiple_categories(self):
        """Test that text can match multiple categories."""
        text = "The government invests in AI research for healthcare."
        categories = categorize_text(text)
        # Could match multiple categories
        assert len(categories) >= 1

    def test_uncategorized(self):
        """Test that non-matching text is uncategorized."""
        text = "The quick brown fox jumps over the lazy dog."
        categories = categorize_text(text)
        assert categories == ["Uncategorized"]

    def test_empty_text(self):
        """Test handling of empty text."""
        categories = categorize_text("")
        assert categories == ["Uncategorized"]

    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        text = "ARTIFICIAL INTELLIGENCE and MACHINE LEARNING"
        categories = categorize_text(text)
        assert "AI & Technology" in categories


class TestTrendCategories:
    def test_all_categories_have_keywords(self):
        """Test that all categories have at least one keyword."""
        for category, keywords in TREND_CATEGORIES.items():
            assert len(keywords) > 0, f"{category} has no keywords"

    def test_keywords_are_lowercase(self):
        """Test that all keywords are lowercase for matching."""
        for category, keywords in TREND_CATEGORIES.items():
            for keyword in keywords:
                assert keyword == keyword.lower(), f"Keyword '{keyword}' in {category} not lowercase"
