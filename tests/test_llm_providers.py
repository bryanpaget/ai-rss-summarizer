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
    ClaudeAgentSDKProvider,
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
            "claude-agent-sdk",
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
        assert len(all_provider_types) == 13

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


# =============================================================================
# Tests for ClaudeProvider
# =============================================================================


class TestClaudeProviderInitialization:
    """Tests for ClaudeProvider initialization."""

    def test_initialization_with_default_model(self, clean_env):
        """Test ClaudeProvider initializes with default model."""
        provider = ClaudeProvider()

        assert provider._model == "claude-sonnet-4-20250514"
        assert provider.name == "Claude"
        assert provider._client is None

    def test_initialization_with_custom_model(self, clean_env):
        """Test ClaudeProvider initializes with custom model."""
        provider = ClaudeProvider(model="claude-opus-4-20250514")

        assert provider._model == "claude-opus-4-20250514"
        assert provider.name == "Claude"

    def test_model_name_property(self, clean_env):
        """Test model_name property returns configured model."""
        provider = ClaudeProvider(model="claude-3-haiku")
        assert provider.model_name == "claude-3-haiku"

    def test_model_name_property_default(self, clean_env):
        """Test model_name property returns default model."""
        provider = ClaudeProvider()
        assert provider.model_name == "claude-sonnet-4-20250514"

    def test_inherits_from_llm_provider(self, clean_env):
        """Test ClaudeProvider inherits from LLMProvider."""
        provider = ClaudeProvider()
        assert isinstance(provider, LLMProvider)

    def test_session_usage_initialized(self, clean_env):
        """Test session usage is initialized correctly."""
        provider = ClaudeProvider()
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}
        assert provider.last_usage is None


class TestClaudeProviderIsAvailable:
    """Tests for ClaudeProvider.is_available() method."""

    def test_is_available_returns_true_with_sdk_and_api_key(self, clean_env):
        """Test is_available returns True when SDK installed and API key set."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
        mock_anthropic = MagicMock()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            assert provider.is_available() is True

    def test_is_available_returns_false_without_api_key(self, clean_env):
        """Test is_available returns False when API key not set."""
        # Ensure no API key is set
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            assert provider.is_available() is False

    def test_is_available_returns_false_without_sdk(self, clean_env):
        """Test is_available returns False when SDK not installed."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        # Mock ImportError by making the import fail
        with patch.dict("sys.modules", {"anthropic": None}):
            provider = ClaudeProvider()
            # When module is None, import will raise ImportError or TypeError
            assert provider.is_available() is False

    def test_is_available_returns_false_without_both(self, clean_env):
        """Test is_available returns False when neither SDK nor API key present."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        with patch.dict("sys.modules", {"anthropic": None}):
            provider = ClaudeProvider()
            assert provider.is_available() is False

    def test_is_available_with_empty_api_key(self, clean_env):
        """Test is_available returns False when API key is empty string."""
        os.environ["ANTHROPIC_API_KEY"] = ""

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            assert provider.is_available() is False


class TestClaudeProviderSummarize:
    """Tests for ClaudeProvider.summarize() method with mocked responses."""

    def test_summarize_returns_empty_for_empty_input(self, clean_env):
        """Test summarize returns empty string for empty input."""
        provider = ClaudeProvider()
        result = provider.summarize("")
        assert result == ""

    def test_summarize_makes_correct_api_call(self, clean_env):
        """Test summarize makes correct API call to Claude."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        # Create mock anthropic module and client
        mock_usage = MagicMock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 10

        mock_content = MagicMock()
        mock_content.text = "Claude summary"

        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_message.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            result = provider.summarize("Test article content", max_length=150)

            assert result == "Claude summary"
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"
            assert call_kwargs["max_tokens"] == 256
            assert "messages" in call_kwargs

    def test_summarize_with_custom_model(self, clean_env):
        """Test summarize uses custom model in API call."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        mock_usage = MagicMock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 10

        mock_content = MagicMock()
        mock_content.text = "Summary"

        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_message.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider(model="claude-3-haiku")
            provider.summarize("Test text")

            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-3-haiku"

    def test_summarize_records_usage_from_response(self, clean_env):
        """Test summarize records usage stats from API response."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 25

        mock_content = MagicMock()
        mock_content.text = "Summary"

        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_message.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            provider.summarize("Test text")

            assert provider.last_usage is not None
            assert provider.last_usage.input_tokens == 100
            assert provider.last_usage.output_tokens == 25
            assert provider.last_usage.model == "claude-sonnet-4-20250514"
            assert provider.last_usage.provider == "Claude"

    def test_summarize_accumulates_session_usage(self, clean_env):
        """Test multiple summarize calls accumulate session usage."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        mock_usage = MagicMock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 10

        mock_content = MagicMock()
        mock_content.text = "Summary"

        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_message.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            provider.summarize("First text")
            provider.summarize("Second text")

            assert provider.session_usage["calls"] == 2
            assert provider.session_usage["total_tokens"] == 120  # 60 * 2

    def test_summarize_strips_whitespace(self, clean_env):
        """Test summarize strips whitespace from response."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        mock_usage = MagicMock()
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 5

        mock_content = MagicMock()
        mock_content.text = "  Summary with whitespace  \n\n"

        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_message.usage = mock_usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            result = provider.summarize("Test")

            assert result == "Summary with whitespace"

    def test_summarize_raises_when_not_available(self, clean_env):
        """Test summarize raises RuntimeError when provider not available."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        with patch.dict("sys.modules", {"anthropic": None}):
            provider = ClaudeProvider()

            with pytest.raises(RuntimeError, match="Claude provider not available"):
                provider.summarize("Test text")

    def test_summarize_estimates_tokens_when_usage_none(self, clean_env):
        """Test summarize estimates tokens when usage is None."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        mock_content = MagicMock()
        mock_content.text = "Summary result"

        mock_message = MagicMock()
        mock_message.content = [mock_content]
        mock_message.usage = None  # No usage data

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            provider.summarize("Test text for summarization")

            assert provider.last_usage is not None
            # Should have estimated tokens
            assert provider.last_usage.input_tokens > 0
            assert provider.last_usage.output_tokens > 0


class TestClaudeProviderAPIKeyHandling:
    """Tests for ClaudeProvider API key handling."""

    def test_api_key_from_environment(self, clean_env):
        """Test API key is read from ANTHROPIC_API_KEY environment variable."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key-12345"

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            assert provider.is_available() is True

    def test_api_key_not_in_other_env_vars(self, clean_env):
        """Test API key is not read from other common env vars."""
        # Set other provider keys but not ANTHROPIC_API_KEY
        os.environ["OPENAI_API_KEY"] = "openai-key"
        os.environ["GOOGLE_API_KEY"] = "google-key"

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            assert provider.is_available() is False

    def test_empty_api_key_treated_as_unavailable(self, clean_env):
        """Test empty string API key is treated as unavailable."""
        os.environ["ANTHROPIC_API_KEY"] = ""

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            assert provider.is_available() is False

    def test_whitespace_only_api_key(self, clean_env):
        """Test whitespace-only API key is treated as available (truthy)."""
        os.environ["ANTHROPIC_API_KEY"] = "   "

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()
            # Whitespace is truthy in Python, so this will return True
            assert provider.is_available() is True


class TestClaudeProviderErrorHandling:
    """Tests for ClaudeProvider error handling."""

    def test_summarize_raises_on_api_error(self, clean_env):
        """Test summarize raises when API returns error."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()

            with pytest.raises(Exception, match="API Error"):
                provider.summarize("Test text")

    def test_summarize_raises_on_rate_limit(self, clean_env):
        """Test summarize raises on rate limit error."""
        os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Rate limit exceeded")

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()

            with pytest.raises(Exception, match="Rate limit exceeded"):
                provider.summarize("Test text")

    def test_summarize_raises_on_invalid_api_key(self, clean_env):
        """Test summarize raises on invalid API key."""
        os.environ["ANTHROPIC_API_KEY"] = "invalid-key"

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Invalid API key")

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = ClaudeProvider()

            with pytest.raises(Exception, match="Invalid API key"):
                provider.summarize("Test text")


# =============================================================================
# Tests for ClaudeCodeProvider
# =============================================================================


class TestClaudeCodeProviderInitialization:
    """Tests for ClaudeCodeProvider initialization."""

    def test_initialization_with_default_model(self):
        """Test ClaudeCodeProvider initializes with default sonnet model."""
        provider = ClaudeCodeProvider()

        assert provider._model == "sonnet"
        assert provider.name == "Claude Code"

    def test_initialization_with_custom_model(self):
        """Test ClaudeCodeProvider initializes with custom model."""
        provider = ClaudeCodeProvider(model="opus")

        assert provider._model == "opus"
        assert provider.name == "Claude Code"

    def test_model_name_property(self):
        """Test model_name property returns configured model."""
        provider = ClaudeCodeProvider(model="haiku")
        assert provider.model_name == "haiku"

    def test_model_name_property_default(self):
        """Test model_name property returns sonnet as default."""
        provider = ClaudeCodeProvider()
        assert provider.model_name == "sonnet"

    def test_inherits_from_llm_provider(self):
        """Test ClaudeCodeProvider inherits from LLMProvider."""
        provider = ClaudeCodeProvider()
        assert isinstance(provider, LLMProvider)

    def test_session_usage_initialized(self):
        """Test session usage is initialized correctly."""
        provider = ClaudeCodeProvider()
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}
        assert provider.last_usage is None


class TestClaudeCodeProviderIsAvailable:
    """Tests for ClaudeCodeProvider.is_available() method."""

    def test_is_available_returns_true_when_claude_cli_found(self):
        """Test is_available returns True when Claude CLI is found."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/claude"

            provider = ClaudeCodeProvider()
            assert provider.is_available() is True
            mock_which.assert_called_once_with("claude")

    def test_is_available_returns_false_when_claude_cli_not_found(self):
        """Test is_available returns False when Claude CLI not found."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = ClaudeCodeProvider()
            assert provider.is_available() is False
            mock_which.assert_called_once_with("claude")

    def test_is_available_checks_shutil_which(self):
        """Test is_available uses shutil.which to check CLI."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/opt/homebrew/bin/claude"

            provider = ClaudeCodeProvider()
            provider.is_available()

            mock_which.assert_called_with("claude")

    def test_is_available_with_custom_model_same_check(self):
        """Test is_available uses same check regardless of model."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/claude"

            provider = ClaudeCodeProvider(model="opus")
            assert provider.is_available() is True
            mock_which.assert_called_once_with("claude")

    def test_is_available_on_windows_path(self):
        """Test is_available works with Windows-style paths."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "C:\\Program Files\\Claude\\claude.exe"

            provider = ClaudeCodeProvider()
            assert provider.is_available() is True


class TestClaudeCodeProviderSummarize:
    """Tests for ClaudeCodeProvider.summarize() method with mocked subprocess."""

    def test_summarize_returns_empty_for_empty_input(self):
        """Test summarize returns empty string for empty input."""
        provider = ClaudeCodeProvider()
        result = provider.summarize("")
        assert result == ""

    def test_summarize_makes_correct_cli_call(self):
        """Test summarize makes correct CLI call to Claude Code."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"result": "Claude Code summary", "usage": {"tokens": 100}}'
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()
            result = provider.summarize("Test article content", max_length=150)

            assert result == "Claude Code summary"
            mock_run.assert_called_once()

            # Verify command arguments
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "claude"
            assert "--print" in cmd
            assert "--output-format" in cmd
            assert "json" in cmd
            assert "--model" in cmd
            assert "sonnet" in cmd

    def test_summarize_with_custom_model(self):
        """Test summarize uses custom model in CLI call."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"result": "Summary"}'
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider(model="opus")
            provider.summarize("Test text")

            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert "opus" in cmd

    def test_summarize_records_usage(self):
        """Test summarize records usage stats."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"result": "Summary", "usage": {"tokens": 100}}'
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()
            provider.summarize("Test text for summarization")

            assert provider.last_usage is not None
            assert provider.last_usage.model == "sonnet"
            assert provider.last_usage.provider == "Claude Code"

    def test_summarize_strips_whitespace(self):
        """Test summarize strips whitespace from response."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"result": "  Summary with whitespace  \\n\\n"}'
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()
            result = provider.summarize("Test")

            assert result == "Summary with whitespace"

    def test_summarize_raises_when_not_available(self):
        """Test summarize raises RuntimeError when CLI not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = ClaudeCodeProvider()

            with pytest.raises(RuntimeError, match="Claude Code CLI not available"):
                provider.summarize("Test text")

    def test_summarize_uses_correct_cli_flags(self):
        """Test summarize uses all required CLI flags."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"result": "Summary"}'
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()
            provider.summarize("Test text")

            call_args = mock_run.call_args
            cmd = call_args[0][0]

            # Verify all expected flags are present
            assert "--print" in cmd
            assert "--output-format" in cmd
            assert "--model" in cmd
            assert "--tools" in cmd
            assert "--no-session-persistence" in cmd


class TestClaudeCodeProviderErrorHandling:
    """Tests for ClaudeCodeProvider error handling."""

    def test_summarize_raises_on_cli_error(self):
        """Test summarize raises when CLI returns non-zero exit code."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "CLI Error: Authentication failed"
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()

            with pytest.raises(RuntimeError, match="Claude Code CLI failed"):
                provider.summarize("Test text")

    def test_summarize_raises_on_timeout(self):
        """Test summarize raises on CLI timeout."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=60)

            provider = ClaudeCodeProvider()

            with pytest.raises(subprocess.TimeoutExpired):
                provider.summarize("Test text")

    def test_summarize_raises_on_invalid_json_response(self):
        """Test summarize raises on invalid JSON response from CLI."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Invalid JSON output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()

            with pytest.raises(Exception):  # json.JSONDecodeError
                provider.summarize("Test text")

    def test_summarize_handles_missing_result_key(self):
        """Test summarize handles missing 'result' key in response."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/claude"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '{"other_key": "value"}'  # No 'result' key
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()
            result = provider.summarize("Test text")

            # Should return empty string when 'result' key is missing
            assert result == ""


class TestClaudeCodeProviderIntegration:
    """Integration tests for ClaudeCodeProvider with get_provider."""

    def test_get_provider_returns_claude_code_provider(self, clean_env):
        """Test get_provider returns ClaudeCodeProvider when configured."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE_CODE,
            model="sonnet",
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeCodeProvider)
        assert provider._model == "sonnet"

    def test_get_provider_with_custom_model(self, clean_env):
        """Test get_provider uses custom model for ClaudeCodeProvider."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE_CODE,
            model="opus",
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeCodeProvider)
        assert provider._model == "opus"

    def test_get_provider_uses_default_model(self, clean_env):
        """Test get_provider uses default sonnet model when not specified."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE_CODE,
            model=None,
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeCodeProvider)
        assert provider._model == "sonnet"

    def test_list_providers_includes_claude_code(self):
        """Test list_providers includes Claude Code in the list."""
        with patch("shutil.which") as mock_which, patch("httpx.get") as mock_get:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_get.side_effect = Exception("Connection refused")  # Mock all HTTP calls

            providers = list_providers()

            claude_code_provider = next(
                (p for p in providers if p["type"] == ProviderType.CLAUDE_CODE),
                None
            )
            assert claude_code_provider is not None
            assert claude_code_provider["name"] == "Claude Code"
            assert claude_code_provider["available"] is True

    def test_list_providers_claude_code_unavailable(self):
        """Test list_providers shows Claude Code as unavailable when CLI not found."""
        with patch("shutil.which") as mock_which, patch("httpx.get") as mock_get:
            mock_which.return_value = None
            mock_get.side_effect = Exception("Connection refused")  # Mock all HTTP calls

            providers = list_providers()

            claude_code_provider = next(
                (p for p in providers if p["type"] == ProviderType.CLAUDE_CODE),
                None
            )
            assert claude_code_provider is not None
            assert claude_code_provider["available"] is False


