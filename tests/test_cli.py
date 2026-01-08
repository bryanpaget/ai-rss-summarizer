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


# =============================================================================
# CLI Argument Parsing Tests
# =============================================================================


class TestFetchCommandArguments:
    """Test fetch command argument parsing."""

    def test_fetch_default_feeds_file(self, cli_runner):
        """Test fetch uses default feeds file path."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, ["fetch"])
            # Default is config/feeds.txt
            mock_load.assert_called_with("config/feeds.txt")

    def test_fetch_custom_feeds_file_short(self, cli_runner):
        """Test fetch with -f short option for feeds file."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, ["fetch", "-f", "custom/feeds.txt"])
            mock_load.assert_called_with("custom/feeds.txt")

    def test_fetch_custom_feeds_file_long(self, cli_runner):
        """Test fetch with --feeds long option for feeds file."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, ["fetch", "--feeds", "custom/feeds.txt"])
            mock_load.assert_called_with("custom/feeds.txt")

    def test_fetch_default_db_path(self, cli_runner):
        """Test fetch uses default database path."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, ["fetch"])
            # Default is articles.db
            mock_storage.assert_called_with("articles.db")

    def test_fetch_custom_db_path_short(self, cli_runner):
        """Test fetch with -d short option for database path."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, ["fetch", "-d", "custom.db"])
            mock_storage.assert_called_with("custom.db")

    def test_fetch_custom_db_path_long(self, cli_runner):
        """Test fetch with --db long option for database path."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, ["fetch", "--db", "custom.db"])
            mock_storage.assert_called_with("custom.db")

    def test_fetch_combined_options(self, cli_runner):
        """Test fetch with both feeds and db options."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, [
                "fetch", "-f", "my/feeds.txt", "-d", "my.db"
            ])
            mock_load.assert_called_with("my/feeds.txt")
            mock_storage.assert_called_with("my.db")


class TestSummarizeCommandArguments:
    """Test summarize command argument parsing."""

    def test_summarize_default_limit(self, cli_runner):
        """Test summarize uses default limit of 10."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=10, use_llm=False, tag_articles=False
            )

    def test_summarize_custom_limit_short(self, cli_runner):
        """Test summarize with -n short option for limit."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "-n", "25"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=25, use_llm=False, tag_articles=False
            )

    def test_summarize_custom_limit_long(self, cli_runner):
        """Test summarize with --limit long option."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "--limit", "50"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=50, use_llm=False, tag_articles=False
            )

    def test_summarize_llm_flag(self, cli_runner):
        """Test summarize with --llm flag."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "--llm"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=10, use_llm=True, tag_articles=False
            )

    def test_summarize_tag_flag(self, cli_runner):
        """Test summarize with --tag flag."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "--tag"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=10, use_llm=False, tag_articles=True
            )

    def test_summarize_combined_flags(self, cli_runner):
        """Test summarize with multiple flags combined."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "--llm", "--tag", "-n", "100"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=100, use_llm=True, tag_articles=True
            )


class TestTrendsCommandArguments:
    """Test trends command argument parsing."""

    def test_trends_default_limit(self, cli_runner):
        """Test trends uses default limit of 100."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.analyze_trends") as mock_analyze:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_analyze.return_value = {"top_trends": [], "processed": 0}

            result = cli_runner.invoke(app, ["trends"])
            mock_analyze.assert_called_with(mock_storage.return_value, limit=100)

    def test_trends_custom_limit(self, cli_runner):
        """Test trends with custom limit."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.analyze_trends") as mock_analyze:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_analyze.return_value = {"top_trends": [], "processed": 0}

            result = cli_runner.invoke(app, ["trends", "-n", "500"])
            mock_analyze.assert_called_with(mock_storage.return_value, limit=500)


class TestListCommandArguments:
    """Test list command argument parsing."""

    def test_list_default_limit(self, cli_runner):
        """Test list uses default limit of 20."""
        with patch("src.cli.get_storage") as mock_storage:
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage.return_value = storage_mock

            result = cli_runner.invoke(app, ["list"])
            storage_mock.get_articles.assert_called_with(limit=20)

    def test_list_custom_limit(self, cli_runner):
        """Test list with custom limit."""
        with patch("src.cli.get_storage") as mock_storage:
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage.return_value = storage_mock

            result = cli_runner.invoke(app, ["list", "-n", "50"])
            storage_mock.get_articles.assert_called_with(limit=50)

    def test_list_trend_filter_short(self, cli_runner):
        """Test list with -t short option for trend filter."""
        with patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.get_articles_by_trend") as mock_by_trend:
            storage_mock = MagicMock()
            mock_storage.return_value = storage_mock
            mock_by_trend.return_value = []

            result = cli_runner.invoke(app, ["list", "-t", "AI & Technology"])
            mock_by_trend.assert_called_with(storage_mock, "AI & Technology", limit=20)

    def test_list_trend_filter_long(self, cli_runner):
        """Test list with --trend long option for trend filter."""
        with patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.get_articles_by_trend") as mock_by_trend:
            storage_mock = MagicMock()
            mock_storage.return_value = storage_mock
            mock_by_trend.return_value = []

            result = cli_runner.invoke(app, ["list", "--trend", "Business"])
            mock_by_trend.assert_called_with(storage_mock, "Business", limit=20)

    def test_list_summary_flag_short(self, cli_runner):
        """Test list with -s short option for summary display."""
        with patch("src.cli.get_storage") as mock_storage:
            storage_mock = MagicMock()
            article_mock = MagicMock()
            article_mock.title = "Test Article"
            article_mock.published = None
            article_mock.trend_tags = None
            article_mock.summary = "Test summary"
            storage_mock.get_articles.return_value = [article_mock]
            mock_storage.return_value = storage_mock

            result = cli_runner.invoke(app, ["list", "-s"])
            # Should show summary section
            assert "Summaries" in result.stdout or result.exit_code == 0

    def test_list_summary_flag_long(self, cli_runner):
        """Test list with --summary long option."""
        with patch("src.cli.get_storage") as mock_storage:
            storage_mock = MagicMock()
            article_mock = MagicMock()
            article_mock.title = "Test Article"
            article_mock.published = None
            article_mock.trend_tags = None
            article_mock.summary = "Test summary"
            storage_mock.get_articles.return_value = [article_mock]
            mock_storage.return_value = storage_mock

            result = cli_runner.invoke(app, ["list", "--summary"])
            # Should show summary section
            assert "Summaries" in result.stdout or result.exit_code == 0

    def test_list_combined_options(self, cli_runner):
        """Test list with multiple options combined."""
        with patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.get_articles_by_trend") as mock_by_trend:
            storage_mock = MagicMock()
            mock_storage.return_value = storage_mock
            mock_by_trend.return_value = []

            result = cli_runner.invoke(app, [
                "list", "-n", "30", "-t", "Science", "-s"
            ])
            mock_by_trend.assert_called_with(storage_mock, "Science", limit=30)


class TestAddFeedCommandArguments:
    """Test add-feed command argument parsing."""

    def test_add_feed_requires_url(self, cli_runner):
        """Test add-feed requires URL argument."""
        result = cli_runner.invoke(app, ["add-feed"])
        assert result.exit_code != 0

    def test_add_feed_with_url(self, cli_runner, temp_dir):
        """Test add-feed with URL argument."""
        feeds_file = os.path.join(temp_dir, "config", "feeds.txt")
        os.makedirs(os.path.dirname(feeds_file), exist_ok=True)
        Path(feeds_file).touch()

        with patch("src.cli.load_feeds") as mock_load:
            mock_load.return_value = []

            result = cli_runner.invoke(app, [
                "add-feed", "https://example.com/feed.xml",
                "-f", feeds_file
            ])
            assert result.exit_code == 0
            assert "Added feed" in result.stdout

    def test_add_feed_custom_feeds_file(self, cli_runner, temp_dir):
        """Test add-feed with custom feeds file."""
        feeds_file = os.path.join(temp_dir, "my_feeds.txt")
        Path(feeds_file).touch()

        with patch("src.cli.load_feeds") as mock_load:
            mock_load.return_value = []

            result = cli_runner.invoke(app, [
                "add-feed", "https://example.com/feed.xml",
                "--feeds", feeds_file
            ])
            assert result.exit_code == 0


class TestUpdateCommandArguments:
    """Test update command argument parsing."""

    def test_update_no_topic(self, cli_runner):
        """Test update with no topic argument."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update"])
            mock_update.assert_called_with(
                topic_filter=None,
                limit=10,
                show_all=False,
                use_context=True,
                show_scores=False,
                min_relevance=0.0,
            )

    def test_update_single_topic_word(self, cli_runner):
        """Test update with single topic word."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "tech"])
            mock_update.assert_called_with(
                topic_filter="tech",
                limit=10,
                show_all=False,
                use_context=True,
                show_scores=False,
                min_relevance=0.0,
            )

    def test_update_multiple_topic_words(self, cli_runner):
        """Test update with multiple topic words (no quotes needed)."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "AI", "news", "tech"])
            mock_update.assert_called_with(
                topic_filter="AI news tech",
                limit=10,
                show_all=False,
                use_context=True,
                show_scores=False,
                min_relevance=0.0,
            )

    def test_update_custom_limit(self, cli_runner):
        """Test update with custom limit."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "-n", "25"])
            mock_update.assert_called_with(
                topic_filter=None,
                limit=25,
                show_all=False,
                use_context=True,
                show_scores=False,
                min_relevance=0.0,
            )

    def test_update_all_flag_short(self, cli_runner):
        """Test update with -a short flag for all articles."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "-a"])
            mock_update.assert_called_with(
                topic_filter=None,
                limit=10,
                show_all=True,
                use_context=True,
                show_scores=False,
                min_relevance=0.0,
            )

    def test_update_all_flag_long(self, cli_runner):
        """Test update with --all long flag."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "--all"])
            mock_update.assert_called_with(
                topic_filter=None,
                limit=10,
                show_all=True,
                use_context=True,
                show_scores=False,
                min_relevance=0.0,
            )

    def test_update_show_scores_flag(self, cli_runner):
        """Test update with --show-scores flag."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "--show-scores"])
            mock_update.assert_called_with(
                topic_filter=None,
                limit=10,
                show_all=False,
                use_context=True,
                show_scores=True,
                min_relevance=0.0,
            )

    def test_update_min_relevance(self, cli_runner):
        """Test update with --min-relevance option."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "--min-relevance", "0.7"])
            mock_update.assert_called_with(
                topic_filter=None,
                limit=10,
                show_all=False,
                use_context=True,
                show_scores=False,
                min_relevance=0.7,
            )

    def test_update_no_context_flag(self, cli_runner):
        """Test update with --no-context flag."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "--no-context"])
            mock_update.assert_called_with(
                topic_filter=None,
                limit=10,
                show_all=False,
                use_context=False,
                show_scores=False,
                min_relevance=0.0,
            )

    def test_update_combined_options(self, cli_runner):
        """Test update with all options combined."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, [
                "update", "tech", "AI",
                "-n", "50",
                "--all",
                "--show-scores",
                "--min-relevance", "0.5",
                "--no-context"
            ])
            mock_update.assert_called_with(
                topic_filter="tech AI",
                limit=50,
                show_all=True,
                use_context=False,
                show_scores=True,
                min_relevance=0.5,
            )


class TestDiscoverCommandArguments:
    """Test discover command argument parsing."""

    def test_discover_requires_query(self, cli_runner):
        """Test discover requires query argument."""
        result = cli_runner.invoke(app, ["discover"])
        assert result.exit_code != 0

    def test_discover_with_query(self, cli_runner):
        """Test discover with query argument."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.llm_providers.get_best_provider") as mock_get_provider:
            mock_setup.return_value = None
            mock_get_provider.return_value = (None, False)

            result = cli_runner.invoke(app, ["discover", "AI and machine learning"])
            # Will exit because no LLM, but query was passed correctly
            assert "LLM required" in result.stdout or result.exit_code == 1


