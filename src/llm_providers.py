"""LLM provider abstraction for configurable summarization backends."""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import httpx


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    SIMPLE = "simple"  # No LLM, just extractive
    LM_STUDIO = "lm-studio"  # Local LM Studio (OpenAI-compatible)
    OLLAMA = "ollama"  # Local Ollama
    OPENAI = "openai"  # OpenAI API
    OPENAI_COMPATIBLE = "openai-compatible"  # Any OpenAI-compatible endpoint
    TRANSFORMERS = "transformers"  # HuggingFace transformers (local)
    CLAUDE = "claude"  # Claude via SDK (for Claude Code users)


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: ProviderType = ProviderType.SIMPLE
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    # Provider-specific defaults
    defaults: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load config from environment variables."""
        provider = ProviderType(os.getenv("RSS_LLM_PROVIDER", "simple"))
        return cls(
            provider=provider,
            base_url=os.getenv("RSS_LLM_BASE_URL"),
            api_key=os.getenv("RSS_LLM_API_KEY"),
            model=os.getenv("RSS_LLM_MODEL"),
        )

    @classmethod
    def from_file(cls, path: str = "config/llm.json") -> "LLMConfig":
        """Load config from JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            data = json.load(f)

        return cls(
            provider=ProviderType(data.get("provider", "simple")),
            base_url=data.get("base_url"),
            api_key=data.get("api_key"),
            model=data.get("model"),
            defaults=data.get("defaults", {}),
        )

    def save(self, path: str = "config/llm.json") -> None:
        """Save config to JSON file."""
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "provider": self.provider.value,
            "base_url": self.base_url,
            "model": self.model,
            "defaults": self.defaults,
        }
        # Don't save API key to file for security
        if self.api_key and not self.api_key.startswith("sk-"):
            data["api_key"] = self.api_key

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate a summary of the given text."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider display name."""
        pass


class SimpleSummarizerProvider(LLMProvider):
    """Simple extractive summarizer (no LLM)."""

    @property
    def name(self) -> str:
        return "Simple (extractive)"

    def is_available(self) -> bool:
        return True

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Extract first sentences up to max_length characters."""
        if not text:
            return ""

        text = " ".join(text.split())

        if len(text) <= max_length:
            return text

        sentences = []
        current = ""
        for char in text:
            current += char
            if char in ".!?" and len(current) > 20:
                sentences.append(current.strip())
                current = ""

        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) + 1 <= max_length:
                summary = (summary + " " + sentence).strip()
            else:
                break

        if not summary:
            summary = text[: max_length - 3].rsplit(" ", 1)[0] + "..."

        return summary


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider for OpenAI-compatible APIs.
    Works with LM Studio, Ollama (with OpenAI compatibility), and OpenAI itself.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider_name: str = "OpenAI-compatible",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "not-needed"  # Many local providers don't need a key
        self.model = model
        self._provider_name = provider_name
        self._fallback = SimpleSummarizerProvider()

    @property
    def name(self) -> str:
        return self._provider_name

    def is_available(self) -> bool:
        """Check if the endpoint is reachable."""
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def _get_model(self) -> str:
        """Get the model to use, discovering from API if not specified."""
        if self.model:
            return self.model

        # Try to discover available models
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    return models[0].get("id", "default")
        except Exception:
            pass

        return "default"

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate summary using the OpenAI-compatible API."""
        if not text:
            return ""

        # Truncate very long text to avoid token limits
        if len(text) > 4000:
            text = text[:4000]

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points.

Text:
{text}

Summary:"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            payload = {
                "model": self._get_model(),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }

            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            )

            if response.status_code == 200:
                data = response.json()
                summary = data["choices"][0]["message"]["content"].strip()
                # Ensure it's not too long
                if len(summary) > max_length * 2:
                    summary = summary[:max_length]
                return summary

        except Exception as e:
            # Log error but don't crash - fall back to simple
            pass

        # Fall back to simple summarizer
        return self._fallback.summarize(text, max_length)


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio local LLM provider."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            base_url="http://localhost:1234/v1",
            model=model,
            provider_name="LM Studio",
        )


