"""Knowledge extraction and accumulation system.

Extracts structured insights from articles, detects connections,
and provides a queryable knowledge base.
"""

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, TYPE_CHECKING

from .storage import Article
from .constitution import get_constitution_context

if TYPE_CHECKING:
    from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)


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
class Triple:
    """RDF-style triple: subject-predicate-object.

    Examples:
        - ("GPT-4", "developed_by", "OpenAI")
        - ("React 19", "introduces", "Server Components")
        - ("AI regulation", "discussed_in", "EU AI Act")
    """

    id: str
    subject: str
    predicate: str
    object: str
    subject_type: str  # 'entity', 'article', 'insight'
    object_type: str   # 'entity', 'article', 'insight', 'literal'
    source_article_id: Optional[str] = None
    confidence: str = "medium"  # 'high', 'medium', 'low'
    extracted_at: Optional[datetime] = None


@dataclass
class EntityRelationship:
    """Direct relationship between two entities.

    More expressive than insight-to-insight relationships.
    Captures things like "Company X acquired Company Y".
    """

    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # 'acquired', 'competes_with', 'partners_with', 'created', etc.
    properties: Optional[str] = None  # JSON string for additional properties
    source_article_id: Optional[str] = None
    detected_at: Optional[datetime] = None


@dataclass
class Embedding:
    """Vector embedding for semantic search.

    Stores embeddings for insights, entities, or articles
    to enable semantic similarity queries.
    """

    id: str
    target_id: str  # ID of insight, entity, or article
    target_type: str  # 'insight', 'entity', 'article'
    vector: bytes  # Serialized numpy array
    model: str  # Model used to generate embedding
    created_at: Optional[datetime] = None


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

            # RDF-style triples table (Option B enhancement)
            # UNIQUE constraint on (subject, predicate, object) prevents exact duplicates
            # Semantic duplicates ("USA" vs "United States") handled by cleanup operation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_triples (
                    id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    source_article_id TEXT,
                    confidence TEXT DEFAULT 'medium',
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_article_id) REFERENCES articles(id),
                    UNIQUE(subject, predicate, object)
                )
            """)

            # Entity-to-entity relationships
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entity_relationships (
                    id TEXT PRIMARY KEY,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    properties TEXT,
                    source_article_id TEXT,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_entity_id) REFERENCES knowledge_entities(id),
                    FOREIGN KEY (target_entity_id) REFERENCES knowledge_entities(id),
                    FOREIGN KEY (source_article_id) REFERENCES articles(id)
                )
            """)

            # Vector embeddings for semantic search
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                    id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    vector BLOB NOT NULL,
                    model TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            # Indexes for triples (graph queries)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_triples_subject ON knowledge_triples(subject)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_triples_predicate ON knowledge_triples(predicate)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_triples_object ON knowledge_triples(object)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_triples_subject_type ON knowledge_triples(subject_type)"
            )

            # Indexes for entity relationships
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entity_rel_source ON entity_relationships(source_entity_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entity_rel_target ON entity_relationships(target_entity_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_entity_rel_type ON entity_relationships(relationship_type)"
            )

            # Indexes for embeddings
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_target ON knowledge_embeddings(target_id, target_type)"
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
        limit: Optional[int] = None,
        insight_type: Optional[str] = None,
        confidence: Optional[str] = None,
        article_id: Optional[str] = None,
    ) -> list[Insight]:
        """Get insights with optional filtering.

        Args:
            limit: Maximum number of insights to return. None means no limit.
            insight_type: Filter by insight type.
            confidence: Filter by confidence level.
            article_id: Filter by source article.
        """
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

        query += " ORDER BY extracted_at DESC"
        if limit is not None:
            query += " LIMIT ?"
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
                    (id, source_insight_id, target_insight_id, relationship_type, strength, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relationship.id,
                        relationship.source_insight_id,
                        relationship.target_insight_id,
                        relationship.relationship_type,
                        relationship.strength,
                        relationship.detected_at.isoformat() if relationship.detected_at else datetime.now().isoformat(),
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
        since: Optional[datetime] = None,
    ) -> list[Relationship]:
        """Get relationships, optionally filtered by insight, type, or time.

        Args:
            insight_id: Filter by source or target insight
            relationship_type: Filter by relationship type
            since: Only return relationships detected after this time
        """
        query = "SELECT * FROM knowledge_relationships WHERE 1=1"
        params: list = []

        if insight_id:
            query += " AND (source_insight_id = ? OR target_insight_id = ?)"
            params.extend([insight_id, insight_id])

        if relationship_type:
            query += " AND relationship_type = ?"
            params.append(relationship_type)

        if since:
            query += " AND detected_at >= ?"
            params.append(since.isoformat())

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

    def _row_to_triple(self, row: sqlite3.Row) -> Triple:
        """Convert database row to Triple object."""
        return Triple(
            id=row["id"],
            subject=row["subject"],
            predicate=row["predicate"],
            object=row["object"],
            subject_type=row["subject_type"],
            object_type=row["object_type"],
            source_article_id=row["source_article_id"],
            confidence=row["confidence"],
            extracted_at=row["extracted_at"],
        )

    def _row_to_entity_relationship(self, row: sqlite3.Row) -> EntityRelationship:
        """Convert database row to EntityRelationship object."""
        return EntityRelationship(
            id=row["id"],
            source_entity_id=row["source_entity_id"],
            target_entity_id=row["target_entity_id"],
            relationship_type=row["relationship_type"],
            properties=row["properties"],
            source_article_id=row["source_article_id"],
            detected_at=row["detected_at"],
        )

    # =========================================================================
    # Triple (RDF-style) Methods - Option B Enhancement
    # =========================================================================

    def save_triple(self, triple: Triple) -> bool:
        """Save an RDF-style triple to the database."""
        # Validate triple - reject tautologies and circular reasoning
        subj_lower = triple.subject.lower().strip()
        obj_lower = triple.object.lower().strip()

        # Reject if subject == object
        if subj_lower == obj_lower:
            return False

        # Reject if one contains the other (circular)
        if subj_lower in obj_lower or obj_lower in subj_lower:
            # Allow if they're very different lengths (e.g., "AI" in "AI safety")
            if len(subj_lower) > 3 and len(obj_lower) > 3:
                if abs(len(subj_lower) - len(obj_lower)) < min(len(subj_lower), len(obj_lower)):
                    return False

        # Reject vague predicates that often produce garbage
        vague_predicates = {'is important to', 'is related to', 'is about', 'involves'}
        if triple.predicate.lower().strip() in vague_predicates:
            return False

        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO knowledge_triples
                    (id, subject, predicate, object, subject_type, object_type,
                     source_article_id, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        triple.id,
                        triple.subject,
                        triple.predicate,
                        triple.object,
                        triple.subject_type,
                        triple.object_type,
                        triple.source_article_id,
                        triple.confidence,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object_val: Optional[str] = None,
        limit: int = 100,
    ) -> list[Triple]:
        """Query triples with optional filters (SPARQL-like)."""
        query = "SELECT * FROM knowledge_triples WHERE 1=1"
        params: list = []

        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if predicate:
            query += " AND predicate = ?"
            params.append(predicate)
        if object_val:
            query += " AND object = ?"
            params.append(object_val)

        query += " ORDER BY extracted_at DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_triple(row) for row in rows]

    def query_triples_pattern(
        self, subject_pattern: Optional[str] = None, predicate_pattern: Optional[str] = None
    ) -> list[Triple]:
        """Query triples with LIKE patterns for graph exploration."""
        query = "SELECT * FROM knowledge_triples WHERE 1=1"
        params: list = []

        if subject_pattern:
            query += " AND subject LIKE ?"
            params.append(f"%{subject_pattern}%")
        if predicate_pattern:
            query += " AND predicate LIKE ?"
            params.append(f"%{predicate_pattern}%")

        query += " ORDER BY extracted_at DESC LIMIT 200"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_triple(row) for row in rows]

    def get_triples_by_article(self, article_id: str, limit: int = 10) -> list[Triple]:
        """Get triples extracted from a specific article.

        Returns facts that were actually extracted from this article,
        not random KB matches.
        """
        query = """
            SELECT * FROM knowledge_triples
            WHERE source_article_id = ?
            ORDER BY extracted_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, (article_id, limit)).fetchall()
            return [self._row_to_triple(row) for row in rows]

    # =========================================================================
    # Entity Relationship Methods - Option B Enhancement
    # =========================================================================

    def save_entity_relationship(self, relationship: EntityRelationship) -> bool:
        """Save an entity-to-entity relationship."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO entity_relationships
                    (id, source_entity_id, target_entity_id, relationship_type,
                     properties, source_article_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relationship.id,
                        relationship.source_entity_id,
                        relationship.target_entity_id,
                        relationship.relationship_type,
                        relationship.properties,
                        relationship.source_article_id,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_entity_relationships(
        self,
        entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
    ) -> list[EntityRelationship]:
        """Get entity relationships, optionally filtered."""
        query = "SELECT * FROM entity_relationships WHERE 1=1"
        params: list = []

        if entity_id:
            query += " AND (source_entity_id = ? OR target_entity_id = ?)"
            params.extend([entity_id, entity_id])
        if relationship_type:
            query += " AND relationship_type = ?"
            params.append(relationship_type)

        query += " ORDER BY detected_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_entity_relationship(row) for row in rows]

    # =========================================================================
    # Graph Traversal Methods - Option B Enhancement
    # =========================================================================

    def get_connected_entities(
        self, entity_name: str, max_depth: int = 2
    ) -> dict[str, list[dict]]:
        """
        Get all entities connected to the given entity within max_depth hops.

        Returns a dict with 'entities' and 'relationships' for graph visualization.
        """
        visited_entities: set[str] = set()
        all_relationships: list[dict] = []
        entities_to_process: list[tuple[str, int]] = [(entity_name, 0)]

        while entities_to_process:
            current_entity, depth = entities_to_process.pop(0)

            if current_entity in visited_entities or depth > max_depth:
                continue

            visited_entities.add(current_entity)

            # Find triples where this entity is subject or object
            with self._connect() as conn:
                # As subject
                rows = conn.execute(
                    "SELECT * FROM knowledge_triples WHERE subject = ?",
                    (current_entity,)
                ).fetchall()
                for row in rows:
                    rel = {
                        "source": row["subject"],
                        "target": row["object"],
                        "predicate": row["predicate"],
                        "confidence": row["confidence"],
                    }
                    all_relationships.append(rel)
                    if row["object"] not in visited_entities:
                        entities_to_process.append((row["object"], depth + 1))

                # As object
                rows = conn.execute(
                    "SELECT * FROM knowledge_triples WHERE object = ?",
                    (current_entity,)
                ).fetchall()
                for row in rows:
                    rel = {
                        "source": row["subject"],
                        "target": row["object"],
                        "predicate": row["predicate"],
                        "confidence": row["confidence"],
                    }
                    all_relationships.append(rel)
                    if row["subject"] not in visited_entities:
                        entities_to_process.append((row["subject"], depth + 1))

        return {
            "entities": list(visited_entities),
            "relationships": all_relationships,
        }

    def find_path(
        self, start_entity: str, end_entity: str, max_depth: int = 4
    ) -> Optional[list[dict]]:
        """
        Find a path between two entities in the knowledge graph.

        Returns list of relationship dicts forming the path, or None if no path found.
        """
        if start_entity == end_entity:
            return []

        # BFS to find shortest path
        visited: set[str] = {start_entity}
        queue: list[tuple[str, list[dict]]] = [(start_entity, [])]

        with self._connect() as conn:
            while queue:
                current, path = queue.pop(0)

                if len(path) >= max_depth:
                    continue

                # Get all connected entities via triples
                rows = conn.execute(
                    """
                    SELECT subject, predicate, object FROM knowledge_triples
                    WHERE subject = ? OR object = ?
                    """,
                    (current, current)
                ).fetchall()

                for row in rows:
                    next_entity = row["object"] if row["subject"] == current else row["subject"]
                    rel = {
                        "from": row["subject"],
                        "predicate": row["predicate"],
                        "to": row["object"],
                    }

                    if next_entity == end_entity:
                        return path + [rel]

                    if next_entity not in visited:
                        visited.add(next_entity)
                        queue.append((next_entity, path + [rel]))

        return None

    def get_entity_neighborhood(self, entity_name: str) -> dict:
        """
        Get immediate neighborhood of an entity (1-hop connections).

        Returns structured data for display or visualization.
        """
        with self._connect() as conn:
            # Outgoing relationships (entity is subject)
            outgoing = conn.execute(
                """
                SELECT predicate, object, object_type, COUNT(*) as count
                FROM knowledge_triples
                WHERE subject = ?
                GROUP BY predicate, object
                ORDER BY count DESC
                """,
                (entity_name,)
            ).fetchall()

            # Incoming relationships (entity is object)
            incoming = conn.execute(
                """
                SELECT subject, predicate, subject_type, COUNT(*) as count
                FROM knowledge_triples
                WHERE object = ?
                GROUP BY subject, predicate
                ORDER BY count DESC
                """,
                (entity_name,)
            ).fetchall()

            return {
                "entity": entity_name,
                "outgoing": [
                    {"predicate": r["predicate"], "target": r["object"], "count": r["count"]}
                    for r in outgoing
                ],
                "incoming": [
                    {"source": r["subject"], "predicate": r["predicate"], "count": r["count"]}
                    for r in incoming
                ],
            }

    # =========================================================================
    # Embedding Methods - Option B Enhancement (Optional, degrades gracefully)
    # =========================================================================

    def save_embedding(self, embedding: Embedding) -> bool:
        """Save a vector embedding."""
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_embeddings
                    (id, target_id, target_type, vector, model)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        embedding.id,
                        embedding.target_id,
                        embedding.target_type,
                        embedding.vector,
                        embedding.model,
                    ),
                )
                conn.commit()
                return True
            except sqlite3.Error:
                return False

    def get_embedding(self, target_id: str, target_type: str) -> Optional[Embedding]:
        """Get embedding for a target."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM knowledge_embeddings
                WHERE target_id = ? AND target_type = ?
                """,
                (target_id, target_type)
            ).fetchone()
            if row:
                return Embedding(
                    id=row["id"],
                    target_id=row["target_id"],
                    target_type=row["target_type"],
                    vector=row["vector"],
                    model=row["model"],
                    created_at=row["created_at"],
                )
            return None

    def has_embeddings(self) -> bool:
        """Check if any embeddings exist in the database."""
        with self._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM knowledge_embeddings"
            ).fetchone()[0]
            return count > 0

    def get_target_ids_with_embeddings(self, target_type: str) -> set[str]:
        """Get all target IDs that have embeddings of the specified type.

        Args:
            target_type: 'article', 'story', or 'insight'

        Returns:
            Set of target IDs that have embeddings
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT target_id FROM knowledge_embeddings WHERE target_type = ?",
                (target_type,)
            ).fetchall()
            return {row["target_id"] for row in rows}

    # =========================================================================
    # Enhanced Statistics - Option B Enhancement
    # =========================================================================

    def get_graph_stats(self) -> dict:
        """Get comprehensive knowledge graph statistics."""
        base_stats = self.get_stats()

        with self._connect() as conn:
            triples_count = conn.execute(
                "SELECT COUNT(*) FROM knowledge_triples"
            ).fetchone()[0]

            entity_rels_count = conn.execute(
                "SELECT COUNT(*) FROM entity_relationships"
            ).fetchone()[0]

            embeddings_count = conn.execute(
                "SELECT COUNT(*) FROM knowledge_embeddings"
            ).fetchone()[0]

            # Unique predicates (relationship types in graph)
            predicates = conn.execute(
                "SELECT DISTINCT predicate FROM knowledge_triples"
            ).fetchall()

            # Most connected entities
            top_entities = conn.execute(
                """
                SELECT subject as entity, COUNT(*) as connections
                FROM knowledge_triples
                GROUP BY subject
                ORDER BY connections DESC
                LIMIT 10
                """
            ).fetchall()

        return {
            **base_stats,
            "total_triples": triples_count,
            "total_entity_relationships": entity_rels_count,
            "total_embeddings": embeddings_count,
            "unique_predicates": len(predicates),
            "predicate_types": [p["predicate"] for p in predicates],
            "top_connected_entities": [
                {"entity": e["entity"], "connections": e["connections"]}
                for e in top_entities
            ],
        }


@dataclass
class ConsolidatedExtractionResult:
    """Result of consolidated extraction - insights and triples in one call."""
    insights: list[Insight]
    new_triples: list[Triple]
    existing_triples: list[Triple]


def extract_all_from_article(
    article: Article,
    llm_provider,
    knowledge_base: KnowledgeBase,
) -> ConsolidatedExtractionResult:
    """
    Extract insights AND triples from article in a SINGLE LLM call.

    This consolidates what was previously 3+ separate calls:
    - extract_insights_from_article (1 call)
    - _semantic_chunk (1 call)
    - extract_triples_with_comparison (N calls per chunk)

    Into 1 call that returns both insights and triples.

    Args:
        article: Article to extract from
        llm_provider: LLM provider for extraction
        knowledge_base: Knowledge base to save to

    Returns:
        ConsolidatedExtractionResult with insights and triples
    """
    result = ConsolidatedExtractionResult(
        insights=[],
        new_triples=[],
        existing_triples=[],
    )

    if not article.content or len(article.content) < 100:
        return result

    # Get user's analysis principles if configured
    constitution_context = get_constitution_context()

    # Single consolidated prompt
    prompt = f"""{constitution_context}
