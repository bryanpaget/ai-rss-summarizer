"""Tests for cli_schedule.py - CLI commands for background fetch scheduling."""

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from src.cli_schedule import app, _parse_interval


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


# =============================================================================
# Tests for app structure
# =============================================================================


class TestAppStructure:
    """Tests for the CLI app structure."""

    def test_app_exists(self):
        """Test that the app exists."""
        from src.cli_schedule import app
        assert app is not None

    def test_app_has_name(self):
        """Test that the app has the correct name."""
        assert app.info.name == "schedule"

    def test_app_has_help_text(self):
        """Test that the app has help text."""
        assert app.info.help == "Background fetch scheduling commands"

    def test_app_has_three_commands(self):
        """Test that the app has 3 commands registered."""
        assert len(app.registered_commands) == 3

    def test_enable_command_registered(self):
        """Test that enable command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "enable" in command_names

    def test_disable_command_registered(self):
        """Test that disable command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "disable" in command_names

    def test_status_command_registered(self):
        """Test that status command is registered."""
        command_names = [cmd.name or cmd.callback.__name__ for cmd in app.registered_commands]
        assert "status" in command_names


# =============================================================================
# Tests for interval parsing
# =============================================================================


class TestParseInterval:
    """Tests for interval string parsing."""

    def test_parse_days(self):
        """Test parsing day intervals."""
        assert _parse_interval("1d") == 1440
        assert _parse_interval("3d") == 4320
        assert _parse_interval("7d") == 10080

    def test_parse_hours(self):
        """Test parsing hour intervals."""
        assert _parse_interval("1h") == 60
        assert _parse_interval("6h") == 360
        assert _parse_interval("12h") == 720
        assert _parse_interval("24h") == 1440

    def test_parse_minutes(self):
        """Test parsing minute intervals."""
        assert _parse_interval("30m") == 30
        assert _parse_interval("60m") == 60
        assert _parse_interval("5m") == 5

    def test_parse_plain_number(self):
        """Test parsing plain numbers as minutes."""
        assert _parse_interval("30") == 30
        assert _parse_interval("60") == 60

    def test_parse_invalid(self):
        """Test parsing invalid intervals returns None."""
        assert _parse_interval("abc") is None
        assert _parse_interval("") is None
        assert _parse_interval("3x") is None

    def test_parse_case_insensitive(self):
        """Test parsing is case insensitive."""
        assert _parse_interval("1D") == 1440
        assert _parse_interval("6H") == 360
        assert _parse_interval("30M") == 30


# =============================================================================
# Tests for schedule callback (no subcommand)
# =============================================================================


class TestScheduleNoSubcommand:
    """Tests for schedule command with no subcommand."""

    def test_no_subcommand_shows_help(self, runner):
        """Test that running without subcommand shows help."""
        result = runner.invoke(app)
        assert result.exit_code == 0
        assert "Background Fetch Scheduling" in result.output
        assert "enable" in result.output
        assert "disable" in result.output
        assert "status" in result.output

    def test_no_subcommand_shows_examples(self, runner):
        """Test that running without subcommand shows examples."""
        result = runner.invoke(app)
        assert "--every 3d" in result.output
        assert "--every 12h" in result.output


# =============================================================================
# Tests for enable command
# =============================================================================


class TestEnableCommand:
    """Tests for the enable command."""

    @patch('src.cli_schedule._create_windows_task')
    @patch('src.cli_schedule._save_schedule_config')
    @patch('platform.system', return_value='Windows')
    def test_enable_with_default_interval(self, mock_system, mock_save, mock_create, runner):
        """Test enabling with default 1d interval."""
        mock_create.return_value = (True, "Task created")

        result = runner.invoke(app, ["enable"])

        assert result.exit_code == 0
        assert "Task created" in result.output
        mock_create.assert_called_once()
        mock_save.assert_called_once_with(True, 1440)

    @patch('src.cli_schedule._create_windows_task')
    @patch('src.cli_schedule._save_schedule_config')
    @patch('platform.system', return_value='Windows')
    def test_enable_with_custom_interval(self, mock_system, mock_save, mock_create, runner):
        """Test enabling with custom interval."""
        mock_create.return_value = (True, "Task created")

        result = runner.invoke(app, ["enable", "--every", "6h"])

        assert result.exit_code == 0
        mock_create.assert_called_once()
        mock_save.assert_called_once_with(True, 360)

    def test_enable_with_invalid_interval(self, runner):
        """Test enabling with invalid interval shows error."""
        result = runner.invoke(app, ["enable", "--every", "invalid"])

        assert result.exit_code == 1
        assert "Invalid interval" in result.output


# =============================================================================
# Tests for disable command
# =============================================================================


class TestDisableCommand:
    """Tests for the disable command."""

    @patch('src.cli_schedule._delete_windows_task')
    @patch('src.cli_schedule._save_schedule_config')
    @patch('platform.system', return_value='Windows')
    def test_disable_success(self, mock_system, mock_save, mock_delete, runner):
        """Test disabling scheduled task."""
        mock_delete.return_value = (True, "Task deleted")

        result = runner.invoke(app, ["disable"])

        assert result.exit_code == 0
        assert "deleted" in result.output.lower() or "Task" in result.output
        mock_delete.assert_called_once()
        mock_save.assert_called_once_with(False)


# =============================================================================
# Tests for status command
# =============================================================================


class TestStatusCommand:
    """Tests for the status command."""

    @patch('src.cli_schedule._get_windows_task_status')
    @patch('src.cli_schedule._load_schedule_config')
    @patch('platform.system', return_value='Windows')
    def test_status_when_enabled(self, mock_system, mock_load, mock_status, runner):
        """Test status when scheduling is enabled."""
        mock_status.return_value = {
            "Status": "Ready",
            "Next Run Time": "2026-01-13 10:00:00",
        }
        mock_load.return_value = {"enabled": True, "interval_minutes": 1440}

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "ENABLED" in result.output

    @patch('src.cli_schedule._get_windows_task_status')
    @patch('src.cli_schedule._load_schedule_config')
    @patch('platform.system', return_value='Windows')
    def test_status_when_disabled(self, mock_system, mock_load, mock_status, runner):
        """Test status when scheduling is disabled."""
        mock_status.return_value = None
        mock_load.return_value = {"enabled": False}

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "DISABLED" in result.output
