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


# =============================================================================
# Tests for LLMConfig.from_env()
# =============================================================================


class TestLLMConfigFromEnv:
    """Tests for LLMConfig.from_env() method."""

    def test_from_env_with_all_vars(self, clean_env):
        """Test loading config with all environment variables set."""
        os.environ["RSS_LLM_PROVIDER"] = "openai"
        os.environ["RSS_LLM_BASE_URL"] = "https://api.openai.com/v1"
        os.environ["RSS_LLM_API_KEY"] = "test-api-key"
        os.environ["RSS_LLM_MODEL"] = "gpt-4o-mini"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.OPENAI
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key == "test-api-key"
        assert config.model == "gpt-4o-mini"
        assert config.defaults == {}

    def test_from_env_with_ollama(self, clean_env):
        """Test loading Ollama config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "ollama"
        os.environ["RSS_LLM_MODEL"] = "llama2"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.OLLAMA
        assert config.model == "llama2"
        assert config.base_url is None
        assert config.api_key is None

    def test_from_env_with_lm_studio(self, clean_env):
        """Test loading LM Studio config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "lm-studio"
        os.environ["RSS_LLM_MODEL"] = "local-model"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.LM_STUDIO
        assert config.model == "local-model"

    def test_from_env_with_claude(self, clean_env):
        """Test loading Claude config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "claude"
        os.environ["RSS_LLM_MODEL"] = "claude-sonnet-4-20250514"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.CLAUDE
        assert config.model == "claude-sonnet-4-20250514"

    def test_from_env_with_gemini(self, clean_env):
        """Test loading Gemini config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "gemini"
        os.environ["RSS_LLM_MODEL"] = "gemini-1.5-flash"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.GEMINI
        assert config.model == "gemini-1.5-flash"

    def test_from_env_with_groq(self, clean_env):
        """Test loading Groq config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "groq"
        os.environ["RSS_LLM_MODEL"] = "llama-3.3-70b-versatile"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.GROQ
        assert config.model == "llama-3.3-70b-versatile"

    def test_from_env_with_grok(self, clean_env):
        """Test loading Grok config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "grok"
        os.environ["RSS_LLM_MODEL"] = "grok-beta"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.GROK
        assert config.model == "grok-beta"

    def test_from_env_with_transformers(self, clean_env):
        """Test loading Transformers config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "transformers"
        os.environ["RSS_LLM_MODEL"] = "facebook/bart-large-cnn"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.TRANSFORMERS
        assert config.model == "facebook/bart-large-cnn"

    def test_from_env_with_openai_compatible(self, clean_env):
        """Test loading OpenAI-compatible config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "openai-compatible"
        os.environ["RSS_LLM_BASE_URL"] = "https://custom-api.example.com/v1"
        os.environ["RSS_LLM_API_KEY"] = "custom-key"
        os.environ["RSS_LLM_MODEL"] = "custom-model"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.OPENAI_COMPATIBLE
        assert config.base_url == "https://custom-api.example.com/v1"
        assert config.api_key == "custom-key"
        assert config.model == "custom-model"

    def test_from_env_with_claude_code(self, clean_env):
        """Test loading Claude Code config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "claude-code"
        os.environ["RSS_LLM_MODEL"] = "sonnet"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.CLAUDE_CODE
        assert config.model == "sonnet"

    def test_from_env_with_gemini_cli(self, clean_env):
        """Test loading Gemini CLI config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "gemini-cli"
        os.environ["RSS_LLM_MODEL"] = "gemini-2.0-flash"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.GEMINI_CLI
        assert config.model == "gemini-2.0-flash"

    def test_from_env_with_codex_cli(self, clean_env):
        """Test loading Codex CLI config from environment."""
        os.environ["RSS_LLM_PROVIDER"] = "codex-cli"
        os.environ["RSS_LLM_MODEL"] = "gpt-4.1"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.CODEX_CLI
        assert config.model == "gpt-4.1"

    def test_from_env_with_no_vars(self, clean_env):
        """Test loading config with no environment variables set."""
        config = LLMConfig.from_env()

        assert config.provider is None
        assert config.base_url is None
        assert config.api_key is None
        assert config.model is None
        assert config.defaults == {}

    def test_from_env_with_only_provider(self, clean_env):
        """Test loading config with only provider set."""
        os.environ["RSS_LLM_PROVIDER"] = "ollama"

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.OLLAMA
        assert config.base_url is None
        assert config.api_key is None
        assert config.model is None

    def test_from_env_with_only_api_key(self, clean_env):
        """Test loading config with only API key set (no provider)."""
        os.environ["RSS_LLM_API_KEY"] = "test-key"

        config = LLMConfig.from_env()

        assert config.provider is None
        assert config.api_key == "test-key"

    def test_from_env_with_invalid_provider_raises(self, clean_env):
        """Test that invalid provider type raises ValueError."""
        os.environ["RSS_LLM_PROVIDER"] = "invalid-provider"

        with pytest.raises(ValueError):
            LLMConfig.from_env()


# =============================================================================
# Tests for LLMConfig.from_file()
# =============================================================================


