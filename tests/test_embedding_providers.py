"""Comprehensive tests for embedding_providers.py.

Tests cover:
- Provider initialization and configuration
- Availability checking with various server states
- Embedding generation with success and error cases
- Batch embedding behavior
- Response parsing edge cases
- Error handling (timeouts, connection errors, malformed responses)
- Provider manager selection logic
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import httpx

from src.embedding_providers import (
    EmbeddingProvider,
    EmbeddingProviderError,
    NoProviderAvailableError,
    ProviderConfig,
    LMStudioProvider,
    OllamaProvider,
    EmbeddingProviderManager,
)


# =============================================================================
# Autouse fixture to mock model manager for all LMStudioProvider tests
# =============================================================================


@pytest.fixture(autouse=True)
def mock_model_manager():
    """Mock ensure_embedding_model to prevent actual model loading in tests."""
    with patch('src.embedding_providers.ensure_embedding_model') as mock:
        mock.return_value = "test-embedding-model"
        yield mock


# =============================================================================
# Autouse fixture to prevent accidental network calls
# =============================================================================


# Note: Most tests in this file explicitly patch requests.get/post.
# Tests that create EmbeddingProviderManager need to mock the default providers
# after creation to prevent network calls during is_available() checks.


# =============================================================================
# Tests for ProviderConfig
# =============================================================================


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_config_with_defaults(self):
        """Test config uses default timeout."""
        config = ProviderConfig(url="http://localhost:1234", model="test")
        assert config.timeout == 60

    def test_config_custom_timeout(self):
        """Test config accepts custom timeout."""
        config = ProviderConfig(url="http://localhost:1234", model="test", timeout=120)
        assert config.timeout == 120


# =============================================================================
# Tests for LMStudioProvider - Initialization
# =============================================================================


class TestLMStudioProviderInit:
    """Tests for LMStudioProvider initialization."""

    def test_default_url(self):
        """Test default URL is localhost:1234."""
        provider = LMStudioProvider()
        assert provider.url == "http://localhost:1234/v1"

    def test_custom_url(self):
        """Test custom URL is used."""
        provider = LMStudioProvider(url="http://custom:8080/v1")
        assert provider.url == "http://custom:8080/v1"

    def test_default_model_none(self):
        """Test model defaults to None (auto-detect)."""
        provider = LMStudioProvider()
        assert provider._model is None

    def test_custom_model(self):
        """Test custom model is used."""
        provider = LMStudioProvider(model="nomic-embed-text")
        assert provider._model == "nomic-embed-text"

    def test_default_timeout(self):
        """Test default timeout is 60 seconds."""
        provider = LMStudioProvider()
        assert provider.timeout == 60

    def test_custom_timeout(self):
        """Test custom timeout is used."""
        provider = LMStudioProvider(timeout=120)
        assert provider.timeout == 120

    def test_name_property(self):
        """Test name property returns 'LM Studio'."""
        provider = LMStudioProvider()
        assert provider.name == "LM Studio"


# =============================================================================
# Tests for LMStudioProvider - Availability
# =============================================================================


class TestLMStudioProviderAvailability:
    """Tests for LMStudioProvider.is_available()."""

    def test_available_when_server_responds(self):
        """Test returns True when server responds with models."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {
                "data": [{"id": "nomic-embed-text"}]
            }

            provider = LMStudioProvider()
            assert provider.is_available() is True

    def test_unavailable_when_no_models_and_auto_load_disabled(self):
        """Test returns False when no models loaded and auto-load disabled."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {"data": []}

            provider = LMStudioProvider(auto_load_model=False)
            assert provider.is_available() is False

    def test_available_when_no_models_but_auto_load_succeeds(self):
        """Test returns True when no models initially but auto-load succeeds."""
        with patch('src.embedding_providers.httpx.get') as mock_get, \
             patch('src.embedding_providers.ensure_embedding_model') as mock_ensure:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {"data": []}
            mock_ensure.return_value = "test-embedding-model"

            provider = LMStudioProvider(auto_load_model=True)
            assert provider.is_available() is True
            mock_ensure.assert_called_once()

    def test_unavailable_when_auto_load_fails(self):
        """Test returns False when auto-load fails and no model loaded."""
        from src.model_manager import ModelManagerError
        with patch('src.embedding_providers.httpx.get') as mock_get, \
             patch('src.embedding_providers.ensure_embedding_model') as mock_ensure:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {"data": []}
            mock_ensure.side_effect = ModelManagerError("Failed to load")

            provider = LMStudioProvider(auto_load_model=True)
            assert provider.is_available() is False

    def test_unavailable_when_connection_refused(self):
        """Test returns False when connection refused."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("")

            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_unavailable_when_timeout(self):
        """Test returns False when request times out."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("")

            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_unavailable_when_http_error(self):
        """Test returns False when HTTP error."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = False

            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_unavailable_when_json_decode_error(self):
        """Test returns False when response is not valid JSON."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.side_effect = ValueError("Invalid JSON")

            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_caches_model_name_from_auto_load(self):
        """Test model name is cached from auto-load result."""
        with patch('src.embedding_providers.httpx.get') as mock_get, \
             patch('src.embedding_providers.ensure_embedding_model') as mock_ensure:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {
                "data": [{"id": "some-other-model"}]
            }
            mock_ensure.return_value = "nomic-embed-text-v1.5"

            provider = LMStudioProvider(auto_load_model=True)
            provider.is_available()

            # Model name should come from ensure_embedding_model
            assert provider.model_name == "nomic-embed-text-v1.5"

    def test_caches_model_name_without_auto_load(self):
        """Test model name is cached from server response when auto-load disabled."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {
                "data": [{"id": "nomic-embed-text-v1.5"}]
            }

            provider = LMStudioProvider(auto_load_model=False)
            provider.is_available()

            assert provider.model_name == "nomic-embed-text-v1.5"


