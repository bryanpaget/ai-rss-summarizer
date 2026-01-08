"""Tests for commands module."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, Mock

import pytest
from typer.testing import CliRunner

from src.commands import (
    update,
    setup_wizard,
    get_digest_summary,
    _display_digest,
    _display_full_digest,
    _matches_topic_keywords,
    _parse_selection,
)
from src.storage import Storage, Article, Story
from src.knowledge import KnowledgeBase


# =============================================================================
# Fixtures for CLI Runner
# =============================================================================


@pytest.fixture
def cli_runner():
    """Create a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def cli_runner_mix_stderr():
    """Create a CLI runner with mixed stderr (for capturing all output)."""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def cli_runner_isolated():
    """Create a CLI runner with isolated filesystem."""
    return CliRunner(isolated_filesystem=True)


# =============================================================================
# Fixtures for Temporary Files and Directories
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database path."""
    return os.path.join(temp_dir, "articles.db")


@pytest.fixture
def temp_kb_db(temp_dir):
    """Create a temporary knowledge base database path."""
    return os.path.join(temp_dir, "knowledge.db")


@pytest.fixture
def temp_feeds_file(temp_dir):
    """Create a temporary feeds file with sample feeds."""
    feeds_dir = os.path.join(temp_dir, "config")
    os.makedirs(feeds_dir, exist_ok=True)
    feeds_file = os.path.join(feeds_dir, "feeds.txt")
    with open(feeds_file, "w") as f:
        f.write("# Test Feeds\n")
        f.write("https://example.com/feed.xml\n")
        f.write("https://techblog.example.com/rss\n")
    return feeds_file


@pytest.fixture
def temp_feeds_file_empty(temp_dir):
    """Create an empty feeds file."""
    feeds_dir = os.path.join(temp_dir, "config")
    os.makedirs(feeds_dir, exist_ok=True)
    feeds_file = os.path.join(feeds_dir, "feeds.txt")
    with open(feeds_file, "w") as f:
        f.write("# No feeds configured\n")
    return feeds_file


@pytest.fixture
def temp_config_dir(temp_dir):
    """Create a temporary config directory."""
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


@pytest.fixture
def temp_llm_config(temp_config_dir):
    """Create a temporary LLM config file."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump({"provider": "ollama", "model": "llama2"}, f)
    return config_path


# =============================================================================
# Fixtures for Storage
# =============================================================================


@pytest.fixture
def storage(temp_db):
    """Create a Storage instance with temp database."""
    return Storage(temp_db)


@pytest.fixture
def storage_with_articles(temp_db):
    """Create a Storage instance pre-populated with sample articles."""
    storage = Storage(temp_db)
    articles = [
        Article(
            id=f"article-{i}",
            feed_url="https://example.com/feed.xml",
            title=f"Test Article {i}",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of test article {i}. " * 20,
            summary=f"Summary of article {i}." if i % 2 == 0 else None,
            trend_tags="AI & Technology" if i % 3 == 0 else "Business & Economy",
            signal_tags=json.dumps({"breaking": ["urgent"]}) if i % 4 == 0 else None,
        )
        for i in range(10)
    ]
    for article in articles:
        storage.save_article(article)
    return storage


@pytest.fixture
def storage_empty(temp_db):
    """Create an empty Storage instance."""
    return Storage(temp_db)


# =============================================================================
# Fixtures for Mock Storage
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock Storage object with common methods."""
    storage = MagicMock(spec=Storage)
    storage.get_articles.return_value = []
    storage.get_article.return_value = None
    storage.save_article.return_value = True
    storage.update_summary.return_value = None
    storage.update_signal_tags.return_value = None
    storage.update_trends.return_value = None
    storage.get_story_clusters.return_value = []
    storage.get_articles_by_cluster.return_value = []
    storage.get_article_count.return_value = 0
    return storage


@pytest.fixture
def mock_storage_with_articles():
    """Create a mock Storage with pre-populated articles."""
    storage = MagicMock(spec=Storage)

    sample_articles = [
        MagicMock(
            id=f"article-{i}",
            feed_url="https://example.com/feed.xml",
            title=f"Test Article {i}",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of test article {i}. " * 20,
            summary=f"Summary of article {i}." if i % 2 == 0 else None,
            trend_tags="AI & Technology" if i % 3 == 0 else "Business & Economy",
            signal_tags=json.dumps({"breaking": ["urgent"]}) if i % 4 == 0 else None,
        )
        for i in range(10)
    ]

    storage.get_articles.return_value = sample_articles
    storage.get_article.side_effect = lambda id: next(
        (a for a in sample_articles if a.id == id), None
    )
    storage.get_article_count.return_value = len(sample_articles)
    storage.get_story_clusters.return_value = []
    storage.get_articles_by_cluster.return_value = []
    return storage


@pytest.fixture
def mock_storage_with_stories():
    """Create a mock Storage with stories and articles."""
    storage = MagicMock(spec=Storage)

    sample_articles = [
        MagicMock(
            id=f"article-{i}",
            feed_url="https://example.com/feed.xml",
            title=f"AI News Article {i}",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content="OpenAI releases new GPT model. " * 20,
            summary="Summary about AI developments.",
            trend_tags="AI & Technology",
            signal_tags=json.dumps({"breaking": ["tech"]}),
            story_id="story-1",
        )
        for i in range(5)
    ]

    sample_stories = [
        {"id": "story-1", "title": "AI Developments", "description": "Latest in AI"},
        {"id": "story-2", "title": "Market Trends", "description": "Stock market news"},
    ]

    storage.get_articles.return_value = sample_articles
    storage.get_story_clusters.return_value = sample_stories
    storage.get_articles_by_cluster.side_effect = lambda story_id: [
        a for a in sample_articles if a.story_id == story_id
    ]
    return storage


# =============================================================================
# Fixtures for Knowledge Base
# =============================================================================


@pytest.fixture
def knowledge_base(temp_kb_db):
    """Create a KnowledgeBase instance with temp database."""
    return KnowledgeBase(temp_kb_db)


@pytest.fixture
def mock_knowledge_base():
    """Create a mock KnowledgeBase."""
    kb = MagicMock(spec=KnowledgeBase)
    kb.get_stats.return_value = {
        "total_insights": 0,
        "total_entities": 0,
        "total_triples": 0,
        "total_relationships": 0,
    }
    kb.save_insight.return_value = True
    kb.save_entity.return_value = True
    kb.save_triple.return_value = True
    return kb


@pytest.fixture
def mock_knowledge_base_with_data():
    """Create a mock KnowledgeBase with pre-populated data."""
    kb = MagicMock(spec=KnowledgeBase)
    kb.get_stats.return_value = {
        "total_insights": 25,
        "total_entities": 15,
        "total_triples": 30,
        "total_relationships": 20,
    }
    return kb


# =============================================================================
# Fixtures for Mock LLM Providers
# =============================================================================


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider that is available."""
    provider = MagicMock()
    provider.name = "MockProvider"
    provider.model_name = "mock-model"
    provider.is_available.return_value = True
    provider.summarize.return_value = "This is a mock summary of the article."
    provider.session_usage = {"calls": 0, "total_tokens": 0}
    provider._discovered_model = "mock-model"
    return provider