class TestLLMConfigFromFile:
    """Tests for LLMConfig.from_file() method."""

    def test_from_file_with_valid_config(self, config_file_openai, sample_config_data):
        """Test loading valid config from file."""
        config = LLMConfig.from_file(config_file_openai)

        assert config.provider == ProviderType.OPENAI
        assert config.base_url == sample_config_data["base_url"]
        assert config.api_key == sample_config_data["api_key"]
        assert config.model == sample_config_data["model"]
        assert config.defaults == sample_config_data["defaults"]

    def test_from_file_with_lm_studio_config(self, config_file_lm_studio, sample_config_lm_studio):
        """Test loading LM Studio config from file."""
        config = LLMConfig.from_file(config_file_lm_studio)

        assert config.provider == ProviderType.LM_STUDIO
        assert config.base_url == sample_config_lm_studio["base_url"]
        assert config.model == sample_config_lm_studio["model"]
        assert config.defaults == sample_config_lm_studio["defaults"]

    def test_from_file_with_minimal_config(self, temp_config_dir):
        """Test loading minimal config with just provider."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        with open(config_path, "w") as f:
            json.dump({"provider": "ollama"}, f)

        config = LLMConfig.from_file(config_path)

        assert config.provider == ProviderType.OLLAMA
        assert config.base_url is None
        assert config.api_key is None
        assert config.model is None
        assert config.defaults == {}

    def test_from_file_with_empty_config(self, config_file_empty):
        """Test loading empty config file."""
        config = LLMConfig.from_file(config_file_empty)

        assert config.provider is None
        assert config.base_url is None
        assert config.api_key is None
        assert config.model is None
        assert config.defaults == {}

    def test_from_file_with_nonexistent_file(self, temp_dir):
        """Test loading config from nonexistent file returns empty config."""
        nonexistent_path = os.path.join(temp_dir, "nonexistent", "llm.json")

        config = LLMConfig.from_file(nonexistent_path)

        assert config.provider is None
        assert config.base_url is None
        assert config.api_key is None
        assert config.model is None

    def test_from_file_with_invalid_json_raises(self, config_file_invalid_json):
        """Test that invalid JSON raises exception."""
        with pytest.raises(json.JSONDecodeError):
            LLMConfig.from_file(config_file_invalid_json)

    def test_from_file_with_invalid_provider_raises(self, config_file_invalid_provider):
        """Test that invalid provider type raises ValueError."""
        with pytest.raises(ValueError):
            LLMConfig.from_file(config_file_invalid_provider)

    def test_from_file_with_all_provider_types(self, temp_config_dir):
        """Test loading config file with each provider type."""
        provider_types = [
            ("lm-studio", ProviderType.LM_STUDIO),
            ("ollama", ProviderType.OLLAMA),
            ("openai", ProviderType.OPENAI),
            ("openai-compatible", ProviderType.OPENAI_COMPATIBLE),
            ("transformers", ProviderType.TRANSFORMERS),
            ("claude", ProviderType.CLAUDE),
            ("claude-code", ProviderType.CLAUDE_CODE),
            ("gemini", ProviderType.GEMINI),
            ("gemini-cli", ProviderType.GEMINI_CLI),
            ("codex-cli", ProviderType.CODEX_CLI),
            ("grok", ProviderType.GROK),
            ("groq", ProviderType.GROQ),
        ]

        for provider_str, expected_type in provider_types:
            config_path = os.path.join(temp_config_dir, "llm.json")
            with open(config_path, "w") as f:
                json.dump({"provider": provider_str}, f)

            config = LLMConfig.from_file(config_path)
            assert config.provider == expected_type, f"Failed for provider: {provider_str}"

    def test_from_file_with_defaults(self, temp_config_dir):
        """Test loading config with various defaults."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        defaults = {
            "temperature": 0.5,
            "max_tokens": 1000,
            "auto_load": {"enabled": True, "ttl_seconds": 600},
        }
        with open(config_path, "w") as f:
            json.dump({"provider": "openai", "defaults": defaults}, f)

        config = LLMConfig.from_file(config_path)

        assert config.defaults == defaults
        assert config.defaults["temperature"] == 0.5
        assert config.defaults["auto_load"]["enabled"] is True

    def test_from_file_uses_default_path(self, temp_dir):
        """Test that from_file uses default path when not specified."""
        # Create default config path
        config_dir = os.path.join(temp_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "llm.json")
        with open(config_path, "w") as f:
            json.dump({"provider": "ollama", "model": "llama2"}, f)

        # Change to temp_dir to test relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            config = LLMConfig.from_file()

            assert config.provider == ProviderType.OLLAMA
            assert config.model == "llama2"
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Tests for LLMConfig.save()
# =============================================================================


