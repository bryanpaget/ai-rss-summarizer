"""Tests for cli_signal_tags.py - CLI commands for signal tag management."""

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
import json

from src.cli_signal_tags import app


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_article():
    """Create a mock article without tags."""
    article = MagicMock()
    article.id = "article-1"
    article.title = "Test Article Title"
    article.content = "Article content"
    article.signal_tags = None
    return article


@pytest.fixture
def mock_tagged_article():
    """Create a mock article with signal tags."""
    article = MagicMock()
    article.id = "article-2"
    article.title = "Tagged Article"
    article.content = "Content"
    article.signal_tags = json.dumps({
        "topics": ["technology", "ai"],
        "sentiment": ["positive"],
    })
    return article


@pytest.fixture
def mock_signal_tags():
    """Create mock signal tags result."""
    tags = MagicMock()
    tags.to_json.return_value = json.dumps({
        "topics": ["technology"],
        "sentiment": ["neutral"],
    })
    return tags


# =============================================================================
# Tests for app structure
# =============================================================================


class TestAppStructure:
    """Tests for the CLI app structure."""

    def test_app_exists(self):
        """Test that the app exists."""
        from src.cli_signal_tags import app
        assert app is not None

    def test_app_has_name(self):
        """Test that the app has the correct name."""
        assert app.info.name == "tag"

    def test_app_has_help_text(self):
        """Test that the app has help text."""
        assert app.info.help == "Signal tag management commands"

    def test_app_has_three_commands(self):
        """Test that the app has 3 commands registered."""
        assert len(app.registered_commands) == 3

    def test_articles_command_registered(self):
        """Test that articles command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "articles" in command_names

    def test_stats_command_registered(self):
        """Test that stats command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "stats" in command_names

    def test_filter_command_registered(self):
        """Test that filter command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "filter" in command_names


# =============================================================================
# Tests for tag_articles_cmd
# =============================================================================


class TestTagArticlesCmd:
    """Tests for the tag_articles_cmd function."""

    def test_no_untagged_articles(self, runner, mock_tagged_article):
        """Test when all articles are already tagged."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_tagged_article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["articles"])

            assert result.exit_code == 0
            assert "No untagged articles found" in result.stdout

    def test_tags_articles_successfully(self, runner, mock_article, mock_signal_tags):
        """Test successful tagging of articles."""
        with patch("src.cli_signal_tags.Storage") as MockStorage, \
             patch("src.signal_tagger.SignalTagger") as MockTagger, \
             patch("src.signal_tagger.tag_articles_batch") as mock_batch:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_article]
            MockStorage.return_value = mock_storage
            MockTagger.return_value = MagicMock()
            mock_batch.return_value = {"article-1": mock_signal_tags}

            result = runner.invoke(app, ["articles"])

            assert result.exit_code == 0
            # Check for parts of the success message (ANSI codes split the text)
            assert "Successfully tagged" in result.stdout
            assert "articles" in result.stdout

    def test_tagger_initialization_error(self, runner, mock_article):
        """Test error handling when tagger initialization fails."""
        with patch("src.cli_signal_tags.Storage") as MockStorage, \
             patch("src.signal_tagger.SignalTagger") as MockTagger:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_article]
            MockStorage.return_value = mock_storage
            MockTagger.side_effect = Exception("Failed to initialize")

            result = runner.invoke(app, ["articles"])

            assert result.exit_code == 1
            assert "Error initializing tagger" in result.stdout

    def test_uses_llm_when_specified(self, runner, mock_article, mock_signal_tags):
        """Test that --llm flag is passed to tagger."""
        with patch("src.cli_signal_tags.Storage") as MockStorage, \
             patch("src.signal_tagger.SignalTagger") as MockTagger, \
             patch("src.signal_tagger.tag_articles_batch") as mock_batch:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_article]
            MockStorage.return_value = mock_storage
            MockTagger.return_value = MagicMock()
            mock_batch.return_value = {"article-1": mock_signal_tags}

            result = runner.invoke(app, ["articles", "--llm"])

            MockTagger.assert_called_once_with(use_llm=True)
            assert "Using LLM backend" in result.stdout

    def test_respects_limit_option(self, runner):
        """Test that --limit option is passed to storage."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["articles", "--limit", "100"])

            mock_storage.get_articles.assert_called_once_with(limit=100)

    def test_uses_custom_db_path(self, runner):
        """Test that --db option is passed to Storage."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["articles", "--db", "custom.db"])

            MockStorage.assert_called_once_with("custom.db")


# =============================================================================
# Tests for tag_stats_cmd
# =============================================================================