@pytest.fixture
def mock_llm_provider_unavailable():
    """Create a mock LLM provider that is unavailable."""
    provider = MagicMock()
    provider.name = "UnavailableProvider"
    provider.is_available.return_value = False
    provider.summarize.side_effect = RuntimeError("Provider not available")
    return provider


@pytest.fixture
def mock_llm_provider_with_errors():
    """Create a mock LLM provider that raises errors."""
    provider = MagicMock()
    provider.name = "ErrorProvider"
    provider.is_available.return_value = True
    provider.summarize.side_effect = Exception("API Error")
    return provider


@pytest.fixture
def mock_llm_provider_slow():
    """Create a mock LLM provider with simulated latency."""
    import time
    provider = MagicMock()
    provider.name = "SlowProvider"
    provider.is_available.return_value = True

    def slow_summarize(text):
        time.sleep(0.01)  # Small delay for testing
        return "Summarized after delay."

    provider.summarize.side_effect = slow_summarize
    return provider


@pytest.fixture
def mock_get_best_provider(mock_llm_provider):
    """Mock get_best_provider to return a mock provider."""
    with patch("src.commands.get_best_provider") as mock:
        mock.return_value = (mock_llm_provider, True)
        yield mock


@pytest.fixture
def mock_get_best_provider_no_llm():
    """Mock get_best_provider when no LLM is available."""
    with patch("src.commands.get_best_provider") as mock:
        mock.return_value = (None, False)
        yield mock


@pytest.fixture
def mock_get_best_provider_non_llm():
    """Mock get_best_provider returning a non-LLM provider."""
    provider = MagicMock()
    provider.name = "SimpleProvider"
    with patch("src.commands.get_best_provider") as mock:
        mock.return_value = (provider, False)
        yield mock


# =============================================================================
# Fixtures for Sample Articles
# =============================================================================


@pytest.fixture
def sample_article():
    """Create a sample article for testing."""
    return Article(
        id="test-article-001",
        feed_url="https://example.com/feed.xml",
        title="Test Article Title",
        link="https://example.com/article-001",
        published=datetime.now(),
        content="This is the full content of the test article. " * 10,
        summary="This is a short summary of the test article.",
        trend_tags="AI & Technology",
        signal_tags=json.dumps({"breaking": ["tech"], "opinion": []}),
    )


@pytest.fixture
def sample_article_unsummarized():
    """Create an unsummarized article."""
    return Article(
        id="unsummarized-001",
        feed_url="https://example.com/feed.xml",
        title="Unsummarized Article",
        link="https://example.com/unsummarized-001",
        published=datetime.now(),
        content="Content that needs summarization. " * 20,
        summary=None,
        trend_tags=None,
        signal_tags=None,
    )


@pytest.fixture
def sample_article_tech():
    """Create a technology-focused article."""
    return Article(
        id="tech-article-001",
        feed_url="https://techblog.example.com/rss",
        title="New AI Model Released",
        link="https://techblog.example.com/ai-model",
        published=datetime.now(),
        content="OpenAI has announced a new AI model with impressive capabilities. " * 10,
        summary="OpenAI releases new model.",
        trend_tags="AI & Technology",
        signal_tags=json.dumps({"breaking": ["tech", "ai"]}),
    )


@pytest.fixture
def sample_article_politics():
    """Create a politics-focused article."""
    return Article(
        id="politics-article-001",
        feed_url="https://news.example.com/rss",
        title="New Policy Announced",
        link="https://news.example.com/policy",
        published=datetime.now(),
        content="The government has announced a new policy on technology regulation. " * 10,
        summary="Government announces tech policy.",
        trend_tags="Politics & Government",
        signal_tags=json.dumps({"opinion": ["analysis"]}),
    )


@pytest.fixture
def sample_articles(sample_article, sample_article_tech, sample_article_politics):
    """Create a list of sample articles for testing."""
    return [sample_article, sample_article_tech, sample_article_politics]


@pytest.fixture
def sample_articles_bulk():
    """Create a larger set of sample articles for bulk testing."""
    articles = []
    for i in range(50):
        categories = ["AI & Technology", "Business & Economy", "Politics & Government",
                      "Health & Medicine", "Science & Research"]
        article = Article(
            id=f"bulk-article-{i:03d}",
            feed_url=f"https://feed{i % 5}.example.com/rss",
            title=f"Article Title {i}",
            link=f"https://example.com/article-{i:03d}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content for article {i}. " * 15,
            summary=f"Summary for article {i}." if i % 2 == 0 else None,
            trend_tags=categories[i % len(categories)],
            signal_tags=json.dumps({"breaking": []}) if i % 3 == 0 else None,
        )
        articles.append(article)
    return articles


# =============================================================================
# Fixtures for Sample Stories
# =============================================================================


@pytest.fixture
def sample_story():
    """Create a sample story."""
    return {
        "id": "story-001",
        "title": "AI Industry Developments",
        "description": "Major developments in AI",
        "keywords": ["AI", "technology", "innovation"],
        "first_seen": datetime.now() - timedelta(days=2),
        "last_updated": datetime.now(),
        "lifecycle_state": "developing",
    }


