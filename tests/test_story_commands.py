"""Tests for story_commands.py - CLI commands for story clustering features."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import typer

from src.story_commands import (
    cluster_command,
    stories_command,
    story_detail_command,
    evolution_command,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock Storage instance."""
    storage = MagicMock()
    return storage


@pytest.fixture
def mock_article():
    """Create a mock Article."""
    article = MagicMock()
    article.id = "article-1"
    article.title = "Test Article Title"
    article.story_id = None
    article.content = "Test content"
    return article


@pytest.fixture
def mock_article_with_story():
    """Create a mock Article that's already in a story."""
    article = MagicMock()
    article.id = "article-2"
    article.title = "Clustered Article"
    article.story_id = "story-1"
    return article


@pytest.fixture
def mock_story():
    """Create a mock Story object."""
    story = MagicMock()
    story.id = "story-1"
    story.title = "Test Story About Technology"
    story.description = "A story about emerging tech trends"
    story.lifecycle_state = "developing"
    story.keywords = ["tech", "AI", "innovation", "startup", "software"]
    story.article_ids = ["article-1", "article-2", "article-3"]
    story.news_item_ids = ["news-1", "news-2"]
    story.last_updated = datetime(2026, 1, 12, 10, 0, 0)
    return story


@pytest.fixture
def mock_news_item():
    """Create a mock NewsItem object."""
    item = MagicMock()
    item.id = "news-1"
    item.title = "Breaking Development"
    item.description = "New information has emerged"
    item.item_type = "new_info"
    item.first_reported_by = "Tech News"
    item.confidence = 0.85
    return item


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.name = "MockLLM"
    return provider


# =============================================================================
# Tests for cluster_command
# =============================================================================


class TestClusterCommand:
    """Tests for the cluster_command function."""

    def test_cluster_command_no_llm_exits(self, mock_storage):
        """Test cluster_command exits when no LLM is available."""
        with patch("src.story_commands.get_best_provider") as mock_get_provider, \
             patch("src.story_commands.console") as mock_console:
            mock_get_provider.return_value = (MagicMock(), False)

            with pytest.raises(typer.Exit):
                cluster_command(mock_storage)

            mock_console.print.assert_any_call("[yellow]LLM required for story clustering.[/yellow]")

    def test_cluster_command_no_unclustered_articles(self, mock_storage, mock_provider, mock_article_with_story):
        """Test cluster_command when all articles are already clustered."""
        mock_storage.get_articles.return_value = [mock_article_with_story]

        with patch("src.story_commands.get_best_provider") as mock_get_provider, \
             patch("src.story_commands.console") as mock_console:
            mock_get_provider.return_value = (mock_provider, True)

            cluster_command(mock_storage)

            mock_console.print.assert_any_call("[yellow]No unclustered articles found.[/yellow]")

    def test_cluster_command_processes_articles(self, mock_storage, mock_provider, mock_article):
        """Test cluster_command processes unclustered articles."""
        mock_storage.get_articles.return_value = [mock_article]

        with patch("src.story_commands.get_best_provider") as mock_get_provider, \
             patch("src.story_commands.batch_process_articles") as mock_batch, \
             patch("src.story_commands.console") as mock_console:
            mock_get_provider.return_value = (mock_provider, True)
            mock_batch.return_value = {
                "processed": 1,
                "stories_created": 1,
                "articles_added_to_existing": 0,
                "total_news_items": 3,
                "errors": [],
            }

            cluster_command(mock_storage)

            mock_batch.assert_called_once()
            mock_console.print.assert_any_call("[green]Processed 1 articles[/green]")

    def test_cluster_command_with_errors(self, mock_storage, mock_provider, mock_article):
        """Test cluster_command displays errors."""
        mock_storage.get_articles.return_value = [mock_article]

        with patch("src.story_commands.get_best_provider") as mock_get_provider, \
             patch("src.story_commands.batch_process_articles") as mock_batch, \
             patch("src.story_commands.console") as mock_console:
            mock_get_provider.return_value = (mock_provider, True)
            mock_batch.return_value = {
                "processed": 1,
                "stories_created": 0,
                "articles_added_to_existing": 0,
                "total_news_items": 0,
                "errors": ["Error processing article-1"],
            }

            cluster_command(mock_storage)

            # Should show error count
            assert any("[yellow]Errors: 1[/yellow]" in str(call) for call in mock_console.print.call_args_list)

    def test_cluster_command_disable_news(self, mock_storage, mock_provider, mock_article):
        """Test cluster_command with news extraction disabled."""
        mock_storage.get_articles.return_value = [mock_article]

        with patch("src.story_commands.get_best_provider") as mock_get_provider, \
             patch("src.story_commands.batch_process_articles") as mock_batch, \
             patch("src.story_commands.console"):
            mock_get_provider.return_value = (mock_provider, True)
            mock_batch.return_value = {
                "processed": 1,
                "stories_created": 1,
                "articles_added_to_existing": 0,
                "total_news_items": 0,
                "errors": [],
            }

            cluster_command(mock_storage, enable_news=False)

            # Verify batch_process_articles was called with enable_news=False
            call_args = mock_batch.call_args
            assert call_args[0][3] == False or call_args[1].get("enable_news") == False

    def test_cluster_command_custom_limit(self, mock_storage, mock_provider, mock_article):
        """Test cluster_command respects limit parameter."""
        mock_storage.get_articles.return_value = [mock_article]

        with patch("src.story_commands.get_best_provider") as mock_get_provider, \
             patch("src.story_commands.batch_process_articles") as mock_batch, \
             patch("src.story_commands.console"):
            mock_get_provider.return_value = (mock_provider, True)
            mock_batch.return_value = {
                "processed": 1,
                "stories_created": 1,
                "articles_added_to_existing": 0,
                "total_news_items": 0,
                "errors": [],
            }

            cluster_command(mock_storage, limit=50)

            mock_storage.get_articles.assert_called_once_with(limit=50)


