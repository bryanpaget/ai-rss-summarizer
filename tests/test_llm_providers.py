"""Tests for llm_providers module."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from src.llm_providers import (
    LLMConfig,
    LLMProvider,
    ProviderType,
    UsageStats,
    OpenAICompatibleProvider,
    LMStudioProvider,
    OllamaProvider,
    TransformersProvider,
    ClaudeProvider,
    ClaudeCodeProvider,
    GeminiProvider,
    GeminiCLIProvider,
    CodexCLIProvider,
    GrokProvider,
    GroqProvider,
    OpenAIAgentsProvider,
    get_provider,
    list_providers,
    auto_detect_provider,
    get_best_provider,
    validate_llm_ready,
)


# =============================================================================
# Fixtures for Temporary Files and Directories
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_config_file(temp_dir):
    """Create a temporary config file path."""
    return os.path.join(temp_dir, "config", "llm.json")


@pytest.fixture
def temp_config_dir(temp_dir):
    """Create a temporary config directory."""
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


# =============================================================================
# Fixtures for Sample Config Data
# =============================================================================


@pytest.fixture
def sample_config_data():
    """Sample LLM configuration data."""
    return {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "test-api-key",
        "model": "gpt-4o-mini",
        "defaults": {"temperature": 0.3},
    }


@pytest.fixture
def sample_config_lm_studio():
    """Sample LM Studio configuration."""
    return {
        "provider": "lm-studio",
        "base_url": "http://localhost:1234/v1",
        "model": "local-model",
        "defaults": {"auto_load": {"enabled": True, "ttl_seconds": 300}},
    }


@pytest.fixture
def sample_config_ollama():
    """Sample Ollama configuration."""
    return {
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "llama2",
        "defaults": {},
    }


@pytest.fixture
def sample_config_claude():
    """Sample Claude configuration."""
    return {
        "provider": "claude",
        "model": "claude-sonnet-4-20250514",
        "defaults": {},
    }


@pytest.fixture
def sample_config_gemini():
    """Sample Gemini configuration."""
    return {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "defaults": {},
    }


@pytest.fixture
def sample_config_groq():
    """Sample Groq configuration."""
    return {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "defaults": {},
    }


@pytest.fixture
def sample_config_empty():
    """Empty configuration data."""
    return {}


@pytest.fixture
def sample_config_minimal():
    """Minimal valid configuration with just provider."""
    return {"provider": "ollama"}


# =============================================================================
# Fixtures for Config Files
# =============================================================================


@pytest.fixture
def config_file_openai(temp_config_dir, sample_config_data):
    """Create a config file with OpenAI settings."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump(sample_config_data, f)
    return config_path


@pytest.fixture
def config_file_lm_studio(temp_config_dir, sample_config_lm_studio):
    """Create a config file with LM Studio settings."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump(sample_config_lm_studio, f)
    return config_path


@pytest.fixture
def config_file_empty(temp_config_dir, sample_config_empty):
    """Create an empty config file."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump(sample_config_empty, f)
    return config_path