class OllamaProvider(OpenAICompatibleProvider):
    """Ollama local LLM provider (using OpenAI-compatible endpoint)."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            base_url="http://localhost:11434/v1",
            model=model or "llama2",
            provider_name="Ollama",
        )


class TransformersProvider(LLMProvider):
    """HuggingFace transformers provider (requires local model download)."""

    def __init__(self, model: str = "facebook/bart-large-cnn"):
        self.model_name = model
        self._pipeline = None
        self._fallback = SimpleSummarizerProvider()

    @property
    def name(self) -> str:
        return f"Transformers ({self.model_name})"

    def is_available(self) -> bool:
        try:
            import transformers  # noqa
            import torch  # noqa

            return True
        except ImportError:
            return False

    def _load_pipeline(self):
        if self._pipeline is None:
            from transformers import pipeline

            self._pipeline = pipeline("summarization", model=self.model_name)
        return self._pipeline

    def summarize(self, text: str, max_length: int = 150) -> str:
        if not text:
            return ""

        if not self.is_available():
            return self._fallback.summarize(text, max_length)

        if len(text) > 4000:
            text = text[:4000]

        try:
            pipeline = self._load_pipeline()
            result = pipeline(
                text,
                max_length=max_length,
                min_length=30,
                do_sample=False,
            )
            return result[0]["summary_text"]
        except Exception:
            return self._fallback.summarize(text, max_length)


def get_provider(config: Optional[LLMConfig] = None) -> LLMProvider:
    """
    Get the appropriate LLM provider based on configuration.

    Priority:
    1. Explicit config passed in
    2. Environment variables
    3. Config file
    4. Default (simple)
    """
    if config is None:
        # Try environment first, then file
        config = LLMConfig.from_env()
        if config.provider == ProviderType.SIMPLE:
            file_config = LLMConfig.from_file()
            if file_config.provider != ProviderType.SIMPLE:
                config = file_config

    if config.provider == ProviderType.SIMPLE:
        return SimpleSummarizerProvider()

    elif config.provider == ProviderType.LM_STUDIO:
        return LMStudioProvider(model=config.model)

    elif config.provider == ProviderType.OLLAMA:
        return OllamaProvider(model=config.model)

    elif config.provider == ProviderType.OPENAI:
        return OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1",
            api_key=config.api_key or os.getenv("OPENAI_API_KEY"),
            model=config.model or "gpt-3.5-turbo",
            provider_name="OpenAI",
        )

    elif config.provider == ProviderType.OPENAI_COMPATIBLE:
        if not config.base_url:
            raise ValueError("base_url required for openai-compatible provider")
        return OpenAICompatibleProvider(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            provider_name="Custom API",
        )

    elif config.provider == ProviderType.TRANSFORMERS:
        return TransformersProvider(model=config.model or "facebook/bart-large-cnn")

    else:
        return SimpleSummarizerProvider()


def list_providers() -> list[dict]:
    """List available providers with their status."""
    providers = [
        {
            "type": ProviderType.SIMPLE,
            "name": "Simple (extractive)",
            "available": True,
            "description": "Fast, no external dependencies",
        },
        {
            "type": ProviderType.LM_STUDIO,
            "name": "LM Studio",
            "available": LMStudioProvider().is_available(),
            "description": "Local LLM via LM Studio (localhost:1234)",
        },
        {
            "type": ProviderType.OLLAMA,
            "name": "Ollama",
            "available": OllamaProvider().is_available(),
            "description": "Local LLM via Ollama (localhost:11434)",
        },
        {
            "type": ProviderType.TRANSFORMERS,
            "name": "Transformers",
            "available": TransformersProvider().is_available(),
            "description": "HuggingFace transformers (local model)",
        },
        {
            "type": ProviderType.OPENAI,
            "name": "OpenAI",
            "available": bool(os.getenv("OPENAI_API_KEY")),
            "description": "OpenAI API (requires API key)",
        },
    ]
    return providers


class ClaudeProvider(LLMProvider):
    """
    Claude provider using the Anthropic SDK.
    Works for users who have Claude Code CLI authenticated.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model_name = model
        self._client = None
        self._fallback = SimpleSummarizerProvider()

    @property
    def name(self) -> str:
        return f"Claude ({self.model_name})"

    def is_available(self) -> bool:
        """Check if Claude SDK is available and authenticated."""
        try:
            import anthropic  # noqa

            # Check if API key is available
            if os.getenv("ANTHROPIC_API_KEY"):
                return True
            # Check for Claude Code config
            claude_config = Path.home() / ".claude" / ".credentials.json"
            return claude_config.exists()
        except ImportError:
            return False

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def summarize(self, text: str, max_length: int = 150) -> str:
        if not text:
            return ""

        if not self.is_available():
            return self._fallback.summarize(text, max_length)

        if len(text) > 4000:
            text = text[:4000]

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points. Return only the summary, no preamble.