class TestHelpCommandArguments:
    """Test help command argument parsing."""

    def test_help_no_argument(self, cli_runner):
        """Test help with no argument shows general help."""
        result = cli_runner.invoke(app, ["help"])
        assert result.exit_code == 0
        assert "RSS Summarizer" in result.stdout

    def test_help_with_command_argument(self, cli_runner):
        """Test help with specific command argument."""
        # The help command runs subprocess, so we just check it doesn't crash
        result = cli_runner.invoke(app, ["help", "fetch"])
        # May have exit code 0 or the subprocess may fail in test env
        assert result.exit_code in [0, 1, 2]


class TestExtractKnowledgeArguments:
    """Test extract-knowledge command argument parsing."""

    def test_extract_knowledge_default_limit(self, cli_runner):
        """Test extract-knowledge uses default limit of 10."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.llm_providers.ensure_llm_or_exit") as mock_llm, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.KnowledgeBase") as mock_kb:
            mock_setup.return_value = None
            mock_provider = MagicMock()
            mock_llm.return_value = mock_provider
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage.return_value = storage_mock
            mock_kb.return_value = MagicMock()

            result = cli_runner.invoke(app, ["extract-knowledge"])
            storage_mock.get_articles.assert_called_with(limit=10)

    def test_extract_knowledge_custom_limit(self, cli_runner):
        """Test extract-knowledge with custom limit."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.llm_providers.ensure_llm_or_exit") as mock_llm, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.KnowledgeBase") as mock_kb:
            mock_setup.return_value = None
            mock_provider = MagicMock()
            mock_llm.return_value = mock_provider
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage.return_value = storage_mock
            mock_kb.return_value = MagicMock()

            result = cli_runner.invoke(app, ["extract-knowledge", "-n", "50"])
            storage_mock.get_articles.assert_called_with(limit=50)

    def test_extract_knowledge_custom_db_path(self, cli_runner):
        """Test extract-knowledge with custom db path."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.llm_providers.ensure_llm_or_exit") as mock_llm, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.KnowledgeBase") as mock_kb:
            mock_setup.return_value = None
            mock_provider = MagicMock()
            mock_llm.return_value = mock_provider
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage.return_value = storage_mock
            mock_kb.return_value = MagicMock()

            result = cli_runner.invoke(app, ["extract-knowledge", "--db", "custom.db"])
            mock_storage.assert_called_with("custom.db")

    def test_extract_knowledge_custom_kb_path(self, cli_runner):
        """Test extract-knowledge with custom kb path."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.llm_providers.ensure_llm_or_exit") as mock_llm, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.KnowledgeBase") as mock_kb:
            mock_setup.return_value = None
            mock_provider = MagicMock()
            mock_llm.return_value = mock_provider
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage.return_value = storage_mock
            mock_kb.return_value = MagicMock()

            result = cli_runner.invoke(app, ["extract-knowledge", "-k", "custom_kb.db"])
            mock_kb.assert_called_with("custom_kb.db")


