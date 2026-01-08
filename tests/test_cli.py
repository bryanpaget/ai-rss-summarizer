"""Tests for cli.py module.

This test file covers the CLI commands, Typer app initialization, argument parsing,
output formatting, and error handling for the RSS summarizer CLI.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, Mock

import pytest
from typer.testing import CliRunner

from src.cli import (
    app,
    is_setup_complete,
    require_setup,
    get_storage,
    console,
)
from src.storage import Storage, Article, Story
from src.knowledge import KnowledgeBase


# =============================================================================
# CLI Runner Fixtures
# =============================================================================


@pytest.fixture
def cli_runner():
    """Create a Typer CLI test runner.

    This is the primary runner for testing CLI commands. It captures both
    stdout and stderr, allowing assertions on command output.
    """
    return CliRunner()


@pytest.fixture
def cli_runner_mix_stderr():
    """Create a CLI runner with separate stderr capture.

    Use this when you need to verify stderr output separately from stdout,
    such as for error messages or warnings.
    """
    return CliRunner(mix_stderr=False)


@pytest.fixture
def cli_runner_isolated():
    """Create a CLI runner with isolated filesystem.

    Use this for tests that create/modify files to prevent affecting
    the real filesystem. The runner provides a temporary directory
    context for each test.
    """
    return CliRunner()


# =============================================================================
# Temporary Files and Directories
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
        f.write("https://news.example.org/atom.xml\n")
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
        json.dump({
            "provider": "ollama",
            "model": "llama2",
            "base_url": "http://localhost:11434"
        }, f)
    return config_path


@pytest.fixture
def temp_llm_config_lmstudio(temp_config_dir):
    """Create a temporary LM Studio config file."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump({
            "provider": "lmstudio",
            "model": "local-model",
            "base_url": "http://localhost:1234/v1"
        }, f)
    return config_path


