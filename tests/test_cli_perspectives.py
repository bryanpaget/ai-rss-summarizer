"""Tests for cli_perspectives.py - CLI commands for perspective synthesis."""

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
import typer

from src.cli_perspectives import add_perspective_commands


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def app():
    """Create a test Typer app with perspective commands."""
    test_app = typer.Typer()
    add_perspective_commands(test_app)
    return test_app


@pytest.fixture
def mock_cluster():
    """Create a mock story cluster."""
    return {
        "id": "cluster-123",
        "title": "Test Story About Technology",
        "created_at": "2026-01-12T10:00:00",
    }


@pytest.fixture
def mock_article():
    """Create a mock article."""
    article = MagicMock()
    article.id = "article-1"
    article.title = "Test Article"
    article.content = "Article content"
    article.source = "Test Source"
    return article


@pytest.fixture
def mock_perspective():
    """Create a mock Perspective object."""
    perspective = MagicMock()
    perspective.content = "This is the synthesized perspective content."
    perspective.confidence = 0.85
    return perspective


# =============================================================================
# Tests for add_perspective_commands
# =============================================================================


class TestAddPerspectiveCommands:
    """Tests for the add_perspective_commands function."""

    def test_registers_three_commands(self, app):
        """Test that exactly 3 commands are registered."""
        assert len(app.registered_commands) == 3

    def test_registers_perspective_config_command(self, app):
        """Test that perspective-config command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "perspective-config" in command_names

    def test_registers_cluster_stories_command(self, app):
        """Test that cluster-stories command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "cluster-stories" in command_names

    def test_add_perspective_commands_returns_none(self):
        """Test that add_perspective_commands returns None (modifies app in place)."""
        test_app = typer.Typer()
        result = add_perspective_commands(test_app)
        assert result is None

    def test_can_add_to_empty_app(self):
        """Test commands can be added to empty Typer app."""
        test_app = typer.Typer()
        assert len(test_app.registered_commands) == 0
        add_perspective_commands(test_app)
        assert len(test_app.registered_commands) == 3


# =============================================================================
# Tests for perspectives command
# =============================================================================


