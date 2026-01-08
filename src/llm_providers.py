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

    LM_STUDIO = "lm-studio"  # Local LM Studio (OpenAI-compatible)
    OLLAMA = "ollama"  # Local Ollama
    OPENAI = "openai"  # OpenAI API
    OPENAI_COMPATIBLE = "openai-compatible"  # Any OpenAI-compatible endpoint
    TRANSFORMERS = "transformers"  # HuggingFace transformers (local)
    CLAUDE = "claude"  # Claude via basic SDK (requires API key)
    CLAUDE_CODE = "claude-code"  # Claude via Claude Code CLI (uses Claude Code auth)
    GEMINI = "gemini"  # Google Gemini API
    GEMINI_CLI = "gemini-cli"  # Gemini via CLI (uses stored OAuth)
    CODEX_CLI = "codex-cli"  # OpenAI Codex CLI (uses ChatGPT subscription auth)
    GROK = "grok"  # xAI Grok API
    GROQ = "groq"  # Groq API (fast inference, FREE tier available)


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: Optional[ProviderType] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    # Provider-specific defaults
    defaults: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load config from environment variables."""
        provider_str = os.getenv("RSS_LLM_PROVIDER")
        provider = ProviderType(provider_str) if provider_str else None
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

        provider_str = data.get("provider")
        provider = ProviderType(provider_str) if provider_str else None
        return cls(
            provider=provider,
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

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Generate a response to a prompt without any wrapping.
        Use this for classification, comparison, or custom prompts.
        Default implementation uses summarize() - subclasses should override.
        """
        return self.summarize(prompt, max_length=max_tokens)

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

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points.

Text:
{text}

Summary:"""

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
        response.raise_for_status()

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

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate a response to a prompt without any wrapping."""
        if not prompt:
            return ""

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
            "max_tokens": max_tokens,
        }

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()

        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()

        # Record usage
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
            self._record_usage(prompt, result, model)

        return result


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio local LLM provider with auto-loading support."""

    def __init__(self, model: Optional[str] = None):
        super().__init__(
            base_url="http://localhost:1234/v1",
            model=model,
            provider_name="LM Studio",
        )
        self._auto_load_attempted = False

    def _auto_load_model(self) -> bool:
        """
        Attempt to auto-load a model using lms CLI.

        Uses project config from config/llm.json:
        - Model name from main 'model' field
        - Auto-load settings from 'defaults.auto_load' dict

        Safety: Checks resources before loading using --estimate-only.
        """
        import subprocess
        import shutil

        # Check if lms CLI is available
        if not shutil.which('lms'):
            return False

        # Load project config
        config = LLMConfig.from_file()

        # Get auto-load settings from project config
        auto_load_config = config.defaults.get("auto_load", {})

        # Auto-load is ENABLED by default for LM Studio
        # Unlike cloud providers which are always available, local LLMs must be loaded
        # Without auto-load, the app breaks when using LM Studio with no model loaded
        if not auto_load_config.get("enabled", True):
            return False

        # Model must be configured in project config
        model_to_load = config.model
        if not model_to_load:
            return False

        ttl_seconds = auto_load_config.get("ttl_seconds", 300)

        try:
            # Check resources first using LM Studio's --estimate-only
            estimate_result = subprocess.run(
                ["lms", "load", model_to_load, "--estimate-only", "--yes"],
                capture_output=True,
                timeout=30,
            )

            # Check if resources are sufficient
            estimate_output = estimate_result.stdout.decode('utf-8', errors='ignore')
            if "cannot be loaded" in estimate_output.lower():
                return False

            # Load the model with TTL for auto-unload after idle
            result = subprocess.run(
                ["lms", "load", model_to_load, "--ttl", str(ttl_seconds), "--yes"],
                capture_output=True,
                timeout=120,
            )

            if result.returncode != 0:
                return False

            # Post-load headroom check
            # After loading, verify system still has adequate resources
            # If overloaded, unload and return False
            if not self._check_post_load_headroom(model_to_load):
                return False

            return True
        except Exception:
            return False

    def _check_post_load_headroom(self, loaded_model: str) -> bool:
        """
        Verify system has adequate resources after model load.

        Checks for minimum memory headroom (1GB by default).
        If system is resource-constrained, unloads the model and returns False.

        Returns:
            True if system has adequate headroom
            False if overloaded (model will be unloaded)
        """
        import subprocess
        import shutil

        # Minimum headroom in MB (2GB required)
        MIN_HEADROOM_MB = 2048

        try:
            # Try to get memory info using platform-appropriate method
            available_mb = self._get_available_memory_mb()

            if available_mb is None:
                # Can't determine memory - assume OK
                return True

            if available_mb < MIN_HEADROOM_MB:
                # System is resource-constrained - unload and return False
                try:
                    subprocess.run(
                        ["lms", "unload", "--yes"],
                        capture_output=True,
                        timeout=30,
                    )
                except Exception:
                    pass
                return False

            return True

        except Exception:
            # If we can't check, assume OK
            return True

    def _get_available_memory_mb(self) -> int | None:
        """
        Get available system memory in MB.

        Returns:
            Available memory in MB, or None if can't determine
        """
        import sys

        try:
            if sys.platform == "win32":
                # Windows: use ctypes to get memory status
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                return stat.ullAvailPhys // (1024 * 1024)

            else:
                # Linux/Mac: read from /proc/meminfo or use sysctl
                try:
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if line.startswith("MemAvailable:"):
                                # Value is in kB
                                kb = int(line.split()[1])
                                return kb // 1024
                except FileNotFoundError:
                    # macOS - use vm_stat
                    import subprocess
                    result = subprocess.run(
                        ["vm_stat"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # Parse vm_stat output
                        # Pages free: XXX
                        # Page size is typically 4096 bytes
                        for line in result.stdout.split("\n"):
                            if "Pages free" in line:
                                pages = int(line.split(":")[1].strip().rstrip("."))
                                return (pages * 4096) // (1024 * 1024)
                return None

        except Exception:
            return None

    def _make_request(self, prompt: str, max_tokens: int, is_summarize: bool = False) -> str:
        """Make a request with auto-load retry on 'No models loaded' error."""
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
            "max_tokens": max_tokens,
        }

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0,
        )

        # Check for "No models loaded" error
        if response.status_code == 400:
            try:
                error_data = response.json()
                if "No models loaded" in error_data.get("error", {}).get("message", ""):
                    if not self._auto_load_attempted:
                        self._auto_load_attempted = True
                        if self._auto_load_model():
                            # Retry the request
                            return self._make_request(prompt, max_tokens, is_summarize)
            except Exception:
                pass

        response.raise_for_status()

        data = response.json()
        result = data["choices"][0]["message"]["content"].strip()

        # Record usage
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
            self._record_usage(prompt, result, model)

        return result

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate summary using LM Studio with auto-load support."""
        if not text:
            return ""

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points.