@pytest.fixture
def sample_stories():
    """Create a list of sample stories."""
    return [
        {
            "id": "story-001",
            "title": "AI Industry Developments",
            "description": "Major developments in AI",
        },
        {
            "id": "story-002",
            "title": "Climate Policy Changes",
            "description": "Global climate initiatives",
        },
        {
            "id": "story-003",
            "title": "Tech Market Trends",
            "description": "Stock market and technology sector",
        },
    ]


# =============================================================================
# Fixtures for Mock User Context
# =============================================================================


@pytest.fixture
def mock_user_context_store():
    """Create a mock UserContextStore."""
    store = MagicMock()
    store.load_profile.return_value = {
        "interests": ["technology", "AI", "programming"],
        "preferred_sources": ["techblog.example.com"],
        "topic_weights": {"AI & Technology": 1.0, "Business & Economy": 0.5},
    }
    return store


@pytest.fixture
def mock_user_context_store_empty():
    """Create a mock UserContextStore with no profile."""
    store = MagicMock()
    store.load_profile.return_value = None
    return store


# =============================================================================
# Fixtures for Environment Variables
# =============================================================================


@pytest.fixture
def clean_env():
    """Remove all RSS-related environment variables."""
    env_vars = [
        "RSS_LLM_PROVIDER",
        "RSS_LLM_BASE_URL",
        "RSS_LLM_API_KEY",
        "RSS_LLM_MODEL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "XAI_API_KEY",
        "GROQ_API_KEY",
    ]
    # Store original values
    original = {key: os.environ.get(key) for key in env_vars}

    # Remove all env vars
    for key in env_vars:
        if key in os.environ:
            del os.environ[key]

    yield

    # Restore original values
    for key, value in original.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_with_provider(clean_env):
    """Set up environment with a provider configured."""
    os.environ["RSS_LLM_PROVIDER"] = "ollama"
    os.environ["RSS_LLM_MODEL"] = "llama2"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_MODEL"]:
        if key in os.environ:
            del os.environ[key]


# =============================================================================
# Fixtures for Mock Console Output
# =============================================================================


@pytest.fixture
def mock_console():
    """Create a mock Rich Console for capturing output."""
    with patch("src.commands.console") as mock:
        mock.print = MagicMock()
        mock.input = MagicMock(return_value="1")
        yield mock


@pytest.fixture
def mock_console_with_inputs():
    """Create a mock Console with predefined inputs."""
    def create_mock(inputs):
        """Factory function to create mock with specific inputs."""
        input_iter = iter(inputs)
        with patch("src.commands.console") as mock:
            mock.print = MagicMock()
            mock.input = MagicMock(side_effect=lambda *args: next(input_iter, ""))
            return mock
    return create_mock


# =============================================================================
# Fixtures for Mock External Dependencies
# =============================================================================


@pytest.fixture
def mock_fetch_all_feeds():
    """Mock fetch_all_feeds function."""
    with patch("src.commands.fetch_all_feeds") as mock:
        mock.return_value = [
            {"url": "https://example.com/feed.xml", "fetched": 10, "new": 5, "errors": []},
            {"url": "https://techblog.example.com/rss", "fetched": 8, "new": 3, "errors": []},
        ]
        yield mock


@pytest.fixture
def mock_fetch_all_feeds_empty():
    """Mock fetch_all_feeds with no new articles."""
    with patch("src.commands.fetch_all_feeds") as mock:
        mock.return_value = [
            {"url": "https://example.com/feed.xml", "fetched": 0, "new": 0, "errors": []},
        ]
        yield mock


@pytest.fixture
def mock_fetch_all_feeds_error():
    """Mock fetch_all_feeds with errors."""
    with patch("src.commands.fetch_all_feeds") as mock:
        mock.return_value = [
            {"url": "https://example.com/feed.xml", "fetched": 0, "new": 0,
             "errors": ["Connection timeout"]},
        ]
        yield mock


@pytest.fixture
def mock_load_feeds():
    """Mock load_feeds function."""
    with patch("src.commands.load_feeds") as mock:
        mock.return_value = [
            "https://example.com/feed.xml",
            "https://techblog.example.com/rss",
        ]
        yield mock


@pytest.fixture
def mock_load_feeds_empty():
    """Mock load_feeds returning empty list."""
    with patch("src.commands.load_feeds") as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_batch_process_articles():
    """Mock batch_process_articles function."""
    with patch("src.commands.batch_process_articles") as mock:
        mock.return_value = {"processed": 10, "stories_created": 3, "errors": []}
        yield mock


@pytest.fixture
def mock_synthesize_perspectives():
    """Mock synthesize_perspectives function."""
    with patch("src.commands.synthesize_perspectives") as mock:
        consensus = MagicMock()
        consensus.content = "All sources agree that AI is advancing rapidly."
        contested = MagicMock()
        contested.content = "Sources disagree on the timeline of AI development."
        mock.return_value = {"consensus": consensus, "contested": contested}
        yield mock


@pytest.fixture
def mock_detect_emerging_trends():
    """Mock detect_emerging_trends function."""
    with patch("src.commands.detect_emerging_trends") as mock:
        trend1 = MagicMock()
        trend1.term = "quantum computing"
        trend1.confidence = "High"
        trend2 = MagicMock()
        trend2.term = "edge AI"
        trend2.confidence = "Medium"
        mock.return_value = [trend1, trend2]
        yield mock


@pytest.fixture
def mock_signal_tagger():
    """Mock SignalTagger."""
    with patch("src.commands.SignalTagger") as mock_class:
        tagger = MagicMock()
        tags = MagicMock()
        tags.to_json.return_value = json.dumps({"breaking": ["tech"]})
        tagger.tag_article.return_value = tags
        mock_class.return_value = tagger
        yield mock_class


@pytest.fixture
def mock_knowledge_extraction():
    """Mock knowledge extraction functions."""
    with patch("src.commands.extract_insights_from_article") as mock_insights, \
         patch("src.commands.extract_triples_from_article") as mock_triples, \
         patch("src.commands.extract_entity_relationships_from_article") as mock_rels, \
         patch("src.commands.detect_connections") as mock_connections:
        mock_insights.return_value = []
        mock_triples.return_value = []
        mock_rels.return_value = []
        mock_connections.return_value = None
        yield {
            "insights": mock_insights,
            "triples": mock_triples,
            "entity_relationships": mock_rels,
            "connections": mock_connections,
        }


