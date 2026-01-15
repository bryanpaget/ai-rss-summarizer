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

---

### Issue 2: Multi-task Quality Degradation
**Status:** Unknown - needs empirical testing

**Problem:** Gemini claims asking LLM to do 6 things at once degrades quality vs doing 1 thing 6 times.

**Solution:** Build testing harness to measure empirically.

**Test design:**
- Same article, same tasks
- One variable: tasks per call (1, 2, 3, 6)
- Measure: quality of output, time taken
- Run full test twice, compare results
- Human + Gemini review output tables

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

Pattern: Cheap operation to narrow down → expensive operation only on filtered set.

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

---

### Issue 6: Error Atomicity
**Status:** Non-issue

**Problem:** Gemini raised concern about data loss if combined calls fail.

**Reality:** System already saves results immediately after each step. If interrupted, resume from last completed step. No change needed.

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

---

### Issue 8: Graph Cleanup Operation
**Status:** New - needs design

**Problem:** With exact-match dedup only, semantic duplicates will accumulate ("USA" vs "United States" as separate nodes).

**Solution:** Periodic cleanup operation that:
- Runs after batch processing (doesn't block ingestion)
- Finds semantically similar triples/nodes via embedding comparison
- Consolidates duplicates
- Could also run on schedule (e.g., weekly) if not triggered automatically

This is the RIGHT place for expensive embedding comparisons - batch cleanup, not per-item ingestion.

---

## Summary Table

| # | Issue | Status | Work Required |
|---|-------|--------|---------------|
| 1 | Chunking confusion | Resolved | Clarify: chunk + extract in ONE call |
| 2 | Multi-task quality | Unknown | Build testing harness, measure empirically |
| 3 | No ANN/FAISS | Real problem | Implement FAISS for O(log N) search |
| 4 | Connection classification | Real problem | ANN candidates → ONE LLM call |
| 5 | Triple dedup blocking | Real problem | Remove embedding calls; add DB constraint |
| 6 | Error atomicity | Non-issue | No change needed |
| 7 | Combined prompt | Pending | Design single extraction prompt |
| 8 | Graph cleanup | New | Design periodic consolidation operation |

---

## Next Steps

1. Critique this document (Claude + Gemini)
2. Iterate until complete
3. Create GitHub issue
4. Implement systematically with testing/validation
5. Push PR
