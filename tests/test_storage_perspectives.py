"""Tests for storage_perspectives.py - Storage extension for perspective features."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import json

from src.storage_perspectives import PerspectiveStorage, add_perspective_methods


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock Storage instance."""
    storage = MagicMock()
    return storage


@pytest.fixture
def mock_story():
    """Create a mock Story object."""
    story = MagicMock()
    story.id = "story-1"
    story.title = "Test Story"
    story.description = "A test story"
    story.created_at = datetime(2026, 1, 12, 10, 0, 0)
    story.last_updated = datetime(2026, 1, 12, 12, 0, 0)
    story.article_ids = ["article-1"]
    return story


@pytest.fixture
def mock_article():
    """Create a mock Article object."""
    article = MagicMock()
    article.id = "article-1"
    article.title = "Test Article"
    article.story_id = "story-1"
    return article


@pytest.fixture
def mock_perspective():
    """Create a mock Perspective object."""
    perspective = MagicMock()
    perspective.content = "Synthesized perspective content"
    perspective.source_articles = ["article-1", "article-2"]
    perspective.confidence = 0.85
    perspective.generated_at = datetime(2026, 1, 12, 12, 0, 0)
    return perspective


@pytest.fixture
def perspective_storage(mock_storage):
    """Create a PerspectiveStorage instance."""
    return PerspectiveStorage(mock_storage)


# =============================================================================
# Tests for PerspectiveStorage.__init__
# =============================================================================


class TestPerspectiveStorageInit:
    """Tests for PerspectiveStorage initialization."""

    def test_stores_storage_reference(self, mock_storage):
        """Test that storage reference is stored."""
        ps = PerspectiveStorage(mock_storage)
        assert ps.storage is mock_storage


# =============================================================================
# Tests for get_story_clusters
# =============================================================================


class TestGetStoryClusters:
    """Tests for get_story_clusters method."""

    def test_returns_empty_list_when_no_stories(self, perspective_storage, mock_storage):
        """Test returns empty list when no stories exist."""
        mock_storage.get_all_stories.return_value = []

        result = perspective_storage.get_story_clusters()

        assert result == []

    def test_returns_formatted_clusters(self, perspective_storage, mock_storage, mock_story):
        """Test returns properly formatted cluster dicts."""
        mock_storage.get_all_stories.return_value = [mock_story]

        result = perspective_storage.get_story_clusters()

        assert len(result) == 1
        assert result[0]['id'] == "story-1"
        assert result[0]['title'] == "Test Story"
        assert 'created_at' in result[0]
        assert 'updated_at' in result[0]


# =============================================================================
# Tests for get_story_cluster
# =============================================================================


class TestGetStoryCluster:
    """Tests for get_story_cluster method."""

    def test_returns_none_when_not_found(self, perspective_storage, mock_storage):
        """Test returns None when story not found."""
        mock_storage.get_story.return_value = None

        result = perspective_storage.get_story_cluster("nonexistent")

        assert result is None

    def test_returns_formatted_cluster(self, perspective_storage, mock_storage, mock_story):
        """Test returns properly formatted cluster dict."""
        mock_storage.get_story.return_value = mock_story

        result = perspective_storage.get_story_cluster("story-1")

        assert result['id'] == "story-1"
        assert result['title'] == "Test Story"


# =============================================================================
# Tests for create_story_cluster
# =============================================================================


class TestCreateStoryCluster:
    """Tests for create_story_cluster method."""

    def test_creates_story(self, perspective_storage, mock_storage):
        """Test that a story is created with correct attributes."""
        perspective_storage.create_story_cluster("new-cluster", "New Cluster Title")

        mock_storage.save_story.assert_called_once()
        saved_story = mock_storage.save_story.call_args[0][0]
        assert saved_story.id == "new-cluster"
        assert saved_story.title == "New Cluster Title"
        assert saved_story.lifecycle_state == "emerging"


# =============================================================================
# Tests for assign_to_cluster
# =============================================================================


