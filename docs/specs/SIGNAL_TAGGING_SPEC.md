# Signal Tagging System - Technical Specification

**Feature**: Issue #16 - Signal Tagging System
**Status**: Implementation Specification
**Date**: 2025-12-15

## Overview

Replace numeric signal scores with descriptive tags that communicate actual article qualities. This provides more intuitive and actionable signals for filtering and understanding article value.

## Problem Statement

Single numeric scores (e.g., "Evidence: 85/100") fail to communicate meaning intuitively:
- What does "85" mean? High quality? High quantity? High confidence?
- Numbers lose semantic content and require mental translation
- Different dimensions (source quality, reasoning, tone) are collapsed into single numbers
- Users can't easily filter for specific qualities they care about

## Solution: Descriptive Tags

Use multi-dimensional tags that directly communicate article qualities across five categories: Source Type, Evidence Handling, Reasoning Quality, Tone/Style, and Actionability.

## Tag Categories

### 1. Source Type
Indicates the nature and originality of the reporting.

- `primary` - Original reporting with first-hand sources
- `secondary` - Reporting based on other reports
- `aggregator` - Compiled from multiple sources
- `press-release` - Corporate/official announcement
- `speculative` - Based on rumors/unnamed sources
- `satirical` - Intentionally humorous/exaggerated

**Detection Logic**: Analyze article for:
- Direct quotes and eyewitness accounts (primary)
- References to other news organizations (secondary)
- Multiple source citations (aggregator)
- Corporate/official language patterns (press-release)
- "Sources say", "rumored", "possibly" (speculative)
- Known satire domains or obvious humor markers (satirical)

### 2. Evidence Handling
Evaluates how claims are supported.

- `well-sourced` - Multiple named sources cited
- `single-source` - One primary source only
- `anonymous-sources` - Unnamed insiders cited
- `documented` - Links to primary documents/data
- `unverified` - Claims without backing

**Detection Logic**: Count and analyze:
- Named individuals or organizations cited
- Links to source documents
- Use of "according to", "sources say", "anonymous official"
- Presence of data, studies, or reports
- Unsupported assertion patterns

### 3. Reasoning Quality
Assesses logical structure and argumentation.

- `logical` - Sound deductions from evidence
- `non-sequitur` - Conclusions don't follow from premises
- `cherry-picked` - Selective evidence use
- `balanced` - Multiple perspectives considered

**Detection Logic**: Look for:
- Clear cause-effect relationships (logical)
- Logical leaps or gaps (non-sequitur)
- One-sided presentation, ignored counterpoints (cherry-picked)
- "However", "on the other hand", multiple viewpoints (balanced)

### 4. Tone/Style
Characterizes writing approach.

- `factual` - Neutral, just-the-facts reporting
- `analytical` - Deep analysis with reasoning
- `opinion` - Clearly editorial/subjective
- `sensational` - Clickbait/hype language
- `spicy` - Hot takes, provocative (entertainment)
- `unhinged` - Wild speculation, extreme (entertainment)

**Detection Logic**: Analyze for:
- Neutral language, attribution patterns (factual)
- Complex reasoning, "because", "therefore" (analytical)
- First-person, "I believe", editorial markers (opinion)
- Exclamation marks, superlatives, "shocking" (sensational)
- Strong language, provocative framing (spicy)
- Extreme claims, conspiracy patterns (unhinged)

### 5. Actionability
Indicates practical value.

- `actionable` - Contains information you can act on
- `awareness` - Good to know, no action needed
- `noise` - No signal value

**Detection Logic**: Look for:
- How-tos, deadlines, specific recommendations (actionable)
- Context, background, general knowledge (awareness)
- Pure entertainment, gossip, speculation (noise)

## Data Structures

### Article Storage Schema (Existing)

The `articles` table already has a `trend_tags` TEXT field. We'll repurpose or extend this for signal tags:

