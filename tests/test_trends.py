"""Tests for trends module."""

import pytest
from unittest.mock import MagicMock

from src.trends import categorize_text, TREND_CATEGORY_DESCRIPTIONS


class MockEmbeddingResult:
    """Mock embedding result with real vector."""
    def __init__(self, vector):
        self.vector = vector


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service for tests."""
    mock_service = MagicMock()
    mock_service.is_available.return_value = True

    # Create predictable vectors based on content
    def embed_text(text):
        text_lower = text.lower()
        # Return vectors that will have high similarity for matching topics
        if "ai" in text_lower or "machine learning" in text_lower or "artificial intelligence" in text_lower:
            return MockEmbeddingResult([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        elif "president" in text_lower or "election" in text_lower or "government" in text_lower:
            return MockEmbeddingResult([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        elif "business" in text_lower or "stock market" in text_lower or "economy" in text_lower:
            return MockEmbeddingResult([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        else:
            return MockEmbeddingResult([0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])

    def cosine_similarity(vec1, vec2):
        """Simple cosine similarity for unit vectors."""
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    mock_service.embed_text.side_effect = embed_text
    mock_service.cosine_similarity.side_effect = cosine_similarity
    return mock_service


class TestCategorizeText:
    def test_uncategorized_without_embedding_service(self):
        """Test that text is uncategorized when no embedding service available."""
        categories = categorize_text("Some text about AI")
        assert categories == ["Uncategorized"]

    def test_uncategorized_when_service_unavailable(self):
        """Test that text is uncategorized when embedding service not available."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = False
        categories = categorize_text("Some text about AI", embedding_service=mock_service)
        assert categories == ["Uncategorized"]

    def test_empty_text(self):
        """Test handling of empty text."""
        categories = categorize_text("")
        assert categories == ["Uncategorized"]


class TestTrendCategoryDescriptions:
    def test_all_categories_have_descriptions(self):
        """Test that all categories have descriptions."""
        for category, description in TREND_CATEGORY_DESCRIPTIONS.items():
            assert len(description) > 0, f"{category} has no description"
            assert isinstance(description, str), f"{category} description not a string"

    def test_expected_categories_exist(self):
        """Test that expected categories are defined."""
        expected = [
            "AI",
            "Technology",
            "Politics & Government",
            "Business & Economy",
            "Science & Research",
            "Climate & Environment",
            "Health & Medicine",
            "Entertainment & Culture",
            "World & International",
        ]
        for cat in expected:
            assert cat in TREND_CATEGORY_DESCRIPTIONS, f"Missing category: {cat}"