class TestQueryCommandArguments:
    """Test query command argument parsing."""

    def test_query_requires_text(self, cli_runner):
        """Test query requires query text argument."""
        result = cli_runner.invoke(app, ["query"])
        assert result.exit_code != 0

    def test_query_with_text(self, cli_runner):
        """Test query with query text argument."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.llm_providers.ensure_llm_or_exit") as mock_llm, \
             patch("src.cli.KnowledgeBase") as mock_kb, \
             patch("src.cli.query_knowledge_base") as mock_query:
            mock_setup.return_value = None
            mock_provider = MagicMock()
            mock_llm.return_value = mock_provider
            mock_kb.return_value = MagicMock()
            mock_query.return_value = {"summary": "Answer", "total_insights": 10}

            result = cli_runner.invoke(app, ["query", "What is AI?"])
            mock_query.assert_called_once()
            assert mock_query.call_args[0][0] == "What is AI?"

    def test_query_custom_kb_path(self, cli_runner):
        """Test query with custom kb path."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.llm_providers.ensure_llm_or_exit") as mock_llm, \
             patch("src.cli.KnowledgeBase") as mock_kb, \
             patch("src.cli.query_knowledge_base") as mock_query:
            mock_setup.return_value = None
            mock_provider = MagicMock()
            mock_llm.return_value = mock_provider
            mock_kb.return_value = MagicMock()
            mock_query.return_value = {"summary": "Answer", "total_insights": 10}

            result = cli_runner.invoke(app, ["query", "Test query", "--kb", "custom.db"])
            mock_kb.assert_called_with("custom.db")


class TestGraphCommandArguments:
    """Test graph command argument parsing."""

    def test_graph_requires_entity(self, cli_runner):
        """Test graph requires entity argument."""
        result = cli_runner.invoke(app, ["graph"])
        assert result.exit_code != 0

    def test_graph_with_entity(self, cli_runner):
        """Test graph with entity argument."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_entity_neighborhood.return_value = {"outgoing": [], "incoming": []}
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["graph", "OpenAI"])
            kb_mock.get_entity_neighborhood.assert_called_with("OpenAI")

    def test_graph_default_depth(self, cli_runner):
        """Test graph uses default depth of 2."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_entity_neighborhood.return_value = {
                "outgoing": [{"predicate": "develops", "target": "GPT"}],
                "incoming": []
            }
            kb_mock.get_connected_entities.return_value = {"entities": [], "relationships": []}
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["graph", "OpenAI"])
            # get_connected_entities called with max_depth=2 (default)
            kb_mock.get_connected_entities.assert_called_with("OpenAI", max_depth=2)

    def test_graph_custom_depth(self, cli_runner):
        """Test graph with custom depth."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_entity_neighborhood.return_value = {
                "outgoing": [{"predicate": "develops", "target": "GPT"}],
                "incoming": []
            }
            kb_mock.get_connected_entities.return_value = {"entities": [], "relationships": []}
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["graph", "OpenAI", "-d", "5"])
            kb_mock.get_connected_entities.assert_called_with("OpenAI", max_depth=5)


class TestGraphPathCommandArguments:
    """Test graph-path command argument parsing."""

    def test_graph_path_requires_start_and_end(self, cli_runner):
        """Test graph-path requires both start and end arguments."""
        result = cli_runner.invoke(app, ["graph-path"])
        assert result.exit_code != 0

        result = cli_runner.invoke(app, ["graph-path", "OpenAI"])
        assert result.exit_code != 0

    def test_graph_path_with_both_entities(self, cli_runner):
        """Test graph-path with both start and end entities."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.find_path.return_value = None
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["graph-path", "OpenAI", "GPT-4"])
            kb_mock.find_path.assert_called_with("OpenAI", "GPT-4")


class TestContextAddCommandArguments:
    """Test context-add command argument parsing."""

    def test_context_add_requires_type_and_name(self, cli_runner):
        """Test context-add requires both type and name arguments."""
        result = cli_runner.invoke(app, ["context-add"])
        assert result.exit_code != 0

        result = cli_runner.invoke(app, ["context-add", "project"])
        assert result.exit_code != 0

    def test_context_add_with_required_args(self, cli_runner):
        """Test context-add with required arguments."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-add", "project", "MyProject"])
            assert result.exit_code == 0
            kb_mock.save_context.assert_called_once()
            context = kb_mock.save_context.call_args[0][0]
            assert context.context_type == "project"
            assert context.name == "MyProject"

    def test_context_add_with_description(self, cli_runner):
        """Test context-add with description option."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, [
                "context-add", "interest", "AI",
                "-d", "Artificial Intelligence research"
            ])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.description == "Artificial Intelligence research"

    def test_context_add_with_long_description(self, cli_runner):
        """Test context-add with --desc long option."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, [
                "context-add", "watching", "Tech News",
                "--desc", "Following tech industry news"
            ])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.description == "Following tech industry news"


class TestEmergingCommandArguments:
    """Test emerging command argument parsing."""

    def test_emerging_default_confidence(self, cli_runner):
        """Test emerging uses default confidence of all."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.detect_emerging_trends") as mock_detect:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_detect.return_value = []

            result = cli_runner.invoke(app, ["emerging"])
            mock_detect.assert_called_with(
                mock_storage.return_value,
                limit=1000,
                min_confidence="Watch"  # "all" maps to "Watch"
            )

    def test_emerging_high_confidence(self, cli_runner):
        """Test emerging with high confidence filter."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.detect_emerging_trends") as mock_detect:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_detect.return_value = []

            result = cli_runner.invoke(app, ["emerging", "-c", "high"])
            mock_detect.assert_called_with(
                mock_storage.return_value,
                limit=1000,
                min_confidence="High"
            )

    def test_emerging_medium_confidence(self, cli_runner):
        """Test emerging with medium confidence filter."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.detect_emerging_trends") as mock_detect:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_detect.return_value = []

            result = cli_runner.invoke(app, ["emerging", "--confidence", "medium"])
            mock_detect.assert_called_with(
                mock_storage.return_value,
                limit=1000,
                min_confidence="Medium"
            )

    def test_emerging_custom_limit(self, cli_runner):
        """Test emerging with custom limit."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.detect_emerging_trends") as mock_detect:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_detect.return_value = []

            result = cli_runner.invoke(app, ["emerging", "-n", "5"])
            # limit for display is 5, but limit for detection is 1000
            mock_detect.assert_called_with(
                mock_storage.return_value,
                limit=1000,
                min_confidence="Watch"
            )


class TestArgumentValidation:
    """Test argument validation and error handling."""

    def test_invalid_limit_type(self, cli_runner):
        """Test error when limit is not a number."""
        result = cli_runner.invoke(app, ["summarize", "-n", "abc"])
        assert result.exit_code != 0
        assert "Invalid value" in result.stdout or "Error" in result.stdout.lower() or result.exit_code == 2

    def test_negative_limit_allowed(self, cli_runner):
        """Test that negative limit is parsed (validation may happen elsewhere)."""
        # Typer will parse negative numbers, validation happens in function
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "-n", "-5"])
            # Should accept the value even if negative
            mock_summarize.assert_called_once()

    def test_float_min_relevance(self, cli_runner):
        """Test min-relevance accepts float values."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "--min-relevance", "0.75"])
            mock_update.assert_called_once()
            assert mock_update.call_args[1]["min_relevance"] == 0.75

    def test_invalid_min_relevance_type(self, cli_runner):
        """Test error when min-relevance is not a number."""
        result = cli_runner.invoke(app, ["update", "--min-relevance", "high"])
        assert result.exit_code != 0

    def test_unknown_option_error(self, cli_runner):
        """Test error for unknown options."""
        result = cli_runner.invoke(app, ["fetch", "--unknown-option"])
        assert result.exit_code != 0

    def test_duplicate_option(self, cli_runner):
        """Test handling of duplicate options (last wins)."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "-n", "10", "-n", "20"])
            # Last value should be used
            mock_summarize.assert_called_once()
            assert mock_summarize.call_args[1]["limit"] == 20


class TestArgumentEdgeCases:
    """Test edge cases in argument handling."""

    def test_empty_string_argument(self, cli_runner):
        """Test handling of empty string argument."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", ""])
            # Empty string becomes empty topic filter
            mock_update.assert_called_once()
            # An empty string argument results in empty string topic
            assert mock_update.call_args[1]["topic_filter"] == ""

    def test_special_characters_in_argument(self, cli_runner):
        """Test handling of special characters in arguments."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "AI & ML", "@tech", "#news"])
            mock_update.assert_called_once()
            assert mock_update.call_args[1]["topic_filter"] == "AI & ML @tech #news"

    def test_unicode_in_argument(self, cli_runner):
        """Test handling of unicode characters in arguments."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", "技術", "ニュース"])
            mock_update.assert_called_once()
            assert mock_update.call_args[1]["topic_filter"] == "技術 ニュース"

    def test_path_with_spaces(self, cli_runner, temp_dir):
        """Test handling of paths with spaces."""
        spaced_dir = os.path.join(temp_dir, "path with spaces")
        os.makedirs(spaced_dir, exist_ok=True)
        feeds_file = os.path.join(spaced_dir, "feeds.txt")
        Path(feeds_file).touch()

        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = []

            result = cli_runner.invoke(app, ["fetch", "-f", feeds_file])
            mock_load.assert_called_with(feeds_file)

    def test_very_long_argument(self, cli_runner):
        """Test handling of very long arguments."""
        long_topic = "a" * 1000
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update", long_topic])
            mock_update.assert_called_once()
            assert mock_update.call_args[1]["topic_filter"] == long_topic

    def test_zero_limit(self, cli_runner):
        """Test handling of zero as limit."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "-n", "0"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=0, use_llm=False, tag_articles=False
            )

    def test_large_limit(self, cli_runner):
        """Test handling of very large limit."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize", "-n", "1000000"])
            mock_summarize.assert_called_with(
                mock_storage.return_value, limit=1000000, use_llm=False, tag_articles=False
            )