```python
@dataclass
class Article:
    id: str
    feed_url: str
    title: str
    link: str
    published: Optional[datetime]
    content: str
    summary: Optional[str] = None
    trend_tags: Optional[str] = None  # JSON string of tags
    signal_tags: Optional[str] = None  # New field for signal tags
    created_at: Optional[datetime] = None
```

**Storage Format**: JSON string containing tag dictionary:
```json
{
  "source_type": ["primary"],
  "evidence": ["well-sourced", "documented"],
  "reasoning": ["balanced"],
  "tone": ["analytical"],
  "actionability": ["actionable"]
}
```

### Signal Tag Class

```python
@dataclass
class SignalTags:
    source_type: list[str]
    evidence: list[str]
    reasoning: list[str]
    tone: list[str]
    actionability: list[str]

    def to_json(self) -> str:
        """Serialize to JSON string for storage."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> 'SignalTags':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(**data)

    def to_display_string(self) -> str:
        """Format tags for display: [primary] [well-sourced] [balanced]"""
        all_tags = (
            self.source_type + self.evidence +
            self.reasoning + self.tone + self.actionability
        )
        return " ".join(f"[{tag}]" for tag in all_tags)

    def has_any_tag(self, *tags: str) -> bool:
        """Check if any of the given tags are present."""
        all_tags = (
            self.source_type + self.evidence +
            self.reasoning + self.tone + self.actionability
        )
        return any(tag in all_tags for tag in tags)
```

## Detection Algorithms

### Option 1: Rule-Based Pattern Matching (Fast, No LLM Required)

Use keyword and pattern matching for tag detection:

```python
PATTERNS = {
    "source_type": {
        "primary": [
            r"\b(witnessed|saw|spoke with|interviewed)\b",
            r"\b(at the scene|on location|first-hand)\b",
        ],
        "secondary": [
            r"\b(according to .+? reported)\b",
            r"\breported by\b",
        ],
        "speculative": [
            r"\b(rumored|possibly|might|could|allegedly)\b",
            r"\bsources? say\b",
        ],
    },
    "evidence": {
        "well-sourced": lambda text: count_named_sources(text) >= 3,
        "documented": [
            r"\b(study|report|document|paper) (shows|reveals|indicates)\b",
            r"http[s]?://\S+\.(pdf|gov|edu)",
        ],
        "anonymous-sources": [
            r"\b(anonymous source|unnamed official|sources familiar)\b",
        ],
    },
    # ... more patterns
}
```

**Pros**: Fast, deterministic, no API costs
**Cons**: Less nuanced, requires maintenance

### Option 2: LLM-Based Detection (Accurate, Context-Aware)

Use LLM with structured prompt for tag assignment:

```python
TAGGING_PROMPT = """Analyze this article and assign appropriate tags from each category.

Article Title: {title}
Article Content: {content}

Tag Categories:
- Source Type: primary, secondary, aggregator, press-release, speculative, satirical
- Evidence: well-sourced, single-source, anonymous-sources, documented, unverified
- Reasoning: logical, non-sequitur, cherry-picked, balanced
- Tone: factual, analytical, opinion, sensational, spicy, unhinged
- Actionability: actionable, awareness, noise

Assign 1-2 tags per category that best describe the article.

Return ONLY a JSON object in this format:
{{
  "source_type": ["tag1"],
  "evidence": ["tag1", "tag2"],
  "reasoning": ["tag1"],
  "tone": ["tag1"],
  "actionability": ["tag1"]
}}
"""
```

**Pros**: More accurate, context-aware, handles nuance
**Cons**: Slower, requires LLM API/service

### Option 3: Hybrid Approach (Recommended)

1. Use rule-based patterns for obvious cases (press-release, satirical domains)
2. Use LLM for nuanced judgment (reasoning quality, tone)
3. Cache results aggressively

## Integration with Existing System

### 1. Storage Layer Updates

Add `signal_tags` column to articles table:

```python
# In storage.py _init_db()
conn.execute("""
    ALTER TABLE articles
    ADD COLUMN signal_tags TEXT
""")
```