# =============================================================================
# Fixtures for Combined Test Scenarios
# =============================================================================


@pytest.fixture
def full_update_mocks(
    mock_get_best_provider,
    mock_load_feeds,
    mock_fetch_all_feeds,
    mock_batch_process_articles,
    mock_synthesize_perspectives,
    mock_detect_emerging_trends,
    mock_signal_tagger,
    mock_knowledge_extraction,
    mock_console,
):
    """Combine all mocks needed for a full update command test."""
    return {
        "provider": mock_get_best_provider,
        "load_feeds": mock_load_feeds,
        "fetch_feeds": mock_fetch_all_feeds,
        "batch_process": mock_batch_process_articles,
        "perspectives": mock_synthesize_perspectives,
        "emerging_trends": mock_detect_emerging_trends,
        "tagger": mock_signal_tagger,
        "knowledge": mock_knowledge_extraction,
        "console": mock_console,
    }


@pytest.fixture
def setup_wizard_mocks(mock_console, clean_env):
    """Combine mocks needed for setup wizard tests."""
    with patch("src.commands.list_providers") as mock_list, \
         patch("src.commands.auto_detect_provider") as mock_auto:
        mock_list.return_value = [
            {"name": "Ollama", "type": "ollama", "available": True, "description": "Local LLM"},
            {"name": "OpenAI", "type": "openai", "available": False, "description": "OpenAI API"},
        ]
        mock_auto.return_value = MagicMock(name="Ollama")
        yield {
            "console": mock_console,
            "list_providers": mock_list,
            "auto_detect": mock_auto,
        }


# =============================================================================
# Fixtures for Edge Cases
# =============================================================================


@pytest.fixture
def article_with_unicode():
    """Create an article with unicode content."""
    return Article(
        id="unicode-001",
        feed_url="https://example.com/feed.xml",
        title="Article with Unicode: \u4e2d\u6587 \u65e5\u672c\u8a9e \ud83d\ude00",
        link="https://example.com/unicode-001",
        published=datetime.now(),
        content="Unicode content: \u4e2d\u6587\u5185\u5bb9 Japanese: \u65e5\u672c\u8a9e " * 5,
        summary="Summary with emoji: \ud83d\ude80",
        trend_tags="World & International",
        signal_tags=None,
    )


@pytest.fixture
def article_with_special_chars():
    """Create an article with special characters."""
    return Article(
        id="special-001",
        feed_url="https://example.com/feed.xml",
        title="Article with <special> & 'chars' \"test\"",
        link="https://example.com/special-001",
        published=datetime.now(),
        content="Content with <html> tags & special chars: \"quoted\" 'apostrophe'",
        summary="Summary with special chars: <>&\"'",
        trend_tags="Uncategorized",
        signal_tags=None,
    )


@pytest.fixture
def article_minimal():
    """Create a minimal article with only required fields."""
    return Article(
        id="minimal-001",
        feed_url="https://example.com/feed.xml",
        title="Minimal Article",
        link="https://example.com/minimal-001",
        published=None,
        content="",
        summary=None,
        trend_tags=None,
        signal_tags=None,
    )


@pytest.fixture
def article_very_long_content():
    """Create an article with very long content."""
    return Article(
        id="long-001",
        feed_url="https://example.com/feed.xml",
        title="Article with Very Long Content",
        link="https://example.com/long-001",
        published=datetime.now(),
        content="This is a very long content. " * 5000,  # ~150KB
        summary=None,
        trend_tags=None,
        signal_tags=None,
    )


# =============================================================================
# Tests for update command
# =============================================================================


class TestUpdateCommandBasicOptions:
    """Test update command with various options."""

    def test_update_returns_stats_dict(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update returns a statistics dictionary."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context:

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert isinstance(result, dict)
            assert "fetched" in result
            assert "new" in result
            assert "summarized" in result
            assert "tagged" in result
            assert "clustered" in result
            assert "stories" in result
            assert "insights" in result
            assert "displayed" in result

    def test_update_with_limit_option(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test update with limit option limits articles processed."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context:

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # Test with different limits
            for limit in [5, 10, 20]:
                update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db, limit=limit)
                # Verify get_articles is called with limit * 3
                call_args = mock_storage.get_articles.call_args
                assert call_args[1].get("limit", call_args[0][0] if call_args[0] else None) == limit * 3

    def test_update_with_show_all_option(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds_empty, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test update with show_all=True still processes when no new articles."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # With show_all=False, should still process recent articles
            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                show_all=False
            )

            # Should still call get_articles to get recent articles
            assert mock_storage.get_articles.called

    def test_update_with_topic_filter(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test update with topic filter."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            mock_storage = MagicMock()

            # Create articles with different topics
            tech_article = MagicMock()
            tech_article.trend_tags = "AI & Technology"
            tech_article.title = "Tech News"
            tech_article.content = "Technology content"
            tech_article.summary = "Tech summary"
            tech_article.signal_tags = None

            politics_article = MagicMock()
            politics_article.trend_tags = "Politics & Government"
            politics_article.title = "Politics News"
            politics_article.content = "Politics content"
            politics_article.summary = "Politics summary"
            politics_article.signal_tags = None

            mock_storage.get_articles.return_value = [tech_article, politics_article]
            mock_storage.get_story_clusters.return_value = [
                {"id": "story-1", "title": "Tech Story"}
            ]
            mock_storage.get_articles_by_cluster.return_value = [tech_article]
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # Topic filter should filter stories
            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                topic_filter="tech"
            )

            assert isinstance(result, dict)

    def test_update_with_use_context_disabled(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test update with use_context=False skips context loading."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                use_context=False
            )

            # Should not attempt to load user context when disabled
            assert isinstance(result, dict)

    def test_update_with_show_scores(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test update with show_scores=True."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                show_scores=True
            )

            assert isinstance(result, dict)


class TestUpdateCommandNoLLM:
    """Test update command when no LLM provider is available."""

    def test_update_returns_early_when_no_llm(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider_no_llm
    ):
        """Test that update returns early when no LLM is available."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.console") as mock_console:

            mock_storage = MagicMock()
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb_cls.return_value = mock_kb

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should return early with empty stats
            assert result["fetched"] == 0
            assert result["summarized"] == 0

            # Should print warning
            mock_console.print.assert_any_call("[yellow]No LLM available. Run 'rss setup' for full features.[/yellow]")

    def test_update_with_non_llm_provider(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider_non_llm
    ):
        """Test update when provider is not an LLM."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.console"):

            mock_storage = MagicMock()
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb_cls.return_value = mock_kb

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert result["fetched"] == 0


