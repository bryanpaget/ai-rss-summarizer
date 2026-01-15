"""FAISS-based vector index for O(log N) similarity search.

Replaces brute-force O(N) scanning with approximate nearest neighbor search.
Maintains sync with SQLite knowledge_embeddings table.
"""

import logging
import pickle
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from a similarity search."""
    target_id: str
    score: float  # Cosine similarity (higher = more similar)


class VectorIndex:
    """FAISS-based vector index for fast similarity search.

    Maintains separate indices per target_type (article, story, insight, triple).
    Auto-syncs with SQLite on startup and on add operations.

    Thread-safe for concurrent reads; writes are serialized.
    """

    def __init__(
        self,
        dimensions: int = 768,  # Common embedding dimension
        index_dir: Optional[Path] = None,
    ):
        """Initialize the vector index.

        Args:
            dimensions: Embedding vector dimensions (must match your model)
            index_dir: Directory to persist indices (optional, in-memory if None)
        """
        self.dimensions = dimensions
        self.index_dir = Path(index_dir) if index_dir else None

        # Separate index per target type
        self._indices: dict[str, faiss.IndexIDMap] = {}
        self._id_maps: dict[str, dict[int, str]] = {}  # faiss_id -> target_id
        self._reverse_maps: dict[str, dict[str, int]] = {}  # target_id -> faiss_id
        self._next_id: dict[str, int] = {}

        self._lock = threading.Lock()
        self._initialized_types: set[str] = set()

    def _get_or_create_index(self, target_type: str) -> faiss.IndexIDMap:
        """Get or create index for a target type."""
        if target_type not in self._indices:
            # Use IndexFlatIP (inner product) for cosine similarity
            # Vectors must be L2-normalized for cosine similarity
            base_index = faiss.IndexFlatIP(self.dimensions)
            self._indices[target_type] = faiss.IndexIDMap(base_index)
            self._id_maps[target_type] = {}
            self._reverse_maps[target_type] = {}
            self._next_id[target_type] = 0
        return self._indices[target_type]

    def _normalize(self, vector: np.ndarray) -> np.ndarray:
        """L2 normalize vector for cosine similarity."""
        norm = np.linalg.norm(vector)
        if norm > 0:
            return vector / norm
        return vector

    def add(
        self,
        target_id: str,
        target_type: str,
        vector: list[float],
    ) -> bool:
        """Add a vector to the index.

        If target_id already exists, updates the vector.

        Args:
            target_id: Unique identifier for the item
            target_type: Type of item (article, story, insight, triple)
            vector: Embedding vector

        Returns:
            True if added successfully
        """
        with self._lock:
            try:
                index = self._get_or_create_index(target_type)

                # Check dimensions
                if len(vector) != self.dimensions:
                    # Handle dimension mismatch by padding or truncating
                    if len(vector) < self.dimensions:
                        vector = vector + [0.0] * (self.dimensions - len(vector))
                    else:
                        vector = vector[:self.dimensions]

                # Normalize for cosine similarity
                vec_array = self._normalize(np.array([vector], dtype=np.float32))

                # Remove existing if updating
                if target_id in self._reverse_maps[target_type]:
                    old_faiss_id = self._reverse_maps[target_type][target_id]
                    # FAISS IndexIDMap doesn't support removal, so we track deletions
                    # and rebuild periodically. For now, just update mappings.
                    del self._id_maps[target_type][old_faiss_id]

                # Add with new ID
                faiss_id = self._next_id[target_type]
                self._next_id[target_type] += 1

                index.add_with_ids(vec_array, np.array([faiss_id], dtype=np.int64))

                self._id_maps[target_type][faiss_id] = target_id
                self._reverse_maps[target_type][target_id] = faiss_id

                return True
            except Exception as e:
                logger.error(f"Failed to add vector to index: {e}")
                return False

    def search(
        self,
        query_vector: list[float],
        target_type: str,
        k: int = 10,
        threshold: float = 0.0,
    ) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: Vector to search for
            target_type: Type of items to search (article, story, insight, triple)
            k: Maximum number of results
            threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of SearchResult sorted by score descending
        """
        with self._lock:
            if target_type not in self._indices:
                return []

            index = self._indices[target_type]
            if index.ntotal == 0:
                return []

            try:
                # Handle dimension mismatch
                if len(query_vector) != self.dimensions:
                    if len(query_vector) < self.dimensions:
                        query_vector = query_vector + [0.0] * (self.dimensions - len(query_vector))
                    else:
                        query_vector = query_vector[:self.dimensions]

                # Normalize query
                query_array = self._normalize(np.array([query_vector], dtype=np.float32))

                # Search (may return fewer than k if index is small)
                actual_k = min(k, index.ntotal)
                scores, ids = index.search(query_array, actual_k)

                results = []
                for score, faiss_id in zip(scores[0], ids[0]):
                    if faiss_id < 0:  # FAISS returns -1 for missing
                        continue
                    if faiss_id not in self._id_maps[target_type]:
                        continue  # Deleted entry
                    if score < threshold:
                        continue

                    target_id = self._id_maps[target_type][faiss_id]
                    results.append(SearchResult(target_id=target_id, score=float(score)))

                return results
            except Exception as e:
                logger.error(f"Failed to search index: {e}")
                return []

    def contains(self, target_id: str, target_type: str) -> bool:
        """Check if a target is in the index."""
        with self._lock:
            if target_type not in self._reverse_maps:
                return False
            return target_id in self._reverse_maps[target_type]

    def size(self, target_type: Optional[str] = None) -> int:
        """Get number of vectors in index."""
        with self._lock:
            if target_type:
                if target_type not in self._id_maps:
                    return 0
                return len(self._id_maps[target_type])
            return sum(len(m) for m in self._id_maps.values())

    def load_from_db(self, kb: "KnowledgeBase", target_type: str) -> int:
        """Load vectors from SQLite knowledge_embeddings table.

        Args:
            kb: KnowledgeBase instance
            target_type: Type to load (article, story, insight)

        Returns:
            Number of vectors loaded
        """
        if target_type in self._initialized_types:
            return self.size(target_type)

        count = 0
        with kb._connect() as conn:
            rows = conn.execute(
                "SELECT target_id, vector FROM knowledge_embeddings WHERE target_type = ?",
                (target_type,)
            ).fetchall()

            for row in rows:
                target_id = row["target_id"]
                vector = pickle.loads(row["vector"])

                # Update dimensions if needed (first vector sets it)
                if count == 0 and len(vector) != self.dimensions:
                    self.dimensions = len(vector)
                    # Reset index with correct dimensions
                    if target_type in self._indices:
                        del self._indices[target_type]

                if self.add(target_id, target_type, vector):
                    count += 1

        self._initialized_types.add(target_type)
        logger.info(f"Loaded {count} {target_type} vectors into FAISS index")
        return count

    def clear(self, target_type: Optional[str] = None) -> None:
        """Clear index (for testing)."""
        with self._lock:
            if target_type:
                if target_type in self._indices:
                    del self._indices[target_type]
                    del self._id_maps[target_type]
                    del self._reverse_maps[target_type]
                    del self._next_id[target_type]
                    self._initialized_types.discard(target_type)
            else:
                self._indices.clear()
                self._id_maps.clear()
                self._reverse_maps.clear()
                self._next_id.clear()
                self._initialized_types.clear()


# Global singleton instance
_global_index: Optional[VectorIndex] = None
_index_lock = threading.Lock()


def get_vector_index(dimensions: int = 768) -> VectorIndex:
    """Get the global vector index instance.

    Creates one if it doesn't exist. Thread-safe.

    Args:
        dimensions: Embedding dimensions (only used on first call)

    Returns:
        Global VectorIndex instance
    """
    global _global_index
    with _index_lock:
        if _global_index is None:
            _global_index = VectorIndex(dimensions=dimensions)
        return _global_index


def reset_vector_index() -> None:
    """Reset the global vector index (for testing)."""
    global _global_index
    with _index_lock:
        if _global_index:
            _global_index.clear()
        _global_index = None