@pytest.fixture
def config_file_invalid_json(temp_config_dir):
    """Create a config file with invalid JSON."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        f.write("{ invalid json }")
    return config_path


@pytest.fixture
def config_file_invalid_provider(temp_config_dir):
    """Create a config file with invalid provider type."""
    config_path = os.path.join(temp_config_dir, "llm.json")
    with open(config_path, "w") as f:
        json.dump({"provider": "invalid-provider"}, f)
    return config_path


# =============================================================================
# Fixtures for Environment Variables
# =============================================================================


@pytest.fixture
def clean_env():
    """Remove all RSS-related environment variables."""
    env_vars = [
        "RSS_LLM_PROVIDER",
        "RSS_LLM_BASE_URL",
        "RSS_LLM_API_KEY",
        "RSS_LLM_MODEL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "GROQ_API_KEY",
    ]
    # Store original values
    original = {key: os.environ.get(key) for key in env_vars}

    # Remove all env vars
    for key in env_vars:
        if key in os.environ:
            del os.environ[key]

    yield

    # Restore original values
    for key, value in original.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_openai(clean_env):
    """Set OpenAI environment variables."""
    os.environ["RSS_LLM_PROVIDER"] = "openai"
    os.environ["RSS_LLM_API_KEY"] = "test-openai-key"
    os.environ["RSS_LLM_MODEL"] = "gpt-4o-mini"
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_API_KEY", "RSS_LLM_MODEL", "OPENAI_API_KEY"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_claude(clean_env):
    """Set Claude environment variables."""
    os.environ["RSS_LLM_PROVIDER"] = "claude"
    os.environ["RSS_LLM_MODEL"] = "claude-sonnet-4-20250514"
    os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_MODEL", "ANTHROPIC_API_KEY"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_gemini(clean_env):
    """Set Gemini environment variables."""
    os.environ["RSS_LLM_PROVIDER"] = "gemini"
    os.environ["RSS_LLM_MODEL"] = "gemini-1.5-flash"
    os.environ["GOOGLE_API_KEY"] = "test-google-key"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_MODEL", "GOOGLE_API_KEY"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_groq(clean_env):
    """Set Groq environment variables."""
    os.environ["RSS_LLM_PROVIDER"] = "groq"
    os.environ["RSS_LLM_MODEL"] = "llama-3.3-70b-versatile"
    os.environ["GROQ_API_KEY"] = "test-groq-key"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_MODEL", "GROQ_API_KEY"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_grok(clean_env):
    """Set Grok environment variables."""
    os.environ["RSS_LLM_PROVIDER"] = "grok"
    os.environ["RSS_LLM_MODEL"] = "grok-beta"
    os.environ["XAI_API_KEY"] = "test-xai-key"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_MODEL", "XAI_API_KEY"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_ollama(clean_env):
    """Set Ollama environment variables."""
    os.environ["RSS_LLM_PROVIDER"] = "ollama"
    os.environ["RSS_LLM_MODEL"] = "llama2"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_MODEL"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def env_lm_studio(clean_env):
    """Set LM Studio environment variables."""
    os.environ["RSS_LLM_PROVIDER"] = "lm-studio"
    os.environ["RSS_LLM_MODEL"] = "local-model"
    yield
    for key in ["RSS_LLM_PROVIDER", "RSS_LLM_MODEL"]:
        if key in os.environ:
            del os.environ[key]


# =============================================================================
# Fixtures for Mock HTTP Responses
# =============================================================================


@pytest.fixture
def mock_httpx_success():
    """Mock httpx for successful API responses."""
    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        # Mock successful models endpoint
        models_response = MagicMock()
        models_response.status_code = 200
        models_response.json.return_value = {
            "data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]
        }
        mock_get.return_value = models_response

        # Mock successful chat completion
        completion_response = MagicMock()
        completion_response.status_code = 200
        completion_response.json.return_value = {
            "choices": [{"message": {"content": "Test summary"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        }
        completion_response.raise_for_status = MagicMock()
        mock_post.return_value = completion_response

        yield {"get": mock_get, "post": mock_post}


@pytest.fixture
def mock_httpx_unavailable():
    """Mock httpx for unavailable API."""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        yield mock_get


@pytest.fixture
def mock_httpx_error():
    """Mock httpx for API error response."""
    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        # Mock models endpoint returning error
        mock_get.side_effect = Exception("Connection timeout")

        # Mock post returning error
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = Exception("Internal Server Error")
        mock_post.return_value = error_response

        yield {"get": mock_get, "post": mock_post}


@pytest.fixture
def mock_httpx_rate_limit():
    """Mock httpx for rate limit response."""
    with patch("httpx.post") as mock_post:
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.json.return_value = {
            "error": {"message": "Rate limit exceeded"}
        }
        rate_limit_response.raise_for_status.side_effect = Exception("Rate limit exceeded")
        mock_post.return_value = rate_limit_response
        yield mock_post


@pytest.fixture
def mock_httpx_no_models():
    """Mock httpx for endpoint with no models loaded."""
    with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
        # Mock models endpoint returning 200 but empty
        models_response = MagicMock()
        models_response.status_code = 200
        models_response.json.return_value = {"data": []}
        mock_get.return_value = models_response

        # Mock chat completion returning "no models loaded" error
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {
            "error": {"message": "No models loaded"}
        }
        mock_post.return_value = error_response

        yield {"get": mock_get, "post": mock_post}


# =============================================================================
# Fixtures for Mock CLI Commands
# =============================================================================


@pytest.fixture
def mock_shutil_which_claude():
    """Mock shutil.which to indicate Claude CLI is available."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/claude"
        yield mock_which


@pytest.fixture
def mock_shutil_which_gemini():
    """Mock shutil.which to indicate Gemini CLI is available."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/gemini"
        yield mock_which


@pytest.fixture
def mock_shutil_which_codex():
    """Mock shutil.which to indicate Codex CLI is available."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/codex"
        yield mock_which