@pytest.fixture
def temp_llm_config_openai(temp_config_dir):
    """Create a temporary OpenAI config file."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump({
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key-12345"
        }, f)
    return config_path


# =============================================================================
# Storage Fixtures
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
            title=f"Test Article {i}: Technology News",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of test article {i} about technology and AI. " * 20,
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


@pytest.fixture
def storage_with_stories(temp_db):
    """Create a Storage instance with sample stories and articles."""
    storage = Storage(temp_db)

    # Create articles
    articles = []
    for i in range(15):
        article = Article(
            id=f"article-{i}",
            feed_url=f"https://source{i % 3}.example.com/feed.xml",
            title=f"Story {i // 5} - Article {i}",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content for story cluster {i // 5}. " * 30,
            summary=f"Summary for article {i}",
            trend_tags="Technology",
            story_id=f"story-{i // 5}",
        )
        storage.save_article(article)
        articles.append(article)

    # Create stories
    for i in range(3):
        story = Story(
            id=f"story-{i}",
            title=f"Major Story {i}",
            description=f"This is the description for story {i}",
            created_at=datetime.now() - timedelta(hours=i * 5),
            updated_at=datetime.now() - timedelta(hours=i),
            article_count=5,
        )
        storage.save_story(story)

    return storage


# =============================================================================
# Mock Storage Fixtures
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
    storage.get_feed_stats.return_value = []
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
            story_id=None,
        )
        for i in range(10)
    ]

    storage.get_articles.return_value = sample_articles
    storage.get_article.side_effect = lambda id: next(
        (a for a in sample_articles if a.id == id), None
    )
    storage.get_article_count.return_value = len(sample_articles)
    storage.get_feed_stats.return_value = [
        {
            "feed_url": "https://example.com/feed.xml",
            "article_count": 10,
            "summarized_count": 5,
            "latest_article": datetime.now().isoformat(),
        }
    ]
    return storage


# =============================================================================
# Knowledge Base Fixtures
# =============================================================================


@pytest.fixture
def kb(temp_kb_db):
    """Create a KnowledgeBase instance with temp database."""
    return KnowledgeBase(temp_kb_db)


@pytest.fixture
def mock_kb():
    """Create a mock KnowledgeBase object."""
    kb = MagicMock(spec=KnowledgeBase)
    kb.get_stats.return_value = {
        "total_insights": 100,
        "high_confidence_insights": 50,
        "total_entities": 200,
        "total_relationships": 150,
        "contradictions": 5,
    }
    kb.get_graph_stats.return_value = {
        "total_insights": 100,
        "total_entities": 200,
        "total_triples": 500,
        "total_entity_relationships": 150,
        "unique_predicates": 25,
        "total_embeddings": 1000,
        "predicate_types": ["related_to", "causes", "implies", "contradicts"],
        "top_connected_entities": [
            {"entity": "AI", "connections": 50},
            {"entity": "Technology", "connections": 40},
            {"entity": "OpenAI", "connections": 30},
        ],
    }
    kb.get_relationships.return_value = []
    kb.get_entity_neighborhood.return_value = {
        "outgoing": [],
        "incoming": [],
    }
    kb.get_connected_entities.return_value = {
        "entities": [],
        "relationships": [],
    }
    kb.find_path.return_value = None
    kb.get_contexts.return_value = []
    return kb


# =============================================================================
# Mock LLM Provider Fixtures
# =============================================================================


@pytest.fixture
def mock_provider_available():
    """Create a mock LLM provider that is available."""
    provider = MagicMock()
    provider.name = "test-provider"
    provider.model_name = "test-model"
    provider.is_available.return_value = True
    provider.summarize.return_value = "This is a test summary."
    return provider


@pytest.fixture
def mock_provider_unavailable():
    """Create a mock LLM provider that is unavailable."""
    provider = MagicMock()
    provider.name = "test-provider"
    provider.model_name = "test-model"
    provider.is_available.return_value = False
    return provider


@pytest.fixture
def mock_get_best_provider_llm(mock_provider_available):
    """Mock get_best_provider to return an available LLM provider."""
    with patch("src.cli.get_best_provider") as mock:
        mock.return_value = (mock_provider_available, True)
        yield mock


@pytest.fixture
def mock_get_best_provider_no_llm():
    """Mock get_best_provider to return no LLM."""
    with patch("src.cli.get_best_provider") as mock:
        mock.return_value = (None, False)
        yield mock


# =============================================================================
# Sample Article Fixtures
# =============================================================================


@pytest.fixture
def sample_article():
    """Create a sample article for testing."""
    return Article(
        id="test-article-1",
        feed_url="https://example.com/feed.xml",
        title="Test Article: Technology News",
        link="https://example.com/article-1",
        published=datetime.now() - timedelta(hours=1),
        content="This is test content about technology and AI." * 10,
        summary="This is a test summary.",
        trend_tags="AI & Technology",
    )


@pytest.fixture
def sample_article_unsummarized():
    """Create a sample article without a summary."""
    return Article(
        id="test-article-2",
        feed_url="https://example.com/feed.xml",
        title="Unsummarized Article",
        link="https://example.com/article-2",
        published=datetime.now() - timedelta(hours=2),
        content="This article has not been summarized yet." * 10,
        summary=None,
        trend_tags=None,
    )


@pytest.fixture
def sample_articles_bulk():
    """Create a list of sample articles for bulk testing."""
    return [
        Article(
            id=f"bulk-article-{i}",
            feed_url=f"https://source{i % 5}.example.com/feed.xml",
            title=f"Bulk Article {i}: {['Tech', 'Business', 'Science', 'Politics', 'Health'][i % 5]}",
            link=f"https://example.com/bulk-article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content for bulk article {i}." * 15,
            summary=f"Summary for article {i}" if i % 2 == 0 else None,
            trend_tags=["AI & Technology", "Business & Economy", "Science", "Politics", "Health"][i % 5],
        )
        for i in range(50)
    ]


# =============================================================================
# Environment Variable Fixtures
# =============================================================================


@pytest.fixture
def clean_env():
    """Clear LLM-related environment variables."""
    env_vars = [
        "RSS_LLM_PROVIDER",
        "RSS_LLM_MODEL",
        "RSS_LLM_API_KEY",
        "RSS_LLM_BASE_URL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
    ]
    original = {k: os.environ.get(k) for k in env_vars}
    for k in env_vars:
        if k in os.environ:
            del os.environ[k]
    yield
    # Restore
    for k, v in original.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]


@pytest.fixture
def env_with_ollama():
    """Set environment for Ollama provider."""
    os.environ["RSS_LLM_PROVIDER"] = "ollama"
    os.environ["RSS_LLM_MODEL"] = "llama2"
    yield
    del os.environ["RSS_LLM_PROVIDER"]
    del os.environ["RSS_LLM_MODEL"]


@pytest.fixture
def env_with_openai():
    """Set environment for OpenAI provider."""
    os.environ["RSS_LLM_PROVIDER"] = "openai"
    os.environ["RSS_LLM_MODEL"] = "gpt-4"
    os.environ["OPENAI_API_KEY"] = "test-key"
    yield
    del os.environ["RSS_LLM_PROVIDER"]
    del os.environ["RSS_LLM_MODEL"]
    del os.environ["OPENAI_API_KEY"]


# =============================================================================
# Mock Console Fixtures
# =============================================================================


@pytest.fixture
def mock_console():
    """Create a mock console for capturing output."""
    mock = MagicMock()
    mock.print = MagicMock()
    return mock


@pytest.fixture
def capture_console_output():
    """Capture Rich console output during tests."""
    from io import StringIO
    from rich.console import Console

    output = StringIO()
    test_console = Console(file=output, force_terminal=True, legacy_windows=True)

    with patch("src.cli.console", test_console):
        yield output


# =============================================================================
# Setup State Fixtures
# =============================================================================


@pytest.fixture
def setup_complete(temp_config_dir):
    """Set up a complete LLM configuration."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump({"provider": "ollama", "model": "llama2"}, f)

    with patch("src.cli.is_setup_complete") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def setup_incomplete():
    """Mock an incomplete setup state."""
    with patch("src.cli.is_setup_complete") as mock:
        mock.return_value = False
        yield mock