# =============================================================================
# Tests for LMStudioProvider - Embedding
# =============================================================================


class TestLMStudioProviderEmbed:
    """Tests for LMStudioProvider.embed() and embed_batch().

    The embed() method calls the safe-model-load.sh gateway via subprocess.
    It writes text to a temp file, calls the gateway, and reads the response
    from a JSON file whose path is returned in the gateway's stdout.
    """

    def _mock_gateway_response(self, embedding, mock_subprocess, mock_open, mock_exists, mock_unlink):
        """Helper to set up mocks for gateway-based embedding."""
        import json
        from unittest.mock import mock_open as create_mock_open

        # Gateway returns FILE=/path/to/response.json
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "FILE=/tmp/response.json\n"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # File exists check
        mock_exists.return_value = True

        # Reading the response file
        response_json = json.dumps({"data": [{"embedding": embedding}]})
        mock_open.return_value.__enter__.return_value.read.return_value = response_json

        # Prevent cleanup errors
        mock_unlink.return_value = None

    def test_embed_single_text_success(self):
        """Test embedding single text returns vector."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getsize') as mock_getsize, \
             patch('os.unlink') as mock_unlink, \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            # Set up temp file mock
            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            # Gateway returns FILE path
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "FILE=/tmp/response.json\n"
            mock_subprocess.return_value = mock_result

            # Response file exists and has content
            mock_exists.return_value = True
            mock_getsize.return_value = 100  # Non-empty file

            # Set up file read to return JSON string
            response_data = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps(response_data)
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            result = provider.embed("test text")

            assert result == [0.1, 0.2, 0.3]

    def test_embed_batch_success(self):
        """Test batch embedding returns multiple vectors."""
        import json

        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        call_count = [0]

        def mock_file_read(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return json.dumps({"data": [{"embedding": embeddings[idx]}]})

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "FILE=/tmp/response.json\n"
            mock_subprocess.return_value = mock_result

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.side_effect = mock_file_read
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            results = provider.embed_batch(["text1", "text2", "text3"])

            assert len(results) == 3
            assert results[0] == [0.1, 0.2]
            assert results[1] == [0.3, 0.4]
            assert results[2] == [0.5, 0.6]

    def test_embed_batch_empty_list(self):
        """Test batch embedding with empty list returns empty."""
        provider = LMStudioProvider()
        results = provider.embed_batch([])
        assert results == []

    def test_embed_gateway_error(self):
        """Test embed raises error when gateway fails."""
        with patch('subprocess.run') as mock_subprocess, \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
             patch('os.unlink'):

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Gateway error: model not loaded"
            mock_subprocess.return_value = mock_result

            provider = LMStudioProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "Gateway failed" in str(exc_info.value)

    def test_embed_timeout(self):
        """Test embed raises error on subprocess timeout."""
        import subprocess

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("cmd", 60)) as mock_subprocess, \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
             patch('os.unlink'):

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            provider = LMStudioProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "timed out" in str(exc_info.value)

    def test_embed_gateway_not_found(self):
        """Test embed raises error when gateway script not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError("bash")), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
             patch('os.unlink'):

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            provider = LMStudioProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "not found" in str(exc_info.value).lower()

    def test_embed_response_with_error_field(self):
        """Test embed raises error when gateway response contains error."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "FILE=/tmp/response.json\n"
            mock_subprocess.return_value = mock_result

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"error": "Model not loaded"})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "Model not loaded" in str(exc_info.value)

    def test_embed_unexpected_response_format(self):
        """Test embed raises error on unexpected response format."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "FILE=/tmp/response.json\n"
            mock_subprocess.return_value = mock_result

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"unexpected": "format"})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "Unexpected response format" in str(exc_info.value)


