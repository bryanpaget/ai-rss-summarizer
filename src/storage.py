"""SQLite storage layer for articles and metadata."""

import json
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

# Current schema version - increment when adding migrations
SCHEMA_VERSION = 1


@dataclass
class Article:
    """Represents an RSS article."""

    id: str
    feed_url: str
    title: str
    link: str
    published: Optional[datetime]
    content: str
    summary: Optional[str] = None
    trend_tags: Optional[str] = None
    signal_tags: Optional[str] = None
    story_id: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Story:
    """Represents a cluster of articles about the same ongoing story."""

    id: str
    title: str
    description: str
    keywords: list[str]
    first_seen: datetime
    last_updated: datetime
    lifecycle_state: str
    article_ids: list[str]
    news_item_ids: list[str]
    created_at: Optional[datetime] = None


@dataclass
class NewsItem:
    """Represents a specific piece of new information within a story."""

    id: str
    story_id: str
    title: str
    description: str
    first_reported_by: str
    first_seen: datetime
    article_ids: list[str]
    item_type: str
    confidence: float
    created_at: Optional[datetime] = None


class Storage:
    """SQLite storage for RSS articles."""

    def __init__(self, db_path: str = "articles.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema with version tracking."""
        with self._connect() as conn:
            # Schema version tracking table - always create first
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Get current schema version
            row = conn.execute(
                "SELECT MAX(version) as v FROM schema_version"
            ).fetchone()
            current_version = row["v"] if row and row["v"] is not None else 0

            # Run migrations only if needed
            if current_version < SCHEMA_VERSION:
                self._run_migrations(conn, current_version)
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,)
                )
                conn.commit()

    def _run_migrations(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Run schema migrations from from_version to SCHEMA_VERSION.

        Each migration is idempotent - safe to run multiple times.
        """
        if from_version < 1:
            print(f"Running schema migration to version 1...", file=sys.stderr)
            self._migrate_to_v1(conn)

        # Future migrations:
        # if from_version < 2:
        #     self._migrate_to_v2(conn)

    def _migrate_to_v1(self, conn: sqlite3.Connection) -> None:
        """Version 1: Initial schema with all current tables."""
        # Articles table with all columns
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                feed_url TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT UNIQUE NOT NULL,
                published TIMESTAMP,
                content TEXT,
                summary TEXT,
                trend_tags TEXT,
                signal_tags TEXT,
                story_id TEXT,
                analyzed_at TIMESTAMP,
                spam_status TEXT,
                spam_reason TEXT,
                spam_flagged_at TIMESTAMP,
                embedding TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add columns if they don't exist (for databases created before versioning)
        columns_to_add = [
            ("signal_tags", "TEXT"),
            ("story_id", "TEXT"),
            ("analyzed_at", "TIMESTAMP"),
            ("spam_status", "TEXT"),
            ("spam_reason", "TEXT"),
            ("spam_flagged_at", "TIMESTAMP"),
            ("embedding", "TEXT"),
        ]
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Indexes for articles
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_feed_url ON articles(feed_url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_analyzed ON articles(analyzed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_story ON articles(story_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_spam ON articles(spam_status)")

        # Stories table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                keywords TEXT,
                first_seen TIMESTAMP NOT NULL,
                last_updated TIMESTAMP NOT NULL,
                lifecycle_state TEXT DEFAULT 'emerging',
                article_ids TEXT,
                news_item_ids TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stories_lifecycle ON stories(lifecycle_state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stories_last_updated ON stories(last_updated)")

        # News items table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_items (
                id TEXT PRIMARY KEY,
                story_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                first_reported_by TEXT,
                first_seen TIMESTAMP NOT NULL,
                article_ids TEXT,
                item_type TEXT DEFAULT 'new_info',
                confidence REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (story_id) REFERENCES stories(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_items_story ON news_items(story_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_items_type ON news_items(item_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_items_first_seen ON news_items(first_seen)")

        # Perspective cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS perspective_cache (
                story_id TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source_articles TEXT,
                confidence REAL DEFAULT 0.5,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (story_id, category),
                FOREIGN KEY (story_id) REFERENCES stories(id)
            )
        """)

        # User perspective configuration table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_perspective_config (
                id INTEGER PRIMARY KEY DEFAULT 1,
                enabled_categories TEXT,
                default_categories TEXT,
                category_order TEXT,
                CHECK (id = 1)
            )
        """)

        conn.commit()
        print("Schema migrated to version 1", file=sys.stderr)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save_article(self, article: Article) -> bool:
        """
        Save an article to the database.
        Returns True if inserted, False if already exists.
        """
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO articles (id, feed_url, title, link, published, content)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article.id,
                        article.feed_url,
                        article.title,
                        article.link,
                        article.published,
                        article.content,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Return False silently - caller should batch these into summary
                return False

    def get_article(self, article_id: str) -> Optional[Article]:
        """Get an article by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM articles WHERE id = ?", (article_id,)
            ).fetchone()
            if row:
                return self._row_to_article(row)
            return None

    def get_articles_by_ids(self, article_ids: list[str]) -> list[Article]:
        """Get multiple articles by their IDs.

        Args:
            article_ids: List of article IDs to retrieve

        Returns:
            List of Article objects (in order of IDs provided, skipping missing)
        """
        if not article_ids:
            return []

        with self._connect() as conn:
            placeholders = ",".join("?" * len(article_ids))
            rows = conn.execute(
                f"SELECT * FROM articles WHERE id IN ({placeholders})",
                article_ids,
            ).fetchall()

            # Convert rows to articles and maintain order
            articles_by_id = {row["id"]: self._row_to_article(row) for row in rows}
            return [articles_by_id[aid] for aid in article_ids if aid in articles_by_id]

    def get_articles(
        self,
        limit: int = 50,
        offset: int = 0,
        feed_url: Optional[str] = None,
        unsummarized_only: bool = False,
    ) -> list[Article]:
        """Get articles with optional filtering."""
        query = "SELECT * FROM articles WHERE 1=1"
        params: list = []

        if feed_url:
            query += " AND feed_url = ?"
            params.append(feed_url)

        if unsummarized_only:
            query += " AND summary IS NULL"

        query += " ORDER BY published DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_article(row) for row in rows]

    def get_unanalyzed_articles(
        self,
        feed_url: Optional[str] = None,
        exclude_spam: bool = True,
        min_content_length: int = 0,
    ) -> list[Article]:
        """Get all articles that haven't been analyzed yet.

        Returns articles where analyzed_at IS NULL, ordered by published date.
        No artificial limit - returns ALL unanalyzed articles.

        Args:
            feed_url: Optional filter by feed
            exclude_spam: If True, excludes articles flagged as spam
            min_content_length: Minimum content length (filters out short articles at DB level)
        """
        query = "SELECT * FROM articles WHERE analyzed_at IS NULL"
        params: list = []

        if feed_url:
            query += " AND feed_url = ?"
            params.append(feed_url)

        if exclude_spam:
            query += " AND (spam_status IS NULL OR spam_status != 'spam')"

        if min_content_length > 0:
            query += " AND content IS NOT NULL AND LENGTH(content) >= ?"
            params.append(min_content_length)

        query += " ORDER BY published DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_article(row) for row in rows]

    def mark_as_analyzed(self, article_id: str) -> None:
        """Mark an article as analyzed."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET analyzed_at = ? WHERE id = ?",
                (datetime.now().isoformat(), article_id),
            )
            conn.commit()

    def get_articles_needing_embeddings(self, exclude_spam: bool = True) -> list[Article]:
        """Get articles that don't have embeddings yet.

        Returns articles where embedding IS NULL, ordered by published date.
        """
        query = "SELECT * FROM articles WHERE embedding IS NULL"
        params: list = []

        if exclude_spam:
            query += " AND (spam_status IS NULL OR spam_status != 'spam')"

        query += " ORDER BY published DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_article(row) for row in rows]

    def save_embedding(self, article_id: str, embedding: list[float]) -> None:
        """Save a pre-computed embedding for an article."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET embedding = ? WHERE id = ?",
                (json.dumps(embedding), article_id),
            )
            conn.commit()

    def get_embedding(self, article_id: str) -> list[float] | None:
        """Get the pre-computed embedding for an article."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT embedding FROM articles WHERE id = ?",
                (article_id,),
            ).fetchone()
            if row and row["embedding"]:
                return json.loads(row["embedding"])
            return None

    def get_articles_with_embeddings_not_analyzed(self, exclude_spam: bool = True) -> list[Article]:
        """Get articles that have embeddings but haven't been fully analyzed.

        These are ready for Phase 2 (LLM processing).
        """
        query = "SELECT * FROM articles WHERE embedding IS NOT NULL AND analyzed_at IS NULL"
        params: list = []

        if exclude_spam:
            query += " AND (spam_status IS NULL OR spam_status != 'spam')"

        query += " ORDER BY published DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_article(row) for row in rows]

    def update_summary(self, article_id: str, summary: str) -> None:
        """Update an article's summary."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET summary = ? WHERE id = ?",
                (summary, article_id),
            )
            conn.commit()

    def update_trends(self, article_id: str, trend_tags: str) -> None:
        """Update an article's trend tags."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET trend_tags = ? WHERE id = ?",
                (trend_tags, article_id),
            )
            conn.commit()

    def update_signal_tags(self, article_id: str, signal_tags: str) -> None:
        """Update an article's signal tags."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET signal_tags = ? WHERE id = ?",
                (signal_tags, article_id),
            )
            conn.commit()

    def get_articles_by_signal_tags(
        self,
        include_tags: Optional[list[str]] = None,
        exclude_tags: Optional[list[str]] = None,
        limit: int = 50,
    ) -> list[Article]:
        """
        Get articles filtered by signal tags.

        Args:
            include_tags: List of tags that must be present (OR logic)
            exclude_tags: List of tags that must NOT be present
            limit: Maximum number of articles to return

        Returns:
            List of articles matching the tag criteria
        """
        articles = self.get_articles(limit=limit * 2)  # Get more for filtering
        filtered = []

        for article in articles:
            if not article.signal_tags:
                continue

            # Parse signal tags
            tags_lower = article.signal_tags.lower()

            # Check exclusions first
            if exclude_tags:
                if any(tag.lower() in tags_lower for tag in exclude_tags):
                    continue

            # Check inclusions
            if include_tags:
                if not any(tag.lower() in tags_lower for tag in include_tags):
                    continue

            filtered.append(article)

            if len(filtered) >= limit:
                break

        return filtered

    def get_article_count(self) -> int:
        """Get total number of articles."""
        with self._connect() as conn:
            result = conn.execute("SELECT COUNT(*) FROM articles").fetchone()
            return result[0] if result else 0

    def get_feed_stats(self) -> list[dict]:
        """Get statistics per feed."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT
                    feed_url,
                    COUNT(*) as article_count,
                    SUM(CASE WHEN summary IS NOT NULL THEN 1 ELSE 0 END) as summarized_count,
                    MAX(published) as latest_article
                FROM articles
                GROUP BY feed_url
                ORDER BY article_count DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def _row_to_article(self, row: sqlite3.Row) -> Article:
        """Convert a database row to an Article object."""
        # Check if story_id column exists in the row
        try:
            story_id_value = row["story_id"]
        except (KeyError, IndexError) as e:
            import sys
            print(f"Legacy row missing story_id column: {e}", file=sys.stderr)
            story_id_value = None

        return Article(
            id=row["id"],
            feed_url=row["feed_url"],
            title=row["title"],
            link=row["link"],
            published=row["published"],
            content=row["content"],
            summary=row["summary"],
            trend_tags=row["trend_tags"],
            story_id=story_id_value,
            created_at=row["created_at"],
        )

    def update_article_story(self, article_id: str, story_id: str) -> None:
        """Update an article's story association."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE articles SET story_id = ? WHERE id = ?",
                (story_id, article_id),
            )
            conn.commit()

    # Story management methods

    def save_story(self, story: Story) -> bool:
        """Save a story to the database. Returns True if inserted, False if already exists."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO stories (
                        id, title, description, keywords, first_seen, last_updated,
                        lifecycle_state, article_ids, news_item_ids
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        story.id,
                        story.title,
                        story.description,
                        json.dumps(story.keywords),
                        story.first_seen,
                        story.last_updated,
                        story.lifecycle_state,
                        json.dumps(story.article_ids),
                        json.dumps(story.news_item_ids),
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Return False silently - caller should batch these into summary
                return False

    def get_story(self, story_id: str) -> Optional[Story]:
        """Get a story by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM stories WHERE id = ?", (story_id,)
            ).fetchone()
            if row:
                return self._row_to_story(row)
            return None

    def get_active_stories(self, limit: int = 50) -> list[Story]:
        """Get active stories (not resolved), sorted by last update."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM stories
                WHERE lifecycle_state != 'resolved'
                ORDER BY last_updated DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._row_to_story(row) for row in rows]

    def get_all_stories(
        self, limit: int = 100, lifecycle_state: Optional[str] = None
    ) -> list[Story]:
        """Get stories with optional filtering by lifecycle state."""
        query = "SELECT * FROM stories WHERE 1=1"
        params: list = []

        if lifecycle_state:
            query += " AND lifecycle_state = ?"
            params.append(lifecycle_state)

        query += " ORDER BY last_updated DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_story(row) for row in rows]

    def update_story(self, story: Story) -> None:
        """Update an existing story."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE stories SET
                    title = ?, description = ?, keywords = ?,
                    last_updated = ?, lifecycle_state = ?,
                    article_ids = ?, news_item_ids = ?
                WHERE id = ?
                """,
                (
                    story.title,
                    story.description,
                    json.dumps(story.keywords),
                    story.last_updated,
                    story.lifecycle_state,
                    json.dumps(story.article_ids),
                    json.dumps(story.news_item_ids),
                    story.id,
                ),
            )
            conn.commit()

    def update_story_title(self, story_id: str, title: str) -> None:
        """Update just the title of a story."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE stories SET title = ? WHERE id = ?",
                (title, story_id),
            )
            conn.commit()

    def _row_to_story(self, row: sqlite3.Row) -> Story:
        """Convert a database row to a Story object."""
        return Story(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            first_seen=row["first_seen"],
            last_updated=row["last_updated"],
            lifecycle_state=row["lifecycle_state"],
            article_ids=json.loads(row["article_ids"]) if row["article_ids"] else [],
            news_item_ids=json.loads(row["news_item_ids"]) if row["news_item_ids"] else [],
            created_at=row["created_at"],
        )

    # News item management methods

    def save_news_item(self, item: NewsItem) -> bool:
        """Save a news item to the database. Returns True if inserted, False if already exists."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO news_items (
                        id, story_id, title, description, first_reported_by,
                        first_seen, article_ids, item_type, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.id,
                        item.story_id,
                        item.title,
                        item.description,
                        item.first_reported_by,
                        item.first_seen,
                        json.dumps(item.article_ids),
                        item.item_type,
                        item.confidence,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Return False silently - caller should batch these into summary
                return False

    def get_news_items(self, story_id: str) -> list[NewsItem]:
        """Get all news items for a story, sorted by first_seen."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM news_items
                WHERE story_id = ?
                ORDER BY first_seen ASC
                """,
                (story_id,),
            ).fetchall()
            return [self._row_to_news_item(row) for row in rows]

    def update_news_item(self, item: NewsItem) -> None:
        """Update an existing news item."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE news_items SET
                    title = ?, description = ?, article_ids = ?,
                    item_type = ?, confidence = ?
                WHERE id = ?
                """,
                (
                    item.title,
                    item.description,
                    json.dumps(item.article_ids),
                    item.item_type,
                    item.confidence,
                    item.id,
                ),
            )
            conn.commit()

    def _row_to_news_item(self, row: sqlite3.Row) -> NewsItem:
        """Convert a database row to a NewsItem object."""
        return NewsItem(
            id=row["id"],
            story_id=row["story_id"],
            title=row["title"],
            description=row["description"],
            first_reported_by=row["first_reported_by"],
            first_seen=row["first_seen"],
            article_ids=json.loads(row["article_ids"]) if row["article_ids"] else [],
            item_type=row["item_type"],
            confidence=row["confidence"],
            created_at=row["created_at"],
        )

    # Term history management methods for emergence detection

    def save_term_mention(
        self,
        term: str,
        week_bucket: str,
        article_id: str,
        category: str,
    ) -> None:
        """
        Record a term mention in the history.

        Args:
            term: The term being tracked (normalized to lowercase)
            week_bucket: ISO week format (e.g., "2025-W50")
            article_id: ID of the article mentioning the term
            category: Category/domain of the article
        """
        with self._connect() as conn:
            # Try to insert, or update if exists
            row = conn.execute(
                "SELECT id, article_ids, categories FROM term_history WHERE term = ? AND week_bucket = ?",
                (term, week_bucket),
            ).fetchone()

            if row:
                # Update existing record
                existing_article_ids = json.loads(row["article_ids"]) if row["article_ids"] else []
                existing_categories = json.loads(row["categories"]) if row["categories"] else []

                if article_id not in existing_article_ids:
                    existing_article_ids.append(article_id)

                if category not in existing_categories:
                    existing_categories.append(category)

                conn.execute(
                    """
                    UPDATE term_history SET
                        mention_count = ?,
                        article_ids = ?,
                        categories = ?
                    WHERE id = ?
                    """,
                    (
                        len(existing_article_ids),
                        json.dumps(existing_article_ids),
                        json.dumps(existing_categories),
                        row["id"],
                    ),
                )
            else:
                # Insert new record
                conn.execute(
                    """
                    INSERT INTO term_history (term, week_bucket, mention_count, article_ids, categories)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        term,
                        week_bucket,
                        1,
                        json.dumps([article_id]),
                        json.dumps([category] if category else []),
                    ),
                )

            conn.commit()

    def get_term_history(self, term: str, weeks_back: int = 8) -> dict[str, int]:
        """
        Get historical mention data for a term.

        Args:
            term: The term to look up
            weeks_back: How many weeks of history to retrieve

        Returns:
            Dictionary mapping week_bucket to mention count
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT week_bucket, mention_count
                FROM term_history
                WHERE term = ?
                ORDER BY week_bucket DESC
                LIMIT ?
                """,
                (term, weeks_back),
            ).fetchall()

            return {row["week_bucket"]: row["mention_count"] for row in rows}

    def get_all_terms_with_history(self, min_weeks: int = 4) -> list[str]:
        """
        Get all terms with sufficient history for analysis.

        Args:
            min_weeks: Minimum number of weeks a term must appear

        Returns:
            List of terms that have appeared in at least min_weeks weeks
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT term, COUNT(DISTINCT week_bucket) as week_count
                FROM term_history
                GROUP BY term
                HAVING week_count >= ?
                ORDER BY week_count DESC
                """,
                (min_weeks,),
            ).fetchall()

            return [row["term"] for row in rows]

    def get_term_categories(self, term: str) -> list[str]:
        """Get all categories where a term has appeared."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT categories FROM term_history WHERE term = ?",
                (term,),
            ).fetchall()

            all_categories = set()
            for row in rows:
                if row["categories"]:
                    categories = json.loads(row["categories"])
                    all_categories.update(categories)

            return list(all_categories)