@pytest.fixture
def mock_require_setup_pass():
    """Mock require_setup to pass (setup is complete)."""
    with patch("src.cli.require_setup") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_require_setup_fail():
    """Mock require_setup to fail (setup incomplete)."""
    import typer

    with patch("src.cli.require_setup") as mock:
        mock.side_effect = typer.Exit(1)
        yield mock


# =============================================================================
# Mock External Dependencies Fixtures
# =============================================================================


@pytest.fixture
def mock_fetch_all_feeds():
    """Mock the fetch_all_feeds function."""
    with patch("src.cli.fetch_all_feeds") as mock:
        mock.return_value = [
            {
                "url": "https://example.com/feed.xml",
                "fetched": 10,
                "new": 5,
                "errors": [],
            },
            {
                "url": "https://techblog.example.com/rss",
                "fetched": 8,
                "new": 3,
                "errors": [],
            },
        ]
        yield mock


@pytest.fixture
def mock_load_feeds():
    """Mock the load_feeds function."""
    with patch("src.cli.load_feeds") as mock:
        mock.return_value = [
            "https://example.com/feed.xml",
            "https://techblog.example.com/rss",
        ]
        yield mock


@pytest.fixture
def mock_load_feeds_empty():
    """Mock load_feeds to return empty list."""
    with patch("src.cli.load_feeds") as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_summarize_articles():
    """Mock the summarize_articles function."""
    with patch("src.cli.summarize_articles") as mock:
        mock.return_value = {
            "processed": 10,
            "tagged": 5,
            "errors": [],
        }
        yield mock