class TestUpdateCommandNoFeeds:
    """Test update command when no feeds are configured."""

    def test_update_returns_early_when_no_feeds(
        self, temp_db, temp_kb_db, mock_get_best_provider, mock_load_feeds_empty
    ):
        """Test that update returns early when no feeds are configured."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console") as mock_console:

            mock_storage = MagicMock()
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file="nonexistent.txt", db_path=temp_db, kb_path=temp_kb_db)

            # Should return empty stats
            assert result["fetched"] == 0
            assert result["new"] == 0

            # Should print warning
            mock_console.print.assert_any_call("[yellow]No feeds configured. Run 'rss add-feed URL' to add one.[/yellow]")


class TestUpdateFeedFetching:
    """Test update command feed fetching behavior."""

    def test_update_accumulates_fetch_stats(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_batch_process_articles, mock_synthesize_perspectives,
        mock_detect_emerging_trends, mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update accumulates stats from all feeds."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.fetch_all_feeds") as mock_fetch:

            # Multiple feeds with different stats
            mock_fetch.return_value = [
                {"url": "feed1", "fetched": 10, "new": 5, "errors": []},
                {"url": "feed2", "fetched": 8, "new": 3, "errors": []},
                {"url": "feed3", "fetched": 12, "new": 7, "errors": []},
            ]

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should accumulate stats from all feeds
            assert result["fetched"] == 30  # 10 + 8 + 12
            assert result["new"] == 15  # 5 + 3 + 7

    def test_update_handles_feed_errors(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds_error, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update handles feed fetch errors gracefully."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # Should not raise exception
            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert isinstance(result, dict)
            assert result["fetched"] == 0
            assert result["new"] == 0


class TestUpdateSummarization:
    """Test update command summarization triggering."""

    def test_update_summarizes_unsummarized_articles(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update summarizes articles without summaries."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.analyze_article") as mock_analyze:

            # Create articles without summaries
            unsummarized1 = MagicMock()
            unsummarized1.id = "unsummarized-1"
            unsummarized1.summary = None
            unsummarized1.content = "Content to summarize"
            unsummarized1.signal_tags = None
            unsummarized1.trend_tags = None

            unsummarized2 = MagicMock()
            unsummarized2.id = "unsummarized-2"
            unsummarized2.summary = None
            unsummarized2.content = "More content"
            unsummarized2.signal_tags = None
            unsummarized2.trend_tags = None

            # Create article with summary
            summarized = MagicMock()
            summarized.id = "summarized-1"
            summarized.summary = "Already has summary"
            summarized.content = "Content"
            summarized.signal_tags = None
            summarized.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [unsummarized1, unsummarized2, summarized]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None
            mock_analyze.return_value = "AI & Technology"

            # Get the mock provider from the fixture
            mock_provider = mock_get_best_provider.return_value[0]

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should have called summarize for unsummarized articles
            assert mock_provider.summarize.call_count == 2
            assert result["summarized"] == 2

    def test_update_skips_summarized_articles(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update skips articles that already have summaries."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            # All articles have summaries
            article1 = MagicMock()
            article1.id = "article-1"
            article1.summary = "Summary 1"
            article1.content = "Content"
            article1.signal_tags = json.dumps({"breaking": []})
            article1.trend_tags = "AI & Technology"

            article2 = MagicMock()
            article2.id = "article-2"
            article2.summary = "Summary 2"
            article2.content = "Content"
            article2.signal_tags = json.dumps({"breaking": []})
            article2.trend_tags = "Business & Economy"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article1, article2]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            mock_provider = mock_get_best_provider.return_value[0]

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should not have called summarize
            assert mock_provider.summarize.call_count == 0
            assert result["summarized"] == 0

    def test_update_handles_summarization_errors(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_load_feeds,
        mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update handles summarization errors gracefully."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.get_best_provider") as mock_provider_func, \
             patch("src.commands.analyze_article") as mock_analyze:

            # Provider that raises error on summarize
            error_provider = MagicMock()
            error_provider.name = "ErrorProvider"
            error_provider.summarize.side_effect = Exception("API Error")
            mock_provider_func.return_value = (error_provider, True)

            article = MagicMock()
            article.id = "article-1"
            article.summary = None
            article.content = "Content"
            article.signal_tags = None
            article.trend_tags = None

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None
            mock_analyze.return_value = "Uncategorized"

            # Should not raise exception
            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert isinstance(result, dict)
            assert result["summarized"] == 0  # Failed to summarize


class TestUpdateSignalTagging:
    """Test update command signal tagging."""

    def test_update_tags_untagged_articles(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update tags articles without signal tags."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            # Article without signal tags
            untagged = MagicMock()
            untagged.id = "untagged-1"
            untagged.summary = "Summary"
            untagged.content = "Content"
            untagged.signal_tags = None
            untagged.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [untagged]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should have tagged the article
            assert result["tagged"] == 1
            mock_storage.update_signal_tags.assert_called()

    def test_update_skips_tagged_articles(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update skips articles with existing signal tags."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            # Article with signal tags
            tagged = MagicMock()
            tagged.id = "tagged-1"
            tagged.summary = "Summary"
            tagged.content = "Content"
            tagged.signal_tags = json.dumps({"breaking": ["tech"]})
            tagged.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [tagged]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should not have tagged
            assert result["tagged"] == 0


class TestUpdateClustering:
    """Test update command clustering behavior."""

    def test_update_clusters_articles_into_stories(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_synthesize_perspectives,
        mock_detect_emerging_trends, mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update clusters articles into stories."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.batch_process_articles") as mock_batch:

            mock_batch.return_value = {"processed": 10, "stories_created": 3, "errors": []}

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.content = "Content"
            article.signal_tags = json.dumps({})
            article.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should have clustering stats
            assert result["clustered"] == 10
            assert result["stories"] == 3

    def test_update_handles_clustering_errors(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_synthesize_perspectives,
        mock_detect_emerging_trends, mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update handles clustering errors gracefully."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.batch_process_articles") as mock_batch:

            mock_batch.side_effect = Exception("Clustering error")

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.content = "Content"
            article.signal_tags = json.dumps({})
            article.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # Should not raise exception
            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert isinstance(result, dict)


class TestUpdateKnowledgeExtraction:
    """Test update command knowledge extraction."""

    def test_update_extracts_insights(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger
    ):
        """Test that update extracts insights from articles."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.extract_insights_from_article") as mock_insights, \
             patch("src.commands.extract_triples_from_article") as mock_triples, \
             patch("src.commands.extract_entity_relationships_from_article") as mock_rels, \
             patch("src.commands.detect_connections") as mock_connections:

            # Return some insights
            insight1 = MagicMock()
            insight2 = MagicMock()
            mock_insights.return_value = [insight1, insight2]
            mock_triples.return_value = []
            mock_rels.return_value = []

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.content = "Content"
            article.signal_tags = json.dumps({})
            article.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should have extracted insights
            assert result["insights"] == 2
            mock_connections.assert_called()

    def test_update_extracts_triples(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger
    ):
        """Test that update extracts knowledge graph triples."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.extract_insights_from_article") as mock_insights, \
             patch("src.commands.extract_triples_from_article") as mock_triples, \
             patch("src.commands.extract_entity_relationships_from_article") as mock_rels, \
             patch("src.commands.detect_connections"):

            mock_insights.return_value = []
            mock_triples.return_value = [MagicMock(), MagicMock(), MagicMock()]
            mock_rels.return_value = []

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.content = "Content"
            article.signal_tags = json.dumps({})
            article.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert result["triples"] == 3

    def test_update_handles_knowledge_extraction_errors(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger
    ):
        """Test that update handles knowledge extraction errors gracefully."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.extract_insights_from_article") as mock_insights, \
             patch("src.commands.extract_triples_from_article"), \
             patch("src.commands.extract_entity_relationships_from_article"), \
             patch("src.commands.detect_connections"):

            mock_insights.side_effect = Exception("Extraction error")

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.content = "Content"
            article.signal_tags = json.dumps({})
            article.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # Should not raise exception
            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert isinstance(result, dict)


