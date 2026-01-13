"""Tests for constitution.py - User analysis policy framework."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.constitution import (
    get_constitution_path,
    constitution_exists,
    get_constitution_content,
    get_constitution_context,
    create_constitution,
    get_example_constitution,
    EXAMPLE_CONSTITUTION,
)


# =============================================================================
# Tests for get_constitution_path
# =============================================================================


class TestGetConstitutionPath:
    """Tests for get_constitution_path function."""

    def test_returns_path_object(self):
        """Test returns a Path object."""
        path = get_constitution_path()
        assert isinstance(path, Path)

    def test_returns_config_constitution_md(self):
        """Test returns expected path."""
        path = get_constitution_path()
        assert path == Path("config/constitution.md")


# =============================================================================
# Tests for constitution_exists
# =============================================================================


class TestConstitutionExists:
    """Tests for constitution_exists function."""

    def test_returns_false_when_no_file(self, tmp_path, monkeypatch):
        """Test returns False when constitution file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        assert constitution_exists() is False

    def test_returns_true_when_file_exists(self, tmp_path, monkeypatch):
        """Test returns True when constitution file exists."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "constitution.md").write_text("# Test")
        assert constitution_exists() is True


# =============================================================================
# Tests for get_constitution_content
# =============================================================================


class TestGetConstitutionContent:
    """Tests for get_constitution_content function."""

    def test_returns_none_when_no_file(self, tmp_path, monkeypatch):
        """Test returns None when constitution file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        assert get_constitution_content() is None

    def test_returns_content_when_file_exists(self, tmp_path, monkeypatch):
        """Test returns content when constitution file exists."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "constitution.md").write_text("# My Principles\n- Be honest")

        content = get_constitution_content()
        assert content == "# My Principles\n- Be honest"

    def test_returns_none_for_empty_file(self, tmp_path, monkeypatch):
        """Test returns None for empty constitution file."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "constitution.md").write_text("")

        assert get_constitution_content() is None

    def test_strips_whitespace(self, tmp_path, monkeypatch):
        """Test strips leading/trailing whitespace."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "constitution.md").write_text("  \n# Test\n  ")

        content = get_constitution_content()
        assert content == "# Test"


# =============================================================================
# Tests for get_constitution_context
# =============================================================================


class TestGetConstitutionContext:
    """Tests for get_constitution_context function."""

    def test_returns_empty_string_when_no_constitution(self, tmp_path, monkeypatch):
        """Test returns empty string when no constitution configured."""
        monkeypatch.chdir(tmp_path)
        assert get_constitution_context() == ""

    def test_returns_formatted_context_when_constitution_exists(self, tmp_path, monkeypatch):
        """Test returns formatted context when constitution exists."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "constitution.md").write_text("# My Principles\n- Be honest")

        context = get_constitution_context()

        assert "## User Analysis Framework" in context
        assert "# My Principles" in context
        assert "- Be honest" in context
        assert "Apply these principles" in context

    def test_context_ends_with_newlines(self, tmp_path, monkeypatch):
        """Test context ends with newlines for proper prompt concatenation."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "constitution.md").write_text("# Test")

        context = get_constitution_context()
        assert context.endswith("\n\n")


# =============================================================================
# Tests for create_constitution
# =============================================================================


class TestCreateConstitution:
    """Tests for create_constitution function."""

    def test_creates_file_with_example_template(self, tmp_path, monkeypatch):
        """Test creates file with example template when no content provided."""
        monkeypatch.chdir(tmp_path)

        path = create_constitution()

        assert path.exists()
        content = path.read_text()
        assert "# My Analysis Principles" in content

    def test_creates_file_with_custom_content(self, tmp_path, monkeypatch):
        """Test creates file with custom content."""
        monkeypatch.chdir(tmp_path)

        path = create_constitution("# Custom Principles\n- Rule 1")

        content = path.read_text()
        assert content == "# Custom Principles\n- Rule 1"

    def test_creates_config_directory_if_needed(self, tmp_path, monkeypatch):
        """Test creates config directory if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        create_constitution()

        assert (tmp_path / "config").is_dir()

    def test_returns_path_to_created_file(self, tmp_path, monkeypatch):
        """Test returns path to the created file."""
        monkeypatch.chdir(tmp_path)

        path = create_constitution()

        # Check it's the expected relative path (resolved to absolute in tmp_path)
        assert path.name == "constitution.md"
        assert path.parent.name == "config"


# =============================================================================
# Tests for get_example_constitution
# =============================================================================


class TestGetExampleConstitution:
    """Tests for get_example_constitution function."""

    def test_returns_example_template(self):
        """Test returns the example template."""
        example = get_example_constitution()
        assert example == EXAMPLE_CONSTITUTION

    def test_example_has_required_sections(self):
        """Test example template has expected sections."""
        example = get_example_constitution()
        assert "# My Analysis Principles" in example
        assert "## Core Values" in example
        assert "## Source Evaluation" in example
        assert "## Focus Areas" in example
        assert "## Red Flags" in example


# =============================================================================
# Integration Tests
# =============================================================================


class TestConstitutionIntegration:
    """Integration tests for constitution usage."""

    def test_constitution_context_can_be_prepended_to_prompt(self, tmp_path, monkeypatch):
        """Test constitution context can be prepended to LLM prompts."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "constitution.md").write_text("- Prioritize accuracy")

        context = get_constitution_context()
        prompt = "Analyze this article."

        full_prompt = context + prompt

        assert "User Analysis Framework" in full_prompt
        assert "Prioritize accuracy" in full_prompt
        assert "Analyze this article." in full_prompt
        # Constitution should come before the main prompt
        assert full_prompt.index("Prioritize accuracy") < full_prompt.index("Analyze this article")

    def test_empty_constitution_doesnt_affect_prompt(self, tmp_path, monkeypatch):
        """Test empty constitution doesn't add anything to prompt."""
        monkeypatch.chdir(tmp_path)

        context = get_constitution_context()
        prompt = "Analyze this article."

        full_prompt = context + prompt

        assert full_prompt == "Analyze this article."