@pytest.fixture
def mock_analyze_trends():
    """Mock the analyze_trends function."""
    with patch("src.cli.analyze_trends") as mock:
        mock.return_value = {
            "top_trends": [
                ("AI & Technology", 50),
                ("Business & Economy", 30),
                ("Science", 20),
            ],
            "emerging": [("GPT-5", 100), ("Quantum Computing", 75)],
            "declining": [("NFT", -50)],
            "processed": 100,
            "hours": 24,
        }
        yield mock


@pytest.fixture
def mock_detect_emerging_trends():
    """Mock the detect_emerging_trends function."""
    with patch("src.cli.detect_emerging_trends") as mock:
        mock.return_value = []
        yield mock


# =============================================================================
# Combined Test Scenario Fixtures
# =============================================================================


@pytest.fixture
def full_cli_mocks(
    mock_require_setup_pass,
    mock_load_feeds,
    mock_fetch_all_feeds,
    mock_summarize_articles,
    mock_analyze_trends,
):
    """Combine all common mocks for full CLI testing."""
    return {
        "require_setup": mock_require_setup_pass,
        "load_feeds": mock_load_feeds,
        "fetch_all_feeds": mock_fetch_all_feeds,
        "summarize_articles": mock_summarize_articles,
        "analyze_trends": mock_analyze_trends,
    }


@pytest.fixture
def cli_with_storage(cli_runner, storage_with_articles, mock_require_setup_pass):
    """CLI runner with pre-populated storage and setup complete."""
    with patch("src.cli.get_storage") as mock_get_storage:
        mock_get_storage.return_value = storage_with_articles
        yield {
            "runner": cli_runner,
            "storage": storage_with_articles,
            "get_storage": mock_get_storage,
        }


@pytest.fixture
def cli_with_empty_storage(cli_runner, storage_empty, mock_require_setup_pass):
    """CLI runner with empty storage and setup complete."""
    with patch("src.cli.get_storage") as mock_get_storage:
        mock_get_storage.return_value = storage_empty
        yield {
            "runner": cli_runner,
            "storage": storage_empty,
            "get_storage": mock_get_storage,
        }


# =============================================================================
# Edge Case Fixtures
# =============================================================================


@pytest.fixture
def sample_article_unicode():
    """Create a sample article with unicode content."""
    return Article(
        id="unicode-article",
        feed_url="https://example.com/feed.xml",
        title="Unicode Test: Emoji and Special Chars",
        link="https://example.com/unicode-article",
        published=datetime.now(),
        content="Content with emojis and unicode chars.",
        summary=None,
    )


@pytest.fixture
def sample_article_special_chars():
    """Create a sample article with special characters."""
    return Article(
        id="special-chars-article",
        feed_url="https://example.com/feed.xml",
        title="Article with <special> & \"chars\"",
        link="https://example.com/special-article",
        published=datetime.now(),
        content="Content with <html>, &amp;, 'quotes' and other special chars.",
        summary="Summary with <tags> and & chars.",
    )


@pytest.fixture
def sample_article_very_long():
    """Create a sample article with very long content."""
    return Article(
        id="long-article",
        feed_url="https://example.com/feed.xml",
        title="Very Long Article " + "A" * 200,
        link="https://example.com/long-article",
        published=datetime.now(),
        content="Very long content. " * 1000,
        summary="Long summary. " * 100,
    )


@pytest.fixture
def sample_article_minimal():
    """Create a minimal article with only required fields."""
    return Article(
        id="minimal-article",
        feed_url="https://example.com/feed.xml",
        title="Minimal Article",
        link="https://example.com/minimal",
        published=None,
        content=None,
        summary=None,
    )


# =============================================================================
# Typer App Reference Fixture
# =============================================================================


@pytest.fixture
def typer_app():
    """Provide access to the main Typer app for testing."""
    return app
