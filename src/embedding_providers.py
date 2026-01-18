"""Embedding providers for semantic similarity.

Supports multiple embedding backends:
- LM Studio (OpenAI-compatible API at localhost:1234)
- Ollama (native API at localhost:11434)

NO FALLBACKS. If no provider is available, operations fail loudly.

Model loading is handled by the gateway module - all requests go through
src/gateway.py which coordinates with safe-model-load.sh.
"""

import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class EmbeddingProviderError(Exception):
    """Raised when embedding provider fails."""
    pass


class NoProviderAvailableError(EmbeddingProviderError):
    """Raised when no embedding provider is available."""
    pass


@dataclass
class ProviderConfig:
    """Configuration for an embedding provider."""
    url: str
    model: str
    timeout: int = 60


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is reachable and ready."""
        ...

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingProviderError: If embedding fails
        """
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingProviderError: If embedding fails
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging/display."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model being used."""
        ...


class LMStudioProvider(EmbeddingProvider):
    """LM Studio embedding provider.

    Uses OpenAI-compatible API at localhost:1234.
    Uses ModelManager to ensure embedding model is loaded before requests.
    """

    DEFAULT_URL = "http://localhost:1234/v1"

    def __init__(
        self,
        url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        auto_load_model: bool = True,
    ):
        self.url = url or self.DEFAULT_URL
        self._model = model  # If None, will auto-detect
        self.timeout = timeout
        self._cached_model: Optional[str] = None
        self._auto_load_model = auto_load_model

    @property
    def name(self) -> str:
        return "LM Studio"

    @property
    def model_name(self) -> str:
        if self._model:
            return self._model
        if self._cached_model:
            return self._cached_model
        # Try to detect loaded model
        try:
            resp = httpx.get(
                f"{self.url}/models",
                timeout=5,
            )
            if resp.is_success:
                data = resp.json()
                if data.get("data"):
                    self._cached_model = data["data"][0].get("id", "unknown")
                    return self._cached_model
        except (httpx.RequestError, httpx.TimeoutException) as e:
            import sys
            print(f"LM Studio not reachable when getting model name: {e}", file=sys.stderr)
        except Exception as e:
            import sys
            print(f"Error getting LM Studio model name: {e}", file=sys.stderr)
        return "unknown"

    def is_available(self) -> bool:
        """Check if LM Studio is running.

        NOTE: Model loading is handled by the gateway - this just checks connectivity.
        The gateway will automatically load the correct model when embed requests are made.
        """
        try:
            resp = httpx.get(
                f"{self.url}/models",
                timeout=5,
            )
            if not resp.is_success:
                return False

            # LM Studio is running - we're good
            # The gateway handles model loading when requests are made
            return True
        except (httpx.RequestError, httpx.TimeoutException) as e:
            import sys
            print(f"LM Studio not reachable: {e}", file=sys.stderr)
            return False
        except Exception as e:
            import sys
            print(f"Error checking LM Studio availability: {e}", file=sys.stderr)
            return False

    # Git Bash path - required on Windows because:
    # - Python subprocess finds WSL bash first (C:\Windows\System32\bash.exe)
    # - WSL uses /mnt/c/ paths, Git Bash uses /c/ paths
    # - The gateway script is written for Git Bash/MSYS path format
    GIT_BASH = "C:/Program Files/Git/usr/bin/bash.exe"

    def _win_to_msys_path(self, win_path: str) -> str:
        """Convert Windows path to MSYS/Git Bash path.

        Windows: C:\\Users\\jpswi\\file.txt
        MSYS:    /c/Users/jpswi/file.txt

        IMPORTANT: On Windows, Python's subprocess finds WSL bash before Git Bash.
        WSL uses /mnt/c/ paths which won't work with our scripts.
        Always use GIT_BASH constant for subprocess calls.
        """
        import os
        if os.name != 'nt':
            return win_path
        # Convert backslashes to forward slashes
        path = win_path.replace('\\', '/')
        # Convert drive letter: C:/ -> /c/
        if len(path) >= 2 and path[1] == ':':
            path = '/' + path[0].lower() + path[2:]
        return path

    def _msys_to_win_path(self, msys_path: str) -> str:
        """Convert MSYS/Git Bash path to Windows path.

        MSYS:    /c/Users/jpswi/file.txt
        Windows: C:/Users/jpswi/file.txt
        """
        if msys_path.startswith('/') and len(msys_path) >= 3 and msys_path[2] == '/':
            return msys_path[1].upper() + ':' + msys_path[2:]
        return msys_path

    def embed(self, text: str) -> list[float]:
        """Generate embedding using the gateway.

        The gateway handles:
        - Model auto-loading (loads embedding model if needed)
        - Queue management and batching by type
        - Model switching coordination

        NO FALLBACKS - gateway is required, fail loudly if unavailable.
        """
        from .gateway import get_gateway

        gateway = get_gateway()
        if not gateway.is_available():
            raise EmbeddingProviderError(
                "Gateway not available. LM Studio must be running.\n"
                "Start LM Studio and ensure it's listening on localhost:1234"
            )
        return gateway.request_embedding(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in ONE API call.

        Uses TRUE server-side batching - sends all texts in a single request
        to the /v1/embeddings endpoint with input as an array.

        This is CRITICAL for performance:
        - Gateway subprocess calls: ~7s overhead PER text
        - Direct batch API call: ONE call for ALL texts

        The embedding model must already be loaded. If not loaded,
        make one gateway.request_embedding() call first to trigger model loading.
        """
        if not texts:
            return []

        # TRUE batch API call directly to LM Studio
        # No gateway overhead - just one HTTP request with array input
        #
        # IMPORTANT: The embedding model must be loaded in LM Studio.
        # If not loaded, this will fail. Use the pipeline's pre-embedding
        # phase which calls gateway.request_embedding() once to trigger
        # model loading before batch operations.
        try:
            response = httpx.post(
                f"{self.url}/embeddings",
                json={
                    "input": texts,
                    "model": self.model_name,
                },
                timeout=self.timeout * len(texts),  # Scale timeout with batch size
            )

            if not response.is_success:
                raise EmbeddingProviderError(
                    f"Batch embedding failed: {response.status_code} - {response.text}"
                )

            data = response.json()

            # Response format: {"data": [{"embedding": [...], "index": 0}, ...]}
            # Sort by index to maintain order
            embeddings_data = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            return [item["embedding"] for item in embeddings_data]

        except httpx.TimeoutException:
            raise EmbeddingProviderError(
                f"Batch embedding timed out after {self.timeout * len(texts)}s for {len(texts)} texts"
            )
        except httpx.RequestError as e:
            raise EmbeddingProviderError(f"Batch embedding request failed: {e}")


class OllamaProvider(EmbeddingProvider):
    """Ollama embedding provider.

    Uses Ollama's native API at localhost:11434.
    Requires an embedding model pulled in Ollama (e.g., nomic-embed-text).
    """

    DEFAULT_URL = "http://localhost:11434"
    DEFAULT_MODEL = "nomic-embed-text"

    def __init__(
        self,
        url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
    ):
        self.url = url or self.DEFAULT_URL
        self._model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Ollama is running and has the model available."""
        try:
            # Check if Ollama is running
            resp = httpx.get(
                f"{self.url}/api/tags",
                timeout=5,
            )
            if not resp.is_success:
                return False

            # Check if our model is available
            data = resp.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]

            # Check if model exists (with or without tag)
            model_base = self._model.split(":")[0]
            return model_base in models

        except (httpx.RequestError, httpx.TimeoutException):
            # Ollama not running - this is expected during provider discovery
            return False
        except Exception:
            # Other errors during availability check
            return False

    def embed(self, text: str) -> list[float]:
        """Generate embedding using Ollama."""
        try:
            resp = httpx.post(
                f"{self.url}/api/embeddings",
                json={
                    "model": self._model,
                    "prompt": text,
                },
                timeout=self.timeout,
            )

            if not resp.is_success:
                raise EmbeddingProviderError(
                    f"Ollama returned {resp.status_code}: {resp.text}"
                )

            data = resp.json()

            if "error" in data:
                raise EmbeddingProviderError(
                    f"Ollama error: {data['error']}"
                )

            embedding = data.get("embedding")
            if not embedding:
                raise EmbeddingProviderError(
                    "Ollama response missing 'embedding' field"
                )

            return embedding

        except httpx.ConnectError:
            raise EmbeddingProviderError(
                "Cannot connect to Ollama. Is it running? "
                "Start with: ollama serve"
            )
        except httpx.TimeoutException:
            raise EmbeddingProviderError(
                f"Ollama request timed out after {self.timeout}s"
            )
        except EmbeddingProviderError:
            raise
        except Exception as e:
            raise EmbeddingProviderError(f"Ollama embedding failed: {e}")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Ollama doesn't support batch embeddings natively,
        so we call embed() for each text sequentially.
        """
        return [self.embed(text) for text in texts]


class EmbeddingProviderManager:
    """Manages multiple embedding providers with automatic selection.

    NO FALLBACKS within the manager. If the selected provider fails,
    operations fail loudly. The manager only handles provider discovery.
    """

    def __init__(self, preferred_provider: Optional[str] = None):
        """Initialize the provider manager.

        Args:
            preferred_provider: Name of preferred provider ("lm_studio" or "ollama").
                               If None, auto-detects first available.
        """
        self._providers: dict[str, EmbeddingProvider] = {
            "lm_studio": LMStudioProvider(),
            "ollama": OllamaProvider(),
        }
        self._preferred = preferred_provider
        self._active_provider: Optional[EmbeddingProvider] = None

    def get_provider(self) -> EmbeddingProvider:
        """Get the active embedding provider.

        Returns:
            The active provider

        Raises:
            NoProviderAvailableError: If no provider is available
        """
        # Return cached provider if still available
        if self._active_provider and self._active_provider.is_available():
            return self._active_provider

        # Try preferred provider first
        if self._preferred and self._preferred in self._providers:
            provider = self._providers[self._preferred]
            if provider.is_available():
                self._active_provider = provider
                return provider
            else:
                raise NoProviderAvailableError(
                    f"Preferred provider '{self._preferred}' is not available. "
                    f"Check that {provider.name} is running with an embedding model loaded."
                )

        # Auto-detect: try each provider in order
        for name, provider in self._providers.items():
            if provider.is_available():
                self._active_provider = provider
                return provider

        # No provider available
        raise NoProviderAvailableError(
            "No embedding provider available. Please start one of:\n"
            "  - LM Studio: Load an embedding model and enable the server\n"
            "  - Ollama: Run 'ollama serve' and 'ollama pull nomic-embed-text'"
        )

    def list_available(self) -> list[str]:
        """List all available providers."""
        return [
            name for name, provider in self._providers.items()
            if provider.is_available()
        ]

    def add_provider(self, name: str, provider: EmbeddingProvider) -> None:
        """Add a custom provider."""
        self._providers[name] = provider
