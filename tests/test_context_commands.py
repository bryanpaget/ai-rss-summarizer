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
