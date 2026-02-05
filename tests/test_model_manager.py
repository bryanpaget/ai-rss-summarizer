"""Tests for model_manager.py - LM Studio model loading/unloading.

Tests cover:
- Configuration loading
- Model availability detection
- Model loading/unloading logic
- Request type handling (text, vision, embedding)
- Error handling
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import httpx

from src.model_manager import (
    ModelConfig,
    ModelManager,
    ModelManagerError,
    LMStudioNotReachableError,
    ModelLoadError,
    ModelUnloadError,
    get_model_manager,
    ensure_embedding_model,
    ensure_text_model,
    ensure_vision_model,
)


# =============================================================================
# Tests for ModelConfig
# =============================================================================


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_config_from_dict(self):
        """Test creating config from dict-like values."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
            ttl_seconds=300,
        )
        assert config.text_model == "text-model"
        assert config.vision_model == "vision-model"
        assert config.embedding_model == "embedding-model"
        assert config.ttl_seconds == 300

    def test_config_defaults(self):
        """Test config default values."""
        config = ModelConfig(
            text_model="text",
            vision_model="vision",
            embedding_model="embedding",
        )
        assert config.ttl_seconds == 300
        assert config.text_temperature == 0.7
        assert config.vision_temperature == 0.0

    def test_config_from_file(self, tmp_path):
        """Test loading config from file."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "text_model": "google/gemma-3n",
            "vision_model": "qwen/qwen3-vl",
            "embedding_model": "Qwen/Qwen3-Embedding",
            "ttl_seconds": 600,
        }))

        config = ModelConfig.from_file(config_file)

        assert config.text_model == "google/gemma-3n"
        assert config.vision_model == "qwen/qwen3-vl"
        assert config.embedding_model == "Qwen/Qwen3-Embedding"
        assert config.ttl_seconds == 600

    def test_config_creates_default_if_missing(self, tmp_path, monkeypatch):
        """Test creates default config if file doesn't exist."""
        # Change to tmp_path so project-local path works
        monkeypatch.chdir(tmp_path)

        config = ModelConfig.from_file()

        # Should create config/model_config.json
        assert (tmp_path / "config" / "model_config.json").exists()
        # Should return empty config
        assert config.text_model == ""
        assert config.embedding_model == ""


# =============================================================================
# Tests for ModelManager - Initialization
# =============================================================================


class TestModelManagerInit:
    """Tests for ModelManager initialization."""

    def test_lazy_config_loading(self):
        """Test config is loaded lazily."""
        manager = ModelManager()
        # Config not loaded yet
        assert manager._config is None
        assert manager._config_loaded is False

    def test_explicit_config(self):
        """Test explicit config is used."""
        config = ModelConfig(
            text_model="text",
            vision_model="vision",
            embedding_model="embedding",
        )
        manager = ModelManager(config=config)

        assert manager._config is config
        assert manager._config_loaded is True


# =============================================================================
# Tests for ModelManager - LM Studio Detection
# =============================================================================