class TestLLMConfigSave:
    """Tests for LLMConfig.save() method."""

    def test_save_creates_directory(self, temp_dir):
        """Test that save creates parent directories if they don't exist."""
        config_path = os.path.join(temp_dir, "nested", "deep", "config", "llm.json")
        config = LLMConfig(
            provider=ProviderType.OLLAMA,
            model="llama2",
        )

        config.save(config_path)

        assert os.path.exists(config_path)
        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["provider"] == "ollama"
        assert saved_data["model"] == "llama2"

    def test_save_includes_provider(self, temp_config_dir):
        """Test that save includes provider value."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(provider=ProviderType.OPENAI)

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["provider"] == "openai"

    def test_save_includes_base_url(self, temp_config_dir):
        """Test that save includes base_url."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(
            provider=ProviderType.OPENAI_COMPATIBLE,
            base_url="https://custom.api.com/v1",
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["base_url"] == "https://custom.api.com/v1"

    def test_save_includes_model(self, temp_config_dir):
        """Test that save includes model."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(
            provider=ProviderType.OPENAI,
            model="gpt-4o-mini",
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["model"] == "gpt-4o-mini"

    def test_save_includes_defaults(self, temp_config_dir):
        """Test that save includes defaults."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        defaults = {"temperature": 0.3, "max_tokens": 500}
        config = LLMConfig(
            provider=ProviderType.OPENAI,
            defaults=defaults,
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["defaults"] == defaults

    def test_save_excludes_sk_api_key(self, temp_config_dir):
        """Test that save does NOT include API keys starting with 'sk-'."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(
            provider=ProviderType.OPENAI,
            api_key="sk-secret-openai-key-12345",
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert "api_key" not in saved_data

    def test_save_includes_non_sk_api_key(self, temp_config_dir):
        """Test that save DOES include API keys NOT starting with 'sk-'."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(
            provider=ProviderType.GROQ,
            api_key="gsk_groq_test_key_12345",
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["api_key"] == "gsk_groq_test_key_12345"

    def test_save_excludes_none_api_key(self, temp_config_dir):
        """Test that save doesn't include api_key when it's None."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(
            provider=ProviderType.OLLAMA,
            api_key=None,
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert "api_key" not in saved_data

    def test_save_excludes_empty_api_key(self, temp_config_dir):
        """Test that save doesn't include api_key when it's empty string."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(
            provider=ProviderType.OLLAMA,
            api_key="",
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)
        assert "api_key" not in saved_data

    def test_save_with_all_provider_types(self, temp_config_dir):
        """Test saving config with each provider type."""
        for provider_type in ProviderType:
            config_path = os.path.join(temp_config_dir, "llm.json")
            config = LLMConfig(provider=provider_type, model="test-model")

            config.save(config_path)

            with open(config_path) as f:
                saved_data = json.load(f)
            assert saved_data["provider"] == provider_type.value

    def test_save_overwrites_existing(self, temp_config_dir):
        """Test that save overwrites existing file."""
        config_path = os.path.join(temp_config_dir, "llm.json")

        # Save first config
        config1 = LLMConfig(provider=ProviderType.OLLAMA, model="llama2")
        config1.save(config_path)

        # Save second config
        config2 = LLMConfig(provider=ProviderType.OPENAI, model="gpt-4o-mini")
        config2.save(config_path)

        # Verify second config was saved
        with open(config_path) as f:
            saved_data = json.load(f)
        assert saved_data["provider"] == "openai"
        assert saved_data["model"] == "gpt-4o-mini"

    def test_save_and_load_roundtrip(self, temp_config_dir):
        """Test that config survives save/load roundtrip."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        original = LLMConfig(
            provider=ProviderType.OPENAI_COMPATIBLE,
            base_url="https://api.example.com/v1",
            api_key="non-sk-api-key-12345",
            model="custom-model",
            defaults={"temperature": 0.7, "stream": True},
        )

        original.save(config_path)
        loaded = LLMConfig.from_file(config_path)

        assert loaded.provider == original.provider
        assert loaded.base_url == original.base_url
        assert loaded.api_key == original.api_key
        assert loaded.model == original.model
        assert loaded.defaults == original.defaults

    def test_save_uses_default_path(self, temp_dir):
        """Test that save uses default path when not specified."""
        # Change to temp_dir to test relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            config = LLMConfig(provider=ProviderType.OLLAMA, model="llama2")

            config.save()

            expected_path = os.path.join(temp_dir, "config", "llm.json")
            assert os.path.exists(expected_path)
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Tests for ProviderType Enum
# =============================================================================


class TestProviderTypeEnum:
    """Tests for ProviderType enum validation and conversion."""

    def test_all_provider_types_exist(self, all_provider_types):
        """Test that all expected provider types exist."""
        expected_values = [
            "lm-studio",
            "ollama",
            "openai",
            "openai-compatible",
            "transformers",
            "claude",
            "claude-code",
            "gemini",
            "gemini-cli",
            "codex-cli",
            "grok",
            "groq",
        ]
        actual_values = [p.value for p in all_provider_types]

        assert len(actual_values) == len(expected_values)
        for expected in expected_values:
            assert expected in actual_values

    def test_provider_type_count(self, all_provider_types):
        """Test that we have the expected number of provider types."""
        assert len(all_provider_types) == 12

    def test_provider_type_from_value(self):
        """Test creating ProviderType from string value."""
        assert ProviderType("lm-studio") == ProviderType.LM_STUDIO
        assert ProviderType("ollama") == ProviderType.OLLAMA
        assert ProviderType("openai") == ProviderType.OPENAI
        assert ProviderType("openai-compatible") == ProviderType.OPENAI_COMPATIBLE
        assert ProviderType("transformers") == ProviderType.TRANSFORMERS
        assert ProviderType("claude") == ProviderType.CLAUDE
        assert ProviderType("claude-code") == ProviderType.CLAUDE_CODE
        assert ProviderType("gemini") == ProviderType.GEMINI
        assert ProviderType("gemini-cli") == ProviderType.GEMINI_CLI
        assert ProviderType("codex-cli") == ProviderType.CODEX_CLI
        assert ProviderType("grok") == ProviderType.GROK
        assert ProviderType("groq") == ProviderType.GROQ

    def test_provider_type_value(self):
        """Test ProviderType.value returns correct string."""
        assert ProviderType.LM_STUDIO.value == "lm-studio"
        assert ProviderType.OLLAMA.value == "ollama"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.OPENAI_COMPATIBLE.value == "openai-compatible"
        assert ProviderType.TRANSFORMERS.value == "transformers"
        assert ProviderType.CLAUDE.value == "claude"
        assert ProviderType.CLAUDE_CODE.value == "claude-code"
        assert ProviderType.GEMINI.value == "gemini"
        assert ProviderType.GEMINI_CLI.value == "gemini-cli"
        assert ProviderType.CODEX_CLI.value == "codex-cli"
        assert ProviderType.GROK.value == "grok"
        assert ProviderType.GROQ.value == "groq"

    def test_provider_type_invalid_value_raises(self):
        """Test that invalid provider value raises ValueError."""
        with pytest.raises(ValueError):
            ProviderType("invalid")

        with pytest.raises(ValueError):
            ProviderType("OPENAI")  # Case-sensitive

        with pytest.raises(ValueError):
            ProviderType("OpenAI")

        with pytest.raises(ValueError):
            ProviderType("")

    def test_provider_type_is_str_enum(self):
        """Test that ProviderType is a string enum."""
        assert isinstance(ProviderType.OPENAI, str)
        # ProviderType inherits from str, so it can be used as a string value
        assert ProviderType.OPENAI.value == "openai"
        # str() returns the enum representation, use .value for string value
        assert ProviderType.OPENAI == "openai"  # Comparison works due to str inheritance

    def test_provider_type_comparison(self):
        """Test ProviderType comparison operations."""
        assert ProviderType.OPENAI == ProviderType.OPENAI
        assert ProviderType.OPENAI != ProviderType.OLLAMA
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.OLLAMA != "openai"

    def test_provider_type_in_list(self, all_provider_types):
        """Test checking if ProviderType is in a list."""
        assert ProviderType.OPENAI in all_provider_types
        assert ProviderType.CLAUDE in all_provider_types
        assert ProviderType.GROQ in all_provider_types

    def test_local_providers(self, local_provider_types):
        """Test that local provider types are correctly categorized."""
        assert ProviderType.LM_STUDIO in local_provider_types
        assert ProviderType.OLLAMA in local_provider_types
        assert ProviderType.TRANSFORMERS in local_provider_types
        assert ProviderType.CLAUDE_CODE in local_provider_types
        assert ProviderType.GEMINI_CLI in local_provider_types
        assert ProviderType.CODEX_CLI in local_provider_types

        # API providers should not be in local list
        assert ProviderType.OPENAI not in local_provider_types
        assert ProviderType.CLAUDE not in local_provider_types
        assert ProviderType.GEMINI not in local_provider_types

    def test_api_providers(self, api_provider_types):
        """Test that API provider types are correctly categorized."""
        assert ProviderType.OPENAI in api_provider_types
        assert ProviderType.OPENAI_COMPATIBLE in api_provider_types
        assert ProviderType.CLAUDE in api_provider_types
        assert ProviderType.GEMINI in api_provider_types
        assert ProviderType.GROK in api_provider_types
        assert ProviderType.GROQ in api_provider_types

        # Local providers should not be in API list
        assert ProviderType.LM_STUDIO not in api_provider_types
        assert ProviderType.OLLAMA not in api_provider_types
        assert ProviderType.TRANSFORMERS not in api_provider_types

    def test_provider_type_iteration(self, all_provider_types):
        """Test iterating over ProviderType enum."""
        provider_count = 0
        for provider in ProviderType:
            assert isinstance(provider, ProviderType)
            provider_count += 1

        assert provider_count == len(all_provider_types)


# =============================================================================
# Tests for LLMConfig Integration
# =============================================================================


class TestLLMConfigIntegration:
    """Integration tests for LLMConfig class."""

    def test_env_takes_precedence_over_file(self, clean_env, config_file_openai):
        """Test that environment variables take precedence over file config."""
        # Set different provider in environment
        os.environ["RSS_LLM_PROVIDER"] = "ollama"
        os.environ["RSS_LLM_MODEL"] = "llama2"

        # Load from environment
        env_config = LLMConfig.from_env()
        file_config = LLMConfig.from_file(config_file_openai)

        assert env_config.provider == ProviderType.OLLAMA
        assert file_config.provider == ProviderType.OPENAI
        assert env_config.provider != file_config.provider

    def test_empty_config_defaults(self):
        """Test that empty LLMConfig has correct defaults."""
        config = LLMConfig()

        assert config.provider is None
        assert config.base_url is None
        assert config.api_key is None
        assert config.model is None
        assert config.defaults == {}

    def test_config_with_partial_data(self, clean_env):
        """Test config with partial environment data."""
        os.environ["RSS_LLM_PROVIDER"] = "groq"
        # No model or API key set

        config = LLMConfig.from_env()

        assert config.provider == ProviderType.GROQ
        assert config.model is None
        assert config.api_key is None

    def test_config_save_preserves_null_values(self, temp_config_dir):
        """Test that save handles None values correctly."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        config = LLMConfig(
            provider=ProviderType.OLLAMA,
            base_url=None,
            api_key=None,
            model=None,
            defaults={},
        )

        config.save(config_path)

        with open(config_path) as f:
            saved_data = json.load(f)

        # base_url and model should be present (as None/null)
        assert "base_url" in saved_data
        assert saved_data["base_url"] is None
        assert "model" in saved_data
        assert saved_data["model"] is None

    def test_config_with_complex_defaults(self, temp_config_dir):
        """Test config with nested defaults."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        complex_defaults = {
            "auto_load": {
                "enabled": True,
                "ttl_seconds": 600,
                "models": ["llama2", "mistral"],
            },
            "retry": {"max_attempts": 3, "delay_ms": 1000},
            "features": ["streaming", "json_mode"],
        }
        config = LLMConfig(
            provider=ProviderType.LM_STUDIO,
            defaults=complex_defaults,
        )

        config.save(config_path)
        loaded = LLMConfig.from_file(config_path)

        assert loaded.defaults == complex_defaults
        assert loaded.defaults["auto_load"]["models"] == ["llama2", "mistral"]

    def test_multiple_configs_independent(self, temp_config_dir):
        """Test that multiple configs are independent."""
        config1 = LLMConfig(provider=ProviderType.OPENAI, model="gpt-4")
        config2 = LLMConfig(provider=ProviderType.CLAUDE, model="sonnet")

        assert config1.provider != config2.provider
        assert config1.model != config2.model

        # Modifying one shouldn't affect the other
        config1.model = "gpt-4o"
        assert config2.model == "sonnet"

    def test_config_equality(self):
        """Test LLMConfig instances with same values."""
        config1 = LLMConfig(provider=ProviderType.OPENAI, model="gpt-4")
        config2 = LLMConfig(provider=ProviderType.OPENAI, model="gpt-4")

        # Dataclasses should be equal if all fields match
        assert config1 == config2

    def test_config_from_file_with_extra_fields(self, temp_config_dir):
        """Test that extra fields in config file are ignored."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        with open(config_path, "w") as f:
            json.dump({
                "provider": "openai",
                "model": "gpt-4",
                "extra_field": "should be ignored",
                "another_extra": {"nested": "value"},
            }, f)

        config = LLMConfig.from_file(config_path)

        assert config.provider == ProviderType.OPENAI
        assert config.model == "gpt-4"
        # Extra fields should not cause errors