class TestUpdatePerspectives:
    """Test update command perspective synthesis."""

    def test_update_synthesizes_perspectives_for_stories(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_detect_emerging_trends, mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update synthesizes perspectives for stories."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.synthesize_perspectives") as mock_synth:

            consensus = MagicMock()
            consensus.content = "All sources agree..."
            contested = MagicMock()
            contested.content = "Sources disagree..."
            mock_synth.return_value = {"consensus": consensus, "contested": contested}

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.signal_tags = json.dumps({})
            article.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = [
                {"id": "story-1", "title": "AI News"}
            ]
            mock_storage.get_articles_by_cluster.return_value = [article]
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should have called synthesize_perspectives
            mock_synth.assert_called()
            assert result["displayed"] == 1

    def test_update_handles_perspective_errors(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_detect_emerging_trends, mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update handles perspective synthesis errors gracefully."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.synthesize_perspectives") as mock_synth:

            mock_synth.side_effect = Exception("Perspective error")

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.signal_tags = json.dumps({})
            article.trend_tags = "AI & Technology"

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = [
                {"id": "story-1", "title": "AI News"}
            ]
            mock_storage.get_articles_by_cluster.return_value = [article]
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # Should not raise exception
            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert isinstance(result, dict)


class TestUpdateEmergingTrends:
    """Test update command emerging trends detection."""

    def test_update_detects_emerging_trends(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update detects emerging trends."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.detect_emerging_trends") as mock_trends:

            trend1 = MagicMock()
            trend1.term = "quantum computing"
            trend1.confidence = "High"
            trend2 = MagicMock()
            trend2.term = "edge AI"
            trend2.confidence = "Medium"
            mock_trends.return_value = [trend1, trend2]

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            # Should have called detect_emerging_trends
            mock_trends.assert_called()

    def test_update_handles_trend_detection_errors(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update handles trend detection errors gracefully."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.detect_emerging_trends") as mock_trends:

            mock_trends.side_effect = Exception("Trend detection error")

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            # Should not raise exception
            result = update(feeds_file=temp_feeds_file, db_path=temp_db, kb_path=temp_kb_db)

            assert isinstance(result, dict)


class TestUpdateUserContext:
    """Test update command user context handling."""

    def test_update_loads_user_context(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update loads user context when enabled."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context_cls, \
             patch("src.commands.console"):

            mock_context = MagicMock()
            mock_context.load_profile.return_value = {
                "interests": ["AI", "technology"],
                "preferred_sources": ["techblog.com"]
            }
            mock_context_cls.return_value = mock_context

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                use_context=True
            )

            # Should have loaded profile
            mock_context.load_profile.assert_called()

    def test_update_handles_context_errors(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update handles context loading errors gracefully."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context_cls, \
             patch("src.commands.console"):

            mock_context_cls.side_effect = Exception("Context error")

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            # Should not raise exception
            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                use_context=True
            )

            assert isinstance(result, dict)

    def test_update_applies_relevance_scoring(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test that update applies relevance scoring with user context."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context_cls, \
             patch("src.commands.console"), \
             patch("src.commands.sort_by_relevance") as mock_sort:

            mock_context = MagicMock()
            mock_context.load_profile.return_value = {"interests": ["AI"]}
            mock_context_cls.return_value = mock_context

            article = MagicMock()
            article.id = "article-1"
            article.summary = "Summary"
            article.signal_tags = json.dumps({})

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = [
                {"id": "story-1", "title": "AI News"}
            ]
            mock_storage.get_articles_by_cluster.return_value = [article]
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_sort.return_value = [article]

            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                use_context=True
            )

            # Should have called sort_by_relevance
            mock_sort.assert_called()