=== ARTICLE TO ANALYZE ===
Extract insights and factual relationships from ONLY the article content below.

Article: "{article.title}"

Content: {article.content}

=== EXTRACTION INSTRUCTIONS ===

1. INSIGHTS: Extract key learnings. For each:
   - content: one clear sentence
   - type: technical/tool/statistic/opinion
   - confidence: high/medium/low
   - reason: why this confidence level

2. TRIPLES: Extract factual subject-predicate-object relationships.
   - Subjects/objects must be PROPER NOUNS (specific names, companies, places)
   - NEVER use generic nouns like 'man', 'woman', 'article'
   - Common predicates: developed_by, acquired, partnered_with, announced, competes_with, located_in, costs, uses

Return as JSON:
{{
  "insights": [
    {{"content": "...", "type": "technical", "confidence": "high", "reason": "..."}}
  ],
  "triples": [
    {{"subject": "Entity", "predicate": "relationship", "object": "Entity", "confidence": "high"}}
  ]
}}

Only return valid JSON, no other text."""

    try:
        response = llm_provider.summarize(prompt, max_length=2000)

        # Parse JSON
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        # Find JSON object
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]

        data = json.loads(response)

        # Process insights
        for insight_data in data.get("insights", []):
            insight_id = str(uuid.uuid4())
            insight = Insight(
                id=insight_id,
                article_id=article.id,
                content=insight_data.get("content", ""),
                insight_type=insight_data.get("type", "technical"),
                confidence=insight_data.get("confidence", "medium"),
                confidence_reason=insight_data.get("reason", ""),
            )
            knowledge_base.save_insight(insight)
            result.insights.append(insight)

        # Process triples
        for triple_data in data.get("triples", []):
            if not isinstance(triple_data, dict):
                continue

            subject = triple_data.get("subject", "")
            predicate = triple_data.get("predicate", "")
            obj = triple_data.get("object", "")

            if not (subject and predicate and obj):
                continue

            triple = Triple(
                id=str(uuid.uuid4()),
                subject=subject,
                predicate=predicate,
                object=obj,
                subject_type="entity",
                object_type="entity",
                source_article_id=article.id,
                confidence=triple_data.get("confidence", "medium"),
            )

            # Check for existing
            existing = knowledge_base.get_triples(
                subject=triple.subject,
                predicate=triple.predicate,
                object_val=triple.object,
                limit=1
            )

            if existing:
                result.existing_triples.append(existing[0])
            else:
                if knowledge_base.save_triple(triple):
                    result.new_triples.append(triple)

        return result

    except json.JSONDecodeError as e:
        import sys
        print(f"JSON parsing failed for consolidated extraction: {e}", file=sys.stderr)
        # Fallback: create minimal insight
        insight = Insight(
            id=str(uuid.uuid4()),
            article_id=article.id,
            content=article.summary or article.title,
            insight_type="technical",
            confidence="low",
            confidence_reason=f"JSON parsing failed: {str(e)}",
        )
        knowledge_base.save_insight(insight)
        result.insights.append(insight)
        return result
    except Exception as e:
        import sys
        print(f"Consolidated extraction failed: {e}", file=sys.stderr)
        return result


def extract_insights_from_article(
    article: Article, llm_provider, knowledge_base: KnowledgeBase
) -> list[Insight]:
    """
    Extract knowledge insights from an article using LLM.

    DEPRECATED: Use extract_all_from_article for consolidated extraction.

    Args:
        article: Article to extract insights from
        llm_provider: LLM provider for extraction
        knowledge_base: Knowledge base to save insights to

    Returns:
        List of extracted insights
    """
    if not article.content or len(article.content) < 100:
        return []

    # Get user's analysis principles if configured
    constitution_context = get_constitution_context()

    # Prepare extraction prompt
    # CRITICAL: Constitution is for HOW to analyze, not WHAT to extract
    prompt = f"""{constitution_context}
