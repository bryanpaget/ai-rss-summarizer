# Perspective Synthesis with User Categories - Technical Specification

## Overview

This feature enables multi-source perspective synthesis across articles covering the same story, allowing users to choose from 12+ perspective categories to customize their view. It addresses the problem that fixed perspective categories don't match what users actually want to see.

## Related Issues

- GitHub Issue #17: Feature: Perspective Synthesis with User Categories
- Depends on: Story Clustering (#15)
- See: `docs/TREND_ANALYSIS_FEATURES.md` for full context

## Architecture

### 1. Story Identification and Grouping

**Purpose:** Identify which articles are about the same underlying story before synthesizing perspectives.

**Approach:**
- Use semantic similarity to group articles by story
- Compare article titles and content using embeddings or keyword overlap
- Store story clusters in the database for reuse

**Implementation:**
```python
class StoryCluster:
    id: str
    title: str  # Representative title for the cluster
    article_ids: list[str]
    created_at: datetime
    updated_at: datetime
```

**Algorithm:**
1. For each new article, compare against existing story clusters
2. If similarity score > threshold (e.g., 0.7), add to existing cluster
3. Otherwise, create new cluster
4. Periodically merge similar clusters

### 2. Perspective Category System

**Available Categories (from Feature Spec):**

#### Factual Perspectives
- `consensus` - What all sources agree on
- `contested` - Where sources disagree or contradict
- `gaps` - What aspects of the story no one is covering
- `timeline` - Chronological sequence of facts/events

#### Source Framing Perspectives
- `tech-industry` - How tech press frames the story
- `mainstream` - General news media framing
- `financial` - Business/market angle
- `political` - Policy/government angle
- `academic` - Research/scholarly perspective

#### Fun/Entertainment Perspectives
- `spiciest-takes` - Most provocative opinions
- `unhinged-speculation` - Wildest predictions/theories
- `contrarian` - Against-the-grain views
- `doom` - Pessimistic takes
- `hype` - Most optimistic takes

#### Analysis Perspectives
- `expert-quotes` - What domain experts say
- `prediction-track-record` - How past predictions held up

**User Configuration:**
```python
class UserPerspectiveConfig:
    enabled_categories: list[str]  # Which categories to display
    default_categories: list[str]  # Default view
    category_order: list[str]  # Display order preference
```

### 3. Data Structures

#### Database Schema Extensions

Add to existing `articles` table:
```sql
ALTER TABLE articles ADD COLUMN story_cluster_id TEXT;
CREATE INDEX idx_articles_story_cluster ON articles(story_cluster_id);
```

New table for story clusters:
```sql
CREATE TABLE story_clusters (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

New table for perspective synthesis cache:
```sql
CREATE TABLE perspective_cache (
    story_cluster_id TEXT,
    category TEXT,
    content TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (story_cluster_id, category),
    FOREIGN KEY (story_cluster_id) REFERENCES story_clusters(id)
);
```

New table for user preferences:
```sql
CREATE TABLE user_perspective_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    enabled_categories TEXT,  -- JSON array
    default_categories TEXT,  -- JSON array
    category_order TEXT,  -- JSON array
    CHECK (id = 1)  -- Ensure single row
);
```

#### Python Data Structures

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class StoryCluster:
    """Represents a group of articles about the same story."""
    id: str
    title: str
    article_ids: list[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class Perspective:
    """A synthesized perspective on a story."""
    category: str
    content: str
    source_articles: list[str]  # Article IDs used
    confidence: float  # 0-1, how confident the synthesis is
    generated_at: datetime

@dataclass
class SynthesizedStory:
    """Complete perspective synthesis for a story."""
    cluster: StoryCluster
    perspectives: dict[str, Perspective]  # category -> Perspective
    articles: list[Article]
```

### 4. Perspective Synthesis Algorithm

**Input:**
- Story cluster with multiple articles
- List of desired perspective categories

**Output:**
- Synthesized perspective for each requested category

**Process:**

