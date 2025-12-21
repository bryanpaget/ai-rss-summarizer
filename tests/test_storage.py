"""Tests for storage module."""

import os
import tempfile
from datetime import datetime

import pytest

from src.storage import Storage, Article


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def storage(temp_db):
    """Create a storage instance with temp database."""
    return Storage(temp_db)


@pytest.fixture
def sample_article():
    """Create a sample article for testing."""
    return Article(
        id="test123",
        feed_url="https://example.com/feed",
        title="Test Article",
        link="https://example.com/article1",
        published=datetime.now(),
        content="This is the content of the test article.",
    )


class TestStorage:
    def test_save_and_get_article(self, storage, sample_article):
        """Test saving and retrieving an article."""
        assert storage.save_article(sample_article) is True

        retrieved = storage.get_article("test123")
        assert retrieved is not None
        assert retrieved.title == "Test Article"
        assert retrieved.link == "https://example.com/article1"

    def test_duplicate_link_rejected(self, storage, sample_article):
        """Test that duplicate links are rejected."""
        assert storage.save_article(sample_article) is True

        # Try to save another article with the same link
        duplicate = Article(
            id="different_id",
            feed_url="https://example.com/feed",
            title="Different Title",
            link="https://example.com/article1",  # Same link
            published=datetime.now(),
            content="Different content",
        )
        assert storage.save_article(duplicate) is False

    def test_get_articles(self, storage):
        """Test retrieving multiple articles."""
        for i in range(5):
            article = Article(
                id=f"article{i}",
                feed_url="https://example.com/feed",
                title=f"Article {i}",
                link=f"https://example.com/article{i}",
                published=datetime.now(),
                content=f"Content {i}",
            )
            storage.save_article(article)

        articles = storage.get_articles(limit=3)
        assert len(articles) == 3

    def test_update_summary(self, storage, sample_article):
        """Test updating an article's summary."""
        storage.save_article(sample_article)
        storage.update_summary("test123", "This is a summary.")

        article = storage.get_article("test123")
        assert article.summary == "This is a summary."

    def test_get_unsummarized_articles(self, storage):
        """Test filtering for unsummarized articles."""
        # Add article without summary
        article1 = Article(
            id="unsummarized",
            feed_url="https://example.com/feed",
            title="No Summary",
            link="https://example.com/no-summary",
            published=datetime.now(),
            content="Content without summary",
        )
        storage.save_article(article1)

        # Add article with summary
        article2 = Article(
            id="summarized",
            feed_url="https://example.com/feed",
            title="Has Summary",
            link="https://example.com/has-summary",
            published=datetime.now(),
            content="Content with summary",
        )
        storage.save_article(article2)
        storage.update_summary("summarized", "A summary")

        unsummarized = storage.get_articles(unsummarized_only=True)
        assert len(unsummarized) == 1
        assert unsummarized[0].id == "unsummarized"

    def test_article_count(self, storage):
        """Test counting articles."""
        assert storage.get_article_count() == 0

        for i in range(3):
            article = Article(
                id=f"count{i}",
                feed_url="https://example.com/feed",
                title=f"Article {i}",
                link=f"https://example.com/count{i}",
                published=datetime.now(),
                content=f"Content {i}",
            )
            storage.save_article(article)

        assert storage.get_article_count() == 3