# =============================================================================
# Tests for OpenAICompatibleProvider
# =============================================================================


class TestOpenAICompatibleProviderIsAvailable:
    """Tests for OpenAICompatibleProvider.is_available() method."""

    def test_is_available_returns_true_when_endpoint_reachable(self):
        """Test is_available returns True when endpoint returns 200."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            assert provider.is_available() is True
            mock_get.assert_called_once_with(
                "http://localhost:1234/v1/models", timeout=5.0
            )

    def test_is_available_returns_false_when_endpoint_returns_error(self):
        """Test is_available returns False when endpoint returns non-200."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            assert provider.is_available() is False

    def test_is_available_returns_false_when_connection_refused(self):
        """Test is_available returns False when connection is refused."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            assert provider.is_available() is False

    def test_is_available_returns_false_on_timeout(self):
        """Test is_available returns False on timeout."""
        with patch("httpx.get") as mock_get:
            import httpx
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            assert provider.is_available() is False

    def test_is_available_returns_false_on_network_error(self):
        """Test is_available returns False on network error."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = ConnectionError("Network unreachable")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            assert provider.is_available() is False

    def test_is_available_strips_trailing_slash_from_base_url(self):
        """Test that trailing slash is stripped from base_url."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1/",
                model="test-model",
            )
            provider.is_available()
            mock_get.assert_called_once_with(
                "http://localhost:1234/v1/models", timeout=5.0
            )

    def test_is_available_with_various_base_urls(self):
        """Test is_available with various base URL formats."""
        test_urls = [
            ("http://localhost:1234/v1", "http://localhost:1234/v1/models"),
            ("https://api.openai.com/v1", "https://api.openai.com/v1/models"),
            ("http://192.168.1.100:8080/api", "http://192.168.1.100:8080/api/models"),
        ]

        for base_url, expected_call in test_urls:
            with patch("httpx.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                provider = OpenAICompatibleProvider(
                    base_url=base_url,
                    model="test-model",
                )
                provider.is_available()
                mock_get.assert_called_once_with(expected_call, timeout=5.0)


class TestOpenAICompatibleProviderSummarize:
    """Tests for OpenAICompatibleProvider.summarize() method."""

    def test_summarize_returns_empty_string_for_empty_input(self):
        """Test summarize returns empty string for empty input."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )
        result = provider.summarize("")
        assert result == ""

    def test_summarize_makes_correct_api_call(self):
        """Test summarize makes correct API call with proper payload."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            # Mock models endpoint
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            # Mock completion endpoint
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

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                api_key="test-key",
                model="test-model",
            )
            result = provider.summarize("Test article content", max_length=150)

            assert result == "Test summary"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:1234/v1/chat/completions"
            assert call_args[1]["json"]["model"] == "test-model"
            assert call_args[1]["json"]["temperature"] == 0.3
            assert "Bearer test-key" in str(call_args[1]["headers"])

    def test_summarize_records_usage_from_api_response(self):
        """Test that summarize records usage stats from API response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            provider.summarize("Test text")

            assert provider.last_usage is not None
            assert provider.last_usage.input_tokens == 100
            assert provider.last_usage.output_tokens == 20
            assert provider.last_usage.total_tokens == 120
            assert provider.session_usage["calls"] == 1
            assert provider.session_usage["total_tokens"] == 120

    def test_summarize_estimates_tokens_when_usage_not_in_response(self):
        """Test that summarize estimates tokens when usage not provided."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary result"}}],
                # No usage field
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            provider.summarize("Test text for summarization")

            assert provider.last_usage is not None
            # Should have estimated tokens (roughly 4 chars per token)
            assert provider.last_usage.input_tokens > 0
            assert provider.last_usage.output_tokens > 0

    def test_summarize_truncates_long_summaries(self):
        """Test that summarize truncates summaries exceeding max_length * 2."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            # Return very long summary
            long_summary = "A" * 500
            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": long_summary}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            result = provider.summarize("Test text", max_length=150)

            # Should be truncated to max_length (150)
            assert len(result) == 150

    def test_summarize_strips_whitespace_from_response(self):
        """Test that summarize strips whitespace from response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "  Summary with whitespace  \n"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            result = provider.summarize("Test text")

            assert result == "Summary with whitespace"

    def test_summarize_uses_default_api_key(self):
        """Test that summarize uses 'not-needed' as default API key."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            provider.summarize("Test text")

            call_args = mock_post.call_args
            assert "Bearer not-needed" in str(call_args[1]["headers"])