Add methods:
```python
def update_signal_tags(self, article_id: str, tags: SignalTags) -> None:
    """Update an article's signal tags."""
    with self._connect() as conn:
        conn.execute(
            "UPDATE articles SET signal_tags = ? WHERE id = ?",
            (tags.to_json(), article_id),
        )
        conn.commit()

def get_articles_by_tags(
    self,
    include_tags: list[str] = None,
    exclude_tags: list[str] = None,
    limit: int = 50
) -> list[Article]:
    """Get articles filtered by signal tags."""
    # Implementation uses JSON queries or post-filtering
```

### 2. Signal Tagger Module

Create `src/signal_tagger.py`:

```python
class SignalTagger:
    """Assigns signal tags to articles."""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        if use_llm:
            from .llm_providers import get_best_provider
            self.provider, _ = get_best_provider()

    def tag_article(self, article: Article) -> SignalTags:
        """Assign signal tags to an article."""
        if self.use_llm:
            return self._tag_with_llm(article)
        else:
            return self._tag_with_rules(article)

    def tag_articles_batch(
        self,
        articles: list[Article],
        show_progress: bool = True
    ) -> dict[str, SignalTags]:
        """Tag multiple articles, return mapping of id -> tags."""
        # Batch processing with progress indication
```

### 3. Summarization Flow Integration

Update `summarize_articles()` to also tag:

```python
def summarize_articles(
    storage,
    limit: int = 10,
    use_llm: bool = False,
    tag_articles: bool = True,  # New parameter
) -> dict:
    """Summarize and optionally tag articles."""
    summarizer = get_summarizer(use_llm)
    tagger = SignalTagger(use_llm) if tag_articles else None

    articles = storage.get_articles(limit=limit, unsummarized_only=True)

    for article in articles:
        # Generate summary
        summary = summarizer.summarize(article.content)
        storage.update_summary(article.id, summary)

        # Generate tags
        if tagger:
            tags = tagger.tag_article(article)
            storage.update_signal_tags(article.id, tags)
```

### 4. CLI Commands

Add new commands:

```bash
# Tag existing articles
rss tag-articles --limit 50 --use-llm

# List with tag filters
rss list --with-tags primary,documented --without-tags press-release

# Show tag distribution
rss tag-stats
```

Implementation in `cli.py`:

```python
@app.command()
def tag_articles(
    limit: int = typer.Option(50, "--limit", "-n"),
    use_llm: bool = typer.Option(True, "--llm"),
):
    """Assign signal tags to articles."""
    # Implementation

@app.command("list")
def list_articles(
    # ... existing params ...
    with_tags: Optional[str] = typer.Option(None, "--with-tags"),
    without_tags: Optional[str] = typer.Option(None, "--without-tags"),
):
    """List articles with tag filtering."""
    # Implementation
```

## User-Defined Tag Filters

Store user preferences in config file:

```json
// config/tag_filters.json
{
  "presets": {
    "serious-research": {
      "include": ["primary", "documented", "well-sourced", "balanced"],
      "exclude": ["press-release", "speculative", "sensational"]
    },
    "entertainment": {
      "include": ["spicy", "unhinged"],
      "exclude": []
    },
    "actionable-only": {
      "include": ["actionable"],
      "exclude": ["noise"]
    }
  },
  "default": "serious-research"
}
```

CLI usage:
```bash
rss list --preset serious-research
rss list --preset entertainment
```

## Error Handling

### LLM Tagging Failures
- Retry with exponential backoff (3 attempts)
- Fall back to rule-based tagging
- Log failures for review
- Mark articles as "untagged" vs "tag-failed"

### Invalid JSON Responses
- Validate LLM response structure
- Use default tags for missing categories
- Log malformed responses

### Database Issues
- Handle missing signal_tags column gracefully
- Provide migration helper

## Edge Cases

1. **Satirical Content Misidentified as Real**
   - Maintain whitelist of known satire domains
   - Look for satire indicators in text
   - Allow manual override

2. **Mixed-Quality Articles**
   - Allow multiple tags per category (e.g., both "documented" and "anonymous-sources")
   - Display all applicable tags