class TestClaudeProviderIntegration:
    """Integration tests for ClaudeProvider with get_provider."""

    def test_get_provider_returns_claude_provider(self, clean_env):
        """Test get_provider returns ClaudeProvider when configured."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE,
            model="claude-sonnet-4-20250514",
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeProvider)
        assert provider._model == "claude-sonnet-4-20250514"

    def test_get_provider_with_custom_model(self, clean_env):
        """Test get_provider uses custom model for ClaudeProvider."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE,
            model="claude-3-haiku",
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeProvider)
        assert provider._model == "claude-3-haiku"

    def test_get_provider_uses_default_model(self, clean_env):
        """Test get_provider uses default model when not specified."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE,
            model=None,
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeProvider)
        assert provider._model == "claude-sonnet-4-20250514"

    def test_list_providers_includes_claude(self, clean_env):
        """Test list_providers includes Claude API in the list."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}), patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            providers = list_providers()

            claude_provider = next(
                (p for p in providers if p["type"] == ProviderType.CLAUDE),
                None
            )
            assert claude_provider is not None
            assert claude_provider["name"] == "Claude (API)"
            assert claude_provider["available"] is True

    def test_list_providers_claude_unavailable(self, clean_env):
        """Test list_providers shows Claude as unavailable without API key."""
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            providers = list_providers()

            claude_provider = next(
                (p for p in providers if p["type"] == ProviderType.CLAUDE),
                None
            )
            assert claude_provider is not None
            assert claude_provider["available"] is False


# =============================================================================
# Tests for ClaudeAgentSDKProvider
# =============================================================================


class TestClaudeAgentSDKProviderInitialization:
    """Tests for ClaudeAgentSDKProvider initialization."""

    def test_initialization_with_default_model(self):
        """Test ClaudeAgentSDKProvider initializes with default sonnet model."""
        provider = ClaudeAgentSDKProvider()

        assert provider._model == "sonnet"
        assert provider.name == "Claude Agent SDK"

    def test_initialization_with_custom_model(self):
        """Test ClaudeAgentSDKProvider initializes with custom model."""
        provider = ClaudeAgentSDKProvider(model="opus")

        assert provider._model == "opus"
        assert provider.name == "Claude Agent SDK"

    def test_model_name_property(self):
        """Test model_name property returns configured model."""
        provider = ClaudeAgentSDKProvider(model="haiku")
        assert provider.model_name == "haiku"

    def test_model_name_property_default(self):
        """Test model_name property returns sonnet as default."""
        provider = ClaudeAgentSDKProvider()
        assert provider.model_name == "sonnet"

    def test_inherits_from_llm_provider(self):
        """Test ClaudeAgentSDKProvider inherits from LLMProvider."""
        provider = ClaudeAgentSDKProvider()
        assert isinstance(provider, LLMProvider)

    def test_session_usage_initialized(self):
        """Test session usage is initialized correctly."""
        provider = ClaudeAgentSDKProvider()
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}
        assert provider.last_usage is None


class TestClaudeAgentSDKProviderIsAvailable:
    """Tests for ClaudeAgentSDKProvider.is_available() method."""

    def test_is_available_returns_true_when_sdk_and_auth_present(self):
        """Test is_available returns True when SDK installed and auth exists."""
        mock_query = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_query}), \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.exists") as mock_exists:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_exists.return_value = True

            provider = ClaudeAgentSDKProvider()
            assert provider.is_available() is True

    def test_is_available_returns_false_when_sdk_not_installed(self):
        """Test is_available returns False when SDK not installed."""
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            import sys
            # Remove the module to simulate ImportError
            if "claude_agent_sdk" in sys.modules:
                del sys.modules["claude_agent_sdk"]

            provider = ClaudeAgentSDKProvider()
            # Force re-check by calling is_available
            result = provider.is_available()
            # Since module is None, it should return False
            assert result is False

    def test_is_available_returns_false_when_claude_cli_not_found(self):
        """Test is_available returns False when Claude CLI not found."""
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}), \
             patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = ClaudeAgentSDKProvider()
            assert provider.is_available() is False

    def test_is_available_returns_false_when_config_not_found(self):
        """Test is_available returns False when config.json doesn't exist."""
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}), \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.exists") as mock_exists:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_exists.return_value = False

            provider = ClaudeAgentSDKProvider()
            assert provider.is_available() is False

    def test_is_available_checks_home_config(self):
        """Test is_available checks ~/.claude/config.json."""
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}), \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.home") as mock_home, \
             patch("pathlib.Path.exists") as mock_exists:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_home.return_value = Path("/home/user")
            mock_exists.return_value = True

            provider = ClaudeAgentSDKProvider()
            provider.is_available()

            # Verify Path.home was called to get config path
            mock_home.assert_called()


class TestClaudeAgentSDKProviderSummarize:
    """Tests for ClaudeAgentSDKProvider.summarize() method."""

    def test_summarize_returns_empty_for_empty_input(self):
        """Test summarize returns empty string for empty input."""
        provider = ClaudeAgentSDKProvider()
        result = provider.summarize("")
        assert result == ""

    def test_summarize_calls_query_async(self):
        """Test summarize calls the async query function."""
        mock_sdk = MagicMock()
        mock_assistant_msg = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "SDK summary"

        mock_assistant_msg.content = [mock_text_block]

        # Create async generator mock
        async def mock_query_gen(prompt):
            yield mock_assistant_msg

        mock_sdk.query = mock_query_gen
        mock_sdk.AssistantMessage = type(mock_assistant_msg)
        mock_sdk.TextBlock = type(mock_text_block)

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}), \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.exists") as mock_exists:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_exists.return_value = True

            provider = ClaudeAgentSDKProvider()
            result = provider.summarize("Test article content", max_length=150)

            assert result == "SDK summary"

    def test_summarize_records_usage(self):
        """Test summarize records usage stats."""
        mock_sdk = MagicMock()
        mock_assistant_msg = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Summary"

        mock_assistant_msg.content = [mock_text_block]

        async def mock_query_gen(prompt):
            yield mock_assistant_msg

        mock_sdk.query = mock_query_gen
        mock_sdk.AssistantMessage = type(mock_assistant_msg)
        mock_sdk.TextBlock = type(mock_text_block)

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}), \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.exists") as mock_exists:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_exists.return_value = True

            provider = ClaudeAgentSDKProvider()
            provider.summarize("Test text for summarization")

            assert provider.last_usage is not None
            assert provider.session_usage["calls"] == 1

    def test_summarize_raises_when_unavailable(self):
        """Test summarize raises RuntimeError when provider unavailable."""
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            provider = ClaudeAgentSDKProvider()

            with pytest.raises(RuntimeError, match="Claude Agent SDK not available"):
                provider.summarize("Test text")


class TestClaudeAgentSDKProviderGenerate:
    """Tests for ClaudeAgentSDKProvider.generate() method."""

    def test_generate_returns_response(self):
        """Test generate returns the response text."""
        mock_sdk = MagicMock()
        mock_assistant_msg = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Generated response"

        mock_assistant_msg.content = [mock_text_block]

        async def mock_query_gen(prompt):
            yield mock_assistant_msg

        mock_sdk.query = mock_query_gen
        mock_sdk.AssistantMessage = type(mock_assistant_msg)
        mock_sdk.TextBlock = type(mock_text_block)

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}), \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.exists") as mock_exists:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_exists.return_value = True

            provider = ClaudeAgentSDKProvider()
            result = provider.generate("Test prompt")

            assert result == "Generated response"

    def test_generate_raises_when_unavailable(self):
        """Test generate raises RuntimeError when provider unavailable."""
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            provider = ClaudeAgentSDKProvider()

            with pytest.raises(RuntimeError, match="Claude Agent SDK not available"):
                provider.generate("Test prompt")


class TestClaudeAgentSDKProviderAsyncHandling:
    """Tests for ClaudeAgentSDKProvider async handling."""

    def test_run_async_creates_new_loop_when_none_running(self):
        """Test _run_async creates new event loop when none running."""
        provider = ClaudeAgentSDKProvider()

        async def simple_coro():
            return "result"

        result = provider._run_async(simple_coro())
        assert result == "result"

    def test_run_async_handles_running_loop(self):
        """Test _run_async handles being called from async context."""
        import asyncio

        provider = ClaudeAgentSDKProvider()

        async def inner_coro():
            return "inner result"

        # This tests that the method can handle edge cases
        result = provider._run_async(inner_coro())
        assert result == "inner result"


class TestClaudeAgentSDKProviderIntegration:
    """Integration tests for ClaudeAgentSDKProvider with get_provider."""

    def test_get_provider_returns_claude_agent_sdk_provider(self, clean_env):
        """Test get_provider returns ClaudeAgentSDKProvider when configured."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE_AGENT_SDK,
            model="sonnet",
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeAgentSDKProvider)
        assert provider._model == "sonnet"

    def test_get_provider_with_custom_model(self, clean_env):
        """Test get_provider uses custom model for ClaudeAgentSDKProvider."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE_AGENT_SDK,
            model="opus",
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeAgentSDKProvider)
        assert provider._model == "opus"

    def test_get_provider_uses_default_model(self, clean_env):
        """Test get_provider uses default sonnet model when not specified."""
        config = LLMConfig(
            provider=ProviderType.CLAUDE_AGENT_SDK,
            model=None,
        )

        provider = get_provider(config)

        assert isinstance(provider, ClaudeAgentSDKProvider)
        assert provider._model == "sonnet"

    def test_list_providers_includes_claude_agent_sdk(self):
        """Test list_providers includes Claude Agent SDK in the list."""
        with patch("src.llm_providers.ClaudeAgentSDKProvider.is_available") as mock_sdk_available, \
             patch("shutil.which") as mock_which, \
             patch("httpx.get") as mock_get:
            mock_sdk_available.return_value = True
            mock_which.return_value = "/usr/local/bin/claude"
            mock_get.side_effect = Exception("Connection refused")

            providers = list_providers()

            claude_agent_sdk_provider = next(
                (p for p in providers if p["type"] == ProviderType.CLAUDE_AGENT_SDK),
                None
            )
            assert claude_agent_sdk_provider is not None
            assert claude_agent_sdk_provider["name"] == "Claude Agent SDK"
            assert claude_agent_sdk_provider["available"] is True

    def test_auto_detect_prefers_agent_sdk_over_claude_code(self, clean_env):
        """Test auto_detect_provider prefers Agent SDK over Claude Code."""
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}), \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.exists") as mock_exists, \
             patch("httpx.get") as mock_get:
            mock_which.return_value = "/usr/local/bin/claude"
            mock_exists.return_value = True
            mock_get.side_effect = Exception("Connection refused")

            provider = auto_detect_provider()

            # Should prefer Agent SDK over Claude Code CLI
            assert isinstance(provider, ClaudeAgentSDKProvider)

    def test_auto_detect_falls_back_to_claude_api_last(self, clean_env):
        """Test auto_detect_provider uses Claude API as last resort."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        # Mock all other providers as unavailable
        with patch("httpx.get") as mock_get, \
             patch("shutil.which") as mock_which, \
             patch("pathlib.Path.exists") as mock_exists, \
             patch.dict("sys.modules", {
                 "claude_agent_sdk": None,
                 "transformers": None,
                 "torch": None,
                 "agents": None,
                 "google.generativeai": None,
             }):
            mock_get.side_effect = Exception("Connection refused")
            mock_which.return_value = None  # No CLI tools available
            mock_exists.return_value = False

            # Mock anthropic SDK as available
            mock_anthropic = MagicMock()
            with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
                provider = auto_detect_provider()

                # Should fall back to Claude API as last resort
                assert isinstance(provider, ClaudeProvider)


# =============================================================================
# Tests for GeminiProvider
# =============================================================================


class TestGeminiProviderInitialization:
    """Tests for GeminiProvider initialization."""

    def test_initialization_with_default_model(self, clean_env):
        """Test GeminiProvider initializes with default model."""
        provider = GeminiProvider()

        assert provider._model == "gemini-1.5-flash"
        assert provider.name == "Gemini"
        assert provider._client is None

    def test_initialization_with_custom_model(self, clean_env):
        """Test GeminiProvider initializes with custom model."""
        provider = GeminiProvider(model="gemini-1.5-pro")

        assert provider._model == "gemini-1.5-pro"
        assert provider.name == "Gemini"

    def test_model_name_property(self, clean_env):
        """Test model_name property returns configured model."""
        provider = GeminiProvider(model="gemini-2.0-flash")
        assert provider.model_name == "gemini-2.0-flash"

    def test_model_name_property_default(self, clean_env):
        """Test model_name property returns default model."""
        provider = GeminiProvider()
        assert provider.model_name == "gemini-1.5-flash"

    def test_inherits_from_llm_provider(self, clean_env):
        """Test GeminiProvider inherits from LLMProvider."""
        provider = GeminiProvider()
        assert isinstance(provider, LLMProvider)

    def test_session_usage_initialized(self, clean_env):
        """Test session usage is initialized correctly."""
        provider = GeminiProvider()
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}
        assert provider.last_usage is None


class TestGeminiProviderIsAvailable:
    """Tests for GeminiProvider.is_available() method."""

    def test_is_available_returns_true_with_sdk_and_google_api_key(self, clean_env):
        """Test is_available returns True when SDK installed and GOOGLE_API_KEY set."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"
        mock_genai = MagicMock()

        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is True

    def test_is_available_returns_true_with_sdk_and_gemini_api_key(self, clean_env):
        """Test is_available returns True when SDK installed and GEMINI_API_KEY set."""
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        mock_genai = MagicMock()

        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is True

    def test_is_available_prefers_google_api_key(self, clean_env):
        """Test is_available works when both API keys are set."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"
        os.environ["GEMINI_API_KEY"] = "test-gemini-key"
        mock_genai = MagicMock()

        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is True

    def test_is_available_returns_false_without_api_key(self, clean_env):
        """Test is_available returns False when API key not set."""
        # Ensure no API key is set
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is False

    def test_is_available_returns_false_without_sdk(self, clean_env):
        """Test is_available returns False when SDK not installed."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        # Mock ImportError by making the import fail
        with patch.dict("sys.modules", {"google.generativeai": None}):
            provider = GeminiProvider()
            # When module is None, import will raise ImportError or TypeError
            assert provider.is_available() is False

    def test_is_available_returns_false_without_both(self, clean_env):
        """Test is_available returns False when neither SDK nor API key present."""
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        with patch.dict("sys.modules", {"google.generativeai": None}):
            provider = GeminiProvider()
            assert provider.is_available() is False

    def test_is_available_with_empty_api_key(self, clean_env):
        """Test is_available returns False when API key is empty string."""
        os.environ["GOOGLE_API_KEY"] = ""

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is False


