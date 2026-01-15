"""Graph cleanup operations for semantic deduplication.

Handles semantic duplicates that exact matching misses, like:
- "USA" vs "United States" vs "U.S."
- "GPT-4" vs "GPT4" vs "gpt-4"

This runs AFTER batch processing, not blocking ingestion.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .knowledge import KnowledgeBase, Triple
from .embeddings import EmbeddingService, EmbeddingError

logger = logging.getLogger(__name__)


@dataclass
class DuplicateCandidate:
    """A pair of potentially duplicate entities/triples."""
    canonical: str  # The preferred form
    duplicate: str  # The form to merge
    similarity: float  # Cosine similarity
    canonical_count: int  # How many times canonical appears
    duplicate_count: int  # How many times duplicate appears
    entity_type: str  # "subject", "object", or "triple"


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    candidates_found: int
    duplicates_merged: int
    triples_updated: int
    errors: list[str]


def find_duplicate_entities(
    kb: KnowledgeBase,
    embedding_service: Optional[EmbeddingService] = None,
    similarity_threshold: float = 0.90,
    entity_type: str = "subject",
) -> list[DuplicateCandidate]:
    """Find semantically similar entities that might be duplicates.

    Uses FAISS to efficiently find similar entities, then returns candidates
    for human review or automated merging.

    Args:
        kb: Knowledge base to analyze
        embedding_service: Embedding service (created if not provided)
        similarity_threshold: Minimum similarity to flag as duplicate (0.90+ is conservative)
        entity_type: "subject" or "object" - which triple field to analyze

    Returns:
        List of DuplicateCandidate pairs for review
    """
    from .vector_index import get_vector_index

    if embedding_service is None:
        embedding_service = EmbeddingService(kb)
        if not embedding_service.is_available():
            logger.warning("Embedding service not available for cleanup")
            return []

    # Get unique entities from triples
    with kb._connect() as conn:
        if entity_type == "subject":
            rows = conn.execute(
                "SELECT subject as entity, COUNT(*) as cnt FROM knowledge_triples GROUP BY subject"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT object as entity, COUNT(*) as cnt FROM knowledge_triples GROUP BY object"
            ).fetchall()

    entities = {row["entity"]: row["cnt"] for row in rows}

    if len(entities) < 2:
        return []

    # Embed all unique entities
    entity_embeddings = {}
    for entity in entities:
        try:
            result = embedding_service.embed_text(entity)
            entity_embeddings[entity] = result.vector
        except EmbeddingError:
            continue

    if len(entity_embeddings) < 2:
        return []

    # Build FAISS index for entities
    index = get_vector_index(dimensions=len(next(iter(entity_embeddings.values()))))
    index.clear(f"cleanup_{entity_type}")

    for entity, vector in entity_embeddings.items():
        index.add(entity, f"cleanup_{entity_type}", vector)

    # Find similar pairs
    candidates = []
    seen_pairs = set()

    for entity, vector in entity_embeddings.items():
        results = index.search(
            query_vector=vector,
            target_type=f"cleanup_{entity_type}",
            k=5,
            threshold=similarity_threshold,
        )

        for result in results:
            other_entity = result.target_id
            if other_entity == entity:
                continue

            # Avoid duplicate pairs
            pair_key = tuple(sorted([entity, other_entity]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Determine canonical form (prefer more frequent or longer)
            entity_count = entities.get(entity, 0)
            other_count = entities.get(other_entity, 0)

            if entity_count > other_count:
                canonical, duplicate = entity, other_entity
                can_count, dup_count = entity_count, other_count
            elif other_count > entity_count:
                canonical, duplicate = other_entity, entity
                can_count, dup_count = other_count, entity_count
            elif len(entity) > len(other_entity):
                # Prefer longer form ("United States" over "US")
                canonical, duplicate = entity, other_entity
                can_count, dup_count = entity_count, other_count
            else:
                canonical, duplicate = other_entity, entity
                can_count, dup_count = other_count, entity_count

            candidates.append(DuplicateCandidate(
                canonical=canonical,
                duplicate=duplicate,
                similarity=result.score,
                canonical_count=can_count,
                duplicate_count=dup_count,
                entity_type=entity_type,
            ))

    # Sort by similarity descending
    candidates.sort(key=lambda x: x.similarity, reverse=True)
    return candidates


def merge_entity(
    kb: KnowledgeBase,
    canonical: str,
    duplicate: str,
    entity_type: str = "subject",
) -> int:
    """Merge a duplicate entity into the canonical form.

    Updates all triples referencing the duplicate to use the canonical form.
    This is done in a transaction for safety.

    Args:
        kb: Knowledge base to update
        canonical: The preferred entity name
        duplicate: The duplicate entity name to replace
        entity_type: "subject" or "object"

    Returns:
        Number of triples updated
    """
    with kb._connect() as conn:
        try:
            if entity_type == "subject":
                result = conn.execute(
                    "UPDATE knowledge_triples SET subject = ? WHERE subject = ?",
                    (canonical, duplicate)
                )
            else:
                result = conn.execute(
                    "UPDATE knowledge_triples SET object = ? WHERE object = ?",
                    (canonical, duplicate)
                )

            updated = result.rowcount
            conn.commit()

            logger.info(f"Merged '{duplicate}' -> '{canonical}': {updated} triples updated")
            return updated

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to merge '{duplicate}' -> '{canonical}': {e}")
            raise


def run_cleanup(
    kb: KnowledgeBase,
    embedding_service: Optional[EmbeddingService] = None,
    auto_merge: bool = False,
    similarity_threshold: float = 0.95,  # High threshold for auto-merge
) -> CleanupResult:
    """Run graph cleanup to find and optionally merge duplicates.

    Args:
        kb: Knowledge base to clean
        embedding_service: Embedding service (created if not provided)
        auto_merge: If True, automatically merge high-confidence duplicates.
                   If False, just find candidates for review.
        similarity_threshold: Minimum similarity for auto-merge (0.95+ is safe)

    Returns:
        CleanupResult with statistics
    """
    result = CleanupResult(
        candidates_found=0,
        duplicates_merged=0,
        triples_updated=0,
        errors=[],
    )

    # Find duplicates in both subjects and objects
    for entity_type in ["subject", "object"]:
        candidates = find_duplicate_entities(
            kb=kb,
            embedding_service=embedding_service,
            similarity_threshold=similarity_threshold,
            entity_type=entity_type,
        )

        result.candidates_found += len(candidates)

        if auto_merge:
            for candidate in candidates:
                if candidate.similarity >= similarity_threshold:
                    try:
                        updated = merge_entity(
                            kb=kb,
                            canonical=candidate.canonical,
                            duplicate=candidate.duplicate,
                            entity_type=entity_type,
                        )
                        result.duplicates_merged += 1
                        result.triples_updated += updated
                    except Exception as e:
                        result.errors.append(
                            f"Failed to merge {candidate.duplicate} -> {candidate.canonical}: {e}"
                        )

    return result


def get_cleanup_report(
    kb: KnowledgeBase,
    embedding_service: Optional[EmbeddingService] = None,
    similarity_threshold: float = 0.85,
    limit: int = 50,
) -> str:
    """Generate a human-readable report of potential duplicates.

    Args:
        kb: Knowledge base to analyze
        embedding_service: Embedding service
        similarity_threshold: Minimum similarity to report
        limit: Maximum candidates to show

    Returns:
        Formatted report string
    """
    lines = ["# Graph Cleanup Report", ""]

    for entity_type in ["subject", "object"]:
        candidates = find_duplicate_entities(
            kb=kb,
            embedding_service=embedding_service,
            similarity_threshold=similarity_threshold,
            entity_type=entity_type,
        )

        if not candidates:
            lines.append(f"## {entity_type.title()}s: No duplicates found")
            lines.append("")
            continue

        lines.append(f"## {entity_type.title()}s: {len(candidates)} potential duplicates")
        lines.append("")
        lines.append("| Similarity | Canonical | Count | Duplicate | Count |")
        lines.append("|------------|-----------|-------|-----------|-------|")

        for candidate in candidates[:limit]:
            lines.append(
                f"| {candidate.similarity:.2%} | {candidate.canonical[:30]} | "
                f"{candidate.canonical_count} | {candidate.duplicate[:30]} | "
                f"{candidate.duplicate_count} |"
            )

        lines.append("")

    return "\n".join(lines)