=== ARTICLE TO ANALYZE ===
Extract insights from ONLY the article content below. Do NOT include the analysis principles above as insights - they are instructions for HOW to analyze, not content to extract.

Extract ALL key learnings from this article. The number of insights depends on content density.

For each insight, provide:
1. The insight text (one clear sentence)
2. Type: technical/tool/statistic/opinion
3. Confidence: high/medium/low
4. Reason for confidence level
5. Entities mentioned (tools, people, companies)

Article: "{article.title}"

Content: {article.content}

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

    except json.JSONDecodeError as e:
        import sys
        print(f"JSON parsing failed for insights from '{article.title[:40]}': {e}", file=sys.stderr)
        insight = Insight(
            id=str(uuid.uuid4()),
            article_id=article.id,
            content=article.summary or article.title,
            insight_type="technical",
            confidence="low",
            confidence_reason=f"JSON parsing failed: {str(e)}",
        )
        knowledge_base.save_insight(insight)
        return [insight]
    except Exception as e:
        # Other errors - log and use fallback
        import sys
        print(f"Warning: Insight extraction failed for '{article.title[:40]}': {e}", file=sys.stderr)
        insight = Insight(
            id=str(uuid.uuid4()),
            article_id=article.id,
            content=article.summary or article.title,
            insight_type="technical",
            confidence="low",
            confidence_reason=f"Extraction error: {str(e)}",
        )
        knowledge_base.save_insight(insight)
        return [insight]