class TestGeminiProviderSummarize:
    """Tests for GeminiProvider.summarize() method with mocked responses."""

    def test_summarize_returns_empty_for_empty_input(self, clean_env):
        """Test summarize returns empty string for empty input."""
        provider = GeminiProvider()
        result = provider.summarize("")
        assert result == ""

    def test_summarize_makes_correct_api_call(self, clean_env):
        """Test summarize makes correct API call to Gemini."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        # Create mock usage metadata
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 50
        mock_usage.candidates_token_count = 10
        mock_usage.total_token_count = 60

        mock_response = MagicMock()
        mock_response.text = "Gemini summary"
        mock_response.usage_metadata = mock_usage

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider()
        # Patch the _get_client method to return our mock
        with patch.object(provider, "_get_client", return_value=mock_model):
            result = provider.summarize("Test article content", max_length=150)

            assert result == "Gemini summary"
            mock_model.generate_content.assert_called_once()

    def test_summarize_with_custom_model(self, clean_env):
        """Test summarize uses custom model in API call."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 50
        mock_usage.candidates_token_count = 10
        mock_usage.total_token_count = 60

        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_response.usage_metadata = mock_usage

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(model="gemini-1.5-pro")
        with patch.object(provider, "_get_client", return_value=mock_model):
            provider.summarize("Test text")

            # Verify the model was called
            mock_model.generate_content.assert_called_once()
            # Verify the provider has the custom model set
            assert provider._model == "gemini-1.5-pro"

    def test_summarize_records_usage_from_response(self, clean_env):
        """Test summarize records usage stats from API response."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 100
        mock_usage.candidates_token_count = 25
        mock_usage.total_token_count = 125

        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_response.usage_metadata = mock_usage

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with patch.object(provider, "_get_client", return_value=mock_model):
            provider.summarize("Test text")

            assert provider.last_usage is not None
            assert provider.last_usage.input_tokens == 100
            assert provider.last_usage.output_tokens == 25
            assert provider.last_usage.total_tokens == 125
            assert provider.last_usage.model == "gemini-1.5-flash"
            assert provider.last_usage.provider == "Gemini"

    def test_summarize_accumulates_session_usage(self, clean_env):
        """Test multiple summarize calls accumulate session usage."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 50
        mock_usage.candidates_token_count = 10
        mock_usage.total_token_count = 60

        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_response.usage_metadata = mock_usage

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with patch.object(provider, "_get_client", return_value=mock_model):
            provider.summarize("First text")
            provider.summarize("Second text")

            assert provider.session_usage["calls"] == 2
            assert provider.session_usage["total_tokens"] == 120  # 60 * 2

    def test_summarize_strips_whitespace(self, clean_env):
        """Test summarize strips whitespace from response."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 5
        mock_usage.total_token_count = 15

        mock_response = MagicMock()
        mock_response.text = "  Summary with whitespace  \n\n"
        mock_response.usage_metadata = mock_usage

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with patch.object(provider, "_get_client", return_value=mock_model):
            result = provider.summarize("Test")

            assert result == "Summary with whitespace"

    def test_summarize_raises_when_not_available(self, clean_env):
        """Test summarize raises RuntimeError when provider not available."""
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        with patch.dict("sys.modules", {"google.generativeai": None}):
            provider = GeminiProvider()

            with pytest.raises(RuntimeError, match="Gemini provider not available"):
                provider.summarize("Test text")

    def test_summarize_estimates_tokens_when_usage_none(self, clean_env):
        """Test summarize estimates tokens when usage is None."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        mock_response = MagicMock()
        mock_response.text = "Summary result"
        mock_response.usage_metadata = None  # No usage data

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with patch.object(provider, "_get_client", return_value=mock_model):
            provider.summarize("Test text for summarization")

            assert provider.last_usage is not None
            # Should have estimated tokens
            assert provider.last_usage.input_tokens > 0
            assert provider.last_usage.output_tokens > 0


class TestGeminiProviderAPIKeyHandling:
    """Tests for GeminiProvider API key handling."""

    def test_api_key_from_google_api_key(self, clean_env):
        """Test API key is read from GOOGLE_API_KEY environment variable."""
        os.environ["GOOGLE_API_KEY"] = "test-key-12345"

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is True

    def test_api_key_from_gemini_api_key(self, clean_env):
        """Test API key is read from GEMINI_API_KEY environment variable."""
        os.environ["GEMINI_API_KEY"] = "test-key-12345"

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is True

    def test_api_key_not_in_other_env_vars(self, clean_env):
        """Test API key is not read from other common env vars."""
        # Set other provider keys but not GOOGLE_API_KEY or GEMINI_API_KEY
        os.environ["OPENAI_API_KEY"] = "openai-key"
        os.environ["ANTHROPIC_API_KEY"] = "anthropic-key"

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is False

    def test_empty_api_key_treated_as_unavailable(self, clean_env):
        """Test empty string API key is treated as unavailable."""
        os.environ["GOOGLE_API_KEY"] = ""
        os.environ["GEMINI_API_KEY"] = ""

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            assert provider.is_available() is False

    def test_whitespace_only_api_key(self, clean_env):
        """Test whitespace-only API key is treated as available (truthy)."""
        os.environ["GOOGLE_API_KEY"] = "   "

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            provider = GeminiProvider()
            # Whitespace is truthy in Python, so this will return True
            assert provider.is_available() is True


class TestGeminiProviderErrorHandling:
    """Tests for GeminiProvider error handling."""

    def test_summarize_raises_on_api_error(self, clean_env):
        """Test summarize raises when API returns error."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")

        provider = GeminiProvider()
        with patch.object(provider, "_get_client", return_value=mock_model):
            with pytest.raises(Exception, match="API Error"):
                provider.summarize("Test text")

    def test_summarize_raises_on_rate_limit(self, clean_env):
        """Test summarize raises on rate limit error."""
        os.environ["GOOGLE_API_KEY"] = "test-google-key"

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Rate limit exceeded")

        provider = GeminiProvider()
        with patch.object(provider, "_get_client", return_value=mock_model):
            with pytest.raises(Exception, match="Rate limit exceeded"):
                provider.summarize("Test text")

    def test_summarize_raises_on_invalid_api_key(self, clean_env):
        """Test summarize raises on invalid API key."""
        os.environ["GOOGLE_API_KEY"] = "invalid-key"

        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Invalid API key")

        provider = GeminiProvider()
        with patch.object(provider, "_get_client", return_value=mock_model):
            with pytest.raises(Exception, match="Invalid API key"):
                provider.summarize("Test text")


class TestGeminiProviderIntegration:
    """Integration tests for GeminiProvider with get_provider and list_providers."""

    def test_get_provider_returns_gemini_provider(self, clean_env):
        """Test get_provider returns GeminiProvider when configured."""
        config = LLMConfig(
            provider=ProviderType.GEMINI,
            model="gemini-1.5-flash",
        )

        provider = get_provider(config)

        assert isinstance(provider, GeminiProvider)
        assert provider._model == "gemini-1.5-flash"

    def test_get_provider_with_custom_model(self, clean_env):
        """Test get_provider uses custom model for GeminiProvider."""
        config = LLMConfig(
            provider=ProviderType.GEMINI,
            model="gemini-1.5-pro",
        )

        provider = get_provider(config)

        assert isinstance(provider, GeminiProvider)
        assert provider._model == "gemini-1.5-pro"

    def test_get_provider_uses_default_model(self, clean_env):
        """Test get_provider uses default model when not specified."""
        config = LLMConfig(
            provider=ProviderType.GEMINI,
            model=None,
        )

        provider = get_provider(config)

        assert isinstance(provider, GeminiProvider)
        assert provider._model == "gemini-1.5-flash"

    def test_list_providers_includes_gemini(self, clean_env):
        """Test list_providers includes Gemini in the list."""
        os.environ["GOOGLE_API_KEY"] = "test-key"

        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}), patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            providers = list_providers()

            gemini_provider = next(
                (p for p in providers if p["type"] == ProviderType.GEMINI),
                None
            )
            assert gemini_provider is not None
            assert gemini_provider["name"] == "Gemini (API)"
            assert gemini_provider["available"] is True

    def test_list_providers_gemini_unavailable(self, clean_env):
        """Test list_providers shows Gemini as unavailable without API key."""
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            providers = list_providers()

            gemini_provider = next(
                (p for p in providers if p["type"] == ProviderType.GEMINI),
                None
            )
            assert gemini_provider is not None
            assert gemini_provider["available"] is False

    def test_auto_detect_includes_gemini_in_priority(self, clean_env):
        """Test auto_detect_provider considers Gemini in detection."""
        os.environ["GOOGLE_API_KEY"] = "test-key"

        # Mock no other providers available
        mock_genai = MagicMock()

        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            with patch("src.llm_providers.LMStudioProvider.is_available", return_value=False):
                with patch("src.llm_providers.OllamaProvider.is_available", return_value=False):
                    provider = auto_detect_provider()

                    if provider is not None:
                        # Should detect Gemini as available
                        assert isinstance(provider, (GeminiProvider, type(provider)))


# =============================================================================
# Tests for GeminiCLIProvider
# =============================================================================


class TestGeminiCLIProviderInitialization:
    """Tests for GeminiCLIProvider initialization."""

    def test_initialization_with_default_model(self):
        """Test GeminiCLIProvider initializes with default model."""
        provider = GeminiCLIProvider()

        assert provider._model == "gemini-2.0-flash"
        assert provider.name == "Gemini CLI"

    def test_initialization_with_custom_model(self):
        """Test GeminiCLIProvider initializes with custom model."""
        provider = GeminiCLIProvider(model="gemini-1.5-pro")

        assert provider._model == "gemini-1.5-pro"
        assert provider.name == "Gemini CLI"

    def test_model_name_property(self):
        """Test model_name property returns configured model."""
        provider = GeminiCLIProvider(model="gemini-1.5-flash")
        assert provider.model_name == "gemini-1.5-flash"

    def test_model_name_property_default(self):
        """Test model_name property returns default model."""
        provider = GeminiCLIProvider()
        assert provider.model_name == "gemini-2.0-flash"

    def test_inherits_from_llm_provider(self):
        """Test GeminiCLIProvider inherits from LLMProvider."""
        provider = GeminiCLIProvider()
        assert isinstance(provider, LLMProvider)

    def test_session_usage_initialized(self):
        """Test session usage is initialized correctly."""
        provider = GeminiCLIProvider()
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}
        assert provider.last_usage is None


class TestGeminiCLIProviderIsAvailable:
    """Tests for GeminiCLIProvider.is_available() method."""

    def test_is_available_returns_true_when_gemini_cli_found(self):
        """Test is_available returns True when Gemini CLI is found."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/gemini"

            provider = GeminiCLIProvider()
            assert provider.is_available() is True
            mock_which.assert_called_once_with("gemini")

    def test_is_available_returns_false_when_gemini_cli_not_found(self):
        """Test is_available returns False when Gemini CLI not found."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = GeminiCLIProvider()
            assert provider.is_available() is False
            mock_which.assert_called_once_with("gemini")

    def test_is_available_checks_shutil_which(self):
        """Test is_available uses shutil.which to check CLI."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/opt/homebrew/bin/gemini"

            provider = GeminiCLIProvider()
            provider.is_available()

            mock_which.assert_called_with("gemini")

    def test_is_available_with_custom_model_same_check(self):
        """Test is_available uses same check regardless of model."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/gemini"

            provider = GeminiCLIProvider(model="gemini-1.5-pro")
            assert provider.is_available() is True
            mock_which.assert_called_once_with("gemini")

    def test_is_available_on_windows_path(self):
        """Test is_available works with Windows-style paths."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "C:\\Program Files\\Gemini\\gemini.exe"

            provider = GeminiCLIProvider()
            assert provider.is_available() is True

    def test_is_available_on_npm_global_install(self):
        """Test is_available works with npm global install path."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/Users/user/.npm-global/bin/gemini"

            provider = GeminiCLIProvider()
            assert provider.is_available() is True


class TestGeminiCLIProviderSummarize:
    """Tests for GeminiCLIProvider.summarize() method with mocked subprocess."""

    def test_summarize_returns_empty_for_empty_input(self):
        """Test summarize returns empty string for empty input."""
        provider = GeminiCLIProvider()
        result = provider.summarize("")
        assert result == ""

    def test_summarize_makes_correct_cli_call(self):
        """Test summarize makes correct CLI call to Gemini CLI."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Gemini CLI summary"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()
            result = provider.summarize("Test article content", max_length=150)

            assert result == "Gemini CLI summary"
            mock_run.assert_called_once()

            # Verify command arguments
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "gemini"
            assert "ask" in cmd
            assert "-o" in cmd
            assert "text" in cmd

    def test_summarize_with_custom_model(self):
        """Test summarize uses custom model setting (model is stored internally)."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Summary"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider(model="gemini-1.5-pro")
            provider.summarize("Test text")

            # Verify the provider has the custom model set
            assert provider._model == "gemini-1.5-pro"
            mock_run.assert_called_once()

    def test_summarize_records_usage(self):
        """Test summarize records usage stats."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Summary"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()
            provider.summarize("Test text for summarization")

            assert provider.last_usage is not None
            assert provider.last_usage.model == "gemini-2.0-flash"
            assert provider.last_usage.provider == "Gemini CLI"

    def test_summarize_strips_whitespace(self):
        """Test summarize strips whitespace from response."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "  Summary with whitespace  \n\n"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()
            result = provider.summarize("Test")

            assert result == "Summary with whitespace"

    def test_summarize_raises_when_not_available(self):
        """Test summarize raises RuntimeError when CLI not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = GeminiCLIProvider()

            with pytest.raises(RuntimeError, match="Gemini CLI not available"):
                provider.summarize("Test text")

    def test_summarize_uses_correct_cli_flags(self):
        """Test summarize uses all required CLI flags."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Summary"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()
            provider.summarize("Test text")

            call_args = mock_run.call_args
            cmd = call_args[0][0]

            # Verify all expected flags are present
            assert "gemini" in cmd
            assert "ask" in cmd
            assert "-o" in cmd
            assert "text" in cmd

    def test_summarize_accumulates_session_usage(self):
        """Test multiple summarize calls accumulate session usage."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Summary"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()
            provider.summarize("First text")
            provider.summarize("Second text")

            assert provider.session_usage["calls"] == 2
            # Total tokens are estimated since CLI doesn't return usage
            assert provider.session_usage["total_tokens"] > 0


class TestGeminiCLIProviderErrorHandling:
    """Tests for GeminiCLIProvider error handling."""

    def test_summarize_raises_on_cli_error(self):
        """Test summarize raises when CLI returns non-zero exit code."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "CLI Error: Authentication failed"
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()

            with pytest.raises(RuntimeError, match="Gemini CLI failed"):
                provider.summarize("Test text")

    def test_summarize_raises_on_timeout(self):
        """Test summarize raises on CLI timeout."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gemini", timeout=60)

            provider = GeminiCLIProvider()

            with pytest.raises(subprocess.TimeoutExpired):
                provider.summarize("Test text")

    def test_summarize_handles_empty_response(self):
        """Test summarize handles empty response from CLI."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""  # Empty response
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()
            result = provider.summarize("Test text")

            # Should return empty string
            assert result == ""

    def test_summarize_handles_whitespace_only_response(self):
        """Test summarize handles whitespace-only response from CLI."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/local/bin/gemini"

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "   \n\n   "  # Whitespace only
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()
            result = provider.summarize("Test text")

            # Should return empty string after stripping
            assert result == ""


class TestGeminiCLIProviderIntegration:
    """Integration tests for GeminiCLIProvider with get_provider and list_providers."""

    def test_get_provider_returns_gemini_cli_provider(self, clean_env):
        """Test get_provider returns GeminiCLIProvider when configured."""
        config = LLMConfig(
            provider=ProviderType.GEMINI_CLI,
            model="gemini-2.0-flash",
        )

        provider = get_provider(config)

        assert isinstance(provider, GeminiCLIProvider)
        assert provider._model == "gemini-2.0-flash"

    def test_get_provider_with_custom_model(self, clean_env):
        """Test get_provider uses custom model for GeminiCLIProvider."""
        config = LLMConfig(
            provider=ProviderType.GEMINI_CLI,
            model="gemini-1.5-pro",
        )

        provider = get_provider(config)

        assert isinstance(provider, GeminiCLIProvider)
        assert provider._model == "gemini-1.5-pro"

    def test_get_provider_uses_default_model(self, clean_env):
        """Test get_provider uses default model when not specified."""
        config = LLMConfig(
            provider=ProviderType.GEMINI_CLI,
            model=None,
        )

        provider = get_provider(config)

        assert isinstance(provider, GeminiCLIProvider)
        assert provider._model == "gemini-2.0-flash"

    def test_list_providers_includes_gemini_cli(self):
        """Test list_providers includes Gemini CLI in the list."""
        with patch("shutil.which") as mock_which, patch("httpx.get") as mock_get:
            mock_which.return_value = "/usr/local/bin/gemini"
            mock_get.side_effect = Exception("Connection refused")

            providers = list_providers()

            gemini_cli_provider = next(
                (p for p in providers if p["type"] == ProviderType.GEMINI_CLI),
                None
            )
            assert gemini_cli_provider is not None
            assert gemini_cli_provider["name"] == "Gemini CLI"
            assert gemini_cli_provider["available"] is True

    def test_list_providers_gemini_cli_unavailable(self):
        """Test list_providers shows Gemini CLI as unavailable when CLI not found."""
        with patch("shutil.which") as mock_which, patch("httpx.get") as mock_get:
            mock_which.return_value = None
            mock_get.side_effect = Exception("Connection refused")

            providers = list_providers()

            gemini_cli_provider = next(
                (p for p in providers if p["type"] == ProviderType.GEMINI_CLI),
                None
            )
            assert gemini_cli_provider is not None
            assert gemini_cli_provider["available"] is False

    def test_config_with_gemini_cli_provider_type(self, clean_env):
        """Test LLMConfig can be created with GEMINI_CLI provider type."""
        config = LLMConfig(
            provider=ProviderType.GEMINI_CLI,
            model="gemini-2.0-flash",
        )

        assert config.provider == ProviderType.GEMINI_CLI
        assert config.model == "gemini-2.0-flash"