class TestMatchesTopicKeywords:
    """Test _matches_topic_keywords helper function."""

    def test_matches_tech_keywords(self, sample_article_tech):
        """Test matching tech keywords."""
        assert _matches_topic_keywords(sample_article_tech, "tech") is True
        assert _matches_topic_keywords(sample_article_tech, "technology") is True
        assert _matches_topic_keywords(sample_article_tech, "ai") is True

    def test_matches_politics_keywords(self, sample_article_politics):
        """Test matching politics keywords."""
        assert _matches_topic_keywords(sample_article_politics, "politics") is True
        assert _matches_topic_keywords(sample_article_politics, "political") is True

    def test_matches_business_keywords(self):
        """Test matching business keywords."""
        article = MagicMock()
        article.trend_tags = "Business & Economy"
        article.title = "Market News"
        article.content = "Stock market update"

        assert _matches_topic_keywords(article, "business") is True
        assert _matches_topic_keywords(article, "economy") is True
        assert _matches_topic_keywords(article, "finance") is True

    def test_matches_content_directly(self):
        """Test matching content when category doesn't match."""
        article = MagicMock()
        article.trend_tags = "Uncategorized"
        article.title = "Python Programming Tips"
        article.content = "Learn Python programming with these tips"

        assert _matches_topic_keywords(article, "python") is True

    def test_no_match(self, sample_article_tech):
        """Test no match for unrelated topic."""
        assert _matches_topic_keywords(sample_article_tech, "cooking") is False
        assert _matches_topic_keywords(sample_article_tech, "sports") is False

    def test_handles_none_trend_tags(self):
        """Test handling articles with None trend_tags."""
        article = MagicMock()
        article.trend_tags = None
        article.title = "Article Title"
        article.content = "Article content"

        # Should not raise error
        result = _matches_topic_keywords(article, "tech")
        assert result is False


class TestParseSelection:
    """Test _parse_selection helper function."""

    def test_parse_single_number(self):
        """Test parsing single number."""
        assert _parse_selection("1", 10) == [0]
        assert _parse_selection("5", 10) == [4]
        assert _parse_selection("10", 10) == [9]

    def test_parse_multiple_numbers(self):
        """Test parsing comma-separated numbers."""
        assert _parse_selection("1,3,5", 10) == [0, 2, 4]
        assert _parse_selection("1, 3, 5", 10) == [0, 2, 4]

    def test_parse_range(self):
        """Test parsing range."""
        assert _parse_selection("1-5", 10) == [0, 1, 2, 3, 4]
        assert _parse_selection("3-7", 10) == [2, 3, 4, 5, 6]

    def test_parse_all(self):
        """Test parsing 'all'."""
        assert _parse_selection("all", 5) == [0, 1, 2, 3, 4]
        assert _parse_selection("ALL", 3) == [0, 1, 2]

    def test_parse_mixed(self):
        """Test parsing mixed selection."""
        assert _parse_selection("1,3-5,8", 10) == [0, 2, 3, 4, 7]

    def test_parse_out_of_range(self):
        """Test parsing out of range numbers."""
        assert _parse_selection("1,15,20", 10) == [0]
        assert _parse_selection("100", 10) == []

    def test_parse_invalid(self):
        """Test parsing invalid input."""
        assert _parse_selection("abc", 10) == []
        assert _parse_selection("", 10) == []

    def test_parse_removes_duplicates(self):
        """Test that parsing removes duplicates."""
        assert _parse_selection("1,1,1", 10) == [0]
        assert _parse_selection("1-3,2-4", 10) == [0, 1, 2, 3]


class TestDisplayDigest:
    """Test _display_digest helper function."""

    def test_display_digest_shows_articles(self, sample_articles, mock_llm_provider):
        """Test that display_digest shows article information."""
        with patch("src.commands.console") as mock_console:
            _display_digest(sample_articles, provider=mock_llm_provider)

            # Should have printed
            assert mock_console.print.called

    def test_display_digest_with_topic_filter(self, sample_articles, mock_llm_provider):
        """Test display_digest with topic filter."""
        with patch("src.commands.console") as mock_console:
            _display_digest(sample_articles, topic_filter="tech", provider=mock_llm_provider)

            # Title should include topic
            assert mock_console.print.called

    def test_display_digest_with_show_scores(self, mock_llm_provider):
        """Test display_digest with show_scores=True."""
        article = MagicMock()
        article.title = "Test Article"
        article.summary = "Summary"
        article.published = datetime.now()
        article.trend_tags = "AI & Technology"
        article.link = "https://example.com"
        article.relevance_score = 0.85

        with patch("src.commands.console") as mock_console:
            _display_digest([article], show_scores=True, provider=mock_llm_provider)

            assert mock_console.print.called

    def test_display_digest_no_provider(self, sample_articles):
        """Test display_digest without provider."""
        with patch("src.commands.console") as mock_console:
            _display_digest(sample_articles, provider=None)

            # Should still work
            assert mock_console.print.called

    def test_display_digest_empty_articles(self, mock_llm_provider):
        """Test display_digest with empty articles list."""
        with patch("src.commands.console") as mock_console:
            _display_digest([], provider=mock_llm_provider)

            assert mock_console.print.called


