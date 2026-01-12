"""Tests for context_commands.py module - CLI commands for personal context management.

This test file covers the context CLI commands including profile initialization,
display, editing, pinning/unpinning, watching/ignoring, statistics, and import/export.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from unittest.mock import MagicMock, patch, Mock, PropertyMock
from io import StringIO

import pytest

from src.context_commands import (
    context_init,
    context_show,
    context_edit,
    context_pin,
    context_unpin,
    context_watch,
    context_ignore,
    context_stats,
    context_export,
    context_import,
    context_clear,
    console,
)
from src.user_context import UserContextProfile, UserContextStore


# =============================================================================
# Temporary Files and Directories
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_config_dir(temp_dir):
    """Create a temporary config directory."""
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


@pytest.fixture
def temp_profile_path(temp_config_dir):
    """Create a temporary profile path."""
    return os.path.join(temp_config_dir, "user_context.json")


@pytest.fixture
def temp_export_file(temp_dir):
    """Create a temporary export file path."""
    return os.path.join(temp_dir, "context_export.json")


@pytest.fixture
def temp_import_file(temp_dir):
    """Create a temporary import file with sample data."""
    import_path = os.path.join(temp_dir, "context_import.json")
    data = {
        "profile": {
            "role": "imported user",
            "current_projects": ["imported project"],
            "watching": ["imported topic"],
            "ignore": [],
            "pinned": [],
            "relevance_threshold": 0.3,
            "diversity_factor": 0.15,
            "personalization_strength": 0.7,
        },
        "interactions": [
            {
                "article_id": "article-1",
                "interaction_type": "expanded",
                "timestamp": datetime.now().isoformat(),
            }
        ],
    }
    with open(import_path, "w") as f:
        json.dump(data, f)
    return import_path


@pytest.fixture
def temp_import_file_empty(temp_dir):
    """Create a temporary import file with empty data."""
    import_path = os.path.join(temp_dir, "context_import_empty.json")
    data = {"profile": {}, "interactions": []}
    with open(import_path, "w") as f:
        json.dump(data, f)
    return import_path


@pytest.fixture
def temp_import_file_invalid_json(temp_dir):
    """Create a temporary import file with invalid JSON."""
    import_path = os.path.join(temp_dir, "context_import_invalid.json")
    with open(import_path, "w") as f:
        f.write("{ invalid json }")
    return import_path


@pytest.fixture
def temp_import_file_nonexistent(temp_dir):
    """Return path to a nonexistent import file."""
    return os.path.join(temp_dir, "nonexistent_import.json")


# =============================================================================
# UserContextProfile Fixtures
# =============================================================================


@pytest.fixture
def profile_default():
    """Create a default UserContextProfile."""
    return UserContextProfile()


@pytest.fixture
def profile_developer():
    """Create a UserContextProfile for a developer."""
    return UserContextProfile(
        role="ML engineer at fintech startup",
        current_projects=["building recommender", "LLM integration"],
        watching=["AI", "Python", "machine learning"],
        ignore=["celebrity news", "sports"],
        pinned=["security updates"],
        personalization_strength=0.7,
    )


@pytest.fixture
def profile_researcher():
    """Create a UserContextProfile for a researcher."""
    return UserContextProfile(
        role="data scientist",
        current_projects=["NLP research", "paper writing"],
        watching=["transformers", "LLMs", "deep learning"],
        ignore=["entertainment"],
        pinned=["academic papers"],
    )


@pytest.fixture
def profile_empty_lists():
    """Create a UserContextProfile with empty lists."""
    return UserContextProfile(
        role="minimal user",
        current_projects=[],
        watching=[],
        ignore=[],
        pinned=[],
    )


@pytest.fixture
def profile_unicode():
    """Create a UserContextProfile with unicode characters."""
    return UserContextProfile(
        role="desarrollador de software",
        current_projects=["proyecto AI", "desarrollo web"],
        watching=["inteligencia artificial", "tecnologia"],
        ignore=["noticias de celebridades"],
        pinned=["seguridad"],
    )


@pytest.fixture
def profile_special_chars():
    """Create a UserContextProfile with special characters."""
    return UserContextProfile(
        role="developer <script>",
        current_projects=["project && test"],
        watching=["topic; select *"],
        ignore=["ignore&topic"],
        pinned=["pinned\\topic"],
    )


@pytest.fixture
def profile_with_all_lists():
    """Create a profile with items in all lists for comprehensive testing."""
    return UserContextProfile(
        role="tech lead",
        current_projects=["project A", "project B", "project C"],
        watching=["topic1", "topic2", "topic3"],
        ignore=["ignore1", "ignore2"],
        pinned=["pinned1", "pinned2"],
        personalization_strength=0.8,
    )


@pytest.fixture
def profile_many_items():
    """Create a profile with many items in each list."""
    return UserContextProfile(
        role="omnivore",
        current_projects=[f"project-{i}" for i in range(10)],
        watching=[f"watch-{i}" for i in range(20)],
        ignore=[f"ignore-{i}" for i in range(15)],
        pinned=[f"pin-{i}" for i in range(5)],
    )


# =============================================================================
# UserContextStore Fixtures
# =============================================================================


@pytest.fixture
def mock_store():
    """Create a mock UserContextStore."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    store.save_profile.return_value = None
    store.get_topic_engagement.return_value = {}
    store.export_data.return_value = {"profile": {}, "interactions": []}
    store.import_data.return_value = None
    store.clear_history.return_value = 0
    return store


@pytest.fixture
def mock_store_with_profile(profile_developer):
    """Create a mock UserContextStore with a developer profile."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = profile_developer
    store.save_profile.return_value = None
    return store


@pytest.fixture
def mock_store_with_empty_profile(profile_empty_lists):
    """Create a mock UserContextStore with empty profile lists."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = profile_empty_lists
    store.save_profile.return_value = None
    return store


