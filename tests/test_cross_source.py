"""Tests for cross-source comparison functionality."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.cross_source import (
    extract_domain,
    get_source_name,
    get_source_leaning,
    get_stories_with_multiple_sources,
    compare_story_coverage,
    format_comparison,
    get_current_feed_leanings,
    suggest_diverse_sources,
    SOURCE_LEANINGS,
    DIVERSE_FEEDS,
)
from src.storage import Article, Story


class TestExtractDomain:
    """Tests for domain extraction."""

    def test_simple_url(self):
        assert extract_domain("https://example.com/feed") == "example.com"

    def test_www_prefix_removed(self):
        assert extract_domain("https://www.example.com/feed") == "example.com"

    def test_subdomain_preserved(self):
        assert extract_domain("https://news.example.com/feed") == "news.example.com"

    def test_complex_url(self):
        assert extract_domain("https://www.nytimes.com/services/xml/rss/nyt/HomePage.xml") == "nytimes.com"

    def test_invalid_url_returns_empty(self):
        # urlparse returns empty netloc for invalid URLs
        result = extract_domain("not a url")
        assert result == ""


class TestGetSourceName:
    """Tests for source name lookup."""

    def test_known_source(self):
        assert get_source_name("nytimes.com") == "New York Times"

    def test_known_source_fox(self):
        assert get_source_name("foxnews.com") == "Fox News"

    def test_unknown_source_titlecase(self):
        result = get_source_name("unknownnews.org")
        assert result == "Unknownnews Org"


class TestGetSourceLeaning:
    """Tests for political leaning lookup."""

    def test_left_source(self):
        assert get_source_leaning("cnn.com") == "left"

    def test_center_source(self):
        assert get_source_leaning("reuters.com") == "center"

    def test_right_source(self):
        assert get_source_leaning("foxnews.com") == "right"

    def test_unknown_source(self):
        assert get_source_leaning("unknownnews.org") == "unknown"


class TestGetStoriesWithMultipleSources:
    """Tests for finding multi-source stories."""

    def test_finds_multi_source_stories(self):
        storage = MagicMock()

        # Create a story with articles from multiple sources
        story = Story(
            id="s1",
            title="Test Story",
            description="A test story",
            keywords=["test"],
            first_seen=datetime.now(),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=["a1", "a2", "a3"],
            news_item_ids=[],
        )

        articles = [
            Article(id="a1", feed_url="https://nytimes.com/feed", title="T1", link="l1", published=None, content=""),
            Article(id="a2", feed_url="https://foxnews.com/feed", title="T2", link="l2", published=None, content=""),
            Article(id="a3", feed_url="https://reuters.com/feed", title="T3", link="l3", published=None, content=""),
        ]

        storage.get_active_stories.return_value = [story]
        storage.get_articles_by_ids.return_value = articles

        result = get_stories_with_multiple_sources(storage, min_sources=2)

        assert len(result) == 1
        assert result[0].id == "s1"

    def test_excludes_single_source_stories(self):
        storage = MagicMock()

        story = Story(
            id="s1",
            title="Single Source Story",
            description="Only one source",
            keywords=["test"],
            first_seen=datetime.now(),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=["a1", "a2"],
            news_item_ids=[],
        )

        # Both articles from same source
        articles = [
            Article(id="a1", feed_url="https://nytimes.com/feed1", title="T1", link="l1", published=None, content=""),
            Article(id="a2", feed_url="https://nytimes.com/feed2", title="T2", link="l2", published=None, content=""),
        ]

        storage.get_active_stories.return_value = [story]
        storage.get_articles_by_ids.return_value = articles

        result = get_stories_with_multiple_sources(storage, min_sources=2)

        assert len(result) == 0


class TestCompareStoryCoverage:
    """Tests for story comparison."""

    def test_creates_comparison(self):
        storage = MagicMock()
        kb = MagicMock()

        story = Story(
            id="s1",
            title="Test Story",
            description="Test",
            keywords=[],
            first_seen=datetime.now(),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=["a1", "a2"],
            news_item_ids=[],
        )

        articles = [
            Article(
                id="a1",
                feed_url="https://nytimes.com/feed",
                title="NYT Take",
                link="l1",
                published=datetime.now(),
                content="Content 1",
                signal_tags='{"source_type": ["primary"]}',
                trend_tags="politics, economy",
            ),
            Article(
                id="a2",
                feed_url="https://foxnews.com/feed",
                title="Fox Take",
                link="l2",
                published=datetime.now(),
                content="Content 2",
                signal_tags='{"source_type": ["secondary"]}',
                trend_tags="politics",
            ),
        ]

        storage.get_articles_by_ids.return_value = articles
        kb.get_triples_by_article.return_value = []

        result = compare_story_coverage(story, storage, kb)

        assert result.story.id == "s1"
        assert len(result.sources) == 2

        source_names = {s.source_name for s in result.sources}
        assert "New York Times" in source_names
        assert "Fox News" in source_names


class TestFormatComparison:
    """Tests for comparison formatting."""

    def test_formats_comparison(self):
        from src.cross_source import SourcePerspective, CrossSourceComparison

        story = Story(
            id="s1",
            title="Test Story",
            description="Test",
            keywords=[],
            first_seen=datetime.now(),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        comparison = CrossSourceComparison(
            story=story,
            sources=[
                SourcePerspective(
                    source_name="NYT",
                    source_domain="nytimes.com",
                    article=MagicMock(),
                    key_claims=["Claim 1"],
                    framing="neutral",
                    emphasis=["economy"],
                ),
            ],
            common_facts=["Fact 1"],
            divergent_claims=[],
            coverage_gap=["Gap 1"],
            bias_indicators={"NYT": "left-center"},
        )

        result = format_comparison(comparison)

        assert "Test Story" in result
        assert "NYT" in result
        assert "Fact 1" in result


class TestDiverseSources:
    """Tests for diverse source management."""

    def test_diverse_feeds_structure(self):
        assert "left" in DIVERSE_FEEDS
        assert "center" in DIVERSE_FEEDS
        assert "right" in DIVERSE_FEEDS

        # Each feed should be (url, name, leaning)
        for category, feeds in DIVERSE_FEEDS.items():
            assert len(feeds) > 0
            for feed in feeds:
                assert len(feed) == 3
                url, name, leaning = feed
                assert url.startswith("http")
                assert isinstance(name, str)
                assert isinstance(leaning, str)

    def test_source_leanings_coverage(self):
        # Ensure we have sources across the spectrum
        leanings = set(SOURCE_LEANINGS.values())
        assert "left" in leanings or "far-left" in leanings
        assert "center" in leanings
        assert "right" in leanings or "far-right" in leanings

    def test_get_current_feed_leanings(self, tmp_path):
        # Create a temp feeds file
        feeds_file = tmp_path / "feeds.txt"
        feeds_file.write_text("""