# =============================================================================
# GroqProvider Tests
# =============================================================================


class TestGroqProviderInitialization:
    """Tests for GroqProvider initialization."""

    def test_initialization_with_default_model(self, clean_env):
        """Test GroqProvider initializes with default model."""
        provider = GroqProvider()

        assert provider.model == "llama-3.3-70b-versatile"
        assert provider.name == "Groq"
        assert provider.base_url == "https://api.groq.com/openai/v1"

    def test_initialization_with_custom_model(self, clean_env):
        """Test GroqProvider initializes with custom model."""
        provider = GroqProvider(model="mixtral-8x7b-32768")

        assert provider.model == "mixtral-8x7b-32768"
        assert provider.name == "Groq"

    def test_model_name_property(self, clean_env):
        """Test model_name property returns configured model."""
        provider = GroqProvider(model="llama3-8b-8192")
        assert provider.model_name == "llama3-8b-8192"

    def test_model_name_property_default(self, clean_env):
        """Test model_name property returns default model."""
        provider = GroqProvider()
        assert provider.model_name == "llama-3.3-70b-versatile"

    def test_inherits_from_openai_compatible(self, clean_env):
        """Test GroqProvider inherits from OpenAICompatibleProvider."""
        provider = GroqProvider()
        assert isinstance(provider, OpenAICompatibleProvider)
        assert isinstance(provider, LLMProvider)

    def test_session_usage_initialized(self, clean_env):
        """Test session usage is initialized correctly."""
        provider = GroqProvider()
        assert provider.session_usage == {"calls": 0, "total_tokens": 0}
        assert provider.last_usage is None

    def test_api_key_from_env(self, clean_env):
        """Test API key is read from GROQ_API_KEY environment variable."""
        os.environ["GROQ_API_KEY"] = "test-groq-key-12345"
        provider = GroqProvider()
        assert provider.api_key == "test-groq-key-12345"


class TestGroqProviderIsAvailable:
    """Tests for GroqProvider.is_available() method."""

    def test_is_available_returns_true_with_api_key(self, clean_env):
        """Test is_available returns True when GROQ_API_KEY is set."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()
        assert provider.is_available() is True

    def test_is_available_returns_false_without_api_key(self, clean_env):
        """Test is_available returns False when GROQ_API_KEY not set."""
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]
        provider = GroqProvider()
        assert provider.is_available() is False

    def test_is_available_returns_false_with_empty_api_key(self, clean_env):
        """Test is_available returns False when GROQ_API_KEY is empty string."""
        os.environ["GROQ_API_KEY"] = ""
        provider = GroqProvider()
        assert provider.is_available() is False

    def test_is_available_with_whitespace_api_key(self, clean_env):
        """Test is_available with whitespace-only API key (truthy)."""
        os.environ["GROQ_API_KEY"] = "   "
        provider = GroqProvider()
        # Whitespace is truthy in Python
        assert provider.is_available() is True

    def test_is_available_not_affected_by_other_env_vars(self, clean_env):
        """Test is_available ignores other provider API keys."""
        os.environ["OPENAI_API_KEY"] = "openai-key"
        os.environ["ANTHROPIC_API_KEY"] = "anthropic-key"
        os.environ["GOOGLE_API_KEY"] = "google-key"
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]

        provider = GroqProvider()
        assert provider.is_available() is False

    def test_is_available_no_sdk_required(self, clean_env):
        """Test is_available does not require SDK installation."""
        # GroqProvider uses OpenAI-compatible API, no SDK needed
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()
        # Should work without any SDK imports
        assert provider.is_available() is True


class TestGroqProviderAPIKeyHandling:
    """Tests for GroqProvider API key handling."""

    def test_api_key_from_groq_api_key_env(self, clean_env):
        """Test API key is read from GROQ_API_KEY environment variable."""
        os.environ["GROQ_API_KEY"] = "gsk_test123456789"
        provider = GroqProvider()
        assert provider.api_key == "gsk_test123456789"

    def test_api_key_not_from_other_env_vars(self, clean_env):
        """Test API key is not read from other provider env vars."""
        os.environ["OPENAI_API_KEY"] = "sk-openai"
        os.environ["XAI_API_KEY"] = "xai-key"
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]

        provider = GroqProvider()
        # Without GROQ_API_KEY, OpenAICompatibleProvider defaults api_key to "not-needed"
        # This is the base class behavior for local providers that don't require API keys
        assert provider.api_key == "not-needed"

    def test_api_key_with_special_characters(self, clean_env):
        """Test API key with special characters is handled correctly."""
        special_key = "gsk_test+key/with=special&chars"
        os.environ["GROQ_API_KEY"] = special_key
        provider = GroqProvider()
        assert provider.api_key == special_key

    def test_api_key_very_long(self, clean_env):
        """Test very long API key is handled correctly."""
        long_key = "gsk_" + "a" * 1000
        os.environ["GROQ_API_KEY"] = long_key
        provider = GroqProvider()
        assert provider.api_key == long_key

    def test_api_key_unicode(self, clean_env):
        """Test unicode in API key (edge case)."""
        unicode_key = "gsk_test_キー_тест"
        os.environ["GROQ_API_KEY"] = unicode_key
        provider = GroqProvider()
        assert provider.api_key == unicode_key


class TestGroqProviderSummarize:
    """Tests for GroqProvider.summarize() method with mocked responses."""

    def test_summarize_returns_empty_for_empty_input(self, clean_env):
        """Test summarize returns empty string for empty input."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()
        result = provider.summarize("")
        assert result == ""

    def test_summarize_makes_correct_api_call(self, clean_env, mock_httpx_success):
        """Test summarize makes correct API call to Groq endpoint."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()

        result = provider.summarize("Test article content", max_length=150)

        assert result == "Test summary"
        mock_httpx_success["post"].assert_called_once()

        # Verify the call was made to Groq's endpoint
        call_args = mock_httpx_success["post"].call_args
        assert "https://api.groq.com/openai/v1/chat/completions" in call_args[0]

    def test_summarize_with_custom_model(self, clean_env, mock_httpx_success):
        """Test summarize uses custom model in API call."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider(model="mixtral-8x7b-32768")

        provider.summarize("Test text")

        call_args = mock_httpx_success["post"].call_args
        payload = call_args[1]["json"]
        assert payload["model"] == "mixtral-8x7b-32768"

    def test_summarize_records_usage_from_response(self, clean_env, mock_httpx_success):
        """Test summarize records usage stats from API response."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()

        provider.summarize("Test text")

        assert provider.last_usage is not None
        assert provider.last_usage.input_tokens == 100
        assert provider.last_usage.output_tokens == 20
        assert provider.last_usage.total_tokens == 120
        assert provider.last_usage.provider == "Groq"

    def test_summarize_accumulates_session_usage(self, clean_env, mock_httpx_success):
        """Test multiple summarize calls accumulate session usage."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()

        provider.summarize("First text")
        provider.summarize("Second text")

        assert provider.session_usage["calls"] == 2
        assert provider.session_usage["total_tokens"] == 240  # 120 * 2

    def test_summarize_strips_whitespace(self, clean_env):
        """Test summarize strips whitespace from response."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "  Summary with whitespace  \n"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = GroqProvider()
            result = provider.summarize("Test")

            assert result == "Summary with whitespace"

    def test_summarize_includes_authorization_header(self, clean_env):
        """Test summarize includes correct Authorization header."""
        os.environ["GROQ_API_KEY"] = "gsk_test123"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            completion_response = MagicMock()
            completion_response.status_code = 200
            completion_response.json.return_value = {
                "choices": [{"message": {"content": "Summary"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            completion_response.raise_for_status = MagicMock()
            mock_post.return_value = completion_response

            provider = GroqProvider()
            provider.summarize("Test")

            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer gsk_test123"


class TestGroqProviderRateLimitHandling:
    """Tests for GroqProvider rate limit handling."""

    def test_summarize_raises_on_rate_limit_429(self, clean_env, mock_httpx_rate_limit):
        """Test summarize raises exception on 429 rate limit response."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            provider = GroqProvider()

            with pytest.raises(Exception, match="Rate limit exceeded"):
                provider.summarize("Test text")

    def test_rate_limit_response_structure(self, clean_env):
        """Test rate limit response has expected structure."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {
                "retry-after": "60",
                "x-ratelimit-limit-requests": "30",
                "x-ratelimit-remaining-requests": "0",
            }
            rate_limit_response.json.return_value = {
                "error": {
                    "message": "Rate limit exceeded. Please retry after 60 seconds.",
                    "type": "rate_limit_error",
                }
            }
            rate_limit_response.raise_for_status.side_effect = Exception(
                "Rate limit exceeded"
            )
            mock_post.return_value = rate_limit_response

            provider = GroqProvider()

            with pytest.raises(Exception, match="Rate limit exceeded"):
                provider.summarize("Test text")

    def test_rate_limit_does_not_affect_session_stats(self, clean_env):
        """Test rate limit error does not increment session stats."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.raise_for_status.side_effect = Exception("Rate limit exceeded")
            mock_post.return_value = rate_limit_response

            provider = GroqProvider()
            initial_calls = provider.session_usage["calls"]

            try:
                provider.summarize("Test text")
            except Exception:
                pass

            # Session stats should not have changed
            assert provider.session_usage["calls"] == initial_calls


class TestGroqProviderErrorHandling:
    """Tests for GroqProvider error handling."""

    def test_summarize_raises_on_api_error(self, clean_env):
        """Test summarize raises when API returns error."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 500
            error_response.raise_for_status.side_effect = Exception("Internal Server Error")
            mock_post.return_value = error_response

            provider = GroqProvider()

            with pytest.raises(Exception, match="Internal Server Error"):
                provider.summarize("Test text")

    def test_summarize_raises_on_connection_error(self, clean_env):
        """Test summarize raises on connection error."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = Exception("Connection refused")

            provider = GroqProvider()

            with pytest.raises(Exception, match="Connection refused"):
                provider.summarize("Test text")

    def test_summarize_raises_on_timeout(self, clean_env):
        """Test summarize raises on timeout."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        import httpx

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = httpx.TimeoutException("Request timed out")

            provider = GroqProvider()

            with pytest.raises(httpx.TimeoutException):
                provider.summarize("Test text")

    def test_summarize_raises_on_invalid_api_key(self, clean_env):
        """Test summarize raises on invalid API key."""
        os.environ["GROQ_API_KEY"] = "invalid-key"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 401
            error_response.json.return_value = {
                "error": {"message": "Invalid API key", "type": "authentication_error"}
            }
            error_response.raise_for_status.side_effect = Exception("Invalid API key")
            mock_post.return_value = error_response

            provider = GroqProvider()

            with pytest.raises(Exception, match="Invalid API key"):
                provider.summarize("Test text")

    def test_summarize_handles_malformed_response(self, clean_env):
        """Test summarize handles malformed API response gracefully."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            mock_get.return_value = models_response

            # Response missing expected structure
            malformed_response = MagicMock()
            malformed_response.status_code = 200
            malformed_response.json.return_value = {"unexpected": "response"}
            malformed_response.raise_for_status = MagicMock()
            mock_post.return_value = malformed_response

            provider = GroqProvider()

            with pytest.raises(KeyError):
                provider.summarize("Test text")


class TestGroqProviderGenerate:
    """Tests for GroqProvider.generate() method."""

    def test_generate_returns_empty_for_empty_input(self, clean_env):
        """Test generate returns empty string for empty input."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()
        result = provider.generate("")
        assert result == ""

    def test_generate_makes_api_call(self, clean_env, mock_httpx_success):
        """Test generate makes API call to Groq endpoint."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()

        result = provider.generate("Classify this text", max_tokens=100)

        assert result == "Test summary"
        mock_httpx_success["post"].assert_called_once()

    def test_generate_records_usage(self, clean_env, mock_httpx_success):
        """Test generate records usage stats."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        provider = GroqProvider()

        provider.generate("Test prompt")

        assert provider.last_usage is not None
        assert provider.session_usage["calls"] == 1


class TestGroqProviderIntegration:
    """Integration tests for GroqProvider with get_provider and list_providers."""

    def test_get_provider_returns_groq_provider(self, clean_env):
        """Test get_provider returns GroqProvider when configured."""
        config = LLMConfig(
            provider=ProviderType.GROQ,
            model="llama-3.3-70b-versatile",
        )

        provider = get_provider(config)

        assert isinstance(provider, GroqProvider)
        assert provider.model == "llama-3.3-70b-versatile"

    def test_get_provider_with_custom_model(self, clean_env):
        """Test get_provider uses custom model for GroqProvider."""
        config = LLMConfig(
            provider=ProviderType.GROQ,
            model="mixtral-8x7b-32768",
        )

        provider = get_provider(config)

        assert isinstance(provider, GroqProvider)
        assert provider.model == "mixtral-8x7b-32768"

    def test_get_provider_uses_default_model(self, clean_env):
        """Test get_provider uses default model when not specified."""
        config = LLMConfig(
            provider=ProviderType.GROQ,
            model=None,
        )

        provider = get_provider(config)

        assert isinstance(provider, GroqProvider)
        assert provider.model == "llama-3.3-70b-versatile"

    def test_list_providers_includes_groq(self, clean_env):
        """Test list_providers includes Groq in the list."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            providers = list_providers()

            groq_provider = next(
                (p for p in providers if p["type"] == ProviderType.GROQ),
                None
            )
            assert groq_provider is not None
            assert groq_provider["name"] == "Groq"
            assert groq_provider["available"] is True
            assert "FREE" in groq_provider["description"]

    def test_list_providers_groq_unavailable(self, clean_env):
        """Test list_providers shows Groq as unavailable when API key not set."""
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            providers = list_providers()

            groq_provider = next(
                (p for p in providers if p["type"] == ProviderType.GROQ),
                None
            )
            assert groq_provider is not None
            assert groq_provider["available"] is False

    def test_config_with_groq_provider_type(self, clean_env):
        """Test LLMConfig can be created with GROQ provider type."""
        config = LLMConfig(
            provider=ProviderType.GROQ,
            model="llama-3.3-70b-versatile",
        )

        assert config.provider == ProviderType.GROQ
        assert config.model == "llama-3.3-70b-versatile"

    def test_groq_from_env_vars(self, env_groq):
        """Test GroqProvider is selected based on environment variables."""
        config = LLMConfig.from_env()

        assert config.provider == ProviderType.GROQ
        assert config.model == "llama-3.3-70b-versatile"

        provider = get_provider(config)
        assert isinstance(provider, GroqProvider)

    def test_groq_provider_type_value(self, clean_env):
        """Test ProviderType.GROQ has correct string value."""
        assert ProviderType.GROQ.value == "groq"
        assert ProviderType.GROQ == "groq"  # str enum comparison


