"""Embedding service for semantic similarity.

Uses embedding providers (LM Studio, Ollama) for vector embeddings,
enabling fast similarity comparisons without expensive LLM calls at query time.

NO FALLBACKS. If no embedding provider is available, operations fail loudly.
"""

import math
import pickle
import uuid
from dataclasses import dataclass
from typing import Optional

from .embedding_providers import (
    EmbeddingProviderManager,
    EmbeddingProviderError,
    NoProviderAvailableError,
)
from .knowledge import KnowledgeBase, Embedding
from .storage import Article, Story


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    vector: list[float]
    model: str
    dimensions: int


class EmbeddingError(Exception):
    """Raised when embedding operations fail."""
    pass


class EmbeddingService:
    """Service for generating and comparing embeddings.

    Uses embedding providers (LM Studio, Ollama) for neural embeddings.
    NO FALLBACKS - fails loudly if no provider available.
    """

    def __init__(
        self,
        kb: Optional[KnowledgeBase] = None,
        preferred_provider: Optional[str] = None,
    ):
        """Initialize embedding service.

        Args:
            kb: Knowledge base for storing embeddings (creates one if None)
            preferred_provider: Preferred provider name ("lm_studio" or "ollama").
                               If None, auto-detects first available.
        """
        self.kb = kb or KnowledgeBase()
        self._provider_manager = EmbeddingProviderManager(preferred_provider)
        self._provider = None  # Lazy initialization

    def _get_provider(self):
        """Get the active embedding provider.

        Raises:
            EmbeddingError: If no provider is available
        """
        try:
            return self._provider_manager.get_provider()
        except NoProviderAvailableError as e:
            raise EmbeddingError(str(e)) from e

    def embed_text(self, text: str) -> EmbeddingResult:
        """Generate embedding for text.

        Args:
            text: Text to embed. Long texts are chunked at sentence boundaries
                  and embeddings are averaged to preserve all information.

        Returns:
            EmbeddingResult with vector

        Raises:
            EmbeddingError: If embedding fails or no provider available
        """
        try:
            provider = self._get_provider()

            # For long text, chunk at sentence boundaries and average embeddings
            # Most embedding models have ~8k token limit, ~2000 chars is conservative
            if len(text) > 2000:
                chunks = self._chunk_at_sentences(text, max_chunk_size=1800)
                if len(chunks) > 1:
                    vectors = provider.embed_batch(chunks)
                    averaged = self._average_vectors(vectors)
                    return EmbeddingResult(
                        vector=averaged,
                        model=provider.model_name,
                        dimensions=len(averaged),
                    )
                text = chunks[0] if chunks else text

            vector = provider.embed(text)

            return EmbeddingResult(
                vector=vector,
                model=provider.model_name,
                dimensions=len(vector),
            )
        except EmbeddingProviderError as e:
            raise EmbeddingError(f"Embedding failed: {e}") from e

    def _chunk_at_sentences(self, text: str, max_chunk_size: int = 1800) -> list[str]:
        """Split text at sentence boundaries to fit embedding model limits."""
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        current_chunk = ""

        # Split on sentence-ending punctuation
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in '.!?' and len(current) > 1:
                sentences.append(current)
                current = ""
        if current.strip():
            sentences.append(current)

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    def _average_vectors(self, vectors: list[list[float]]) -> list[float]:
        """Average multiple embedding vectors into one."""
        if not vectors:
            return []
        if len(vectors) == 1:
            return vectors[0]

        dim = len(vectors[0])
        averaged = [0.0] * dim
        for vec in vectors:
            for i, v in enumerate(vec):
                if i < dim:
                    averaged[i] += v

        n = len(vectors)
        return [v / n for v in averaged]

    def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed. Long texts are chunked and averaged.

        Returns:
            List of EmbeddingResults

        Raises:
            EmbeddingError: If embedding fails or no provider available
        """
        if not texts:
            return []

        try:
            provider = self._get_provider()

            # Process each text, chunking and averaging as needed
            results = []
            for text in texts:
                if len(text) > 2000:
                    chunks = self._chunk_at_sentences(text, max_chunk_size=1800)
                    if len(chunks) > 1:
                        vectors = provider.embed_batch(chunks)
                        averaged = self._average_vectors(vectors)
                        results.append(EmbeddingResult(
                            vector=averaged,
                            model=provider.model_name,
                            dimensions=len(averaged),
                        ))
                        continue
                    text = chunks[0] if chunks else text

                vector = provider.embed(text)
                results.append(EmbeddingResult(
                    vector=vector,
                    model=provider.model_name,
                    dimensions=len(vector),
                ))
            return results
        except EmbeddingProviderError as e:
            raise EmbeddingError(f"Batch embedding failed: {e}") from e

    def embed_article(self, article: Article) -> EmbeddingResult:
        """Generate embedding for an article.

        Combines title and full content for complete representation.
        Long content is chunked and embeddings are averaged.

        Raises:
            EmbeddingError: If embedding fails
        """
        text = f"{article.title}\n\n{article.content or ''}"
        return self.embed_text(text)

    def embed_story(self, story: Story) -> EmbeddingResult:
        """Generate embedding for a story.

        Uses title, description, and keywords.

        Raises:
            EmbeddingError: If embedding fails
        """
        keywords_str = ", ".join(story.keywords[:20]) if story.keywords else ""
        text = f"{story.title}\n\n{story.description or ''}\n\nKeywords: {keywords_str}"
        return self.embed_text(text)

    def save_embedding(
        self,
        target_id: str,
        target_type: str,
        embedding: EmbeddingResult,
    ) -> bool:
        """Save embedding to knowledge base and FAISS index.

        Args:
            target_id: ID of the article, story, or insight
            target_type: 'article', 'story', or 'insight'
            embedding: The embedding result to save

        Returns:
            True if saved successfully

        Raises:
            EmbeddingError: If FAISS is not available (NO FALLBACKS - fix it, don't work around it)
        """
        # FAIL FAST: FAISS must be available. No silent degradation.
        try:
            from .vector_index import get_vector_index
        except ImportError as e:
            raise EmbeddingError(
                f"FAISS not available: {e}\n"
                "This is a FATAL error - embeddings without FAISS won't be searchable.\n"
                "Fix: pip install faiss-cpu\n"
                "DO NOT catch this error and continue - that hides the problem."
            ) from e

        emb = Embedding(
            id=str(uuid.uuid4()),
            target_id=target_id,
            target_type=target_type,
            vector=pickle.dumps(embedding.vector),
            model=embedding.model,
        )
        saved = self.kb.save_embedding(emb)

        # Also add to FAISS index for fast similarity search
        if saved:
            index = get_vector_index(dimensions=len(embedding.vector))
            index.add(target_id, target_type, embedding.vector)

        return saved

    def get_embedding(self, target_id: str, target_type: str) -> Optional[list[float]]:
        """Get stored embedding for a target.

        Args:
            target_id: ID of the article, story, or insight
            target_type: 'article', 'story', or 'insight'

        Returns:
            Vector as list of floats, or None if not found
        """
        emb = self.kb.get_embedding(target_id, target_type)
        if emb:
            return pickle.loads(emb.vector)
        return None

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score between -1 and 1 (higher is more similar)
        """
        if len(vec1) != len(vec2):
            # Pad shorter vector with zeros
            max_len = max(len(vec1), len(vec2))
            vec1 = vec1 + [0.0] * (max_len - len(vec1))
            vec2 = vec2 + [0.0] * (max_len - len(vec2))

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return dot_product / (mag1 * mag2)

    def find_similar(
        self,
        query_vector: list[float],
        target_type: str,
        threshold: float = 0.7,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """Find similar items by vector similarity using FAISS.

        Uses approximate nearest neighbor search for O(log N) performance
        instead of brute-force O(N) scanning.

        Args:
            query_vector: Vector to compare against
            target_type: Type of targets to search ('article', 'story', 'insight')
            threshold: Minimum similarity score
            limit: Maximum results to return

        Returns:
            List of (target_id, similarity_score) tuples, sorted by score desc

        Raises:
            EmbeddingError: If FAISS is not available (NO FALLBACKS)
        """
        # FAIL FAST: FAISS must be available
        try:
            from .vector_index import get_vector_index
        except ImportError as e:
            raise EmbeddingError(
                f"FAISS not available: {e}\n"
                "Fix: pip install faiss-cpu"
            ) from e

        # Get or initialize the FAISS index
        index = get_vector_index(dimensions=len(query_vector))

        # Load from DB if not already loaded
        index.load_from_db(self.kb, target_type)

        # Search using FAISS (O(log N))
        results = index.search(
            query_vector=query_vector,
            target_type=target_type,
            k=limit,
            threshold=threshold,
        )

        return [(r.target_id, r.score) for r in results]

    def is_available(self) -> bool:
        """Check if the configured embedding provider is available."""
        try:
            self._get_provider()
            return True
        except EmbeddingError:
            return False

    def get_provider_info(self) -> dict:
        """Get information about the active provider.

        Returns:
            Dict with provider name and model, or error info
        """
        try:
            provider = self._get_provider()
            return {
                "available": True,
                "provider": provider.name,
                "model": provider.model_name,
            }
        except EmbeddingError as e:
            return {
                "available": False,
                "error": str(e),
            }


def embed_and_store_article(
    article: Article,
    kb: Optional[KnowledgeBase] = None,
) -> bool:
    """Convenience function to embed an article and store it.

    Args:
        article: Article to embed
        kb: Optional KnowledgeBase (creates one if not provided)

    Returns:
        True if embedding was created and stored

    Raises:
        EmbeddingError: If no embedding provider is available
    """
    service = EmbeddingService(kb)

    embedding = service.embed_article(article)
    return service.save_embedding(article.id, "article", embedding)


def embed_and_store_story(
    story: Story,
    kb: Optional[KnowledgeBase] = None,
) -> bool:
    """Convenience function to embed a story and store it.

    Args:
        story: Story to embed
        kb: Optional KnowledgeBase (creates one if not provided)

    Returns:
        True if embedding was created and stored

    Raises:
        EmbeddingError: If no embedding provider is available
    """
    service = EmbeddingService(kb)

    embedding = service.embed_story(story)
    return service.save_embedding(story.id, "story", embedding)