# =============================================================================
# Tests for OllamaProvider - Initialization
# =============================================================================


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    def test_default_url(self):
        """Test default URL is localhost:11434."""
        provider = OllamaProvider()
        assert provider.url == "http://localhost:11434"

    def test_custom_url(self):
        """Test custom URL is used."""
        provider = OllamaProvider(url="http://custom:11434")
        assert provider.url == "http://custom:11434"

    def test_default_model(self):
        """Test default model is nomic-embed-text."""
        provider = OllamaProvider()
        assert provider._model == "nomic-embed-text"

    def test_custom_model(self):
        """Test custom model is used."""
        provider = OllamaProvider(model="all-minilm")
        assert provider._model == "all-minilm"

    def test_name_property(self):
        """Test name property returns 'Ollama'."""
        provider = OllamaProvider()
        assert provider.name == "Ollama"

    def test_model_name_property(self):
        """Test model_name returns the configured model."""
        provider = OllamaProvider(model="custom-model")
        assert provider.model_name == "custom-model"


# =============================================================================
# Tests for OllamaProvider - Availability
# =============================================================================


class TestOllamaProviderAvailability:
    """Tests for OllamaProvider.is_available()."""

    def test_available_when_model_exists(self):
        """Test returns True when model is available."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {
                "models": [
                    {"name": "nomic-embed-text:latest"},
                    {"name": "llama2:latest"},
                ]
            }

            provider = OllamaProvider()
            assert provider.is_available() is True

    def test_available_matches_model_without_tag(self):
        """Test matches model name without tag."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {
                "models": [{"name": "nomic-embed-text:v1.5"}]
            }

            provider = OllamaProvider(model="nomic-embed-text")
            assert provider.is_available() is True

    def test_unavailable_when_model_not_found(self):
        """Test returns False when model not available."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {
                "models": [{"name": "llama2:latest"}]
            }

            provider = OllamaProvider(model="nomic-embed-text")
            assert provider.is_available() is False

    def test_unavailable_when_no_models(self):
        """Test returns False when no models available."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {"models": []}

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_unavailable_when_connection_refused(self):
        """Test returns False when connection refused."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("")

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_unavailable_when_http_error(self):
        """Test returns False when HTTP error."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = False

            provider = OllamaProvider()
            assert provider.is_available() is False


# =============================================================================
# Tests for OllamaProvider - Embedding
# =============================================================================