# =============================================================================
# BATCH HELPERS: Separate prompt building from response parsing for batching
# =============================================================================

def build_insight_prompt(article: Article) -> Optional[str]:
    """Build the prompt for insight extraction. Returns None if article not suitable."""
    if not article.content or len(article.content) < 100:
        return None

    constitution_context = get_constitution_context()

    return f"""{constitution_context}
=== ARTICLE TO ANALYZE ===
Extract insights from ONLY the article content below. Do NOT include the analysis principles above as insights - they are instructions for HOW to analyze, not content to extract.

Extract ALL key learnings from this article. The number of insights depends on content density.

For each insight, provide:
1. The insight text (one clear sentence)
2. Type: technical/tool/statistic/opinion
3. Confidence: high/medium/low
4. Reason for confidence level
5. Entities mentioned (tools, people, companies)

Article: "{article.title}"

Content: {article.content}

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


def parse_insight_response(
    article: Article, response: str, knowledge_base: "KnowledgeBase"
) -> list[Insight]:
    """Parse LLM response and save insights to knowledge base."""
    try:
        # Handle potential markdown code blocks
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        insights_data = json.loads(response)

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

            knowledge_base.save_insight(insight)
            insights.append(insight)

            # Process entities
            entities = data.get("entities", [])
            for entity_data in entities:
                entity_name = entity_data.get("name", "")
                entity_type = entity_data.get("type", "concept")

                if not entity_name:
                    continue

                existing = knowledge_base.get_entity_by_name(entity_name, entity_type)
                if existing:
                    entity_id = existing.id
                    knowledge_base.save_entity(existing)
                else:
                    entity_id = str(uuid.uuid4())
                    entity = Entity(
                        id=entity_id,
                        name=entity_name,
                        entity_type=entity_type,
                    )
                    knowledge_base.save_entity(entity)

                knowledge_base.link_insight_to_entity(insight_id, entity_id)

        return insights

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed for insights from '{article.title[:40]}': {e}")
        insight = Insight(
            id=str(uuid.uuid4()),
            article_id=article.id,
            content=article.summary or article.title,
            insight_type="technical",
            confidence="low",
            confidence_reason=f"JSON parsing failed: {str(e)}",
        )
        knowledge_base.save_insight(insight)
        return [insight]
    except Exception as e:
        logger.warning(f"Insight parsing failed for '{article.title[:40]}': {e}")
        insight = Insight(
            id=str(uuid.uuid4()),
            article_id=article.id,
            content=article.summary or article.title,
            insight_type="technical",
            confidence="low",
            confidence_reason=f"Parsing error: {str(e)}",
        )
        knowledge_base.save_insight(insight)
        return [insight]


@dataclass
class TripleExtractionResult:
    """Result of triple extraction with visibility into new vs existing."""
    new_triples: list[Triple]
    existing_triples: list[Triple]  # Already in KB
    updated_triples: list[Triple]   # Updated existing with new source

    @property
    def total_extracted(self) -> int:
        return len(self.new_triples) + len(self.existing_triples) + len(self.updated_triples)

    @property
    def actually_new(self) -> int:
        return len(self.new_triples)


def _correct_inverted_predicate(subject: str, predicate: str, obj: str) -> tuple[str, str, str]:
    """Correct inverted "_by" predicates.

    Problem: LLM sometimes generates "Elon Musk -> founded_by -> X" when it should be
    "X -> founded_by -> Elon Musk" (meaning X was founded by Elon Musk).

    Solution: For "_by" predicates where subject looks like a person (capitalized name),
    swap subject/object to correct the direction.

    Args:
        subject: Triple subject
        predicate: Triple predicate
        obj: Triple object

    Returns:
        Tuple of (corrected_subject, corrected_predicate, corrected_object)
    """
    # Predicates that imply the subject is the recipient of an action by the object
    passive_predicates = {
        "founded_by", "created_by", "developed_by", "invented_by",
        "acquired_by", "owned_by", "led_by", "managed_by", "directed_by",
        "written_by", "designed_by", "built_by", "made_by"
    }

    predicate_lower = predicate.lower().replace(" ", "_")

    if predicate_lower in passive_predicates:
        # Role terms that indicate a person/people acting on something
        role_terms = {
            "co-founders", "co-founder", "founders", "founder",
            "ceo", "cto", "cfo", "coo", "executives", "executive",
            "researchers", "researcher", "scientists", "scientist",
            "directors", "director", "engineers", "engineer"
        }

        # Check if subject is a role term (should be swapped)
        if subject.lower() in role_terms:
            return obj, predicate, subject

        # Check if subject looks like a person (capitalized words, no obvious company markers)
        subject_words = subject.split()
        looks_like_person = (
            len(subject_words) <= 4 and  # Names usually 1-4 words
            all(w[0].isupper() for w in subject_words if w) and  # All words capitalized
            not any(marker in subject.lower() for marker in ["inc", "corp", "ltd", "llc", "co.", "company"])
        )

        # Check if object looks like a company/product (often contains lowercase or markers)
        looks_like_company = any(
            marker in obj.lower()
            for marker in ["inc", "corp", "ltd", "llc", "co.", "company", "technologies", "systems"]
        ) or (obj[0].isupper() and len(obj.split()) == 1)  # Single capitalized word often a product/company

        # If subject looks like person acting on a company, swap them
        if looks_like_person and (looks_like_company or not subject_words):
            return obj, predicate, subject

    return subject, predicate, obj


def _semantic_chunk(text: str, llm_provider, article_title: str = "") -> list[str]:
    """
    Split text into semantically meaningful chunks using LLM.

    Purpose: These chunks will be embedded for similarity matching and knowledge
    extraction. The LLM identifies natural semantic boundaries in the content.

    Args:
        text: Full article content to chunk
        llm_provider: LLM provider for semantic analysis
        article_title: Article title for context

    Returns:
        List of semantically coherent chunks
    """
    if not text or len(text) < 200:
        return [text] if text else []

    prompt = f"""Divide this article into semantically coherent chunks for embedding and knowledge extraction.

Article: "{article_title}"

Content:
{text}

Instructions:
- Identify natural semantic boundaries (topic shifts, section breaks, conceptual units)
- Each chunk should be a complete, coherent unit of meaning
- Preserve all content - do not summarize or omit anything
- Return the actual text chunks, not descriptions of them

Return as JSON array of strings, where each string is a complete chunk:
["chunk 1 full text here...", "chunk 2 full text here...", ...]

