"""LM Studio model manager for automatic model loading/unloading.

Recreates the relevant parts of safe-model-load.sh for Python use.
Ensures the correct model is loaded before making embedding/text/vision requests.

NO FALLBACKS. If model management fails, operations fail loudly.
"""

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal

import httpx


class ModelManagerError(Exception):
    """Raised when model management fails."""
    pass


class LMStudioNotReachableError(ModelManagerError):
    """Raised when LM Studio server is not reachable."""
    pass


class ModelLoadError(ModelManagerError):
    """Raised when model loading fails."""
    pass


class ModelUnloadError(ModelManagerError):
    """Raised when model unloading fails."""
    pass


@dataclass
class ModelConfig:
    """Configuration for model management."""
    text_model: str
    vision_model: str
    embedding_model: str
    ttl_seconds: int = 300
    text_temperature: float = 0.7
    vision_temperature: float = 0.0

    @classmethod
    def from_file(cls, config_path: Optional[Path] = None) -> "ModelConfig":
        """Load configuration from project-local config file.

        Looks for config in this order:
        1. Explicit path if provided
        2. config/model_config.json (project-local)
        3. Creates default config if not found
        """
        if config_path is None:
            # Project-local config
            config_path = Path("config/model_config.json")

        if not config_path.exists():
            # Create default config for the project
            return cls.create_default(config_path)

        with open(config_path) as f:
            data = json.load(f)

        return cls(
            text_model=data.get("text_model", ""),
            vision_model=data.get("vision_model", ""),
            embedding_model=data.get("embedding_model", ""),
            ttl_seconds=int(data.get("ttl_seconds", 300)),
            text_temperature=float(data.get("text_temperature", 0.7)),
            vision_temperature=float(data.get("vision_temperature", 0.0)),
        )

    @classmethod
    def create_default(cls, config_path: Path) -> "ModelConfig":
        """Create default config file and return config object.

        Users should edit this file to specify their model paths.
        """
        default_config = {
            "text_model": "",
            "vision_model": "",
            "embedding_model": "",
            "ttl_seconds": 300,
            "text_temperature": 0.7,
            "vision_temperature": 0.0,
            "_comment": "Configure your LM Studio model paths here. Run 'lms ls' to see available models."
        }

        # Create config directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)

        return cls(
            text_model="",
            vision_model="",
            embedding_model="",
        )


RequestType = Literal["text", "vision", "embedding"]