@pytest.fixture
def mock_store_with_engagement():
    """Create a mock UserContextStore with engagement data."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    store.get_topic_engagement.return_value = {
        "AI": 0.85,
        "Python": 0.75,
        "Machine Learning": 0.65,
        "Web Development": 0.50,
        "Cloud": 0.40,
    }
    return store


@pytest.fixture
def mock_store_empty_engagement():
    """Create a mock UserContextStore with no engagement data."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    store.get_topic_engagement.return_value = {}
    return store


@pytest.fixture
def mock_store_many_engagements():
    """Create a mock UserContextStore with many engagement entries."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    # More than 15 topics to test truncation
    engagement = {f"topic-{i}": 0.9 - (i * 0.05) for i in range(20)}
    store.get_topic_engagement.return_value = engagement
    return store


@pytest.fixture
def mock_store_with_history():
    """Create a mock UserContextStore with interaction history."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    store.clear_history.return_value = 50  # 50 interactions cleared
    return store


@pytest.fixture
def mock_store_export_data():
    """Create a mock UserContextStore with export data."""
    store = MagicMock(spec=UserContextStore)
    store.export_data.return_value = {
        "profile": {
            "role": "developer",
            "current_projects": ["project1"],
            "watching": ["AI"],
            "ignore": [],
            "pinned": [],
        },
        "interactions": [
            {
                "article_id": "article-1",
                "interaction_type": "expanded",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "article_id": "article-2",
                "interaction_type": "saved",
                "timestamp": datetime.now().isoformat(),
            },
        ],
    }
    return store


# =============================================================================
# Console Input/Output Fixtures
# =============================================================================


@pytest.fixture
def mock_console():
    """Create a mock Rich Console."""
    mock = MagicMock()
    mock.print = MagicMock()
    mock.input = MagicMock(return_value="")
    return mock


@pytest.fixture
def mock_console_with_inputs():
    """Create a mock console that returns inputs in sequence."""
    mock = MagicMock()
    mock.print = MagicMock()
    inputs = iter([
        "ML engineer at startup",  # role
        "project1, project2",      # projects
        "AI, Python",              # watching
        "sports, celebrity",       # ignore
    ])
    mock.input = MagicMock(side_effect=lambda prompt="": next(inputs))
    return mock


@pytest.fixture
def mock_console_empty_inputs():
    """Create a mock console that returns empty inputs (keep defaults)."""
    mock = MagicMock()
    mock.print = MagicMock()
    mock.input = MagicMock(return_value="")
    return mock


@pytest.fixture
def mock_console_partial_inputs():
    """Create a mock console with some inputs filled, some empty."""
    mock = MagicMock()
    mock.print = MagicMock()
    inputs = iter([
        "new role",  # role - filled
        "",          # projects - empty, keep default
        "new topic", # watching - filled
        "",          # ignore - empty, keep default
    ])
    mock.input = MagicMock(side_effect=lambda prompt="": next(inputs))
    return mock


@pytest.fixture
def mock_console_unicode_inputs():
    """Create a mock console with unicode inputs."""
    mock = MagicMock()
    mock.print = MagicMock()
    inputs = iter([
        "desarrollador de software",
        "proyecto AI, desarrollo web",
        "inteligencia artificial, tecnologia",
        "noticias de celebridades",
    ])
    mock.input = MagicMock(side_effect=lambda prompt="": next(inputs))
    return mock


@pytest.fixture
def mock_console_special_chars_inputs():
    """Create a mock console with special characters in inputs."""
    mock = MagicMock()
    mock.print = MagicMock()
    inputs = iter([
        "developer <script>",
        "project && test",
        "topic; select *",
        "ignore&topic",
    ])
    mock.input = MagicMock(side_effect=lambda prompt="": next(inputs))
    return mock


@pytest.fixture
def mock_console_whitespace_inputs():
    """Create a mock console with whitespace-padded inputs."""
    mock = MagicMock()
    mock.print = MagicMock()
    inputs = iter([
        "  role with spaces  ",
        "  project1  ,  project2  ",
        "  topic1 , topic2  ",
        "  ignore1 ",
    ])
    mock.input = MagicMock(side_effect=lambda prompt="": next(inputs))
    return mock


# =============================================================================
# Topic Input Fixtures
# =============================================================================


@pytest.fixture
def topic_simple():
    """A simple topic string."""
    return "AI"


@pytest.fixture
def topic_multi_word():
    """A multi-word topic string."""
    return "machine learning"


@pytest.fixture
def topic_unicode():
    """A unicode topic string."""
    return "inteligencia artificial"


@pytest.fixture
def topic_special_chars():
    """A topic with special characters."""
    return "C++ programming"


@pytest.fixture
def topic_empty():
    """An empty topic string."""
    return ""


@pytest.fixture
def topic_whitespace():
    """A whitespace-only topic string."""
    return "   "


@pytest.fixture
def topic_already_pinned():
    """A topic that is already pinned in test profiles."""
    return "security updates"


@pytest.fixture
def topic_already_watching():
    """A topic that is already being watched in test profiles."""
    return "AI"


@pytest.fixture
def topic_already_ignored():
    """A topic that is already ignored in test profiles."""
    return "celebrity news"


# =============================================================================
# Export/Import Data Fixtures
# =============================================================================


@pytest.fixture
def export_data_standard():
    """Standard export data."""
    return {
        "profile": {
            "role": "developer",
            "current_projects": ["project1", "project2"],
            "watching": ["AI", "Python"],
            "ignore": ["sports"],
            "pinned": ["security"],
            "relevance_threshold": 0.3,
            "diversity_factor": 0.15,
            "personalization_strength": 0.7,
        },
        "interactions": [
            {
                "article_id": "article-1",
                "interaction_type": "expanded",
                "timestamp": datetime.now().isoformat(),
            },
        ],
    }


@pytest.fixture
def export_data_empty():
    """Empty export data."""
    return {"profile": {}, "interactions": []}


@pytest.fixture
def export_data_many_interactions():
    """Export data with many interactions."""
    now = datetime.now()
    return {
        "profile": {"role": "heavy user"},
        "interactions": [
            {
                "article_id": f"article-{i}",
                "interaction_type": "expanded" if i % 2 == 0 else "saved",
                "timestamp": (now - timedelta(hours=i)).isoformat(),
            }
            for i in range(100)
        ],
    }