class TestPerspectivesCommand:
    """Tests for the perspectives command."""

    def test_perspectives_no_clusters_exits(self, runner, app):
        """Test perspectives exits when no clusters exist."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.llm_providers.get_best_provider") as mock_get_provider, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.perspectives.get_user_perspective_config") as mock_config, \
             patch("src.storage_perspectives.add_perspective_methods"):
            mock_storage = MagicMock()
            mock_storage.get_story_clusters.return_value = []
            MockStorage.return_value = mock_storage
            mock_get_provider.return_value = (MagicMock(), True)
            mock_update.return_value = {"processed": 0, "new_clusters": 0}
            mock_config.return_value = {"default_categories": ["consensus"]}

            result = runner.invoke(app, ["perspectives"])

            assert result.exit_code == 1
            assert "No story clusters found" in result.stdout

    def test_perspectives_invalid_category_exits(self, runner, app):
        """Test perspectives exits with invalid category."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.llm_providers.get_best_provider") as mock_get_provider, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.perspectives.get_user_perspective_config") as mock_config, \
             patch("src.storage_perspectives.add_perspective_methods"), \
             patch("src.perspectives.PERSPECTIVE_CATEGORIES", {"consensus": {"name": "Consensus"}}):
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage
            mock_get_provider.return_value = (MagicMock(), True)
            mock_update.return_value = {"processed": 0, "new_clusters": 0}
            mock_config.return_value = {"default_categories": ["consensus"]}

            result = runner.invoke(app, ["perspectives", "--categories", "invalid-cat"])

            assert result.exit_code == 1
            assert "Invalid categories" in result.stdout

    def test_perspectives_story_id_not_found(self, runner, app):
        """Test perspectives with non-existent story_id."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.llm_providers.get_best_provider") as mock_get_provider, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.perspectives.get_user_perspective_config") as mock_config, \
             patch("src.storage_perspectives.add_perspective_methods"), \
             patch("src.perspectives.PERSPECTIVE_CATEGORIES", {"consensus": {"name": "Consensus"}}):
            mock_storage = MagicMock()
            mock_storage.get_story_cluster.return_value = None
            MockStorage.return_value = mock_storage
            mock_get_provider.return_value = (MagicMock(), True)
            mock_update.return_value = {"processed": 0, "new_clusters": 0}
            mock_config.return_value = {"default_categories": ["consensus"]}

            result = runner.invoke(app, ["perspectives", "nonexistent-id"])

            assert result.exit_code == 1
            assert "Story cluster not found" in result.stdout

    def test_perspectives_story_id_no_articles(self, runner, app, mock_cluster):
        """Test perspectives with story_id that has no articles."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.llm_providers.get_best_provider") as mock_get_provider, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.perspectives.get_user_perspective_config") as mock_config, \
             patch("src.storage_perspectives.add_perspective_methods"), \
             patch("src.perspectives.PERSPECTIVE_CATEGORIES", {"consensus": {"name": "Consensus"}}):
            mock_storage = MagicMock()
            mock_storage.get_story_cluster.return_value = mock_cluster
            mock_storage.get_articles_by_cluster.return_value = []
            MockStorage.return_value = mock_storage
            mock_get_provider.return_value = (MagicMock(), True)
            mock_update.return_value = {"processed": 0, "new_clusters": 0}
            mock_config.return_value = {"default_categories": ["consensus"]}

            result = runner.invoke(app, ["perspectives", "cluster-123"])

            assert result.exit_code == 1
            assert "No articles in this story cluster" in result.stdout

    def test_perspectives_displays_story_perspectives(
        self, runner, app, mock_cluster, mock_article, mock_perspective
    ):
        """Test perspectives displays perspectives for specific story."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.llm_providers.get_best_provider") as mock_get_provider, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.perspectives.get_user_perspective_config") as mock_config, \
             patch("src.storage_perspectives.add_perspective_methods"), \
             patch("src.perspectives.synthesize_perspectives") as mock_synth, \
             patch("src.perspectives.PERSPECTIVE_CATEGORIES", {
                 "consensus": {"name": "Consensus", "description": "Common ground"}
             }):
            mock_storage = MagicMock()
            mock_storage.get_story_cluster.return_value = mock_cluster
            mock_storage.get_articles_by_cluster.return_value = [mock_article, mock_article]
            MockStorage.return_value = mock_storage
            mock_get_provider.return_value = (MagicMock(), True)
            mock_update.return_value = {"processed": 0, "new_clusters": 0}
            mock_config.return_value = {"default_categories": ["consensus"]}
            mock_synth.return_value = {"consensus": mock_perspective}

            result = runner.invoke(app, ["perspectives", "cluster-123"])

            assert result.exit_code == 0
            assert "Test Story About Technology" in result.stdout


# =============================================================================
# Tests for perspective-config command
# =============================================================================


class TestPerspectiveConfigCommand:
    """Tests for the perspective-config command."""

    def test_config_displays_current_settings(self, runner, app):
        """Test perspective-config displays current settings."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.perspectives.get_user_perspective_config") as mock_config, \
             patch("src.storage_perspectives.add_perspective_methods"), \
             patch("src.perspectives.PERSPECTIVE_CATEGORIES", {
                 "consensus": {"name": "Consensus", "description": "Common ground"},
                 "contested": {"name": "Contested", "description": "Disputed points"},
             }), \
             patch("src.perspectives.DEFAULT_CATEGORIES", ["consensus"]):
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage
            mock_config.return_value = {"default_categories": ["consensus"]}

            result = runner.invoke(app, ["perspective-config"])

            assert result.exit_code == 0
            assert "Current perspective settings" in result.stdout
            assert "Consensus" in result.stdout


# =============================================================================
# Tests for cluster-stories command
# =============================================================================


