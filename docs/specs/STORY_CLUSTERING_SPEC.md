# Technical Specification: Two-Level Story Clustering & Evolution Tracking

## Overview

This specification defines the architecture and implementation for a two-level clustering system that:
1. Groups articles into stories (Level 1)
2. Identifies specific news items within each story (Level 2)
3. Tracks story evolution over time

## Goals

- Distinguish actual new information from recap/analysis/opinion
- Track which outlet broke specific news
- Show information flow across providers
- Track story lifecycle: emerging → developing → peaked → declining → resolved

## Architecture

### Data Model

#### Story

```python
@dataclass
class Story:
    """Represents a cluster of articles about the same ongoing story."""

    id: str  # UUID
    title: str  # Generated story title
    description: str  # Brief description of what the story is about
    keywords: list[str]  # Key terms that identify this story
    first_seen: datetime  # When first article appeared
    last_updated: datetime  # When last article was added
    lifecycle_state: str  # emerging, developing, peaked, declining, resolved
    article_ids: list[str]  # IDs of articles in this story
    news_item_ids: list[str]  # IDs of news items within this story
    created_at: datetime
```

#### NewsItem

```python
@dataclass
class NewsItem:
    """Represents a specific piece of new information within a story."""

    id: str  # UUID
    story_id: str  # Parent story
    title: str  # What's new
    description: str  # The actual new information
    first_reported_by: str  # Feed URL of first reporter
    first_seen: datetime  # When this news item first appeared
    article_ids: list[str]  # Articles that mention this news item
    item_type: str  # new_info, recap, analysis, opinion
    confidence: float  # 0-1, how confident we are in the classification
    created_at: datetime
```

### Database Schema

```sql
-- Stories table
CREATE TABLE stories (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    keywords TEXT,  -- JSON array
    first_seen TIMESTAMP NOT NULL,
    last_updated TIMESTAMP NOT NULL,
    lifecycle_state TEXT DEFAULT 'emerging',
    article_ids TEXT,  -- JSON array
    news_item_ids TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stories_lifecycle ON stories(lifecycle_state);
CREATE INDEX idx_stories_last_updated ON stories(last_updated);

-- News items table
CREATE TABLE news_items (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    first_reported_by TEXT,
    first_seen TIMESTAMP NOT NULL,
    article_ids TEXT,  -- JSON array
    item_type TEXT DEFAULT 'new_info',
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id)
);

CREATE INDEX idx_news_items_story ON news_items(story_id);
CREATE INDEX idx_news_items_type ON news_items(item_type);
CREATE INDEX idx_news_items_first_seen ON news_items(first_seen);

-- Add story_id to articles table
ALTER TABLE articles ADD COLUMN story_id TEXT;
CREATE INDEX idx_articles_story ON articles(story_id);
```

## Algorithm Design

### Level 1: Story Identification

**Goal**: Cluster articles into story groups

**Approach**: LLM-assisted semantic clustering

**Process**:

1. **Extract article features** for each new article:
   - Title and content text
   - Named entities (people, places, organizations)
   - Key phrases and topics
   - Published timestamp

2. **Compare with existing stories**:
   - For each existing active story (not resolved):
     - Calculate semantic similarity using LLM
     - Check for overlapping entities and keywords
     - Consider temporal proximity

3. **Clustering decision**:
   - If similarity > threshold (0.75): Add to existing story
   - If similarity < threshold: Create new story

4. **Story metadata generation**:
   - Generate story title from cluster centroid
   - Extract common keywords across articles
   - Update lifecycle state based on article velocity

**LLM Prompt Template**:

```python
def generate_story_comparison_prompt(article: Article, story: Story) -> str:
    return f"""
Compare this article to an existing story.

ARTICLE:
Title: {article.title}
Content: {article.content[:500]}

EXISTING STORY:
Title: {story.title}
Description: {story.description}
Keywords: {', '.join(story.keywords)}

Are these about the same ongoing story? Consider:
- Same event or topic
- Related developments in same story
- Same key entities (people, organizations, places)

Respond with JSON:
{{
    "is_same_story": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""
```

### Level 2: News Item Identification

**Goal**: Within a story, identify specific pieces of new information

**Approach**: LLM-based information extraction and deduplication

**Process**:

1. **Extract claims from article**:
   - Use LLM to extract distinct factual claims
   - Classify each claim as: new_info, recap, analysis, opinion

2. **Compare with existing news items in story**:
   - Check if claim is truly new or already reported
   - Identify the original source if this is a secondary report

