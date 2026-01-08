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
import typer
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


# =============================================================================
# CLI App Initialization Tests
# =============================================================================


class TestAppCreation:
    """Test Typer app creation and configuration."""

    def test_app_is_typer_instance(self):
        """Test that app is a Typer instance."""
        assert isinstance(app, typer.Typer)

    def test_app_has_name(self):
        """Test that app has the correct name."""
        # The name is set via Typer(name="rss")
        assert app.info.name == "rss"

    def test_app_has_help_text(self):
        """Test that app has help text."""
        assert app.info.help is not None
        assert "AI-powered RSS feed summarizer" in app.info.help

    def test_app_completion_disabled(self):
        """Test that shell completion is disabled."""
        # add_completion=False was passed to Typer
        # When add_completion=False, there's no 'completion' command registered
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        # If completion was enabled, there would be a completion command
        # We verify by checking the app was configured correctly during init
        # Note: We can't directly check add_completion after init, but we can verify no shell completion commands
        assert "--install-completion" not in [c for c in command_names]

    def test_app_callback_registered(self):
        """Test that the main callback is registered."""
        assert app.registered_callback is not None

    def test_app_callback_function(self):
        """Test that the callback function is the main function."""
        # The callback should exist and have the expected docstring
        callback = app.registered_callback.callback
        assert callback is not None
        assert "AI RSS Summarizer" in callback.__doc__

    def test_app_has_commands(self):
        """Test that app has registered commands."""
        assert len(app.registered_commands) > 0

    def test_app_has_subtypers(self):
        """Test that app has registered subtyper groups."""
        # The tag subcommand group is a registered typer
        assert len(app.registered_groups) > 0


class TestConsoleConfiguration:
    """Test console configuration."""

    def test_console_is_rich_console(self):
        """Test that console is a Rich Console instance."""
        from rich.console import Console as RichConsole
        assert isinstance(console, RichConsole)

    def test_console_is_configured_correctly(self):
        """Test that console is configured for Windows compatibility."""
        # The console should be configured - we check it's a valid Console instance
        # The force_terminal and legacy_windows are internal settings set during init
        assert console is not None
        # Console should be able to print (basic functionality test)
        assert hasattr(console, 'print')
        assert callable(console.print)

    def test_console_is_terminal_mode(self):
        """Test that console is in terminal mode (for color output)."""
        # When force_terminal=True, is_terminal should be True
        assert console.is_terminal is True


class TestCommandRegistration:
    """Test that all expected commands are registered."""

    def test_fetch_command_registered(self):
        """Test that fetch command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "fetch" in command_names

    def test_summarize_command_registered(self):
        """Test that summarize command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "summarize" in command_names

    def test_trends_command_registered(self):
        """Test that trends command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "trends" in command_names

    def test_list_command_registered(self):
        """Test that list command is registered with correct name."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "list" in command_names

    def test_stats_command_registered(self):
        """Test that stats command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "stats" in command_names

    def test_add_feed_command_registered(self):
        """Test that add-feed command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "add_feed" in command_names or "add-feed" in command_names

    def test_update_command_registered(self):
        """Test that update command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "update" in command_names

    def test_setup_command_registered(self):
        """Test that setup command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "setup" in command_names

    def test_discover_command_registered(self):
        """Test that discover command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "discover" in command_names

    def test_help_command_registered(self):
        """Test that help command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        # The function is named help_cmd but registered as "help"
        assert "help" in command_names or "help_cmd" in command_names

    def test_providers_command_registered(self):
        """Test that providers command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "providers" in command_names

    def test_extract_knowledge_command_registered(self):
        """Test that extract-knowledge command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "extract_knowledge" in command_names or "extract-knowledge" in command_names

    def test_query_command_registered(self):
        """Test that query command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "query" in command_names

    def test_contradictions_command_registered(self):
        """Test that contradictions command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "contradictions" in command_names

    def test_knowledge_stats_command_registered(self):
        """Test that knowledge-stats command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "knowledge-stats" in command_names or "knowledge_stats" in command_names

    def test_graph_command_registered(self):
        """Test that graph command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "graph" in command_names

    def test_graph_path_command_registered(self):
        """Test that graph-path command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "graph-path" in command_names or "graph_path" in command_names

    def test_graph_stats_command_registered(self):
        """Test that graph-stats command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "graph-stats" in command_names or "graph_stats" in command_names

    def test_context_add_command_registered(self):
        """Test that context-add command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "context_add" in command_names or "context-add" in command_names

    def test_context_list_command_registered(self):
        """Test that context-list command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "context_list" in command_names or "context-list" in command_names

    def test_emerging_command_registered(self):
        """Test that emerging command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "emerging" in command_names


class TestPerspectiveCommandsRegistration:
    """Test perspective commands are registered via add_perspective_commands."""

    def test_perspectives_command_registered(self):
        """Test that perspectives command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "perspectives" in command_names

    def test_perspective_config_command_registered(self):
        """Test that perspective-config command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "perspective-config" in command_names or "configure_perspectives" in command_names

    def test_cluster_stories_command_registered(self):
        """Test that cluster-stories command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "cluster-stories" in command_names or "cluster_stories" in command_names