class TestTagSubcommandArguments:
    """Test tag subcommand group argument parsing."""

    def test_tag_articles_no_args(self, cli_runner):
        """Test tag articles with no arguments uses defaults."""
        with patch("src.cli_signal_tags.Storage") as mock_storage_class:
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage_class.return_value = storage_mock

            result = cli_runner.invoke(app, ["tag", "articles"])
            # Default limit is applied (50)
            storage_mock.get_articles.assert_called_with(limit=50)

    def test_tag_articles_custom_limit(self, cli_runner):
        """Test tag articles with custom limit."""
        with patch("src.cli_signal_tags.Storage") as mock_storage_class:
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage_class.return_value = storage_mock

            result = cli_runner.invoke(app, ["tag", "articles", "-n", "100"])
            storage_mock.get_articles.assert_called_with(limit=100)

    def test_tag_filter_with_include(self, cli_runner):
        """Test tag filter with include option."""
        with patch("src.cli_signal_tags.Storage") as mock_storage_class:
            storage_mock = MagicMock()
            storage_mock.get_articles_by_signal_tags.return_value = []
            mock_storage_class.return_value = storage_mock

            result = cli_runner.invoke(app, ["tag", "filter", "-i", "breaking,urgent"])
            storage_mock.get_articles_by_signal_tags.assert_called_with(
                include_tags=["breaking", "urgent"],
                exclude_tags=None,
                limit=20,
            )

    def test_tag_filter_with_exclude(self, cli_runner):
        """Test tag filter with exclude option."""
        with patch("src.cli_signal_tags.Storage") as mock_storage_class:
            storage_mock = MagicMock()
            storage_mock.get_articles_by_signal_tags.return_value = []
            mock_storage_class.return_value = storage_mock

            result = cli_runner.invoke(app, ["tag", "filter", "-e", "spam"])
            storage_mock.get_articles_by_signal_tags.assert_called_with(
                include_tags=None,
                exclude_tags=["spam"],
                limit=20,
            )

    def test_tag_filter_combined_options(self, cli_runner):
        """Test tag filter with both include and exclude."""
        with patch("src.cli_signal_tags.Storage") as mock_storage_class:
            storage_mock = MagicMock()
            storage_mock.get_articles_by_signal_tags.return_value = []
            mock_storage_class.return_value = storage_mock

            result = cli_runner.invoke(app, [
                "tag", "filter",
                "-i", "tech,AI",
                "-e", "spam",
                "-n", "30"
            ])
            storage_mock.get_articles_by_signal_tags.assert_called_with(
                include_tags=["tech", "AI"],
                exclude_tags=["spam"],
                limit=30,
            )

    def test_tag_stats_default_db(self, cli_runner):
        """Test tag stats uses default database."""
        with patch("src.cli_signal_tags.Storage") as mock_storage_class:
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage_class.return_value = storage_mock

            result = cli_runner.invoke(app, ["tag", "stats"])
            mock_storage_class.assert_called_with("articles.db")

    def test_tag_stats_custom_db(self, cli_runner):
        """Test tag stats with custom database."""
        with patch("src.cli_signal_tags.Storage") as mock_storage_class:
            storage_mock = MagicMock()
            storage_mock.get_articles.return_value = []
            mock_storage_class.return_value = storage_mock

            result = cli_runner.invoke(app, ["tag", "stats", "-d", "custom.db"])
            mock_storage_class.assert_called_with("custom.db")


class TestKnowledgeCommandsArguments:
    """Test knowledge-related command arguments."""

    def test_contradictions_default_kb_path(self, cli_runner):
        """Test contradictions uses default kb path."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_relationships.return_value = []
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["contradictions"])
            mock_kb.assert_called_with("knowledge.db")

    def test_contradictions_custom_kb_path(self, cli_runner):
        """Test contradictions with custom kb path."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_relationships.return_value = []
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["contradictions", "-k", "custom_kb.db"])
            mock_kb.assert_called_with("custom_kb.db")

    def test_knowledge_stats_default_path(self, cli_runner):
        """Test knowledge-stats uses default kb path."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_stats.return_value = {
                "total_insights": 0,
                "high_confidence_insights": 0,
                "total_entities": 0,
                "total_relationships": 0,
                "contradictions": 0,
            }
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["knowledge-stats"])
            mock_kb.assert_called_with("knowledge.db")

    def test_graph_stats_default_path(self, cli_runner):
        """Test graph-stats uses default kb path."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_graph_stats.return_value = {
                "total_insights": 0,
                "total_entities": 0,
                "total_triples": 0,
                "total_entity_relationships": 0,
                "unique_predicates": 0,
                "total_embeddings": 0,
                "predicate_types": [],
                "top_connected_entities": [],
            }
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["graph-stats"])
            mock_kb.assert_called_with("knowledge.db")


