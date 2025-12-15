"""Knowledge extraction and accumulation system.

Extracts structured insights from articles, detects connections,
and provides a queryable knowledge base.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .storage import Article


@dataclass
class Insight:
    """Represents a knowledge insight extracted from an article."""

    id: str
    article_id: str
    content: str
    insight_type: str  # 'technical', 'tool', 'statistic', 'opinion'
    confidence: str  # 'high', 'medium', 'low'
    confidence_reason: Optional[str] = None
    extracted_at: Optional[datetime] = None


@dataclass
class Entity:
    """Represents an entity (tool, person, company, concept) mentioned in articles."""

    id: str
    name: str
    entity_type: str  # 'tool', 'person', 'company', 'concept'
    first_seen: Optional[datetime] = None
    mention_count: int = 1


@dataclass
class Relationship:
    """Represents a relationship between two insights."""

    id: str
    source_insight_id: str
    target_insight_id: str
    relationship_type: str  # 'confirms', 'contradicts', 'refines', 'extends'
    strength: float = 1.0
    detected_at: Optional[datetime] = None


@dataclass
class UserContext:
    """Represents user's personal context (projects, interests)."""

    id: str
    context_type: str  # 'project', 'interest', 'watching'
    name: str
    description: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgeBase:
    """Manages the knowledge extraction and storage system."""

    def __init__(self, db_path: str = "knowledge.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema for knowledge storage."""
        with self._connect() as conn:
            # Core knowledge insights table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_insights (
                    id TEXT PRIMARY KEY,
                    article_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    insight_type TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    confidence_reason TEXT,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Entities table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    entity_type TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    mention_count INTEGER DEFAULT 1
                )
            """)

            # Link insights to entities
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insight_entities (
                    insight_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    relevance TEXT,
                    PRIMARY KEY (insight_id, entity_id),
                    FOREIGN KEY (insight_id) REFERENCES knowledge_insights(id),
                    FOREIGN KEY (entity_id) REFERENCES knowledge_entities(id)
                )
            """)

            # Relationships between insights
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_relationships (
                    id TEXT PRIMARY KEY,
                    source_insight_id TEXT NOT NULL,
                    target_insight_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL DEFAULT 1.0,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_insight_id) REFERENCES knowledge_insights(id),
                    FOREIGN KEY (target_insight_id) REFERENCES knowledge_insights(id)
                )
            """)

            # User context table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_context (
                    id TEXT PRIMARY KEY,
                    context_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Link insights to user context
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insight_context (
                    insight_id TEXT NOT NULL,
                    context_id TEXT NOT NULL,
                    relevance_score REAL DEFAULT 0.5,
                    PRIMARY KEY (insight_id, context_id),
                    FOREIGN KEY (insight_id) REFERENCES knowledge_insights(id),
                    FOREIGN KEY (context_id) REFERENCES user_context(id)
                )
            """)

            # Create indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_insights_type ON knowledge_insights(insight_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_insights_confidence ON knowledge_insights(confidence)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_insights_article ON knowledge_insights(article_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON knowledge_entities(entity_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON knowledge_entities(name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relationships_type ON knowledge_relationships(relationship_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relationships_source ON knowledge_relationships(source_insight_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_relationships_target ON knowledge_relationships(target_insight_id)"
            )

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

    def save_insight(self, insight: Insight) -> bool:
        """Save an insight to the database."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO knowledge_insights
                    (id, article_id, content, insight_type, confidence, confidence_reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        insight.id,
                        insight.article_id,
                        insight.content,
                        insight.insight_type,
                        insight.confidence,
                        insight.confidence_reason,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_insight(self, insight_id: str) -> Optional[Insight]:
        """Get an insight by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_insights WHERE id = ?", (insight_id,)
            ).fetchone()
            if row:
                return self._row_to_insight(row)
            return None

    def get_insights(
        self,
        limit: int = 50,
        insight_type: Optional[str] = None,
        confidence: Optional[str] = None,
        article_id: Optional[str] = None,
    ) -> list[Insight]:
        """Get insights with optional filtering."""
        query = "SELECT * FROM knowledge_insights WHERE 1=1"
        params: list = []

        if insight_type:
            query += " AND insight_type = ?"
            params.append(insight_type)

        if confidence:
            query += " AND confidence = ?"
            params.append(confidence)

        if article_id:
            query += " AND article_id = ?"
            params.append(article_id)

        query += " ORDER BY extracted_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_insight(row) for row in rows]

    def save_entity(self, entity: Entity) -> bool:
        """Save or update an entity."""
        with self._connect() as conn:
            try:
                # Try to insert
                conn.execute(
                    """
                    INSERT INTO knowledge_entities
                    (id, name, entity_type, mention_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (entity.id, entity.name, entity.entity_type, entity.mention_count),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Entity exists, increment mention count
                conn.execute(
                    """
                    UPDATE knowledge_entities
                    SET mention_count = mention_count + 1
                    WHERE name = ? AND entity_type = ?
                    """,
                    (entity.name, entity.entity_type),
                )
                conn.commit()
                return False

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_entities WHERE id = ?", (entity_id,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
            return None

    def get_entity_by_name(self, name: str, entity_type: str) -> Optional[Entity]:
        """Get an entity by name and type."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_entities WHERE name = ? AND entity_type = ?",
                (name, entity_type),
            ).fetchone()
            if row:
                return self._row_to_entity(row)
            return None

    def link_insight_to_entity(
        self, insight_id: str, entity_id: str, relevance: Optional[str] = None
    ) -> None:
        """Link an insight to an entity."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO insight_entities
                (insight_id, entity_id, relevance)
                VALUES (?, ?, ?)
                """,
                (insight_id, entity_id, relevance),
            )
            conn.commit()

    def save_relationship(self, relationship: Relationship) -> bool:
        """Save a relationship between insights."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO knowledge_relationships
                    (id, source_insight_id, target_insight_id, relationship_type, strength)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        relationship.id,
                        relationship.source_insight_id,
                        relationship.target_insight_id,
                        relationship.relationship_type,
                        relationship.strength,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_relationships(
        self,
        insight_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> list[Relationship]:
        """Get relationships, optionally filtered by insight or type."""
        query = "SELECT * FROM knowledge_relationships WHERE 1=1"
        params: list = []

        if insight_id:
            query += " AND (source_insight_id = ? OR target_insight_id = ?)"
            params.extend([insight_id, insight_id])

        if relationship_type:
            query += " AND relationship_type = ?"
            params.append(relationship_type)

        query += " ORDER BY detected_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_relationship(row) for row in rows]

    def save_context(self, context: UserContext) -> bool:
        """Save user context."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO user_context
                    (id, context_type, name, description, active)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        context.id,
                        context.context_type,
                        context.name,
                        context.description,
                        context.active,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_contexts(self, active_only: bool = True) -> list[UserContext]:
        """Get user contexts."""
        query = "SELECT * FROM user_context"
        params: list = []

        if active_only:
            query += " WHERE active = TRUE"

        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_context(row) for row in rows]

    def update_context_active(self, context_id: str, active: bool) -> None:
        """Update context active status."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_context
                SET active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (active, context_id),
            )
            conn.commit()

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        with self._connect() as conn:
            insights_count = conn.execute(
                "SELECT COUNT(*) FROM knowledge_insights"
            ).fetchone()[0]

            entities_count = conn.execute(
                "SELECT COUNT(*) FROM knowledge_entities"
            ).fetchone()[0]

            relationships_count = conn.execute(
                "SELECT COUNT(*) FROM knowledge_relationships"
            ).fetchone()[0]

            contradictions = conn.execute(
                """
                SELECT COUNT(*) FROM knowledge_relationships
                WHERE relationship_type = 'contradicts'
                """
            ).fetchone()[0]

            high_confidence = conn.execute(
                """
                SELECT COUNT(*) FROM knowledge_insights
                WHERE confidence = 'high'
                """
            ).fetchone()[0]

            return {
                "total_insights": insights_count,
                "total_entities": entities_count,
                "total_relationships": relationships_count,
                "contradictions": contradictions,
                "high_confidence_insights": high_confidence,
            }

    def _row_to_insight(self, row: sqlite3.Row) -> Insight:
        """Convert database row to Insight object."""
        return Insight(
            id=row["id"],
            article_id=row["article_id"],
            content=row["content"],
            insight_type=row["insight_type"],
            confidence=row["confidence"],
            confidence_reason=row["confidence_reason"],
            extracted_at=row["extracted_at"],
        )

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert database row to Entity object."""
        return Entity(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"],
            first_seen=row["first_seen"],
            mention_count=row["mention_count"],
        )

    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        """Convert database row to Relationship object."""
        return Relationship(
            id=row["id"],
            source_insight_id=row["source_insight_id"],
            target_insight_id=row["target_insight_id"],
            relationship_type=row["relationship_type"],
            strength=row["strength"],
            detected_at=row["detected_at"],
        )

    def _row_to_context(self, row: sqlite3.Row) -> UserContext:
        """Convert database row to UserContext object."""
        return UserContext(
            id=row["id"],
            context_type=row["context_type"],
            name=row["name"],
            description=row["description"],
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def extract_insights_from_article(
    article: Article, llm_provider, knowledge_base: KnowledgeBase
) -> list[Insight]:
    """
    Extract knowledge insights from an article using LLM.

    Args:
        article: Article to extract insights from
        llm_provider: LLM provider for extraction
        knowledge_base: Knowledge base to save insights to

    Returns:
        List of extracted insights
    """
    if not article.content or len(article.content) < 100:
        return []

    # Prepare extraction prompt
    prompt = f"""Extract key learnings from this article. Identify 3-5 specific insights.

For each insight, provide:
1. The insight text (one clear sentence)
2. Type: technical/tool/statistic/opinion
3. Confidence: high/medium/low
4. Reason for confidence level
5. Entities mentioned (tools, people, companies)

Article: "{article.title}"

Content (excerpt): {article.content[:2000]}

Return as JSON array:
[
  {{
    "content": "Insight text here",
    "type": "technical",
    "confidence": "high",
    "reason": "Cited peer-reviewed study",
    "entities": [{{"name": "Tool Name", "type": "tool"}}]
  }}
]

Only return valid JSON, no other text."""

    try:
        # Get LLM response
        response = llm_provider.summarize(prompt, max_length=1000)

        # Parse JSON response
        # Handle potential markdown code blocks
        response = response.strip()
        if response.startswith("```"):
            # Remove markdown code fences
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        insights_data = json.loads(response)

        # Create Insight objects
        insights = []
        for data in insights_data:
            insight_id = str(uuid.uuid4())
            insight = Insight(
                id=insight_id,
                article_id=article.id,
                content=data.get("content", ""),
                insight_type=data.get("type", "technical"),
                confidence=data.get("confidence", "medium"),
                confidence_reason=data.get("reason", ""),
            )

            # Save insight
            knowledge_base.save_insight(insight)
            insights.append(insight)

            # Process entities
            entities = data.get("entities", [])
            for entity_data in entities:
                entity_name = entity_data.get("name", "")
                entity_type = entity_data.get("type", "concept")

                if not entity_name:
                    continue

                # Check if entity exists
                existing = knowledge_base.get_entity_by_name(entity_name, entity_type)
                if existing:
                    entity_id = existing.id
                    # Increment mention count
                    knowledge_base.save_entity(existing)
                else:
                    # Create new entity
                    entity_id = str(uuid.uuid4())
                    entity = Entity(
                        id=entity_id,
                        name=entity_name,
                        entity_type=entity_type,
                    )
                    knowledge_base.save_entity(entity)

                # Link insight to entity
                knowledge_base.link_insight_to_entity(insight_id, entity_id)

        return insights

    except (json.JSONDecodeError, Exception) as e:
        # Fall back to simple extraction if LLM fails
        # Extract at least the article as a single insight
        insight = Insight(
            id=str(uuid.uuid4()),
            article_id=article.id,
            content=article.summary or article.title,
            insight_type="technical",
            confidence="low",
            confidence_reason=f"Automatic extraction failed: {str(e)}",
        )
        knowledge_base.save_insight(insight)
        return [insight]


def detect_connections(
    new_insight: Insight, knowledge_base: KnowledgeBase, llm_provider
) -> list[Relationship]:
    """
    Detect relationships between new insight and existing knowledge.

    Args:
        new_insight: Newly extracted insight
        knowledge_base: Knowledge base with existing insights
        llm_provider: LLM provider for relationship detection

    Returns:
        List of detected relationships
    """
    # Get recent insights to compare against (limit to avoid overwhelming LLM)
    existing_insights = knowledge_base.get_insights(limit=20)

    if not existing_insights:
        return []

    relationships = []

    # Simple keyword-based similarity for now
    # In production, would use embeddings for semantic similarity
    new_words = set(new_insight.content.lower().split())

    for existing in existing_insights:
        if existing.id == new_insight.id:
            continue

        # Calculate word overlap
        existing_words = set(existing.content.lower().split())
        overlap = len(new_words.intersection(existing_words))

        # If significant overlap, analyze relationship
        if overlap >= 3:
            # Use LLM to determine relationship type
            prompt = f"""Compare these two insights and determine their relationship.

Insight A: "{existing.content}"
Insight B: "{new_insight.content}"

Do they:
- Confirm each other (say similar things)?
- Contradict each other (say opposite things)?
- Refine (B adds nuance to A)?
- Extend (B builds on A)?
- None (unrelated)?

Return only one word: confirms/contradicts/refines/extends/none"""

            try:
                response = llm_provider.summarize(prompt, max_length=50).strip().lower()

                if response in ["confirms", "contradicts", "refines", "extends"]:
                    relationship = Relationship(
                        id=str(uuid.uuid4()),
                        source_insight_id=new_insight.id,
                        target_insight_id=existing.id,
                        relationship_type=response,
                        strength=min(overlap / 10.0, 1.0),
                    )
                    knowledge_base.save_relationship(relationship)
                    relationships.append(relationship)
            except Exception:
                # Skip relationship on error
                pass

    return relationships


def query_knowledge_base(
    query: str, knowledge_base: KnowledgeBase, llm_provider
) -> dict:
    """
    Query the knowledge base using natural language.

    Args:
        query: Natural language query
        knowledge_base: Knowledge base to query
        llm_provider: LLM provider for query processing

    Returns:
        Structured query results
    """
    # Get all insights (in production, would use semantic search)
    all_insights = knowledge_base.get_insights(limit=100)

    if not all_insights:
        return {
            "query": query,
            "results": [],
            "summary": "No insights found in knowledge base.",
        }

    # Use LLM to filter relevant insights
    insights_text = "\n\n".join(
        [
            f"[{i+1}] {insight.content} (Type: {insight.insight_type}, Confidence: {insight.confidence})"
            for i, insight in enumerate(all_insights[:50])
        ]
    )

    prompt = f"""Answer this question using only the insights below.

Question: {query}

Insights:
{insights_text}

Provide a clear answer summarizing what we know. Group by confidence level if relevant.
Mention which insights support your answer."""

    try:
        response = llm_provider.summarize(prompt, max_length=500)

        return {
            "query": query,
            "summary": response,
            "total_insights": len(all_insights),
        }
    except Exception as e:
        return {
            "query": query,
            "summary": f"Error processing query: {str(e)}",
            "total_insights": len(all_insights),
        }