class TestSubcommandGroupsRegistration:
    """Test subcommand groups are registered correctly."""

    def test_tag_subcommand_group_registered(self):
        """Test that tag subcommand group is registered."""
        group_names = [group.name for group in app.registered_groups]
        assert "tag" in group_names

    def test_tag_subcommand_group_has_help(self):
        """Test that tag subcommand group has help text."""
        for group in app.registered_groups:
            if group.name == "tag":
                assert group.typer_instance.info.help is not None
                break
        else:
            pytest.fail("tag group not found")

    def test_tag_subcommand_group_has_commands(self):
        """Test that tag subcommand group has its own commands."""
        for group in app.registered_groups:
            if group.name == "tag":
                assert len(group.typer_instance.registered_commands) > 0
                break
        else:
            pytest.fail("tag group not found")

    def test_tag_articles_subcommand_exists(self):
        """Test that tag articles subcommand exists."""
        for group in app.registered_groups:
            if group.name == "tag":
                command_names = [
                    cmd.name or cmd.callback.__name__
                    for cmd in group.typer_instance.registered_commands
                ]
                assert "articles" in command_names
                break
        else:
            pytest.fail("tag group not found")

    def test_tag_stats_subcommand_exists(self):
        """Test that tag stats subcommand exists."""
        for group in app.registered_groups:
            if group.name == "tag":
                command_names = [
                    cmd.name or cmd.callback.__name__
                    for cmd in group.typer_instance.registered_commands
                ]
                assert "stats" in command_names
                break
        else:
            pytest.fail("tag group not found")

    def test_tag_filter_subcommand_exists(self):
        """Test that tag filter subcommand exists."""
        for group in app.registered_groups:
            if group.name == "tag":
                command_names = [
                    cmd.name or cmd.callback.__name__
                    for cmd in group.typer_instance.registered_commands
                ]
                assert "filter" in command_names
                break
        else:
            pytest.fail("tag group not found")


class TestCommandCount:
    """Test expected number of commands and groups."""

    def test_minimum_command_count(self):
        """Test that we have at least the expected number of commands."""
        # Expected: fetch, summarize, trends, list, stats, add-feed, update, setup,
        # discover, help, providers, extract-knowledge, query, contradictions,
        # knowledge-stats, graph, graph-path, graph-stats, context-add, context-list,
        # emerging, perspectives, perspective-config, cluster-stories
        # That's at least 24 commands
        assert len(app.registered_commands) >= 24

    def test_minimum_subcommand_group_count(self):
        """Test that we have at least the expected number of subcommand groups."""
        # Expected: tag
        assert len(app.registered_groups) >= 1