Only return the JSON array, no other text."""

    try:
        response = llm_provider.generate(prompt, max_tokens=4000)
        response = response.strip()

        # Find JSON array in response
        start_idx = response.find('[')
        end_idx = response.rfind(']') + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            chunks = json.loads(json_str)
            if isinstance(chunks, list) and all(isinstance(c, str) for c in chunks):
                # Filter out empty chunks
                chunks = [c.strip() for c in chunks if c.strip()]
                if chunks:
                    return chunks
    except json.JSONDecodeError:
        # Silently fall back - expected for some LLM outputs
        pass
    except Exception:
        # Silently fall back
        pass

    # Fallback: return full text as single chunk (never truncate)
    return [text]


def _find_similar_triple(
    triple: Triple,
    knowledge_base: KnowledgeBase,
    embedding_service: Optional["EmbeddingService"] = None,
    similarity_threshold: float = 0.75,
) -> Optional[Triple]:
    """Check if a matching triple already exists (case-insensitive).

    Checks for both exact matches and case-insensitive matches to prevent
    duplicates like "McConaughey trademarked" vs "MCCONAUGHEY trademarked".

    Args:
        triple: Triple to check for duplicates
        knowledge_base: Knowledge base to search
        embedding_service: UNUSED - kept for API compatibility
        similarity_threshold: UNUSED - kept for API compatibility

    Returns:
        Matching triple if found, None otherwise
    """
    # First try exact match (fast, uses index)
    existing = knowledge_base.get_triples(
        subject=triple.subject,
        predicate=triple.predicate,
        object_val=triple.object,
        limit=1
    )
    if existing:
        return existing[0]

    # Try case-insensitive match via pattern query
    # This catches "McConaughey" vs "MCCONAUGHEY" duplicates
    similar = knowledge_base.query_triples_pattern(
        subject_pattern=triple.subject,
        predicate_pattern=triple.predicate,
    )
    for t in similar:
        if t.object.lower() == triple.object.lower():
            return t

    return None


def extract_triples_from_article(
    article: Article,
    llm_provider,
    knowledge_base: KnowledgeBase,
    embedding_service: Optional["EmbeddingService"] = None,
) -> list[Triple]:
    """
    Extract RDF-style triples from an article using LLM.

    Chunks the article and extracts triples from each chunk for thorough coverage.
    Compares against existing knowledge to identify new vs redundant.

    Args:
        article: Article to extract triples from
        llm_provider: LLM provider for extraction
        knowledge_base: Knowledge base to save triples to
        embedding_service: Optional EmbeddingService for semantic deduplication

    Returns:
        List of NEW triples (already saved to KB)
    """
    result = extract_triples_with_comparison(
        article, llm_provider, knowledge_base, embedding_service
    )
    return result.new_triples


def extract_triples_with_comparison(
    article: Article,
    llm_provider,
    knowledge_base: KnowledgeBase,
    embedding_service: Optional["EmbeddingService"] = None,
) -> TripleExtractionResult:
    """
    Extract triples with full visibility into what's new vs existing.

    This is the detailed version that shows:
    - new_triples: Actually new facts added to KB
    - existing_triples: Already known, not added
    - updated_triples: Existing triple updated with new source article

    Args:
        article: Article to extract triples from
        llm_provider: LLM provider for extraction
        knowledge_base: Knowledge base to save triples to

    Returns:
        TripleExtractionResult with categorized triples
    """
    result = TripleExtractionResult(
        new_triples=[],
        existing_triples=[],
        updated_triples=[]
    )

    if not article.content or len(article.content) < 100:
        return result

    # Chunk the article semantically for thorough extraction
    chunks = _semantic_chunk(article.content, llm_provider, article.title)

    for chunk_idx, chunk in enumerate(chunks):
        prompt = f"""Extract factual relationships from this text as subject-predicate-object triples.

Article: "{article.title}"
Section {chunk_idx + 1}/{len(chunks)}:

{chunk}

Extract ALL factual relationships from this section. Be thorough - the number of triples depends entirely on the content density.

IMPORTANT: Subjects and objects must be PROPER NOUNS - specific named people (e.g., "John Smith"), companies (e.g., "Google"), places (e.g., "Paris"), organizations (e.g., "UN").
NEVER use generic nouns like 'woman', 'man', 'father', 'pigs', 'speech', 'article', 'analysis'. If you can't identify a specific name, skip the triple entirely.

Common predicates:
- developed_by, created_by, founded_by (attribution)
- acquired, merged_with, partnered_with (corporate)
- announced, released, launched (events)
- competes_with, integrates_with, replaces (relationships)
- located_in, works_at, leads (associations)
- costs, valued_at, raised (financial)
- uses, requires, supports (technical)
- is_a, part_of, belongs_to (taxonomy)
- affects, causes, enables (causation)

Return as JSON array:
[
  {{"subject": "Entity", "predicate": "relationship", "object": "Entity/Value", "subject_type": "entity", "object_type": "entity", "confidence": "high"}}
]

Types: entity (company/person/product/technology), literal (facts/values/descriptions)

Only return valid JSON array, no other text."""

        try:
            response = llm_provider.summarize(prompt, max_length=1500)

            # Clean response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

            # Find JSON array
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                response = response[start:end]

            triples_data = json.loads(response)

            for data in triples_data:
                if not isinstance(data, dict):
                    continue

                # Extract and correct inverted predicates
                raw_subject = data.get("subject", "")
                raw_predicate = data.get("predicate", "")
                raw_object = data.get("object", "")

                corrected_subject, corrected_predicate, corrected_object = _correct_inverted_predicate(
                    raw_subject, raw_predicate, raw_object
                )

                triple = Triple(
                    id=str(uuid.uuid4()),
                    subject=corrected_subject,
                    predicate=corrected_predicate,
                    object=corrected_object,
                    subject_type=data.get("subject_type", "entity"),
                    object_type=data.get("object_type", "entity"),
                    source_article_id=article.id,
                    confidence=data.get("confidence", "medium"),
                )

                if not (triple.subject and triple.predicate and triple.object):
                    continue

                # Check for existing similar triple (using embeddings if available)
                existing = _find_similar_triple(
                    triple, knowledge_base, embedding_service=embedding_service
                )

                if existing:
                    # Already have this fact
                    result.existing_triples.append(existing)
                else:
                    # New fact - save it
                    if knowledge_base.save_triple(triple):
                        result.new_triples.append(triple)

        except json.JSONDecodeError as e:
            import sys
            print(f"JSON parsing failed for triple extraction: {e}", file=sys.stderr)
            continue
        except Exception as e:
            import sys
            print(f"Error extracting triples from chunk: {e}", file=sys.stderr)
            continue

    return result


def extract_entity_relationships_from_article(
    article: Article, llm_provider, knowledge_base: KnowledgeBase
) -> list[EntityRelationship]:
    """
    Extract entity-to-entity relationships from an article.

    These are higher-level relationships between known entities,
    like "Microsoft acquired Activision" or "Google competes with OpenAI".

    Args:
        article: Article to extract relationships from
        llm_provider: LLM provider for extraction
        knowledge_base: Knowledge base to save relationships to

    Returns:
        List of extracted entity relationships
    """
    if not article.content or len(article.content) < 100:
        return []

    prompt = f"""Identify ALL relationships between organizations, people, and products in this article. Extract every significant relationship present.

Article: "{article.title}"

Content: {article.content}

Find all significant relationships between named entities. Focus on:
- Business relationships (acquired, partnered, competes_with)
- People relationships (founded, leads, joined, left)
- Product relationships (created, maintains, deprecated)

Return as JSON array:
[
  {{
    "source": "Microsoft",
    "target": "OpenAI",
    "relationship": "invested_in",
    "properties": {{"amount": "$10 billion", "year": "2023"}}
  }}
]

