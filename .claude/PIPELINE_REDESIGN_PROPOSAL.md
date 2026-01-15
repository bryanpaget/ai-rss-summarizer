# Pipeline Redesign Proposal

## Problem Statement

The current report pipeline makes **8-15 LLM calls and 7-15 embedding calls per article**, with constant model switching between text and embedding models. This is:
1. Extremely slow (model switches take 10-30 seconds each)
2. Wasteful (multiple LLM calls on the same article content)
3. Architecturally confused (no clear phase separation)

## Core Principles

1. **Never make multiple LLM calls on the same data** - If we have article content, extract EVERYTHING from it in ONE call
2. **Efficient ordering** - Group all same-type operations together to minimize model switches
3. **100% visibility** - Every step reports transparently as it happens

## Current vs Proposed

### Current (Per Article)
```
extract_insights(article)           → LLM call 1
semantic_chunk(article)             → LLM call 2
extract_triples(chunk1)             → LLM call 3
extract_triples(chunk2)             → LLM call 4
  └─ find_similar_triple()          → EMBEDDING calls (interleaved)
detect_connections(insight1)        → EMBEDDING + LLM calls (interleaved)
detect_connections(insight2)        → EMBEDDING + LLM calls (interleaved)
analyze_article(article)            → EMBEDDING call
tag_article(article)                → LLM call 5
create_new_story(article)           → LLM calls 6, 7, 8
```
**Result: 8+ LLM calls, 7+ embedding calls, 6-10 model switches PER ARTICLE**

### Proposed (Per Article)
```
PHASE 1 - LLM:    extract_all(article) → insights + triples + signal_tags  [1 call]
PHASE 2 - EMBED:  embed_article() + embed_insights() + categorize()        [N calls]
PHASE 3 - MATCH:  find_story_match() + find_similar_insights()             [0 calls - math only]
PHASE 4 - LLM:    create_story() + classify_connections()                  [1-2 calls if needed]
```
**Result: 2-3 LLM calls, N embedding calls, 2 model switches PER ARTICLE**

---

## Detailed Design

### Phase 1: Batch LLM Extraction

**For each article, ONE prompt that extracts everything:**

```
Given this article, extract the following in JSON format:

1. INSIGHTS: Key learnings, facts, opinions worth remembering
2. TRIPLES: Subject-predicate-object facts (e.g., "OpenAI - released - GPT-5")
3. SIGNAL_TAGS:
   - source_type: [research, news, opinion, tutorial, announcement, analysis]
   - evidence_level: [anecdotal, data-driven, peer-reviewed, speculation]
   - reasoning_type: [causal, correlational, descriptive, predictive]
   - tone: [neutral, optimistic, critical, alarmist, promotional]
   - actionability: [informational, actionable, reference]
   - is_ad: true/false
4. SUMMARY: 2-3 sentence summary

Article:
{title}
{content}

Respond with JSON only.
```

**Output structure:**
```json
{
  "insights": ["insight1", "insight2"],
  "triples": [
    {"subject": "X", "predicate": "Y", "object": "Z"},
  ],
  "signal_tags": {
    "source_type": ["research"],
    "evidence_level": "data-driven",
    ...
  },
  "summary": "..."
}
```

**Visibility output:**
```
[1/10] "Article Title Here"
       → 3 insights, 7 triples
       → signal: research, data-driven, neutral
       → summary: "Brief summary text..."
```

---

### Phase 2: Batch Embedding

**All embedding operations in sequence:**

1. **Embed article semantic cards** (title + summary + tags)
2. **Embed new insights** (for later connection detection)
3. **Trend categorization** (compare article embedding to category embeddings)

**Visibility output:**
```
[Embedding Phase]
  Articles: 10/10 embedded
  Insights: 23/23 embedded
  Trends assigned:
    - "Article 1" → AI/ML, Research
    - "Article 2" → Markets, Finance
```

---

### Phase 3: Matching (No Model Calls)

**Pure computation using pre-computed embeddings:**

1. **Story matching**: Compare each article embedding to existing story embeddings
   - If similarity > threshold: match to existing story
   - If no match: flag for new story creation

2. **Connection candidates**: Compare each new insight embedding to existing insight embeddings
   - Find pairs above similarity threshold
   - Queue for relationship classification

**Visibility output:**
```
[Matching Phase]
  Story matches:
    - "Article 1" → matched to "Ongoing AI Story"
    - "Article 2" → no match (new story needed)
    - "Article 3" → matched to "Market Trends"

  Connection candidates: 12 insight pairs found
```

---

### Phase 4: Batch LLM (Remaining Work)

**Two types of remaining LLM work:**

#### 4a. Story Creation (for unmatched articles)

**ONE prompt per new story:**
```
Create a story entry for this article cluster:

Article: {title}
Summary: {summary}
Key insights: {insights}

Provide JSON with:
- title: Compelling story title (not the article title)
- description: 1-2 sentence story description
- keywords: Array of relevant keywords
```

#### 4b. Connection Classification

**Could batch multiple pairs in ONE prompt:**
```
Classify the relationship between these insight pairs:

Pair 1:
- New: "GPT-5 achieves human-level reasoning"
- Existing: "GPT-4 showed improved reasoning over GPT-3"

Pair 2:
- New: "AI regulation proposed in EU"
- Existing: "US lacks comprehensive AI regulation"

For each pair, classify as: supports, contradicts, extends, related, or unrelated
```

**Visibility output:**
```
[Story & Connection Phase]
  Created stories:
    - "Market Volatility Q1 2026" for Article 2

  Connections classified:
    - "GPT-5 reasoning" EXTENDS "GPT-4 reasoning improvements"
    - "EU AI regulation" RELATED TO "US AI regulation gaps"
```