@pytest.fixture
def mock_shutil_which_none():
    """Mock shutil.which to indicate no CLI is available."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        yield mock_which


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess for successful CLI execution."""
    with patch("subprocess.run") as mock_run:
        result = MagicMock()
        result.returncode = 0
        result.stdout = '{"result": "Test summary", "usage": {"tokens": 100}}'
        result.stderr = ""
        mock_run.return_value = result
        yield mock_run


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess for failed CLI execution."""
    with patch("subprocess.run") as mock_run:
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "Command failed"
        mock_run.return_value = result
        yield mock_run


@pytest.fixture
def mock_subprocess_timeout():
    """Mock subprocess for CLI timeout."""
    import subprocess

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=60)
        yield mock_run


# =============================================================================
# Fixtures for Mock Provider Instances
# =============================================================================


@pytest.fixture
def mock_provider_available():
    """Create a mock provider that is available."""

    class MockProvider(LLMProvider):
        def __init__(self):
            super().__init__()
            self._is_available = True
            self._summarize_response = "Mock summary"

        @property
        def name(self) -> str:
            return "Mock Provider"

        def is_available(self) -> bool:
            return self._is_available

        def summarize(self, text: str, max_length: int = 150) -> str:
            self._record_usage(text, self._summarize_response, "mock-model")
            return self._summarize_response

    return MockProvider()


@pytest.fixture
def mock_provider_unavailable():
    """Create a mock provider that is unavailable."""

    class MockProvider(LLMProvider):
        def __init__(self):
            super().__init__()
            self._is_available = False

        @property
        def name(self) -> str:
            return "Unavailable Provider"

        def is_available(self) -> bool:
            return self._is_available

        def summarize(self, text: str, max_length: int = 150) -> str:
            raise RuntimeError("Provider not available")

    return MockProvider()


# =============================================================================
# Fixtures for Sample Text Data
# =============================================================================


@pytest.fixture
def sample_text_short():
    """Short sample text for summarization."""
    return "This is a short article about Python programming."


@pytest.fixture
def sample_text_long():
    """Long sample text for summarization."""
    return """
    Python is a high-level, general-purpose programming language. Its design philosophy
    emphasizes code readability with the use of significant indentation. Python is
    dynamically typed and garbage-collected. It supports multiple programming paradigms,
    including structured, object-oriented, and functional programming.

    Python was conceived in the late 1980s by Guido van Rossum at Centrum Wiskunde &
    Informatica (CWI) in the Netherlands as a successor to the ABC programming language,
    which was inspired by SETL, capable of exception handling and interfacing with the
    Amoeba operating system. Its implementation began in December 1989.

    Python consistently ranks as one of the most popular programming languages.
    """ * 3


@pytest.fixture
def sample_text_empty():
    """Empty sample text."""
    return ""


@pytest.fixture
def sample_text_unicode():
    """Unicode sample text for summarization."""
    return "Python supports Unicode: 日本語, 中文, العربية, ελληνικά, עברית"


# =============================================================================
# Fixtures for LLMConfig Instances
# =============================================================================


@pytest.fixture
def config_openai():
    """Create an LLMConfig for OpenAI."""
    return LLMConfig(
        provider=ProviderType.OPENAI,
        base_url="https://api.openai.com/v1",
        api_key="test-api-key",
        model="gpt-4o-mini",
        defaults={"temperature": 0.3},
    )


@pytest.fixture
def config_lm_studio():
    """Create an LLMConfig for LM Studio."""
    return LLMConfig(
        provider=ProviderType.LM_STUDIO,
        base_url="http://localhost:1234/v1",
        model="local-model",
        defaults={"auto_load": {"enabled": True}},
    )


@pytest.fixture
def config_ollama():
    """Create an LLMConfig for Ollama."""
    return LLMConfig(
        provider=ProviderType.OLLAMA,
        model="llama2",
        defaults={},
    )


@pytest.fixture
def config_claude():
    """Create an LLMConfig for Claude."""
    return LLMConfig(
        provider=ProviderType.CLAUDE,
        model="claude-sonnet-4-20250514",
        defaults={},
    )


@pytest.fixture
def config_gemini():
    """Create an LLMConfig for Gemini."""
    return LLMConfig(
        provider=ProviderType.GEMINI,
        model="gemini-1.5-flash",
        defaults={},
    )


@pytest.fixture
def config_groq():
    """Create an LLMConfig for Groq."""
    return LLMConfig(
        provider=ProviderType.GROQ,
        model="llama-3.3-70b-versatile",
        defaults={},
    )


@pytest.fixture
def config_grok():
    """Create an LLMConfig for Grok."""
    return LLMConfig(
        provider=ProviderType.GROK,
        model="grok-beta",
        defaults={},
    )


@pytest.fixture
def config_openai_compatible():
    """Create an LLMConfig for OpenAI-compatible provider."""
    return LLMConfig(
        provider=ProviderType.OPENAI_COMPATIBLE,
        base_url="https://custom-api.example.com/v1",
        api_key="custom-key",
        model="custom-model",
        defaults={},
    )


@pytest.fixture
def config_empty():
    """Create an empty LLMConfig."""
    return LLMConfig()


# =============================================================================
# Fixtures for UsageStats Instances
# =============================================================================


@pytest.fixture
def usage_stats_basic():
    """Create basic usage stats."""
    return UsageStats(
        input_tokens=100,
        output_tokens=50,
        model="gpt-4o-mini",
        provider="OpenAI",
    )


@pytest.fixture
def usage_stats_with_total():
    """Create usage stats with explicit total."""
    return UsageStats(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        model="gpt-4o-mini",
        provider="OpenAI",
    )


@pytest.fixture
def usage_stats_empty():
    """Create empty usage stats."""
    return UsageStats()


# =============================================================================
# Fixtures for Provider Type Enumeration
# =============================================================================


@pytest.fixture
def all_provider_types():
    """Return all available provider types."""
    return list(ProviderType)


@pytest.fixture
def local_provider_types():
    """Return local provider types (no API key needed for basic functionality)."""
    return [
        ProviderType.LM_STUDIO,
        ProviderType.OLLAMA,
        ProviderType.TRANSFORMERS,
        ProviderType.CLAUDE_CODE,
        ProviderType.GEMINI_CLI,
        ProviderType.CODEX_CLI,
    ]


@pytest.fixture
def api_provider_types():
    """Return API-based provider types (require API key)."""
    return [
        ProviderType.OPENAI,
        ProviderType.OPENAI_COMPATIBLE,
        ProviderType.CLAUDE,
        ProviderType.GEMINI,
        ProviderType.GROK,
        ProviderType.GROQ,
    ]


# =============================================================================
# Fixtures for Mock Import Scenarios
# =============================================================================


@pytest.fixture
def mock_anthropic_available():
    """Mock anthropic SDK being available."""
    with patch.dict("sys.modules", {"anthropic": MagicMock()}):
        yield


@pytest.fixture
def mock_anthropic_unavailable():
    """Mock anthropic SDK being unavailable."""
    import sys
    original = sys.modules.get("anthropic")
    sys.modules["anthropic"] = None
    yield
    if original is not None:
        sys.modules["anthropic"] = original
    elif "anthropic" in sys.modules:
        del sys.modules["anthropic"]


@pytest.fixture
def mock_google_genai_available():
    """Mock google.generativeai SDK being available."""
    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Mock Gemini summary"
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model
    with patch.dict("sys.modules", {"google": MagicMock(), "google.generativeai": mock_genai}):
        yield mock_genai


@pytest.fixture
def mock_transformers_available():
    """Mock transformers library being available."""
    mock_transformers = MagicMock()
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [{"summary_text": "Mock summary"}]
    mock_transformers.pipeline.return_value = mock_pipeline
    with patch.dict("sys.modules", {"transformers": mock_transformers, "torch": MagicMock()}):
        yield


@pytest.fixture
def mock_transformers_unavailable():
    """Mock transformers library being unavailable."""
    import sys
    original_transformers = sys.modules.get("transformers")
    original_torch = sys.modules.get("torch")

    # Set to None to simulate ImportError
    sys.modules["transformers"] = None
    sys.modules["torch"] = None

    yield

    # Restore
    if original_transformers is not None:
        sys.modules["transformers"] = original_transformers
    elif "transformers" in sys.modules:
        del sys.modules["transformers"]

    if original_torch is not None:
        sys.modules["torch"] = original_torch
    elif "torch" in sys.modules:
        del sys.modules["torch"]


@pytest.fixture
def mock_agents_available():
    """Mock OpenAI Agents SDK being available."""
    mock_agents = MagicMock()
    mock_agent = MagicMock()
    mock_runner = MagicMock()
    mock_result = MagicMock()
    mock_result.final_output = "Mock agent summary"
    mock_runner.run_sync.return_value = mock_result
    mock_agents.Agent.return_value = mock_agent
    mock_agents.Runner = mock_runner
    with patch.dict("sys.modules", {"agents": mock_agents}):
        yield mock_agents


# =============================================================================
# Fixtures for Edge Cases
# =============================================================================


@pytest.fixture
def config_with_sk_api_key():
    """Config with API key starting with 'sk-' (should not be saved to file)."""
    return LLMConfig(
        provider=ProviderType.OPENAI,
        api_key="sk-test-secret-key-12345",
        model="gpt-4o-mini",
    )


@pytest.fixture
def config_with_safe_api_key():
    """Config with API key not starting with 'sk-' (can be saved to file)."""
    return LLMConfig(
        provider=ProviderType.GROQ,
        api_key="gsk_test_groq_key_12345",
        model="llama-3.3-70b-versatile",
    )


@pytest.fixture
def mock_all_providers_unavailable(mock_httpx_unavailable, mock_shutil_which_none, clean_env):
    """Mock all providers being unavailable."""
    yield
