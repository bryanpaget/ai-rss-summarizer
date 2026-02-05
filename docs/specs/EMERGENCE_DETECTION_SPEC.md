# Emergence Detection - Technical Specification

**Feature**: Issue #19 - Emergence Detection
**Status**: Draft
**Author**: AI Implementation
**Date**: 2025-12-15

## Overview

Emergence Detection tracks weak signals before they become mainstream trends. This feature identifies new terminology, cross-domain connections, and acceleration patterns that indicate topics moving from niche to widespread adoption.

## Core Concept

An "emerging" trend is defined by:
1. **Low historical baseline**: Few or no mentions in older data
2. **Recent acceleration**: Significant increase in recent mentions
3. **Velocity**: Rate of change is positive and significant
4. **Cross-domain appearance**: Shows up in multiple categories or contexts
5. **Trajectory**: Patterns suggest continued growth

## Detection Algorithm

### 1. Term Frequency Analysis

Track frequency of terms/phrases over multiple time windows:

```python
Time Windows:
- Current week (0-7 days)
- Previous week (7-14 days)
- 2 weeks ago (14-21 days)
- 1 month ago (21-28 days)
- 2 months ago (28-60 days)
```

**Emerging Signal**: When a term shows:
- 0-2 mentions in 2+ month window
- 3+ mentions in current week
- Progressive increase across windows (1 → 2 → 5 → 8)

### 2. Velocity Calculation

Velocity measures rate of change in mentions:

```python
velocity = (current_period - previous_period) / previous_period * 100

Thresholds:
- Emerging: velocity > 100% AND current_mentions >= 3
- Accelerating: velocity > 50% AND current_mentions >= 8
- Mainstream: velocity < 20% AND current_mentions > 20
```

### 3. Cross-Domain Detection

Track which trend categories mention each term:

```python
domains_seen = {
    "Constitutional AI": ["AI & Technology", "Science & Research"],
    "Mixture of Experts": ["AI & Technology", "Business & Economy"]
}

Cross-domain signal: term appears in 2+ categories within same time window
```

### 4. Trajectory Prediction

Classify trajectory based on historical pattern:

- **Research → Blogs**: Started in Science, now in AI & Technology
- **Blogs → Mainstream**: Started in AI & Technology, now in Business & Economy
- **Technical → General**: Started with technical articles, now in general news
- **Niche → Widespread**: Started in single domain, now multi-domain

### 5. Expert Pivot Detection

Track when known sources/authors change focus:

```python
author_topics = {
    "techcrunch.com": {
        "previous_month": ["startups", "funding", "ipo"],
        "current_month": ["constitutional AI", "ai safety"]
    }
}

Pivot signal: > 30% of recent articles from source cover new topics
```

## Historical Data Requirements

### Database Schema Extension

Add new table for term tracking:

```sql
CREATE TABLE term_history (
    id INTEGER PRIMARY KEY,
    term TEXT NOT NULL,
    week_bucket TEXT NOT NULL,  -- ISO week: "2025-W50"
    mention_count INTEGER DEFAULT 1,
    article_ids TEXT,  -- JSON array of article IDs
    categories TEXT,   -- JSON array of categories seen
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(term, week_bucket)
);

CREATE INDEX idx_term_history_term ON term_history(term);
CREATE INDEX idx_term_history_week ON term_history(week_bucket);
```

### Data Collection

- Extract key terms from articles (2-4 word phrases)
- Filter stopwords and common terms
- Store weekly aggregates
- Maintain at least 8 weeks of history for meaningful trends

### Term Extraction Strategy

```python
1. Use existing article content and titles
2. Extract noun phrases (2-4 words)
3. Filter by:
   - Not in common stopwords
   - Capitalized or technical terms preferred
   - Present in at least 2 articles
4. Store with normalized form (lowercase for matching)
```

## Thresholds and Tuning Parameters

### Detection Thresholds

```python
EMERGENCE_CONFIG = {
    # Minimum mentions to be considered
    "min_current_mentions": 3,
    "min_historical_mentions": 0,
    "max_historical_mentions": 2,

    # Velocity thresholds
    "emerging_velocity": 100,  # % change
    "accelerating_velocity": 50,
    "mainstream_velocity": 20,

    # Time windows (days)
    "current_window": 7,
    "comparison_windows": [7, 14, 28, 60],

    # Cross-domain detection
    "min_domains_for_cross": 2,
    "min_articles_per_domain": 1,

    # Trajectory prediction
    "min_weeks_for_trajectory": 3,

    # Expert pivot
    "pivot_threshold": 0.3,  # 30% topic change
}
```

### Confidence Levels

Assign confidence to predictions:

```python
Confidence = "High" if:
    - velocity > 150%
    - current_mentions >= 5
    - seen in 3+ domains
    - consistent growth over 3+ weeks

Confidence = "Medium" if:
    - velocity > 100%
    - current_mentions >= 3
    - seen in 2+ domains

Confidence = "Low" if:
    - velocity > 50%
    - current_mentions >= 3
    - single domain
```

## User Presentation

### CLI Output Format

```
EMERGING TRENDS
═══════════════════════════════════════════════════════════

HIGH CONFIDENCE

"Constitutional AI" (12 mentions, up from 1 two months ago)
  Velocity: +1100%
  Trajectory: Research → Technical Blogs → Mainstream
  Domains: AI & Technology, Science & Research, Business
  Time to peak: ~2-4 months
  Action: Learn now before it's everywhere

  Recent articles:
    - "Constitutional AI: A New Approach..." (Dec 12)
    - "Anthropic Releases Claude with..." (Dec 10)
    - "The Business Case for Constitutional..." (Dec 8)


MEDIUM CONFIDENCE

"Mixture of Experts" (8 mentions, up from 2 last month)
  Velocity: +300%
  Trajectory: Technical → Mainstream adoption
  Domains: AI & Technology, Business & Economy
  Status: Entering mainstream adoption
  Action: If unfamiliar, prioritize learning

  Context: Related to existing trend "Large Language Models"


WATCH LIST (Early Signals)

"Agentic Workflows" (4 mentions, first seen this week)
  Status: New terminology emerging
  Domain: AI & Technology
  Note: Too early to assess trajectory
```