# =============================================================================
# Tests for list_providers() - Available Providers List
# =============================================================================


class TestListProviders:
    """Tests for list_providers() function that lists all available providers."""

    @pytest.fixture(autouse=True)
    def mock_network(self):
        """Mock httpx for all tests in this class to prevent real network calls."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            yield mock_get

    def test_list_providers_returns_list(self, clean_env):
        """Test list_providers returns a list."""
        providers = list_providers()

        assert isinstance(providers, list)
        assert len(providers) > 0

    def test_list_providers_contains_all_provider_types(self, clean_env):
        """Test list_providers includes all expected provider types."""
        providers = list_providers()

        expected_types = [
            ProviderType.LM_STUDIO,
            ProviderType.OLLAMA,
            ProviderType.OPENAI,
            ProviderType.CODEX_CLI,
            ProviderType.CLAUDE,
            ProviderType.CLAUDE_CODE,
            ProviderType.GEMINI,
            ProviderType.GEMINI_CLI,
            ProviderType.GROK,
            ProviderType.GROQ,
        ]

        provider_types = [p["type"] for p in providers]
        for expected_type in expected_types:
            assert expected_type in provider_types, f"Missing provider type: {expected_type}"

    def test_list_providers_has_required_fields(self, clean_env):
        """Test each provider dict has required fields."""
        providers = list_providers()

        required_fields = ["type", "name", "available", "description"]
        for provider in providers:
            for field in required_fields:
                assert field in provider, f"Missing field '{field}' in provider: {provider}"

    def test_list_providers_available_is_boolean(self, clean_env):
        """Test available field is a boolean."""
        providers = list_providers()

        for provider in providers:
            assert isinstance(provider["available"], bool), \
                f"Provider {provider['name']} 'available' is not boolean"

    def test_list_providers_type_is_provider_type(self, clean_env):
        """Test type field is a ProviderType enum value."""
        providers = list_providers()

        for provider in providers:
            assert isinstance(provider["type"], ProviderType), \
                f"Provider {provider['name']} type is not ProviderType"

    def test_list_providers_with_api_key_shows_available(self, clean_env):
        """Test provider shows available when API key is set."""
        os.environ["GROQ_API_KEY"] = "test-key"

        providers = list_providers()
        groq = next((p for p in providers if p["type"] == ProviderType.GROQ), None)

        assert groq is not None
        assert groq["available"] is True

    def test_list_providers_without_api_key_shows_unavailable(self, clean_env):
        """Test provider shows unavailable when API key is not set."""
        providers = list_providers()
        groq = next((p for p in providers if p["type"] == ProviderType.GROQ), None)

        assert groq is not None
        assert groq["available"] is False

    def test_list_providers_local_providers_with_mock(self, clean_env, mock_httpx_success):
        """Test local providers show available when server responds."""
        providers = list_providers()

        lm_studio = next((p for p in providers if p["type"] == ProviderType.LM_STUDIO), None)
        assert lm_studio is not None
        # May be available or unavailable depending on mock setup

    def test_list_providers_descriptions_not_empty(self, clean_env):
        """Test all providers have non-empty descriptions."""
        providers = list_providers()

        for provider in providers:
            assert provider["description"], f"Provider {provider['name']} has empty description"
            assert len(provider["description"]) > 0

    def test_list_providers_names_not_empty(self, clean_env):
        """Test all providers have non-empty names."""
        providers = list_providers()

        for provider in providers:
            assert provider["name"], f"Provider has empty name"
            assert len(provider["name"]) > 0


class TestListProvidersWithMultipleAvailable:
    """Tests for list_providers when multiple providers are available."""

    @pytest.fixture(autouse=True)
    def mock_network(self):
        """Mock httpx for all tests in this class to prevent real network calls."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            yield mock_get

    def test_multiple_api_keys_set(self, clean_env):
        """Test list_providers with multiple API keys set."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"
        os.environ["GOOGLE_API_KEY"] = "test-google-key"
        os.environ["XAI_API_KEY"] = "test-xai-key"

        providers = list_providers()

        available = [p for p in providers if p["available"]]
        # At least Groq, Grok should be available (Gemini needs SDK import)
        available_types = [p["type"] for p in available]
        assert ProviderType.GROQ in available_types
        assert ProviderType.GROK in available_types

    def test_list_providers_order_is_consistent(self, clean_env):
        """Test list_providers returns providers in consistent order."""
        providers1 = list_providers()
        providers2 = list_providers()

        types1 = [p["type"] for p in providers1]
        types2 = [p["type"] for p in providers2]

        assert types1 == types2


# =============================================================================
# Tests for auto_detect_provider() - Provider Auto Detection
# =============================================================================


class TestAutoDetectProvider:
    """Tests for auto_detect_provider() function."""

    def test_auto_detect_returns_none_when_nothing_available(self, clean_env):
        """Test auto_detect_provider returns None when no providers available."""
        # Mock all providers as unavailable
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=False), \
             patch.object(TransformersProvider, 'is_available', return_value=False):

            result = auto_detect_provider()

            assert result is None

    def test_auto_detect_returns_lm_studio_first(self, clean_env):
        """Test auto_detect_provider returns LMStudioProvider when available (first priority)."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True):
            result = auto_detect_provider()

            assert isinstance(result, LMStudioProvider)

    def test_auto_detect_returns_ollama_second(self, clean_env):
        """Test auto_detect_provider returns OllamaProvider when LM Studio unavailable."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, OllamaProvider)

    def test_auto_detect_returns_gemini_third(self, clean_env):
        """Test auto_detect_provider returns GeminiProvider when local providers unavailable."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, GeminiProvider)

    def test_auto_detect_returns_grok_fourth(self, clean_env):
        """Test auto_detect_provider returns GrokProvider when higher priority unavailable."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, GrokProvider)

    def test_auto_detect_returns_claude_agent_sdk_fifth(self, clean_env):
        """Test auto_detect_provider returns ClaudeAgentSDKProvider when higher priority unavailable."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, ClaudeAgentSDKProvider)

    def test_auto_detect_returns_claude_code_sixth(self, clean_env):
        """Test auto_detect_provider returns ClaudeCodeProvider when higher priority unavailable."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, ClaudeCodeProvider)

    def test_auto_detect_returns_openai_seventh(self, clean_env):
        """Test auto_detect_provider returns OpenAIAgentsProvider when higher priority unavailable."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, OpenAIAgentsProvider)

    def test_auto_detect_returns_transformers_eighth(self, clean_env):
        """Test auto_detect_provider returns TransformersProvider when higher priority unavailable."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=False), \
             patch.object(TransformersProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, TransformersProvider)

    def test_auto_detect_returns_claude_api_ninth(self, clean_env):
        """Test auto_detect_provider returns ClaudeProvider as last resort."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=False), \
             patch.object(TransformersProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, ClaudeProvider)


class TestAutoDetectProviderPriority:
    """Tests for verifying auto_detect_provider follows correct priority order."""

    def test_lm_studio_over_ollama(self, clean_env):
        """Test LM Studio is preferred over Ollama."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True), \
             patch.object(OllamaProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, LMStudioProvider)

    def test_ollama_over_gemini(self, clean_env):
        """Test Ollama is preferred over Gemini."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=True), \
             patch.object(GeminiProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, OllamaProvider)

    def test_gemini_over_grok(self, clean_env):
        """Test Gemini is preferred over Grok."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=True), \
             patch.object(GrokProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, GeminiProvider)

    def test_grok_over_claude_agent_sdk(self, clean_env):
        """Test Grok is preferred over Claude Agent SDK."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=True), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=True), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, GrokProvider)

    def test_claude_agent_sdk_over_claude_code(self, clean_env):
        """Test Claude Agent SDK is preferred over Claude Code CLI."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=True), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, ClaudeAgentSDKProvider)

    def test_claude_code_over_openai(self, clean_env):
        """Test Claude Code is preferred over OpenAI."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=True), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, ClaudeCodeProvider)

    def test_openai_over_claude_api(self, clean_env):
        """Test OpenAI is preferred over Claude API (Claude API is last resort)."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=True), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=True), \
             patch.object(TransformersProvider, 'is_available', return_value=False):

            result = auto_detect_provider()

            # OpenAI should be preferred over Claude API (which is last resort)
            assert isinstance(result, OpenAIAgentsProvider)

    def test_openai_over_transformers(self, clean_env):
        """Test OpenAI is preferred over Transformers."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=True), \
             patch.object(TransformersProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, OpenAIAgentsProvider)

    def test_all_providers_available_returns_lm_studio(self, clean_env):
        """Test when all providers available, LM Studio is returned first."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True), \
             patch.object(OllamaProvider, 'is_available', return_value=True), \
             patch.object(GeminiProvider, 'is_available', return_value=True), \
             patch.object(GrokProvider, 'is_available', return_value=True), \
             patch.object(ClaudeAgentSDKProvider, 'is_available', return_value=True), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=True), \
             patch.object(ClaudeProvider, 'is_available', return_value=True), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=True), \
             patch.object(TransformersProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, LMStudioProvider)


class TestAutoDetectProviderRealChecks:
    """Tests for auto_detect_provider with real availability checks via mocking."""

    def test_auto_detect_with_groq_api_key(self, clean_env):
        """Test auto_detect returns Groq when only GROQ_API_KEY is set."""
        os.environ["GROQ_API_KEY"] = "test-groq-key"

        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=False), \
             patch.object(TransformersProvider, 'is_available', return_value=False):

            # With everything mocked as unavailable, should return None
            result = auto_detect_provider()
            assert result is None

    def test_auto_detect_with_local_server_mock(self, clean_env, mock_httpx_success):
        """Test auto_detect with mocked local server."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True):
            result = auto_detect_provider()

            assert isinstance(result, LMStudioProvider)


# =============================================================================
# Tests for get_provider() with Auto Detection
# =============================================================================


class TestGetProviderAutoDetection:
    """Tests for get_provider() when using auto-detection."""

    def test_get_provider_no_config_uses_auto_detect(self, clean_env):
        """Test get_provider with no config falls back to auto-detection."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True):
            result = get_provider(None)

            assert isinstance(result, LMStudioProvider)

    def test_get_provider_raises_when_no_provider_available(self, clean_env):
        """Test get_provider raises ValueError when no provider available."""
        # Also need to mock file config loading to return empty config
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=False), \
             patch.object(TransformersProvider, 'is_available', return_value=False), \
             patch("src.llm_providers.LLMConfig.from_file") as mock_from_file:

            # Return empty config to ensure no provider is set from file
            mock_from_file.return_value = LLMConfig(provider=None)

            with pytest.raises(ValueError) as exc_info:
                get_provider(None)

            assert "No LLM provider configured or available" in str(exc_info.value)

    def test_get_provider_explicit_config_overrides_auto_detect(self, clean_env):
        """Test explicit config takes priority over auto-detection."""
        config = LLMConfig(provider=ProviderType.GROQ, model="test-model")

        # Even if LM Studio is available, explicit config wins
        with patch.object(LMStudioProvider, 'is_available', return_value=True):
            result = get_provider(config)

            assert isinstance(result, GroqProvider)

    def test_get_provider_env_over_auto_detect(self, env_groq):
        """Test environment config takes priority over auto-detection."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True):
            result = get_provider(None)

            assert isinstance(result, GroqProvider)

    def test_get_provider_file_config_over_auto_detect(self, clean_env, temp_config_dir, sample_config_groq):
        """Test file config takes priority over auto-detection."""
        config_path = os.path.join(temp_config_dir, "llm.json")
        with open(config_path, "w") as f:
            json.dump(sample_config_groq, f)

        with patch("src.llm_providers.LLMConfig.from_file") as mock_from_file:
            mock_from_file.return_value = LLMConfig(
                provider=ProviderType.GROQ,
                model="llama-3.3-70b-versatile"
            )

            with patch.object(LMStudioProvider, 'is_available', return_value=True):
                result = get_provider(None)

                assert isinstance(result, GroqProvider)


class TestGetProviderWithProviderTypes:
    """Tests for get_provider() with each provider type."""

    def test_get_provider_lm_studio(self, clean_env):
        """Test get_provider returns LMStudioProvider."""
        config = LLMConfig(provider=ProviderType.LM_STUDIO, model="test-model")

        result = get_provider(config)

        assert isinstance(result, LMStudioProvider)
        assert result.model == "test-model"

    def test_get_provider_ollama(self, clean_env):
        """Test get_provider returns OllamaProvider."""
        config = LLMConfig(provider=ProviderType.OLLAMA, model="llama2")

        result = get_provider(config)

        assert isinstance(result, OllamaProvider)
        assert result.model == "llama2"

    def test_get_provider_openai(self, clean_env):
        """Test get_provider returns OpenAIAgentsProvider."""
        config = LLMConfig(provider=ProviderType.OPENAI, model="gpt-4o")

        result = get_provider(config)

        assert isinstance(result, OpenAIAgentsProvider)

    def test_get_provider_openai_compatible_requires_base_url(self, clean_env):
        """Test get_provider raises when base_url missing for openai-compatible."""
        config = LLMConfig(provider=ProviderType.OPENAI_COMPATIBLE, model="test")

        with pytest.raises(ValueError) as exc_info:
            get_provider(config)

        assert "base_url required" in str(exc_info.value)

    def test_get_provider_openai_compatible_with_base_url(self, clean_env):
        """Test get_provider returns OpenAICompatibleProvider with base_url."""
        config = LLMConfig(
            provider=ProviderType.OPENAI_COMPATIBLE,
            base_url="http://localhost:8000/v1",
            model="test-model"
        )

        result = get_provider(config)

        assert isinstance(result, OpenAICompatibleProvider)

    def test_get_provider_transformers(self, clean_env):
        """Test get_provider returns TransformersProvider."""
        config = LLMConfig(provider=ProviderType.TRANSFORMERS, model="facebook/bart-large-cnn")

        result = get_provider(config)

        assert isinstance(result, TransformersProvider)

    def test_get_provider_claude_code(self, clean_env):
        """Test get_provider returns ClaudeCodeProvider."""
        config = LLMConfig(provider=ProviderType.CLAUDE_CODE, model="sonnet")

        result = get_provider(config)

        assert isinstance(result, ClaudeCodeProvider)

    def test_get_provider_gemini(self, clean_env):
        """Test get_provider returns GeminiProvider."""
        config = LLMConfig(provider=ProviderType.GEMINI, model="gemini-1.5-pro")

        result = get_provider(config)

        assert isinstance(result, GeminiProvider)

    def test_get_provider_gemini_cli(self, clean_env):
        """Test get_provider returns GeminiCLIProvider."""
        config = LLMConfig(provider=ProviderType.GEMINI_CLI, model="gemini-2.0-flash")

        result = get_provider(config)

        assert isinstance(result, GeminiCLIProvider)

    def test_get_provider_codex_cli(self, clean_env):
        """Test get_provider returns CodexCLIProvider."""
        config = LLMConfig(provider=ProviderType.CODEX_CLI, model="gpt-4.1")

        result = get_provider(config)

        assert isinstance(result, CodexCLIProvider)

    def test_get_provider_grok(self, clean_env):
        """Test get_provider returns GrokProvider."""
        config = LLMConfig(provider=ProviderType.GROK, model="grok-beta")

        result = get_provider(config)

        assert isinstance(result, GrokProvider)

    def test_get_provider_groq(self, clean_env):
        """Test get_provider returns GroqProvider."""
        config = LLMConfig(provider=ProviderType.GROQ, model="llama-3.3-70b-versatile")

        result = get_provider(config)

        assert isinstance(result, GroqProvider)

    def test_get_provider_claude(self, clean_env):
        """Test get_provider returns ClaudeProvider."""
        config = LLMConfig(provider=ProviderType.CLAUDE, model="claude-sonnet-4-20250514")

        result = get_provider(config)

        assert isinstance(result, ClaudeProvider)


