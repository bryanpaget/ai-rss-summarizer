# STOP - READ FIRST

**Before doing ANYTHING in this project, read `.claude/BLOCKING_PRIORITY.md`**

This project is blocked on organization and documentation. No code changes until the system is fully mapped and documented. Every "fix" applied without understanding the full system makes things worse.

---

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

## Local Codebase Explorer Tool

**Location:** `scripts/local-codebase-explorer.py` (CANONICAL - this project)
**Global copy:** `~/.claude/scripts/local-codebase-explorer.py` (for other projects)

This tool documents codebases by extracting functions/classes and describing each with LLM.

**Usage:**
```bash
python scripts/local-codebase-explorer.py . -o docs/CODEBASE.md -l 50
```

**Options:**
- `-o FILE` - Output markdown documentation
- `-f` - Force reprocess (ignore cache)
- `-w N` - Concurrent workers (default 10)
- `-v` - Verbose per-item progress
- `-l N` - Limit to first N files (incremental testing)

**Outputs:**
- `.cache/codebase_docs.json` - Hash cache (skip unchanged)
- `.cache/llm_responses.log` - Full prompt/response log (debugging)

**Sync rule:** After modifying, copy to global:
```bash
cp scripts/local-codebase-explorer.py ~/.claude/scripts/
```

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
1. **Text requests go through gateway** - Use `gateway.request_text()` or `gateway.submit_text()`
2. **Single embeddings go through gateway** - Use `gateway.request_embedding()` for model loading
3. **Batch embeddings use DIRECT API** - See "CRITICAL: Embedding Batching" section below
4. **Batch by phase, not by item** - Submit ALL text requests first, then ALL embeddings
5. **Gateway handles model switching** - Don't add your own `ensure_text_model()` calls

### Correct Pattern
```python
from .gateway import get_gateway

# TEXT: Always use gateway
gateway = get_gateway()
response = gateway.request_text("Your prompt here")

# EMBEDDING (single): Use gateway to trigger model loading
embedding = gateway.request_embedding(text)

# EMBEDDING (batch): Use EmbeddingService.embed_batch() which calls LM Studio API directly
# This is the ONLY exception to "use gateway for everything"
from .embeddings import EmbeddingService
service = EmbeddingService()
results = service.embed_batch(list_of_texts)  # ONE API call for ALL texts
```

## CRITICAL: Embedding Batching Architecture

**Embeddings are the #1 bottleneck. This section explains why and how to fix it.**

### The Problem (DO NOT REPEAT THIS MISTAKE)

Gateway subprocess calls have ~7 seconds overhead PER request:
1. Python writes prompt to temp file
2. Subprocess spawns bash script
3. Bash script reads file, makes API call, writes response
4. Python polls for response file, reads it

If you call `gateway.request_embedding()` 10 times, that's 70+ seconds of overhead for embeddings that take milliseconds each.

**Symptoms of this bug:**
- LM Studio shows "ready" 99% of the time during embedding phase
- Embeddings complete instantly (one frame) then nothing for 7+ seconds
- Batch of 10 embeddings takes 70+ seconds instead of <3 seconds

### The Solution: TRUE Server-Side Batching

The OpenAI-compatible `/v1/embeddings` API accepts an ARRAY of texts:
```json
{"input": ["text1", "text2", "text3", ...], "model": "model-name"}
```

And returns ALL embeddings in ONE response. This is TRUE batching.

**Implementation** (`embedding_providers.py:LMStudioProvider.embed_batch`):
1. Makes ONE direct `httpx.post()` call to LM Studio with `input` as array
2. Gets ALL embeddings back in one response
3. No subprocess overhead, no file-based IPC

**Performance:**
- Gateway approach: ~7 seconds per embedding (subprocess overhead)
- Direct batch API: ~260ms per embedding (10 in 2.6 seconds)
- That's a **27x improvement**

### Rules for Embedding Code

1. **Use `embedding_service.embed_batch(texts)`** - This calls the API directly with array input
2. **NEVER loop with `embed_text()` one at a time** - Each call has 7s gateway overhead
3. **Model loading**: Call `gateway.request_embedding("trigger")` ONCE before batch operations to ensure embedding model is loaded
4. **The pipeline's pre-embedding phase handles model loading** - `ensure_categories_initialized()` makes a gateway call

### Where Batch Embedding is Used

- `_run_pre_embedding_phase()` - insights and stories (Step 2)
- `_run_embedding_phase()` - articles (Step 4)
- `_run_connection_detection()` - new insights (Step 4.5)

**If you see a loop calling `embed_text()` individually, that's a bug. Fix it to use `embed_batch()`.**

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

## ✓ Extraction Architecture (IMPLEMENTED)

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

## IMPLEMENTATION PLAN: Process-Once Architecture

**Status: COMPLETE (validated 2026-01-17)**

### Phase 1: Fix Extraction (ONE LLM call gives everything)
- [x] Add `summary`, `headline`, `keywords` to `CombinedExtractionOutput` dataclass
- [x] Modify extraction prompt to return all fields in one call
- [x] Add `headline TEXT`, `keywords TEXT` columns to articles table (schema v2)
- [x] Update `_run_llm_phase` to save headline/keywords to storage
- [x] Test: verified extraction returns all fields

### Phase 2: Fix Story Creation (ZERO LLM calls)
- [x] Rewrite `create_new_story` to use article's extracted data
- [x] Remove the 3 LLM prompt functions (all removed)
- [x] Test: verified 0 LLM calls during story creation

### Phase 3: Fix Chunk Embeddings (Better matching)
- [x] Create `article_chunks` table schema (schema v3)
- [x] Modify `embed_article` to store each chunk embedding separately
- [x] Modify story matching to use chunk-to-chunk comparison
- [x] Test: chunk embeddings stored, chunk-based matching enabled

### Validation
- [x] Run `rss report -m 5` end-to-end
- [x] Verify story creation uses 0 LLM calls
- [x] Verify no extra LLM calls after extraction phase

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
