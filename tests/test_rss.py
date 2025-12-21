"""Tests for RSS module."""

import tempfile
import os

import pytest

from src.rss import (
    load_feeds,
    generate_article_id,
    get_entry_content,
)


class TestLoadFeeds:
    def test_load_feeds_from_file(self):
        """Test loading feeds from a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# Comment line\n")
            f.write("https://example.com/feed1\n")
            f.write("\n")  # Empty line
            f.write("https://example.com/feed2\n")
            f.name

        try:
            feeds = load_feeds(f.name)
            assert len(feeds) == 2
            assert "https://example.com/feed1" in feeds
            assert "https://example.com/feed2" in feeds
        finally:
            os.unlink(f.name)

    def test_load_feeds_nonexistent_file(self):
        """Test loading from nonexistent file returns empty list."""
        feeds = load_feeds("/nonexistent/path/feeds.txt")
        assert feeds == []


class TestGenerateArticleId:
    def test_generates_consistent_id(self):
        """Test that same link generates same ID."""
        link = "https://example.com/article"
        id1 = generate_article_id(link)
        id2 = generate_article_id(link)
        assert id1 == id2

    def test_different_links_different_ids(self):
        """Test that different links generate different IDs."""
        id1 = generate_article_id("https://example.com/article1")
        id2 = generate_article_id("https://example.com/article2")
        assert id1 != id2

    def test_id_is_16_chars(self):
        """Test that generated ID is 16 characters."""
        article_id = generate_article_id("https://example.com/test")
        assert len(article_id) == 16


class TestGetEntryContent:
    def test_prefers_content_field(self):
        """Test that content field is preferred over summary."""

        class MockEntry:
            content = [{"value": "Full content here"}]
            summary = "Just a summary"

        entry = MockEntry()
        content = get_entry_content(entry)
        assert content == "Full content here"

    def test_falls_back_to_summary(self):
        """Test fallback to summary when no content."""

        class MockEntry:
            summary = "Summary text"

            def get(self, key, default=None):
                return default

        entry = MockEntry()
        # No content attribute
        content = get_entry_content(entry)
        assert content == "Summary text"

    def test_falls_back_to_title(self):
        """Test fallback to title when no content or summary."""

        class MockEntry:
            def get(self, key, default=None):
                if key == "title":
                    return "Article Title"
                return default

        entry = MockEntry()
        content = get_entry_content(entry)
        assert content == "Article Title"

    def test_removes_html_tags(self):
        """Test that HTML tags are properly removed from content."""

        class MockEntry:
            content = [{"value": "Text with <a href='link'>HTML</a> tags and &amp; entities."}]

        entry = MockEntry()
        content = get_entry_content(entry)
        # Should remove HTML tags and decode entities
        assert content == "Text with HTML tags and & entities."

    def test_removes_complex_html(self):
        """Test that complex HTML is properly stripped."""

        class MockEntry:
            summary = "<p>This is a <strong>paragraph</strong> with <em>emphasis</em>.</p> <a href='#'>Link</a> More text."

        entry = MockEntry()
        content = get_entry_content(entry)
        assert content == "This is a paragraph with emphasis. Link More text."

    def test_removes_script_tags(self):
        """Test that potentially dangerous script tags are properly removed."""

        class MockEntry:
            content = [{"value": "Text with <script>alert('bad');</script> and other content."}]

        entry = MockEntry()
        content = get_entry_content(entry)
        assert content == "Text with and other content."

    def test_handles_nested_html(self):
        """Test that nested HTML tags are properly handled."""

        class MockEntry:
            summary = "<div>Outer <p>Inner <strong>content</strong> here</p> text</div>"

        entry = MockEntry()
        content = get_entry_content(entry)
        assert "Outer" in content
        assert "Inner" in content
        assert "content" in content
        assert "text" in content
        assert content == "Outer Inner content here text"  # Exact match