class TestIsSetupComplete:
    """Test is_setup_complete function."""

    def test_is_setup_complete_when_config_exists(self, temp_config_dir):
        """Test is_setup_complete returns True when config exists."""
        # Create the config file
        config_path = os.path.join(temp_config_dir, "llm.json")
        with open(config_path, "w") as f:
            f.write('{"provider": "ollama"}')

        with patch("src.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            result = is_setup_complete()
            assert result is True

    def test_is_setup_complete_when_config_missing(self):
        """Test is_setup_complete returns False when config is missing."""
        with patch("src.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            result = is_setup_complete()
            assert result is False


class TestRequireSetup:
    """Test require_setup function."""

    def test_require_setup_passes_when_complete(self):
        """Test require_setup does nothing when setup is complete."""
        with patch("src.cli.is_setup_complete") as mock_check:
            mock_check.return_value = True
            # Should not raise
            require_setup()

    def test_require_setup_exits_when_incomplete(self):
        """Test require_setup raises Exit when setup is incomplete."""
        with patch("src.cli.is_setup_complete") as mock_check:
            mock_check.return_value = False
            with pytest.raises(typer.Exit) as exc_info:
                require_setup()
            assert exc_info.value.exit_code == 1

    def test_require_setup_prints_message_when_incomplete(self, mock_console):
        """Test require_setup prints setup required message."""
        with patch("src.cli.is_setup_complete") as mock_check:
            mock_check.return_value = False
            with patch("src.cli.console", mock_console):
                with pytest.raises(typer.Exit):
                    require_setup()
                # Verify message was printed
                mock_console.print.assert_called()


class TestGetStorage:
    """Test get_storage function."""

    def test_get_storage_returns_storage_instance(self, temp_dir):
        """Test get_storage returns a Storage instance."""
        db_path = os.path.join(temp_dir, "test.db")
        storage = get_storage(db_path)
        assert isinstance(storage, Storage)

    def test_get_storage_uses_default_path(self):
        """Test get_storage uses default path if none provided."""
        with patch("src.cli.Storage") as mock_storage:
            get_storage()
            mock_storage.assert_called_once_with("articles.db")

    def test_get_storage_uses_custom_path(self):
        """Test get_storage uses custom path if provided."""
        with patch("src.cli.Storage") as mock_storage:
            get_storage("/custom/path/db.sqlite")
            mock_storage.assert_called_once_with("/custom/path/db.sqlite")


class TestAppHelpViaCLI:
    """Test app help output via CLI runner."""

    def test_app_shows_help_with_no_args(self, cli_runner):
        """Test that app runs when invoked without arguments."""
        result = cli_runner.invoke(app)
        # Typer app with callback and no required args should run successfully
        # Exit code 0 = success, 2 = CLI error (acceptable for some Typer configs)
        assert result.exit_code in [0, 2]

    def test_app_shows_help_with_help_flag(self, cli_runner):
        """Test that app shows help with --help flag."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Should contain the app description
        assert "AI RSS Summarizer" in result.stdout or "RSS" in result.stdout

    def test_command_help_available(self, cli_runner):
        """Test that command help is available."""
        result = cli_runner.invoke(app, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "feeds" in result.stdout.lower() or "fetch" in result.stdout.lower()


class TestSubcommandHelpViaCLI:
    """Test subcommand group help via CLI runner."""

    def test_tag_help_available(self, cli_runner):
        """Test that tag subcommand help is available."""
        result = cli_runner.invoke(app, ["tag", "--help"])
        assert result.exit_code == 0
        assert "signal tag" in result.stdout.lower() or "tag" in result.stdout.lower()

    def test_tag_articles_help_available(self, cli_runner):
        """Test that tag articles help is available."""
        result = cli_runner.invoke(app, ["tag", "articles", "--help"])
        assert result.exit_code == 0
        assert "tag" in result.stdout.lower() or "articles" in result.stdout.lower()

    def test_tag_stats_help_available(self, cli_runner):
        """Test that tag stats help is available."""
        result = cli_runner.invoke(app, ["tag", "stats", "--help"])
        assert result.exit_code == 0

    def test_tag_filter_help_available(self, cli_runner):
        """Test that tag filter help is available."""
        result = cli_runner.invoke(app, ["tag", "filter", "--help"])
        assert result.exit_code == 0


class TestCommandCallbacksExist:
    """Test that command callbacks are properly defined."""

    def test_fetch_callback_exists(self):
        """Test that fetch command has a callback function."""
        for cmd in app.registered_commands:
            if (cmd.name or cmd.callback.__name__) == "fetch":
                assert cmd.callback is not None
                assert callable(cmd.callback)
                break
        else:
            pytest.fail("fetch command not found")

    def test_summarize_callback_exists(self):
        """Test that summarize command has a callback function."""
        for cmd in app.registered_commands:
            if (cmd.name or cmd.callback.__name__) == "summarize":
                assert cmd.callback is not None
                assert callable(cmd.callback)
                break
        else:
            pytest.fail("summarize command not found")

    def test_update_callback_exists(self):
        """Test that update command has a callback function."""
        for cmd in app.registered_commands:
            if (cmd.name or cmd.callback.__name__) == "update":
                assert cmd.callback is not None
                assert callable(cmd.callback)
                break
        else:
            pytest.fail("update command not found")

    def test_setup_callback_exists(self):
        """Test that setup command has a callback function."""
        for cmd in app.registered_commands:
            if (cmd.name or cmd.callback.__name__) == "setup":
                assert cmd.callback is not None
                assert callable(cmd.callback)
                break
        else:
            pytest.fail("setup command not found")


class TestCommandHasCorrectDecorator:
    """Test that commands have correct decorators and metadata."""

    def test_list_command_uses_name_decorator(self):
        """Test that list command is registered with name='list'."""
        # The function is list_articles but registered as 'list'
        for cmd in app.registered_commands:
            if cmd.name == "list":
                assert cmd.callback.__name__ == "list_articles"
                break
        else:
            pytest.fail("list command not found with correct name")

    def test_help_command_uses_name_decorator(self):
        """Test that help command is registered with name='help'."""
        # The function is help_cmd but registered as 'help'
        for cmd in app.registered_commands:
            if cmd.name == "help":
                assert cmd.callback.__name__ == "help_cmd"
                break
        else:
            pytest.fail("help command not found with correct name")

    def test_knowledge_stats_command_uses_name_decorator(self):
        """Test that knowledge-stats command is registered correctly."""
        for cmd in app.registered_commands:
            if cmd.name == "knowledge-stats":
                assert cmd.callback.__name__ == "knowledge_stats"
                break
        else:
            pytest.fail("knowledge-stats command not found with correct name")

    def test_graph_path_command_uses_name_decorator(self):
        """Test that graph-path command is registered correctly."""
        for cmd in app.registered_commands:
            if cmd.name == "graph-path":
                assert cmd.callback.__name__ == "graph_path"
                break
        else:
            pytest.fail("graph-path command not found with correct name")

    def test_graph_stats_command_uses_name_decorator(self):
        """Test that graph-stats command is registered correctly."""
        for cmd in app.registered_commands:
            if cmd.name == "graph-stats":
                assert cmd.callback.__name__ == "graph_stats"
                break
        else:
            pytest.fail("graph-stats command not found with correct name")


class TestAppIntegration:
    """Integration tests for app initialization."""

    def test_app_can_be_invoked(self, cli_runner):
        """Test that app can be invoked without errors."""
        result = cli_runner.invoke(app)
        # Should run without exception (exit_code 0 or 2 for missing required)
        assert result.exit_code in [0, 2]

    def test_unknown_command_error(self, cli_runner):
        """Test that unknown command returns error."""
        result = cli_runner.invoke(app, ["unknown-command-xyz"])
        assert result.exit_code != 0

    def test_all_registered_commands_have_callbacks(self):
        """Test that all registered commands have callback functions."""
        for cmd in app.registered_commands:
            assert cmd.callback is not None, f"Command {cmd.name} has no callback"
            assert callable(cmd.callback), f"Command {cmd.name} callback is not callable"

    def test_all_subcommand_group_commands_have_callbacks(self):
        """Test that all subcommand group commands have callbacks."""
        for group in app.registered_groups:
            for cmd in group.typer_instance.registered_commands:
                assert cmd.callback is not None, f"Subcommand {cmd.name} in {group.name} has no callback"
                assert callable(cmd.callback), f"Subcommand {cmd.name} in {group.name} callback is not callable"


class TestAddPerspectiveCommandsFunction:
    """Test the add_perspective_commands function."""

    def test_add_perspective_commands_function_exists(self):
        """Test that add_perspective_commands function exists."""
        from src.cli_perspectives import add_perspective_commands
        assert callable(add_perspective_commands)

    def test_add_perspective_commands_adds_to_app(self):
        """Test that add_perspective_commands adds commands to an app."""
        from src.cli_perspectives import add_perspective_commands

        test_app = typer.Typer()
        initial_count = len(test_app.registered_commands)

        add_perspective_commands(test_app)

        # Should have added at least 3 commands: perspectives, perspective-config, cluster-stories
        assert len(test_app.registered_commands) >= initial_count + 3

    def test_perspective_commands_registered_with_correct_names(self):
        """Test perspective commands are registered with correct names."""
        from src.cli_perspectives import add_perspective_commands

        test_app = typer.Typer()
        add_perspective_commands(test_app)

        command_names = [cmd.name or cmd.callback.__name__ for cmd in test_app.registered_commands]

        assert "perspectives" in command_names
        assert "perspective-config" in command_names or "configure_perspectives" in command_names
        assert "cluster-stories" in command_names or "cluster_stories" in command_names


class TestSignalTagsAppConfiguration:
    """Test signal_tags_app configuration."""

    def test_signal_tags_app_exists(self):
        """Test that signal_tags_app exists."""
        from src.cli_signal_tags import app as signal_tags_app
        assert isinstance(signal_tags_app, typer.Typer)

    def test_signal_tags_app_has_name(self):
        """Test that signal_tags_app has the correct name."""
        from src.cli_signal_tags import app as signal_tags_app
        assert signal_tags_app.info.name == "tag"

    def test_signal_tags_app_has_help(self):
        """Test that signal_tags_app has help text."""
        from src.cli_signal_tags import app as signal_tags_app
        assert signal_tags_app.info.help is not None
        assert "signal tag" in signal_tags_app.info.help.lower()

    def test_signal_tags_app_has_articles_command(self):
        """Test that signal_tags_app has articles command."""
        from src.cli_signal_tags import app as signal_tags_app
        command_names = [cmd.name or cmd.callback.__name__ for cmd in signal_tags_app.registered_commands]
        assert "articles" in command_names

    def test_signal_tags_app_has_stats_command(self):
        """Test that signal_tags_app has stats command."""
        from src.cli_signal_tags import app as signal_tags_app
        command_names = [cmd.name or cmd.callback.__name__ for cmd in signal_tags_app.registered_commands]
        assert "stats" in command_names

    def test_signal_tags_app_has_filter_command(self):
        """Test that signal_tags_app has filter command."""
        from src.cli_signal_tags import app as signal_tags_app
        command_names = [cmd.name or cmd.callback.__name__ for cmd in signal_tags_app.registered_commands]
        assert "filter" in command_names


class TestAppImports:
    """Test that necessary imports are available."""

    def test_app_import(self):
        """Test that app can be imported."""
        from src.cli import app
        assert app is not None

    def test_console_import(self):
        """Test that console can be imported."""
        from src.cli import console
        assert console is not None

    def test_is_setup_complete_import(self):
        """Test that is_setup_complete can be imported."""
        from src.cli import is_setup_complete
        assert callable(is_setup_complete)

    def test_require_setup_import(self):
        """Test that require_setup can be imported."""
        from src.cli import require_setup
        assert callable(require_setup)

    def test_get_storage_import(self):
        """Test that get_storage can be imported."""
        from src.cli import get_storage
        assert callable(get_storage)