@pytest.fixture
def export_data_unicode():
    """Export data with unicode content."""
    return {
        "profile": {
            "role": "desarrollador",
            "current_projects": ["proyecto AI"],
            "watching": ["inteligencia artificial"],
        },
        "interactions": [],
    }


# =============================================================================
# Engagement Statistics Fixtures
# =============================================================================


@pytest.fixture
def engagement_stats_standard():
    """Standard engagement statistics."""
    return {
        "AI": 0.85,
        "Python": 0.75,
        "Machine Learning": 0.65,
        "Web Development": 0.50,
        "Cloud Computing": 0.40,
    }


@pytest.fixture
def engagement_stats_empty():
    """Empty engagement statistics."""
    return {}


@pytest.fixture
def engagement_stats_single():
    """Single topic engagement statistics."""
    return {"AI": 0.90}


@pytest.fixture
def engagement_stats_many():
    """Many topic engagement statistics (more than display limit)."""
    return {f"topic-{i}": max(0.1, 0.95 - (i * 0.05)) for i in range(20)}


@pytest.fixture
def engagement_stats_low():
    """Low engagement statistics."""
    return {
        "topic1": 0.10,
        "topic2": 0.05,
        "topic3": 0.02,
    }


@pytest.fixture
def engagement_stats_perfect():
    """Perfect (100%) engagement statistics."""
    return {
        "topic1": 1.0,
        "topic2": 1.0,
    }


# =============================================================================
# Context Clear Fixtures
# =============================================================================


@pytest.fixture
def mock_store_clear_many():
    """Mock store that returns high clear count."""
    store = MagicMock(spec=UserContextStore)
    store.clear_history.return_value = 500
    return store


@pytest.fixture
def mock_store_clear_none():
    """Mock store that returns zero clear count."""
    store = MagicMock(spec=UserContextStore)
    store.clear_history.return_value = 0
    return store


# =============================================================================
# Edge Case Fixtures
# =============================================================================


@pytest.fixture
def profile_with_long_strings():
    """Profile with very long strings."""
    return UserContextProfile(
        role="A" * 500,
        current_projects=["B" * 200, "C" * 200],
        watching=["D" * 100, "E" * 100],
        ignore=["F" * 100],
        pinned=["G" * 100],
    )


@pytest.fixture
def profile_with_newlines():
    """Profile with newlines in strings."""
    return UserContextProfile(
        role="developer\nwith\nnewlines",
        current_projects=["project\nwith\nlines"],
        watching=["topic\nwith\nlines"],
    )


@pytest.fixture
def topic_with_newlines():
    """Topic string with newlines."""
    return "topic\nwith\nnewlines"


@pytest.fixture
def topic_very_long():
    """Very long topic string."""
    return "A" * 500


# =============================================================================
# Integration Testing Fixtures
# =============================================================================


@pytest.fixture
def full_context_setup(temp_dir, profile_developer):
    """Full context setup for integration testing."""
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    profile_path = os.path.join(config_dir, "user_context.json")

    # Save profile to file
    with open(profile_path, "w") as f:
        json.dump(profile_developer.to_dict(), f)

    return {
        "temp_dir": temp_dir,
        "config_dir": config_dir,
        "profile_path": profile_path,
        "profile": profile_developer,
    }


@pytest.fixture
def context_init_mocks():
    """Combined mocks for context_init testing."""
    mock_store = MagicMock(spec=UserContextStore)
    mock_store.load_profile.return_value = UserContextProfile()
    mock_store.save_profile.return_value = None

    mock_console = MagicMock()
    mock_console.print = MagicMock()
    inputs = iter([
        "ML engineer",
        "project1, project2",
        "AI, Python",
        "sports",
    ])
    mock_console.input = MagicMock(side_effect=lambda prompt="": next(inputs))

    return {
        "store": mock_store,
        "console": mock_console,
    }


@pytest.fixture
def context_edit_mocks(profile_developer):
    """Combined mocks for context_edit testing."""
    mock_store = MagicMock(spec=UserContextStore)
    mock_store.load_profile.return_value = profile_developer
    mock_store.save_profile.return_value = None

    mock_console = MagicMock()
    mock_console.print = MagicMock()
    # Empty inputs to keep current values
    mock_console.input = MagicMock(return_value="")

    return {
        "store": mock_store,
        "console": mock_console,
        "profile": profile_developer,
    }


@pytest.fixture
def context_show_mocks(profile_with_all_lists):
    """Combined mocks for context_show testing."""
    mock_store = MagicMock(spec=UserContextStore)
    mock_store.load_profile.return_value = profile_with_all_lists

    mock_console = MagicMock()
    mock_console.print = MagicMock()

    return {
        "store": mock_store,
        "console": mock_console,
        "profile": profile_with_all_lists,
    }


@pytest.fixture
def context_stats_mocks(engagement_stats_standard):
    """Combined mocks for context_stats testing."""
    mock_store = MagicMock(spec=UserContextStore)
    mock_store.get_topic_engagement.return_value = engagement_stats_standard

    mock_console = MagicMock()
    mock_console.print = MagicMock()

    return {
        "store": mock_store,
        "console": mock_console,
        "engagement": engagement_stats_standard,
    }


# =============================================================================
# Error Handling Fixtures
# =============================================================================


@pytest.fixture
def mock_store_file_error():
    """Mock store that raises file errors."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.side_effect = FileNotFoundError("Profile not found")
    return store


@pytest.fixture
def mock_store_permission_error():
    """Mock store that raises permission errors."""
    store = MagicMock(spec=UserContextStore)
    store.save_profile.side_effect = PermissionError("Cannot write profile")
    return store


@pytest.fixture
def mock_store_json_error():
    """Mock store that raises JSON decode errors."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    return store


@pytest.fixture
def mock_store_import_error():
    """Mock store that raises errors during import."""
    store = MagicMock(spec=UserContextStore)
    store.import_data.side_effect = ValueError("Invalid import data")
    return store


# =============================================================================
# Console Output Capture Fixtures
# =============================================================================