### API/Data Structure

```python
@dataclass
class EmergingTrend:
    term: str
    current_mentions: int
    historical_mentions: dict[str, int]  # {week: count}
    velocity: float
    confidence: str  # "High", "Medium", "Low"
    trajectory: str
    domains: list[str]
    time_to_peak_estimate: Optional[str]
    action_recommendation: str
    recent_article_ids: list[str]
    related_trends: list[str]
```

## Edge Cases and Error Handling

### 1. Insufficient Historical Data

**Problem**: New installation with < 4 weeks data

**Solution**:
- Gracefully degrade to "Watch List" only
- Show message: "Building historical baseline. Full emergence detection available after 4 weeks."
- Still track terms but don't calculate velocity

### 2. Flash-in-the-Pan Detection

**Problem**: One-time event causes spike, not a trend

**Solution**:
- Require growth over multiple windows, not just one spike
- Check if mentions drop off after spike
- Filter events tied to single news story

### 3. Seasonal/Periodic Patterns

**Problem**: Term appears cyclically (e.g., "tax season")

**Solution**:
- Compare to same period in previous cycle if data available
- Identify if velocity is unusual for this time period
- Mark as "Seasonal" vs "Emerging"

### 4. Name Collisions

**Problem**: Same term, different meanings ("apple" the fruit vs. company)

**Solution**:
- Use context from article categories
- Prefer terms with consistent category association
- Flag ambiguous terms for manual review

### 5. Data Quality Issues

**Problem**: Malformed dates, missing content, spam articles

**Solution**:
```python
- Skip articles with missing published dates
- Validate term extraction results
- Filter terms that appear in > 50% of articles (too generic)
- Minimum article quality threshold (has content, valid URL)
```

### 6. Performance with Large Datasets

**Problem**: Scanning thousands of articles is slow

**Solution**:
- Index term_history table by term and week
- Cache recent calculations (TTL: 1 hour)
- Limit analysis to recent N articles (default: 1000)
- Background processing for expensive calculations

### 7. False Positives

**Problem**: Generic terms flagged as emerging

**Solution**:
- Maintain stoplist of common terms
- Require minimum specificity (2+ words for technical terms)
- Weight by article quality/source reputation
- User can dismiss/hide false positives

## Integration Points

### With Existing Trend Analysis

```python
# In trends.py
from .emergence import detect_emerging_trends

def analyze_trends(storage, limit=100, hours=24):
    # ... existing code ...

    # Add emergence detection
    emerging = detect_emerging_trends(storage)

    return {
        "processed": processed,
        "top_trends": top_trends,
        "emerging": emerging,  # New enhanced format
        # ... other fields ...
    }
```

### With Storage Layer

```python
# New methods in storage.py
class Storage:
    def save_term_mention(self, term: str, week: str, article_id: str, category: str):
        """Record a term mention in the history."""

    def get_term_history(self, term: str, weeks_back: int = 8) -> dict:
        """Get historical mention data for a term."""

    def get_all_terms_with_history(self, min_weeks: int = 4) -> list:
        """Get all terms with sufficient history for analysis."""
```

### With CLI

```python
# New command in cli.py
@app.command()
def emerging(
    confidence: str = typer.Option("all", help="Filter by confidence: high, medium, low, all"),
    limit: int = typer.Option(10, help="Number of trends to show"),
):
    """Show emerging trends before they go mainstream."""
```

## Testing Strategy

### Unit Tests

```python
test_emergence.py:
- test_velocity_calculation()
- test_cross_domain_detection()
- test_trajectory_classification()
- test_insufficient_data_handling()
- test_term_extraction()
- test_confidence_assignment()
```

### Integration Tests

```python
- test_full_pipeline_with_mock_data()
- test_database_integration()
- test_cli_output_formatting()
```

### Test Data Requirements

```python
# Mock historical data with known patterns
articles = [
    # Week 1: 1 mention of "Constitutional AI"
    # Week 2: 1 mention
    # Week 3: 3 mentions
    # Week 4: 8 mentions (should trigger "emerging")
]
```

## Implementation Phases

### Phase 1: Core Detection (MVP)
- [ ] Database schema for term_history
- [ ] Term extraction from articles
- [ ] Basic velocity calculation
- [ ] Simple CLI output

### Phase 2: Enhanced Analysis
- [ ] Cross-domain detection
- [ ] Trajectory classification
- [ ] Confidence scoring
- [ ] Rich CLI output with recommendations

### Phase 3: Advanced Features
- [ ] Expert pivot detection
- [ ] Time-to-peak estimation
- [ ] Related trend clustering
- [ ] Historical comparison

## Success Metrics

Feature is successful if:
1. Detects emerging terms 2-4 weeks before mainstream adoption
2. False positive rate < 20%
3. User can act on recommendations (clear, actionable)
4. Performance: < 2 seconds for emergence analysis
5. Works with as little as 4 weeks of data

## Future Enhancements

- Machine learning for better trajectory prediction
- Sentiment analysis on emerging trends
- Integration with external trend data (Google Trends, etc.)
- User feedback loop to improve detection
- Personalized emergence (based on user interests)
- Email/notification system for high-confidence emerging trends
