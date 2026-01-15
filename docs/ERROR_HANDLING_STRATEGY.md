# Error Handling Strategy

This document describes the standardized error handling approach implemented across all LLM-dependent features in the RSS Summarizer. The core philosophy is **"No Silent Failures"** - all errors and quality degradations are explicitly surfaced to users.

## Table of Contents

- [Core Principles](#core-principles)
- [Exception Hierarchy](#exception-hierarchy)
- [Module-Specific Error Handling](#module-specific-error-handling)
- [Processing Modes](#processing-modes)
- [Quality Observability](#quality-observability)
- [CLI Integration](#cli-integration)
- [Error Recovery Guide](#error-recovery-guide)
- [Best Practices for Developers](#best-practices-for-developers)

---

## Core Principles

### 1. No Silent Fallbacks

Every feature that depends on LLM processing follows these rules:

- **Never silently degrade** to a lower-quality fallback
- **Never return empty results** and pretend processing succeeded
- **Always mark processing mode** so users know what happened
- **Always surface errors** with actionable recovery hints

### 2. Fail-Fast at Startup

LLM availability is validated at startup before processing begins:

```python
from src.llm_providers import validate_provider_at_startup, LLMUnavailableError

try:
    provider = validate_provider_at_startup()
except LLMUnavailableError as e:
    print(e.setup_instructions)
    sys.exit(1)
```

### 3. Explicit Error Classes

Each module defines its own error hierarchy:

- `*Error` - Fatal errors that prevent processing
- `*DegradedError` - Quality degradation in strict mode

### 4. Quality Metadata

All results include quality metadata:

- `mode` - Processing mode used (LLM, degraded, unavailable)
- `is_degraded` - Whether quality was compromised
- `degradation_reason` - Human-readable explanation
- `llm_calls_made/failed` - Statistics for debugging

---

## Exception Hierarchy

### Base Provider Errors (llm_providers.py)

| Exception | When Raised | Contains |
|-----------|-------------|----------|
| `LLMUnavailableError` | No LLM provider available | `message`, `setup_instructions` |
| `LLMProviderError` | LLM call failed | `provider_name`, `operation`, `original_error` |

### Feature-Specific Errors

Each feature module follows the same pattern:

| Module | Fatal Error | Degraded Error |
|--------|-------------|----------------|
| `clustering.py` | `ClusteringError` | `ClusteringDegradedError` |
| `perspectives.py` | `PerspectiveError` | `PerspectiveDegradedError` |
| `signal_tagger.py` | `SignalError` | `SignalDegradedError` |
| `knowledge.py` | `KnowledgeError` | `KnowledgeDegradedError` |
| `trends.py` | `TrendsError` | `TrendsDegradedError` |
| `observability.py` | - | `QualityDegradedError` |

### Error Structure

All errors include:

```python
class FeatureError(Exception):
    def __init__(
        self,
        message: str,           # What went wrong
        operation: str,         # Which operation failed
        original_error: Exception = None,  # Root cause
        recovery_hint: str = None,  # How to fix it
    ):
        ...
```

---

## Module-Specific Error Handling

### LLM Providers (llm_providers.py)

**Startup Validation:**
```python
# Fail fast at startup with clear instructions
provider = validate_provider_at_startup()

# Or validate specific provider
provider = get_provider(config, validate=True)
```

**Runtime Errors:**
- API failures raise `LLMProviderError`
- Unavailability raises `LLMUnavailableError`
- Each provider includes `setup_instructions` property

### Story Clustering (clustering.py)

**Processing Modes:**
| Mode | Meaning |
|------|---------|
| `LLM_SIMILARITY` | Full LLM-based semantic clustering |
| `DEGRADED` | LLM failed, quality compromised |
| `UNAVAILABLE` | Cannot perform clustering |

**Behavior:**
- Requires LLM - no fallback to keyword matching
- Tracks every LLM call success/failure
- Raises `ClusteringError` if LLM unavailable
- Returns `ClusteringResult` with quality metadata

### Perspective Generation (perspectives.py)

**Processing Modes:**
| Mode | Meaning |
|------|---------|
| `LLM_GENERATED` | Full LLM-based analysis |
| `DEGRADED` | Some perspectives failed |
| `UNAVAILABLE` | Cannot generate perspectives |

**Behavior:**
- Requires LLM - no generic fallback perspectives
- Attempts all viewpoints, tracks failures individually
- Empty result raises `PerspectiveError`

### Signal Tagging (signal_tagger.py)

**Processing Modes:**
| Mode | Meaning |
|------|---------|
| `AI_DETECTED` | Full AI signal detection |
| `RULE_BASED` | Using pattern matching (explicit) |
| `DEGRADED` | AI failed, fallback not allowed |
| `UNAVAILABLE` | No detection possible |

**Behavior:**
- Can optionally fall back to rule-based detection
- **Always marks mode explicitly** - users know when using rules
- `processing_mode_message` explains what happened

### Knowledge Extraction (knowledge.py)

**Processing Modes:**
| Mode | Meaning |
|------|---------|
| `LLM_EXTRACTED` | Full LLM-based extraction |
| `PARTIAL` | Some items extracted, some failed |
| `DEGRADED` | Extraction quality compromised |
| `UNAVAILABLE` | Cannot extract knowledge |

**Extraction Status (per item):**
| Status | Meaning |
|--------|---------|
| `SUCCESS` | Extracted with high confidence |
| `LOW_CONFIDENCE` | Extracted but uncertain |
| `FAILED` | Extraction attempt failed |
| `EMPTY` | LLM returned nothing (NOT success) |

**Behavior:**
- Empty extraction is NOT treated as success
- Each item includes confidence score
- `mark_extraction_empty()` explicitly surfaces when LLM returns nothing

### Trend Detection (trends.py)

**Processing Modes:**
| Mode | Meaning |
|------|---------|
| `LLM_DETECTED` | Full LLM-based detection |
| `PARTIAL` | Some detection calls failed |
| `DEGRADED` | Detection quality compromised |
| `UNAVAILABLE` | Cannot detect trends |

**Behavior:**
- **Distinguishes "no trends found" from "detection failed"**
- `is_available` flag indicates if detection could run
- `detection_status_message` always explains what happened
- `mark_unavailable()` vs `mark_no_trends_found()` methods

---

## Processing Modes

### Mode Enums by Feature

All features use string enums for serialization compatibility:

```python
class FeatureMode(str, Enum):
    FULL = "full"           # Best quality, LLM working
    DEGRADED = "degraded"   # Reduced quality
    UNAVAILABLE = "unavailable"  # Feature cannot run
```

### Mode Determination Logic

Modes are determined based on:

1. **LLM Availability** - Is a provider configured and responding?
2. **Call Success Rate** - What percentage of LLM calls succeeded?
3. **Result Quality** - Did we get meaningful results?

Example from clustering:
```python
if result.llm_calls_failed > 0:
    failure_rate = result.llm_calls_failed / result.llm_calls_made
    if failure_rate > 0.5:
        result.mode = ClusteringMode.DEGRADED
```

---

## Quality Observability

### QualityTracker Class

Unified tracking across all features:

```python
from src.observability import QualityTracker

tracker = QualityTracker(strict_mode=False, verbose=True)

# Track results as they come in
tracker.track_clustering(clustering_result)
tracker.track_perspectives(perspective_result)
tracker.track_signals(signal_result)
tracker.track_knowledge(knowledge_result)
tracker.track_trends(trends_result)

# Get report
report = tracker.get_report()
print(report.get_verbose_report())
```

### OverallQuality Enum

Aggregate quality assessment:

| Quality | Meaning |
|---------|---------|
| `FULL_LLM` | All features using full LLM processing |
| `MOSTLY_LLM` | Most features using LLM, minor issues |
| `PARTIAL` | Mix of LLM and fallbacks |
| `DEGRADED` | Significant degradation across features |
| `UNAVAILABLE` | Most features unavailable |

### QualityReport Structure

```python
@dataclass
class QualityReport:
    features: list[FeatureStatus]
    overall_quality: OverallQuality
    timestamp: str

    # Aggregate stats
    total_llm_calls: int
    total_llm_failures: int
    features_using_llm: int
    features_degraded: int
    features_unavailable: int

    # Messages
    summary_message: str
    detailed_warnings: list[str]
```

---

## CLI Integration

### Quality Flags

| Flag | Short | Effect |
|------|-------|--------|
| `--verbose` | `-v` | Show detailed quality reports |
| `--strict` | `-s` | Exit code 1 on any degradation |

### Example Usage

```bash
# Normal update
rss update

# With quality details
rss update --verbose

# CI mode - fail on degradation
rss update --strict

# Both flags
rss update -v -s
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, or degradation in non-strict mode |
| 1 | Strict mode with degradation, or fatal error |

### Quality Output

**Non-verbose mode (degradation detected):**
```
Quality Warning: Quality: DEGRADED (2 affected)
Use --verbose for details
```

**Verbose mode:**
```
============================================================
FEATURE QUALITY REPORT
============================================================

OK Clustering: OK
   Mode: llm_similarity
   Quality: Full LLM-based semantic clustering
   LLM Calls: 15 (0 failed)

DEGRADED Signal Tagging: DEGRADED
   Mode: rule_based
   Quality: RULE-BASED: AI provider not available
    AI signal detection provides more accurate results.

------------------------------------------------------------
OVERALL SUMMARY
------------------------------------------------------------
Overall Quality: PARTIAL
Features Using LLM: 4/5
Features Degraded: 1
Features Unavailable: 0
Total LLM Calls: 45
Total LLM Failures: 3
============================================================
```

---

## Error Recovery Guide

### LLM Provider Unavailable

**Symptoms:**
- `LLMUnavailableError` at startup
- Features return `UNAVAILABLE` mode

**Solutions:**
1. Check provider is running (LM Studio, Ollama)
2. Verify API keys (OpenAI, Claude)
3. Run `rss providers` to see status
4. Run `rss setup` to reconfigure

### High LLM Failure Rate

**Symptoms:**
- Features return `DEGRADED` mode
- `llm_calls_failed` > 50% of `llm_calls_made`

**Solutions:**
1. Check provider health and rate limits
2. Reduce batch size or add delays
3. Try different model or provider
4. Check network connectivity

### Empty Results

**Symptoms:**
- `ExtractionStatus.EMPTY` on knowledge items
- `mark_extraction_empty()` called

**Solutions:**
1. Article may lack extractable content
2. Prompt may need adjustment
3. Model may need different configuration
4. Try different knowledge categories

---

## Best Practices for Developers

### 1. Always Check Availability First

```python
from src.clustering import validate_clustering_available

available, error = validate_clustering_available()
if not available:
    # Handle gracefully - don't silently skip
    logger.warning(f"Clustering unavailable: {error}")
    return create_unavailable_result(error)
```

### 2. Track All LLM Calls

```python
result.llm_calls_made += 1
try:
    response = provider.summarize(prompt)
except LLMProviderError as e:
    result.llm_calls_failed += 1
    result.add_warning(f"LLM call failed: {e}")
```

### 3. Never Return Silent Failures

```python
# BAD - Silent failure
if not response:
    return []

# GOOD - Explicit failure
if not response:
    result.add_warning("Empty response from LLM")
    result.mark_degraded("LLM returned no content")
    return result
```

### 4. Use Strict Mode in Tests

```python
def test_clustering_quality():
    result = cluster_articles(articles, strict_mode=True)
    # Will raise ClusteringDegradedError if any issues
    assert result.mode == ClusteringMode.LLM_SIMILARITY
```

### 5. Provide Recovery Hints

```python
raise FeatureError(
    message="Cannot extract knowledge",
    operation="extract_knowledge",
    original_error=e,
    recovery_hint="Check your LLM provider is running. Run 'rss providers' to diagnose."
)
```

### 6. Use Quality Tracker for Aggregation

```python
tracker = QualityTracker(strict_mode=args.strict, verbose=args.verbose)

# Track all features
tracker.track_clustering(cluster_result)
tracker.track_perspectives(perspective_result)
# ...

# Check overall health
report = tracker.get_report()
if not report.is_healthy:
    # Log or alert
    pass
```

---

## Summary

The error handling strategy ensures:

1. **Transparency** - Users always know what quality they're getting
2. **Actionability** - Errors include recovery hints
3. **Observability** - Quality metrics are tracked and surfaced
4. **Flexibility** - Strict mode for CI, lenient mode for interactive use
5. **Consistency** - Same patterns across all features

Every LLM-dependent feature follows these principles, making the system trustworthy and debuggable.