Text:
{text}

Summary:"""

        result = self._make_request(prompt, max_tokens=max_length * 2, is_summarize=True)

        # Ensure it's not too long
        if len(result) > max_length * 2:
            result = result[:max_length]

        return result

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate response using LM Studio with auto-load support."""
        if not prompt:
            return ""
        return self._make_request(prompt, max_tokens=max_tokens)


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
        super().__init__()
        self._model = model
        self._pipeline = None

    @property
    def name(self) -> str:
        return f"Transformers ({self._model})"

    @property
    def model_name(self) -> str:
        return self._model

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

            self._pipeline = pipeline("summarization", model=self._model)
        return self._pipeline

    def summarize(self, text: str, max_length: int = 150) -> str:
        if not text:
            return ""

        if not self.is_available():
            raise RuntimeError("Transformers library not available")

        pipeline = self._load_pipeline()
        result = pipeline(
            text,
            max_length=max_length,
            min_length=30,
            do_sample=False,
        )
        return result[0]["summary_text"]


def get_provider(config: Optional[LLMConfig] = None) -> LLMProvider:
    """
    Get the appropriate LLM provider based on configuration.

    Priority:
    1. Explicit config passed in
    2. Environment variables
    3. Config file
    4. Auto-detect available provider

    Raises ValueError if no provider is available.
    """
    if config is None:
        # Try environment first, then file
        config = LLMConfig.from_env()
        if config.provider is None:
            file_config = LLMConfig.from_file()
            if file_config.provider is not None:
                config = file_config

    # If no explicit provider, auto-detect
    if config.provider is None:
        provider = auto_detect_provider()
        if provider is None:
            raise ValueError("No LLM provider configured or available. Run 'rss setup' to configure.")
        return provider

    if config.provider == ProviderType.LM_STUDIO:
        return LMStudioProvider(model=config.model)

    elif config.provider == ProviderType.OLLAMA:
        return OllamaProvider(model=config.model)

    elif config.provider == ProviderType.OPENAI:
        return OpenAIAgentsProvider(model=config.model or "gpt-4o-mini")

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

    elif config.provider == ProviderType.CLAUDE_CODE:
        return ClaudeCodeProvider(model=config.model or "sonnet")

    elif config.provider == ProviderType.GEMINI:
        return GeminiProvider(model=config.model or "gemini-1.5-flash")

    elif config.provider == ProviderType.GEMINI_CLI:
        return GeminiCLIProvider(model=config.model or "gemini-2.0-flash")

    elif config.provider == ProviderType.CODEX_CLI:
        return CodexCLIProvider(model=config.model or "gpt-4.1")

    elif config.provider == ProviderType.GROK:
        return GrokProvider(model=config.model or "grok-beta")

    elif config.provider == ProviderType.GROQ:
        return GroqProvider(model=config.model or "llama-3.3-70b-versatile")

    elif config.provider == ProviderType.CLAUDE:
        return ClaudeProvider(model=config.model or "claude-sonnet-4-20250514")

    else:
        raise ValueError(f"Unknown provider type: {config.provider}")


