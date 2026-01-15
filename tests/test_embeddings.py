"""Tests for embeddings.py - Embedding service for semantic similarity."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import pickle

from src.embeddings import EmbeddingService, EmbeddingResult, EmbeddingError, embed_and_store_article
from src.embedding_providers import (
    EmbeddingProvider,
    EmbeddingProviderError,
    NoProviderAvailableError,
    LMStudioProvider,
    OllamaProvider,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_article():
    """Create a mock article."""
    article = MagicMock()
    article.id = "article-1"
    article.title = "Test Article About AI Technology"
    article.content = "This is the content of the article about artificial intelligence and machine learning."
    return article


@pytest.fixture
def mock_story():
    """Create a mock story."""
    story = MagicMock()
    story.id = "story-1"
    story.title = "AI Technology Story"
    story.description = "A story about artificial intelligence developments"
    story.keywords = ["AI", "technology", "machine learning"]
    return story


@pytest.fixture
def mock_kb():
    """Create a mock knowledge base."""
    kb = MagicMock()
    kb.get_embedding.return_value = None
    kb.save_embedding.return_value = True
    return kb


@pytest.fixture
def mock_provider():
    """Create a mock embedding provider."""
    provider = MagicMock(spec=EmbeddingProvider)
    provider.is_available.return_value = True
    provider.name = "MockProvider"
    provider.model_name = "mock-embedding-model"
    # Return a 256-dim vector for any text
    provider.embed.return_value = [0.1] * 256
    provider.embed_batch.return_value = [[0.1] * 256]
    return provider


@pytest.fixture
def embedding_service(mock_kb, mock_provider):
    """Create embedding service with mocked provider."""
    with patch('src.embeddings.EmbeddingProviderManager') as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager.get_provider.return_value = mock_provider
        mock_manager.list_available.return_value = ["mock"]
        mock_manager_class.return_value = mock_manager

        service = EmbeddingService(mock_kb)
        # Store the mock for test access
        service._mock_provider = mock_provider
        return service


# =============================================================================
# Tests for EmbeddingResult
# =============================================================================


class TestEmbeddingResult:
    """Tests for the EmbeddingResult dataclass."""

    def test_embedding_result_creation(self):
        """Test creating an EmbeddingResult."""
        result = EmbeddingResult(
            vector=[0.1, 0.2, 0.3],
            model="test-model",
            dimensions=3,
        )
        assert result.vector == [0.1, 0.2, 0.3]
        assert result.model == "test-model"
        assert result.dimensions == 3


# =============================================================================
# Tests for EmbeddingService
# =============================================================================


class TestEmbeddingServiceInit:
    """Tests for EmbeddingService initialization."""

    def test_service_creates_with_kb(self, mock_kb):
        """Test service initializes with provided KB."""
        with patch('src.embeddings.EmbeddingProviderManager'):
            service = EmbeddingService(mock_kb)
            assert service.kb == mock_kb

    def test_service_creates_default_kb(self):
        """Test service creates default KB if none provided."""
        with patch('src.embeddings.KnowledgeBase') as mock_kb_class:
            with patch('src.embeddings.EmbeddingProviderManager'):
                mock_kb_class.return_value = MagicMock()
                service = EmbeddingService()
                mock_kb_class.assert_called_once()


class TestEmbedText:
    """Tests for embed_text with mocked provider."""

    def test_embed_text_returns_result(self, embedding_service):
        """Test embed_text returns an EmbeddingResult."""
        result = embedding_service.embed_text("Test text for embedding")
        assert isinstance(result, EmbeddingResult)
        assert len(result.vector) == 256

    def test_embed_text_calls_provider(self, embedding_service):
        """Test embed_text calls the provider."""
        embedding_service.embed_text("Test text")
        embedding_service._mock_provider.embed.assert_called()

    def test_embed_text_handles_long_text_via_chunking(self, embedding_service):
        """Test that long text is chunked and averaged, not truncated."""
        # Create text with sentence boundaries for proper chunking
        long_text = "This is a test sentence. " * 200  # ~5000 chars
        embedding_service._mock_provider.embed_batch.return_value = [
            [0.1] * 128,
            [0.3] * 128,
        ]
        result = embedding_service.embed_text(long_text)
        # Should use embed_batch for chunked text
        embedding_service._mock_provider.embed_batch.assert_called()
        # Result should be averaged embeddings
        assert result.vector is not None

    def test_embed_text_raises_on_provider_error(self, mock_kb):
        """Test embed_text raises EmbeddingError on provider failure."""
        with patch('src.embeddings.EmbeddingProviderManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_provider = MagicMock()
            mock_provider.embed.side_effect = EmbeddingProviderError("Connection failed")
            mock_manager.get_provider.return_value = mock_provider
            mock_manager_class.return_value = mock_manager

            service = EmbeddingService(mock_kb)

            with pytest.raises(EmbeddingError) as exc_info:
                service.embed_text("Test")

            assert "Connection failed" in str(exc_info.value)

    def test_embed_text_raises_on_no_provider(self, mock_kb):
        """Test embed_text raises EmbeddingError when no provider available."""
        with patch('src.embeddings.EmbeddingProviderManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.get_provider.side_effect = NoProviderAvailableError("No provider")
            mock_manager_class.return_value = mock_manager

            service = EmbeddingService(mock_kb)

            with pytest.raises(EmbeddingError) as exc_info:
                service.embed_text("Test")

            assert "No provider" in str(exc_info.value)


class TestEmbedBatch:
    """Tests for embed_batch."""

    def test_embed_batch_returns_list(self, embedding_service):
        """Test embed_batch returns list of results."""
        embedding_service._mock_provider.embed_batch.return_value = [[0.1] * 256, [0.2] * 256]
        results = embedding_service.embed_batch(["Text 1", "Text 2"])
        assert len(results) == 2
        assert all(isinstance(r, EmbeddingResult) for r in results)

    def test_embed_batch_empty_list(self, embedding_service):
        """Test embed_batch with empty list."""
        results = embedding_service.embed_batch([])
        assert results == []


class TestEmbedArticle:
    """Tests for embed_article."""

    def test_embed_article_returns_result(self, embedding_service, mock_article):
        """Test embed_article returns an EmbeddingResult."""
        result = embedding_service.embed_article(mock_article)
        assert isinstance(result, EmbeddingResult)

    def test_embed_article_combines_title_and_content(self, embedding_service, mock_article):
        """Test that embedding includes both title and content."""
        embedding_service.embed_article(mock_article)
        call_args = embedding_service._mock_provider.embed.call_args[0][0]
        assert mock_article.title in call_args
        assert mock_article.content[:100] in call_args


class TestEmbedStory:
    """Tests for embed_story."""

    def test_embed_story_returns_result(self, embedding_service, mock_story):
        """Test embed_story returns an EmbeddingResult."""
        result = embedding_service.embed_story(mock_story)
        assert isinstance(result, EmbeddingResult)

    def test_embed_story_includes_keywords(self, embedding_service, mock_story):
        """Test that story embedding includes keywords."""
        embedding_service.embed_story(mock_story)
        call_args = embedding_service._mock_provider.embed.call_args[0][0]
        assert "AI" in call_args
        assert "technology" in call_args


# =============================================================================
# Tests for cosine similarity
# =============================================================================


class TestCosineSimilarity:
    """Tests for cosine_similarity calculation."""

    def test_identical_vectors_similarity_one(self, embedding_service):
        """Test identical vectors have similarity of 1."""
        vec = [0.5, 0.5, 0.5, 0.5]
        similarity = embedding_service.cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.001

    def test_orthogonal_vectors_similarity_zero(self, embedding_service):
        """Test orthogonal vectors have similarity of 0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = embedding_service.cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.001

    def test_opposite_vectors_similarity_negative(self, embedding_service):
        """Test opposite vectors have similarity of -1."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        similarity = embedding_service.cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 0.001

    def test_different_length_vectors_padded(self, embedding_service):
        """Test vectors of different lengths are padded."""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0, 0.0]
        # Should not raise, and should compute similarity
        similarity = embedding_service.cosine_similarity(vec1, vec2)
        assert isinstance(similarity, float)

    def test_zero_vector_returns_zero(self, embedding_service):
        """Test zero vector returns similarity of 0."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 1.0, 1.0]
        similarity = embedding_service.cosine_similarity(vec1, vec2)
        assert similarity == 0.0