# =============================================================================
# Tests for stories_command
# =============================================================================


class TestStoriesCommand:
    """Tests for the stories_command function."""

    def test_stories_command_no_stories(self, mock_storage):
        """Test stories_command when no stories exist."""
        mock_storage.get_all_stories.return_value = []

        with patch("src.story_commands.console") as mock_console:
            stories_command(mock_storage)

            mock_console.print.assert_any_call("[yellow]No stories found.[/yellow]")

    def test_stories_command_displays_table(self, mock_storage, mock_story):
        """Test stories_command displays story table."""
        mock_storage.get_all_stories.return_value = [mock_story]

        with patch("src.story_commands.console") as mock_console:
            stories_command(mock_storage)

            # Should print table and total
            assert mock_console.print.called
            assert any("Total: 1 stories" in str(call) for call in mock_console.print.call_args_list)

    def test_stories_command_filter_by_lifecycle(self, mock_storage, mock_story):
        """Test stories_command filters by lifecycle state."""
        mock_storage.get_all_stories.return_value = [mock_story]

        with patch("src.story_commands.console"):
            stories_command(mock_storage, lifecycle="developing")

            mock_storage.get_all_stories.assert_called_once_with(limit=20, lifecycle_state="developing")

    def test_stories_command_respects_limit(self, mock_storage, mock_story):
        """Test stories_command respects limit parameter."""
        mock_storage.get_all_stories.return_value = [mock_story]

        with patch("src.story_commands.console"):
            stories_command(mock_storage, limit=50)

            mock_storage.get_all_stories.assert_called_once_with(limit=50)

    def test_stories_command_truncates_long_titles(self, mock_storage):
        """Test stories_command truncates long story titles."""
        long_story = MagicMock()
        long_story.title = "A" * 100  # Very long title
        long_story.lifecycle_state = "emerging"
        long_story.article_ids = []
        long_story.news_item_ids = []
        long_story.last_updated = None

        mock_storage.get_all_stories.return_value = [long_story]

        with patch("src.story_commands.console"):
            stories_command(mock_storage)

            # Should not crash with long title

    def test_stories_command_handles_all_lifecycle_states(self, mock_storage):
        """Test stories_command handles all lifecycle state colors."""
        states = ["emerging", "developing", "peaked", "declining", "resolved"]

        for state in states:
            story = MagicMock()
            story.title = f"Story in {state} state"
            story.lifecycle_state = state
            story.article_ids = ["a1"]
            story.news_item_ids = []
            story.last_updated = datetime.now()

            mock_storage.get_all_stories.return_value = [story]

            with patch("src.story_commands.console"):
                stories_command(mock_storage)

            # Should not crash for any state


# =============================================================================
# Tests for story_detail_command
# =============================================================================