class TestClusterStoriesCommand:
    """Tests for the cluster-stories command."""

    def test_cluster_stories_runs_clustering(self, runner, app):
        """Test cluster-stories runs the clustering process."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.storage_perspectives.add_perspective_methods"):
            mock_storage = MagicMock()
            mock_storage.get_story_clusters.return_value = []
            MockStorage.return_value = mock_storage
            mock_update.return_value = {
                "processed": 10,
                "new_clusters": 3,
                "added_to_existing": 5,
                "skipped": 2,
            }

            result = runner.invoke(app, ["cluster-stories"])

            assert result.exit_code == 0
            assert "Processed" in result.stdout
            mock_update.assert_called_once()

    def test_cluster_stories_force_option(self, runner, app):
        """Test cluster-stories with --force option uses longer lookback."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.storage_perspectives.add_perspective_methods"):
            mock_storage = MagicMock()
            mock_storage.get_story_clusters.return_value = []
            MockStorage.return_value = mock_storage
            mock_update.return_value = {
                "processed": 20,
                "new_clusters": 5,
                "added_to_existing": 10,
                "skipped": 5,
            }

            result = runner.invoke(app, ["cluster-stories", "--force"])

            assert result.exit_code == 0
            # Force uses 168 hours lookback
            mock_update.assert_called_once_with(mock_storage, lookback_hours=168)

    def test_cluster_stories_shows_top_clusters(self, runner, app, mock_cluster, mock_article):
        """Test cluster-stories shows top clusters after processing."""
        with patch("src.storage.Storage") as MockStorage, \
             patch("src.clustering.update_story_clusters") as mock_update, \
             patch("src.storage_perspectives.add_perspective_methods"):
            mock_storage = MagicMock()
            mock_storage.get_story_clusters.return_value = [mock_cluster]
            mock_storage.get_articles_by_cluster.return_value = [mock_article, mock_article]
            MockStorage.return_value = mock_storage
            mock_update.return_value = {
                "processed": 10,
                "new_clusters": 3,
                "added_to_existing": 5,
                "skipped": 2,
            }

            result = runner.invoke(app, ["cluster-stories"])

            assert result.exit_code == 0
            assert "Top story clusters" in result.stdout


# =============================================================================
# Tests for update_story_clusters function
# =============================================================================


class TestUpdateStoryClusters:
    """Tests for the update_story_clusters function in clustering.py."""

    def test_function_exists(self):
        """Test that update_story_clusters function exists."""
        from src.clustering import update_story_clusters
        assert callable(update_story_clusters)

    def test_returns_expected_keys(self):
        """Test that function returns expected dictionary keys."""
        from src.clustering import update_story_clusters
        with patch("src.llm_providers.get_best_provider") as mock_provider:
            mock_provider.return_value = (None, False)  # No LLM

            # Create a minimal mock storage
            mock_storage = MagicMock()
            mock_storage.get_articles.return_value = []

            result = update_story_clusters(mock_storage)

            assert 'processed' in result
            assert 'new_clusters' in result
            assert 'added_to_existing' in result
            assert 'skipped' in result

    def test_no_llm_returns_zeros(self):
        """Test returns zeros when no LLM is available."""
        from src.clustering import update_story_clusters
        with patch("src.llm_providers.get_best_provider") as mock_provider:
            mock_provider.return_value = (None, False)

            mock_storage = MagicMock()
            result = update_story_clusters(mock_storage)

            assert result['processed'] == 0
            assert result['new_clusters'] == 0


# =============================================================================
# Tests for module import
# =============================================================================


class TestModuleImport:
    """Tests for module import behavior."""

    def test_module_imports_successfully(self):
        """Test that cli_perspectives module can be imported."""
        from src import cli_perspectives
        assert cli_perspectives is not None

    def test_add_perspective_commands_is_callable(self):
        """Test that add_perspective_commands is a callable function."""
        from src.cli_perspectives import add_perspective_commands
        assert callable(add_perspective_commands)

    def test_console_is_initialized(self):
        """Test that console is initialized in the module."""
        from src.cli_perspectives import console
        assert console is not None
