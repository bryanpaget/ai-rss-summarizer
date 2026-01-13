"""Tests for cli_context.py - CLI commands for user context management."""

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from src.cli_context import app


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_context():
    """Create a mock user context."""
    ctx = MagicMock()
    ctx.id = "ctx-1"
    ctx.context_type = "project"
    ctx.name = "Test Project"
    ctx.description = "A test project"
    ctx.active = True
    return ctx


# =============================================================================
# Tests for app structure
# =============================================================================


class TestAppStructure:
    """Tests for the CLI app structure."""

    def test_app_exists(self):
        """Test that the app exists."""
        from src.cli_context import app
        assert app is not None

    def test_app_has_name(self):
        """Test that the app has the correct name."""
        assert app.info.name == "context"

    def test_app_has_help_text(self):
        """Test that the app has help text."""
        assert app.info.help == "User context management commands"

    def test_app_has_four_commands(self):
        """Test that the app has 4 commands registered."""
        assert len(app.registered_commands) == 4

    def test_add_command_registered(self):
        """Test that add command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "add" in command_names

    def test_list_command_registered(self):
        """Test that list command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "list" in command_names

    def test_remove_command_registered(self):
        """Test that remove command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "remove" in command_names

    def test_show_command_registered(self):
        """Test that show command is registered."""
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "show" in command_names


# =============================================================================
# Tests for context callback (no subcommand)
# =============================================================================


class TestContextNoSubcommand:
    """Tests for context command with no subcommand."""

    def test_no_subcommand_shows_help(self, runner):
        """Test that running without subcommand shows help."""
        result = runner.invoke(app)
        assert result.exit_code == 0
        assert "User Context Management" in result.output
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

    def test_no_subcommand_shows_context_types(self, runner):
        """Test that help shows context types."""
        result = runner.invoke(app)
        assert "project" in result.output
        assert "interest" in result.output
        assert "watching" in result.output


# =============================================================================
# Tests for add command
# =============================================================================


class TestAddCommand:
    """Tests for the add command."""

    @patch('src.cli_context.KnowledgeBase')
    def test_add_project_context(self, mock_kb_class, runner):
        """Test adding a project context."""
        mock_kb = MagicMock()
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["add", "project", "My Project"])

        assert result.exit_code == 0
        assert "Added project" in result.output
        assert "My Project" in result.output
        mock_kb.save_context.assert_called_once()

    @patch('src.cli_context.KnowledgeBase')
    def test_add_interest_context(self, mock_kb_class, runner):
        """Test adding an interest context."""
        mock_kb = MagicMock()
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["add", "interest", "Machine Learning"])

        assert result.exit_code == 0
        assert "Added interest" in result.output
        mock_kb.save_context.assert_called_once()

    @patch('src.cli_context.KnowledgeBase')
    def test_add_with_description(self, mock_kb_class, runner):
        """Test adding context with description."""
        mock_kb = MagicMock()
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["add", "project", "My Project", "--desc", "Building something"])

        assert result.exit_code == 0
        assert "Building something" in result.output

    def test_add_invalid_type(self, runner):
        """Test adding context with invalid type."""
        result = runner.invoke(app, ["add", "invalid", "Test"])

        assert result.exit_code == 1
        assert "Invalid context type" in result.output


# =============================================================================
# Tests for list command
# =============================================================================


class TestListCommand:
    """Tests for the list command."""

    @patch('src.cli_context.KnowledgeBase')
    def test_list_contexts(self, mock_kb_class, runner, mock_context):
        """Test listing contexts."""
        mock_kb = MagicMock()
        mock_kb.get_contexts.return_value = [mock_context]
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "Test Project" in result.output
        assert "project" in result.output

    @patch('src.cli_context.KnowledgeBase')
    def test_list_empty(self, mock_kb_class, runner):
        """Test listing when no contexts exist."""
        mock_kb = MagicMock()
        mock_kb.get_contexts.return_value = []
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No contexts found" in result.output

    @patch('src.cli_context.KnowledgeBase')
    def test_list_filter_by_type(self, mock_kb_class, runner, mock_context):
        """Test listing with type filter."""
        mock_kb = MagicMock()
        mock_kb.get_contexts.return_value = [mock_context]
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["list", "--type", "project"])

        assert result.exit_code == 0
        mock_kb.get_contexts.assert_called_once()


# =============================================================================
# Tests for remove command
# =============================================================================


class TestRemoveCommand:
    """Tests for the remove command."""

    @patch('src.cli_context.KnowledgeBase')
    def test_remove_existing_context(self, mock_kb_class, runner, mock_context):
        """Test removing an existing context."""
        mock_kb = MagicMock()
        mock_kb.get_contexts.return_value = [mock_context]
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["remove", "Test Project"])

        assert result.exit_code == 0
        assert "Removed" in result.output or "Deactivated" in result.output

    @patch('src.cli_context.KnowledgeBase')
    def test_remove_nonexistent_context(self, mock_kb_class, runner):
        """Test removing a nonexistent context."""
        mock_kb = MagicMock()
        mock_kb.get_contexts.return_value = []
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["remove", "Nonexistent"])

        assert result.exit_code == 0
        assert "not found" in result.output


# =============================================================================
# Tests for show command
# =============================================================================


class TestShowCommand:
    """Tests for the show command."""

    @patch('src.cli_context.KnowledgeBase')
    def test_show_existing_context(self, mock_kb_class, runner, mock_context):
        """Test showing an existing context."""
        mock_kb = MagicMock()
        mock_kb.get_contexts.return_value = [mock_context]
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["show", "Test Project"])

        assert result.exit_code == 0
        assert "Test Project" in result.output
        assert "project" in result.output

    @patch('src.cli_context.KnowledgeBase')
    def test_show_nonexistent_context(self, mock_kb_class, runner):
        """Test showing a nonexistent context."""
        mock_kb = MagicMock()
        mock_kb.get_contexts.return_value = []
        mock_kb_class.return_value = mock_kb

        result = runner.invoke(app, ["show", "Nonexistent"])

        assert result.exit_code == 0
        assert "not found" in result.output