class TestStoryDetailCommand:
    """Tests for the story_detail_command function."""

    def test_story_detail_invalid_index_zero(self, mock_storage, mock_story):
        """Test story_detail_command with index 0."""
        mock_storage.get_all_stories.return_value = [mock_story]

        with patch("src.story_commands.console") as mock_console:
            story_detail_command(mock_storage, story_index=0)

            assert any("Invalid story index" in str(call) for call in mock_console.print.call_args_list)

    def test_story_detail_invalid_index_too_high(self, mock_storage, mock_story):
        """Test story_detail_command with index higher than list size."""
        mock_storage.get_all_stories.return_value = [mock_story]

        with patch("src.story_commands.console") as mock_console:
            story_detail_command(mock_storage, story_index=5)

            assert any("Invalid story index" in str(call) for call in mock_console.print.call_args_list)

    def test_story_detail_displays_story(self, mock_storage, mock_story, mock_article):
        """Test story_detail_command displays story details."""
        mock_storage.get_all_stories.return_value = [mock_story]
        mock_storage.get_article.return_value = mock_article
        mock_storage.get_news_items.return_value = []

        with patch("src.story_commands.console") as mock_console:
            story_detail_command(mock_storage, story_index=1)

            # Should print Panel for story details
            assert mock_console.print.called

    def test_story_detail_shows_articles(self, mock_storage, mock_story, mock_article):
        """Test story_detail_command shows related articles."""
        mock_storage.get_all_stories.return_value = [mock_story]
        mock_storage.get_article.return_value = mock_article
        mock_storage.get_news_items.return_value = []

        with patch("src.story_commands.console"):
            story_detail_command(mock_storage, story_index=1)

            # Should call get_article for each article_id
            assert mock_storage.get_article.call_count >= 1

    def test_story_detail_shows_news_items(self, mock_storage, mock_story, mock_news_item):
        """Test story_detail_command shows news items."""
        mock_storage.get_all_stories.return_value = [mock_story]
        mock_storage.get_article.return_value = None
        mock_storage.get_news_items.return_value = [mock_news_item]

        with patch("src.story_commands.console"):
            story_detail_command(mock_storage, story_index=1, show_items=True)

            mock_storage.get_news_items.assert_called_once_with(mock_story.id)

    def test_story_detail_hides_news_items_when_disabled(self, mock_storage, mock_story):
        """Test story_detail_command hides news items when show_items=False."""
        mock_storage.get_all_stories.return_value = [mock_story]
        mock_storage.get_article.return_value = None

        with patch("src.story_commands.console"):
            story_detail_command(mock_storage, story_index=1, show_items=False)

            mock_storage.get_news_items.assert_not_called()

    def test_story_detail_handles_many_articles(self, mock_storage, mock_article):
        """Test story_detail_command handles stories with many articles."""
        story = MagicMock()
        story.id = "story-1"
        story.title = "Big Story"
        story.description = "Description"
        story.lifecycle_state = "developing"
        story.keywords = ["keyword"]
        story.article_ids = [f"article-{i}" for i in range(20)]  # 20 articles
        story.news_item_ids = []
        story.last_updated = datetime.now()

        mock_storage.get_all_stories.return_value = [story]
        mock_storage.get_article.return_value = mock_article
        mock_storage.get_news_items.return_value = []

        with patch("src.story_commands.console") as mock_console:
            story_detail_command(mock_storage, story_index=1)

            # Should show "... and X more" message
            assert any("more" in str(call) for call in mock_console.print.call_args_list)

    def test_story_detail_handles_all_news_item_types(self, mock_storage, mock_story):
        """Test story_detail_command handles all news item types."""
        item_types = ["new_info", "recap", "analysis", "opinion"]

        for item_type in item_types:
            item = MagicMock()
            item.title = f"{item_type} item"
            item.description = "Description"
            item.item_type = item_type
            item.first_reported_by = "Source"
            item.confidence = 0.9

            mock_storage.get_all_stories.return_value = [mock_story]
            mock_storage.get_article.return_value = None
            mock_storage.get_news_items.return_value = [item]

            with patch("src.story_commands.console"):
                story_detail_command(mock_storage, story_index=1)

            # Should not crash for any item type


# =============================================================================
# Tests for evolution_command
# =============================================================================