class ModelManager:
    """Manages LM Studio model loading/unloading.

    Ensures the correct model type is loaded before requests.
    """

    LM_STUDIO_URL = "http://localhost:1234/v1"
    LMS_COMMAND = "lms"

    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the model manager.

        Args:
            config: Model configuration. If None, loads from default location.
        """
        self._config = config
        self._config_loaded = config is not None

    @property
    def config(self) -> ModelConfig:
        """Lazy-load configuration."""
        if not self._config_loaded:
            self._config = ModelConfig.from_file()
            self._config_loaded = True
        return self._config

    def _has_lms_command(self) -> bool:
        """Check if 'lms' command is available."""
        try:
            # Use 'lms help' since --version is not a valid flag
            result = subprocess.run(
                [self.LMS_COMMAND, "help"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def check_lm_studio(self) -> bool:
        """Check if LM Studio server is reachable."""
        try:
            resp = httpx.get(
                f"{self.LM_STUDIO_URL}/models",
                timeout=5,
            )
            return resp.is_success
        except (httpx.RequestError, httpx.TimeoutException) as e:
            import sys
            print(f"LM Studio not reachable: {e}", file=sys.stderr)
            return False
        except Exception as e:
            import sys
            print(f"Error checking LM Studio: {e}", file=sys.stderr)
            return False

    def get_loaded_model(self) -> Optional[str]:
        """Get the currently loaded model path/identifier.

        Returns:
            Model path if a model is loaded, None otherwise.
        """
        if self._has_lms_command():
            try:
                result = subprocess.run(
                    [self.LMS_COMMAND, "ps", "--json"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    if data and len(data) > 0:
                        return data[0].get("path", "").strip()
            except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                import sys
                print(f"Error getting loaded model via lms: {e}", file=sys.stderr)
            except Exception as e:
                import sys
                print(f"Error getting loaded model via lms: {e}", file=sys.stderr)

        # Fallback to API
        try:
            resp = httpx.get(
                f"{self.LM_STUDIO_URL}/models",
                timeout=5,
            )
            if resp.is_success:
                data = resp.json()
                if data.get("data"):
                    return data["data"][0].get("id", "")
        except (httpx.RequestError, httpx.TimeoutException) as e:
            import sys
            print(f"LM Studio API not reachable: {e}", file=sys.stderr)
        except Exception as e:
            import sys
            print(f"Error getting loaded model via API: {e}", file=sys.stderr)

        return None

    def get_loaded_model_identifier(self) -> Optional[str]:
        """Get the model identifier (for unloading)."""
        if self._has_lms_command():
            try:
                result = subprocess.run(
                    [self.LMS_COMMAND, "ps", "--json"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    if data and len(data) > 0:
                        return data[0].get("identifier", "").strip()
            except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                import sys
                print(f"Error getting model identifier via lms: {e}", file=sys.stderr)
            except Exception as e:
                import sys
                print(f"Error getting model identifier via lms: {e}", file=sys.stderr)

        # Fallback: use model path as identifier
        return self.get_loaded_model()

    def get_model_type(self, model_path: str) -> Optional[RequestType]:
        """Determine the type of a model based on config."""
        if not model_path:
            return None

        if model_path == self.config.embedding_model:
            return "embedding"
        elif model_path == self.config.vision_model:
            return "vision"
        elif model_path == self.config.text_model:
            return "text"

        return None

    def unload_model(self, identifier: str) -> None:
        """Unload the specified model.

        Args:
            identifier: Model identifier to unload.

        Raises:
            ModelUnloadError: If unloading fails.
        """
        if not self._has_lms_command():
            raise ModelUnloadError(
                "Cannot unload model: 'lms' command not available.\n"
                "Please install LM Studio CLI or manually unload the model."
            )

        try:
            result = subprocess.run(
                [self.LMS_COMMAND, "unload", identifier],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            # lms unload may return non-zero even on success
        except subprocess.TimeoutExpired:
            raise ModelUnloadError(f"Timeout waiting to unload model: {identifier}")

    def wait_for_unload(self, max_wait: int = 30) -> bool:
        """Wait for model to be fully unloaded.

        Args:
            max_wait: Maximum seconds to wait.

        Returns:
            True if model unloaded, False if timeout.
        """
        for _ in range(max_wait):
            loaded = self.get_loaded_model()
            if not loaded:
                return True
            time.sleep(1)

        return False

    def load_model(self, model_path: str) -> None:
        """Load a model into LM Studio.

        Args:
            model_path: Path to the model to load.

        Raises:
            ModelLoadError: If loading fails.
        """
        if not self._has_lms_command():
            raise ModelLoadError(
                "Cannot load model: 'lms' command not available.\n"
                "Please install LM Studio CLI or manually load the model."
            )

        try:
            result = subprocess.run(
                [
                    self.LMS_COMMAND,
                    "load",
                    model_path,
                    "--ttl",
                    str(self.config.ttl_seconds),
                    "--yes",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,  # Model loading can take time
            )

            if result.returncode != 0:
                raise ModelLoadError(
                    f"Failed to load model: {model_path}\n"
                    f"Error: {result.stderr}"
                )

            # Wait for model to be ready
            time.sleep(2)

        except subprocess.TimeoutExpired:
            raise ModelLoadError(f"Timeout loading model: {model_path}")

    def ensure_model_for_request(self, request_type: RequestType) -> str:
        """Ensure the correct model is loaded for the request type.

        This is the main entry point. Call this before making any LLM request.

        Args:
            request_type: Type of request ("text", "vision", or "embedding").

        Returns:
            The model path that is now loaded.

        Raises:
            LMStudioNotReachableError: If LM Studio is not running.
            ModelManagerError: If model switching fails.
        """
        if not self.check_lm_studio():
            raise LMStudioNotReachableError(
                "LM Studio is not reachable.\n"
                "Check that LM Studio is running and the server toggle is ON."
            )

        current = self.get_loaded_model()

        # Determine target model
        if request_type == "embedding":
            target_model = self.config.embedding_model
        elif request_type == "vision":
            target_model = self.config.vision_model
        elif request_type == "text":
            target_model = self.config.text_model
        else:
            raise ModelManagerError(f"Unknown request type: {request_type}")

        if not target_model:
            raise ModelManagerError(
                f"No model configured for type: {request_type}\n"
                "Check ~/.claude/config/safe-auto-load.json"
            )

        # Determine if we need to switch
        need_switch = False

        if not current:
            need_switch = True
        elif current == target_model:
            need_switch = False
        elif request_type == "text":
            # Text requests can use vision model or any non-embedding model
            current_type = self.get_model_type(current)
            if current_type != "embedding":
                need_switch = False
            else:
                need_switch = True
        else:
            need_switch = True

        if need_switch:
            # Unload current if present
            if current:
                identifier = self.get_loaded_model_identifier()
                if identifier:
                    self.unload_model(identifier)
                    if not self.wait_for_unload():
                        raise ModelUnloadError(
                            f"Timeout waiting for model to unload: {current}"
                        )

            # Load target
            self.load_model(target_model)
            return target_model

        return current or target_model


# Module-level singleton for convenience
_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get the singleton model manager instance."""
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager


def ensure_embedding_model() -> str:
    """Convenience function to ensure embedding model is loaded.

    Returns:
        The model path that is now loaded.
    """
    return get_model_manager().ensure_model_for_request("embedding")


def ensure_text_model() -> str:
    """Convenience function to ensure text model is loaded.

    Returns:
        The model path that is now loaded.
    """
    return get_model_manager().ensure_model_for_request("text")


def ensure_vision_model() -> str:
    """Convenience function to ensure vision model is loaded.

    Returns:
        The model path that is now loaded.
    """
    return get_model_manager().ensure_model_for_request("vision")