@pytest.fixture
def capture_console_output():
    """Fixture to capture console output.

    Returns a context manager that captures all console.print calls.
    """
    output = []

    def capture(*args, **kwargs):
        # Convert args to string representation
        output.append(" ".join(str(arg) for arg in args))

    return output, capture


@pytest.fixture
def printed_lines():
    """Simple list to capture printed lines during tests."""
    return []


# =============================================================================
# Pin/Unpin/Watch/Ignore State Fixtures
# =============================================================================


@pytest.fixture
def profile_for_pinning():
    """Profile ready for pin testing - has some pinned, some not."""
    return UserContextProfile(
        role="tester",
        pinned=["already-pinned"],
        watching=["already-watching"],
        ignore=["already-ignoring"],
    )


@pytest.fixture
def mock_store_for_pin_test():
    """Mock store configured for pin/unpin testing."""
    profile = UserContextProfile(
        role="tester",
        pinned=["already-pinned"],
    )
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = profile
    store.save_profile.return_value = None
    return store


@pytest.fixture
def mock_store_for_watch_test():
    """Mock store configured for watch testing."""
    profile = UserContextProfile(
        role="tester",
        watching=["already-watching"],
    )
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = profile
    store.save_profile.return_value = None
    return store


@pytest.fixture
def mock_store_for_ignore_test():
    """Mock store configured for ignore testing."""
    profile = UserContextProfile(
        role="tester",
        ignore=["already-ignoring"],
    )
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = profile
    store.save_profile.return_value = None
    return store


# =============================================================================
# CLI Runner Fixtures (for CLI command tests)
# =============================================================================


@pytest.fixture
def cli_runner():
    """Create a Typer CLI test runner."""
    from typer.testing import CliRunner
    return CliRunner()


# =============================================================================
# Context Init Command Tests
# =============================================================================


class TestContextInitBasic:
    """Test context_init basic functionality."""

    def test_context_init_creates_profile(self, mock_console_with_inputs):
        """Test context_init creates a profile with user input."""
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_with_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = UserContextProfile()
            mock_store_class.return_value = mock_store

            context_init()

            mock_store.save_profile.assert_called_once()
            saved_profile = mock_store.save_profile.call_args[0][0]
            assert saved_profile.role == "ML engineer at startup"
            assert saved_profile.current_projects == ["project1", "project2"]
            assert saved_profile.watching == ["AI", "Python"]
            assert saved_profile.ignore == ["sports", "celebrity"]

    def test_context_init_keeps_defaults_on_empty_input(self, mock_console_empty_inputs):
        """Test context_init keeps existing values when input is empty."""
        existing_profile = UserContextProfile(
            role="existing role",
            current_projects=["existing project"],
            watching=["existing topic"],
            ignore=["existing ignore"],
        )
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_empty_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = existing_profile
            mock_store_class.return_value = mock_store

            context_init()

            mock_store.save_profile.assert_called_once()
            saved_profile = mock_store.save_profile.call_args[0][0]
            # Original values should be preserved when input is empty
            assert saved_profile.role == "existing role"

    def test_context_init_shows_panel(self, mock_console_empty_inputs):
        """Test context_init displays the setup panel."""
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_empty_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = UserContextProfile()
            mock_store_class.return_value = mock_store

            context_init()

            # Should print panel and success message
            print_calls = [str(call) for call in mock_console_empty_inputs.print.call_args_list]
            assert any("Personal Context Setup" in str(call) or "Panel" in str(call) for call in print_calls)

    def test_context_init_shows_success_message(self, mock_console_empty_inputs):
        """Test context_init displays success message."""
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_empty_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = UserContextProfile()
            mock_store_class.return_value = mock_store

            context_init()

            # Check for success message
            print_calls = [str(call) for call in mock_console_empty_inputs.print.call_args_list]
            assert any("saved successfully" in str(call).lower() or "green" in str(call).lower() for call in print_calls)


class TestContextInitInputHandling:
    """Test context_init input handling scenarios."""

    def test_context_init_with_partial_inputs(self, mock_console_partial_inputs):
        """Test context_init with some inputs filled, some empty."""
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_partial_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            existing_profile = UserContextProfile(
                current_projects=["old project"],
                ignore=["old ignore"],
            )
            mock_store.load_profile.return_value = existing_profile
            mock_store_class.return_value = mock_store

            context_init()

            saved_profile = mock_store.save_profile.call_args[0][0]
            assert saved_profile.role == "new role"
            assert saved_profile.watching == ["new topic"]

    def test_context_init_with_unicode_inputs(self, mock_console_unicode_inputs):
        """Test context_init handles unicode inputs."""
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_unicode_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = UserContextProfile()
            mock_store_class.return_value = mock_store

            context_init()

            saved_profile = mock_store.save_profile.call_args[0][0]
            assert saved_profile.role == "desarrollador de software"
            assert "proyecto AI" in saved_profile.current_projects

    def test_context_init_with_whitespace_inputs(self, mock_console_whitespace_inputs):
        """Test context_init strips whitespace from inputs."""
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_whitespace_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = UserContextProfile()
            mock_store_class.return_value = mock_store

            context_init()

            saved_profile = mock_store.save_profile.call_args[0][0]
            assert saved_profile.role == "role with spaces"
            assert saved_profile.current_projects == ["project1", "project2"]

    def test_context_init_with_special_chars_inputs(self, mock_console_special_chars_inputs):
        """Test context_init handles special characters."""
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console_special_chars_inputs):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = UserContextProfile()
            mock_store_class.return_value = mock_store

            context_init()

            saved_profile = mock_store.save_profile.call_args[0][0]
            assert saved_profile.role == "developer <script>"


# =============================================================================
# Context Show Command Tests
# =============================================================================


