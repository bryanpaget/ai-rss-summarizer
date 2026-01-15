# Pipeline Issues Tracking

## Context

The current report pipeline has fundamental efficiency and scalability problems. This document tracks all identified issues and proposed solutions.

## Core Principles

1. **Never make multiple LLM calls on the same data** - If processing an article, extract everything in ONE call
2. **Efficient ordering** - Group same-type operations to minimize model switches
3. **100% visibility** - Every step reports transparently as it happens
4. **Don't block ingestion with expensive operations** - Cleanup can happen separately

---

## Issues

### Issue 1: Chunking Confusion
**Status:** Resolved (clarification needed)

**Problem:** Proposal was misread as "eliminate chunking" when the intent was "eliminate SEPARATE chunking calls"

**Solution:** Keep chunking, but chunk + extract in ONE LLM call, not:
- Call 1: "chunk this" → returns chunks
- Call 2: "extract from chunk 1"
- Call 3: "extract from chunk 2"

Instead: ONE call that chunks AND extracts from each chunk.

**Note on large articles:** If an article exceeds the model's input context, pre-chunking may be necessary. The principle is: don't make multiple calls on data that fits in one call.

---

### Issue 2: Multi-task Quality Degradation
**Status:** Unknown - needs empirical testing

**Problem:** Concern that asking LLM to do 6 things at once degrades quality vs doing 1 thing 6 times.

**Solution:** Build testing harness to measure empirically.

**Test design:**
- Same article, same tasks
- One variable: tasks per call (1, 2, 3, 6)
- Measure: quality of output, time taken
- Run full test twice, compare results
- Human + Gemini review output tables

**Plan B:** If testing shows unacceptable quality degradation, we split into logical groups:
- Group A: Insights + Triples (knowledge extraction)
- Group B: Signal tags + Summary (article-level metadata)

This would be 2 calls instead of 6, still a major improvement.

---

### Issue 3: No ANN/FAISS for Vector Search
**Status:** Confirmed problem

**Problem:** Current `find_similar()` in `embeddings.py` does brute-force O(N):
```python
rows = conn.execute("SELECT * FROM knowledge_embeddings...")
for row in rows:
    similarity = self.cosine_similarity(query_vector, stored_vector)
```

Loads ALL vectors, compares one by one. Completely unscalable.

**Solution:** Implement FAISS or similar ANN library for O(log N) similarity search.

**Sync consideration:** ANN index must stay in sync with SQLite. On insert: write to both DB and index. On index failure: log error, item still in DB, can rebuild index from DB.

---

### Issue 4: Connection Classification Scaling
**Status:** Confirmed problem

**Problem:** Current approach for finding insight connections:
- New insight comes in
- Compare to potentially EVERY existing insight via LLM calls
- O(N) LLM calls per insight

With 1000 existing insights and 10 new ones = potentially 10,000 LLM calls.

**Solution:**
1. Use embeddings + ANN to find top N candidates (fast, O(log N))
2. ONE LLM call: "Here are 10 potential matches. Which are actually related, and how?"

**Batch optimization:** If processing multiple new insights, batch them:
- "Here are 5 new insights. For each, here are their top candidates. Classify all relationships."
- Reduces from 5 LLM calls to 1.

---

### Issue 5: Triple Dedup Blocking Ingestion
**Status:** Confirmed problem

**Problem:** Current code calls `_find_similar_triple()` with EMBEDDING comparison for EVERY triple before inserting. Extracting 10 triples = 10 embedding calls just for dedup.

This is backwards - expensive operations blocking simple inserts.

**Solution:**
1. Remove per-triple embedding calls on insert
2. Add UNIQUE(subject, predicate, object) constraint to database
3. Exact duplicates rejected automatically by DB (free, instant)
4. Semantic dedup handled by separate cleanup operation (Issue 8)

**Trade-off acknowledged:** Graph will have semantic duplicates ("USA" vs "United States") until cleanup runs. This is acceptable because:
- Ingestion is not blocked
- Graph is still usable (just has some redundancy)
- Cleanup consolidates periodically

---

### Issue 6: Error Atomicity
**Status:** Needs clarification

**Original claim:** Non-issue because system saves immediately.

**Gemini's critique:** If Issue 7's combined call fails, there are no intermediate steps to resume from.

**Clarification:**
- Each ARTICLE's results are saved after processing that article
- If combined call fails for Article 3, Articles 1-2 are already saved
- Article 3 can be retried
- We do NOT batch multiple articles into one call

**Mitigation for truncated output:** If LLM output is truncated (incomplete JSON), log error, skip article, continue. Can retry failed articles with smaller chunk size or split prompt.

---

### Issue 7: Combined Prompt Design
**Status:** Pending

**Problem:** Need to design single prompt that extracts everything from an article.