# =============================================================================
# Tests for save and get embedding
# =============================================================================


class TestSaveAndGetEmbedding:
    """Tests for saving and retrieving embeddings."""

    def test_save_embedding_calls_kb(self, embedding_service, mock_kb):
        """Test save_embedding calls KB save method."""
        result = EmbeddingResult(
            vector=[0.1, 0.2, 0.3],
            model="test",
            dimensions=3,
        )
        embedding_service.save_embedding("target-1", "article", result)
        mock_kb.save_embedding.assert_called_once()

    def test_get_embedding_returns_none_when_not_found(self, embedding_service, mock_kb):
        """Test get_embedding returns None when not found."""
        mock_kb.get_embedding.return_value = None
        result = embedding_service.get_embedding("nonexistent", "article")
        assert result is None

    def test_get_embedding_returns_vector_when_found(self, embedding_service, mock_kb):
        """Test get_embedding returns vector when found."""
        stored_vector = [0.1, 0.2, 0.3]
        mock_embedding = MagicMock()
        mock_embedding.vector = pickle.dumps(stored_vector)
        mock_kb.get_embedding.return_value = mock_embedding

        result = embedding_service.get_embedding("target-1", "article")
        assert result == stored_vector


# =============================================================================
# Tests for find_similar
# =============================================================================