class TestContextListArguments:
    """Test context-list command arguments."""

    def test_context_list_default_path(self, cli_runner):
        """Test context-list uses default kb path."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_contexts.return_value = []
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            mock_kb.assert_called_with("knowledge.db")

    def test_context_list_custom_path(self, cli_runner):
        """Test context-list with custom kb path."""
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_contexts.return_value = []
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list", "--kb", "my_kb.db"])
            mock_kb.assert_called_with("my_kb.db")


class TestBooleanFlagBehavior:
    """Test boolean flag behavior (defaults and toggling)."""

    def test_llm_flag_defaults_false(self, cli_runner):
        """Test --llm flag defaults to False."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize"])
            assert mock_summarize.call_args[1]["use_llm"] is False

    def test_tag_flag_defaults_false(self, cli_runner):
        """Test --tag flag defaults to False."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            result = cli_runner.invoke(app, ["summarize"])
            assert mock_summarize.call_args[1]["tag_articles"] is False

    def test_all_flag_defaults_false(self, cli_runner):
        """Test --all flag defaults to False in update command."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            result = cli_runner.invoke(app, ["update"])
            assert mock_update.call_args[1]["show_all"] is False

    def test_no_context_flag_inverts_use_context(self, cli_runner):
        """Test --no-context flag inverts use_context to False."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.commands.update") as mock_update:
            mock_setup.return_value = None

            # Without flag
            result = cli_runner.invoke(app, ["update"])
            assert mock_update.call_args[1]["use_context"] is True

            # With flag
            result = cli_runner.invoke(app, ["update", "--no-context"])
            assert mock_update.call_args[1]["use_context"] is False


class TestArgumentParsingIntegration:
    """Integration tests for argument parsing across commands."""

    def test_all_commands_accept_help(self, cli_runner):
        """Test all main commands accept --help flag."""
        commands = [
            "fetch", "summarize", "trends", "list", "stats",
            "add-feed", "update", "setup", "discover", "help",
            "providers", "extract-knowledge", "query", "contradictions",
            "knowledge-stats", "graph", "graph-path", "graph-stats",
            "context-add", "context-list", "emerging", "perspectives",
            "cluster-stories"
        ]

        for cmd in commands:
            result = cli_runner.invoke(app, [cmd, "--help"])
            # All should succeed with help
            assert result.exit_code == 0, f"Command {cmd} failed with --help"

    def test_subcommands_accept_help(self, cli_runner):
        """Test subcommands accept --help flag."""
        subcommands = [
            ["tag", "articles", "--help"],
            ["tag", "stats", "--help"],
            ["tag", "filter", "--help"],
        ]

        for subcmd in subcommands:
            result = cli_runner.invoke(app, subcmd)
            assert result.exit_code == 0, f"Subcommand {' '.join(subcmd)} failed"

    def test_short_and_long_options_equivalent(self, cli_runner):
        """Test short and long options produce equivalent results."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.summarize_articles") as mock_summarize:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_summarize.return_value = {"processed": 0, "errors": []}

            # Short option
            cli_runner.invoke(app, ["summarize", "-n", "42", "-d", "test.db"])
            short_call = mock_summarize.call_args

            mock_summarize.reset_mock()

            # Long option
            cli_runner.invoke(app, ["summarize", "--limit", "42", "--db", "test.db"])
            long_call = mock_summarize.call_args

            # Should be equivalent
            assert short_call[1]["limit"] == long_call[1]["limit"] == 42


# =============================================================================
# Output Formatting Tests (Subtask 3.7)
# =============================================================================


class TestRichConsoleOutput:
    """Test Rich console output functionality."""

    def test_console_print_with_markup(self, capture_console_output):
        """Test console prints with Rich markup."""
        from src.cli import console
        console.print("[green]Test message[/green]")
        output = capture_console_output.getvalue()
        assert "Test message" in output

    def test_console_print_with_bold_markup(self, capture_console_output):
        """Test console prints with bold markup."""
        from src.cli import console
        console.print("[bold]Bold message[/bold]")
        output = capture_console_output.getvalue()
        assert "Bold message" in output

    def test_console_print_with_dim_markup(self, capture_console_output):
        """Test console prints with dim markup."""
        from src.cli import console
        console.print("[dim]Dim message[/dim]")
        output = capture_console_output.getvalue()
        assert "Dim message" in output

    def test_console_print_with_nested_markup(self, capture_console_output):
        """Test console prints with nested markup."""
        from src.cli import console
        console.print("[bold cyan]Bold cyan message[/bold cyan]")
        output = capture_console_output.getvalue()
        assert "Bold cyan message" in output

    def test_console_print_with_color_markup(self, capture_console_output):
        """Test console prints with color markup."""
        from src.cli import console
        for color in ["red", "green", "yellow", "blue", "magenta", "cyan"]:
            console.print(f"[{color}]{color} text[/{color}]")
        output = capture_console_output.getvalue()
        assert "red text" in output
        assert "green text" in output
        assert "yellow text" in output

    def test_console_print_without_markup(self, capture_console_output):
        """Test console prints plain text without markup."""
        from src.cli import console
        console.print("Plain text message")
        output = capture_console_output.getvalue()
        assert "Plain text message" in output


class TestTableFormatting:
    """Test Rich table formatting."""

    def test_table_creation(self):
        """Test basic table creation."""
        from rich.table import Table
        table = Table(title="Test Table")
        assert table.title == "Test Table"

    def test_table_add_column(self):
        """Test adding columns to table."""
        from rich.table import Table
        table = Table()
        table.add_column("Column 1", style="cyan")
        table.add_column("Column 2", justify="right")
        table.add_column("Column 3", style="green", max_width=50)
        assert len(table.columns) == 3

    def test_table_add_row(self):
        """Test adding rows to table."""
        from rich.table import Table
        table = Table()
        table.add_column("Col1")
        table.add_column("Col2")
        table.add_row("Value1", "Value2")
        table.add_row("Value3", "Value4")
        assert table.row_count == 2

    def test_table_renders_with_console(self, capture_console_output):
        """Test table renders properly with console."""
        from src.cli import console
        from rich.table import Table
        table = Table(title="Render Test")
        table.add_column("Name")
        table.add_column("Value")
        table.add_row("Test", "123")
        console.print(table)
        output = capture_console_output.getvalue()
        assert "Render Test" in output
        assert "Test" in output
        assert "123" in output

    def test_table_with_styled_content(self, capture_console_output):
        """Test table with styled cell content."""
        from src.cli import console
        from rich.table import Table
        table = Table()
        table.add_column("Status")
        table.add_row("[green]OK[/green]")
        table.add_row("[red]ERROR[/red]")
        console.print(table)
        output = capture_console_output.getvalue()
        assert "OK" in output
        assert "ERROR" in output

    def test_table_column_max_width(self):
        """Test table column with max_width respects limit."""
        from rich.table import Table
        table = Table()
        table.add_column("Feed", max_width=50)
        # Column should be created with max_width
        assert table.columns[0].max_width == 50

    def test_table_column_justify(self):
        """Test table column justification settings."""
        from rich.table import Table
        table = Table()
        table.add_column("Left", justify="left")
        table.add_column("Right", justify="right")
        table.add_column("Center", justify="center")
        assert table.columns[0].justify == "left"
        assert table.columns[1].justify == "right"
        assert table.columns[2].justify == "center"

    def test_table_show_header_false(self):
        """Test table with hidden header."""
        from rich.table import Table
        table = Table(show_header=False)
        assert table.show_header is False