3. **Language Barriers**
   - Initially support English only
   - Detect non-English content and skip or use language-specific patterns

4. **Very Short Articles**
   - Minimum content length requirement (100 chars)
   - Default to conservative tags (e.g., "secondary", "awareness")

5. **Tag Ambiguity**
   - Some articles legitimately fit multiple categories
   - Prioritize most distinctive/useful tags
   - Display top 2 per category max

## Testing Strategy

### Unit Tests
- Test pattern matching for each tag category
- Test SignalTags serialization/deserialization
- Test tag filtering logic

### Integration Tests
- Test full tagging pipeline on sample articles
- Test storage integration
- Test CLI commands

### Manual Testing
- Tag 20 diverse articles
- Verify tag accuracy and usefulness
- Test filter combinations
- Validate display formatting

### Test Data
Create `tests/fixtures/sample_articles.json` with diverse examples:
- Tech press release
- Investigative journalism
- Opinion piece
- Satirical article
- Sensational clickbait

## Performance Considerations

### LLM Tagging
- Batch requests where possible (10-20 articles per batch)
- Cache LLM responses (article hash -> tags)
- Rate limiting to avoid API quota issues
- Estimated: ~2-5 seconds per article with LLM

### Rule-Based Tagging
- Pre-compile regex patterns
- Estimated: <100ms per article

### Database Queries
- Index signal_tags column for filtering
- Consider JSON column type for better querying (SQLite 3.38+)

## Metrics & Monitoring

Track:
- Tag distribution across corpus
- Most/least common tags
- Tag combination patterns
- User filter preferences
- Tagging failures and causes

Display in `rss tag-stats`:
```
Signal Tag Statistics (1000 articles)

Source Type:
  secondary      █████████████████░░░  520 (52%)
  primary        ██████████░░░░░░░░░░  310 (31%)
  aggregator     ████░░░░░░░░░░░░░░░░  120 (12%)
  press-release  ██░░░░░░░░░░░░░░░░░░   50 (5%)

Most Common Combinations:
  [secondary] [well-sourced] [factual]           180 articles
  [primary] [documented] [analytical]            120 articles
  [secondary] [anonymous-sources] [speculative]   95 articles
```

## Future Enhancements

1. **Machine Learning Model**
   - Train custom classifier on tagged corpus
   - Faster than LLM, more accurate than rules

2. **Tag Confidence Scores**
   - Include confidence level with each tag
   - "probably_satirical" vs "definitely_satirical"

3. **Temporal Tag Analysis**
   - Track tag distribution over time
   - Detect shifts in media coverage patterns

4. **Source Reputation Tracking**
   - Learn which sources typically have which tags
   - Pre-tag based on source patterns

5. **User Feedback Loop**
   - Allow users to correct tags
   - Use corrections to improve tagging

## Migration Plan

### Phase 1: Database Schema
1. Add signal_tags column to articles table
2. Create migration script for existing installations

### Phase 2: Core Implementation
1. Implement SignalTags class and serialization
2. Implement rule-based tagger
3. Add storage methods for tag CRUD

### Phase 3: LLM Integration
1. Implement LLM-based tagger
2. Add fallback logic
3. Add caching

### Phase 4: CLI & UX
1. Add tag-articles command
2. Add tag filtering to list command
3. Add tag-stats command
4. Update update command to include tagging

### Phase 5: User Preferences
1. Implement preset system
2. Add tag filter configuration
3. Add filter builder UI (future)

## Success Criteria

1. **Accuracy**: Tags correctly describe article qualities in 80%+ of cases
2. **Performance**: Tagging adds <5 seconds per article (LLM mode)
3. **Usability**: Users can easily filter to find desired content types
4. **Adoption**: Tag-based filtering is used in 50%+ of list queries
5. **Coverage**: 90%+ of articles successfully tagged without errors

## References

- Issue #16: Signal Tagging System
- docs/TREND_ANALYSIS_FEATURES.md: Original feature specification
- src/trends.py: Existing trend categorization system (to be extended/replaced)
