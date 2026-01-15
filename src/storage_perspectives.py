"""Storage extension for perspective synthesis features."""

import json
from datetime import datetime
from typing import Optional

from .storage import Storage, Story, Article


class PerspectiveStorage:
    """
    Extension methods for Storage to handle perspective synthesis.

    This class adds perspective-related methods without modifying the core Storage class.
    """

    def __init__(self, storage: Storage):
        self.storage = storage

    def get_story_clusters(self, min_articles: int = 1) -> list[dict]:
        """Get story clusters sorted by article count (most articles first).

        Args:
            min_articles: Minimum number of articles to include (default 1)
        """
        stories = self.storage.get_all_stories(limit=500)
        result = []
        for s in stories:
            if len(s.article_ids) >= min_articles:
                result.append({
                    'id': s.id,
                    'title': s.title,
                    'created_at': s.created_at,
                    'updated_at': s.last_updated,
                    'article_count': len(s.article_ids)
                })
        # Sort by article count descending
        result.sort(key=lambda x: x['article_count'], reverse=True)
        return result

    def get_story_cluster(self, cluster_id: str) -> Optional[dict]:
        """Get a specific story cluster."""
        story = self.storage.get_story(cluster_id)
        if story:
            return {
                'id': story.id,
                'title': story.title,
                'created_at': story.created_at,
                'updated_at': story.last_updated
            }
        return None

    def create_story_cluster(self, cluster_id: str, title: str) -> None:
        """Create a new story cluster."""
        story = Story(
            id=cluster_id,
            title=title,
            description='',
            keywords=[],
            first_seen=datetime.now(),
            last_updated=datetime.now(),
            lifecycle_state='emerging',
            article_ids=[],
            news_item_ids=[]
        )
        self.storage.save_story(story)

    def assign_to_cluster(self, article_id: str, cluster_id: str) -> None:
        """Assign an article to a story cluster."""
        self.storage.update_article_story(article_id, cluster_id)
        # Also update the story's article_ids
        story = self.storage.get_story(cluster_id)
        if story and article_id not in story.article_ids:
            story.article_ids.append(article_id)
            self.storage.update_story(story)

    def update_cluster_timestamp(self, cluster_id: str) -> None:
        """Update the last_updated timestamp for a cluster."""
        story = self.storage.get_story(cluster_id)
        if story:
            story.last_updated = datetime.now()
            self.storage.update_story(story)

    def get_articles_by_cluster(self, cluster_id: str) -> list[Article]:
        """Get all articles in a story cluster."""
        with self.storage._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM articles WHERE story_id = ? ORDER BY published DESC",
                (cluster_id,)
            ).fetchall()
            return [self.storage._row_to_article(row) for row in rows]

    def delete_story_cluster(self, cluster_id: str) -> None:
        """Delete a story cluster."""
        with self.storage._connect() as conn:
            # Unassign articles
            conn.execute("UPDATE articles SET story_id = NULL WHERE story_id = ?", (cluster_id,))
            # Delete perspectives
            conn.execute("DELETE FROM perspective_cache WHERE story_id = ?", (cluster_id,))
            # Delete story
            conn.execute("DELETE FROM stories WHERE id = ?", (cluster_id,))
            conn.commit()

    def get_old_story_clusters(self, cutoff_date) -> list[dict]:
        """Get story clusters older than cutoff_date."""
        with self.storage._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, created_at, last_updated FROM stories WHERE last_updated < ?",
                (cutoff_date,)
            ).fetchall()
            return [dict(row) for row in rows]

    def cache_perspective(self, cluster_id: str, category: str, perspective) -> None:
        """Cache a synthesized perspective."""
        with self.storage._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO perspective_cache
                (story_id, category, content, source_articles, confidence, generated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster_id,
                    category,
                    perspective.content,
                    json.dumps(perspective.source_articles),
                    perspective.confidence,
                    perspective.generated_at
                )
            )
            conn.commit()

    def get_cached_perspective(self, cluster_id: str, category: str):
        """Get a cached perspective if it exists."""
        from .perspectives import Perspective
        with self.storage._connect() as conn:
            row = conn.execute(
                "SELECT * FROM perspective_cache WHERE story_id = ? AND category = ?",
                (cluster_id, category)
            ).fetchone()
            if row:
                return Perspective(
                    category=row['category'],
                    content=row['content'],
                    source_articles=json.loads(row['source_articles']) if row['source_articles'] else [],
                    confidence=row['confidence'],
                    generated_at=datetime.fromisoformat(row['generated_at']) if isinstance(row['generated_at'], str) else row['generated_at']
                )
            return None

    def invalidate_perspective_cache(self, cluster_id: str) -> None:
        """Invalidate all cached perspectives for a cluster."""
        with self.storage._connect() as conn:
            conn.execute("DELETE FROM perspective_cache WHERE story_id = ?", (cluster_id,))
            conn.commit()

    def get_perspective_config(self) -> Optional[dict]:
        """Get user's perspective configuration."""
        with self.storage._connect() as conn:
            row = conn.execute("SELECT * FROM user_perspective_config WHERE id = 1").fetchone()
            if row:
                return {
                    'enabled_categories': json.loads(row['enabled_categories']) if row['enabled_categories'] else [],
                    'default_categories': json.loads(row['default_categories']) if row['default_categories'] else [],
                    'category_order': json.loads(row['category_order']) if row['category_order'] else []
                }
            return None

    def save_perspective_config(self, config: dict) -> None:
        """Save user's perspective configuration."""
        with self.storage._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_perspective_config (id, enabled_categories, default_categories, category_order)
                VALUES (1, ?, ?, ?)
                """,
                (
                    json.dumps(config.get('enabled_categories', [])),
                    json.dumps(config.get('default_categories', [])),
                    json.dumps(config.get('category_order', []))
                )
            )
            conn.commit()


# Convenience functions that add methods to Storage instances
def add_perspective_methods(storage: Storage):
    """
    Add perspective-related methods to a Storage instance.

    Usage:
        storage = Storage()
        add_perspective_methods(storage)
        storage.get_story_clusters()  # Now available
    """
    ps = PerspectiveStorage(storage)

    # Add methods to storage instance
    storage.get_story_clusters = ps.get_story_clusters
    storage.get_story_cluster = ps.get_story_cluster
    storage.create_story_cluster = ps.create_story_cluster
    storage.assign_to_cluster = ps.assign_to_cluster
    storage.update_cluster_timestamp = ps.update_cluster_timestamp
    storage.get_articles_by_cluster = ps.get_articles_by_cluster
    storage.delete_story_cluster = ps.delete_story_cluster
    storage.get_old_story_clusters = ps.get_old_story_clusters
    storage.cache_perspective = ps.cache_perspective
    storage.get_cached_perspective = ps.get_cached_perspective
    storage.invalidate_perspective_cache = ps.invalidate_perspective_cache
    storage.get_perspective_config = ps.get_perspective_config
    storage.save_perspective_config = ps.save_perspective_config

    return storage