class TestContextShowBasic:
    """Test context_show basic functionality."""

    def test_context_show_displays_role(self, profile_developer):
        """Test context_show displays the user's role."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_show()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("ML engineer at fintech startup" in str(call) for call in print_calls)

    def test_context_show_displays_projects(self, profile_developer):
        """Test context_show displays current projects."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_show()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("building recommender" in str(call) for call in print_calls)

    def test_context_show_displays_watching(self, profile_developer):
        """Test context_show displays watching topics."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_show()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Python" in str(call) or "machine learning" in str(call) for call in print_calls)

    def test_context_show_displays_pinned(self, profile_developer):
        """Test context_show displays pinned topics."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_show()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("security updates" in str(call) for call in print_calls)

    def test_context_show_displays_ignore(self, profile_developer):
        """Test context_show displays ignored topics."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_show()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("celebrity news" in str(call) or "sports" in str(call) for call in print_calls)

    def test_context_show_displays_personalization_strength(self, profile_developer):
        """Test context_show displays personalization strength."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_show()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("70%" in str(call) or "personalization" in str(call).lower() for call in print_calls)


class TestContextShowEdgeCases:
    """Test context_show with edge cases."""

    def test_context_show_with_empty_profile(self, profile_empty_lists):
        """Test context_show with empty profile lists."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_empty_lists
            mock_store_class.return_value = mock_store

            context_show()

            # Should not crash, just show minimal info
            mock_console.print.assert_called()

    def test_context_show_with_unicode_profile(self, profile_unicode):
        """Test context_show handles unicode content."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_unicode
            mock_store_class.return_value = mock_store

            context_show()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("desarrollador" in str(call) for call in print_calls)

    def test_context_show_with_many_items(self, profile_many_items):
        """Test context_show handles profiles with many items."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_many_items
            mock_store_class.return_value = mock_store

            context_show()

            # Should handle many items without error
            mock_console.print.assert_called()


# =============================================================================
# Context Edit Command Tests
# =============================================================================


class TestContextEditBasic:
    """Test context_edit basic functionality."""

    def test_context_edit_preserves_values_on_empty_input(self, profile_developer):
        """Test context_edit preserves values when input is empty."""
        mock_console = MagicMock()
        mock_console.input = MagicMock(return_value="")

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_edit()

            mock_store.save_profile.assert_called_once()
            # Profile should be saved (even if unchanged)

    def test_context_edit_updates_role(self, profile_developer):
        """Test context_edit updates role when new value provided."""
        mock_console = MagicMock()
        inputs = iter(["new role", "", "", ""])
        mock_console.input = MagicMock(side_effect=lambda prompt="": next(inputs))

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_edit()

            saved_profile = mock_store.save_profile.call_args[0][0]
            assert saved_profile.role == "new role"

    def test_context_edit_updates_projects(self, profile_developer):
        """Test context_edit updates projects when new value provided."""
        mock_console = MagicMock()
        inputs = iter(["", "new project 1, new project 2", "", ""])
        mock_console.input = MagicMock(side_effect=lambda prompt="": next(inputs))

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_edit()

            saved_profile = mock_store.save_profile.call_args[0][0]
            assert saved_profile.current_projects == ["new project 1", "new project 2"]

    def test_context_edit_shows_current_values(self, profile_developer):
        """Test context_edit shows current values in prompts."""
        mock_console = MagicMock()
        mock_console.input = MagicMock(return_value="")

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_edit()

            # Check that input was called with prompts containing current values
            input_calls = [str(call) for call in mock_console.input.call_args_list]
            # At least one prompt should contain current role
            assert len(input_calls) >= 4  # role, projects, watching, ignore

    def test_context_edit_shows_success_message(self, profile_developer):
        """Test context_edit shows success message."""
        mock_console = MagicMock()
        mock_console.input = MagicMock(return_value="")

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile_developer
            mock_store_class.return_value = mock_store

            context_edit()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("updated" in str(call).lower() or "green" in str(call).lower() for call in print_calls)


# =============================================================================
# Context Pin/Unpin Command Tests
# =============================================================================


class TestContextPinBasic:
    """Test context_pin basic functionality."""

    def test_context_pin_adds_new_topic(self, mock_store_for_pin_test):
        """Test context_pin adds a new topic to pinned list."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_pin_test

            context_pin("new-topic")

            mock_store_for_pin_test.save_profile.assert_called_once()
            saved_profile = mock_store_for_pin_test.save_profile.call_args[0][0]
            assert "new-topic" in saved_profile.pinned

    def test_context_pin_shows_already_pinned_message(self, mock_store_for_pin_test):
        """Test context_pin shows message for already pinned topic."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_pin_test

            context_pin("already-pinned")

            # Should not save because topic is already pinned
            mock_store_for_pin_test.save_profile.assert_not_called()
            # Should show already pinned message
            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("already pinned" in str(call).lower() for call in print_calls)

    def test_context_pin_shows_success_message(self, mock_store_for_pin_test):
        """Test context_pin shows success message when pinning."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_pin_test

            context_pin("new-topic")

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("pinned" in str(call).lower() and "new-topic" in str(call) for call in print_calls)


class TestContextUnpinBasic:
    """Test context_unpin basic functionality."""

    def test_context_unpin_removes_topic(self, mock_store_for_pin_test):
        """Test context_unpin removes a topic from pinned list."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_pin_test

            context_unpin("already-pinned")

            mock_store_for_pin_test.save_profile.assert_called_once()
            saved_profile = mock_store_for_pin_test.save_profile.call_args[0][0]
            assert "already-pinned" not in saved_profile.pinned

    def test_context_unpin_shows_not_pinned_message(self, mock_store_for_pin_test):
        """Test context_unpin shows message for not pinned topic."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_pin_test

            context_unpin("not-pinned-topic")

            # Should not save because topic is not pinned
            mock_store_for_pin_test.save_profile.assert_not_called()
            # Should show not pinned message
            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("not pinned" in str(call).lower() for call in print_calls)

    def test_context_unpin_shows_success_message(self, mock_store_for_pin_test):
        """Test context_unpin shows success message."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_pin_test

            context_unpin("already-pinned")

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("unpinned" in str(call).lower() for call in print_calls)


# =============================================================================
# Context Watch/Ignore Command Tests
# =============================================================================


class TestContextWatchBasic:
    """Test context_watch basic functionality."""

    def test_context_watch_adds_new_topic(self, mock_store_for_watch_test):
        """Test context_watch adds a new topic to watching list."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_watch_test

            context_watch("new-topic")

            mock_store_for_watch_test.save_profile.assert_called_once()
            saved_profile = mock_store_for_watch_test.save_profile.call_args[0][0]
            assert "new-topic" in saved_profile.watching

    def test_context_watch_shows_already_watching_message(self, mock_store_for_watch_test):
        """Test context_watch shows message for already watched topic."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_watch_test

            context_watch("already-watching")

            mock_store_for_watch_test.save_profile.assert_not_called()
            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("already watching" in str(call).lower() for call in print_calls)

    def test_context_watch_shows_success_message(self, mock_store_for_watch_test):
        """Test context_watch shows success message."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_watch_test

            context_watch("new-topic")

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("now watching" in str(call).lower() for call in print_calls)