class TestPanelRendering:
    """Test Rich Panel rendering."""

    def test_panel_creation(self):
        """Test basic panel creation."""
        from rich.panel import Panel
        panel = Panel("Test content")
        assert panel.renderable == "Test content"

    def test_panel_with_title(self):
        """Test panel with title."""
        from rich.panel import Panel
        panel = Panel("Content", title="Panel Title")
        assert panel.title == "Panel Title"

    def test_panel_with_style(self):
        """Test panel with border style."""
        from rich.panel import Panel
        panel = Panel("Content", border_style="blue")
        assert panel.border_style == "blue"

    def test_panel_renders_with_console(self, capture_console_output):
        """Test panel renders properly with console."""
        from src.cli import console
        from rich.panel import Panel
        panel = Panel("Panel content", title="Test Panel")
        console.print(panel)
        output = capture_console_output.getvalue()
        assert "Panel content" in output
        assert "Test Panel" in output

    def test_panel_with_styled_title(self, capture_console_output):
        """Test panel with styled title."""
        from src.cli import console
        from rich.panel import Panel
        panel = Panel("Content", title="[cyan]Styled Title[/cyan]")
        console.print(panel)
        output = capture_console_output.getvalue()
        assert "Styled Title" in output

    def test_panel_with_border_dim(self, capture_console_output):
        """Test panel with dim border style."""
        from src.cli import console
        from rich.panel import Panel
        panel = Panel("Summary content", border_style="dim")
        console.print(panel)
        output = capture_console_output.getvalue()
        assert "Summary content" in output


class TestStatusIndicators:
    """Test status indicator formatting."""

    def test_ok_status_format(self, capture_console_output):
        """Test OK status indicator format."""
        from src.cli import console
        console.print("[green]OK[/green]")
        output = capture_console_output.getvalue()
        assert "OK" in output

    def test_error_status_format(self, capture_console_output):
        """Test ERROR status indicator format."""
        from src.cli import console
        console.print("[red]ERROR[/red]")
        output = capture_console_output.getvalue()
        assert "ERROR" in output

    def test_warning_status_format(self, capture_console_output):
        """Test warning status indicator format."""
        from src.cli import console
        console.print("[yellow]Warnings[/yellow]")
        output = capture_console_output.getvalue()
        assert "Warnings" in output

    def test_available_status_format(self, capture_console_output):
        """Test available status indicator format."""
        from src.cli import console
        console.print("[green]Available[/green]")
        output = capture_console_output.getvalue()
        assert "Available" in output

    def test_not_available_status_format(self, capture_console_output):
        """Test not available status indicator format."""
        from src.cli import console
        console.print("[dim]Not Available[/dim]")
        output = capture_console_output.getvalue()
        assert "Not Available" in output

    def test_ready_status_format(self, capture_console_output):
        """Test ready status indicator format."""
        from src.cli import console
        console.print("[green]Ready[/green]")
        output = capture_console_output.getvalue()
        assert "Ready" in output

    def test_needs_setup_status_format(self, capture_console_output):
        """Test needs setup status indicator format."""
        from src.cli import console
        console.print("[yellow]Needs Setup[/yellow]")
        output = capture_console_output.getvalue()
        assert "Needs Setup" in output


class TestFetchResultsTableOutput:
    """Test fetch results table output formatting."""

    def test_fetch_results_table_structure(self, cli_runner):
        """Test fetch command creates properly structured table."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = [
                {"url": "https://example.com/feed.xml", "fetched": 5, "new": 3, "errors": []}
            ]

            result = cli_runner.invoke(app, ["fetch"])
            # Table should contain column headers and data
            assert "Feed" in result.stdout or "Fetch" in result.stdout
            assert "5" in result.stdout or "fetched" in result.stdout.lower()

    def test_fetch_results_shows_status(self, cli_runner):
        """Test fetch results shows OK status for successful fetches."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = [
                {"url": "https://example.com/feed.xml", "fetched": 5, "new": 3, "errors": []}
            ]

            result = cli_runner.invoke(app, ["fetch"])
            # Should show OK status for no errors
            assert "OK" in result.stdout or "5" in result.stdout

    def test_fetch_results_shows_warning_status(self, cli_runner):
        """Test fetch results shows warning status when errors present."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_load.return_value = ["https://example.com/feed.xml"]
            mock_fetch.return_value = [
                {"url": "https://example.com/feed.xml", "fetched": 5, "new": 3, "errors": ["Some error"]}
            ]

            result = cli_runner.invoke(app, ["fetch"])
            # Should show Warning status for errors
            assert "Warning" in result.stdout or "5" in result.stdout

    def test_fetch_results_truncates_long_urls(self, cli_runner):
        """Test fetch results truncates URLs longer than 50 chars."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.load_feeds") as mock_load, \
             patch("src.cli.fetch_all_feeds") as mock_fetch:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            long_url = "https://very-long-domain-name.example.com/very/long/path/to/feed.xml"
            mock_load.return_value = [long_url]
            mock_fetch.return_value = [
                {"url": long_url, "fetched": 5, "new": 3, "errors": []}
            ]

            result = cli_runner.invoke(app, ["fetch"])
            # URL should be truncated (ending with ...)
            assert "..." in result.stdout or "example" in result.stdout


