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
    CLAUDE = "claude"  # Claude via basic SDK (requires API key)
    CLAUDE_AGENT = "claude-agent"  # Claude via Agent SDK (uses Claude Code auth)
    GEMINI = "gemini"  # Google Gemini API
    GROK = "grok"  # xAI Grok API


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


@dataclass
class UsageStats:
    """Statistics from a summarization call."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""

    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self):
        # Track usage from last summarization call
        self.last_usage: Optional[UsageStats] = None
        # Track cumulative usage for session
        self.session_usage = {"calls": 0, "total_tokens": 0}

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

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return "unknown"

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough: ~4 chars per token)."""
        return len(text) // 4

    def _record_usage(self, input_text: str, output_text: str, model: str = ""):
        """Record usage stats from a summarization call."""
        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(output_text)
        self.last_usage = UsageStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model or self.model_name,
            provider=self.name,
        )
        self.session_usage["calls"] += 1
        self.session_usage["total_tokens"] += self.last_usage.total_tokens


class SimpleSummarizerProvider(LLMProvider):
    """Simple extractive summarizer (no LLM)."""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "Simple (extractive)"

    @property
    def model_name(self) -> str:
        return "extractive"

    def is_available(self) -> bool:
        return True

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Extract first sentences up to max_length characters."""
        if not text:
            return ""

        original_text = text
        text = " ".join(text.split())

        if len(text) <= max_length:
            self._record_usage(original_text, text)
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

        self._record_usage(original_text, summary)
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
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "not-needed"  # Many local providers don't need a key
        self.model = model
        self._provider_name = provider_name
        self._fallback = SimpleSummarizerProvider()
        self._discovered_model: Optional[str] = None

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        if self._discovered_model:
            return self._discovered_model
        return self.model or "auto"

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

        original_text = text
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

            model = self._get_model()
            self._discovered_model = model

            payload = {
                "model": model,
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

                # Record usage - try to get actual tokens from API response
                usage = data.get("usage", {})
                if usage:
                    self.last_usage = UsageStats(
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        model=model,
                        provider=self.name,
                    )
                    self.session_usage["calls"] += 1
                    self.session_usage["total_tokens"] += self.last_usage.total_tokens
                else:
                    self._record_usage(original_text, summary, model)

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

    elif config.provider == ProviderType.CLAUDE_AGENT:
        return ClaudeAgentProvider(model=config.model or "claude-sonnet-4-20250514")

    elif config.provider == ProviderType.GEMINI:
        return GeminiProvider(model=config.model or "gemini-1.5-flash")

    elif config.provider == ProviderType.GROK:
        return GrokProvider(model=config.model or "grok-beta")

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
        {
            "type": ProviderType.CLAUDE,
            "name": "Claude (API)",
            "available": ClaudeProvider().is_available(),
            "description": "Claude API - requires ANTHROPIC_API_KEY (NOT same as Claude subscription)",
        },
        {
            "type": ProviderType.CLAUDE_AGENT,
            "name": "Claude (Agent SDK)",
            "available": ClaudeAgentProvider().is_available(),
            "description": "Claude via Agent SDK - uses Claude Code auth (no API key needed)",
        },
        {
            "type": ProviderType.GEMINI,
            "name": "Gemini",
            "available": GeminiProvider().is_available(),
            "description": "Google Gemini API (free tier available)",
        },
        {
            "type": ProviderType.GROK,
            "name": "Grok",
            "available": GrokProvider().is_available(),
            "description": "xAI Grok API (requires API key)",
        },
    ]
    return providers


class ClaudeProvider(LLMProvider):
    """
    Claude provider using the Anthropic Python SDK.
    Requires ANTHROPIC_API_KEY environment variable.

    Note: This uses the basic 'anthropic' SDK, NOT the Agent SDK.
    The basic SDK requires an API key and cannot use Claude Code auth.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__()
        self._model = model
        self._client = None
        self._fallback = SimpleSummarizerProvider()

    @property
    def name(self) -> str:
        return "Claude"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Claude SDK is available and API key is set."""
        try:
            import anthropic  # noqa

            # The basic anthropic SDK requires an API key
            # It CANNOT use Claude Code auth - that requires the Agent SDK
            return bool(os.getenv("ANTHROPIC_API_KEY"))
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

        original_text = text
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
                model=self._model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            summary = message.content[0].text.strip()

            # Record usage from API response
            usage = message.usage
            if usage:
                self.last_usage = UsageStats(
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    model=self._model,
                    provider=self.name,
                )
                self.session_usage["calls"] += 1
                self.session_usage["total_tokens"] += self.last_usage.total_tokens
            else:
                self._record_usage(original_text, summary, self._model)

            return summary
        except Exception:
            return self._fallback.summarize(text, max_length)


class ClaudeAgentProvider(LLMProvider):
    """
    Claude provider using the Agent SDK.
    Can use Claude Code authentication (no API key needed if authenticated).
    Falls back to ANTHROPIC_API_KEY if Claude Code auth not available.

    Requires: pip install claude-agent-sdk
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__()
        self._model = model
        self._fallback = SimpleSummarizerProvider()

    @property
    def name(self) -> str:
        return "Claude (Agent SDK)"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Claude Agent SDK is available."""
        try:
            import claude_agent_sdk  # noqa
            return True
        except ImportError:
            return False

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate summary using Claude Agent SDK."""
        import asyncio

        if not text:
            return ""

        if not self.is_available():
            return self._fallback.summarize(text, max_length)

        original_text = text
        if len(text) > 4000:
            text = text[:4000]

        try:
            # Run async summarization
            summary = asyncio.run(self._async_summarize(text, max_length))
            self._record_usage(original_text, summary, self._model)
            return summary
        except Exception:
            return self._fallback.summarize(text, max_length)

    async def _async_summarize(self, text: str, max_length: int) -> str:
        """Async implementation using Agent SDK."""
        from claude_agent_sdk import query, ClaudeAgentOptions

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points. Return only the summary, no preamble.