Text:
{text}"""

        try:
            client = self._get_client()
            message = client.messages.create(
                model=self.model_name,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except Exception:
            return self._fallback.summarize(text, max_length)


def auto_detect_provider() -> Optional[LLMProvider]:
    """
    Auto-detect the best available LLM provider.

    Priority:
    1. LM Studio (if running locally - free, fast)
    2. Ollama (if running locally - free)
    3. Claude (if SDK installed and authenticated)
    4. OpenAI (if API key set)
    5. Transformers (if installed - can be slow first run)
    6. None (user needs to set up a provider)
    """
    # Check local providers first (free, no API costs)
    lm_studio = LMStudioProvider()
    if lm_studio.is_available():
        return lm_studio

    ollama = OllamaProvider()
    if ollama.is_available():
        return ollama

    # Check Claude (common for Claude Code users)
    claude = ClaudeProvider()
    if claude.is_available():
        return claude

    # Check OpenAI
    if os.getenv("OPENAI_API_KEY"):
        return OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1",
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
            provider_name="OpenAI",
        )

    # Check transformers (last because can be slow)
    transformers = TransformersProvider()
    if transformers.is_available():
        return transformers

    return None


def get_best_provider() -> tuple[LLMProvider, bool]:
    """
    Get the best available provider, with fallback to simple.

    Returns:
        Tuple of (provider, is_llm) where is_llm indicates if it's a real LLM
        or just the simple fallback.
    """
    provider = auto_detect_provider()
    if provider:
        return provider, True
    return SimpleSummarizerProvider(), False


def get_setup_instructions() -> str:
    """Get instructions for setting up an LLM provider."""
    return """
No LLM provider detected. For AI-powered summaries, set up one of:

1. LM Studio (recommended for local/free):
   - Download from https://lmstudio.ai
   - Load a model and start the local server
   - It will auto-detect at localhost:1234

2. Ollama (alternative local option):
   - Install from https://ollama.ai
   - Run: ollama pull llama2
   - It will auto-detect at localhost:11434

3. Claude (if you use Claude Code):
   - Install: pip install anthropic
   - Set ANTHROPIC_API_KEY or use Claude Code auth

4. OpenAI:
   - Set OPENAI_API_KEY environment variable

Run 'rss setup' for guided configuration.
"""


def validate_llm_ready(require_llm: bool = False) -> tuple[LLMProvider, bool, Optional[str]]:
    """
    Validate that an LLM provider is available and ready.

    Args:
        require_llm: If True, require a real LLM (not simple extractor)

    Returns:
        Tuple of (provider, is_ready, error_message)
        - provider: The best available provider
        - is_ready: True if provider can be used
        - error_message: None if ready, or helpful error message with onboarding instructions
    """
    provider, is_llm = get_best_provider()

    if require_llm and not is_llm:
        return (
            provider,
            False,
            """No LLM provider is configured.

This feature requires an AI model to work properly. Please set up one of these:

[QUICK OPTIONS]
1. LM Studio (recommended if you have a decent GPU):
   - Download: https://lmstudio.ai
   - Load any model and click "Start Server"
   - We'll auto-detect it at localhost:1234

2. Ollama (simpler setup):
   - Install: https://ollama.ai
   - Run: ollama pull llama2 && ollama serve
   - We'll auto-detect it at localhost:11434

[CLOUD OPTIONS]
3. Claude (if you use Claude Code):
   - pip install anthropic
   - Set ANTHROPIC_API_KEY or use existing Claude Code auth

4. OpenAI:
   - Set OPENAI_API_KEY environment variable

Run 'rss setup' for interactive configuration."""
        )

    # Test the provider actually works
    if is_llm:
        if not provider.is_available():
            return (
                provider,
                False,
                f"""The configured provider ({provider.name}) is not currently available.

Possible issues:
- LM Studio: Make sure a model is loaded and server is running
- Ollama: Make sure the service is running (ollama serve)
- Claude: Check your API key or Claude Code authentication
- OpenAI: Verify your API key is valid

Run 'rss providers' to see current status.
Run 'rss setup' to reconfigure."""
            )

    return provider, True, None


def ensure_llm_or_exit(require_llm: bool = False):
    """
    Ensure an LLM is available, or print helpful error and exit.

    Use this at the start of commands that need LLM functionality.
    """
    import sys

    provider, is_ready, error = validate_llm_ready(require_llm)

    if not is_ready:
        print(error)
        print("\n" + "=" * 60)
        print("Run 'rss setup' to configure an LLM provider.")
        print("=" * 60)
        sys.exit(1)

    return provider