class TestDisplayFullDigest:
    """Test _display_full_digest helper function."""

    def test_display_full_digest_no_stories(self, mock_llm_provider, mock_knowledge_base):
        """Test display_full_digest with no stories."""
        with patch("src.commands.console") as mock_console:
            _display_full_digest(
                story_data=[],
                emerging=[],
                provider=mock_llm_provider,
                stats={"summarized": 0, "tagged": 0, "stories": 0, "insights": 0},
                kb=mock_knowledge_base
            )

            # Should print no stories message
            mock_console.print.assert_any_call("[yellow]No stories to display.[/yellow]")

    def test_display_full_digest_with_stories(self, mock_llm_provider, mock_knowledge_base):
        """Test display_full_digest with stories."""
        article = MagicMock()
        article.summary = "Article summary"
        article.signal_tags = json.dumps({"breaking": ["tech"]})

        story_data = [{
            "story": {"id": "story-1", "title": "AI News"},
            "articles": [article],
            "perspectives": {}
        }]

        with patch("src.commands.console") as mock_console:
            _display_full_digest(
                story_data=story_data,
                emerging=[],
                provider=mock_llm_provider,
                stats={"summarized": 1, "tagged": 1, "stories": 1, "insights": 2},
                kb=mock_knowledge_base
            )

            assert mock_console.print.called

    def test_display_full_digest_with_perspectives(self, mock_llm_provider, mock_knowledge_base):
        """Test display_full_digest with perspectives."""
        article = MagicMock()
        article.summary = "Article summary"
        article.signal_tags = None

        consensus = MagicMock()
        consensus.content = "All sources agree that AI is important."
        contested = MagicMock()
        contested.content = "Sources disagree on the timeline."

        story_data = [{
            "story": {"id": "story-1", "title": "AI News"},
            "articles": [article],
            "perspectives": {"consensus": consensus, "contested": contested}
        }]

        with patch("src.commands.console") as mock_console:
            _display_full_digest(
                story_data=story_data,
                emerging=[],
                provider=mock_llm_provider,
                stats={"summarized": 1, "tagged": 0, "stories": 1, "insights": 0},
                kb=mock_knowledge_base
            )

            assert mock_console.print.called

    def test_display_full_digest_with_emerging_trends(self, mock_llm_provider, mock_knowledge_base):
        """Test display_full_digest with emerging trends."""
        trend1 = MagicMock()
        trend1.term = "quantum computing"
        trend1.confidence = "High"
        trend2 = MagicMock()
        trend2.term = "edge AI"
        trend2.confidence = "Medium"

        with patch("src.commands.console") as mock_console:
            _display_full_digest(
                story_data=[],
                emerging=[trend1, trend2],
                provider=mock_llm_provider,
                stats={"summarized": 0, "tagged": 0, "stories": 0, "insights": 0},
                kb=mock_knowledge_base
            )

            assert mock_console.print.called


class TestGetDigestSummary:
    """Test get_digest_summary function."""

    def test_get_digest_summary_with_recent_articles(self):
        """Test get_digest_summary with recent articles."""
        mock_storage = MagicMock()

        # Create articles with datetime published (as MagicMock)
        article1 = MagicMock()
        article1.published = datetime.now() - timedelta(hours=1)
        article1.trend_tags = "AI & Technology"
        article1.summary = "Tech summary"
        article1.title = "Tech article"

        article2 = MagicMock()
        article2.published = datetime.now() - timedelta(hours=2)
        article2.trend_tags = "Business & Economy"
        article2.summary = "Business summary"
        article2.title = "Business article"

        mock_storage.get_articles.return_value = [article1, article2]

        result = get_digest_summary(mock_storage, hours=48)

        assert isinstance(result, str)
        assert "articles" in result.lower()

    def test_get_digest_summary_no_recent_articles(self, storage_empty):
        """Test get_digest_summary with no recent articles."""
        result = get_digest_summary(storage_empty, hours=24)

        assert "No new articles" in result

    def test_get_digest_summary_with_topic_filter(self):
        """Test get_digest_summary with topic filter."""
        mock_storage = MagicMock()

        # Create articles with datetime published (as MagicMock)
        article1 = MagicMock()
        article1.published = datetime.now() - timedelta(hours=1)
        article1.trend_tags = "AI & Technology"
        article1.summary = "Tech summary"
        article1.title = "Tech article"
        article1.content = "Technology content about AI"

        mock_storage.get_articles.return_value = [article1]

        result = get_digest_summary(mock_storage, topic_filter="tech", hours=48)

        assert isinstance(result, str)

    def test_get_digest_summary_groups_by_trend(self):
        """Test that get_digest_summary groups articles by trend."""
        mock_storage = MagicMock()

        # Create articles with different trends
        article1 = MagicMock()
        article1.published = datetime.now() - timedelta(hours=1)
        article1.trend_tags = "AI & Technology"
        article1.summary = "Tech summary"
        article1.title = "Tech article"

        article2 = MagicMock()
        article2.published = datetime.now() - timedelta(hours=2)
        article2.trend_tags = "Business & Economy"
        article2.summary = "Business summary"
        article2.title = "Business article"

        mock_storage.get_articles.return_value = [article1, article2]

        result = get_digest_summary(mock_storage, hours=24)

        assert isinstance(result, str)


class TestUpdateIntegration:
    """Integration tests for update command."""

    def test_full_update_workflow(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test complete update workflow."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"), \
             patch("src.commands.analyze_article") as mock_analyze, \
             patch("src.commands.sort_by_relevance") as mock_sort:

            # Create article needing full processing
            article = MagicMock()
            article.id = "test-article"
            article.summary = None
            article.content = "Test content"
            article.signal_tags = None
            article.trend_tags = None

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            mock_storage.get_story_clusters.return_value = [
                {"id": "story-1", "title": "Test Story"}
            ]
            mock_storage.get_articles_by_cluster.return_value = [article]
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 5, "total_entities": 3}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = {
                "interests": ["technology"]
            }

            mock_analyze.return_value = "AI & Technology"
            mock_sort.return_value = [article]

            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                limit=10,
                show_all=False,
                use_context=True,
                show_scores=False
            )

            # Verify all stats are present
            assert "fetched" in result
            assert "new" in result
            assert "summarized" in result
            assert "tagged" in result
            assert "clustered" in result
            assert "stories" in result
            assert "insights" in result
            assert "displayed" in result

    def test_update_with_all_options(
        self, temp_db, temp_kb_db, temp_feeds_file, mock_get_best_provider,
        mock_load_feeds, mock_fetch_all_feeds, mock_batch_process_articles,
        mock_synthesize_perspectives, mock_detect_emerging_trends,
        mock_signal_tagger, mock_knowledge_extraction
    ):
        """Test update with all options specified."""
        with patch("src.commands.Storage") as mock_storage_cls, \
             patch("src.commands.KnowledgeBase") as mock_kb_cls, \
             patch("src.commands.add_perspective_methods"), \
             patch("src.commands.UserContextStore") as mock_context, \
             patch("src.commands.console"):

            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            mock_storage.get_story_clusters.return_value = []
            mock_storage_cls.return_value = mock_storage

            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {"total_insights": 0, "total_entities": 0}
            mock_kb_cls.return_value = mock_kb

            mock_context.return_value.load_profile.return_value = None

            result = update(
                feeds_file=temp_feeds_file,
                db_path=temp_db,
                kb_path=temp_kb_db,
                topic_filter="tech",
                limit=5,
                show_all=True,
                use_context=False,
                show_scores=True,
                min_relevance=0.5
            )

            assert isinstance(result, dict)