class TestOllamaProviderEmbed:
    """Tests for OllamaProvider.embed() and embed_batch()."""

    def test_embed_success(self):
        """Test embedding returns vector."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.return_value.is_success = True
            mock_post.return_value.json.return_value = {
                "embedding": [0.1, 0.2, 0.3, 0.4]
            }

            provider = OllamaProvider()
            result = provider.embed("test text")

            assert result == [0.1, 0.2, 0.3, 0.4]

    def test_embed_sends_correct_payload(self):
        """Test embed sends correct model and prompt."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.return_value.is_success = True
            mock_post.return_value.json.return_value = {"embedding": [0.1]}

            provider = OllamaProvider(model="custom-model")
            provider.embed("test text")

            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "custom-model"
            assert call_args[1]["json"]["prompt"] == "test text"

    def test_embed_batch_calls_embed_for_each(self):
        """Test batch embedding calls embed for each text (Ollama doesn't support batch)."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.return_value.is_success = True
            mock_post.return_value.json.return_value = {"embedding": [0.1, 0.2]}

            provider = OllamaProvider()
            results = provider.embed_batch(["text1", "text2", "text3"])

            assert len(results) == 3
            assert mock_post.call_count == 3

    def test_embed_connection_error(self):
        """Test embed raises error on connection failure."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("")

            provider = OllamaProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "Cannot connect to Ollama" in str(exc_info.value)

    def test_embed_timeout_error(self):
        """Test embed raises error on timeout."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("")

            provider = OllamaProvider(timeout=30)

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "timed out" in str(exc_info.value)

    def test_embed_http_error(self):
        """Test embed raises error on HTTP error."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.return_value.is_success = False
            mock_post.return_value.status_code = 404
            mock_post.return_value.text = "Model not found"

            provider = OllamaProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "404" in str(exc_info.value)

    def test_embed_api_error_response(self):
        """Test embed raises error when API returns error."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.return_value.is_success = True
            mock_post.return_value.json.return_value = {
                "error": "model 'nomic-embed-text' not found"
            }

            provider = OllamaProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "not found" in str(exc_info.value)

    def test_embed_missing_embedding_field(self):
        """Test embed raises error when embedding field missing."""
        with patch('src.embedding_providers.httpx.post') as mock_post:
            mock_post.return_value.is_success = True
            mock_post.return_value.json.return_value = {
                "model": "nomic-embed-text"
                # Missing "embedding" field
            }

            provider = OllamaProvider()

            with pytest.raises(EmbeddingProviderError) as exc_info:
                provider.embed("test")

            assert "missing 'embedding'" in str(exc_info.value)


# =============================================================================
# Tests for EmbeddingProviderManager - Initialization
# =============================================================================


class TestEmbeddingProviderManagerInit:
    """Tests for EmbeddingProviderManager initialization."""

    def test_creates_default_providers(self):
        """Test manager creates LM Studio and Ollama providers."""
        manager = EmbeddingProviderManager()
        # Just checking keys exist - no network calls
        assert "lm_studio" in manager._providers
        assert "ollama" in manager._providers

    def test_accepts_preferred_provider(self):
        """Test manager accepts preferred provider."""
        manager = EmbeddingProviderManager(preferred_provider="ollama")
        assert manager._preferred == "ollama"


# =============================================================================
# Tests for EmbeddingProviderManager - Provider Selection
# =============================================================================


class TestEmbeddingProviderManagerSelection:
    """Tests for EmbeddingProviderManager.get_provider()."""

    def test_returns_first_available_provider(self):
        """Test returns first available provider when no preference."""
        manager = EmbeddingProviderManager()

        # Mock LM Studio as available
        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = True
        manager._providers["lm_studio"].name = "LM Studio"

        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False

        provider = manager.get_provider()
        assert provider.name == "LM Studio"

    def test_returns_preferred_provider_when_available(self):
        """Test returns preferred provider when available."""
        manager = EmbeddingProviderManager(preferred_provider="ollama")

        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = True

        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = True
        manager._providers["ollama"].name = "Ollama"

        provider = manager.get_provider()
        assert provider.name == "Ollama"

    def test_raises_when_preferred_unavailable(self):
        """Test raises error when preferred provider unavailable."""
        manager = EmbeddingProviderManager(preferred_provider="ollama")

        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = True

        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False
        manager._providers["ollama"].name = "Ollama"

        with pytest.raises(NoProviderAvailableError) as exc_info:
            manager.get_provider()

        assert "ollama" in str(exc_info.value)

    def test_raises_when_no_provider_available(self):
        """Test raises error when no provider available."""
        manager = EmbeddingProviderManager()

        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = False

        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False

        with pytest.raises(NoProviderAvailableError) as exc_info:
            manager.get_provider()

        assert "No embedding provider available" in str(exc_info.value)

    def test_caches_active_provider(self):
        """Test caches active provider for subsequent calls."""
        manager = EmbeddingProviderManager()

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        manager._providers["lm_studio"] = mock_provider
        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False

        # First call
        provider1 = manager.get_provider()
        # Second call
        provider2 = manager.get_provider()

        assert provider1 is provider2
        # is_available should be called twice (once per get_provider)
        assert mock_provider.is_available.call_count == 2

    def test_reselects_if_cached_becomes_unavailable(self):
        """Test reselects provider if cached one becomes unavailable."""
        manager = EmbeddingProviderManager()

        mock_lm = MagicMock()
        mock_lm.is_available.return_value = True
        mock_lm.name = "LM Studio"

        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_ollama.name = "Ollama"

        manager._providers["lm_studio"] = mock_lm
        manager._providers["ollama"] = mock_ollama

        # First call - LM Studio is available
        provider1 = manager.get_provider()
        assert provider1.name == "LM Studio"

        # LM Studio becomes unavailable, Ollama becomes available
        mock_lm.is_available.return_value = False
        mock_ollama.is_available.return_value = True

        # Second call - should switch to Ollama
        provider2 = manager.get_provider()
        assert provider2.name == "Ollama"


# =============================================================================
# Tests for EmbeddingProviderManager - List Available
# =============================================================================


class TestEmbeddingProviderManagerListAvailable:
    """Tests for EmbeddingProviderManager.list_available()."""

    def test_lists_all_available(self):
        """Test lists all available providers."""
        manager = EmbeddingProviderManager()

        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = True

        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = True

        available = manager.list_available()
        assert "lm_studio" in available
        assert "ollama" in available

    def test_lists_only_available(self):
        """Test lists only available providers."""
        manager = EmbeddingProviderManager()

        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = True

        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False

        available = manager.list_available()
        assert available == ["lm_studio"]

    def test_returns_empty_when_none_available(self):
        """Test returns empty list when no providers available."""
        manager = EmbeddingProviderManager()

        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = False

        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False

        available = manager.list_available()
        assert available == []


# =============================================================================
# Tests for EmbeddingProviderManager - Add Provider
# =============================================================================


class TestEmbeddingProviderManagerAddProvider:
    """Tests for EmbeddingProviderManager.add_provider()."""

    def test_adds_custom_provider(self):
        """Test adding a custom provider."""
        manager = EmbeddingProviderManager()

        # Mock the default providers to prevent network calls
        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = False
        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False

        custom_provider = MagicMock(spec=EmbeddingProvider)
        custom_provider.is_available.return_value = True
        custom_provider.name = "Custom"

        manager.add_provider("custom", custom_provider)

        assert "custom" in manager._providers
        assert "custom" in manager.list_available()

    def test_custom_provider_can_be_selected(self):
        """Test custom provider can be selected."""
        manager = EmbeddingProviderManager(preferred_provider="custom")

        # Mock the default providers to prevent network calls
        manager._providers["lm_studio"] = MagicMock()
        manager._providers["lm_studio"].is_available.return_value = False
        manager._providers["ollama"] = MagicMock()
        manager._providers["ollama"].is_available.return_value = False

        custom_provider = MagicMock(spec=EmbeddingProvider)
        custom_provider.is_available.return_value = True
        custom_provider.name = "Custom"

        manager.add_provider("custom", custom_provider)

        provider = manager.get_provider()
        assert provider.name == "Custom"


# =============================================================================
# Tests for Edge Cases
# =============================================================================


class TestEmbeddingProviderEdgeCases:
    """Tests for edge cases in embedding providers."""

    def _setup_gateway_mock(self, embedding):
        """Helper to create gateway mock context."""
        return {
            'subprocess_mock': MagicMock(returncode=0, stdout="FILE=/tmp/response.json\n"),
            'response': {"data": [{"embedding": embedding}]}
        }

    def test_embed_empty_string(self):
        """Test embedding empty string."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_subprocess.return_value = MagicMock(returncode=0, stdout="FILE=/tmp/r.json\n")

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"data": [{"embedding": [0.0] * 384}]})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            result = provider.embed("")

            assert len(result) == 384

    def test_embed_unicode_text(self):
        """Test embedding unicode text."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_subprocess.return_value = MagicMock(returncode=0, stdout="FILE=/tmp/r.json\n")

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"data": [{"embedding": [0.1, 0.2]}]})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            result = provider.embed("Hello 世界 🌍 مرحبا")

            assert result == [0.1, 0.2]

    def test_embed_very_long_text(self):
        """Test embedding very long text (provider should handle truncation)."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_subprocess.return_value = MagicMock(returncode=0, stdout="FILE=/tmp/r.json\n")

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"data": [{"embedding": [0.1]}]})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            long_text = "x" * 100000
            result = provider.embed(long_text)

            assert result == [0.1]

    def test_embed_special_characters(self):
        """Test embedding text with special characters."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_subprocess.return_value = MagicMock(returncode=0, stdout="FILE=/tmp/r.json\n")

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"data": [{"embedding": [0.1]}]})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            result = provider.embed('Text with "quotes" and \n newlines \t tabs')

            assert result == [0.1]

    def test_embed_batch_single_item(self):
        """Test batch embedding with single item."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_subprocess.return_value = MagicMock(returncode=0, stdout="FILE=/tmp/r.json\n")

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"data": [{"embedding": [0.1, 0.2]}]})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            results = provider.embed_batch(["single"])

            assert len(results) == 1
            assert results[0] == [0.1, 0.2]

    def test_provider_recovers_after_transient_error(self):
        """Test provider can recover after transient error."""
        import subprocess as sp
        import json

        call_count = [0]

        def subprocess_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise sp.TimeoutExpired("cmd", 60)
            return MagicMock(returncode=0, stdout="FILE=/tmp/r.json\n")

        with patch('subprocess.run', side_effect=subprocess_side_effect), \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"data": [{"embedding": [0.1]}]})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()

            # First call should fail
            with pytest.raises(EmbeddingProviderError):
                provider.embed("test")

            # Second call should succeed
            result = provider.embed("test")
            assert result == [0.1]