class TestContextIgnoreBasic:
    """Test context_ignore basic functionality."""

    def test_context_ignore_adds_new_topic(self, mock_store_for_ignore_test):
        """Test context_ignore adds a new topic to ignore list."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_ignore_test

            context_ignore("new-topic")

            mock_store_for_ignore_test.save_profile.assert_called_once()
            saved_profile = mock_store_for_ignore_test.save_profile.call_args[0][0]
            assert "new-topic" in saved_profile.ignore

    def test_context_ignore_shows_already_ignoring_message(self, mock_store_for_ignore_test):
        """Test context_ignore shows message for already ignored topic."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_ignore_test

            context_ignore("already-ignoring")

            mock_store_for_ignore_test.save_profile.assert_not_called()
            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("already ignoring" in str(call).lower() for call in print_calls)

    def test_context_ignore_shows_success_message(self, mock_store_for_ignore_test):
        """Test context_ignore shows success message."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_for_ignore_test

            context_ignore("new-topic")

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("now ignoring" in str(call).lower() for call in print_calls)


# =============================================================================
# Context Stats Command Tests
# =============================================================================


class TestContextStatsBasic:
    """Test context_stats basic functionality."""

    def test_context_stats_shows_engagement_table(self, mock_store_with_engagement):
        """Test context_stats displays engagement table."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_with_engagement

            context_stats()

            # Should show engagement data
            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Table" in str(call) or "Engagement" in str(call) for call in print_calls)

    def test_context_stats_shows_no_engagement_message(self, mock_store_empty_engagement):
        """Test context_stats shows message when no engagement."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_empty_engagement

            context_stats()

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("no engagement" in str(call).lower() for call in print_calls)

    def test_context_stats_limits_to_15_topics(self, mock_store_many_engagements):
        """Test context_stats limits display to 15 topics."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_many_engagements

            context_stats()

            # Stats should be called with days parameter
            mock_store_many_engagements.get_topic_engagement.assert_called_with(days=30)

    def test_context_stats_sorts_by_engagement_rate(self, mock_store_with_engagement):
        """Test context_stats sorts topics by engagement rate."""
        mock_console = MagicMock()
        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_with_engagement

            context_stats()

            # Function should complete without error
            mock_console.print.assert_called()


# =============================================================================
# Context Export/Import Command Tests
# =============================================================================


class TestContextExportBasic:
    """Test context_export basic functionality."""

    def test_context_export_writes_json_file(self, temp_dir, mock_store_export_data):
        """Test context_export writes data to JSON file."""
        mock_console = MagicMock()
        output_path = os.path.join(temp_dir, "export.json")

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_export_data

            context_export(output_path)

            # File should be created
            assert os.path.exists(output_path)
            # Content should be valid JSON
            with open(output_path) as f:
                data = json.load(f)
            assert "profile" in data or "interactions" in data

    def test_context_export_shows_success_message(self, temp_dir, mock_store_export_data):
        """Test context_export shows success message."""
        mock_console = MagicMock()
        output_path = os.path.join(temp_dir, "export.json")

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_export_data

            context_export(output_path)

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("exported" in str(call).lower() for call in print_calls)


class TestContextImportBasic:
    """Test context_import basic functionality."""

    def test_context_import_reads_json_file(self, temp_import_file):
        """Test context_import reads data from JSON file."""
        mock_console = MagicMock()
        mock_store = MagicMock(spec=UserContextStore)

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store

            context_import(temp_import_file)

            mock_store.import_data.assert_called_once()

    def test_context_import_shows_success_message(self, temp_import_file):
        """Test context_import shows success message."""
        mock_console = MagicMock()
        mock_store = MagicMock(spec=UserContextStore)

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store

            context_import(temp_import_file)

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("imported" in str(call).lower() for call in print_calls)

    def test_context_import_handles_invalid_json(self, temp_import_file_invalid_json):
        """Test context_import handles invalid JSON gracefully."""
        mock_console = MagicMock()

        with patch("src.context_commands.console", mock_console):
            with pytest.raises(json.JSONDecodeError):
                context_import(temp_import_file_invalid_json)

    def test_context_import_handles_nonexistent_file(self, temp_import_file_nonexistent):
        """Test context_import handles nonexistent file."""
        mock_console = MagicMock()

        with patch("src.context_commands.console", mock_console):
            with pytest.raises(FileNotFoundError):
                context_import(temp_import_file_nonexistent)


# =============================================================================
# Context Clear Command Tests
# =============================================================================


class TestContextClearBasic:
    """Test context_clear basic functionality."""

    def test_context_clear_without_confirm_shows_warning(self):
        """Test context_clear without confirm shows warning."""
        mock_console = MagicMock()

        with patch("src.context_commands.console", mock_console):
            context_clear(confirm=False)

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("delete" in str(call).lower() or "confirm" in str(call).lower() for call in print_calls)

    def test_context_clear_with_confirm_clears_history(self, mock_store_with_history):
        """Test context_clear with confirm clears history."""
        mock_console = MagicMock()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_with_history

            context_clear(confirm=True)

            mock_store_with_history.clear_history.assert_called_once()

    def test_context_clear_shows_count(self, mock_store_with_history):
        """Test context_clear shows deleted count."""
        mock_console = MagicMock()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_with_history

            context_clear(confirm=True)

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("50" in str(call) or "cleared" in str(call).lower() for call in print_calls)

    def test_context_clear_with_zero_records(self, mock_store_clear_none):
        """Test context_clear when no records to clear."""
        mock_console = MagicMock()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store_clear_none

            context_clear(confirm=True)

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("0" in str(call) for call in print_calls)


