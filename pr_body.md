## Summary

Complete system overhaul - a ground-up rebuild of the RSS summarizer into an intelligence briefing system. Consolidates PRs #30 and #31.

---

## Bug Fixes Since PR Creation (Jan 16-19, 2026)

### Gateway Throughput Fix (Jan 19)
**Problem:** Batch submission of 50 clusters caused queue buildup. Requests waited 195+ seconds in queue, causing timeouts before processing even started.

**Evidence from logs:**
| Metric | Early Batch | Late Batch |
|--------|-------------|------------|
| Queue time | 3,132ms | 195,351ms |
| Process time | 37,516ms | 115,639ms |
| Total | ~40s | ~310s (exceeds 300s timeout) |

**Fix:**
- Sliding window submission (MAX_IN_FLIGHT=10) prevents queue buildup
- Timeout increased to 600s for legitimate long operations
- Automatic retry on timeout (request likely never started)

**Files:** `src/report.py` (connection detection phase)

---

### Schema Validation Fix (Jan 18)
**Problem:** LLM sometimes returned triples with `null` object values, causing Pydantic validation errors.

**Error:**
```
chunks.2.triples.1.object: Input should be a valid string
```

**Fix:** Added `@model_validator` to `SemanticChunk` that filters out triples with None values before validation.

**Files:** `src/schema.py`

---

### Embedding Model Reload Fix (Jan 18)
**Problem:** "No models loaded" error in Step 4.5 (connection detection) after LLM phase.

**Root cause:** `_model_loaded` flag in `LMStudioProvider` became stale after LLM phase switched models.

**Fix:** Added gateway call at start of `_run_connection_detection()` to reload embedding model.

**Files:** `src/report.py`

---

### Previous Fixes (Jan 16)

| Bug | Symptom | Root Cause | Fix |
|-----|---------|------------|-----|
| **Summary not saved** | 3% summaries | `extract_all_from_article()` returned summary but `_run_llm_phase()` never saved it | Added `storage.update_summary()` call |
| **Signal tags not loaded** | 0% signal tags | `_row_to_article()` missing field | Added `signal_tags=row["signal_tags"]` |

---

## User-Facing Features

### Interactive Setup Wizard (`rss context setup`)
**NEW** - Tree-navigation onboarding for new users:
- **15 categories** (Technology, Science, Politics, Business, etc.)
- **30+ subjects** per category (AI & ML, Cybersecurity, Space, etc.)
- **80+ curated RSS feeds** from reputable sources
- Navigate with arrow keys, Enter to drill down, Back to go up
- Feeds **automatically added** to subscriptions (not just printed)
- Topics auto-derived from feed selections
- Final confirmation screen before committing
- `rss report --setup` forces wizard to run again

### Intelligence Briefing (`rss report`)
The main interaction loop. Produces a personalized 6-section briefing:
1. **Top Priority** - Must-read items with insights, KB context, story tracking.
2. **Your Interest Areas** - Dynamic sections based on tracked topics
3. **Discovered Connections** - Cross-source synthesis
4. **Knowledge Graph Updates** - New facts/insights extracted
5. **Quick Scan** - Remaining items by relevance
6. **Session Stats** - Processing metrics

**Progress Tracking:**
- Live elapsed time per step
- Per-article timing with ETA in LLM phase
- Total pipeline time shown at completion

**Large Backlog Handling:**
- Auto-warning when 20+ articles need processing
- Suggests `rss report -m 5` for incremental processing
- Help reminder for more options

**Flags:**
- `--setup` - Force setup wizard to run
- `--limit N` / `-n N` - Limit items per step
- `--reprocess` - Re-analyze already-summarized articles

### Feed Discovery (`rss discover`)
Find new RSS feeds based on your interests using web search.

### Constitution System (`rss constitution`)
Customize how the AI analyzes content:
- `rss constitution` - View current guidelines
- `rss constitution-create` - Create from template
- Define what to prioritize, what to be skeptical of, what to watch for
- Boundary enforcement prevents constitution pollution in outputs

### User Context Management (`rss context`)
Tell the system about yourself for personalization:
- `rss context setup` - Interactive tree-navigation wizard
- `rss context watch "Topic"` - Quick-add a topic
- `rss context unwatch "Topic"` - Remove a topic
- `rss context add project "AI Safety Research"` - Track projects
- `rss context add interest "Climate Tech"` - Track interests
- `rss context list` - View your profile