# =============================================================================
# Tests for Model Manager Integration
# =============================================================================


class TestModelManagerIntegration:
    """Tests for model manager integration with LMStudioProvider.

    Note: The embed() method now uses the gateway script which handles model
    loading internally. These tests focus on is_available() behavior which
    still uses the model manager directly.
    """

    def test_is_available_calls_ensure_embedding_model(self, mock_model_manager):
        """Test is_available calls ensure_embedding_model when auto_load enabled."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {"data": [{"id": "model"}]}

            provider = LMStudioProvider(auto_load_model=True)
            provider.is_available()

            mock_model_manager.assert_called_once()

    def test_is_available_skips_model_manager_when_disabled(self, mock_model_manager):
        """Test is_available skips model manager when auto_load disabled."""
        with patch('src.embedding_providers.httpx.get') as mock_get:
            mock_get.return_value.is_success = True
            mock_get.return_value.json.return_value = {"data": [{"id": "model"}]}

            provider = LMStudioProvider(auto_load_model=False)
            provider.is_available()

            mock_model_manager.assert_not_called()

    def test_embed_uses_gateway_not_direct_api(self):
        """Test embed uses subprocess gateway instead of direct httpx calls."""
        import json

        with patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', new_callable=MagicMock) as mock_open, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('os.unlink'), \
             patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
             patch('src.embedding_providers.httpx.post') as mock_httpx:

            mock_temp = MagicMock()
            mock_temp.__enter__.return_value.name = "/tmp/input.txt"
            mock_tempfile.return_value = mock_temp

            mock_subprocess.return_value = MagicMock(returncode=0, stdout="FILE=/tmp/r.json\n")

            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = json.dumps({"data": [{"embedding": [0.1]}]})
            mock_open.return_value = mock_file

            provider = LMStudioProvider()
            provider.embed("test")

            # Gateway subprocess should be called
            mock_subprocess.assert_called_once()
            # Direct httpx should NOT be called for embed
            mock_httpx.assert_not_called()