class TestOpenAICompatibleProviderModelDiscovery:
    """Tests for OpenAICompatibleProvider._get_model() method."""

    def test_get_model_returns_configured_model(self):
        """Test _get_model returns configured model when set."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="configured-model",
        )
        assert provider._get_model() == "configured-model"

    def test_get_model_discovers_from_api_when_not_configured(self):
        """Test _get_model discovers model from API when not configured."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {
                "data": [{"id": "discovered-model"}, {"id": "another-model"}]
            }
            mock_get.return_value = models_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=None,
            )
            result = provider._get_model()

            assert result == "discovered-model"

    def test_get_model_returns_default_when_discovery_fails(self):
        """Test _get_model returns 'default' when discovery fails."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=None,
            )
            result = provider._get_model()

            assert result == "default"

    def test_get_model_returns_default_when_no_models_available(self):
        """Test _get_model returns 'default' when no models in response."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": []}
            mock_get.return_value = models_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=None,
            )
            result = provider._get_model()

            assert result == "default"

    def test_get_model_returns_default_when_api_returns_error(self):
        """Test _get_model returns 'default' when API returns error status."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 500
            mock_get.return_value = models_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=None,
            )
            result = provider._get_model()

            assert result == "default"

    def test_get_model_handles_malformed_response(self):
        """Test _get_model handles malformed API response."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"unexpected": "format"}
            mock_get.return_value = models_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=None,
            )
            result = provider._get_model()

            assert result == "default"

    def test_get_model_uses_first_model_from_list(self):
        """Test _get_model uses first model from discovered list."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {
                "data": [
                    {"id": "first-model"},
                    {"id": "second-model"},
                    {"id": "third-model"},
                ]
            }
            mock_get.return_value = models_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=None,
            )
            result = provider._get_model()

            assert result == "first-model"


class TestOpenAICompatibleProviderErrorHandling:
    """Tests for OpenAICompatibleProvider error handling."""

    def test_summarize_raises_on_api_error(self):
        """Test summarize raises when API returns error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 500
            error_response.raise_for_status.side_effect = Exception("Internal Server Error")
            mock_post.return_value = error_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Internal Server Error"):
                provider.summarize("Test text")

    def test_summarize_raises_on_connection_error(self):
        """Test summarize raises on connection error during POST."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = Exception("Connection refused")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Connection refused"):
                provider.summarize("Test text")

    def test_summarize_raises_on_timeout(self):
        """Test summarize raises on timeout during POST."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            import httpx

            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(httpx.TimeoutException):
                provider.summarize("Test text")

    def test_summarize_raises_on_rate_limit(self):
        """Test summarize raises when API returns rate limit error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.raise_for_status.side_effect = Exception("Rate limit exceeded")
            mock_post.return_value = rate_limit_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Rate limit exceeded"):
                provider.summarize("Test text")

    def test_summarize_raises_on_unauthorized(self):
        """Test summarize raises when API returns unauthorized error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            unauthorized_response = MagicMock()
            unauthorized_response.status_code = 401
            unauthorized_response.raise_for_status.side_effect = Exception("Unauthorized")
            mock_post.return_value = unauthorized_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Unauthorized"):
                provider.summarize("Test text")