3. **News item tracking**:
   - Record which outlet first reported each news item
   - Track which articles mention each news item
   - Maintain chronological order of developments

**LLM Prompt Template**:

```python
def generate_news_extraction_prompt(article: Article, existing_items: list[NewsItem]) -> str:
    existing_summary = "\n".join([
        f"- {item.title}: {item.description}"
        for item in existing_items
    ])

    return f"""
Extract new information from this article.

ARTICLE:
Title: {article.title}
Content: {article.content}

ALREADY KNOWN (from previous articles):
{existing_summary if existing_summary else "None"}

Task: Extract distinct pieces of NEW information from this article.
For each piece of information, classify it as:
- new_info: Actually new development or fact
- recap: Background/context from earlier
- analysis: Commentary or interpretation
- opinion: Editorial perspective

Respond with JSON array:
[
    {{
        "title": "brief title of news item",
        "description": "what's new",
        "type": "new_info|recap|analysis|opinion",
        "confidence": 0.0-1.0
    }}
]
"""
```

### Story Evolution Tracking

**Goal**: Track story lifecycle and identify state transitions

**States**:
- `emerging`: 1-3 articles, less than 24 hours old
- `developing`: 4+ articles, increasing velocity
- `peaked`: High article count, velocity declining
- `declining`: Decreasing velocity, no new articles recently
- `resolved`: No new articles for 7+ days, story concluded

**Velocity Calculation**:

```python
def calculate_velocity(story: Story, window_hours: int = 24) -> float:
    """Calculate article velocity (articles per day)."""
    recent_cutoff = datetime.now() - timedelta(hours=window_hours)
    recent_articles = [
        aid for aid in story.article_ids
        if get_article_timestamp(aid) > recent_cutoff
    ]
    return len(recent_articles) / (window_hours / 24)
```

**State Transition Logic**:

```python
def update_lifecycle_state(story: Story) -> str:
    """Determine story lifecycle state."""
    age_hours = (datetime.now() - story.first_seen).total_seconds() / 3600
    hours_since_update = (datetime.now() - story.last_updated).total_seconds() / 3600
    article_count = len(story.article_ids)
    velocity = calculate_velocity(story)

    # Resolved: No activity for 7 days
    if hours_since_update > 168:
        return "resolved"

    # Declining: No recent articles but not resolved yet
    if hours_since_update > 48 and velocity < 0.5:
        return "declining"

    # Peaked: Many articles but velocity declining
    if article_count >= 10 and velocity < 2.0:
        return "peaked"

    # Developing: Multiple articles and growing
    if article_count >= 4 or velocity >= 2.0:
        return "developing"

    # Emerging: New story
    return "emerging"
```

## Integration Points

### 1. Storage Layer (`src/storage.py`)

**New methods**:

```python
class Storage:
    def save_story(self, story: Story) -> bool
    def get_story(self, story_id: str) -> Optional[Story]
    def get_active_stories(self, limit: int = 50) -> list[Story]
    def update_story(self, story: Story) -> None

    def save_news_item(self, item: NewsItem) -> bool
    def get_news_items(self, story_id: str) -> list[NewsItem]
    def update_article_story(self, article_id: str, story_id: str) -> None
```

### 2. Clustering Module (`src/clustering.py` - NEW)

**Classes**:

```python
class StoryClusterer:
    """Handles Level 1 clustering: grouping articles into stories."""

    def __init__(self, llm_provider: LLMProvider, storage: Storage)
    def cluster_article(self, article: Article) -> Story
    def find_matching_story(self, article: Article) -> Optional[Story]
    def create_new_story(self, article: Article) -> Story
    def update_story_with_article(self, story: Story, article: Article) -> Story

class NewsItemExtractor:
    """Handles Level 2: extracting news items within stories."""

    def __init__(self, llm_provider: LLMProvider, storage: Storage)
    def extract_news_items(self, article: Article, story: Story) -> list[NewsItem]
    def deduplicate_items(self, new_items: list[NewsItem], existing: list[NewsItem]) -> list[NewsItem]

class StoryEvolutionTracker:
    """Tracks story lifecycle and state transitions."""

    def __init__(self, storage: Storage)
    def update_all_stories(self) -> dict
    def calculate_velocity(self, story: Story, window_hours: int = 24) -> float
    def update_lifecycle_state(self, story: Story) -> str
```

### 3. Summarization Flow (`src/summarizer.py`)

**Updated flow**:

```python
def summarize_articles(storage, limit: int = 10, use_clustering: bool = True):
    """
    Enhanced summarization with clustering.

    1. Fetch unsummarized articles
    2. Generate summaries (existing functionality)
    3. If use_clustering:
       - Cluster articles into stories
       - Extract news items within stories
       - Update story metadata
    """
```

### 4. CLI Commands (`src/cli.py`)

**New commands**:

```python
@app.command()
def stories(
    limit: int = 20,
    lifecycle: Optional[str] = None,  # Filter by state
):
    """List stories with their articles and news items."""

@app.command()
def story(story_id: str):
    """Show detailed view of a specific story."""

@app.command()
def evolution():
    """Show story evolution statistics and trends."""
```

## Error Handling

### LLM Failures

- **Timeout**: Fall back to keyword-based similarity
- **Invalid JSON**: Use regex parsing or skip item
- **API errors**: Queue for retry, continue processing

### Edge Cases

1. **Ambiguous articles**: May belong to multiple stories
   - Solution: Allow article to belong to multiple stories
   - Track primary vs secondary story relationship

2. **Story merging**: Two stories discovered to be the same
   - Solution: Implement story merge operation
   - Combine article_ids and news_item_ids

3. **Story splitting**: One story contains multiple distinct narratives
   - Solution: Manual or LLM-assisted story split
   - Create child stories with appropriate articles

4. **News item deduplication**: Same info phrased differently
   - Solution: Use semantic similarity threshold
   - Keep highest confidence version

## Performance Considerations

### Optimization Strategies

1. **Caching**:
   - Cache story embeddings for faster similarity
   - Cache active stories in memory
   - Invalidate on updates

2. **Batch processing**:
   - Process articles in batches
   - Bulk LLM calls when possible

3. **Incremental updates**:
   - Only check active stories (not resolved)
   - Limit comparison window (last 30 days)

4. **Async processing**:
   - Clustering can happen asynchronously
   - Queue articles for background processing

### Estimated Costs

**LLM calls per article**:
- Story comparison: 1-10 calls (depends on active stories)
- News extraction: 1 call
- Total: ~5-10 calls per article average

**For 100 articles/day**:
- ~500-1000 LLM calls/day
- Using local LLM (LM Studio): Free
- Using Claude API: ~$0.50-2.00/day
- Using Gemini Free tier: Free (up to quota)

## Testing Strategy

### Unit Tests

1. Test story creation from article
2. Test similarity comparison logic
3. Test news item extraction
4. Test lifecycle state transitions
5. Test database operations

### Integration Tests

1. Process batch of real articles
2. Verify story clustering accuracy
3. Verify news item deduplication
4. Test full pipeline end-to-end

### Validation Metrics

- **Clustering accuracy**: Manual review of samples
- **News item precision**: % of items that are truly new
- **News item recall**: % of new info that was caught
- **State transition accuracy**: Validate lifecycle states

## Future Enhancements

1. **Cross-story connections**: Link related stories
2. **Story summarization**: Generate story-level summaries
3. **Breaking news detection**: Alert on significant new items
4. **Source reliability tracking**: Track which sources break news first
5. **Fact-checking integration**: Verify claims across sources
6. **Timeline visualization**: Visual story evolution view
7. **Email digests**: Daily/weekly story summaries

## Implementation Timeline

**Phase 1 (MVP)**: Core functionality
- Story clustering (Level 1)
- Basic news item extraction (Level 2)
- Database schema and models
- CLI commands

**Phase 2**: Evolution tracking
- Lifecycle state tracking
- Velocity calculations
- Story metadata updates

**Phase 3**: Polish
- Optimization and caching
- Comprehensive testing
- Documentation
- UI improvements

## Dependencies

**Required**:
- Existing LLM provider system
- SQLite database
- Python 3.10+

**New packages**:
- None (uses existing dependencies)

**LLM requirements**:
- Need decent context window (8K+ tokens)
- JSON mode support helpful but not required
- Works with: Claude, GPT-4, Gemini, local models (7B+)

## Configuration

**New settings in `config/llm.json`**:

```json
{
    "clustering": {
        "enabled": true,
        "story_similarity_threshold": 0.75,
        "max_active_stories": 100,
        "story_ttl_days": 30,
        "min_confidence": 0.7
    }
}
```

## Rollout Plan

1. **Alpha**: Test with developers
2. **Beta**: Opt-in flag for users
3. **GA**: Enabled by default with option to disable

## Success Criteria

- Successfully clusters 80%+ of related articles
- Identifies new information with 70%+ precision
- Story lifecycle states are accurate
- No significant performance degradation
- Users find the feature valuable (feedback)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-15
**Status**: Draft for Implementation