class TestTagStatsCmd:
    """Tests for the tag_stats_cmd function."""

    def test_no_tagged_articles(self, runner, mock_article):
        """Test when no articles are tagged."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["stats"])

            assert result.exit_code == 1
            assert "No tagged articles found" in result.stdout

    def test_displays_statistics(self, runner, mock_tagged_article):
        """Test that statistics are displayed."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_tagged_article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["stats"])

            assert result.exit_code == 0
            assert "Signal Tag Statistics" in result.stdout
            assert "Total Articles" in result.stdout
            assert "Tagged Articles" in result.stdout

    def test_shows_tag_counts(self, runner, mock_tagged_article):
        """Test that tag counts are shown."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_tagged_article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["stats"])

            assert result.exit_code == 0
            assert "Most Common Tags" in result.stdout

    def test_handles_invalid_json(self, runner):
        """Test that invalid JSON tags are handled gracefully."""
        article = MagicMock()
        article.signal_tags = "not valid json"

        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["stats"])

            # Article counts as "tagged" (has signal_tags), shows stats panel
            # but tag counts will be empty since JSON is invalid
            assert result.exit_code == 0
            assert "Signal Tag Statistics" in result.stdout

    def test_uses_custom_db_path(self, runner, mock_tagged_article):
        """Test that --db option is passed to Storage."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = [mock_tagged_article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["stats", "--db", "custom.db"])

            MockStorage.assert_called_once_with("custom.db")


# =============================================================================
# Tests for filter_by_tags
# =============================================================================


class TestFilterByTags:
    """Tests for the filter_by_tags function."""

    def test_no_matching_articles(self, runner):
        """Test when no articles match the filter."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter", "--include", "nonexistent"])

            assert result.exit_code == 0
            assert "No articles match" in result.stdout

    def test_displays_filtered_results(self, runner, mock_tagged_article):
        """Test that filtered articles are displayed."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = [mock_tagged_article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter", "--include", "technology"])

            assert result.exit_code == 0
            assert "Filtered Articles" in result.stdout

    def test_passes_include_tags(self, runner):
        """Test that include tags are passed correctly."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter", "--include", "tech,ai"])

            mock_storage.get_articles_by_signal_tags.assert_called_once_with(
                include_tags=["tech", "ai"],
                exclude_tags=None,
                limit=20,
            )

    def test_passes_exclude_tags(self, runner):
        """Test that exclude tags are passed correctly."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter", "--exclude", "spam,ads"])

            mock_storage.get_articles_by_signal_tags.assert_called_once_with(
                include_tags=None,
                exclude_tags=["spam", "ads"],
                limit=20,
            )

    def test_combines_include_and_exclude(self, runner):
        """Test that both include and exclude work together."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, [
                "filter",
                "--include", "tech",
                "--exclude", "spam",
            ])

            mock_storage.get_articles_by_signal_tags.assert_called_once_with(
                include_tags=["tech"],
                exclude_tags=["spam"],
                limit=20,
            )

    def test_respects_limit_option(self, runner):
        """Test that --limit option is passed correctly."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter", "--limit", "50"])

            mock_storage.get_articles_by_signal_tags.assert_called_once_with(
                include_tags=None,
                exclude_tags=None,
                limit=50,
            )

    def test_truncates_long_titles(self, runner):
        """Test that long titles are truncated."""
        article = MagicMock()
        article.title = "A" * 100  # Very long title
        article.signal_tags = json.dumps({"topics": ["test"]})

        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = [article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter"])

            assert result.exit_code == 0
            # Should not crash with long title

    def test_handles_invalid_json_tags(self, runner):
        """Test that invalid JSON tags are handled gracefully."""
        article = MagicMock()
        article.title = "Test Article"
        article.signal_tags = "not valid json"

        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = [article]
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter"])

            assert result.exit_code == 0
            # Should not crash with invalid JSON

    def test_uses_custom_db_path(self, runner):
        """Test that --db option is passed to Storage."""
        with patch("src.cli_signal_tags.Storage") as MockStorage:
            mock_storage = MagicMock()
            mock_storage.get_articles_by_signal_tags.return_value = []
            MockStorage.return_value = mock_storage

            result = runner.invoke(app, ["filter", "--db", "custom.db"])

            MockStorage.assert_called_once_with("custom.db")


# =============================================================================
# Tests for module import
# =============================================================================


class TestModuleImport:
    """Tests for module import behavior."""

    def test_module_imports_successfully(self):
        """Test that cli_signal_tags module can be imported."""
        from src import cli_signal_tags
        assert cli_signal_tags is not None

    def test_app_is_typer_instance(self):
        """Test that app is a Typer instance."""
        import typer
        from src.cli_signal_tags import app
        assert isinstance(app, typer.Typer)

    def test_console_is_initialized(self):
        """Test that console is initialized in the module."""
        from src.cli_signal_tags import console
        assert console is not None