```python
def synthesize_perspectives(
    cluster: StoryCluster,
    articles: list[Article],
    categories: list[str],
    llm_provider
) -> dict[str, Perspective]:
    """
    Generate perspectives for a story cluster.

    Args:
        cluster: Story cluster to synthesize
        articles: Articles in the cluster
        categories: Which perspectives to generate
        llm_provider: LLM provider for synthesis

    Returns:
        Dictionary mapping category to Perspective
    """
    perspectives = {}

    for category in categories:
        # Check cache first
        cached = get_cached_perspective(cluster.id, category)
        if cached and is_fresh(cached):
            perspectives[category] = cached
            continue

        # Generate new perspective
        prompt = build_perspective_prompt(category, articles)
        synthesis = llm_provider.generate(prompt)

        perspective = Perspective(
            category=category,
            content=synthesis,
            source_articles=[a.id for a in articles],
            confidence=estimate_confidence(synthesis, articles),
            generated_at=datetime.now()
        )

        # Cache for reuse
        cache_perspective(cluster.id, category, perspective)
        perspectives[category] = perspective

    return perspectives
```

**Prompt Templates by Category:**

1. **Consensus**: "Given these articles about [topic], what facts do all sources agree on? List only points with unanimous agreement."

2. **Contested**: "Given these articles about [topic], what specific claims or interpretations do the sources disagree about? For each disagreement, cite which sources say what."

3. **Gaps**: "Given these articles about [topic], what important aspects of the story are NOT being covered by any source? What questions remain unanswered?"

4. **Timeline**: "Given these articles about [topic], construct a chronological timeline of events. Include only factual events with timestamps, not opinions."

5. **Spiciest-takes**: "Given these articles about [topic], extract the most provocative, bold, or inflammatory opinions. Quote directly and cite sources."

6. **Tech-industry / Mainstream / Financial / Political / Academic**: "Given these articles about [topic], how is this story being framed from a [PERSPECTIVE] angle? What unique concerns or priorities does this perspective emphasize?"

7. **Expert-quotes**: "Given these articles about [topic], extract all quotes from domain experts (researchers, practitioners, authorities). Identify their credentials."

8. **Contrarian**: "Given these articles about [topic], find views that go against the prevailing narrative. What alternative interpretations are presented?"

**Confidence Estimation:**

```python
def estimate_confidence(synthesis: str, articles: list[Article]) -> float:
    """
    Estimate confidence in a synthesized perspective.

    Factors:
    - Number of source articles (more is better)
    - Agreement between sources (less contradiction is better)
    - Presence of primary sources vs opinion pieces
    - Recency of articles

    Returns:
        Confidence score 0-1
    """
    score = 0.0

    # Base score from article count
    if len(articles) >= 5:
        score += 0.4
    elif len(articles) >= 3:
        score += 0.3
    elif len(articles) >= 2:
        score += 0.2
    else:
        score += 0.1

    # Check for primary sources (tags like 'primary', 'documented')
    primary_count = sum(1 for a in articles if 'primary' in (a.trend_tags or ''))
    if primary_count > 0:
        score += 0.2

    # Recency bonus
    recent_count = sum(1 for a in articles if is_recent(a.published, hours=24))
    if recent_count >= len(articles) * 0.7:
        score += 0.2

    # Check synthesis quality (length, structure)
    if len(synthesis) > 100 and '\n' in synthesis:
        score += 0.2

    return min(score, 1.0)
```

### 5. Integration with Existing Flow

**Current Flow:**
1. Fetch articles from RSS feeds
2. Store in database
3. Generate summaries
4. Categorize into trend tags
5. Display via CLI

**Enhanced Flow with Perspective Synthesis:**
1. Fetch articles from RSS feeds
2. Store in database
3. **NEW: Cluster articles into stories**
4. Generate summaries
5. Categorize into trend tags
6. **NEW: Generate perspective synthesis for story clusters**
7. Display via CLI with perspective options

**Entry Points:**

```python
# In src/perspective.py
def update_story_clusters(storage: Storage) -> list[StoryCluster]:
    """
    Update story clusters for recent articles.
    Run after fetching new articles.
    """
    pass

def generate_perspectives(
    cluster_id: str,
    categories: list[str],
    storage: Storage,
    llm_provider
) -> dict[str, Perspective]:
    """
    Generate perspectives for a story cluster.
    """
    pass
```

**CLI Integration:**

```python
# New commands in cli.py

@app.command()
def perspectives(
    story_id: Optional[str] = None,
    categories: Optional[list[str]] = None,
    limit: int = 10,
):
    """
    View synthesized perspectives on stories.

    Examples:
        rss perspectives                    # Show top stories with default perspectives
        rss perspectives --categories consensus,spiciest-takes
        rss perspectives story_123          # Show specific story
    """
    pass

@app.command("perspective-config")
def configure_perspectives():
    """
    Configure which perspective categories to show by default.
    """
    pass
```