class TestEvolutionCommand:
    """Tests for the evolution_command function."""

    def test_evolution_command_updates_stories(self, mock_storage):
        """Test evolution_command updates story lifecycle states."""
        with patch("src.story_commands.StoryEvolutionTracker") as MockTracker, \
             patch("src.story_commands.console"):
            mock_tracker = MagicMock()
            mock_tracker.update_all_stories.return_value = {"updated": 5}
            mock_tracker.get_evolution_stats.return_value = {
                "total_stories": 5,
                "by_state": {"emerging": 2, "developing": 3},
                "avg_articles_per_story": 3.0,
                "avg_news_items_per_story": 2.5,
            }
            MockTracker.return_value = mock_tracker

            evolution_command(mock_storage)

            mock_tracker.update_all_stories.assert_called_once()

    def test_evolution_command_displays_stats(self, mock_storage):
        """Test evolution_command displays evolution statistics."""
        with patch("src.story_commands.StoryEvolutionTracker") as MockTracker, \
             patch("src.story_commands.console") as mock_console:
            mock_tracker = MagicMock()
            mock_tracker.update_all_stories.return_value = {"updated": 5}
            mock_tracker.get_evolution_stats.return_value = {
                "total_stories": 10,
                "by_state": {
                    "emerging": 3,
                    "developing": 4,
                    "peaked": 2,
                    "declining": 1,
                },
                "avg_articles_per_story": 5.5,
                "avg_news_items_per_story": 3.2,
            }
            MockTracker.return_value = mock_tracker

            evolution_command(mock_storage)

            # Should print summary with total stories
            assert any("Total stories: 10" in str(call) for call in mock_console.print.call_args_list)

    def test_evolution_command_empty_stats(self, mock_storage):
        """Test evolution_command handles empty stats."""
        with patch("src.story_commands.StoryEvolutionTracker") as MockTracker, \
             patch("src.story_commands.console"):
            mock_tracker = MagicMock()
            mock_tracker.update_all_stories.return_value = {"updated": 0}
            mock_tracker.get_evolution_stats.return_value = {
                "total_stories": 0,
                "by_state": {},
                "avg_articles_per_story": 0.0,
                "avg_news_items_per_story": 0.0,
            }
            MockTracker.return_value = mock_tracker

            evolution_command(mock_storage)

            # Should not crash with empty stats

    def test_evolution_command_displays_state_distribution(self, mock_storage):
        """Test evolution_command displays lifecycle state distribution."""
        with patch("src.story_commands.StoryEvolutionTracker") as MockTracker, \
             patch("src.story_commands.console") as mock_console:
            mock_tracker = MagicMock()
            mock_tracker.update_all_stories.return_value = {"updated": 5}
            mock_tracker.get_evolution_stats.return_value = {
                "total_stories": 5,
                "by_state": {
                    "emerging": 1,
                    "developing": 2,
                    "peaked": 1,
                    "declining": 1,
                    "resolved": 0,
                },
                "avg_articles_per_story": 3.0,
                "avg_news_items_per_story": 2.0,
            }
            MockTracker.return_value = mock_tracker

            evolution_command(mock_storage)

            # Should print table (Table object)
            assert mock_console.print.called


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestStoryCommandsIntegration:
    """Integration-style tests for story commands working together."""

    def test_cluster_then_list_workflow(self, mock_storage, mock_provider, mock_article, mock_story):
        """Test workflow: cluster articles then list stories."""
        mock_storage.get_articles.return_value = [mock_article]
        mock_storage.get_all_stories.return_value = [mock_story]

        with patch("src.story_commands.get_best_provider") as mock_get_provider, \
             patch("src.story_commands.batch_process_articles") as mock_batch, \
             patch("src.story_commands.console"):
            mock_get_provider.return_value = (mock_provider, True)
            mock_batch.return_value = {
                "processed": 1,
                "stories_created": 1,
                "articles_added_to_existing": 0,
                "total_news_items": 2,
                "errors": [],
            }

            # First cluster
            cluster_command(mock_storage)

            # Then list
            stories_command(mock_storage)

            # Both should complete without error

    def test_list_then_detail_workflow(self, mock_storage, mock_story, mock_article):
        """Test workflow: list stories then view detail."""
        mock_storage.get_all_stories.return_value = [mock_story]
        mock_storage.get_article.return_value = mock_article
        mock_storage.get_news_items.return_value = []

        with patch("src.story_commands.console"):
            # First list
            stories_command(mock_storage)

            # Then view detail of first story
            story_detail_command(mock_storage, story_index=1)

            # Both should complete without error