---

## File Changes Required

### 1. New: `src/extraction.py`
Combined extraction module with single-prompt extraction.

```python
def extract_all(article, provider) -> ExtractionResult:
    """ONE LLM call to extract insights, triples, signal tags, summary."""
    prompt = build_combined_prompt(article)
    response = provider.generate(prompt)
    return parse_extraction_response(response)
```

### 2. Modify: `src/report.py`
Restructure pipeline into 4 phases.

```python
def generate_report(...):
    # Phase 1: LLM extraction (all articles)
    extractions = []
    for article in articles:
        result = extract_all(article, provider)
        display_extraction(article, result)  # Visibility
        extractions.append(result)

    # Phase 2: Embedding (all data)
    embed_articles(articles, extractions)
    embed_insights(extractions)
    assign_trends(articles)

    # Phase 3: Matching (no model calls)
    story_matches = match_to_stories(articles)
    connection_candidates = find_similar_insights(extractions)

    # Phase 4: LLM remaining work
    create_stories_for_unmatched(articles, story_matches)
    classify_connections(connection_candidates)
```

### 3. Deprecate/Remove:
- `knowledge.py`: `extract_insights_from_article()` - replaced by combined extraction
- `knowledge.py`: `extract_triples_with_comparison()` - replaced by combined extraction
- `knowledge.py`: `_semantic_chunk()` - no longer needed
- `signal_tagger.py`: Simplify to just parse the combined response

### 4. Keep but Modify:
- `clustering.py`: Keep story matching logic, remove LLM calls for keywords
- `knowledge.py`: Keep `detect_connections()` but restructure to work with pre-computed embeddings

---

## Model Switch Analysis

| Scenario | Current | Proposed |
|----------|---------|----------|
| 1 article | 6-10 switches | 2 switches |
| 10 articles | 60-100 switches | 2 switches |
| 50 articles | 300-500 switches | 2 switches |

The proposed architecture switches models exactly **twice** regardless of article count:
1. TEXT model for Phase 1
2. EMBEDDING model for Phase 2
3. TEXT model for Phase 4

---

## Visibility Format

```
════════════════════════════════════════════════════════════════
PHASE 1: LLM Extraction (10 articles)
════════════════════════════════════════════════════════════════

[1/10] "OpenAI Announces GPT-5"
       → 4 insights, 12 triples
       → signal: announcement, data-driven, optimistic
       → summary: "OpenAI released GPT-5 with significant improvements..."

[2/10] "Market Volatility Continues"
       → 2 insights, 5 triples
       → signal: news, anecdotal, neutral
       → summary: "Stock markets showed continued volatility..."

...

════════════════════════════════════════════════════════════════
PHASE 2: Embeddings
════════════════════════════════════════════════════════════════

  Embedding articles... 10/10 ✓
  Embedding insights... 28/28 ✓
  Categorizing trends... 10/10 ✓

  Trend assignments:
    "OpenAI Announces GPT-5" → AI/ML, Technology
    "Market Volatility Continues" → Finance, Markets

════════════════════════════════════════════════════════════════
PHASE 3: Matching
════════════════════════════════════════════════════════════════

  Story matches:
    ✓ "OpenAI Announces GPT-5" → "AI Model Releases" (92% similar)
    ✗ "Market Volatility Continues" → no match (new story needed)
    ✓ "Fed Interest Rate Decision" → "Monetary Policy 2026" (87% similar)

  Connection candidates: 15 pairs above 70% similarity

════════════════════════════════════════════════════════════════
PHASE 4: Story Creation & Connections
════════════════════════════════════════════════════════════════

  New stories created:
    "Market Volatility Continues" → "Q1 2026 Market Turbulence"

  Connections classified:
    "GPT-5 reasoning" EXTENDS "GPT-4 benchmarks"
    "Fed rate hold" SUPPORTS "inflation cooling trend"
    ...

════════════════════════════════════════════════════════════════
COMPLETE: 10 articles processed
════════════════════════════════════════════════════════════════
  - 28 insights extracted
  - 67 triples added to knowledge base
  - 8 stories updated, 2 new stories created
  - 15 connections discovered
  - Errors: 0
```

---

## Questions for Review

1. **Triple deduplication**: Currently we check if triples already exist before adding. Should this happen:
   - During Phase 1 (include existing triples in the prompt for comparison)?
   - During Phase 3 (use embeddings to find similar existing triples)?
   - After Phase 4 (simple post-processing)?

2. **Story creation timing**: We don't know if an article needs a new story until after embedding (Phase 2) and matching (Phase 3). The current design handles this in Phase 4. Is this acceptable?

3. **Connection classification batching**: Should we batch all connection pairs into ONE LLM call, or is there a limit where quality degrades?

4. **Error handling**: If Phase 1 fails for one article, should we:
   - Skip that article entirely?
   - Retry with a simpler prompt?
   - Continue and note the error?

---

## Implementation Order

1. Create `src/extraction.py` with combined prompt
2. Test combined extraction on sample articles
3. Modify `report.py` to use 4-phase structure
4. Update visibility/output formatting
5. Remove deprecated functions
6. Update tests
7. Full integration testing

---

## Risks

1. **Combined prompt complexity**: One prompt doing everything might be harder for the LLM to handle consistently. Mitigation: Clear JSON schema, good examples.

2. **Response size**: Combined response will be larger. Mitigation: Set appropriate max_tokens.

3. **Partial failures**: If the combined prompt fails, we lose everything vs. current approach where individual extractions might succeed. Mitigation: Good error handling, maybe fallback to separate calls.
