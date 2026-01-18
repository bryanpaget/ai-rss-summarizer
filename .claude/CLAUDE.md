## ✓ INTELLIGENCE BRIEFING - IMPLEMENTED

**`rss report` now outputs the intelligence briefing format from REPORT_DESIGN_SPEC.md**

The 6 sections are implemented in `src/report.py:_show_final_report()`:
1. **Top Priority** - 1-3 must-read items with key insight, signal, "what we know" from KB
2. **Your Interest Areas** - Dynamic sections based on user's tracked topics (via `rss context watch`)
3. **Discovered Connections** - Cross-source synthesis showing relationships
4. **Knowledge Graph Updates** - New facts and insights with examples
5. **Quick Scan** - Remaining items sorted by relevance score
6. **Session Stats** - Articles processed, feeds, time, insights, facts, connections, stories

---

## CRITICAL: Project Portability Requirement

**This project MUST work on ANY computer without relying on user-specific paths like ~/.claude/**

The gateway script `scripts/safe-model-load.sh` MUST exist IN THIS PROJECT.
- Location: `<project>/scripts/safe-model-load.sh`
- `src/gateway.py` looks for the project copy ONLY - NO FALLBACKS
- If the project copy is missing, the code MUST FAIL LOUDLY
- This requirement has been communicated dozens of times - violating it is unacceptable

**Before modifying any gateway-related code:**
1. Verify `scripts/safe-model-load.sh` exists in this project
2. If missing, copy it and verify
3. Never assume ~/.claude paths will exist on other machines

## CRITICAL: No Fallbacks Policy

**Fallbacks are illegal - they hide incompetence.**

A fallback makes broken code appear to work on the developer's machine while failing everywhere else. This wastes enormous time debugging "works for me" situations.

Rules:
- NEVER add fallback paths (e.g., "try X, if missing try Y")
- Code MUST fail loudly when requirements are missing
- If something is required, its absence is an error, not a condition to handle
- The error message must explain what's missing and how to fix it

This applies especially to:
- Gateway script paths (project copy ONLY, no ~/.claude fallback)
- Configuration files
- Any resource the code needs to function

---

## CRITICAL: No Hardcoded Limits Policy

**Internal functions must NOT have hardcoded limits. The only limit is the user's `-m/--max-per-step` parameter.**

Rules:
- Query functions default to `limit=None` (no limit)
- NEVER replace one hardcoded limit with another (e.g., changing `limit=200` to `limit=10000` is WRONG)
- "No limit" means NO LIMIT, not "pick a big number"
- Only the user-facing limit parameter controls processing

Functions that follow this policy:
- `get_active_stories(limit=None)` - returns ALL active stories by default
- `get_all_stories(limit=None)` - returns ALL stories by default
- `get_insights(limit=None)` - returns ALL insights by default

When you see a hardcoded limit in a query function, the fix is to make `limit` optional (defaulting to `None`), NOT to increase the number.

---

No arbitrary limits. Process based on meaning/content, not arbitrary constraints.
- Content truncation (`[:N]`) destroys information - use semantic chunking via LLM instead
- Fixed extraction counts ("aim for N", "3-5", "5-10") contradict "extract ALL" - let content determine output
- Character-based chunking ignores semantic boundaries - LLM identifies meaningful boundaries
Semantic chunking: Send full content to LLM, ask it to identify boundaries AND return chunks directly, explain purpose (embeddings). Extract from each chunk with output determined by content (0 facts if garbage, 50 if dense).

## Local LLM Gateway Architecture (CRITICAL)

ALL local LLM requests MUST go through `src/gateway.py`. This is non-negotiable.

### Why the Gateway Exists
The safe-model-load gateway (`scripts/safe-model-load.sh` in this project) handles:
1. **Automatic model loading** - You specify request TYPE (text/embedding/vision), gateway loads correct model
2. **Queue management** - Batches requests by type to minimize model switches
3. **Race condition prevention** - Coordinates concurrent requests safely

### Rules
1. **NEVER make direct API calls to LM Studio/Ollama** - No `httpx.post(...localhost:1234...)` for text
2. **Use gateway for ALL request types** - Text, embedding, vision all go through gateway
3. **Batch by phase, not by item** - Submit ALL text requests first, then ALL embeddings
4. **Gateway handles model switching** - Don't add your own `ensure_text_model()` calls

### Correct Pattern
```python
from .gateway import get_gateway

# WRONG: Direct API call
response = httpx.post("http://localhost:1234/v1/chat/completions", ...)

# RIGHT: Gateway request
gateway = get_gateway()
response = gateway.request_text("Your prompt here")

# RIGHT: Batched requests (efficient)
results = gateway.batch_text(list_of_prompts)
embeddings = gateway.batch_embedding(list_of_texts)
```

### Pipeline Structure
The report pipeline MUST be structured in phases:
1. **Pre-embedding phase** - Embed existing stories/insights (batch embedding)
2. **LLM phase** - ALL summaries, facts, tags (batch text) - NO embedding calls here
3. **Embedding phase** - Embed new articles (batch embedding) - NO text calls here
4. **Story matching** - Uses pre-computed embeddings only

NEVER interleave text and embedding requests item-by-item. This causes excessive model switching.

### Architectural Tests (ENFORCED)

These invariants are enforced by `tests/test_pipeline_architecture.py`:

| Test | Rule | Enforcement |
|------|------|-------------|
| `test_llm_phase_no_embedding_calls` | LLM phase must have 0 embedding calls | Fails if embedding service called during `_run_llm_phase` |
| `test_llm_phase_model_switches` | LLM phase must have 0 model switches | Fails if LLM->EMBED->LLM pattern detected |
| `test_llm_calls_per_article` | 1 LLM call per article | Fails if calls != article count |

**How tests work:**
1. Mock provider and embedding service log ALL calls with caller function names
2. Run the pipeline phase
3. Parse log to detect violations
4. ALWAYS print full call log for visibility (pass or fail)

**If tests fail:**
1. Look at the CALL SEQUENCE in the output
2. Find which function made the wrong call
3. Fix that function, don't add workarounds

**Consolidated extraction:**
- `extract_all_from_article()` in knowledge.py does insights + triples in 1 LLM call
- Replaces the old pattern of 3+ separate calls per article
- If you see separate insight/triple extraction calls, that's a regression

**Trend tagging (ENFORCED):**
- `test_trend_tagging_no_new_embeddings` - Fails if trend tagging calls `embed_text()`
- Category embeddings are seeded ONCE during pre-embedding phase via `ensure_categories_initialized()`
- `analyze_article()` uses STORED article embedding via `get_embedding()`, never creates new
- If you see `embed_text()` during trend tagging, that's a violation

## CRITICAL: Extraction Architecture (BROKEN - NEEDS FIX)

**Problem: The extraction system is incomplete and inconsistent.**

### What Exists

1. **schema.py** has `CombinedExtractionResult` with:
   - `chunks: list[SemanticChunk]` - each chunk has content, insights, triples
   - `summary: str`
   - `signal_tags: list[SignalTag]`

2. **knowledge.py** has `ConsolidatedExtractionResult` (DIFFERENT!) with only:
   - `insights: list[Insight]`
   - `new_triples: list[Triple]`
   - `existing_triples: list[Triple]`
   - NO summary, NO chunks, NO headline, NO keywords

3. **report.py** line 594 references `extraction.summary` but that field doesn't exist on `ConsolidatedExtractionResult` - this code is silently broken.

4. **The CLAUDE.md itself says** (line 72): "Semantic chunking: Send full content to LLM, ask it to identify boundaries AND return chunks directly" - but the current `extract_all_from_article` prompt does NOT ask for chunks.

### What Should Happen

ONE extraction call should return:
- `summary` - 1-2 sentence description
- `headline` - rewritten title (for stories)
- `keywords` - key terms (for stories)
- `chunks` - semantically chunked content
- `insights` - per chunk
- `triples` - per chunk

Then:
- Embed the CHUNKS (not whole article)
- Story creation uses already-extracted headline/summary/keywords (NO additional LLM calls)
- Story matching uses chunk embeddings

### Why Story Matching Is Broken

1. Stories are created with LLM-generated title/description (3 LLM calls)
2. Story embedding = embed(LLM_title + LLM_description)
3. Article embedding = embed(article.title + article.content)
4. These are DIFFERENT semantic spaces - they will never match!

**Fix:** Story metadata should come from article extraction, not separate LLM calls.

### Embedding Architecture Problem

**Current behavior** (`embeddings.py:embed_text`):
1. If text > 2000 chars, chunk at sentence boundaries
2. Embed each chunk separately
3. AVERAGE the chunk embeddings into ONE vector
4. DISCARD the individual chunk embeddings

**Problem:** Averaging destroys fine-grained matching:
- Article about topics A, B, C gets averaged into mush
- Another article about topics C, D, E also averaged
- The shared topic C is diluted by the other topics
- Match score is low even though they share content

**What should happen:**
- Store EACH chunk embedding separately
- Match by finding chunks that are similar
- Articles match if ANY chunks align, not just overall average
- More aligned chunks = stronger correlation

### Current Schema (storage.py)

**Article fields:**
- id, feed_url, title, link, published, content
- summary (TEXT) - exists but not being populated correctly
- trend_tags, signal_tags (TEXT)
- story_id (TEXT)
- embedding (TEXT) - single serialized vector
- NO headline field
- NO keywords field

**Story fields:**
- id, title, description, keywords
- first_seen, last_updated, lifecycle_state
- article_ids, news_item_ids

**Schema changes needed:**
1. Add `headline TEXT` to articles table
2. Add `keywords TEXT` to articles table (JSON array)
3. Consider: chunk embeddings table (article_id, chunk_index, chunk_text, embedding)

---

## CRITICAL: Validate Changes by Running Actual Commands

**Unit tests passing does NOT mean the code works. Always run the actual user-facing command.**

After making changes to any code that affects user-facing functionality:
1. Run the actual CLI command (e.g., `rss report -m 1`) to verify it works
2. Do NOT ask the user for error messages you could get by running the command yourself
3. If the command crashes, fix it immediately before reporting "done"

Why this matters:
- Unit tests mock dependencies - they don't test real integration
- Mocked tests can pass while real code crashes (e.g., Unicode encoding issues on Windows)
- Asking the user for errors you could trivially obtain yourself wastes their time and destroys trust

**The work is NOT complete until the actual command runs successfully.**

---

## Problem Solving Principles

### Bandaids vs Root Cause
- Retry logic is a bandaid, not a fix
- "Works sometimes" is not solved
- Investigate WHY something fails before adding workarounds
- If you don't understand the root cause, you haven't fixed it

### When Something Breaks
1. Reproduce the error
2. Understand WHY it happens
3. Fix the root cause
4. Verify the fix addresses the cause
5. Don't just suppress the symptom