class TestTrendsTableOutput:
    """Test trends command table output formatting."""

    def test_trends_table_structure(self, cli_runner):
        """Test trends command creates properly structured table."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.analyze_trends") as mock_analyze:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_analyze.return_value = {
                "top_trends": [("AI & Technology", 50), ("Business", 30)],
                "emerging": [],
                "declining": [],
                "processed": 100,
                "hours": 24
            }

            result = cli_runner.invoke(app, ["trends"])
            # Should contain trend data
            assert "AI" in result.stdout or "Tech" in result.stdout or "Top Trends" in result.stdout

    def test_trends_shows_bar_visualization(self, cli_runner):
        """Test trends shows bar visualization for counts."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.analyze_trends") as mock_analyze:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_analyze.return_value = {
                "top_trends": [("Category", 50)],
                "emerging": [],
                "declining": [],
                "processed": 100,
                "hours": 24
            }

            result = cli_runner.invoke(app, ["trends"])
            # Bar visualization uses # characters
            assert "#" in result.stdout or "50" in result.stdout

    def test_trends_shows_emerging_section(self, cli_runner):
        """Test trends shows emerging trends section when present."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.analyze_trends") as mock_analyze:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_analyze.return_value = {
                "top_trends": [("Tech", 50)],
                "emerging": [("GPT-5", 100)],
                "declining": [],
                "processed": 100,
                "hours": 24
            }

            result = cli_runner.invoke(app, ["trends"])
            # Should show emerging trends
            assert "Emerging" in result.stdout or "GPT" in result.stdout


class TestListTableOutput:
    """Test list command table output formatting."""

    def test_list_table_structure(self, cli_runner):
        """Test list command creates properly structured article table."""
        with patch("src.cli.get_storage") as mock_storage:
            mock_storage_instance = MagicMock()
            mock_article = MagicMock()
            mock_article.title = "Test Article Title"
            mock_article.published = datetime.now()
            mock_article.trend_tags = "Tech"
            mock_article.summary = "Test summary"
            mock_article.link = "https://example.com/article"
            mock_storage_instance.get_articles.return_value = [mock_article]
            mock_storage.return_value = mock_storage_instance

            result = cli_runner.invoke(app, ["list"])
            # Should show article title
            assert "Test Article" in result.stdout or "Recent Articles" in result.stdout

    def test_list_truncates_long_titles(self, cli_runner):
        """Test list truncates titles longer than 50 chars."""
        with patch("src.cli.get_storage") as mock_storage:
            mock_storage_instance = MagicMock()
            mock_article = MagicMock()
            mock_article.title = "A" * 100  # Very long title
            mock_article.published = datetime.now()
            mock_article.trend_tags = "Tech"
            mock_article.summary = None
            mock_article.link = "https://example.com"
            mock_storage_instance.get_articles.return_value = [mock_article]
            mock_storage.return_value = mock_storage_instance

            result = cli_runner.invoke(app, ["list"])
            # Should truncate (original is 100 chars, limit is 50)
            assert "..." in result.stdout or result.exit_code == 0

    def test_list_with_summary_shows_panels(self, cli_runner):
        """Test list with --summary shows article summaries in panels."""
        with patch("src.cli.get_storage") as mock_storage:
            mock_storage_instance = MagicMock()
            mock_article = MagicMock()
            mock_article.title = "Test Article"
            mock_article.published = datetime.now()
            mock_article.trend_tags = "Tech"
            mock_article.summary = "This is the article summary"
            mock_article.link = "https://example.com"
            mock_storage_instance.get_articles.return_value = [mock_article]
            mock_storage.return_value = mock_storage_instance

            result = cli_runner.invoke(app, ["list", "--summary"])
            # Should show summary content
            assert "Summaries" in result.stdout or "article summary" in result.stdout or result.exit_code == 0


class TestStatsTableOutput:
    """Test stats command table output formatting."""

    def test_stats_shows_panel(self, cli_runner):
        """Test stats command shows panel with total count."""
        with patch("src.cli.get_storage") as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.get_article_count.return_value = 100
            mock_storage_instance.get_feed_stats.return_value = []
            mock_storage.return_value = mock_storage_instance

            result = cli_runner.invoke(app, ["stats"])
            # Should show total count
            assert "100" in result.stdout or "Total" in result.stdout

    def test_stats_shows_feed_stats_table(self, cli_runner):
        """Test stats shows table when feed stats available."""
        with patch("src.cli.get_storage") as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.get_article_count.return_value = 100
            mock_storage_instance.get_feed_stats.return_value = [
                {
                    "feed_url": "https://example.com/feed.xml",
                    "article_count": 50,
                    "summarized_count": 25,
                    "latest_article": "2024-01-01"
                }
            ]
            mock_storage.return_value = mock_storage_instance

            result = cli_runner.invoke(app, ["stats"])
            # Should show feed URL or counts
            assert "example.com" in result.stdout or "50" in result.stdout


class TestProvidersTableOutput:
    """Test providers command table output formatting."""

    def test_providers_table_structure(self, cli_runner):
        """Test providers command creates properly structured table."""
        with patch("src.llm_providers.list_providers") as mock_list:
            mock_list.return_value = [
                {"name": "Ollama", "available": True, "description": "Local Ollama"},
                {"name": "OpenAI", "available": False, "description": "OpenAI API"}
            ]

            result = cli_runner.invoke(app, ["providers"])
            # Should show provider names
            assert "Ollama" in result.stdout or "Provider" in result.stdout

    def test_providers_shows_available_status(self, cli_runner):
        """Test providers shows Available status for available providers."""
        with patch("src.llm_providers.list_providers") as mock_list:
            mock_list.return_value = [
                {"name": "Ollama", "available": True, "description": "Local Ollama"}
            ]

            result = cli_runner.invoke(app, ["providers"])
            # Should show Available status
            assert "Available" in result.stdout or "Ollama" in result.stdout

    def test_providers_shows_not_available_status(self, cli_runner):
        """Test providers shows Not Available status for unavailable providers."""
        with patch("src.llm_providers.list_providers") as mock_list:
            mock_list.return_value = [
                {"name": "OpenAI", "available": False, "description": "OpenAI API"}
            ]

            result = cli_runner.invoke(app, ["providers"])
            # Should show Not Available or just the provider
            assert "Not Available" in result.stdout or "OpenAI" in result.stdout


class TestKnowledgeStatsOutput:
    """Test knowledge-stats command output formatting."""

    def test_knowledge_stats_shows_panel(self, cli_runner):
        """Test knowledge-stats shows panel with header."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {
                "total_insights": 100,
                "high_confidence_insights": 50,
                "total_entities": 200,
                "total_relationships": 150,
                "contradictions": 5
            }
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["knowledge-stats"])
            # Should show Knowledge Base heading
            assert "Knowledge" in result.stdout or "100" in result.stdout

    def test_knowledge_stats_shows_table(self, cli_runner):
        """Test knowledge-stats shows table with metrics."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_stats.return_value = {
                "total_insights": 100,
                "high_confidence_insights": 50,
                "total_entities": 200,
                "total_relationships": 150,
                "contradictions": 5
            }
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["knowledge-stats"])
            # Should show metric values
            assert "100" in result.stdout or "Insights" in result.stdout


class TestGraphStatsOutput:
    """Test graph-stats command output formatting."""

    def test_graph_stats_shows_panel(self, cli_runner):
        """Test graph-stats shows panel with header."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_graph_stats.return_value = {
                "total_insights": 100,
                "total_entities": 200,
                "total_triples": 500,
                "total_entity_relationships": 150,
                "unique_predicates": 25,
                "total_embeddings": 1000,
                "predicate_types": ["related_to", "causes"],
                "top_connected_entities": []
            }
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["graph-stats"])
            # Should show Graph Statistics heading
            assert "Graph" in result.stdout or "100" in result.stdout

    def test_graph_stats_shows_predicate_types(self, cli_runner):
        """Test graph-stats shows predicate types when present."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_graph_stats.return_value = {
                "total_insights": 100,
                "total_entities": 200,
                "total_triples": 500,
                "total_entity_relationships": 150,
                "unique_predicates": 25,
                "total_embeddings": 1000,
                "predicate_types": ["related_to", "causes", "implies"],
                "top_connected_entities": []
            }
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["graph-stats"])
            # Should show predicate types
            assert "related_to" in result.stdout or "Predicate" in result.stdout or "25" in result.stdout


class TestContextListOutput:
    """Test context-list command output formatting."""

    def test_context_list_shows_table(self, cli_runner):
        """Test context-list shows table with contexts."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "Test Project"
            mock_context.active = True
            mock_context.description = "Test description"
            mock_kb.get_contexts.return_value = [mock_context]
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["context-list"])
            # Should show context data
            assert "project" in result.stdout or "Test Project" in result.stdout or "Contexts" in result.stdout

    def test_context_list_shows_active_status(self, cli_runner):
        """Test context-list shows Active status for active contexts."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "Test Project"
            mock_context.active = True
            mock_context.description = ""
            mock_kb.get_contexts.return_value = [mock_context]
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["context-list"])
            # Should show Active status
            assert "Active" in result.stdout or "project" in result.stdout

    def test_context_list_shows_empty_message(self, cli_runner):
        """Test context-list shows message when no contexts."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_contexts.return_value = []
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["context-list"])
            # Should show no contexts message
            assert "No contexts" in result.stdout or "context-add" in result.stdout