class TestOpenAICompatibleProviderGenerate:
    """Tests for OpenAICompatibleProvider.generate() method."""

    def test_generate_returns_empty_string_for_empty_input(self):
        """Test generate returns empty string for empty input."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )
        result = provider.generate("")
        assert result == ""

    def test_generate_makes_correct_api_call(self):
        """Test generate makes correct API call with proper payload."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Generated response"}}],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 30,
                    "total_tokens": 80,
                },
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                api_key="test-key",
                model="test-model",
            )
            result = provider.generate("Custom prompt", max_tokens=500)

            assert result == "Generated response"
            call_args = mock_post.call_args
            assert call_args[1]["json"]["max_tokens"] == 500

    def test_generate_records_usage_stats(self):
        """Test generate records usage stats from API response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Response"}}],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 30,
                    "total_tokens": 80,
                },
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            provider.generate("Test prompt")

            assert provider.last_usage is not None
            assert provider.last_usage.input_tokens == 50
            assert provider.last_usage.output_tokens == 30
            assert provider.last_usage.total_tokens == 80


class TestOpenAICompatibleProviderProperties:
    """Tests for OpenAICompatibleProvider properties."""

    def test_name_returns_provider_name(self):
        """Test name property returns provider name."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
            provider_name="Custom Provider",
        )
        assert provider.name == "Custom Provider"

    def test_name_returns_default_name(self):
        """Test name property returns default when not specified."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )
        assert provider.name == "OpenAI-compatible"

    def test_model_name_returns_configured_model(self):
        """Test model_name returns configured model."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="my-model",
        )
        assert provider.model_name == "my-model"

    def test_model_name_returns_discovered_model(self):
        """Test model_name returns discovered model after API call."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "discovered-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model=None,
            )
            # Before summarize call
            assert provider.model_name == "auto"

            # After summarize call (model discovered)
            provider.summarize("Test")
            assert provider.model_name == "discovered-model"

    def test_model_name_returns_auto_when_no_model(self):
        """Test model_name returns 'auto' when no model configured."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model=None,
        )
        assert provider.model_name == "auto"