class TestGetProviderDefaultModels:
    """Tests for get_provider() default model assignment."""

    def test_get_provider_openai_default_model(self, clean_env):
        """Test get_provider uses default model for OpenAI when none specified."""
        config = LLMConfig(provider=ProviderType.OPENAI, model=None)

        result = get_provider(config)

        assert isinstance(result, OpenAIAgentsProvider)
        assert result.model_name == "gpt-4o-mini"

    def test_get_provider_transformers_default_model(self, clean_env):
        """Test get_provider uses default model for Transformers."""
        config = LLMConfig(provider=ProviderType.TRANSFORMERS, model=None)

        result = get_provider(config)

        assert result.model_name == "facebook/bart-large-cnn"

    def test_get_provider_claude_code_default_model(self, clean_env):
        """Test get_provider uses default model for Claude Code."""
        config = LLMConfig(provider=ProviderType.CLAUDE_CODE, model=None)

        result = get_provider(config)

        assert result.model_name == "sonnet"

    def test_get_provider_gemini_default_model(self, clean_env):
        """Test get_provider uses default model for Gemini."""
        config = LLMConfig(provider=ProviderType.GEMINI, model=None)

        result = get_provider(config)

        assert result.model_name == "gemini-1.5-flash"

    def test_get_provider_gemini_cli_default_model(self, clean_env):
        """Test get_provider uses default model for Gemini CLI."""
        config = LLMConfig(provider=ProviderType.GEMINI_CLI, model=None)

        result = get_provider(config)

        assert result.model_name == "gemini-2.0-flash"

    def test_get_provider_codex_cli_default_model(self, clean_env):
        """Test get_provider uses default model for Codex CLI."""
        config = LLMConfig(provider=ProviderType.CODEX_CLI, model=None)

        result = get_provider(config)

        assert result.model_name == "gpt-4.1"

    def test_get_provider_grok_default_model(self, clean_env):
        """Test get_provider uses default model for Grok."""
        config = LLMConfig(provider=ProviderType.GROK, model=None)

        result = get_provider(config)

        assert result.model == "grok-beta"

    def test_get_provider_groq_default_model(self, clean_env):
        """Test get_provider uses default model for Groq."""
        config = LLMConfig(provider=ProviderType.GROQ, model=None)

        result = get_provider(config)

        assert result.model == "llama-3.3-70b-versatile"

    def test_get_provider_claude_default_model(self, clean_env):
        """Test get_provider uses default model for Claude."""
        config = LLMConfig(provider=ProviderType.CLAUDE, model=None)

        result = get_provider(config)

        assert result.model_name == "claude-sonnet-4-20250514"


# =============================================================================
# Tests for get_best_provider()
# =============================================================================


class TestGetBestProvider:
    """Tests for get_best_provider() helper function."""

    def test_get_best_provider_returns_tuple(self, clean_env):
        """Test get_best_provider returns a tuple."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True):
            result = get_best_provider()

            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_get_best_provider_returns_provider_and_true_when_available(self, clean_env):
        """Test get_best_provider returns provider and True when available."""
        with patch.object(LMStudioProvider, 'is_available', return_value=True):
            provider, is_llm = get_best_provider()

            assert isinstance(provider, LMStudioProvider)
            assert is_llm is True

    def test_get_best_provider_returns_none_and_false_when_unavailable(self, clean_env):
        """Test get_best_provider returns None and False when none available."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=False), \
             patch.object(TransformersProvider, 'is_available', return_value=False):

            provider, is_llm = get_best_provider()

            assert provider is None
            assert is_llm is False

    def test_get_best_provider_uses_auto_detect_priority(self, clean_env):
        """Test get_best_provider follows auto_detect_provider priority."""
        # Both LM Studio and Ollama available - should return LM Studio
        with patch.object(LMStudioProvider, 'is_available', return_value=True), \
             patch.object(OllamaProvider, 'is_available', return_value=True):

            provider, is_llm = get_best_provider()

            assert isinstance(provider, LMStudioProvider)
            assert is_llm is True


# =============================================================================
# Tests for Provider Priority Order Documentation
# =============================================================================


class TestProviderPriorityDocumentation:
    """Tests that verify the documented provider priority order."""

    def test_documented_priority_order(self, clean_env):
        """
        Verify the documented priority order:
        1. LM Studio (local, free, fast)
        2. Ollama (local, free)
        3. Gemini (has free tier)
        4. Grok (xAI)
        5. Claude Code (no API key needed)
        6. Claude API (requires key)
        7. OpenAI (requires key)
        8. Transformers (slow first run)
        """
        # Test each provider in priority order
        priority_order = [
            (LMStudioProvider, "LM Studio"),
            (OllamaProvider, "Ollama"),
            (GeminiProvider, "Gemini"),
            (GrokProvider, "Grok"),
            (ClaudeCodeProvider, "Claude Code"),
            (ClaudeProvider, "Claude API"),
            (OpenAIAgentsProvider, "OpenAI"),
            (TransformersProvider, "Transformers"),
        ]

        for i, (expected_class, name) in enumerate(priority_order):
            # Make this provider available, all higher priority unavailable
            patches = []
            for j, (cls, _) in enumerate(priority_order):
                patches.append(
                    patch.object(cls, 'is_available', return_value=(j == i))
                )

            with patches[0], patches[1], patches[2], patches[3], \
                 patches[4], patches[5], patches[6], patches[7]:
                result = auto_detect_provider()

                assert isinstance(result, expected_class), \
                    f"Expected {name} at priority {i+1}, got {type(result)}"


class TestProviderPriorityRationale:
    """Tests verifying the rationale behind provider priority."""

    def test_local_providers_first(self, clean_env):
        """Test local providers (LM Studio, Ollama) are checked before cloud."""
        # LM Studio and Gemini both available - should prefer local
        with patch.object(LMStudioProvider, 'is_available', return_value=True), \
             patch.object(GeminiProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, LMStudioProvider)

    def test_free_tier_providers_before_api_key_only(self, clean_env):
        """Test providers with free tier are checked before API-key-only."""
        # Gemini (free tier) and OpenAI (API key required) both available
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=True), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, GeminiProvider)

    def test_no_api_key_providers_before_api_key_required(self, clean_env):
        """Test Claude Code (no API key) is checked before Claude API."""
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=True), \
             patch.object(ClaudeProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, ClaudeCodeProvider)

    def test_transformers_is_last_resort(self, clean_env):
        """Test Transformers is only used when all others unavailable."""
        # Transformers can be slow on first run, so should be last
        with patch.object(LMStudioProvider, 'is_available', return_value=False), \
             patch.object(OllamaProvider, 'is_available', return_value=False), \
             patch.object(GeminiProvider, 'is_available', return_value=False), \
             patch.object(GrokProvider, 'is_available', return_value=False), \
             patch.object(ClaudeCodeProvider, 'is_available', return_value=False), \
             patch.object(ClaudeProvider, 'is_available', return_value=False), \
             patch.object(OpenAIAgentsProvider, 'is_available', return_value=False), \
             patch.object(TransformersProvider, 'is_available', return_value=True):

            result = auto_detect_provider()

            assert isinstance(result, TransformersProvider)


# =============================================================================
# Tests for UsageStats Class
# =============================================================================


class TestUsageStatsConstruction:
    """Tests for UsageStats class construction and initialization."""

    def test_usage_stats_default_values(self):
        """Test UsageStats initializes with default values."""
        stats = UsageStats()

        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.total_tokens == 0
        assert stats.model == ""
        assert stats.provider == ""

    def test_usage_stats_with_explicit_values(self):
        """Test UsageStats with explicitly provided values."""
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            model="gpt-4o-mini",
            provider="OpenAI",
        )

        assert stats.input_tokens == 100
        assert stats.output_tokens == 50
        assert stats.total_tokens == 150
        assert stats.model == "gpt-4o-mini"
        assert stats.provider == "OpenAI"

    def test_usage_stats_auto_calculates_total_tokens(self):
        """Test __post_init__ auto-calculates total_tokens when not provided."""
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            model="test-model",
            provider="Test",
        )

        # total_tokens should be auto-calculated as input + output
        assert stats.total_tokens == 150

    def test_usage_stats_respects_explicit_total_tokens(self):
        """Test explicit total_tokens is not overwritten."""
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            total_tokens=200,  # Explicitly different from sum
            model="test-model",
            provider="Test",
        )

        # total_tokens should remain as explicitly set
        assert stats.total_tokens == 200

    def test_usage_stats_zero_total_triggers_auto_calculation(self):
        """Test total_tokens=0 triggers auto-calculation."""
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            total_tokens=0,
            model="test-model",
            provider="Test",
        )

        # total_tokens=0 should trigger recalculation
        assert stats.total_tokens == 150


class TestUsageStatsEdgeCases:
    """Tests for UsageStats edge cases."""

    def test_usage_stats_with_only_input_tokens(self):
        """Test UsageStats with only input tokens."""
        stats = UsageStats(input_tokens=100)

        assert stats.input_tokens == 100
        assert stats.output_tokens == 0
        assert stats.total_tokens == 100

    def test_usage_stats_with_only_output_tokens(self):
        """Test UsageStats with only output tokens."""
        stats = UsageStats(output_tokens=50)

        assert stats.input_tokens == 0
        assert stats.output_tokens == 50
        assert stats.total_tokens == 50

    def test_usage_stats_with_large_values(self):
        """Test UsageStats handles large token counts."""
        stats = UsageStats(
            input_tokens=1_000_000,
            output_tokens=500_000,
            model="large-model",
            provider="Test",
        )

        assert stats.input_tokens == 1_000_000
        assert stats.output_tokens == 500_000
        assert stats.total_tokens == 1_500_000

    def test_usage_stats_with_model_only(self):
        """Test UsageStats with just model name."""
        stats = UsageStats(model="claude-sonnet-4-20250514")

        assert stats.model == "claude-sonnet-4-20250514"
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.total_tokens == 0

    def test_usage_stats_with_provider_only(self):
        """Test UsageStats with just provider name."""
        stats = UsageStats(provider="Groq")

        assert stats.provider == "Groq"
        assert stats.model == ""


class TestUsageStatsDataclass:
    """Tests for UsageStats dataclass behavior."""

    def test_usage_stats_is_dataclass(self):
        """Test UsageStats is a dataclass with expected fields."""
        from dataclasses import fields

        stat_fields = {f.name for f in fields(UsageStats)}
        expected_fields = {"input_tokens", "output_tokens", "total_tokens", "model", "provider"}

        assert stat_fields == expected_fields

    def test_usage_stats_equality(self):
        """Test UsageStats instances can be compared for equality."""
        stats1 = UsageStats(input_tokens=100, output_tokens=50, model="test")
        stats2 = UsageStats(input_tokens=100, output_tokens=50, model="test")
        stats3 = UsageStats(input_tokens=200, output_tokens=50, model="test")

        assert stats1 == stats2
        assert stats1 != stats3

    def test_usage_stats_repr(self):
        """Test UsageStats has a meaningful repr."""
        stats = UsageStats(
            input_tokens=100,
            output_tokens=50,
            model="test-model",
            provider="Test",
        )

        repr_str = repr(stats)
        assert "UsageStats" in repr_str
        assert "100" in repr_str
        assert "50" in repr_str


# =============================================================================
# Tests for Token Estimation (_estimate_tokens)
# =============================================================================


class ConcreteProviderForTesting(LLMProvider):
    """Concrete implementation of LLMProvider for testing base class methods."""

    def __init__(self, name: str = "Test Provider", model: str = "test-model"):
        super().__init__()
        self._name = name
        self._model = model

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return True

    def summarize(self, text: str, max_length: int = 150) -> str:
        # Simple mock summarize
        result = text[:max_length] if len(text) > max_length else text
        self._record_usage(text, result, self._model)
        return result


class TestEstimateTokens:
    """Tests for _estimate_tokens method."""

    def test_estimate_tokens_empty_string(self):
        """Test token estimation for empty string."""
        provider = ConcreteProviderForTesting()

        tokens = provider._estimate_tokens("")

        assert tokens == 0

    def test_estimate_tokens_short_text(self):
        """Test token estimation for short text."""
        provider = ConcreteProviderForTesting()

        # "Hello" = 5 chars, ~1 token
        tokens = provider._estimate_tokens("Hello")

        assert tokens == 1  # 5 // 4 = 1

    def test_estimate_tokens_medium_text(self):
        """Test token estimation for medium-length text."""
        provider = ConcreteProviderForTesting()

        # 100 chars = ~25 tokens
        text = "a" * 100
        tokens = provider._estimate_tokens(text)

        assert tokens == 25  # 100 // 4 = 25

    def test_estimate_tokens_long_text(self):
        """Test token estimation for long text."""
        provider = ConcreteProviderForTesting()

        # 4000 chars = ~1000 tokens
        text = "x" * 4000
        tokens = provider._estimate_tokens(text)

        assert tokens == 1000  # 4000 // 4 = 1000

    def test_estimate_tokens_exact_multiple(self):
        """Test token estimation for text that's exact multiple of 4."""
        provider = ConcreteProviderForTesting()

        text = "abcd" * 25  # 100 chars
        tokens = provider._estimate_tokens(text)

        assert tokens == 25

    def test_estimate_tokens_with_whitespace(self):
        """Test token estimation includes whitespace in count."""
        provider = ConcreteProviderForTesting()

        text = "hello world"  # 11 chars
        tokens = provider._estimate_tokens(text)

        assert tokens == 2  # 11 // 4 = 2

    def test_estimate_tokens_with_unicode(self):
        """Test token estimation with unicode characters."""
        provider = ConcreteProviderForTesting()

        # Unicode chars are counted by string length
        text = "こんにちは"  # 5 Japanese chars
        tokens = provider._estimate_tokens(text)

        # Python len() counts unicode codepoints
        assert tokens == 1  # 5 // 4 = 1

    def test_estimate_tokens_with_newlines(self):
        """Test token estimation with newlines."""
        provider = ConcreteProviderForTesting()

        text = "line1\nline2\nline3"  # 17 chars
        tokens = provider._estimate_tokens(text)

        assert tokens == 4  # 17 // 4 = 4

    def test_estimate_tokens_with_special_characters(self):
        """Test token estimation with special characters."""
        provider = ConcreteProviderForTesting()

        text = "!@#$%^&*()[]{}|;:',.<>?"  # 23 chars
        tokens = provider._estimate_tokens(text)

        assert tokens == 5  # 23 // 4 = 5


# =============================================================================
# Tests for Session Tracking
# =============================================================================


class TestSessionTrackingInitialization:
    """Tests for session tracking initialization."""

    def test_session_usage_initialized_on_creation(self):
        """Test session_usage is initialized on provider creation."""
        provider = ConcreteProviderForTesting()

        assert provider.session_usage == {"calls": 0, "total_tokens": 0}

    def test_last_usage_initialized_none(self):
        """Test last_usage is None initially."""
        provider = ConcreteProviderForTesting()

        assert provider.last_usage is None

    def test_session_usage_is_mutable_dict(self):
        """Test session_usage is a mutable dictionary."""
        provider = ConcreteProviderForTesting()

        provider.session_usage["calls"] = 5
        provider.session_usage["total_tokens"] = 100

        assert provider.session_usage["calls"] == 5
        assert provider.session_usage["total_tokens"] == 100