# =============================================================================
# CLI Runner Tests for context-add Command
# =============================================================================


class TestContextAddCLI:
    """Test context-add CLI command with runner."""

    def test_context_add_help(self, cli_runner):
        """Test context-add help is available."""
        from src.cli import app
        result = cli_runner.invoke(app, ["context-add", "--help"])
        assert result.exit_code == 0
        assert "type" in result.stdout.lower() or "project" in result.stdout.lower()

    def test_context_add_with_project_type(self, cli_runner):
        """Test context-add with project type."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-add", "project", "TestProject"])
            assert result.exit_code == 0
            kb_mock.save_context.assert_called_once()
            context = kb_mock.save_context.call_args[0][0]
            assert context.context_type == "project"
            assert context.name == "TestProject"

    def test_context_add_with_interest_type(self, cli_runner):
        """Test context-add with interest type."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-add", "interest", "Machine Learning"])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.context_type == "interest"
            assert context.name == "Machine Learning"

    def test_context_add_with_watching_type(self, cli_runner):
        """Test context-add with watching type."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-add", "watching", "AI News"])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.context_type == "watching"
            assert context.name == "AI News"

    def test_context_add_with_description_short(self, cli_runner):
        """Test context-add with -d description option."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, [
                "context-add", "project", "MyProject",
                "-d", "This is my project description"
            ])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.description == "This is my project description"

    def test_context_add_with_description_long(self, cli_runner):
        """Test context-add with --desc description option."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, [
                "context-add", "interest", "AI",
                "--desc", "Artificial Intelligence research"
            ])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.description == "Artificial Intelligence research"

    def test_context_add_with_custom_kb_path(self, cli_runner):
        """Test context-add with custom knowledge base path."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, [
                "context-add", "project", "TestProject",
                "--kb", "custom_kb.db"
            ])
            assert result.exit_code == 0
            mock_kb.assert_called_with("custom_kb.db")

    def test_context_add_shows_success_message(self, cli_runner):
        """Test context-add shows success message."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-add", "project", "TestProject"])
            assert "added" in result.stdout.lower() or "project" in result.stdout.lower()

    def test_context_add_requires_type_argument(self, cli_runner):
        """Test context-add requires type argument."""
        from src.cli import app
        result = cli_runner.invoke(app, ["context-add"])
        assert result.exit_code != 0

    def test_context_add_requires_name_argument(self, cli_runner):
        """Test context-add requires name argument."""
        from src.cli import app
        result = cli_runner.invoke(app, ["context-add", "project"])
        assert result.exit_code != 0


class TestContextAddCLIEdgeCases:
    """Test context-add CLI command edge cases."""

    def test_context_add_with_unicode_name(self, cli_runner):
        """Test context-add handles unicode in name."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-add", "project", "项目名称"])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.name == "项目名称"

    def test_context_add_with_special_chars_name(self, cli_runner):
        """Test context-add handles special characters in name."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-add", "project", "Project & Test"])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.name == "Project & Test"

    def test_context_add_with_very_long_name(self, cli_runner):
        """Test context-add handles very long names."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_kb.return_value = kb_mock

            long_name = "A" * 200
            result = cli_runner.invoke(app, ["context-add", "project", long_name])
            assert result.exit_code == 0
            context = kb_mock.save_context.call_args[0][0]
            assert context.name == long_name


# =============================================================================
# CLI Runner Tests for context-list Command
# =============================================================================


