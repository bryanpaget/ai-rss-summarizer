"""Adaptive Personal Context Engine for personalized article relevance."""

import json
import math
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Iterator


@dataclass
class UserContextProfile:
    """User's personal context for content filtering."""

    # Core identity
    role: Optional[str] = None

    # Active interests
    current_projects: List[str] = field(default_factory=list)
    watching: List[str] = field(default_factory=list)
    ignore: List[str] = field(default_factory=list)
    pinned: List[str] = field(default_factory=list)

    # Settings
    relevance_threshold: float = 0.3
    diversity_factor: float = 0.15
    personalization_strength: float = 0.8  # 0-1, how much to personalize

    # Metadata
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    last_feedback_prompt: Optional[datetime] = None

    def __post_init__(self):
        """Initialize timestamps if not set."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.last_updated:
            data["last_updated"] = self.last_updated.isoformat()
        if self.last_feedback_prompt:
            data["last_feedback_prompt"] = self.last_feedback_prompt.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "UserContextProfile":
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        if "created_at" in data and data["created_at"]:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "last_updated" in data and data["last_updated"]:
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        if "last_feedback_prompt" in data and data["last_feedback_prompt"]:
            data["last_feedback_prompt"] = datetime.fromisoformat(
                data["last_feedback_prompt"]
            )
        return cls(**data)


@dataclass
class ArticleInteraction:
    """Record of user interaction with an article."""

    article_id: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Interaction types
    expanded: bool = False
    time_spent: Optional[float] = None  # Seconds
    saved: bool = False
    shared: bool = False
    skipped: bool = False

    # Feedback
    thumbs_up: Optional[bool] = None
    relevance_score: Optional[float] = None


class UserContextStore:
    """Storage for user context and interaction history."""

    VERSION = 1

    def __init__(
        self, profile_path: str = "config/user_context.json", db_path: str = "articles.db"
    ):
        self.profile_path = Path(profile_path)
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize interaction tracking table."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    article_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    expanded INTEGER DEFAULT 0,
                    time_spent REAL,
                    saved INTEGER DEFAULT 0,
                    shared INTEGER DEFAULT 0,
                    skipped INTEGER DEFAULT 0,
                    thumbs_up INTEGER,
                    relevance_score REAL,
                    PRIMARY KEY (article_id, timestamp)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_interactions_article
                ON user_interactions(article_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_interactions_timestamp
                ON user_interactions(timestamp)
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

    def load_profile(self) -> UserContextProfile:
        """Load user profile from disk, or create default."""
        if not self.profile_path.exists():
            return UserContextProfile()

        try:
            with open(self.profile_path) as f:
                data = json.load(f)

            # Validate version
            version = data.get("_version", 1)
            if version != self.VERSION:
                data = self._migrate_profile(data, version)

            # Remove version field before creating profile
            data.pop("_version", None)
            return UserContextProfile.from_dict(data)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Log error and return default profile
            print(f"Warning: Could not load user profile: {e}")
            return UserContextProfile()

    def save_profile(self, profile: UserContextProfile) -> None:
        """Save user profile to disk."""
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)

        profile.last_updated = datetime.now()
        data = profile.to_dict()
        data["_version"] = self.VERSION

        # Atomic write using temp file
        temp_path = self.profile_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)

        temp_path.replace(self.profile_path)

    def _migrate_profile(self, data: dict, from_version: int) -> dict:
        """Migrate profile from old version to current."""
        # Placeholder for future migrations
        # For now, just return data as-is
        return data

    def record_interaction(self, interaction: ArticleInteraction) -> None:
        """Record a user interaction with an article."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_interactions
                (article_id, timestamp, expanded, time_spent, saved, shared,
                 skipped, thumbs_up, relevance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.article_id,
                    interaction.timestamp,
                    1 if interaction.expanded else 0,
                    interaction.time_spent,
                    1 if interaction.saved else 0,
                    1 if interaction.shared else 0,
                    1 if interaction.skipped else 0,
                    1 if interaction.thumbs_up else (0 if interaction.thumbs_up is False else None),
                    interaction.relevance_score,
                ),
            )
            conn.commit()

    def get_interactions(
        self, article_id: Optional[str] = None, days: int = 90
    ) -> List[ArticleInteraction]:
        """Get interaction history, optionally filtered."""
        cutoff = datetime.now() - timedelta(days=days)

        query = "SELECT * FROM user_interactions WHERE timestamp > ?"
        params = [cutoff]

        if article_id:
            query += " AND article_id = ?"
            params.append(article_id)

        query += " ORDER BY timestamp DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        interactions = []
        for row in rows:
            interactions.append(
                ArticleInteraction(
                    article_id=row["article_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    expanded=bool(row["expanded"]),
                    time_spent=row["time_spent"],
                    saved=bool(row["saved"]),
                    shared=bool(row["shared"]),
                    skipped=bool(row["skipped"]),
                    thumbs_up=bool(row["thumbs_up"]) if row["thumbs_up"] is not None else None,
                    relevance_score=row["relevance_score"],
                )
            )

        return interactions

    def get_topic_engagement(self, days: int = 30) -> Dict[str, float]:
        """
        Get engagement rate per topic over recent history.

        Returns:
            Dict mapping topic -> engagement_rate (0-1)
        """
        # This requires joining with articles table to get trend_tags
        cutoff = datetime.now() - timedelta(days=days)

        query = """
            SELECT a.trend_tags,
                   SUM(CASE WHEN i.expanded = 1 OR i.saved = 1 THEN 1 ELSE 0 END) as engaged,
                   COUNT(*) as total
            FROM user_interactions i
            JOIN articles a ON i.article_id = a.id
            WHERE i.timestamp > ? AND a.trend_tags IS NOT NULL
            GROUP BY a.trend_tags
        """

        engagement = {}
        with self._connect() as conn:
            rows = conn.execute(query, [cutoff]).fetchall()

        for row in rows:
            tags = row["trend_tags"]
            if tags:
                # Split comma-separated tags
                for tag in tags.split(","):
                    tag = tag.strip()
                    if tag:
                        rate = row["engaged"] / row["total"] if row["total"] > 0 else 0
                        engagement[tag] = rate

        return engagement

    def clear_history(self, days: Optional[int] = None) -> int:
        """
        Clear interaction history.

        Args:
            days: If specified, only clear history older than this many days.
                  If None, clear all history.

        Returns:
            Number of records deleted.
        """
        with self._connect() as conn:
            if days is None:
                result = conn.execute("DELETE FROM user_interactions")
            else:
                cutoff = datetime.now() - timedelta(days=days)
                result = conn.execute(
                    "DELETE FROM user_interactions WHERE timestamp < ?", [cutoff]
                )
            deleted = result.rowcount
            conn.commit()

        return deleted

    def export_data(self) -> dict:
        """Export all user data for backup/portability."""
        profile = self.load_profile()
        interactions = self.get_interactions(days=365)  # Get full year

        return {
            "profile": profile.to_dict(),
            "interactions": [
                {
                    "article_id": i.article_id,
                    "timestamp": i.timestamp.isoformat(),
                    "expanded": i.expanded,
                    "time_spent": i.time_spent,
                    "saved": i.saved,
                    "shared": i.shared,
                    "skipped": i.skipped,
                    "thumbs_up": i.thumbs_up,
                    "relevance_score": i.relevance_score,
                }
                for i in interactions
            ],
            "version": self.VERSION,
        }

    def import_data(self, data: dict) -> None:
        """Import user data from export."""
        # Import profile
        if "profile" in data:
            profile = UserContextProfile.from_dict(data["profile"])
            self.save_profile(profile)

        # Import interactions
        if "interactions" in data:
            for interaction_data in data["interactions"]:
                interaction = ArticleInteraction(
                    article_id=interaction_data["article_id"],
                    timestamp=datetime.fromisoformat(interaction_data["timestamp"]),
                    expanded=interaction_data.get("expanded", False),
                    time_spent=interaction_data.get("time_spent"),
                    saved=interaction_data.get("saved", False),
                    shared=interaction_data.get("shared", False),
                    skipped=interaction_data.get("skipped", False),
                    thumbs_up=interaction_data.get("thumbs_up"),
                    relevance_score=interaction_data.get("relevance_score"),
                )
                self.record_interaction(interaction)


class RelevanceEngine:
    """Calculate personalized relevance scores for articles."""

    # Decay constants
    DECAY_HALF_LIFE_DAYS = 14  # Standard topic decay
    COMPLETED_DECAY_HALF_LIFE_DAYS = 7  # Faster decay for completed projects

    def __init__(self, store: UserContextStore):
        self.store = store

    def calculate_relevance(
        self, article, profile: UserContextProfile
    ) -> float:
        """
        Calculate relevance score (0-1) for an article.

        Factors:
        1. Topic match (40%): Does it match watching/current_projects?
        2. Historical engagement (30%): Similar articles engaged with before?
        3. Recency (15%): Recent topics get temporary boost
        4. Diversity (15%): Avoid filter bubbles, surface some new topics
        """
        # Get article topics
        topics = self._extract_topics(article)
        if not topics:
            return 0.5  # Neutral for uncategorized

        # Factor 1: Topic match (40%)
        topic_score = self._calculate_topic_match(topics, profile)

        # Factor 2: Historical engagement (30%)
        engagement_score = self._calculate_engagement_score(topics)

        # Factor 3: Recency boost (15%)
        recency_score = self._calculate_recency_boost(topics)

        # Factor 4: Diversity (15%)
        diversity_score = self._calculate_diversity_score(topics)

        # Weighted combination
        raw_score = (
            topic_score * 0.4
            + engagement_score * 0.3
            + recency_score * 0.15
            + diversity_score * 0.15
        )

        # Apply personalization strength
        # At 0 strength, return 0.5 (neutral)
        # At 1.0 strength, return raw score
        final_score = 0.5 + (raw_score - 0.5) * profile.personalization_strength

        # Clamp to [0, 1]
        return max(0.0, min(1.0, final_score))

    def _extract_topics(self, article) -> List[str]:
        """Extract topics from article (trend tags or content analysis)."""
        topics = []

        # From trend tags
        if hasattr(article, "trend_tags") and article.trend_tags:
            topics.extend([t.strip() for t in article.trend_tags.split(",")])

        # From title (simple keyword extraction)
        if hasattr(article, "title") and article.title:
            # This is a simple implementation
            # Could be enhanced with NLP/embeddings
            title_lower = article.title.lower()
            topics.extend([word for word in title_lower.split() if len(word) > 4])

        return [t for t in topics if t]  # Remove empty strings

    def _calculate_topic_match(
        self, topics: List[str], profile: UserContextProfile
    ) -> float:
        """Calculate how well topics match user's profile."""
        if not topics:
            return 0.5

        score = 0.5  # Start neutral

        # Check each topic against profile
        topics_lower = [t.lower() for t in topics]

        # Exact matches in watching/current_projects
        watching_lower = [w.lower() for w in profile.watching]
        projects_lower = [p.lower() for p in profile.current_projects]

        for topic in topics_lower:
            # Direct matches
            if any(topic in w or w in topic for w in watching_lower):
                score += 0.4
            if any(topic in p or p in topic for p in projects_lower):
                score += 0.4

            # Pinned topics (always maintain relevance)
            if any(topic in p.lower() or p.lower() in topic for p in profile.pinned):
                score = max(score, 0.7)

            # Ignore list
            if any(topic in i.lower() or i.lower() in topic for i in profile.ignore):
                score -= 0.5

        return max(0.0, min(1.0, score))

    def _calculate_engagement_score(self, topics: List[str]) -> float:
        """Calculate score based on historical engagement with similar topics."""
        engagement_rates = self.store.get_topic_engagement(days=30)

        if not engagement_rates:
            return 0.5  # Neutral if no history

        # Find engagement rates for these topics
        scores = []
        for topic in topics:
            topic_lower = topic.lower()
            # Look for matching or similar topics in history
            for hist_topic, rate in engagement_rates.items():
                hist_lower = hist_topic.lower()
                if topic_lower in hist_lower or hist_lower in topic_lower:
                    scores.append(rate)

        if not scores:
            return 0.5

        # Average engagement rate
        return sum(scores) / len(scores)

    def _calculate_recency_boost(self, topics: List[str]) -> float:
        """Boost topics that were engaged with recently."""
        recent_interactions = self.store.get_interactions(days=7)

        if not recent_interactions:
            return 0.5

        # Simple heuristic: boost if any recent interaction
        # More sophisticated: check if topics match recent interactions
        # For now, return neutral
        return 0.5

    def _calculate_diversity_score(self, topics: List[str]) -> float:
        """
        Score for diversity.

        Give slight boost to topics user hasn't seen much.
        This prevents filter bubbles.
        """
        engagement_rates = self.store.get_topic_engagement(days=30)

        if not engagement_rates:
            # No history, all topics are diverse
            return 0.8

        # Check if this is a new topic
        topics_lower = [t.lower() for t in topics]
        seen_topics = {t.lower() for t in engagement_rates.keys()}

        new_topic_count = sum(1 for t in topics_lower if t not in seen_topics)
        diversity_ratio = new_topic_count / len(topics_lower) if topics_lower else 0

        # Higher diversity ratio = higher score
        return 0.5 + diversity_ratio * 0.5

    def apply_relevance_decay(
        self, profile: UserContextProfile, days_since_update: int
    ) -> UserContextProfile:
        """
        Apply decay to topics based on time since last interaction.

        This is a placeholder for more sophisticated decay logic.
        """
        # For now, return profile unchanged
        # In future, could:
        # - Reduce weights of topics in watching list based on engagement
        # - Automatically move inactive projects to archive
        # - Adjust relevance thresholds based on overall engagement
        return profile


def sort_by_relevance(articles: List, profile: UserContextProfile, store: UserContextStore) -> List:
    """Sort articles by relevance score."""
    engine = RelevanceEngine(store)

    # Calculate scores
    scored_articles = []
    for article in articles:
        relevance = engine.calculate_relevance(article, profile)
        # Store score in article object if possible
        if hasattr(article, "__dict__"):
            article.relevance_score = relevance
        scored_articles.append((relevance, article))

    # Sort by score descending
    scored_articles.sort(key=lambda x: x[0], reverse=True)

    return [article for score, article in scored_articles]


def apply_diversity_filter(
    articles: List, profile: UserContextProfile, diversity_factor: float = 0.15
) -> List:
    """
    Apply diversity filter to ensure some variety in recommendations.

    Args:
        articles: Articles already sorted by relevance
        profile: User context profile
        diversity_factor: What fraction should be diverse content (0-1)

    Returns:
        Mixed list with diversity_factor% diverse content
    """
    if not articles:
        return articles

    # Number of diverse articles to include
    diverse_count = max(1, int(len(articles) * diversity_factor))

    # Take top N minus diverse_count
    highly_relevant = articles[: len(articles) - diverse_count]

    # Take some from the bottom (diverse content)
    diverse = articles[-diverse_count:]

    # Interleave them
    result = []
    for i in range(max(len(highly_relevant), len(diverse))):
        if i < len(highly_relevant):
            result.append(highly_relevant[i])
        if i < len(diverse):
            result.append(diverse[i])

    return result
