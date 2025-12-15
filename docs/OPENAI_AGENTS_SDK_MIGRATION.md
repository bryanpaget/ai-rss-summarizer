# Migration Plan: OpenAI Basic SDK → Agents SDK

## Overview
Replace the basic OpenAI SDK provider with the OpenAI Agents SDK for enhanced capabilities that align with our complex feature set (story clustering, signal tagging, perspective synthesis, etc.).

## Current State
- `ProviderType.OPENAI` exists
- `OpenAICompatibleProvider` handles OpenAI API calls
- Uses basic `openai` package for simple chat completions

## Target State
- `ProviderType.OPENAI` unchanged (config compatibility)
- New `OpenAIAgentsProvider` class using Agents SDK
- Supports both sync and async contexts
- Tracks token usage
- Warns when newer SDK versions are available

## Migration Steps

### Step 1: Dependencies (pyproject.toml)
Add to optional dependencies:
```toml
openai-agents = ["openai-agents~=0.6.0", "nest-asyncio~=1.6.0"]
```
Uses `~=0.6.0` (not `>=`) to pin to 0.6.x versions only. Prevents auto-breaking on major updates.
`nest-asyncio` allows the provider to work in async contexts (web servers, notebooks).

### Step 2: ProviderType Enum
Keep `OPENAI = "openai"` unchanged. Existing configs continue working.

### Step 3: Keep OpenAICompatibleProvider
Do NOT delete - still used for `OPENAI_COMPATIBLE`, `LM_STUDIO`, `GROK`.

### Step 4: Create OpenAIAgentsProvider Class

Key requirements:
- Pass model to Agent constructor (required by SDK)
- Detect sync vs async context and call appropriate Runner method
- Track token usage
- Let errors propagate to user (no silent fallbacks)

```python
class OpenAIAgentsProvider(LLMProvider):
    """OpenAI provider using the Agents SDK."""

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
            from agents import Agent, Runner
            return bool(os.getenv("OPENAI_API_KEY"))
        except ImportError:
            return False

    def summarize(self, text: str, max_length: int = 150) -> str:
        from agents import Agent, Runner
        import asyncio

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
            self._record_usage(text, summary, self._model)

        return summary
```

### Step 5: Update get_provider()
```python
elif config.provider == ProviderType.OPENAI:
    return OpenAIAgentsProvider(model=config.model)
```
Model is required. User must specify model in config.

### Step 6: Update list_providers()
```python
{
    "type": ProviderType.OPENAI,
    "name": "OpenAI Agents",
    "available": OpenAIAgentsProvider(model="gpt-4o").is_available(),
    "description": "OpenAI Agents SDK (requires API key)",
},
```

### Step 7: Update auto_detect_provider()
The `auto_detect_provider()` function returns an OpenAI provider when API key is present. Update to return the new class:
```python
if os.getenv("OPENAI_API_KEY"):
    return OpenAIAgentsProvider(model="gpt-4o-mini")
```

### Step 8: Add Version Detection Command
Add `rss check-updates` command that checks PyPI for newer SDK versions. This is opt-in, not automatic on startup:
```python
def check_agents_sdk_version():
    """Warn if newer openai-agents version available."""
    import importlib.metadata
    import urllib.request
    import json

    try:
        installed = importlib.metadata.version("openai-agents")
        with urllib.request.urlopen("https://pypi.org/pypi/openai-agents/json") as resp:
            latest = json.loads(resp.read())["info"]["version"]

        if not latest.startswith("0.6"):
            print(f"Warning: openai-agents {latest} available but only 0.6.x tested.")
            print("Contact developer to update support.")
        else:
            print(f"openai-agents {installed} is current.")
    except Exception as e:
        print(f"Could not check for updates: {e}")
```

### Step 9: Testing
1. Syntax check: `python -c "from src import llm_providers"`
2. Provider list: `rss providers` shows OpenAI Agents entry
3. Config compatibility: Existing `"provider": "openai"` configs work
4. Actual summarization test: Call summarize() with real text, verify output
5. Usage tracking: Verify token counts are recorded
6. Async context: Test from both sync script and async context

## Risks and Mitigations

### Risk 1: Breaking existing users
Mitigation: Keep same enum value, same config format

### Risk 2: openai-agents not installed
Mitigation: is_available() checks for import, returns False if missing

### Risk 3: SDK breaking changes
Mitigation: Pin to ~=0.6.0, detect newer versions and warn user

## Rollback Plan
1. Revert get_provider() to return OpenAICompatibleProvider
2. Revert list_providers() description
3. No config changes needed (enum unchanged)