Only return valid JSON, no other text."""

    try:
        response = llm_provider.summarize(prompt, max_length=800)

        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        rels_data = json.loads(response)

        relationships = []
        for data in rels_data:
            source_name = data.get("source", "")
            target_name = data.get("target", "")

            if not source_name or not target_name:
                continue

            # Get or create entities
            source_entity = knowledge_base.get_entity_by_name(source_name, "company")
            if not source_entity:
                source_entity = Entity(
                    id=str(uuid.uuid4()),
                    name=source_name,
                    entity_type="company",
                )
                knowledge_base.save_entity(source_entity)

            target_entity = knowledge_base.get_entity_by_name(target_name, "company")
            if not target_entity:
                target_entity = Entity(
                    id=str(uuid.uuid4()),
                    name=target_name,
                    entity_type="company",
                )
                knowledge_base.save_entity(target_entity)

            # Create relationship
            properties = data.get("properties")
            rel = EntityRelationship(
                id=str(uuid.uuid4()),
                source_entity_id=source_entity.id,
                target_entity_id=target_entity.id,
                relationship_type=data.get("relationship", "related_to"),
                properties=json.dumps(properties) if properties else None,
                source_article_id=article.id,
            )
            knowledge_base.save_entity_relationship(rel)
            relationships.append(rel)

        return relationships

    except json.JSONDecodeError as e:
        import sys
        print(f"JSON parsing failed for entity relationships from '{article.title[:40]}': {e}", file=sys.stderr)
        return []
    except Exception as e:
        import sys
        print(f"Error extracting entity relationships from '{article.title[:40]}': {e}", file=sys.stderr)
        return []


def build_chunk_prompt(article: Article) -> Optional[str]:
    """Build the prompt for semantic chunking. Returns None if article not suitable."""
    if not article.content or len(article.content) < 200:
        return None

    return f"""Divide this article into semantically coherent chunks for embedding and knowledge extraction.

Article: "{article.title}"

Content:
{article.content}

Instructions:
- Identify natural semantic boundaries (topic shifts, section breaks, conceptual units)
- Each chunk should be a complete, coherent unit of meaning
- Preserve all content - do not summarize or omit anything
- Return the actual text chunks, not descriptions of them

Return as JSON array of strings, where each string is a complete chunk:
["chunk 1 full text here...", "chunk 2 full text here...", ...]

Only return the JSON array, no other text."""


def parse_chunk_response(article: Article, response: str) -> list[str]:
    """Parse LLM response to get chunks. Returns [full_content] as fallback."""
    try:
        response = response.strip()
        start_idx = response.find('[')
        end_idx = response.rfind(']') + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response[start_idx:end_idx]
            chunks = json.loads(json_str)
            if isinstance(chunks, list) and all(isinstance(c, str) for c in chunks):
                chunks = [c.strip() for c in chunks if c.strip()]
                if chunks:
                    return chunks
    except (json.JSONDecodeError, Exception):
        pass
    # Fallback: return full content as single chunk
    return [article.content] if article.content else []


def get_connection_candidates(
    insight: Insight,
    knowledge_base: "KnowledgeBase",
    embedding_service: "EmbeddingService",
    similarity_threshold: float = 0.70,
    max_comparisons: int = 50,
) -> list[tuple[Insight, float]]:
    """
    Get candidate insights for connection detection (FAISS lookup, no LLM).

    Returns list of (existing_insight, similarity) tuples.
    """
    from .embeddings import EmbeddingError

    # Get or create embedding for insight
    try:
        embedding = embedding_service.get_embedding(insight.id, "insight")
        if not embedding:
            result = embedding_service.embed_text(insight.content)
            embedding = result.vector
            embedding_service.save_embedding(insight.id, "insight", result)
    except EmbeddingError:
        return []

    # Use FAISS to find similar insights
    similar_results = embedding_service.find_similar(
        query_vector=embedding,
        target_type="insight",
        threshold=similarity_threshold,
        limit=max_comparisons,
    )

    if not similar_results:
        return []

    # Filter out self-match and get insight objects
    candidates = []
    for target_id, similarity in similar_results:
        if target_id == insight.id:
            continue
        existing = knowledge_base.get_insight(target_id)
        if existing:
            candidates.append((existing, similarity))

    return candidates[:10]  # Limit to top 10


def build_connection_prompt(insight: Insight, candidates: list[tuple[Insight, float]]) -> Optional[str]:
    """Build prompt for connection classification. Returns None if no candidates."""
    if not candidates:
        return None

    pairs_text = ""
    for i, (existing, similarity) in enumerate(candidates):
        pairs_text += f"\nPair {i+1} (similarity: {similarity:.2f}):\n"
        pairs_text += f'- Existing: "{existing.content}"\n'
        pairs_text += f'- New: "{insight.content}"\n'

    return f"""Classify the relationships between these insight pairs.
{pairs_text}
For each pair, determine the relationship from the NEW insight to the EXISTING insight:
- confirms: New says essentially the same thing as existing
- contradicts: New says the opposite of existing
- refines: New adds nuance or detail to existing
- extends: New builds on existing with new information
- none: They are about similar topics but unrelated

Return a JSON array with the relationship for each pair in order:
["confirms", "none", "extends", ...]

Return ONLY the JSON array, no other text."""


def parse_connection_response(
    insight: Insight,
    candidates: list[tuple[Insight, float]],
    response: str,
    knowledge_base: "KnowledgeBase",
) -> list["Relationship"]:
    """Parse LLM response and save relationships to knowledge base."""
    try:
        from .schema import extract_json_from_response
        json_str = extract_json_from_response(response)
        relationship_types = json.loads(json_str)

        if not isinstance(relationship_types, list):
            relationship_types = [relationship_types]

        relationships = []
        valid_types = {"confirms", "contradicts", "refines", "extends"}

        for i, (existing, similarity) in enumerate(candidates):
            if i >= len(relationship_types):
                break

            rel_type = str(relationship_types[i]).lower().strip()
            if rel_type not in valid_types:
                continue

            relationship = Relationship(
                id=str(uuid.uuid4()),
                source_insight_id=insight.id,
                target_insight_id=existing.id,
                relationship_type=rel_type,
                strength=similarity,
                detected_at=datetime.now(),
            )
            knowledge_base.save_relationship(relationship)
            relationships.append(relationship)

        return relationships

    except Exception as e:
        logger.warning(f"Failed to parse connection response: {e}")
        return []


def build_triple_prompt(article_title: str, chunk_idx: int, total_chunks: int, chunk: str) -> str:
    """Build the prompt for triple extraction from one chunk."""
    return f"""Extract factual relationships from this text as subject-predicate-object triples.

Article: "{article_title}"
Section {chunk_idx + 1}/{total_chunks}:

{chunk}

Extract ALL factual relationships from this section. Be thorough - the number of triples depends entirely on the content density.

IMPORTANT: Subjects and objects must be PROPER NOUNS - specific named people (e.g., "John Smith"), companies (e.g., "Google"), places (e.g., "Paris"), organizations (e.g., "UN").
NEVER use generic nouns like 'woman', 'man', 'father', 'pigs', 'speech', 'article', 'analysis'. If you can't identify a specific name, skip the triple entirely.

Common predicates:
- developed_by, created_by, founded_by (attribution)
- acquired, merged_with, partnered_with (corporate)
- announced, released, launched (events)
- competes_with, integrates_with, replaces (relationships)
- located_in, works_at, leads (associations)
- costs, valued_at, raised (financial)
- uses, requires, supports (technical)
- is_a, part_of, belongs_to (taxonomy)
- affects, causes, enables (causation)

Return as JSON array:
[
  {{"subject": "Entity", "predicate": "relationship", "object": "Entity/Value", "subject_type": "entity", "object_type": "entity", "confidence": "high"}}
]

Types: entity (company/person/product/technology), literal (facts/values/descriptions)

