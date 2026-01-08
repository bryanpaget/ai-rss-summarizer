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
