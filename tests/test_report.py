"""Tests for report.py - Report generation with live progress display."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_article():
    """Create a mock article with sufficient content (100+ chars required)."""
    article = MagicMock()
    article.id = "article-1"
    article.title = "Test Article About AI Technology"
    # Content must be 100+ chars for processing (content validation requirement)
    article.content = (
        "This is the content of the article about AI and machine learning. "
        "The article discusses various aspects of artificial intelligence technology "
        "and its applications in modern software development."
    )
    article.summary = None
    article.trend_tags = None
    article.signal_tags = None
    article.link = "https://example.com/article"
    article.published = None
    return article


@pytest.fixture
def mock_summarized_article():
    """Create a mock article with summary."""
    article = MagicMock()
    article.id = "article-2"
    article.title = "Summarized Article"
    article.content = "Content here"
    article.summary = "This is a summary of the article."
    article.trend_tags = "AI & Technology"
    article.signal_tags = '{"topics": ["ai"]}'
    article.link = "https://example.com/article2"
    article.published = None
    return article


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.name = "MockProvider"
    provider.summarize.return_value = "Generated summary of the article."
    provider.generate.return_value = '{"entities": ["AI", "Technology"]}'
    return provider


@pytest.fixture
def mock_storage():
    """Create a mock storage."""
    storage = MagicMock()
    storage.get_articles.return_value = []
    storage.get_article_count.return_value = 100
    return storage


@pytest.fixture
def mock_kb():
    """Create a mock knowledge base."""
    kb = MagicMock()
    kb.get_stats.return_value = {
        "total_insights": 50,
        "total_entities": 25,
        "high_confidence_insights": 30,
        "total_relationships": 20,
        "contradictions": 0,
    }
    return kb


# =============================================================================
# Tests for generate_report function
# =============================================================================


class TestGenerateReport:
    """Tests for the generate_report function."""

    @patch('src.report.get_best_provider')
    def test_returns_stats_without_llm(self, mock_get_provider):
        """Test that report returns empty stats when no LLM available."""
        from src.report import generate_report

        mock_get_provider.return_value = (MagicMock(), False)

        stats = generate_report(limit=5)

        assert stats["processed"] == 0
        assert stats["insights"] == 0

    @patch('src.report.cleanup_old_spam')
    @patch('src.report.filter_articles')
    @patch('src.report.StoryClusterer')
    @patch('src.report.extract_triples_with_comparison')
    @patch('src.report.SignalTagger')
    @patch('src.report.extract_insights_from_article')
    @patch('src.report.analyze_article')
    @patch('src.report.detect_connections')
    @patch('src.report.EmbeddingService')
    @patch('src.report.KnowledgeBase')
    @patch('src.report.add_perspective_methods')
    @patch('src.report.Storage')
    @patch('src.report.load_feeds')
    @patch('src.report.fetch_all_feeds')
    @patch('src.report.get_best_provider')
    @patch('src.model_manager.ensure_embedding_model')
    @patch('src.model_manager.ensure_text_model')
    def test_processes_articles(
        self,
        mock_ensure_text,
        mock_ensure_embed,
        mock_get_provider,
        mock_fetch,
        mock_load_feeds,
        mock_storage_class,
        mock_add_perspectives,
        mock_kb_class,
        mock_embedding_service_class,
        mock_detect_connections,
        mock_analyze_article,
        mock_extract,
        mock_tagger_class,
        mock_triples,
        mock_clusterer_class,
        mock_filter,
        mock_cleanup,
        mock_article,
        mock_provider,
        mock_kb,
    ):
        """Test that report processes articles."""
        from src.report import generate_report
        from src.knowledge import TripleExtractionResult

        # Setup mocks
        mock_get_provider.return_value = (mock_provider, True)
        mock_load_feeds.return_value = ["feed1.xml"]
        # Include new_article_ids so report knows which articles to fetch
        mock_fetch.return_value = [{"fetched": 5, "new": 3, "errors": [], "new_article_ids": ["article-1"]}]

        mock_storage = MagicMock()
        # Now uses get_unanalyzed_articles instead of get_articles_by_ids
        mock_storage.get_unanalyzed_articles.return_value = [mock_article]
        mock_storage.get_articles_by_ids.return_value = [mock_article]
        mock_storage.get_active_stories.return_value = []
        mock_storage_class.return_value = mock_storage

        mock_kb_class.return_value = mock_kb
        mock_kb.get_insights.return_value = []

        # Mock EmbeddingService
        mock_embedding_service = MagicMock()
        mock_embedding_service.is_available.return_value = True
        mock_embedding_service.get_provider_info.return_value = {"provider": "mock", "model": "mock-embed"}
        mock_embedding_service.get_embedding.return_value = None
        mock_embedding_service_class.return_value = mock_embedding_service

        # Mock connection detection and article analysis
        mock_detect_connections.return_value = []
        mock_analyze_article.return_value = "AI, Technology"

        mock_extract.return_value = []

        # Mock triple extraction result
        mock_triples.return_value = TripleExtractionResult(
            new_triples=[],
            existing_triples=[],
            updated_triples=[]
        )

        mock_tagger = MagicMock()
        mock_tagger.tag_article.return_value = MagicMock(to_json=lambda: '{}', to_compact_string=lambda: "")
        mock_tagger_class.return_value = mock_tagger

        # Mock story clusterer
        mock_clusterer = MagicMock()
        mock_clusterer.find_matching_story.return_value = None  # No matching story
        mock_clusterer.find_matching_story_with_embedding.return_value = None
        mock_clusterer.create_new_story.return_value = MagicMock(title="Test Story", id="story-1")
        mock_clusterer_class.return_value = mock_clusterer

        # Mock filter_articles to return clean articles (no spam)
        mock_filter.return_value = ([mock_article], [])
        mock_cleanup.return_value = 0

        stats = generate_report(limit=5)

        # Should have called get_unanalyzed_articles
        mock_storage.get_unanalyzed_articles.assert_called()
        assert stats["fetched"] == 5
        assert stats["new"] == 3

    @patch('src.report.cleanup_old_spam')
    @patch('src.report.filter_articles')
    @patch('src.report.EmbeddingService')
    @patch('src.report.KnowledgeBase')
    @patch('src.report.add_perspective_methods')
    @patch('src.report.Storage')
    @patch('src.report.load_feeds')
    @patch('src.report.fetch_all_feeds')
    @patch('src.report.get_best_provider')
    def test_handles_no_articles(
        self,
        mock_get_provider,
        mock_fetch,
        mock_load_feeds,
        mock_storage_class,
        mock_add_perspectives,
        mock_kb_class,
        mock_embedding_service_class,
        mock_filter,
        mock_cleanup,
        mock_provider,
        mock_kb,
    ):
        """Test report handles case with no articles to process."""
        from src.report import generate_report

        mock_get_provider.return_value = (mock_provider, True)
        mock_load_feeds.return_value = ["feed1.xml"]
        mock_fetch.return_value = [{"fetched": 5, "new": 0, "errors": [], "new_article_ids": []}]

        mock_storage = MagicMock()
        mock_storage.get_unanalyzed_articles.return_value = []
        mock_storage.get_articles_by_ids.return_value = []
        mock_storage_class.return_value = mock_storage

        mock_kb_class.return_value = mock_kb
        mock_kb.get_insights.return_value = []

        # Mock EmbeddingService
        mock_embedding_service = MagicMock()
        mock_embedding_service.is_available.return_value = True
        mock_embedding_service_class.return_value = mock_embedding_service

        mock_filter.return_value = ([], [])  # No clean, no spam
        mock_cleanup.return_value = 0

        stats = generate_report(limit=5)

        assert stats["processed"] == 0


# =============================================================================
# Tests for _show_final_report function
# =============================================================================


class TestShowFinalReport:
    """Tests for the final report display."""

    def test_show_report_with_articles(self, mock_article, mock_kb, mock_provider):
        """Test showing final report with processed articles."""
        from src.report import _show_final_report

        processed = [
            {
                "article": mock_article,
                "insights": [],
                "triples": [],
                "connections": [],
            }
        ]

        stats = {
            "processed": 1,
            "summarized": 1,
            "insights": 0,
            "triples": 0,
            "connections": 0,
            "errors": 0,
        }

        # Should not raise
        _show_final_report(processed, stats, mock_kb, mock_provider)

    def test_show_report_empty(self, mock_kb, mock_provider):
        """Test showing final report with no articles."""
        from src.report import _show_final_report

        stats = {
            "processed": 0,
            "summarized": 0,
            "insights": 0,
            "triples": 0,
            "connections": 0,
            "errors": 0,
        }

        # Should not raise
        _show_final_report([], stats, mock_kb, mock_provider)


# =============================================================================
# Integration with CLI
# =============================================================================


class TestReportCLIIntegration:
    """Tests for report command integration."""

    def test_report_command_exists(self):
        """Test that report command is registered in main CLI."""
        from src.cli import app

        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "report" in command_names