Text:
{text}"""

        options = ClaudeAgentOptions(
            max_turns=1,
            allowed_tools=[],  # No tools needed for summarization
        )

        summary = ""
        async for message in query(prompt=prompt, options=options):
            # Extract text from assistant messages
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        summary += block.text

        return summary.strip()


class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider.
    Free tier available with generous limits.
    """

    def __init__(self, model: str = "gemini-1.5-flash"):
        super().__init__()
        self._model = model
        self._client = None
        self._fallback = SimpleSummarizerProvider()

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Gemini SDK is available and API key is set."""
        try:
            import google.generativeai  # noqa

            # Check for API key
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            return bool(api_key)
        except ImportError:
            return False

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai

            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(self._model)
        return self._client

    def summarize(self, text: str, max_length: int = 150) -> str:
        if not text:
            return ""

        original_text = text
        if not self.is_available():
            return self._fallback.summarize(text, max_length)

        if len(text) > 4000:
            text = text[:4000]

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points. Return only the summary, no preamble.

Text:
{text}"""

        try:
            model = self._get_client()
            response = model.generate_content(prompt)
            summary = response.text.strip()

            # Record usage - Gemini provides usage metadata
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                self.last_usage = UsageStats(
                    input_tokens=getattr(usage, 'prompt_token_count', 0),
                    output_tokens=getattr(usage, 'candidates_token_count', 0),
                    total_tokens=getattr(usage, 'total_token_count', 0),
                    model=self._model,
                    provider=self.name,
                )
                self.session_usage["calls"] += 1
                self.session_usage["total_tokens"] += self.last_usage.total_tokens
            else:
                self._record_usage(original_text, summary, self._model)

            return summary
        except Exception:
            return self._fallback.summarize(text, max_length)