def list_providers() -> list[dict]:
    """List available providers with their status."""
    providers = [

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
            "type": ProviderType.OPENAI,
            "name": "OpenAI Agents",
            "available": OpenAIAgentsProvider(model="gpt-4o-mini").is_available(),
            "description": "OpenAI Agents SDK (requires API key)",
        },
        {
            "type": ProviderType.CODEX_CLI,
            "name": "Codex CLI",
            "available": CodexCLIProvider().is_available(),
            "description": "OpenAI via ChatGPT subscription (no API key needed)",
        },
        {
            "type": ProviderType.CLAUDE,
            "name": "Claude (API)",
            "available": ClaudeProvider().is_available(),
            "description": "Claude API - requires ANTHROPIC_API_KEY (NOT same as Claude subscription)",
        },
        {
            "type": ProviderType.CLAUDE_CODE,
            "name": "Claude Code",
            "available": ClaudeCodeProvider().is_available(),
            "description": "Uses Claude Code CLI auth (no API key needed)",
        },
        {
            "type": ProviderType.GEMINI,
            "name": "Gemini (API)",
            "available": GeminiProvider().is_available(),
            "description": "Google Gemini API (requires API key)",
        },
        {
            "type": ProviderType.GEMINI_CLI,
            "name": "Gemini CLI",
            "available": GeminiCLIProvider().is_available(),
            "description": "Uses Gemini CLI auth (no API key needed)",
        },
        {
            "type": ProviderType.GROK,
            "name": "Grok",
            "available": GrokProvider().is_available(),
            "description": "xAI Grok API (requires API key)",
        },
        {
            "type": ProviderType.GROQ,
            "name": "Groq",
            "available": GroqProvider().is_available(),
            "description": "Groq API - FREE tier (fast Llama inference)",
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
            raise RuntimeError("Claude provider not available")

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points. Return only the summary, no preamble.

Text:
{text}"""

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


class ClaudeCodeProvider(LLMProvider):
    """
    Claude provider using Claude Code CLI.
    Uses your existing Claude Code authentication (no API key needed).
    Calls 'claude --print' via subprocess.
    """

    def __init__(self, model: str = "sonnet"):
        super().__init__()
        self._model = model

    @property
    def name(self) -> str:
        return "Claude Code"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Claude Code CLI is available."""
        import shutil
        return shutil.which("claude") is not None

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate summary using Claude Code CLI."""
        import subprocess
        import json

        if not text:
            return ""

        if not self.is_available():
            raise RuntimeError("Claude Code CLI not available")

        original_text = text

        prompt = f"Summarize this in {max_length} characters or less. Return only the summary:\n\n{text}"

        cmd = [
            "claude",
            "--print",
            "--output-format", "json",
            "--model", self._model,
            "--tools", "",
            "--no-session-persistence",
            prompt
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60
        )

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code CLI failed: {result.stderr}")

        response = json.loads(result.stdout)
        summary = response.get("result", "").strip()

        # Record usage if available
        usage = response.get("usage", {})
        if usage:
            self._record_usage(original_text, summary, self._model)

        return summary


class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider.
    Free tier available with generous limits.
    """

    def __init__(self, model: str = "gemini-1.5-flash"):
        super().__init__()
        self._model = model
        self._client = None

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
            raise RuntimeError("Gemini provider not available")

        prompt = f"""Summarize the following text in {max_length} characters or less.
Be concise and capture the key points. Return only the summary, no preamble.

Text:
{text}"""

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




class GeminiCLIProvider(LLMProvider):
    """
    Gemini provider using Gemini CLI.
    Uses stored OAuth credentials (no API key needed).
    Install: npm install -g @google/gemini-cli
    Auth: gemini auth
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        super().__init__()
        self._model = model

    @property
    def name(self) -> str:
        return "Gemini CLI"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Gemini CLI is available and authenticated."""
        import shutil
        return shutil.which("gemini") is not None

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate summary using Gemini CLI."""
        import subprocess

        if not text:
            return ""

        if not self.is_available():
            raise RuntimeError("Gemini CLI not available")

        original_text = text

        prompt = f"Summarize this in {max_length} characters or less. Return only the summary:\n\n{text}"

        cmd = [
            "gemini",
            "ask",
            "-o", "text",
            prompt
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60
        )

        if result.returncode != 0:
            raise RuntimeError(f"Gemini CLI failed: {result.stderr}")

        summary = result.stdout.strip()
        self._record_usage(original_text, summary, self._model)
        return summary


class CodexCLIProvider(LLMProvider):
    """
    OpenAI Codex CLI provider.
    Uses ChatGPT subscription auth (Plus/Pro/Team/Enterprise) - no API key needed.
    Install: npm install -g @openai/codex
    """

    def __init__(self, model: str = "gpt-4.1"):
        super().__init__()
        self._model = model

    @property
    def name(self) -> str:
        return "Codex CLI"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Codex CLI is installed."""
        import shutil
        return shutil.which("codex") is not None

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate summary using Codex CLI."""
        import subprocess
        import json

        if not text:
            return ""

        if not self.is_available():
            raise RuntimeError("Codex CLI not available")

        original_text = text

        prompt = f"Summarize this in {max_length} characters or less. Return only the summary:\n\n{text}"

        cmd = [
            "codex",
            "exec",
            prompt,
            "--json",
            "--model", self._model,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60
        )

        if result.returncode != 0:
            raise RuntimeError(f"Codex CLI failed: {result.stderr}")

        # Parse JSON Lines output, get final message
        lines = result.stdout.strip().split("\n")
        for line in reversed(lines):
            try:
                event = json.loads(line)
                if event.get("type") == "message" and event.get("content"):
                    summary = event["content"].strip()
                    self._record_usage(original_text, summary, self._model)
                    return summary
            except json.JSONDecodeError:
                continue

        raise RuntimeError("No valid response from Codex CLI")


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


class GroqProvider(OpenAICompatibleProvider):
    """
    Groq API provider - extremely fast inference.
    Uses OpenAI-compatible API format.
    Requires GROQ_API_KEY environment variable.

    FREE TIER: 6,000 tokens/minute, 30 requests/minute
    Get free API key at: https://console.groq.com/keys
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        api_key = os.getenv("GROQ_API_KEY")
        super().__init__(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model=model,
            provider_name="Groq",
        )

    def is_available(self) -> bool:
        """Check if Groq API key is set."""
        return bool(os.getenv("GROQ_API_KEY"))


class OpenAIAgentsProvider(LLMProvider):
    """
    OpenAI provider using the Agents SDK.
    Provides advanced features: tool orchestration, state management, guardrails.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, model: str):
        super().__init__()
        self._model = model

    @property
    def name(self) -> str:
        return "OpenAI Agents"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        try:
            from agents import Agent, Runner  # noqa
            return bool(os.getenv("OPENAI_API_KEY"))
        except ImportError:
            return False

    def summarize(self, text: str, max_length: int = 150) -> str:
        from agents import Agent, Runner
        import asyncio

        if not text:
            return ""

        original_text = text

        agent = Agent(
            name="Summarizer",
            model=self._model,
            instructions=f"Summarize the following text in {max_length} characters or less. Return only the summary, nothing else."
        )

        # Detect async context and handle appropriately
        try:
            asyncio.get_running_loop()
            # Inside async context - use nest_asyncio to allow nested loop
            import nest_asyncio
            nest_asyncio.apply()
        except RuntimeError:
            # No running loop, sync context - proceed normally
            pass

        result = Runner.run_sync(agent, text)
        summary = str(result.final_output).strip()

        # Track usage
        if hasattr(result, 'usage') and result.usage:
            usage = result.usage
            self.last_usage = UsageStats(
                input_tokens=getattr(usage, 'input_tokens', 0),
                output_tokens=getattr(usage, 'output_tokens', 0),
                total_tokens=getattr(usage, 'total_tokens', 0),
                model=self._model,
                provider=self.name,
            )
            self.session_usage["calls"] += 1
            self.session_usage["total_tokens"] += self.last_usage.total_tokens
        else:
            self._record_usage(original_text, summary, self._model)

        return summary

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
    claude_code = ClaudeCodeProvider()
    if claude_code.is_available():
        return claude_code

    # Check Claude API (requires ANTHROPIC_API_KEY)
    claude = ClaudeProvider()
    if claude.is_available():
        return claude

    # Check OpenAI Agents SDK
    openai_agents = OpenAIAgentsProvider(model="gpt-4o-mini")
    if openai_agents.is_available():
        return openai_agents

    # Check transformers (last because can be slow)
    transformers = TransformersProvider()
    if transformers.is_available():
        return transformers

    return None


def get_best_provider() -> tuple[Optional[LLMProvider], bool]:
    """
    Get the best available provider.

    Returns:
        Tuple of (provider, is_llm) where is_llm indicates if a real LLM was found.
        If no provider is available, returns (None, False).
    """
    provider = auto_detect_provider()
    if provider:
        return provider, True
    return None, False


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