class TestFindSimilar:
    """Tests for find_similar."""

    def test_find_similar_returns_list(self, mock_kb, mock_provider):
        """Test find_similar returns a list."""
        mock_kb.get_embedding.return_value = None
        # Mock the database query
        mock_kb._connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = []

        with patch('src.embeddings.EmbeddingProviderManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.get_provider.return_value = mock_provider
            mock_manager_class.return_value = mock_manager

            service = EmbeddingService(mock_kb)
            results = service.find_similar([0.5, 0.5], "article")
            assert isinstance(results, list)


# =============================================================================
# Tests for provider info
# =============================================================================


class TestProviderInfo:
    """Tests for is_available and get_provider_info."""

    def test_is_available_true(self, embedding_service):
        """Test is_available returns True when provider available."""
        assert embedding_service.is_available() is True

    def test_get_provider_info_success(self, embedding_service):
        """Test get_provider_info returns provider details."""
        info = embedding_service.get_provider_info()
        assert info["available"] is True
        assert "provider" in info
        assert "model" in info

    def test_get_provider_info_failure(self, mock_kb):
        """Test get_provider_info when no provider available."""
        with patch('src.embeddings.EmbeddingProviderManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.get_provider.side_effect = NoProviderAvailableError("No provider")
            mock_manager.list_available.return_value = []
            mock_manager_class.return_value = mock_manager

            service = EmbeddingService(mock_kb)
            info = service.get_provider_info()

            assert info["available"] is False
            assert "error" in info


# =============================================================================
# Tests for embedding providers
# =============================================================================


class TestLMStudioProvider:
    """Tests for LMStudioProvider."""

    def test_provider_name(self):
        """Test provider name."""
        provider = LMStudioProvider()
        assert provider.name == "LM Studio"

    @patch('src.embedding_providers.httpx.get')
    def test_is_available_success(self, mock_get):
        """Test is_available returns True when LM Studio responds."""
        mock_get.return_value.is_success = True
        mock_get.return_value.json.return_value = {"data": [{"id": "model"}]}

        provider = LMStudioProvider()
        assert provider.is_available() is True

    def test_embed_batch_success(self):
        """Test embed_batch with successful response via gateway module."""
        embeddings = [[0.1, 0.2], [0.3, 0.4]]

        # Mock the gateway module (preferred path)
        mock_gateway = MagicMock()
        mock_gateway.is_available.return_value = True
        mock_gateway.batch_embedding.return_value = embeddings

        with patch('src.gateway.get_gateway', return_value=mock_gateway):
            provider = LMStudioProvider()
            results = provider.embed_batch(["text1", "text2"])

            assert len(results) == 2
            assert results[0] == [0.1, 0.2]
            assert results[1] == [0.3, 0.4]
            mock_gateway.batch_embedding.assert_called_once_with(["text1", "text2"])


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_provider_name(self):
        """Test provider name."""
        provider = OllamaProvider()
        assert provider.name == "Ollama"

    def test_default_model(self):
        """Test default model is nomic-embed-text."""
        provider = OllamaProvider()
        assert provider.model_name == "nomic-embed-text"

    @patch('src.embedding_providers.httpx.post')
    def test_embed_success(self, mock_post):
        """Test embed with successful response."""
        mock_post.return_value.is_success = True
        mock_post.return_value.json.return_value = {
            "embedding": [0.1, 0.2, 0.3]
        }

        provider = OllamaProvider()
        result = provider.embed("test text")

        assert result == [0.1, 0.2, 0.3]


# =============================================================================
# Integration tests
# =============================================================================


class TestEmbeddingIntegration:
    """Integration tests for embedding workflow."""

    def test_full_embedding_workflow(self, mock_kb, mock_article, mock_provider):
        """Test full workflow: embed article, save, retrieve, compare."""
        with patch('src.embeddings.EmbeddingProviderManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.get_provider.return_value = mock_provider
            mock_manager_class.return_value = mock_manager

            service = EmbeddingService(mock_kb)

            # Embed article
            result = service.embed_article(mock_article)
            assert result is not None
            assert len(result.vector) > 0

            # Save embedding
            service.save_embedding(mock_article.id, "article", result)
            assert mock_kb.save_embedding.called

            # Compare with self (should be 1.0)
            similarity = service.cosine_similarity(result.vector, result.vector)
            assert abs(similarity - 1.0) < 0.001