class GrokProvider(OpenAICompatibleProvider):
    """
    xAI Grok API provider.
    Uses OpenAI-compatible API format.
    Requires XAI_API_KEY environment variable.
    """

    def __init__(self, model: str = "grok-beta"):
        api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        super().__init__(
            base_url="https://api.x.ai/v1",
            api_key=api_key,
            model=model,
            provider_name="Grok",
        )

    def is_available(self) -> bool:
        """Check if Grok API key is set."""
        api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        return bool(api_key)


def auto_detect_provider() -> Optional[LLMProvider]:
    """
    Auto-detect the best available LLM provider.

    Priority:
    1. LM Studio (if running locally - free, fast)
    2. Ollama (if running locally - free)
    3. Gemini (if API key set - has free tier)
    4. Claude (if SDK installed and authenticated)
    5. OpenAI (if API key set)
    6. Transformers (if installed - can be slow first run)
    7. None (user needs to set up a provider)
    """
    # Check local providers first (free, no API costs)
    lm_studio = LMStudioProvider()
    if lm_studio.is_available():
        return lm_studio

    ollama = OllamaProvider()
    if ollama.is_available():
        return ollama

    # Check Gemini (has free tier, good quality)
    gemini = GeminiProvider()
    if gemini.is_available():
        return gemini

    # Check Grok
    grok = GrokProvider()
    if grok.is_available():
        return grok

    # Check Claude Agent SDK first (can use Claude Code auth, no API key needed)
    claude_agent = ClaudeAgentProvider()
    if claude_agent.is_available():
        return claude_agent

    # Check Claude API (requires ANTHROPIC_API_KEY)
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

[LOCAL OPTIONS - Free, no API costs]
1. LM Studio (recommended for local/free):
   - Download from https://lmstudio.ai
   - Load a model and start the local server
   - It will auto-detect at localhost:1234

2. Ollama (alternative local option):
   - Install from https://ollama.ai
   - Run: ollama pull llama2
   - It will auto-detect at localhost:11434

[CLOUD OPTIONS - API-based]
3. Gemini (FREE tier available - recommended):
   - Get free API key at https://aistudio.google.com/apikey
   - pip install google-generativeai
   - Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable

4. Claude Agent SDK (uses Claude Code auth - no API key needed!):
   - pip install claude-agent-sdk
   - If you have Claude Code authenticated, it works automatically
   - Requires Claude Pro/Max subscription

5. Claude API (separate API key required):
   - pip install anthropic
   - Set ANTHROPIC_API_KEY environment variable
   - NOTE: A Claude subscription (claude.ai) is NOT an API key!
     Get API key at: https://console.anthropic.com/

6. Grok (xAI):
   - Get API key at: https://console.x.ai/
   - Set XAI_API_KEY environment variable

7. OpenAI:
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

[LOCAL OPTIONS - Free, no API costs]
1. LM Studio (recommended if you have a decent GPU):
   - Download: https://lmstudio.ai
   - Load any model and click "Start Server"
   - We'll auto-detect it at localhost:1234

2. Ollama (simpler setup):
   - Install: https://ollama.ai
   - Run: ollama pull llama2 && ollama serve
   - We'll auto-detect it at localhost:11434

[CLOUD OPTIONS]
3. Gemini (FREE tier available - easiest cloud option):
   - Get free API key: https://aistudio.google.com/apikey
   - pip install google-generativeai
   - Set GOOGLE_API_KEY or GEMINI_API_KEY

4. Claude Agent SDK (uses Claude Code auth - no API key needed!):
   - pip install claude-agent-sdk
   - If you have Claude Code authenticated, it works automatically
   - Requires Claude Pro/Max subscription

5. Claude API (separate API key required):
   - pip install anthropic
   - Set ANTHROPIC_API_KEY environment variable
   - NOTE: A Claude subscription (claude.ai) is NOT an API key!
     Get API key at: https://console.anthropic.com/

6. Grok (xAI):
   - Get API key at: https://console.x.ai/
   - Set XAI_API_KEY environment variable

7. OpenAI:
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