class TestAssignToCluster:
    """Tests for assign_to_cluster method."""

    def test_updates_article_story(self, perspective_storage, mock_storage, mock_story):
        """Test that article's story_id is updated."""
        mock_storage.get_story.return_value = mock_story

        perspective_storage.assign_to_cluster("article-2", "story-1")

        mock_storage.update_article_story.assert_called_once_with("article-2", "story-1")

    def test_adds_article_to_story_article_ids(self, perspective_storage, mock_storage, mock_story):
        """Test that article is added to story's article_ids."""
        mock_story.article_ids = ["article-1"]
        mock_storage.get_story.return_value = mock_story

        perspective_storage.assign_to_cluster("article-2", "story-1")

        assert "article-2" in mock_story.article_ids
        mock_storage.update_story.assert_called_once()

    def test_does_not_duplicate_article_id(self, perspective_storage, mock_storage, mock_story):
        """Test that article_id is not duplicated if already in list."""
        mock_story.article_ids = ["article-1"]
        mock_storage.get_story.return_value = mock_story

        perspective_storage.assign_to_cluster("article-1", "story-1")

        # Should not add duplicate
        assert mock_story.article_ids.count("article-1") == 1


# =============================================================================
# Tests for update_cluster_timestamp
# =============================================================================


class TestUpdateClusterTimestamp:
    """Tests for update_cluster_timestamp method."""

    def test_updates_timestamp(self, perspective_storage, mock_storage, mock_story):
        """Test that last_updated is updated."""
        old_timestamp = mock_story.last_updated
        mock_storage.get_story.return_value = mock_story

        perspective_storage.update_cluster_timestamp("story-1")

        assert mock_story.last_updated != old_timestamp
        mock_storage.update_story.assert_called_once()

    def test_handles_nonexistent_story(self, perspective_storage, mock_storage):
        """Test handling of nonexistent story."""
        mock_storage.get_story.return_value = None

        # Should not raise
        perspective_storage.update_cluster_timestamp("nonexistent")

        mock_storage.update_story.assert_not_called()


# =============================================================================
# Tests for get_articles_by_cluster
# =============================================================================


class TestGetArticlesByCluster:
    """Tests for get_articles_by_cluster method."""

    def test_queries_articles_by_story_id(self, perspective_storage, mock_storage, mock_article):
        """Test that articles are queried by story_id."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [{"id": "article-1"}]
        mock_storage._connect.return_value.__enter__.return_value = mock_conn
        mock_storage._row_to_article.return_value = mock_article

        result = perspective_storage.get_articles_by_cluster("story-1")

        mock_conn.execute.assert_called_once()
        assert "story_id = ?" in mock_conn.execute.call_args[0][0]

    def test_returns_articles(self, perspective_storage, mock_storage, mock_article):
        """Test that articles are returned."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [{"id": "article-1"}]
        mock_storage._connect.return_value.__enter__.return_value = mock_conn
        mock_storage._row_to_article.return_value = mock_article

        result = perspective_storage.get_articles_by_cluster("story-1")

        assert len(result) == 1
        assert result[0].id == "article-1"


# =============================================================================
# Tests for delete_story_cluster
# =============================================================================


class TestDeleteStoryCluster:
    """Tests for delete_story_cluster method."""

    def test_deletes_cluster(self, perspective_storage, mock_storage):
        """Test that cluster is deleted."""
        mock_conn = MagicMock()
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        perspective_storage.delete_story_cluster("story-1")

        # Should execute 3 queries: update articles, delete perspectives, delete story
        assert mock_conn.execute.call_count == 3
        mock_conn.commit.assert_called_once()


# =============================================================================
# Tests for get_old_story_clusters
# =============================================================================


class TestGetOldStoryClusters:
    """Tests for get_old_story_clusters method."""

    def test_queries_with_cutoff_date(self, perspective_storage, mock_storage):
        """Test that query uses cutoff_date."""
        cutoff = datetime(2026, 1, 1)
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        perspective_storage.get_old_story_clusters(cutoff)

        mock_conn.execute.assert_called_once()
        assert cutoff in mock_conn.execute.call_args[0][1]


# =============================================================================
# Tests for cache_perspective
# =============================================================================


class TestCachePerspective:
    """Tests for cache_perspective method."""

    def test_caches_perspective(self, perspective_storage, mock_storage, mock_perspective):
        """Test that perspective is cached."""
        mock_conn = MagicMock()
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        perspective_storage.cache_perspective("story-1", "consensus", mock_perspective)

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


# =============================================================================
# Tests for get_cached_perspective
# =============================================================================