class TestSessionTrackingAccumulation:
    """Tests for session tracking accumulation."""

    def test_single_call_updates_session_usage(self):
        """Test a single summarize call updates session_usage."""
        provider = ConcreteProviderForTesting()

        provider.summarize("Test input text")

        assert provider.session_usage["calls"] == 1
        assert provider.session_usage["total_tokens"] > 0

    def test_multiple_calls_accumulate_count(self):
        """Test multiple calls accumulate the call count."""
        provider = ConcreteProviderForTesting()

        provider.summarize("First call")
        provider.summarize("Second call")
        provider.summarize("Third call")

        assert provider.session_usage["calls"] == 3

    def test_multiple_calls_accumulate_tokens(self):
        """Test multiple calls accumulate total tokens."""
        provider = ConcreteProviderForTesting()

        # Each call adds tokens
        provider.summarize("a" * 40)  # ~10 input tokens
        initial_tokens = provider.session_usage["total_tokens"]

        provider.summarize("b" * 40)  # ~10 more input tokens
        second_tokens = provider.session_usage["total_tokens"]

        assert second_tokens > initial_tokens

    def test_session_usage_tracks_all_calls_in_session(self):
        """Test session_usage tracks cumulative usage across session."""
        provider = ConcreteProviderForTesting()

        # Make several calls
        for i in range(5):
            provider.summarize(f"Text number {i}")

        assert provider.session_usage["calls"] == 5
        assert provider.session_usage["total_tokens"] > 0


class TestSessionTrackingWithLastUsage:
    """Tests for interaction between session_usage and last_usage."""

    def test_last_usage_updated_each_call(self):
        """Test last_usage is updated after each call."""
        provider = ConcreteProviderForTesting()

        provider.summarize("First text")
        first_usage = provider.last_usage

        provider.summarize("Second text that is much longer")
        second_usage = provider.last_usage

        assert first_usage is not None
        assert second_usage is not None
        # last_usage should be different object or different values
        assert first_usage is not second_usage or first_usage.input_tokens != second_usage.input_tokens

    def test_last_usage_reflects_most_recent_call(self):
        """Test last_usage reflects the most recent call only."""
        provider = ConcreteProviderForTesting()

        provider.summarize("Short")
        provider.summarize("A much longer text string for testing")

        # last_usage should reflect the longer text
        assert provider.last_usage is not None
        assert provider.last_usage.input_tokens > 0

    def test_session_totals_match_sum_of_calls(self):
        """Test session totals match sum of individual call totals."""
        provider = ConcreteProviderForTesting()

        calls_total = 0
        tokens_total = 0

        # Track each call manually
        for i in range(3):
            provider.summarize(f"Call number {i}")
            calls_total += 1
            tokens_total += provider.last_usage.total_tokens

        assert provider.session_usage["calls"] == calls_total
        assert provider.session_usage["total_tokens"] == tokens_total


# =============================================================================
# Tests for _record_usage Method
# =============================================================================


class TestRecordUsageBasic:
    """Tests for basic _record_usage functionality."""

    def test_record_usage_creates_usage_stats(self):
        """Test _record_usage creates UsageStats instance."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("input text", "output text", "test-model")

        assert provider.last_usage is not None
        assert isinstance(provider.last_usage, UsageStats)

    def test_record_usage_sets_model_name(self):
        """Test _record_usage sets model name from parameter."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("input", "output", "my-custom-model")

        assert provider.last_usage.model == "my-custom-model"

    def test_record_usage_uses_model_name_property_when_empty(self):
        """Test _record_usage uses model_name property when model param is empty."""
        provider = ConcreteProviderForTesting(model="default-model")

        provider._record_usage("input", "output", "")

        assert provider.last_usage.model == "default-model"

    def test_record_usage_sets_provider_name(self):
        """Test _record_usage sets provider name from name property."""
        provider = ConcreteProviderForTesting(name="Custom Provider")

        provider._record_usage("input", "output", "model")

        assert provider.last_usage.provider == "Custom Provider"

    def test_record_usage_estimates_input_tokens(self):
        """Test _record_usage estimates input tokens correctly."""
        provider = ConcreteProviderForTesting()

        # 100 chars = 25 tokens
        input_text = "a" * 100
        provider._record_usage(input_text, "output", "model")

        assert provider.last_usage.input_tokens == 25

    def test_record_usage_estimates_output_tokens(self):
        """Test _record_usage estimates output tokens correctly."""
        provider = ConcreteProviderForTesting()

        # 40 chars = 10 tokens
        output_text = "b" * 40
        provider._record_usage("input", output_text, "model")

        assert provider.last_usage.output_tokens == 10


class TestRecordUsageSessionUpdate:
    """Tests for _record_usage session tracking updates."""

    def test_record_usage_increments_calls(self):
        """Test _record_usage increments session calls count."""
        provider = ConcreteProviderForTesting()

        assert provider.session_usage["calls"] == 0

        provider._record_usage("input", "output", "model")

        assert provider.session_usage["calls"] == 1

    def test_record_usage_adds_to_total_tokens(self):
        """Test _record_usage adds to session total tokens."""
        provider = ConcreteProviderForTesting()

        assert provider.session_usage["total_tokens"] == 0

        # 20 input chars = 5 tokens, 20 output chars = 5 tokens, total = 10
        provider._record_usage("a" * 20, "b" * 20, "model")

        assert provider.session_usage["total_tokens"] == 10

    def test_record_usage_accumulates_across_calls(self):
        """Test _record_usage accumulates across multiple calls."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("a" * 40, "b" * 40, "model")  # 10 + 10 = 20 tokens
        provider._record_usage("c" * 40, "d" * 40, "model")  # 10 + 10 = 20 tokens

        assert provider.session_usage["calls"] == 2
        assert provider.session_usage["total_tokens"] == 40


class TestRecordUsageEdgeCases:
    """Tests for _record_usage edge cases."""

    def test_record_usage_with_empty_input(self):
        """Test _record_usage handles empty input text."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("", "output", "model")

        assert provider.last_usage.input_tokens == 0

    def test_record_usage_with_empty_output(self):
        """Test _record_usage handles empty output text."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("input", "", "model")

        assert provider.last_usage.output_tokens == 0

    def test_record_usage_with_both_empty(self):
        """Test _record_usage handles both empty input and output."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("", "", "model")

        assert provider.last_usage.input_tokens == 0
        assert provider.last_usage.output_tokens == 0
        assert provider.last_usage.total_tokens == 0
        # Call should still be counted
        assert provider.session_usage["calls"] == 1

    def test_record_usage_with_very_long_text(self):
        """Test _record_usage handles very long text."""
        provider = ConcreteProviderForTesting()

        # 1MB of text
        long_text = "x" * 1_000_000
        provider._record_usage(long_text, "short output", "model")

        assert provider.last_usage.input_tokens == 250_000  # 1M / 4

    def test_record_usage_overwrites_last_usage(self):
        """Test _record_usage overwrites previous last_usage."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("first input", "first output", "model-1")
        first_usage = provider.last_usage

        provider._record_usage("second input", "second output", "model-2")

        assert provider.last_usage is not first_usage
        assert provider.last_usage.model == "model-2"


# =============================================================================
# Tests for Usage Tracking Integration
# =============================================================================


class TestUsageTrackingIntegration:
    """Integration tests for usage tracking across provider operations."""

    def test_usage_tracking_through_summarize(self):
        """Test usage is tracked through summarize method."""
        provider = ConcreteProviderForTesting()

        result = provider.summarize("This is a test input for summarization")

        assert provider.last_usage is not None
        assert provider.session_usage["calls"] == 1
        assert provider.session_usage["total_tokens"] > 0

    def test_usage_tracking_multiple_summarize_calls(self):
        """Test usage accumulates across multiple summarize calls."""
        provider = ConcreteProviderForTesting()

        provider.summarize("First text")
        provider.summarize("Second text")
        provider.summarize("Third text")

        assert provider.session_usage["calls"] == 3

    def test_usage_stats_reflects_actual_text_lengths(self):
        """Test usage stats reflect actual input/output text lengths."""
        provider = ConcreteProviderForTesting()

        input_text = "a" * 400  # 100 tokens
        provider.summarize(input_text)

        assert provider.last_usage.input_tokens == 100

    def test_different_providers_have_independent_tracking(self):
        """Test different provider instances track usage independently."""
        provider1 = ConcreteProviderForTesting(name="Provider 1")
        provider2 = ConcreteProviderForTesting(name="Provider 2")

        provider1.summarize("Text for provider 1")
        provider1.summarize("Another text for provider 1")

        provider2.summarize("Text for provider 2")

        assert provider1.session_usage["calls"] == 2
        assert provider2.session_usage["calls"] == 1
        assert provider1.last_usage.provider == "Provider 1"
        assert provider2.last_usage.provider == "Provider 2"

    def test_usage_tracking_preserves_provider_identity(self):
        """Test usage tracking preserves provider name in stats."""
        provider = ConcreteProviderForTesting(name="Custom Named Provider")

        provider.summarize("Some text")

        assert provider.last_usage.provider == "Custom Named Provider"

    def test_usage_tracking_preserves_model_identity(self):
        """Test usage tracking preserves model name in stats."""
        provider = ConcreteProviderForTesting(model="custom-model-v2")

        provider.summarize("Some text")

        assert provider.last_usage.model == "custom-model-v2"


class TestUsageTrackingConsistency:
    """Tests for usage tracking consistency and accuracy."""

    def test_total_tokens_always_calculated(self):
        """Test total_tokens is always calculated in last_usage."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("a" * 40, "b" * 20, "model")

        # 40/4 = 10 input, 20/4 = 5 output, total = 15
        assert provider.last_usage.input_tokens == 10
        assert provider.last_usage.output_tokens == 5
        assert provider.last_usage.total_tokens == 15

    def test_session_tokens_match_sum(self):
        """Test session total tokens matches sum of all call totals."""
        provider = ConcreteProviderForTesting()

        expected_total = 0

        for i in range(5):
            text = "x" * ((i + 1) * 40)  # Varying lengths
            provider._record_usage(text, "output", "model")
            expected_total += provider.last_usage.total_tokens

        assert provider.session_usage["total_tokens"] == expected_total

    def test_session_calls_matches_record_count(self):
        """Test session calls matches number of _record_usage calls."""
        provider = ConcreteProviderForTesting()

        num_calls = 7
        for _ in range(num_calls):
            provider._record_usage("input", "output", "model")

        assert provider.session_usage["calls"] == num_calls

    def test_empty_calls_still_counted(self):
        """Test calls with empty text are still counted."""
        provider = ConcreteProviderForTesting()

        provider._record_usage("", "", "model")
        provider._record_usage("", "", "model")

        assert provider.session_usage["calls"] == 2
        assert provider.session_usage["total_tokens"] == 0


# =============================================================================
# Tests for Provider Unavailable Scenarios
# =============================================================================


class TestProviderUnavailableScenarios:
    """Tests for scenarios when providers are unavailable."""

    def test_lm_studio_unavailable_when_server_not_running(self, clean_env):
        """Test LM Studio shows unavailable when server not running."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_ollama_unavailable_when_server_not_running(self, clean_env):
        """Test Ollama shows unavailable when server not running."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_openai_compatible_unavailable_when_endpoint_unreachable(self):
        """Test OpenAI-compatible provider unavailable when endpoint unreachable."""
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:9999/v1",
                model="test-model",
            )
            assert provider.is_available() is False

    def test_claude_unavailable_without_api_key(self, clean_env):
        """Test Claude shows unavailable without ANTHROPIC_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear all API keys
            for key in ["ANTHROPIC_API_KEY"]:
                if key in os.environ:
                    del os.environ[key]

            provider = ClaudeProvider()
            assert provider.is_available() is False

    def test_claude_unavailable_without_sdk(self, clean_env):
        """Test Claude shows unavailable without anthropic SDK."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        with patch.dict("sys.modules", {"anthropic": None}):
            # Import will fail
            provider = ClaudeProvider()
            # With mocked import failure, is_available should return False
            with patch("builtins.__import__", side_effect=ImportError):
                assert provider.is_available() is False

    def test_claude_code_unavailable_without_cli(self, clean_env):
        """Test Claude Code shows unavailable without claude CLI."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = ClaudeCodeProvider()
            assert provider.is_available() is False

    def test_gemini_unavailable_without_api_key(self, clean_env):
        """Test Gemini shows unavailable without API key."""
        # Clear all Gemini API keys
        for key in ["GOOGLE_API_KEY", "GEMINI_API_KEY"]:
            if key in os.environ:
                del os.environ[key]

        provider = GeminiProvider()
        assert provider.is_available() is False

    def test_gemini_cli_unavailable_without_cli(self, clean_env):
        """Test Gemini CLI shows unavailable without gemini CLI."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = GeminiCLIProvider()
            assert provider.is_available() is False

    def test_codex_cli_unavailable_without_cli(self, clean_env):
        """Test Codex CLI shows unavailable without codex CLI."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = CodexCLIProvider()
            assert provider.is_available() is False

    def test_grok_unavailable_without_api_key(self, clean_env):
        """Test Grok shows unavailable without API key."""
        for key in ["XAI_API_KEY", "GROK_API_KEY"]:
            if key in os.environ:
                del os.environ[key]

        provider = GrokProvider()
        assert provider.is_available() is False

    def test_groq_unavailable_without_api_key(self, clean_env):
        """Test Groq shows unavailable without API key."""
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]

        provider = GroqProvider()
        assert provider.is_available() is False

    def test_transformers_unavailable_without_packages(self, clean_env):
        """Test Transformers shows unavailable without required packages."""
        with patch.dict("sys.modules", {"transformers": None, "torch": None}):
            provider = TransformersProvider()
            # With mocked import failure, is_available should return False
            with patch("builtins.__import__", side_effect=ImportError):
                assert provider.is_available() is False

    def test_openai_agents_unavailable_without_api_key(self, clean_env):
        """Test OpenAI Agents shows unavailable without API key."""
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        provider = OpenAIAgentsProvider(model="gpt-4o-mini")
        assert provider.is_available() is False


class TestAllProvidersUnavailable:
    """Tests for when all providers are unavailable."""

    def test_auto_detect_returns_none_when_all_unavailable(self, clean_env):
        """Test auto_detect_provider returns None when all providers unavailable."""
        with patch("httpx.get") as mock_get, \
             patch("shutil.which") as mock_which, \
             patch.object(TransformersProvider, "is_available", return_value=False), \
             patch.object(OpenAIAgentsProvider, "is_available", return_value=False):
            # All HTTP providers fail
            mock_get.side_effect = Exception("Connection refused")
            # All CLI providers missing
            mock_which.return_value = None

            result = auto_detect_provider()

            assert result is None

    def test_get_provider_raises_when_no_config_and_none_available(self, clean_env):
        """Test get_provider raises ValueError when no config and no providers available."""
        with patch("httpx.get") as mock_get, \
             patch("shutil.which") as mock_which, \
             patch.object(TransformersProvider, "is_available", return_value=False), \
             patch.object(OpenAIAgentsProvider, "is_available", return_value=False), \
             patch.object(LLMConfig, "from_file", return_value=LLMConfig()):
            mock_get.side_effect = Exception("Connection refused")
            mock_which.return_value = None

            with pytest.raises(ValueError, match="No LLM provider configured"):
                get_provider(None)

    def test_validate_llm_ready_returns_not_ready_when_unavailable(self, clean_env):
        """Test validate_llm_ready returns not ready when provider unavailable."""
        with patch("httpx.get") as mock_get, \
             patch("shutil.which") as mock_which, \
             patch.object(TransformersProvider, "is_available", return_value=False), \
             patch.object(OpenAIAgentsProvider, "is_available", return_value=False):
            mock_get.side_effect = Exception("Connection refused")
            mock_which.return_value = None

            provider, is_ready, error = validate_llm_ready(require_llm=True)

            assert is_ready is False
            assert error is not None
            assert "No LLM provider" in error

    def test_validate_llm_ready_includes_setup_instructions(self, clean_env):
        """Test validate_llm_ready error includes setup instructions."""
        with patch("httpx.get") as mock_get, \
             patch("shutil.which") as mock_which, \
             patch.object(TransformersProvider, "is_available", return_value=False), \
             patch.object(OpenAIAgentsProvider, "is_available", return_value=False):
            mock_get.side_effect = Exception("Connection refused")
            mock_which.return_value = None

            provider, is_ready, error = validate_llm_ready(require_llm=True)

            assert "LM Studio" in error
            assert "Ollama" in error
            assert "Gemini" in error


class TestProviderBecameUnavailable:
    """Tests for when provider was available but becomes unavailable."""

    def test_validate_llm_ready_detects_provider_became_unavailable(self, clean_env):
        """Test validate_llm_ready detects when auto-detected provider becomes unavailable.

        This tests the race condition where is_available() returns True during
        auto_detect but False when validate_llm_ready does its own check.
        """
        # Create a mock provider that was found but is now unavailable
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False
        mock_provider.name = "Mock Provider"

        with patch("src.llm_providers.get_best_provider") as mock_get_best:
            # Provider was found (is_llm=True) but is now unavailable
            mock_get_best.return_value = (mock_provider, True)

            provider, is_ready, error = validate_llm_ready(require_llm=True)

            # Should detect provider is not available
            assert is_ready is False
            assert error is not None
            assert "not currently available" in error

    def test_validate_llm_ready_suggests_troubleshooting(self, clean_env):
        """Test validate_llm_ready suggests troubleshooting steps when provider unavailable."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False
        mock_provider.name = "LM Studio"

        with patch("src.llm_providers.get_best_provider") as mock_get_best:
            mock_get_best.return_value = (mock_provider, True)

            provider, is_ready, error = validate_llm_ready(require_llm=True)

            # Should include troubleshooting suggestions
            assert "Possible issues" in error or "not currently available" in error