### Story Clustering (`rss stories`)
Group related articles into developing stories:
- `rss stories list` - View story clusters with lifecycle states
- `rss stories stats` - Embedding coverage
- `rss stories fix-titles` - Regenerate bad LLM titles
- `rss stories backfill-embeddings` - Fix stories missing vectors
- Lifecycle states: emerging -> developing -> peaked -> declining -> resolved

### Knowledge Graph
Build and explore a knowledge graph from extracted facts:
- `rss graph "Entity Name"` - Explore connections around an entity
- `rss graph-path "Entity A" "Entity B"` - Find relationship paths
- `rss graph-stats` - Graph statistics
- `rss extract-knowledge` - Extract insights from articles
- `rss contradictions` - Find conflicting information
- `rss knowledge-stats` - Knowledge base metrics
- `rss query "question"` - Natural language KB queries
- **Proper noun constraint** - Only named entities (people, companies, places), not generic nouns

### Perspectives Synthesis (`rss perspectives`)
Multiple viewpoints on stories.

### Signal Tagging (`rss tag`)
Content classification and filtering.

### Scheduled Fetches (`rss schedule`)
Background automation for fetching articles (not reports).

---

## Architecture

### Gateway System (`src/gateway.py`)
All local LLM requests route through gateway:
- Automatic model loading by type (text/embedding/vision)
- Queue management for request batching
- Race condition prevention
- Proper cleanup on exit (clear queue + unload models)
- Uses project-local `scripts/safe-model-load.sh`

### Sliding Window Submission (NEW)
Connection detection now uses sliding window to prevent queue saturation:
- MAX_IN_FLIGHT = 10 requests at a time
- As responses return, new requests submitted
- Prevents queue times from exceeding processing times
- 600s timeout with automatic retry

### Embedding-First Pipeline
- Shared `EmbeddingService` across all phases
- Pre-embedding phase BEFORE LLM analysis
- Semantic cards (distilled content) embedded, not raw text
- FAISS vector index for similarity search
- Embedding-based trend categorization (not keyword matching)

### Pipeline Phase Isolation (ENFORCED BY TESTS)

The report pipeline enforces strict phase isolation to prevent model switching:

| Phase | Model Type | Operations |
|-------|------------|------------|
| Pre-embedding | EMBED | Embed existing stories/insights |
| LLM Analysis | TEXT | 1 consolidated call per article (insights + triples) |
| Article Embedding | EMBED | Embed new articles, trend tagging |
| Connection Detection | TEXT | Sliding window cluster analysis |
| Story Matching | NONE | Uses pre-computed embeddings only |

**Architectural tests (`tests/test_pipeline_architecture.py`) enforce:**
- LLM phase must have **0 embedding calls**
- LLM phase must have **0 model switches**
- Exactly **1 LLM call per article** (consolidated extraction)

### No Hardcoded Limits Policy

Internal query functions default to `limit=None` meaning **no limit**:
- `get_active_stories()` - returns ALL active stories
- `get_all_stories()` - returns ALL stories
- `get_insights()` - returns ALL insights

The only limit is the user-configurable `-m/--max-per-step` parameter.

### Self-Healing Pipeline
1. Verification - detect gaps from interrupted runs
2. Pre-embedding - stories/insights get vectors
3. LLM Analysis - summaries, facts, signal tags
4. Article Embedding - semantic cards
5. Connection Detection - **sliding window to prevent saturation**
6. Story Matching - vector similarity

### Content Filtering (`src/content_filter.py`)
- Spam detection and filtering
- Old spam cleanup
- Configurable thresholds

---

## Configuration

- `config/feeds.txt` - RSS feed URLs (auto-managed by setup wizard)
- `config/model_config.json` - Model settings
- `config/schedule.json` - Scheduled fetch times
- `config/constitution.md` - Analysis guidelines
- `config/user_context.json` - User profile and interests

---

## Testing

- **2615+ tests** in test suite
- Mock providers for isolated testing
- **Architectural tests** enforce pipeline phase isolation
- Call logging validates no model switching within phases

---

## Installation

```bash
# Unix
./install.sh

# Windows
install.bat
```

---

Consolidates work from closed PRs #30 (testing) and #31 (embedding architecture).

Generated with [Claude Code](https://claude.com/claude-code)