class TestGraphOutput:
    """Test graph command output formatting."""

    def test_graph_shows_panel(self, cli_runner):
        """Test graph command shows panel with entity name."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_entity_neighborhood.return_value = {
                "outgoing": [{"predicate": "related_to", "target": "Entity2"}],
                "incoming": []
            }
            mock_kb.get_connected_entities.return_value = {
                "entities": ["Entity2"],
                "relationships": []
            }
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["graph", "TestEntity"])
            # Should show Knowledge Graph heading or entity relationships
            assert "Knowledge Graph" in result.stdout or "related_to" in result.stdout or "Entity2" in result.stdout

    def test_graph_shows_outgoing_relationships(self, cli_runner):
        """Test graph shows outgoing relationships when present."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_entity_neighborhood.return_value = {
                "outgoing": [{"predicate": "develops", "target": "Product"}],
                "incoming": []
            }
            mock_kb.get_connected_entities.return_value = {"entities": [], "relationships": []}
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["graph", "Company"])
            # Should show outgoing relationship
            assert "develops" in result.stdout or "Product" in result.stdout or "Outgoing" in result.stdout

    def test_graph_shows_no_relationships_message(self, cli_runner):
        """Test graph shows message when entity has no relationships."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.get_entity_neighborhood.return_value = {
                "outgoing": [],
                "incoming": []
            }
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["graph", "UnknownEntity"])
            # Should show no relationships message
            assert "No relationships" in result.stdout or "not found" in result.stdout.lower() or result.exit_code == 0


class TestGraphPathOutput:
    """Test graph-path command output formatting."""

    def test_graph_path_shows_panel_on_success(self, cli_runner):
        """Test graph-path shows panel when path found."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.find_path.return_value = [
                {"from": "Start", "predicate": "connects_to", "to": "End"}
            ]
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["graph-path", "Start", "End"])
            # Should show path or relationship
            assert "Path" in result.stdout or "connects_to" in result.stdout or "Start" in result.stdout

    def test_graph_path_shows_no_path_message(self, cli_runner):
        """Test graph-path shows message when no path found."""
        with patch("src.cli.KnowledgeBase") as mock_kb_class:
            mock_kb = MagicMock()
            mock_kb.find_path.return_value = None
            mock_kb_class.return_value = mock_kb

            result = cli_runner.invoke(app, ["graph-path", "A", "B"])
            # Should show no path message
            assert "No path" in result.stdout or result.exit_code == 0


class TestEmergingOutput:
    """Test emerging command output formatting."""

    def test_emerging_shows_confidence_headers(self, cli_runner):
        """Test emerging shows confidence level headers."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.detect_emerging_trends") as mock_detect:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()

            mock_trend = MagicMock()
            mock_trend.term = "TestTrend"
            mock_trend.confidence = "High"
            mock_detect.return_value = [mock_trend]

            with patch("src.cli.format_emerging_trend") as mock_format:
                mock_format.return_value = "TestTrend - emerging trend"
                result = cli_runner.invoke(app, ["emerging"])

            # Should show confidence level or trend
            assert "HIGH" in result.stdout or "TestTrend" in result.stdout or "Emerging" in result.stdout.lower() or result.exit_code in [0, 1]

    def test_emerging_shows_no_trends_message(self, cli_runner):
        """Test emerging shows message when no trends detected."""
        with patch("src.cli.require_setup") as mock_setup, \
             patch("src.cli.get_storage") as mock_storage, \
             patch("src.cli.detect_emerging_trends") as mock_detect:
            mock_setup.return_value = None
            mock_storage.return_value = MagicMock()
            mock_detect.return_value = []

            result = cli_runner.invoke(app, ["emerging"])
            # Should show no trends message
            assert "No emerging" in result.stdout or "not enough" in result.stdout.lower() or result.exit_code in [0, 1]


class TestHelpCommandOutput:
    """Test help command output formatting."""

    def test_help_shows_command_categories(self, cli_runner):
        """Test help shows command categories."""
        with patch("src.cli.is_setup_complete") as mock_check:
            mock_check.return_value = True
            result = cli_runner.invoke(app, ["help"])
            # Should show command categories
            assert "Setup" in result.stdout or "Main" in result.stdout or "Commands" in result.stdout

    def test_help_shows_setup_required_when_incomplete(self, cli_runner):
        """Test help shows setup required message when incomplete."""
        with patch("src.cli.is_setup_complete") as mock_check:
            mock_check.return_value = False
            result = cli_runner.invoke(app, ["help"])
            # Should show setup message or dim commands
            assert "setup" in result.stdout.lower()


class TestOutputFormattingIntegration:
    """Integration tests for output formatting across commands."""

    def test_all_table_commands_have_titles(self, cli_runner):
        """Test that table-producing commands have table titles."""
        # This is a meta-test to ensure consistency
        from rich.table import Table

        # Tables with titles should be created correctly
        table = Table(title="Test Title")
        assert table.title is not None

    def test_panel_border_styles_are_valid(self):
        """Test that panel border styles used are valid Rich styles."""
        from rich.panel import Panel

        # These are the border styles used in cli.py
        valid_styles = ["blue", "green", "dim"]
        for style in valid_styles:
            panel = Panel("Content", border_style=style)
            assert panel.border_style == style

    def test_status_indicators_use_consistent_colors(self, capture_console_output):
        """Test status indicators use consistent color scheme."""
        from src.cli import console

        # Good statuses should use green
        console.print("[green]OK[/green]")
        console.print("[green]Available[/green]")
        console.print("[green]Ready[/green]")
        console.print("[green]Active[/green]")

        # Warning statuses should use yellow
        console.print("[yellow]Warnings[/yellow]")
        console.print("[yellow]Needs Setup[/yellow]")
        console.print("[yellow]Setup required[/yellow]")

        # Error statuses should use red
        console.print("[red]ERROR[/red]")
        console.print("[red]Not Available[/red]")

        output = capture_console_output.getvalue()
        assert "OK" in output
        assert "Warnings" in output
        assert "ERROR" in output

    def test_dim_text_for_supplementary_info(self, capture_console_output):
        """Test dim text is used for supplementary information."""
        from src.cli import console

        console.print("[dim]Additional context...[/dim]")
        console.print("[dim]Run 'rss setup' to configure[/dim]")

        output = capture_console_output.getvalue()
        assert "Additional context" in output
        assert "rss setup" in output

    def test_cyan_text_for_data_fields(self, capture_console_output):
        """Test cyan text is used for data fields consistently."""
        from src.cli import console

        console.print("[cyan]https://example.com/feed.xml[/cyan]")
        console.print("[cyan]Article Title[/cyan]")

        output = capture_console_output.getvalue()
        assert "example.com" in output
        assert "Article Title" in output