**Solution:** Design prompt that in ONE call:
- Identifies semantic chunks
- Extracts insights from each chunk
- Extracts triples from each chunk
- Generates signal tags (article-level)
- Generates summary (article-level)

Returns structured JSON with all results.

**Output token limit consideration:**
- Most articles will fit within output limits (4k-8k tokens)
- For very dense articles that might exceed limits, detect truncation and fall back to split calls
- Monitor and log truncation frequency to assess if this is a real problem

---

### Issue 8: Graph Cleanup Operation
**Status:** New - needs design

**Problem:** With exact-match dedup only, semantic duplicates will accumulate ("USA" vs "United States" as separate nodes).

**Solution:** Periodic cleanup operation that:
- Runs after batch processing (doesn't block ingestion)
- Finds semantically similar triples/nodes via embedding comparison
- Consolidates duplicates

**Complexity acknowledged (Gemini's critique):**
Merging nodes is not trivial. It requires:
1. Identify duplicate nodes (via embedding similarity)
2. Choose canonical node (e.g., most common form, or most connected)
3. Re-point all edges from duplicate to canonical
4. Delete duplicate node
5. All in a transaction to prevent corruption

**Implementation approach:**
- Start simple: just flag potential duplicates for human review
- Later: automated merging with transaction safety
- Track merge history for debugging

---

### Issue 9: Schema Enforcement
**Status:** New - from Gemini critique

**Problem:** Relying on "Respond with JSON only" instructions is fragile. LLMs can include markdown formatting, conversational filler, or malformed JSON.

**Solution:**
1. Use JSON mode if available (OpenAI-compatible endpoints support this)
2. Implement robust parsing with fallback:
   - Try `json.loads()` first
   - If fails, try to extract JSON from markdown code blocks
   - If still fails, log raw response and skip article
3. Consider Pydantic validation for type safety on parsed results

**Priority:** Lower than core pipeline issues. Current system likely handles this ad-hoc already; this formalizes it.

---

## Summary Table

| # | Issue | Status | Work Required |
|---|-------|--------|---------------|
| 1 | Chunking confusion | Resolved | Clarify: chunk + extract in ONE call |
| 2 | Multi-task quality | **DONE** | scripts/quality_test_harness.py created |
| 3 | No ANN/FAISS | **DONE** | src/vector_index.py - FAISS integration |
| 4 | Connection classification | **DONE** | detect_connections() uses FAISS + batched LLM |
| 5 | Triple dedup blocking | **DONE** | UNIQUE constraint + removed embedding calls |
| 6 | Error atomicity | Clarified | Per-article saves; handle truncation gracefully |
| 7 | Combined prompt | **DONE** | extract_all_from_article() + Pydantic schema |
| 8 | Graph cleanup | **DONE** | src/graph_cleanup.py created |
| 9 | Schema enforcement | **DONE** | src/schema.py with Pydantic + fallback parsing |

---

## Gemini Critique Response

### First Review (Proposal)

| Gemini Finding | Severity | Response |
|----------------|----------|----------|
| Output token limits will truncate | CRITICAL | Added truncation detection and fallback strategy |
| Resume contradiction | CRITICAL | Clarified: per-article saves, not per-batch |
| Efficiency vs quality conflict | MAJOR | Added Plan B if testing shows degradation |
| Semantic duplicates fragment graph | MAJOR | Accepted trade-off; cleanup handles it |
| Graph cleanup is complex | MAJOR | Acknowledged; start with flagging, then automate |
| ANN sync issues | MINOR | Added sync strategy |
| Batch connection optimization | MINOR | Added to Issue 4 |

### Second Review (Tracking Document)

| Gemini Finding | Severity | Response |
|----------------|----------|----------|
| Quality regression from removing chunking | CRITICAL | **Already addressed**: Issue 1 clarifies chunking IS kept |
| Combined prompt cognitive load | MAJOR | **Already addressed**: Issue 2 + Plan B |
| All-or-nothing failure mode | MAJOR | **Already addressed**: Issue 6 (per-article saves) |
| Scalability bottleneck Phase 3 | MAJOR | **Already addressed**: Issue 3 (FAISS) |
| Triple deduplication gap | MAJOR | **Already addressed**: Issues 5 + 8 |
| Batch connection classification quality | MINOR | **Already addressed**: Issue 4 |
| Lack of schema enforcement | MINOR | **NEW**: Added as Issue 9 |
| Misleading model switch claim | MINOR | Acknowledged; marketing claim vs implementation |
| Hardcoded signal taxonomy | MINOR | Out of scope for this fix; config-driven is future work |

---

## Next Steps

1. ~~Critique this document (Claude + Gemini)~~ Done
2. Review critique responses (Human)
3. Create GitHub issue when approved
4. Implement systematically with testing/validation
5. Push PR