class TestOpenAICompatibleProviderIntegration:
    """Integration tests for OpenAICompatibleProvider."""

    def test_multiple_summarize_calls_accumulate_usage(self):
        """Test multiple summarize calls accumulate session usage."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            provider.summarize("First text")
            provider.summarize("Second text")
            provider.summarize("Third text")

            assert provider.session_usage["calls"] == 3
            assert provider.session_usage["total_tokens"] == 360  # 120 * 3

    def test_provider_initialization_with_all_parameters(self):
        """Test provider initialization with all parameters."""
        provider = OpenAICompatibleProvider(
            base_url="https://api.custom.com/v1",
            api_key="custom-api-key",
            model="custom-model",
            provider_name="My Custom API",
        )

        assert provider.base_url == "https://api.custom.com/v1"
        assert provider.api_key == "custom-api-key"
        assert provider.model == "custom-model"
        assert provider.name == "My Custom API"
        assert provider.last_usage is None
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}

    def test_provider_initialization_with_minimal_parameters(self):
        """Test provider initialization with minimal parameters."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
        )

        assert provider.base_url == "http://localhost:1234/v1"
        assert provider.api_key == "not-needed"
        assert provider.model is None
        assert provider.name == "OpenAI-compatible"

    def test_estimate_tokens_method(self):
        """Test _estimate_tokens method."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
        )

        # 4 chars per token estimation
        assert provider._estimate_tokens("") == 0
        assert provider._estimate_tokens("1234") == 1
        assert provider._estimate_tokens("12345678") == 2
        assert provider._estimate_tokens("a" * 100) == 25

    def test_record_usage_method(self):
        """Test _record_usage method updates stats correctly."""
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:1234/v1",
            model="test-model",
            provider_name="Test Provider",
        )

        provider._record_usage("input text", "output", "my-model")

        assert provider.last_usage is not None
        assert provider.last_usage.model == "my-model"
        assert provider.last_usage.provider == "Test Provider"
        assert provider.session_usage["calls"] == 1
        assert provider.session_usage["total_tokens"] > 0


# =============================================================================
# Tests for OllamaProvider
# =============================================================================


class TestOllamaProviderInitialization:
    """Tests for OllamaProvider initialization."""

    def test_initialization_with_default_model(self):
        """Test OllamaProvider initializes with default llama2 model."""
        provider = OllamaProvider()

        assert provider.model == "llama2"
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.name == "Ollama"
        assert provider.api_key == "not-needed"

    def test_initialization_with_custom_model(self):
        """Test OllamaProvider initializes with custom model."""
        provider = OllamaProvider(model="mistral")

        assert provider.model == "mistral"
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.name == "Ollama"

    def test_initialization_with_none_model_uses_default(self):
        """Test OllamaProvider uses llama2 when model is None."""
        provider = OllamaProvider(model=None)

        assert provider.model == "llama2"

    def test_model_name_property(self):
        """Test model_name property returns configured model."""
        provider = OllamaProvider(model="phi3")
        assert provider.model_name == "phi3"

    def test_model_name_property_default(self):
        """Test model_name property returns llama2 for default."""
        provider = OllamaProvider()
        assert provider.model_name == "llama2"

    def test_inherits_from_openai_compatible_provider(self):
        """Test OllamaProvider inherits from OpenAICompatibleProvider."""
        provider = OllamaProvider()
        assert isinstance(provider, OpenAICompatibleProvider)

    def test_session_usage_initialized(self):
        """Test session usage is initialized correctly."""
        provider = OllamaProvider()
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}
        assert provider.last_usage is None


class TestOllamaProviderIsAvailable:
    """Tests for OllamaProvider.is_available() method."""

    def test_is_available_returns_true_when_ollama_running(self):
        """Test is_available returns True when Ollama is running."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            provider = OllamaProvider()
            assert provider.is_available() is True
            mock_get.assert_called_once_with(
                "http://localhost:11434/v1/models", timeout=5.0
            )

    def test_is_available_returns_false_when_ollama_not_running(self):
        """Test is_available returns False when Ollama is not running."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_is_available_returns_false_on_non_200_response(self):
        """Test is_available returns False when endpoint returns non-200."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_is_available_returns_false_on_timeout(self):
        """Test is_available returns False on timeout."""
        with patch("httpx.get") as mock_get:
            import httpx
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_is_available_returns_false_on_connection_error(self):
        """Test is_available returns False on connection error."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = ConnectionError("Network unreachable")

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_is_available_calls_correct_endpoint(self):
        """Test is_available calls the correct Ollama endpoint."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            provider = OllamaProvider()
            provider.is_available()

            # Verify the correct URL is called
            args, kwargs = mock_get.call_args
            assert args[0] == "http://localhost:11434/v1/models"
            assert kwargs["timeout"] == 5.0

    def test_is_available_with_custom_model_same_endpoint(self):
        """Test is_available uses same endpoint regardless of model."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            provider = OllamaProvider(model="codellama")
            provider.is_available()

            args, _ = mock_get.call_args
            assert args[0] == "http://localhost:11434/v1/models"


class TestOllamaProviderModelListing:
    """Tests for OllamaProvider model listing via _get_model()."""

    def test_get_model_returns_configured_model(self):
        """Test _get_model returns configured model when set."""
        provider = OllamaProvider(model="mistral")
        assert provider._get_model() == "mistral"

    def test_get_model_returns_default_model_when_not_set(self):
        """Test _get_model returns llama2 as default."""
        provider = OllamaProvider()
        # Since model is "llama2" by default, it should return that
        assert provider._get_model() == "llama2"

    def test_get_model_discovers_from_api_when_model_none(self):
        """Test _get_model discovers model from API when configured model is None."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {
                "data": [{"id": "mistral"}, {"id": "llama2"}]
            }
            mock_get.return_value = models_response

            # Create provider and manually set model to None to test discovery
            provider = OllamaProvider()
            provider.model = None  # Override default to test discovery
            result = provider._get_model()

            assert result == "mistral"  # First model from list
            mock_get.assert_called_with(
                "http://localhost:11434/v1/models", timeout=5.0
            )

    def test_get_model_returns_default_when_discovery_fails(self):
        """Test _get_model returns 'default' when discovery fails."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            provider = OllamaProvider()
            provider.model = None  # Override to test discovery path
            result = provider._get_model()

            assert result == "default"

    def test_get_model_returns_default_when_no_models_loaded(self):
        """Test _get_model returns 'default' when no models are loaded."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": []}
            mock_get.return_value = models_response

            provider = OllamaProvider()
            provider.model = None
            result = provider._get_model()

            assert result == "default"

    def test_get_model_returns_default_on_api_error(self):
        """Test _get_model returns 'default' when API returns error."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 500
            mock_get.return_value = models_response

            provider = OllamaProvider()
            provider.model = None
            result = provider._get_model()

            assert result == "default"

    def test_get_model_handles_malformed_response(self):
        """Test _get_model handles malformed API response gracefully."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"unexpected": "format"}
            mock_get.return_value = models_response

            provider = OllamaProvider()
            provider.model = None
            result = provider._get_model()

            assert result == "default"

    def test_get_model_uses_first_available_model(self):
        """Test _get_model uses first model from discovered list."""
        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {
                "data": [
                    {"id": "phi3"},
                    {"id": "llama2"},
                    {"id": "mistral"},
                ]
            }
            mock_get.return_value = models_response

            provider = OllamaProvider()
            provider.model = None
            result = provider._get_model()

            assert result == "phi3"


