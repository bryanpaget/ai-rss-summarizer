"""SQLite storage layer for articles and metadata."""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional


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
    created_at: Optional[datetime] = None


class Storage:
    """SQLite storage for RSS articles."""

    def __init__(self, db_path: str = "articles.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._connect() as conn:
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_feed_url ON articles(feed_url)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published)
            """)
            conn.commit()

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
        return Article(
            id=row["id"],
            feed_url=row["feed_url"],
            title=row["title"],
            link=row["link"],
            published=row["published"],
            content=row["content"],
            summary=row["summary"],
            trend_tags=row["trend_tags"],
            created_at=row["created_at"],
        )