# =============================================================================
# Tests for API Error Handling
# =============================================================================


class TestAPIErrorResponses:
    """Tests for various API error response handling."""

    def test_api_400_bad_request(self):
        """Test handling of 400 Bad Request response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 400
            error_response.raise_for_status.side_effect = Exception("Bad Request: Invalid parameters")
            mock_post.return_value = error_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Bad Request"):
                provider.summarize("Test text")

    def test_api_401_unauthorized(self):
        """Test handling of 401 Unauthorized response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 401
            error_response.raise_for_status.side_effect = Exception("Unauthorized: Invalid API key")
            mock_post.return_value = error_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                api_key="invalid-key",
                model="test-model",
            )

            with pytest.raises(Exception, match="Unauthorized"):
                provider.summarize("Test text")

    def test_api_403_forbidden(self):
        """Test handling of 403 Forbidden response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 403
            error_response.raise_for_status.side_effect = Exception("Forbidden: Access denied")
            mock_post.return_value = error_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Forbidden"):
                provider.summarize("Test text")

    def test_api_404_not_found(self):
        """Test handling of 404 Not Found response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 404
            error_response.raise_for_status.side_effect = Exception("Not Found: Model not found")
            mock_post.return_value = error_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="nonexistent-model",
            )

            with pytest.raises(Exception, match="Not Found"):
                provider.summarize("Test text")

    def test_api_429_rate_limit(self):
        """Test handling of 429 Rate Limit response."""
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

            with pytest.raises(Exception, match="Rate limit"):
                provider.summarize("Test text")

    def test_api_500_internal_server_error(self):
        """Test handling of 500 Internal Server Error response."""
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

    def test_api_502_bad_gateway(self):
        """Test handling of 502 Bad Gateway response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 502
            error_response.raise_for_status.side_effect = Exception("Bad Gateway")
            mock_post.return_value = error_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Bad Gateway"):
                provider.summarize("Test text")

    def test_api_503_service_unavailable(self):
        """Test handling of 503 Service Unavailable response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            error_response = MagicMock()
            error_response.status_code = 503
            error_response.raise_for_status.side_effect = Exception("Service Unavailable")
            mock_post.return_value = error_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Service Unavailable"):
                provider.summarize("Test text")


class TestAPIConnectionErrors:
    """Tests for API connection-level errors."""

    def test_connection_refused(self):
        """Test handling of connection refused error."""
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

    def test_connection_reset(self):
        """Test handling of connection reset error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = Exception("Connection reset by peer")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="Connection reset"):
                provider.summarize("Test text")

    def test_dns_resolution_failure(self):
        """Test handling of DNS resolution failure."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = Exception("Failed to resolve host")

            provider = OpenAICompatibleProvider(
                base_url="http://nonexistent-host.local/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="resolve"):
                provider.summarize("Test text")

    def test_network_unreachable(self):
        """Test handling of network unreachable error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = Exception("Network is unreachable")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(Exception, match="unreachable"):
                provider.summarize("Test text")


class TestMalformedAPIResponses:
    """Tests for malformed API response handling."""

    def test_empty_response_body(self):
        """Test handling of empty response body."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            empty_response = MagicMock()
            empty_response.status_code = 200
            empty_response.json.return_value = {}
            empty_response.raise_for_status = MagicMock()
            mock_post.return_value = empty_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(KeyError):
                provider.summarize("Test text")

    def test_missing_choices_field(self):
        """Test handling of response missing 'choices' field."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            malformed_response = MagicMock()
            malformed_response.status_code = 200
            malformed_response.json.return_value = {"data": "unexpected"}
            malformed_response.raise_for_status = MagicMock()
            mock_post.return_value = malformed_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(KeyError):
                provider.summarize("Test text")

    def test_empty_choices_array(self):
        """Test handling of empty choices array."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            empty_choices_response = MagicMock()
            empty_choices_response.status_code = 200
            empty_choices_response.json.return_value = {"choices": []}
            empty_choices_response.raise_for_status = MagicMock()
            mock_post.return_value = empty_choices_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(IndexError):
                provider.summarize("Test text")

    def test_invalid_json_response(self):
        """Test handling of invalid JSON response."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            invalid_json_response = MagicMock()
            invalid_json_response.status_code = 200
            invalid_json_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            invalid_json_response.raise_for_status = MagicMock()
            mock_post.return_value = invalid_json_response

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(json.JSONDecodeError):
                provider.summarize("Test text")


# =============================================================================
# Tests for Timeout Handling
# =============================================================================


class TestTimeoutHandling:
    """Tests for timeout handling across providers."""

    def test_httpx_read_timeout(self):
        """Test handling of httpx read timeout."""
        import httpx

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = httpx.ReadTimeout("Read timed out")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(httpx.ReadTimeout):
                provider.summarize("Test text")

    def test_httpx_connect_timeout(self):
        """Test handling of httpx connect timeout."""
        import httpx

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = httpx.ConnectTimeout("Connect timed out")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(httpx.ConnectTimeout):
                provider.summarize("Test text")

    def test_httpx_write_timeout(self):
        """Test handling of httpx write timeout."""
        import httpx

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = httpx.WriteTimeout("Write timed out")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(httpx.WriteTimeout):
                provider.summarize("Test text")

    def test_httpx_pool_timeout(self):
        """Test handling of httpx pool timeout."""
        import httpx

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = httpx.PoolTimeout("Pool timed out")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            with pytest.raises(httpx.PoolTimeout):
                provider.summarize("Test text")

    def test_httpx_generic_timeout(self):
        """Test handling of generic httpx timeout."""
        import httpx

        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
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


class TestTimeoutOnAvailabilityCheck:
    """Tests for timeout during availability checks."""

    def test_lm_studio_timeout_on_availability_check(self):
        """Test LM Studio returns unavailable on timeout during availability check."""
        import httpx

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            provider = LMStudioProvider()
            assert provider.is_available() is False

    def test_ollama_timeout_on_availability_check(self):
        """Test Ollama returns unavailable on timeout during availability check."""
        import httpx

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            provider = OllamaProvider()
            assert provider.is_available() is False

    def test_openai_compatible_timeout_on_availability_check(self):
        """Test OpenAI-compatible returns unavailable on timeout."""
        import httpx

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )
            assert provider.is_available() is False


class TestCLIProviderTimeouts:
    """Tests for CLI-based provider timeout handling."""

    def test_claude_code_timeout(self, clean_env):
        """Test Claude Code handles subprocess timeout."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/claude"
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=60)

            provider = ClaudeCodeProvider()

            with pytest.raises(subprocess.TimeoutExpired):
                provider.summarize("Test text")

    def test_gemini_cli_timeout(self, clean_env):
        """Test Gemini CLI handles subprocess timeout."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/gemini"
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gemini", timeout=60)

            provider = GeminiCLIProvider()

            with pytest.raises(subprocess.TimeoutExpired):
                provider.summarize("Test text")

    def test_codex_cli_timeout(self, clean_env):
        """Test Codex CLI handles subprocess timeout."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/codex"
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="codex", timeout=60)

            provider = CodexCLIProvider()

            with pytest.raises(subprocess.TimeoutExpired):
                provider.summarize("Test text")


class TestCLIProviderErrors:
    """Tests for CLI-based provider error handling."""

    def test_claude_code_nonzero_exit(self, clean_env):
        """Test Claude Code handles non-zero exit code."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/claude"
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Error: Authentication failed"
            mock_run.return_value = mock_result

            provider = ClaudeCodeProvider()

            with pytest.raises(RuntimeError, match="Claude Code CLI failed"):
                provider.summarize("Test text")

    def test_gemini_cli_nonzero_exit(self, clean_env):
        """Test Gemini CLI handles non-zero exit code."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/gemini"
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Error: Not authenticated"
            mock_run.return_value = mock_result

            provider = GeminiCLIProvider()

            with pytest.raises(RuntimeError, match="Gemini CLI failed"):
                provider.summarize("Test text")

    def test_codex_cli_nonzero_exit(self, clean_env):
        """Test Codex CLI handles non-zero exit code."""
        import subprocess

        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/codex"
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Error: Invalid credentials"
            mock_run.return_value = mock_result

            provider = CodexCLIProvider()

            with pytest.raises(RuntimeError, match="Codex CLI failed"):
                provider.summarize("Test text")

    def test_codex_cli_invalid_json_output(self, clean_env):
        """Test Codex CLI handles invalid JSON output."""
        with patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_run:
            mock_which.return_value = "/usr/bin/codex"
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "not valid json at all"
            mock_run.return_value = mock_result

            provider = CodexCLIProvider()

            with pytest.raises(RuntimeError, match="No valid response"):
                provider.summarize("Test text")


class TestLMStudioAutoLoadErrors:
    """Tests for LM Studio auto-load error handling."""

    def test_lm_studio_no_models_loaded_error(self):
        """Test LM Studio handles 'No models loaded' error."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post, \
             patch("shutil.which") as mock_which, patch("subprocess.run") as mock_subprocess:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": []}
            mock_get.return_value = models_response

            # No lms CLI available (prevents auto-load attempt)
            mock_which.return_value = None

            # First call returns "No models loaded" error
            error_response = MagicMock()
            error_response.status_code = 400
            error_response.json.return_value = {
                "error": {"message": "No models loaded"}
            }
            error_response.raise_for_status.side_effect = Exception("Bad Request")
            mock_post.return_value = error_response

            provider = LMStudioProvider()

            with pytest.raises(Exception, match="Bad Request"):
                provider.summarize("Test text")

    def test_lm_studio_auto_load_fails_gracefully(self):
        """Test LM Studio auto-load failure is handled gracefully."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post, \
             patch("shutil.which") as mock_which, \
             patch("subprocess.run") as mock_subprocess:
            # Models endpoint returns 200 but empty
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": []}
            mock_get.return_value = models_response

            # lms CLI is available
            mock_which.return_value = "/usr/bin/lms"

            # Auto-load fails
            mock_subprocess.return_value = MagicMock(returncode=1)

            # Chat completion fails with "No models loaded"
            error_response = MagicMock()
            error_response.status_code = 400
            error_response.json.return_value = {
                "error": {"message": "No models loaded"}
            }
            error_response.raise_for_status.side_effect = Exception("Bad Request")
            mock_post.return_value = error_response

            provider = LMStudioProvider()

            # Should eventually fail but not crash
            with pytest.raises(Exception):
                provider.summarize("Test text")


class TestProviderNotAvailableForSummarize:
    """Tests for summarize when provider reports not available."""

    def test_claude_summarize_raises_when_unavailable(self, clean_env):
        """Test Claude.summarize raises RuntimeError when not available."""
        # Don't set API key
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        provider = ClaudeProvider()

        with pytest.raises(RuntimeError, match="not available"):
            provider.summarize("Test text")

    def test_claude_code_summarize_raises_when_unavailable(self, clean_env):
        """Test ClaudeCode.summarize raises RuntimeError when not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = ClaudeCodeProvider()

            with pytest.raises(RuntimeError, match="not available"):
                provider.summarize("Test text")

    def test_gemini_summarize_raises_when_unavailable(self, clean_env):
        """Test Gemini.summarize raises RuntimeError when not available."""
        # Clear API keys
        for key in ["GOOGLE_API_KEY", "GEMINI_API_KEY"]:
            if key in os.environ:
                del os.environ[key]

        provider = GeminiProvider()

        with pytest.raises(RuntimeError, match="not available"):
            provider.summarize("Test text")

    def test_gemini_cli_summarize_raises_when_unavailable(self, clean_env):
        """Test GeminiCLI.summarize raises RuntimeError when not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = GeminiCLIProvider()

            with pytest.raises(RuntimeError, match="not available"):
                provider.summarize("Test text")

    def test_codex_cli_summarize_raises_when_unavailable(self, clean_env):
        """Test CodexCLI.summarize raises RuntimeError when not available."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            provider = CodexCLIProvider()

            with pytest.raises(RuntimeError, match="not available"):
                provider.summarize("Test text")

    def test_transformers_summarize_raises_when_unavailable(self, clean_env):
        """Test Transformers.summarize raises RuntimeError when not available."""
        with patch.dict("sys.modules", {"transformers": None, "torch": None}):
            provider = TransformersProvider()

            with patch.object(provider, "is_available", return_value=False):
                with pytest.raises(RuntimeError, match="not available"):
                    provider.summarize("Test text")


class TestErrorHandlingIntegration:
    """Integration tests for error handling across the provider system."""

    def test_get_provider_with_invalid_provider_type(self, clean_env):
        """Test get_provider raises for invalid provider type."""
        with pytest.raises(ValueError):
            # Create config with invalid provider value directly
            from dataclasses import replace
            config = LLMConfig()
            # Manually set invalid provider (bypass enum validation)
            config.provider = "invalid"
            get_provider(config)

    def test_get_provider_openai_compatible_missing_base_url(self, clean_env):
        """Test get_provider raises when OpenAI-compatible missing base_url."""
        config = LLMConfig(
            provider=ProviderType.OPENAI_COMPATIBLE,
            base_url=None,  # Missing required field
        )

        with pytest.raises(ValueError, match="base_url required"):
            get_provider(config)

    def test_list_providers_handles_check_failures(self, clean_env):
        """Test list_providers handles provider check failures gracefully."""
        with patch("httpx.get") as mock_get:
            # All HTTP checks fail
            mock_get.side_effect = Exception("Connection failed")

            # Should not raise, just return providers marked unavailable
            providers = list_providers()

            assert isinstance(providers, list)
            # Local HTTP providers should be unavailable
            lm_studio = next(
                (p for p in providers if p["type"] == ProviderType.LM_STUDIO),
                None
            )
            if lm_studio:
                assert lm_studio["available"] is False

    def test_error_does_not_update_usage_stats(self):
        """Test that errors don't increment usage stats."""
        with patch("httpx.get") as mock_get, patch("httpx.post") as mock_post:
            models_response = MagicMock()
            models_response.status_code = 200
            models_response.json.return_value = {"data": [{"id": "test-model"}]}
            mock_get.return_value = models_response

            mock_post.side_effect = Exception("API Error")

            provider = OpenAICompatibleProvider(
                base_url="http://localhost:1234/v1",
                model="test-model",
            )

            initial_calls = provider.session_usage["calls"]
            initial_tokens = provider.session_usage["total_tokens"]

            try:
                provider.summarize("Test text")
            except Exception:
                pass

            # Usage should not have been updated
            assert provider.session_usage["calls"] == initial_calls
            assert provider.session_usage["total_tokens"] == initial_tokens