### 6. Edge Cases and Error Handling

#### Edge Case 1: Single Article in Cluster
**Problem:** Can't synthesize multiple perspectives from one source
**Solution:**
- Still generate perspectives but mark with low confidence
- Show warning: "Limited perspectives (only 1 source)"
- Some categories may not apply (e.g., 'contested' requires multiple sources)

#### Edge Case 2: No Articles Match Story Cluster
**Problem:** Cluster exists but all articles were deleted/expired
**Solution:**
- Delete orphaned cluster
- Return empty perspective set

#### Edge Case 3: LLM Provider Unavailable
**Problem:** Can't generate perspectives without LLM
**Solution:**
- Fall back to simple extraction (pull quotes, aggregate titles)
- Cache last successful generation
- Show warning: "Perspectives limited without LLM"

#### Edge Case 4: Articles Too Similar (All Same Source)
**Problem:** Multiple articles but all from same outlet, no real diversity
**Solution:**
- Detect source diversity in cluster
- Mark perspectives with "Limited source diversity"
- Reduce confidence score

#### Edge Case 5: Category Not Applicable
**Problem:** Some stories don't have "expert-quotes" or "contrarian" views
**Solution:**
- Return None for that perspective
- Display: "No [category] perspective available"
- Don't fail entire synthesis

#### Edge Case 6: Cache Staleness
**Problem:** Story evolves, cached perspectives become outdated
**Solution:**
- TTL on cached perspectives (e.g., 6 hours)
- Detect when new articles added to cluster -> invalidate cache
- Allow manual cache refresh

#### Error Handling Patterns

```python
class PerspectiveError(Exception):
    """Base exception for perspective synthesis errors."""
    pass

class InsufficientSourcesError(PerspectiveError):
    """Not enough articles to generate perspective."""
    pass

class CategoryNotApplicableError(PerspectiveError):
    """Requested category doesn't apply to this story."""
    pass

class LLMProviderError(PerspectiveError):
    """LLM provider failed to generate perspective."""
    pass

# Usage
try:
    perspective = generate_perspective(cluster, 'consensus', llm_provider)
except InsufficientSourcesError:
    perspective = Perspective(
        category='consensus',
        content='Insufficient sources for synthesis (only 1 article)',
        source_articles=[],
        confidence=0.1,
        generated_at=datetime.now()
    )
except LLMProviderError:
    # Fall back to simple extraction
    perspective = fallback_perspective(cluster, 'consensus')
```

### 7. User Experience

**Display Format:**

```
Story: "GPT-5 Development Rumors"
Sources: 5 articles from TechCrunch, Reuters, Bloomberg, The Verge, Ars Technica
Last updated: 2 hours ago

[consensus] ████████████████ High confidence
- OpenAI is working on next-generation model (all sources confirm)
- No official release date announced (confirmed by OpenAI spokesperson)
- Model will be "substantially more capable" (Sam Altman quote, 3 sources)

[contested] ████████░░░░░░░░ Medium confidence
- Release timeline: Q2 2024 (Bloomberg, TechCrunch) vs H2 2024 (Ars Technica)
- Compute requirements: 5x GPT-4 (Bloomberg) vs 10x GPT-4 (The Verge)

[spiciest-takes] ██████░░░░░░░░░░ Low confidence
- "Will make all other AI obsolete" - TechCrunch opinion piece
- "AGI within reach" - Unnamed OpenAI insider via Bloomberg
- "Mostly hype, incremental improvement" - AI researcher (Ars Technica)

[gaps] ████████████████ High confidence
- Training data sources and cut-off date
- Specific capabilities beyond "more capable"
- Pricing structure and API availability
- Environmental impact of training run

Configure perspectives: rss perspective-config
```

**User Configuration UI (CLI):**

```
$ rss perspective-config

Current perspective settings:

Default categories (shown for all stories):
  ✓ consensus
  ✓ contested
  ✓ gaps

Available categories (use --categories to show):
  □ timeline
  □ tech-industry
  □ mainstream
  □ financial
  □ political
  □ academic
  □ spiciest-takes
  □ unhinged-speculation
  □ contrarian
  □ doom
  □ hype
  □ expert-quotes
  □ prediction-track-record

Change settings:
  [1] Add category to defaults
  [2] Remove category from defaults
  [3] Reset to defaults
  [4] Done

Your choice:
```