Only return valid JSON array, no other text."""


def parse_triple_response(
    article: Article,
    response: str,
    knowledge_base: "KnowledgeBase",
    embedding_service: Optional["EmbeddingService"] = None,
) -> tuple[list[Triple], list[Triple]]:
    """
    Parse LLM response and save triples to knowledge base.

    Returns:
        Tuple of (new_triples, existing_triples)
    """
    new_triples = []
    existing_triples = []

    try:
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        # Find JSON array
        start = response.find("[")
        end = response.rfind("]") + 1
        if start >= 0 and end > start:
            response = response[start:end]

        triples_data = json.loads(response)

        for data in triples_data:
            if not isinstance(data, dict):
                continue

            raw_subject = data.get("subject", "")
            raw_predicate = data.get("predicate", "")
            raw_object = data.get("object", "")

            corrected_subject, corrected_predicate, corrected_object = _correct_inverted_predicate(
                raw_subject, raw_predicate, raw_object
            )

            triple = Triple(
                id=str(uuid.uuid4()),
                subject=corrected_subject,
                predicate=corrected_predicate,
                object=corrected_object,
                subject_type=data.get("subject_type", "entity"),
                object_type=data.get("object_type", "entity"),
                source_article_id=article.id,
                confidence=data.get("confidence", "medium"),
            )

            if not (triple.subject and triple.predicate and triple.object):
                continue

            existing = _find_similar_triple(
                triple, knowledge_base, embedding_service=embedding_service
            )

            if existing:
                existing_triples.append(existing)
            else:
                if knowledge_base.save_triple(triple):
                    new_triples.append(triple)

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed for triple extraction: {e}")
    except Exception as e:
        logger.warning(f"Triple parsing failed: {e}")

    return new_triples, existing_triples


def build_entity_rel_prompt(article: Article) -> Optional[str]:
    """Build the prompt for entity relationship extraction. Returns None if article not suitable."""
    if not article.content or len(article.content) < 100:
        return None

    return f"""Identify ALL relationships between organizations, people, and products in this article. Extract every significant relationship present.

Article: "{article.title}"

Content: {article.content}

Find all significant relationships between named entities. Focus on:
- Business relationships (acquired, partnered, competes_with)
- People relationships (founded, leads, joined, left)
- Product relationships (created, maintains, deprecated)

Return as JSON array:
[
  {{
    "source": "Microsoft",
    "target": "OpenAI",
    "relationship": "invested_in",
    "properties": {{"amount": "$10 billion", "year": "2023"}}
  }}
]

Only return valid JSON, no other text."""


def parse_entity_rel_response(
    article: Article, response: str, knowledge_base: "KnowledgeBase"
) -> list[EntityRelationship]:
    """Parse LLM response and save entity relationships to knowledge base."""
    try:
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if len(lines) > 2 else lines)

        rels_data = json.loads(response)

        relationships = []
        for data in rels_data:
            source_name = data.get("source", "")
            target_name = data.get("target", "")

            if not source_name or not target_name:
                continue

            # Get or create entities
            source_entity = knowledge_base.get_entity_by_name(source_name, "company")
            if not source_entity:
                source_entity = Entity(
                    id=str(uuid.uuid4()),
                    name=source_name,
                    entity_type="company",
                )
                knowledge_base.save_entity(source_entity)

            target_entity = knowledge_base.get_entity_by_name(target_name, "company")
            if not target_entity:
                target_entity = Entity(
                    id=str(uuid.uuid4()),
                    name=target_name,
                    entity_type="company",
                )
                knowledge_base.save_entity(target_entity)

            # Create relationship
            properties = data.get("properties")
            rel = EntityRelationship(
                id=str(uuid.uuid4()),
                source_entity_id=source_entity.id,
                target_entity_id=target_entity.id,
                relationship_type=data.get("relationship", "related_to"),
                properties=json.dumps(properties) if properties else None,
                source_article_id=article.id,
            )
            knowledge_base.save_entity_relationship(rel)
            relationships.append(rel)

        return relationships

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed for entity relationships from '{article.title[:40]}': {e}")
        return []
    except Exception as e:
        logger.warning(f"Entity relationship parsing failed for '{article.title[:40]}': {e}")
        return []


def detect_connections(
    new_insight: Insight,
    knowledge_base: KnowledgeBase,
    llm_provider,
    similarity_threshold: float = 0.70,
    max_comparisons: int = 50,
    embedding_service: Optional["EmbeddingService"] = None,
) -> list[Relationship]:
    """
    Detect relationships between a new insight and existing knowledge.

    OPTIMIZED (Issue 4): Uses FAISS for O(log N) candidate finding instead of
    O(N) brute force, then ONE batched LLM call to classify all relationships
    instead of N separate calls.

    Args:
        new_insight: Newly extracted insight to find connections for
        knowledge_base: Knowledge base with existing insights
        llm_provider: LLM provider for relationship classification
        similarity_threshold: Minimum cosine similarity to consider (0.0-1.0)
        max_comparisons: Maximum candidates to consider (used as FAISS k)
        embedding_service: Optional EmbeddingService (for testing injection).
                          If not provided, one will be created.

    Returns:
        List of detected relationships with human-readable types
    """
    import sys
    from .embeddings import EmbeddingService, EmbeddingError

    # Initialize embedding service if not provided
    if embedding_service is None:
        try:
            embedding_service = EmbeddingService(knowledge_base)
            if not embedding_service.is_available():
                print("Warning: No embedding provider available for connection detection", file=sys.stderr)
                return []
        except Exception as e:
            print(f"Warning: Could not initialize embedding service: {e}", file=sys.stderr)
            return []
    else:
        if not embedding_service.is_available():
            return []

    # Get or create embedding for new insight
    try:
        new_embedding = embedding_service.get_embedding(new_insight.id, "insight")
        if not new_embedding:
            result = embedding_service.embed_text(new_insight.content)
            new_embedding = result.vector
            embedding_service.save_embedding(new_insight.id, "insight", result)
    except EmbeddingError as e:
        print(f"Warning: Could not embed new insight: {e}", file=sys.stderr)
        return []

    # Use FAISS to find similar insights - O(log N) instead of O(N)
    similar_results = embedding_service.find_similar(
        query_vector=new_embedding,
        target_type="insight",
        threshold=similarity_threshold,
        limit=max_comparisons,
    )

    if not similar_results:
        return []

    # Filter out self-match and get insight objects
    candidates = []
    for target_id, similarity in similar_results:
        if target_id == new_insight.id:
            continue
        insight = knowledge_base.get_insight(target_id)
        if insight:
            candidates.append((insight, similarity))

    if not candidates:
        return []

    # Limit to top 10 for LLM classification
    candidates = candidates[:10]

    # ONE batched LLM call to classify ALL relationships
    pairs_text = ""
    for i, (existing, similarity) in enumerate(candidates):
        pairs_text += f"\nPair {i+1} (similarity: {similarity:.2f}):\n"
        pairs_text += f'- Existing: "{existing.content}"\n'
        pairs_text += f'- New: "{new_insight.content}"\n'

    prompt = f"""Classify the relationships between these insight pairs.
{pairs_text}
For each pair, determine the relationship from the NEW insight to the EXISTING insight:
- confirms: New says essentially the same thing as existing
- contradicts: New says the opposite of existing
- refines: New adds nuance or detail to existing
- extends: New builds on existing with new information
- none: They are about similar topics but unrelated

Return a JSON array with the relationship for each pair in order:
["confirms", "none", "extends", ...]