class TestModelManagerLMStudioDetection:
    """Tests for LM Studio reachability checking."""

    def test_check_lm_studio_available(self):
        """Test LM Studio detected when reachable."""
        config = ModelConfig(
            text_model="text",
            vision_model="vision",
            embedding_model="embedding",
        )
        manager = ModelManager(config=config)

        with patch.object(httpx, 'get') as mock_get:
            mock_get.return_value.is_success = True

            assert manager.check_lm_studio() is True

    def test_check_lm_studio_unavailable(self):
        """Test LM Studio not detected when unreachable."""
        config = ModelConfig(
            text_model="text",
            vision_model="vision",
            embedding_model="embedding",
        )
        manager = ModelManager(config=config)

        with patch.object(httpx, 'get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("")

            assert manager.check_lm_studio() is False


# =============================================================================
# Tests for ModelManager - Get Loaded Model
# =============================================================================


class TestModelManagerGetLoadedModel:
    """Tests for getting currently loaded model."""

    def test_get_loaded_model_via_lms_command(self):
        """Test getting loaded model via lms command."""
        config = ModelConfig(
            text_model="text",
            vision_model="vision",
            embedding_model="embedding",
        )
        manager = ModelManager(config=config)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps([
                {"path": "test-model", "identifier": "test-id"}
            ])

            result = manager.get_loaded_model()

            assert result == "test-model"

    def test_get_loaded_model_fallback_to_api(self):
        """Test fallback to API when lms command unavailable."""
        config = ModelConfig(
            text_model="text",
            vision_model="vision",
            embedding_model="embedding",
        )
        manager = ModelManager(config=config)

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with patch.object(httpx, 'get') as mock_get:
                mock_get.return_value.is_success = True
                mock_get.return_value.json.return_value = {
                    "data": [{"id": "api-model"}]
                }

                result = manager.get_loaded_model()

                assert result == "api-model"

    def test_get_loaded_model_none_loaded(self):
        """Test returns None when no model loaded."""
        config = ModelConfig(
            text_model="text",
            vision_model="vision",
            embedding_model="embedding",
        )
        manager = ModelManager(config=config)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "[]"

            with patch.object(httpx, 'get') as mock_get:
                mock_get.return_value.is_success = True
                mock_get.return_value.json.return_value = {"data": []}

                result = manager.get_loaded_model()

                assert result is None


# =============================================================================
# Tests for ModelManager - Model Type Detection
# =============================================================================


class TestModelManagerModelType:
    """Tests for model type detection."""

    def test_get_model_type_embedding(self):
        """Test embedding model type detected."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        assert manager.get_model_type("embedding-model") == "embedding"

    def test_get_model_type_text(self):
        """Test text model type detected."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        assert manager.get_model_type("text-model") == "text"

    def test_get_model_type_vision(self):
        """Test vision model type detected."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        assert manager.get_model_type("vision-model") == "vision"

    def test_get_model_type_unknown(self):
        """Test unknown model returns None."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        assert manager.get_model_type("unknown-model") is None

    def test_get_model_type_empty(self):
        """Test empty model returns None."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        assert manager.get_model_type("") is None


# =============================================================================
# Tests for ModelManager - Ensure Model for Request
# =============================================================================


class TestModelManagerEnsureModel:
    """Tests for ensure_model_for_request."""

    def test_ensure_embedding_model_when_none_loaded(self):
        """Test loads embedding model when none loaded."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=True):
            with patch.object(manager, 'get_loaded_model', return_value=None):
                with patch.object(manager, 'load_model') as mock_load:
                    result = manager.ensure_model_for_request("embedding")

                    mock_load.assert_called_once_with("embedding-model")
                    assert result == "embedding-model"

    def test_ensure_embedding_model_already_loaded(self):
        """Test no switch when correct model already loaded."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=True):
            with patch.object(manager, 'get_loaded_model', return_value="embedding-model"):
                with patch.object(manager, 'load_model') as mock_load:
                    result = manager.ensure_model_for_request("embedding")

                    mock_load.assert_not_called()
                    assert result == "embedding-model"

    def test_ensure_embedding_model_switches_from_text(self):
        """Test switches from text model to embedding model."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=True):
            with patch.object(manager, 'get_loaded_model', return_value="text-model"):
                with patch.object(manager, 'get_loaded_model_identifier', return_value="text-id"):
                    with patch.object(manager, 'unload_model') as mock_unload:
                        with patch.object(manager, 'wait_for_unload', return_value=True):
                            with patch.object(manager, 'load_model') as mock_load:
                                result = manager.ensure_model_for_request("embedding")

                                mock_unload.assert_called_once_with("text-id")
                                mock_load.assert_called_once_with("embedding-model")

    def test_ensure_text_model_uses_vision_model(self):
        """Test text request can use vision model without switching."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=True):
            with patch.object(manager, 'get_loaded_model', return_value="vision-model"):
                with patch.object(manager, 'load_model') as mock_load:
                    result = manager.ensure_model_for_request("text")

                    mock_load.assert_not_called()
                    assert result == "vision-model"

    def test_ensure_text_model_switches_from_embedding(self):
        """Test text request switches away from embedding model."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=True):
            with patch.object(manager, 'get_loaded_model', return_value="embedding-model"):
                with patch.object(manager, 'get_loaded_model_identifier', return_value="emb-id"):
                    with patch.object(manager, 'unload_model'):
                        with patch.object(manager, 'wait_for_unload', return_value=True):
                            with patch.object(manager, 'load_model') as mock_load:
                                manager.ensure_model_for_request("text")

                                mock_load.assert_called_once_with("text-model")

    def test_ensure_model_raises_when_lm_studio_unreachable(self):
        """Test raises error when LM Studio unreachable."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=False):
            with pytest.raises(LMStudioNotReachableError):
                manager.ensure_model_for_request("embedding")

    def test_ensure_model_raises_for_unknown_type(self):
        """Test raises error for unknown request type."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="embedding-model",
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=True):
            with patch.object(manager, 'get_loaded_model', return_value=None):
                with pytest.raises(ModelManagerError) as exc_info:
                    manager.ensure_model_for_request("unknown")

                assert "Unknown request type" in str(exc_info.value)

    def test_ensure_model_raises_when_no_model_configured(self):
        """Test raises error when target model not configured."""
        config = ModelConfig(
            text_model="text-model",
            vision_model="vision-model",
            embedding_model="",  # Not configured
        )
        manager = ModelManager(config=config)

        with patch.object(manager, 'check_lm_studio', return_value=True):
            with patch.object(manager, 'get_loaded_model', return_value=None):
                with pytest.raises(ModelManagerError) as exc_info:
                    manager.ensure_model_for_request("embedding")

                assert "No model configured" in str(exc_info.value)


# =============================================================================
# Tests for Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_model_manager_singleton(self):
        """Test get_model_manager returns singleton."""
        # Reset singleton
        import src.model_manager as mm
        mm._manager = None

        manager1 = get_model_manager()
        manager2 = get_model_manager()

        assert manager1 is manager2

    def test_ensure_embedding_model_calls_manager(self):
        """Test ensure_embedding_model delegates to manager."""
        with patch('src.model_manager.get_model_manager') as mock_get:
            mock_manager = MagicMock()
            mock_manager.ensure_model_for_request.return_value = "embedding-model"
            mock_get.return_value = mock_manager

            result = ensure_embedding_model()

            mock_manager.ensure_model_for_request.assert_called_once_with("embedding")
            assert result == "embedding-model"

    def test_ensure_text_model_calls_manager(self):
        """Test ensure_text_model delegates to manager."""
        with patch('src.model_manager.get_model_manager') as mock_get:
            mock_manager = MagicMock()
            mock_manager.ensure_model_for_request.return_value = "text-model"
            mock_get.return_value = mock_manager

            result = ensure_text_model()

            mock_manager.ensure_model_for_request.assert_called_once_with("text")
            assert result == "text-model"

    def test_ensure_vision_model_calls_manager(self):
        """Test ensure_vision_model delegates to manager."""
        with patch('src.model_manager.get_model_manager') as mock_get:
            mock_manager = MagicMock()
            mock_manager.ensure_model_for_request.return_value = "vision-model"
            mock_get.return_value = mock_manager

            result = ensure_vision_model()

            mock_manager.ensure_model_for_request.assert_called_once_with("vision")
            assert result == "vision-model"
