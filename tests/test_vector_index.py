"""Tests for FAISS-based vector index."""

import pytest
from src.vector_index import VectorIndex, get_vector_index, reset_vector_index, SearchResult


class TestVectorIndex:
    """Tests for VectorIndex class."""

    def setup_method(self):
        """Reset global index before each test."""
        reset_vector_index()

    def test_add_and_search(self):
        """Test basic add and search operations."""
        idx = VectorIndex(dimensions=4)

        idx.add("item1", "article", [1.0, 0.0, 0.0, 0.0])
        idx.add("item2", "article", [0.9, 0.1, 0.0, 0.0])
        idx.add("item3", "article", [0.0, 1.0, 0.0, 0.0])

        results = idx.search([1.0, 0.0, 0.0, 0.0], "article", k=3)

        assert len(results) == 3
        assert results[0].target_id == "item1"
        assert results[0].score > 0.99  # Should be ~1.0

    def test_search_with_threshold(self):
        """Test that threshold filters results."""
        idx = VectorIndex(dimensions=4)

        idx.add("item1", "article", [1.0, 0.0, 0.0, 0.0])
        idx.add("item2", "article", [0.0, 1.0, 0.0, 0.0])  # Orthogonal

        results = idx.search([1.0, 0.0, 0.0, 0.0], "article", k=10, threshold=0.5)

        assert len(results) == 1
        assert results[0].target_id == "item1"

    def test_separate_indices_per_type(self):
        """Test that different target types have separate indices."""
        idx = VectorIndex(dimensions=4)

        idx.add("article1", "article", [1.0, 0.0, 0.0, 0.0])
        idx.add("story1", "story", [1.0, 0.0, 0.0, 0.0])

        article_results = idx.search([1.0, 0.0, 0.0, 0.0], "article", k=10)
        story_results = idx.search([1.0, 0.0, 0.0, 0.0], "story", k=10)

        assert len(article_results) == 1
        assert article_results[0].target_id == "article1"
        assert len(story_results) == 1
        assert story_results[0].target_id == "story1"

    def test_update_existing_vector(self):
        """Test that adding same target_id updates the vector."""
        idx = VectorIndex(dimensions=4)

        idx.add("item1", "article", [1.0, 0.0, 0.0, 0.0])
        idx.add("item1", "article", [0.0, 1.0, 0.0, 0.0])  # Update

        # Search for original vector
        results = idx.search([1.0, 0.0, 0.0, 0.0], "article", k=10)

        # item1 should now be less similar to [1,0,0,0]
        assert len(results) >= 1
        # The new vector is orthogonal, so similarity should be low
        assert results[0].score < 0.5

    def test_contains(self):
        """Test contains check."""
        idx = VectorIndex(dimensions=4)

        idx.add("item1", "article", [1.0, 0.0, 0.0, 0.0])

        assert idx.contains("item1", "article")
        assert not idx.contains("item2", "article")
        assert not idx.contains("item1", "story")

    def test_size(self):
        """Test size reporting."""
        idx = VectorIndex(dimensions=4)

        assert idx.size() == 0
        assert idx.size("article") == 0

        idx.add("item1", "article", [1.0, 0.0, 0.0, 0.0])
        idx.add("item2", "article", [0.0, 1.0, 0.0, 0.0])
        idx.add("story1", "story", [1.0, 0.0, 0.0, 0.0])

        assert idx.size() == 3
        assert idx.size("article") == 2
        assert idx.size("story") == 1

    def test_dimension_mismatch_handled(self):
        """Test that dimension mismatches are handled gracefully."""
        idx = VectorIndex(dimensions=4)

        # Add shorter vector (should be padded)
        idx.add("item1", "article", [1.0, 0.0])

        # Add longer vector (should be truncated)
        idx.add("item2", "article", [0.0, 1.0, 0.0, 0.0, 0.5, 0.5])

        # Should still find both
        results = idx.search([1.0, 0.0, 0.0, 0.0], "article", k=10)
        assert len(results) == 2

    def test_empty_search(self):
        """Test searching empty index returns empty list."""
        idx = VectorIndex(dimensions=4)

        results = idx.search([1.0, 0.0, 0.0, 0.0], "article", k=10)
        assert results == []

    def test_clear(self):
        """Test clearing the index."""
        idx = VectorIndex(dimensions=4)

        idx.add("item1", "article", [1.0, 0.0, 0.0, 0.0])
        idx.add("story1", "story", [1.0, 0.0, 0.0, 0.0])

        assert idx.size() == 2

        idx.clear("article")
        assert idx.size("article") == 0
        assert idx.size("story") == 1

        idx.clear()
        assert idx.size() == 0


class TestGlobalIndex:
    """Tests for global index singleton."""

    def setup_method(self):
        """Reset before each test."""
        reset_vector_index()

    def test_get_vector_index_singleton(self):
        """Test that get_vector_index returns same instance."""
        idx1 = get_vector_index()
        idx2 = get_vector_index()

        assert idx1 is idx2

    def test_reset_clears_global(self):
        """Test that reset creates new instance."""
        idx1 = get_vector_index()
        idx1.add("item1", "article", [1.0, 0.0, 0.0, 0.0])

        reset_vector_index()

        idx2 = get_vector_index()
        assert idx2.size() == 0


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test SearchResult can be created."""
        result = SearchResult(target_id="test123", score=0.95)

        assert result.target_id == "test123"
        assert result.score == 0.95