### 8. Performance Considerations

**Caching Strategy:**
- Cache generated perspectives for 6 hours
- Invalidate when new articles added to cluster
- Store in SQLite for persistence

**Batch Processing:**
- Generate perspectives for multiple clusters in parallel
- Use async/await for LLM API calls
- Rate limit to avoid API throttling

**Cost Management (LLM API):**
- Only generate perspectives on-demand or for top N stories
- Reuse cached perspectives aggressively
- Allow users to set perspective budget (max API calls per day)

**Database Performance:**
- Index on story_cluster_id for fast lookups
- Use prepared statements for perspective queries
- Periodically clean up old clusters (>30 days)

### 9. Testing Strategy

**Unit Tests:**
- Test story clustering algorithm with known similar/dissimilar articles
- Test perspective prompt generation for each category
- Test confidence score calculation with various inputs
- Test cache hit/miss behavior

**Integration Tests:**
- Test full flow: fetch -> cluster -> synthesize -> display
- Test with real RSS articles (use fixtures)
- Test LLM provider fallback when unavailable

**Manual Testing Scenarios:**
1. Single article cluster -> verify low confidence warnings
2. Large cluster (10+ articles) -> verify synthesis quality
3. All articles from same source -> verify diversity warning
4. Story evolves over time -> verify cache invalidation
5. Each perspective category -> verify appropriate content

**Test Data:**
Create fixture articles about a well-known story (e.g., "OpenAI leadership changes Nov 2023") with:
- Articles that agree (for 'consensus')
- Articles that disagree (for 'contested')
- Articles with provocative takes (for 'spiciest-takes')
- Articles with expert quotes
- Articles from different source types (tech, mainstream, financial)

### 10. Implementation Phases

**Phase 1: Core Infrastructure** (MVP)
- [ ] Database schema changes
- [ ] Story clustering algorithm (simple keyword-based)
- [ ] Basic perspective synthesis (consensus, contested only)
- [ ] Cache layer

**Phase 2: Category Expansion**
- [ ] Implement all 14+ perspective categories
- [ ] Refine prompts for each category
- [ ] Confidence scoring

**Phase 3: User Configuration**
- [ ] User preference storage
- [ ] CLI commands for configuration
- [ ] Display formatting

**Phase 4: Optimization**
- [ ] Improve clustering with embeddings
- [ ] Batch processing
- [ ] Performance tuning

**Phase 5: Polish**
- [ ] Error handling
- [ ] Edge case coverage
- [ ] Documentation

### 11. Dependencies

**Existing Code:**
- `src/storage.py` - Database layer (extend with new tables)
- `src/summarizer.py` - LLM providers (reuse for perspective synthesis)
- `src/trends.py` - Trend analysis (complement with perspectives)
- `src/cli.py` - CLI interface (add new commands)

**New Modules:**
- `src/clustering.py` - Story clustering logic
- `src/perspectives.py` - Perspective synthesis core
- `src/perspective_config.py` - User configuration management

**External Libraries:**
- No new dependencies required
- Optional: sentence-transformers for better clustering (can start without)

### 12. Open Questions

1. **Clustering Algorithm**: Start with simple keyword overlap or invest in embeddings immediately?
   - **Recommendation**: Start simple, upgrade if needed

2. **Cache TTL**: 6 hours reasonable? Should vary by story velocity?
   - **Recommendation**: 6h default, allow per-cluster override for fast-moving stories

3. **Perspective Quality**: How to validate that synthesized perspectives are accurate?
   - **Recommendation**: Manual spot-checking initially, consider user feedback mechanism

4. **Source Diversity**: Minimum number of sources for each perspective category?
   - **Recommendation**: 2 for most, 3+ for 'contested', 1 acceptable for 'consensus'

## Summary

This specification provides a complete design for multi-source perspective synthesis with user-defined categories. The implementation is phased to deliver value incrementally, starting with core clustering and basic perspectives, then expanding to the full 14+ category system with user customization.

Key features:
- Flexible category system (users choose what to see)
- Confidence scoring (users know when to trust synthesis)
- Intelligent caching (minimize LLM API costs)
- Graceful degradation (works without LLM, just limited)
- Integration with existing codebase (minimal disruption)