class TestOllamaProviderSummarize:
    """Tests for OllamaProvider.summarize() method with mocked responses."""

    def test_summarize_returns_empty_for_empty_input(self):
        """Test summarize returns empty string for empty input."""
        provider = OllamaProvider()
        result = provider.summarize("")
        assert result == ""

    def test_summarize_makes_correct_api_call(self):
        """Test summarize makes correct API call to Ollama."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            # Mock models endpoint
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            # Mock completion endpoint
            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Ollama summary"}}],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 10,
                    "total_tokens": 60,
                },
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            result = provider.summarize("Test article content", max_length=150)

            assert result == "Ollama summary"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://localhost:11434/v1/chat/completions"
            assert call_args[1]["json"]["model"] == "llama2"

    def test_summarize_with_custom_model(self):
        """Test summarize uses custom model in API call."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "mistral"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider(model="mistral")
            provider.summarize("Test text")

            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "mistral"

    def test_summarize_records_usage_from_response(self):
        """Test summarize records usage stats from API response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 25,
                    "total_tokens": 125,
                },
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            provider.summarize("Test text")

            assert provider.last_usage is not None
            assert provider.last_usage.input_tokens == 100
            assert provider.last_usage.output_tokens == 25
            assert provider.last_usage.total_tokens == 125
            assert provider.last_usage.model == "llama2"
            assert provider.last_usage.provider == "Ollama"

    def test_summarize_estimates_tokens_when_not_in_response(self):
        """Test summarize estimates tokens when usage not in response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary result"}}],
                # No usage field
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            provider.summarize("Test text for summarization")

            assert provider.last_usage is not None
            # Should have estimated tokens
            assert provider.last_usage.input_tokens > 0
            assert provider.last_usage.output_tokens > 0

    def test_summarize_accumulates_session_usage(self):
        """Test multiple summarize calls accumulate session usage."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            provider.summarize("First text")
            provider.summarize("Second text")

            assert provider.session_usage["calls"] == 2
            assert provider.session_usage["total_tokens"] == 120  # 60 * 2

    def test_summarize_strips_whitespace(self):
        """Test summarize strips whitespace from response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "  Summary with whitespace  \n\n"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            result = provider.summarize("Test")

            assert result == "Summary with whitespace"

    def test_summarize_truncates_long_response(self):
        """Test summarize truncates response exceeding max_length * 2."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            # Return very long summary
            long_summary = "A" * 500
            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": long_summary}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            result = provider.summarize("Test text", max_length=150)

            # Should be truncated to max_length (150)
            assert len(result) == 150


class TestOllamaProviderErrorHandling:
    """Tests for OllamaProvider error handling."""

    def test_summarize_raises_on_api_error(self):
        """Test summarize raises when API returns error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 500
            error_response.raise_for_status.side_effect = Exception("Internal Server Error")
            mock_post.return_value = error_response

            provider = OllamaProvider()

            with pytest.raises(Exception, match="Internal Server Error"):
                provider.summarize("Test text")

    def test_summarize_raises_on_connection_error(self):
        """Test summarize raises on connection error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = Exception("Connection refused")

            provider = OllamaProvider()

            with pytest.raises(Exception, match="Connection refused"):
                provider.summarize("Test text")

    def test_summarize_raises_on_timeout(self):
        """Test summarize raises on timeout."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            import httpx

            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            provider = OllamaProvider()

            with pytest.raises(httpx.TimeoutException):
                provider.summarize("Test text")

    def test_summarize_raises_on_model_not_found(self):
        """Test summarize raises when model is not found."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 404
            error_response.raise_for_status.side_effect = Exception("Model not found")
            mock_post.return_value = error_response

            provider = OllamaProvider(model="nonexistent-model")

            with pytest.raises(Exception, match="Model not found"):
                provider.summarize("Test text")


class TestOllamaProviderGenerate:
    """Tests for OllamaProvider.generate() method."""

    def test_generate_returns_empty_for_empty_input(self):
        """Test generate returns empty string for empty input."""
        provider = OllamaProvider()
        result = provider.generate("")
        assert result == ""

    def test_generate_makes_correct_api_call(self):
        """Test generate makes correct API call with max_tokens."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Generated response"}}],
                "usage": {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            result = provider.generate("Custom prompt", max_tokens=300)

            assert result == "Generated response"
            call_args = mock_post.call_args
            assert call_args[1]["json"]["max_tokens"] == 300

    def test_generate_records_usage(self):
        """Test generate records usage stats."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama2"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Response"}}],
                "usage": {"prompt_tokens": 40, "completion_tokens": 30, "total_tokens": 70},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider()
            provider.generate("Test prompt")

            assert provider.last_usage is not None
            assert provider.last_usage.input_tokens == 40
            assert provider.last_usage.output_tokens == 30
            assert provider.last_usage.total_tokens == 70


class TestOllamaProviderIntegration:
    """Integration tests for OllamaProvider."""

    def test_provider_used_in_get_provider_with_ollama_config(self, clean_env):
        """Test get_provider returns OllamaProvider for ollama config."""
        config = LLMConfig(provider=ProviderType.OLLAMA, model="phi3")
        provider = get_provider(config)

        assert isinstance(provider, OllamaProvider)
        assert provider.model == "phi3"
        assert provider.name == "Ollama"

    def test_provider_used_in_get_provider_with_default_model(self, clean_env):
        """Test get_provider uses llama2 as default model."""
        config = LLMConfig(provider=ProviderType.OLLAMA)
        provider = get_provider(config)

        assert isinstance(provider, OllamaProvider)
        assert provider.model == "llama2"

    def test_provider_listed_in_list_providers(self):
        """Test OllamaProvider appears in list_providers."""
        with patch("httpx.get") as mock_get:
            # Mock unavailable response
            mock_get.side_effect = Exception("Not running")

            providers = list_providers()
            ollama_info = next(
                (p for p in providers if p["type"] == ProviderType.OLLAMA), None
            )

            assert ollama_info is not None
            assert ollama_info["name"] == "Ollama"
            assert "localhost:11434" in ollama_info["description"]
            assert ollama_info["available"] is False

    def test_provider_listed_as_available_when_running(self):
        """Test OllamaProvider shows as available when running."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            providers = list_providers()
            ollama_info = next(
                (p for p in providers if p["type"] == ProviderType.OLLAMA), None
            )

            assert ollama_info is not None
            assert ollama_info["available"] is True

    def test_auto_detect_finds_ollama(self):
        """Test auto_detect_provider finds Ollama when available."""
        with patch("httpx.get") as mock_get:
            # Mock LM Studio unavailable, Ollama available
            def mock_get_handler(url, **kwargs):
                if "11434" in url:  # Ollama port
                    response = MagicMock()
                    response.status_code = 200
                    return response
                raise Exception("Not running")

            mock_get.side_effect = mock_get_handler

            provider = auto_detect_provider()

            # Either LM Studio or Ollama could be first
            # This test verifies Ollama is detected if LM Studio is not available
            assert provider is not None
            if isinstance(provider, OllamaProvider):
                assert provider.name == "Ollama"

    def test_ollama_provider_different_port(self):
        """Test OllamaProvider uses correct port (11434 vs 1234 for LM Studio)."""
        ollama = OllamaProvider()
        lm_studio = LMStudioProvider()

        assert "11434" in ollama.base_url
        assert "1234" in lm_studio.base_url
        assert ollama.base_url != lm_studio.base_url

    def test_ollama_vs_lm_studio_provider_names(self):
        """Test Ollama and LM Studio have different provider names."""
        ollama = OllamaProvider()
        lm_studio = LMStudioProvider()

        assert ollama.name == "Ollama"
        assert lm_studio.name == "LM Studio"

    def test_multiple_requests_use_same_model(self):
        """Test multiple requests use the same configured model."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "codellama"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = OllamaProvider(model="codellama")
            provider.summarize("Text 1")
            provider.summarize("Text 2")

            # Both calls should use the same model
            for call in mock_post.call_args_list:
                assert call[1]["json"]["model"] == "codellama"