Return ONLY the JSON array, no other text."""

    try:
        response = llm_provider.generate(prompt, max_tokens=200)

        # Parse the response
        from .schema import extract_json_from_response
        json_str = extract_json_from_response(response)
        relationship_types = json.loads(json_str)

        if not isinstance(relationship_types, list):
            relationship_types = [relationship_types]

        # Create relationships for valid classifications
        relationships = []
        valid_types = {"confirms", "contradicts", "refines", "extends"}

        for i, (existing, similarity) in enumerate(candidates):
            if i >= len(relationship_types):
                break

            rel_type = str(relationship_types[i]).lower().strip()
            if rel_type not in valid_types:
                continue

            relationship = Relationship(
                id=str(uuid.uuid4()),
                source_insight_id=new_insight.id,
                target_insight_id=existing.id,
                relationship_type=rel_type,
                strength=similarity,
                detected_at=datetime.now(),
            )
            knowledge_base.save_relationship(relationship)
            relationships.append(relationship)

        return relationships

    except Exception as e:
        print(f"Warning: Failed to classify relationships: {e}", file=sys.stderr)
        return []


def format_relationship(relationship: Relationship, knowledge_base: KnowledgeBase) -> str:
    """
    Format a relationship for human-readable display.

    Args:
        relationship: The relationship to format
        knowledge_base: Knowledge base to look up insight content

    Returns:
        Human-readable string like:
        "New insight CONFIRMS existing: 'AI improves productivity' (similarity: 0.85)"
    """
    # Get the target insight content by direct ID lookup
    target_insight = knowledge_base.get_insight(relationship.target_insight_id)

    target_preview = "unknown"
    if target_insight:
        # Show full content - let terminal wrap naturally
        target_preview = target_insight.content

    rel_type = relationship.relationship_type.upper()
    strength = relationship.strength

    return f"{rel_type} existing: '{target_preview}' (similarity: {strength:.2f})"


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


# ============================================================================
# Combined Extraction - Issue 7: ONE LLM call extracts everything
# ============================================================================

@dataclass
class CombinedExtractionOutput:
    """Output from combined extraction operation."""
    insights: list[Insight]
    new_triples: list[Triple]  # Triples newly saved to KB
    existing_triples: list[Triple]  # Triples that already existed
    signal_tags: list[dict]  # {"tag": str, "confidence": float}
    summary: str
    is_ad: bool
    chunks_processed: int


def extract_all_from_article(
    article: Article,
    llm_provider,
    knowledge_base: KnowledgeBase,
) -> CombinedExtractionOutput:
    """Extract everything from an article in ONE LLM call.

    This is the Issue 7 solution - instead of making 6 separate LLM calls
    (chunk, insights, triples, signal tags, summary, etc.), we make ONE call
    that extracts everything at once.

    Args:
        article: Article to process
        llm_provider: LLM provider for extraction
        knowledge_base: Knowledge base to save results to

    Returns:
        CombinedExtractionOutput with all extracted data
    """
    from .schema import parse_combined_extraction, CombinedExtractionResult
    from .constitution import get_constitution_context

    if not article.content or len(article.content) < 100:
        return CombinedExtractionOutput(
            insights=[],
            new_triples=[],
            existing_triples=[],
            signal_tags=[],
            summary="",
            is_ad=False,
            chunks_processed=0,
        )

    constitution_context = get_constitution_context()

    # ONE prompt that extracts everything
    # CRITICAL: Constitution is for HOW to analyze, not WHAT to extract
    prompt = f"""{constitution_context}
=== ARTICLE TO ANALYZE ===
Extract information from ONLY the article content below. Do NOT include the analysis principles above as insights or facts - they are instructions for HOW to analyze, not content to extract.

Analyze this article completely. Extract ALL information in a single structured response.

Article: "{article.title}"

Content:
{article.content}

Instructions:
1. Divide the content into semantically coherent chunks (by topic/section)
2. For EACH chunk, extract:
   - Insights (key learnings, facts, claims)
   - Triples (subject-predicate-object relationships where subjects and objects are PROPER NOUNS only - specific named people, companies, places, organizations. NEVER use generic nouns like 'woman', 'man', 'article', 'analysis'.)
3. For the ENTIRE article, provide:
   - Signal tags (topics, themes, categories)
   - Whether this appears to be an advertisement/sponsored content
   - A concise summary (2-3 sentences)

Return as JSON with this exact structure:
{{
  "chunks": [
    {{
      "content": "The chunk text...",
      "insights": [
        {{"content": "Insight text", "type": "technical|tool|statistic|opinion", "confidence": "high|medium|low", "reason": "Why this confidence"}}
      ],
      "triples": [
        {{"subject": "Entity", "predicate": "relationship", "object": "Entity/Value", "subject_type": "entity", "object_type": "entity|literal", "confidence": "high|medium|low"}}
      ]
    }}
  ],
  "signal_tags": [
    {{"tag": "topic name", "confidence": 0.9, "reason": "Why this tag"}}
  ],
  "is_ad": false,
  "summary": "Concise 2-3 sentence summary of the article."
}}

Extract ALL relevant information. The number of chunks, insights, and triples depends entirely on the content density.
Return ONLY valid JSON, no other text."""

    try:
        # ONE LLM call for everything
        response = llm_provider.generate(prompt, max_tokens=4000)

        # Parse with schema validation
        try:
            result = parse_combined_extraction(response)
        except ValueError as e:
            logger.warning(f"Schema validation failed, attempting fallback: {e}")
            # Fallback: try to extract JSON manually
            from .schema import parse_json_response
            data = parse_json_response(response)
            result = CombinedExtractionResult.model_validate(data)

        # Process extracted data and save to knowledge base
        all_insights = []
        new_triples = []
        existing_triples = []

        for chunk in result.chunks:
            # Save insights from this chunk
            for insight_data in chunk.insights:
                insight = Insight(
                    id=str(uuid.uuid4()),
                    article_id=article.id,
                    content=insight_data.content,
                    insight_type=insight_data.type,
                    confidence=insight_data.confidence,
                    confidence_reason=insight_data.reason,
                )
                if knowledge_base.save_insight(insight):
                    all_insights.append(insight)

            # Save triples from this chunk
            for triple_data in chunk.triples:
                if not (triple_data.subject and triple_data.predicate and triple_data.object):
                    continue
                triple = Triple(
                    id=str(uuid.uuid4()),
                    subject=triple_data.subject,
                    predicate=triple_data.predicate,
                    object=triple_data.object,
                    subject_type=triple_data.subject_type,
                    object_type=triple_data.object_type,
                    source_article_id=article.id,
                    confidence=triple_data.confidence,
                )
                if knowledge_base.save_triple(triple):
                    new_triples.append(triple)
                else:
                    existing_triples.append(triple)

        # Convert signal tags to dict format
        signal_tags = [
            {"tag": t.tag, "confidence": t.confidence, "reason": t.reason}
            for t in result.signal_tags
        ]

        return CombinedExtractionOutput(
            insights=all_insights,
            new_triples=new_triples,
            existing_triples=existing_triples,
            signal_tags=signal_tags,
            summary=result.summary,
            is_ad=result.is_ad,
            chunks_processed=len(result.chunks),
        )

    except Exception as e:
        logger.error(f"Combined extraction failed for '{article.title[:40]}': {e}")
        # Return empty result on failure
        return CombinedExtractionOutput(
            insights=[],
            new_triples=[],
            existing_triples=[],
            signal_tags=[],
            summary="",
            is_ad=False,
            chunks_processed=0,
        )