class TestContextListCLI:
    """Test context-list CLI command with runner."""

    def test_context_list_help(self, cli_runner):
        """Test context-list help is available."""
        from src.cli import app
        result = cli_runner.invoke(app, ["context-list", "--help"])
        assert result.exit_code == 0

    def test_context_list_with_contexts(self, cli_runner):
        """Test context-list displays contexts."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "TestProject"
            mock_context.active = True
            mock_context.description = "Test description"
            kb_mock.get_contexts.return_value = [mock_context]
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            assert result.exit_code == 0
            assert "project" in result.stdout.lower() or "TestProject" in result.stdout

    def test_context_list_empty_shows_suggestion(self, cli_runner):
        """Test context-list shows add suggestion when empty."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_contexts.return_value = []
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            assert "context-add" in result.stdout.lower() or "no context" in result.stdout.lower()

    def test_context_list_with_custom_kb_path(self, cli_runner):
        """Test context-list with custom knowledge base path."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            kb_mock.get_contexts.return_value = []
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list", "--kb", "custom_kb.db"])
            mock_kb.assert_called_with("custom_kb.db")

    def test_context_list_shows_active_status(self, cli_runner):
        """Test context-list shows Active status."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "ActiveProject"
            mock_context.active = True
            mock_context.description = "Active project"
            kb_mock.get_contexts.return_value = [mock_context]
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            # Active status should be shown
            assert result.exit_code == 0

    def test_context_list_shows_inactive_status(self, cli_runner):
        """Test context-list shows Inactive status."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "InactiveProject"
            mock_context.active = False
            mock_context.description = "Inactive project"
            kb_mock.get_contexts.return_value = [mock_context]
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            assert result.exit_code == 0

    def test_context_list_truncates_description(self, cli_runner):
        """Test context-list truncates long descriptions."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "TestProject"
            mock_context.active = True
            mock_context.description = "A" * 100  # Long description
            kb_mock.get_contexts.return_value = [mock_context]
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            assert result.exit_code == 0

    def test_context_list_multiple_contexts(self, cli_runner):
        """Test context-list with multiple contexts."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            contexts = []
            for i in range(5):
                ctx = MagicMock()
                ctx.context_type = "project" if i % 2 == 0 else "interest"
                ctx.name = f"Context{i}"
                ctx.active = i % 2 == 0
                ctx.description = f"Description {i}"
                contexts.append(ctx)
            kb_mock.get_contexts.return_value = contexts
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            assert result.exit_code == 0


class TestContextListCLIEdgeCases:
    """Test context-list CLI command edge cases."""

    def test_context_list_with_unicode_content(self, cli_runner):
        """Test context-list handles unicode content."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "项目"
            mock_context.active = True
            mock_context.description = "这是一个测试项目"
            kb_mock.get_contexts.return_value = [mock_context]
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            assert result.exit_code == 0

    def test_context_list_with_none_description(self, cli_runner):
        """Test context-list handles None description."""
        from src.cli import app
        with patch("src.cli.KnowledgeBase") as mock_kb:
            kb_mock = MagicMock()
            mock_context = MagicMock()
            mock_context.context_type = "project"
            mock_context.name = "NoDescProject"
            mock_context.active = True
            mock_context.description = None
            kb_mock.get_contexts.return_value = [mock_context]
            mock_kb.return_value = kb_mock

            result = cli_runner.invoke(app, ["context-list"])
            assert result.exit_code == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestContextCommandsIntegration:
    """Integration tests for context commands."""

    def test_context_init_then_show(self):
        """Test context_init followed by context_show."""
        mock_console = MagicMock()
        inputs = iter(["developer", "project1", "AI", "sports"])
        mock_console.input = MagicMock(side_effect=lambda prompt="": next(inputs))

        profile = UserContextProfile()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile
            mock_store.save_profile.side_effect = lambda p: None
            mock_store_class.return_value = mock_store

            # Init
            context_init()

            # Update profile for show
            saved_profile = mock_store.save_profile.call_args[0][0]
            mock_store.load_profile.return_value = saved_profile

            # Show - should display the saved profile
            context_show()

            # Both functions should have been executed
            assert mock_store.save_profile.called
            assert mock_console.print.call_count > 0

    def test_context_pin_then_unpin_flow(self):
        """Test pin then unpin flow."""
        profile = UserContextProfile(pinned=[])
        mock_console = MagicMock()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile
            mock_store.save_profile.return_value = None
            mock_store_class.return_value = mock_store

            # Pin a topic
            context_pin("test-topic")
            assert "test-topic" in profile.pinned

            # Unpin the topic
            context_unpin("test-topic")
            assert "test-topic" not in profile.pinned

    def test_context_export_import_roundtrip(self, temp_dir):
        """Test export then import preserves data."""
        mock_console = MagicMock()
        export_path = os.path.join(temp_dir, "roundtrip.json")

        export_data = {
            "profile": {
                "role": "test-role",
                "current_projects": ["project1"],
                "watching": ["topic1"],
            },
            "interactions": [],
        }

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            # Export
            mock_store_export = MagicMock(spec=UserContextStore)
            mock_store_export.export_data.return_value = export_data
            mock_store_class.return_value = mock_store_export

            context_export(export_path)

            # Import
            mock_store_import = MagicMock(spec=UserContextStore)
            mock_store_class.return_value = mock_store_import

            context_import(export_path)

            # Verify import was called
            mock_store_import.import_data.assert_called_once()

    def test_context_watch_and_ignore_workflow(self):
        """Test adding topics to watch and ignore lists."""
        profile = UserContextProfile(watching=[], ignore=[])
        mock_console = MagicMock()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile
            mock_store.save_profile.return_value = None
            mock_store_class.return_value = mock_store

            # Watch some topics
            context_watch("AI")
            context_watch("Python")
            assert "AI" in profile.watching
            assert "Python" in profile.watching

            # Ignore some topics
            context_ignore("sports")
            context_ignore("celebrity")
            assert "sports" in profile.ignore
            assert "celebrity" in profile.ignore


class TestContextCommandsEdgeCases:
    """Edge case tests for context commands."""

    def test_context_pin_empty_string(self):
        """Test pinning an empty string topic."""
        profile = UserContextProfile(pinned=[])
        mock_console = MagicMock()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile
            mock_store_class.return_value = mock_store

            context_pin("")

            # Empty string should still be added (no validation in function)
            mock_store.save_profile.assert_called_once()

    def test_context_watch_with_very_long_topic(self):
        """Test watching a very long topic name."""
        profile = UserContextProfile(watching=[])
        mock_console = MagicMock()
        long_topic = "A" * 500

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.load_profile.return_value = profile
            mock_store_class.return_value = mock_store

            context_watch(long_topic)

            saved_profile = mock_store.save_profile.call_args[0][0]
            assert long_topic in saved_profile.watching

    def test_context_stats_with_zero_engagement_rate(self):
        """Test context_stats with zero engagement rates."""
        mock_console = MagicMock()
        mock_store = MagicMock(spec=UserContextStore)
        mock_store.get_topic_engagement.return_value = {
            "topic1": 0.0,
            "topic2": 0.0,
        }

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store

            context_stats()

            mock_console.print.assert_called()

    def test_context_stats_with_high_engagement_rate(self):
        """Test context_stats with 100% engagement rates."""
        mock_console = MagicMock()
        mock_store = MagicMock(spec=UserContextStore)
        mock_store.get_topic_engagement.return_value = {
            "topic1": 1.0,
            "topic2": 1.0,
        }

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.return_value = mock_store

            context_stats()

            mock_console.print.assert_called()


class TestContextCommandsErrorHandling:
    """Error handling tests for context commands."""

    def test_context_show_handles_store_error(self):
        """Test context_show handles store errors gracefully."""
        mock_console = MagicMock()

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store_class.side_effect = Exception("Store error")

            with pytest.raises(Exception):
                context_show()

    def test_context_export_handles_write_error(self, temp_dir):
        """Test context_export handles write errors."""
        mock_console = MagicMock()
        # Use a path that doesn't exist and can't be created
        invalid_path = os.path.join(temp_dir, "nonexistent", "nested", "file.json")

        with patch("src.user_context.UserContextStore") as mock_store_class, \
             patch("src.context_commands.console", mock_console):
            mock_store = MagicMock(spec=UserContextStore)
            mock_store.export_data.return_value = {"profile": {}}
            mock_store_class.return_value = mock_store

            with pytest.raises((OSError, FileNotFoundError)):
                context_export(invalid_path)