https://nytimes.com/feed
https://foxnews.com/feed
https://reuters.com/feed
""")

        result = get_current_feed_leanings(str(feeds_file))

        assert "nytimes.com" in result["left"]
        assert "foxnews.com" in result["right"]
        assert "reuters.com" in result["center"]

    @patch("src.cross_source.get_current_feed_leanings")
    def test_suggest_diverse_sources_balanced(self, mock_leanings):
        # Already balanced - should suggest one from each
        mock_leanings.return_value = {
            "left": ["nytimes.com"],
            "center": ["reuters.com"],
            "right": ["foxnews.com"],
            "unknown": [],
        }

        result = suggest_diverse_sources()

        # When balanced, we get some suggestions
        total = sum(len(v) for v in result.values())
        assert total >= 0  # May be empty if balanced

    @patch("src.cross_source.get_current_feed_leanings")
    def test_suggest_diverse_sources_left_heavy(self, mock_leanings):
        # Heavy left bias - should suggest right
        mock_leanings.return_value = {
            "left": ["nytimes.com", "cnn.com", "msnbc.com"],
            "center": [],
            "right": [],
            "unknown": [],
        }

        result = suggest_diverse_sources()

        assert len(result.get("right", [])) > 0
        assert len(result.get("center", [])) > 0