class TestGetCachedPerspective:
    """Tests for get_cached_perspective method."""

    def test_returns_none_when_not_cached(self, perspective_storage, mock_storage):
        """Test returns None when perspective not cached."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        result = perspective_storage.get_cached_perspective("story-1", "consensus")

        assert result is None

    def test_returns_perspective_when_cached(self, perspective_storage, mock_storage):
        """Test returns Perspective when cached."""
        mock_row = {
            'category': 'consensus',
            'content': 'Cached content',
            'source_articles': '["article-1"]',
            'confidence': 0.9,
            'generated_at': '2026-01-12T12:00:00',
        }
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        with patch("src.perspectives.Perspective") as MockPerspective:
            result = perspective_storage.get_cached_perspective("story-1", "consensus")

            MockPerspective.assert_called_once()


# =============================================================================
# Tests for invalidate_perspective_cache
# =============================================================================


class TestInvalidatePerspectiveCache:
    """Tests for invalidate_perspective_cache method."""

    def test_deletes_cached_perspectives(self, perspective_storage, mock_storage):
        """Test that cached perspectives are deleted."""
        mock_conn = MagicMock()
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        perspective_storage.invalidate_perspective_cache("story-1")

        mock_conn.execute.assert_called_once()
        assert "DELETE FROM perspective_cache" in mock_conn.execute.call_args[0][0]
        mock_conn.commit.assert_called_once()


# =============================================================================
# Tests for get_perspective_config
# =============================================================================


class TestGetPerspectiveConfig:
    """Tests for get_perspective_config method."""

    def test_returns_none_when_no_config(self, perspective_storage, mock_storage):
        """Test returns None when no config exists."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        result = perspective_storage.get_perspective_config()

        assert result is None

    def test_returns_config_when_exists(self, perspective_storage, mock_storage):
        """Test returns config dict when exists."""
        mock_row = {
            'enabled_categories': '["consensus", "contested"]',
            'default_categories': '["consensus"]',
            'category_order': '["consensus", "contested", "gaps"]',
        }
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = mock_row
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        result = perspective_storage.get_perspective_config()

        assert result['enabled_categories'] == ["consensus", "contested"]
        assert result['default_categories'] == ["consensus"]


# =============================================================================
# Tests for save_perspective_config
# =============================================================================


class TestSavePerspectiveConfig:
    """Tests for save_perspective_config method."""

    def test_saves_config(self, perspective_storage, mock_storage):
        """Test that config is saved."""
        mock_conn = MagicMock()
        mock_storage._connect.return_value.__enter__.return_value = mock_conn

        config = {
            'enabled_categories': ['consensus'],
            'default_categories': ['consensus'],
            'category_order': ['consensus'],
        }
        perspective_storage.save_perspective_config(config)

        mock_conn.execute.assert_called_once()
        mock_conn.commit.assert_called_once()


# =============================================================================
# Tests for add_perspective_methods
# =============================================================================


class TestAddPerspectiveMethods:
    """Tests for add_perspective_methods function."""

    def test_adds_all_methods(self, mock_storage):
        """Test that all perspective methods are added."""
        add_perspective_methods(mock_storage)

        assert hasattr(mock_storage, 'get_story_clusters')
        assert hasattr(mock_storage, 'get_story_cluster')
        assert hasattr(mock_storage, 'create_story_cluster')
        assert hasattr(mock_storage, 'assign_to_cluster')
        assert hasattr(mock_storage, 'update_cluster_timestamp')
        assert hasattr(mock_storage, 'get_articles_by_cluster')
        assert hasattr(mock_storage, 'delete_story_cluster')
        assert hasattr(mock_storage, 'get_old_story_clusters')
        assert hasattr(mock_storage, 'cache_perspective')
        assert hasattr(mock_storage, 'get_cached_perspective')
        assert hasattr(mock_storage, 'invalidate_perspective_cache')
        assert hasattr(mock_storage, 'get_perspective_config')
        assert hasattr(mock_storage, 'save_perspective_config')

    def test_returns_storage(self, mock_storage):
        """Test that storage instance is returned."""
        result = add_perspective_methods(mock_storage)
        assert result is mock_storage

    def test_methods_are_callable(self, mock_storage):
        """Test that added methods are callable."""
        add_perspective_methods(mock_storage)

        assert callable(mock_storage.get_story_clusters)
        assert callable(mock_storage.get_story_cluster)
        assert callable(mock_storage.create_story_cluster)


# =============================================================================
# Tests for module import
# =============================================================================


class TestModuleImport:
    """Tests for module import behavior."""

    def test_module_imports_successfully(self):
        """Test that module can be imported."""
        from src import storage_perspectives
        assert storage_perspectives is not None

    def test_perspective_storage_class_exists(self):
        """Test that PerspectiveStorage class exists."""
        from src.storage_perspectives import PerspectiveStorage
        assert PerspectiveStorage is not None

    def test_add_perspective_methods_exists(self):
        """Test that add_perspective_methods function exists."""
        from src.storage_perspectives import add_perspective_methods
        assert callable(add_perspective_methods)
