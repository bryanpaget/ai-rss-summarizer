# Technical Specification: Adaptive Personal Context Engine

**Feature:** Issue #18 - Adaptive Personal Context Engine
**Version:** 1.0
**Status:** Draft
**Date:** 2025-12-15

## 1. Overview

The Adaptive Personal Context Engine is a system that learns user preferences over time to provide personalized article relevance scoring and filtering. It combines explicit user configuration with implicit behavioral learning to continuously improve recommendation quality.

## 2. Core Components

### 2.1 User Context Profile

The user context profile stores information about the user's interests, role, and current focus areas.

**Data Structure:**
```python
@dataclass
class UserContextProfile:
    """User's personal context for content filtering."""

    # Core identity
    role: Optional[str]  # e.g., "ML engineer at fintech startup"

    # Active interests
    current_projects: List[str]  # e.g., ["Fraud detection deployment"]
    watching: List[str]  # Topics to prioritize
    ignore: List[str]  # Topics to deprioritize
    pinned: List[str]  # Topics that never decay

    # Metadata
    created_at: datetime
    last_updated: datetime
    last_feedback_prompt: Optional[datetime]
```

**Storage Format:**
- Primary: JSON file at `config/user_context.json`
- Format: Human-readable, version-controlled
- Migration: Support schema versioning for future changes

### 2.2 Behavioral Tracking

Track user interactions with articles to learn implicit preferences.

**Tracked Behaviors:**
```python
@dataclass
class ArticleInteraction:
    """Record of user interaction with an article."""

    article_id: str
    timestamp: datetime

    # Interaction types
    expanded: bool  # User clicked to read more
    time_spent: Optional[float]  # Seconds spent reading
    saved: bool  # User saved for later
    shared: bool  # User shared the article
    skipped: bool  # User explicitly skipped

    # Feedback
    thumbs_up: Optional[bool]  # Explicit feedback
    relevance_score: Optional[float]  # 0-1, derived or explicit
```

**Storage:**
- SQLite table: `user_interactions`
- Indexed by: article_id, timestamp, interaction type
- Retention: Last 90 days (configurable)

### 2.3 Topic Relevance Scoring

Calculate personalized relevance scores for articles based on context.

**Scoring Algorithm:**

```python
def calculate_relevance_score(article: Article, context: UserContextProfile,
                               history: List[ArticleInteraction]) -> float:
    """
    Calculate relevance score (0-1) for an article.

    Factors:
    1. Topic match (40%): Does it match watching/current_projects?
    2. Historical engagement (30%): Similar articles engaged with before?
    3. Recency (15%): Recent topics get temporary boost
    4. Diversity (15%): Avoid filter bubbles, surface some new topics

    Returns:
        Float between 0 (not relevant) and 1 (highly relevant)
    """
    pass
```

**Topic Match Logic:**
- Exact match in `watching`: +0.4
- Match in `current_projects`: +0.4
- Related to active topics (semantic similarity): +0.2 to +0.3
- In `ignore` list: -0.5
- In `pinned` list: Always maintain base relevance of 0.3

**Historical Engagement:**
- Articles with similar tags that user engaged with: +0.3
- Similar articles user skipped: -0.2
- Topic engagement rate over last 30 days: weighted factor

**Recency Boost:**
- Topics engaged with in last 7 days: +0.15
- Topics engaged with 8-30 days ago: +0.1
- Decays exponentially after 30 days

**Diversity Factor:**
- 15% of shown articles should be from topics user hasn't seen
- Prevents filter bubbles
- Surfaces emerging interests

### 2.4 Relevance Decay

Topics naturally lose relevance over time unless actively engaged with.

**Decay Strategy:**
```python
class RelevanceDecay:
    """Manages automatic decay of topic relevance."""

    DECAY_HALF_LIFE = 14  # days

    def apply_decay(self, topic: str, last_interaction: datetime) -> float:
        """
        Apply exponential decay to topic relevance.

        - Topics not engaged with lose 50% relevance every 14 days
        - Pinned topics are immune to decay
        - Completed projects decay faster (7 day half-life)
        """
        pass
```

**Decay Rules:**
- Default decay: 50% every 14 days (exponential)
- Pinned topics: No decay
- Completed projects: 50% every 7 days (faster decay)
- Manual override: User can mark topics as "completed" or "archived"

### 2.5 Feedback Mechanisms

**Explicit Feedback:**

1. **Quick Reactions:**
   - Thumbs up/down on individual articles
   - "Not interested" button (adds to temporary ignore)
   - "More like this" button (boosts related topics)

2. **Periodic Check-ins:**
   - Weekly prompt: "How are these summaries? Still relevant?"
   - Shows engagement summary (what was marked high relevance vs. what was read)
   - Prompts to update profile if discrepancies detected

3. **Profile Editing:**
   - CLI command: `rss context edit`
   - Interactive editor for profile fields
   - Can add/remove topics, mark projects as complete

**Implicit Feedback:**

1. **Read vs. Skip Analysis:**
   - Track which articles user expands/reads
   - Track which articles user skips
   - Calculate engagement rate per topic

2. **Time-based Signals:**
   - Time spent reading (if measurable)
   - Time of day preferences (future enhancement)

3. **Search Behavior:**
   - If user searches for specific topics, boost those
   - Track which search results are clicked

## 3. Privacy & Data Protection

### 3.1 Privacy Principles

1. **Local-First:** All user data stored locally, never transmitted
2. **Transparent:** User can view all tracked data
3. **Controllable:** User can delete data at any time
4. **Minimal:** Only track what's necessary for personalization

### 3.2 Data Retention

- **User Profile:** Kept indefinitely (user-controlled)
- **Interaction History:** 90 days default (configurable)
- **Aggregated Stats:** Keep topic engagement summaries indefinitely
- **Deleted Articles:** Remove associated interactions after 30 days

### 3.3 Export & Deletion

```bash
# Export all user data
rss context export --output user_data.json

# Delete all personalization data
rss context clear --confirm

# Delete specific topic history
rss context forget "topic-name"
```

## 4. Integration Points

### 4.1 Summarization Flow Integration

Modified article processing pipeline:

```python
def process_articles_with_context(articles: List[Article],
                                   context: UserContextProfile) -> List[Article]:
    """
    Process articles with personalized relevance scoring.

    1. Generate summaries (existing flow)
    2. Calculate relevance scores (new)
    3. Sort by relevance (new)
    4. Apply diversity filter (new)
    5. Return personalized feed (new)
    """
    # Existing summarization
    summarized = summarize_articles(articles)

    # New: Add relevance scoring
    for article in summarized:
        article.relevance_score = calculate_relevance_score(
            article, context, get_user_history()
        )

    # New: Sort by relevance
    sorted_articles = sort_by_relevance(summarized)

    # New: Apply diversity filter
    diverse_articles = apply_diversity_filter(sorted_articles, context)

    return diverse_articles
```

### 4.2 CLI Integration

New commands:

```bash
# Initialize user context
rss context init

# Edit context profile
rss context edit

# Show current context
rss context show

# View engagement statistics
rss context stats

# Manage topics
rss context pin "AI regulation"
rss context unpin "crypto"
rss context ignore "celebrity tech"
rss context watch "embedding models"

# Feedback
rss context feedback --weekly  # Trigger weekly check-in
rss context clear-history       # Clear interaction history

# Export/Import
rss context export user_data.json
rss context import user_data.json
```

### 4.3 Update Command Integration

Modified `rss update` command:

```bash
# Show articles with relevance scores
rss update --show-scores

# Filter by minimum relevance threshold
rss update --min-relevance 0.7

# Show why articles are relevant
rss update --explain-relevance

# Disable personalization temporarily
rss update --no-context
```

## 5. Implementation Plan

### Phase 1: Core Storage (Week 1)

- [ ] Implement `UserContextProfile` data class
- [ ] Create JSON storage for user profile
- [ ] Implement `ArticleInteraction` data class
- [ ] Add SQLite table for interactions
- [ ] Write basic CRUD operations

### Phase 2: Scoring Engine (Week 2)

- [ ] Implement topic matching logic
- [ ] Build relevance scoring algorithm
- [ ] Add decay calculations
- [ ] Implement diversity filter
- [ ] Add unit tests for scoring

### Phase 3: Integration (Week 3)

- [ ] Integrate with summarization flow
- [ ] Modify storage to include relevance scores
- [ ] Update article display to show scores
- [ ] Add sorting/filtering by relevance

### Phase 4: CLI Commands (Week 4)

- [ ] Implement `rss context init`
- [ ] Implement `rss context edit`
- [ ] Implement `rss context show`
- [ ] Implement topic management commands
- [ ] Implement feedback commands

### Phase 5: Feedback Loop (Week 5)

- [ ] Implement interaction tracking
- [ ] Add quick reaction buttons (if UI available)
- [ ] Build weekly feedback prompt
- [ ] Implement automatic profile updates based on behavior

### Phase 6: Polish & Testing (Week 6)

- [ ] Add comprehensive tests
- [ ] Performance optimization
- [ ] Documentation
- [ ] User guide

## 6. Edge Cases & Error Handling

### 6.1 Cold Start Problem

**Issue:** New users have no interaction history.

**Solutions:**
1. Default to trend-based scoring for first 2 weeks
2. Prompt for initial interests during setup
3. Gradually transition from trend-based to personalized as data accumulates
4. Show "bootstrapping" indicator to user

### 6.2 Topic Drift

**Issue:** User interests change over time, old data becomes stale.

**Solutions:**
1. Apply time-based decay to all interactions
2. Weight recent interactions more heavily (last 30 days = 70% of weight)
3. Periodic prompts to review and update profile
4. Automatic detection of engagement pattern changes

### 6.3 Filter Bubble

**Issue:** Over-personalization creates echo chamber.

**Solutions:**
1. Always include 15% diverse content (topics user hasn't seen)
2. Periodic "What's Trending" section that ignores personalization
3. Surface counter-narratives and contested views
4. Allow user to adjust personalization strength (slider: 0-100%)

### 6.4 Data Corruption

**Issue:** Profile or interaction data becomes corrupted.

**Solutions:**
1. Schema validation on load
2. Automatic backups (keep last 7 versions)
3. Graceful degradation (fall back to default behavior)
4. Clear error messages with recovery instructions

### 6.5 Migration & Versioning

**Issue:** Schema changes require data migration.

**Solutions:**
1. Version field in all data structures
2. Migration scripts for each version transition
3. Automatic detection and migration on load
4. Backup before migration
5. Rollback capability

### 6.6 Performance at Scale

**Issue:** Relevance calculation might be slow for large article sets.

**Solutions:**
1. Cache relevance scores (invalidate after 1 hour)
2. Batch processing for large feeds
3. Lazy evaluation (calculate only for displayed articles)
4. Pre-filter by trend before personalization
5. Asynchronous processing for non-critical updates

## 7. Metrics & Success Criteria

### 7.1 User Engagement Metrics

- **Read Rate:** % of shown articles that user reads (target: +20% vs. baseline)
- **Time Saved:** Reduction in time to find relevant articles (target: -30%)
- **Satisfaction:** Weekly feedback ratings (target: 4.0/5.0)

### 7.2 System Performance Metrics

- **Scoring Latency:** Time to calculate relevance (target: <100ms per article)
- **Update Latency:** Time to update after user action (target: <50ms)
- **Storage Size:** Disk usage for user data (target: <10MB per user)

### 7.3 Quality Metrics

- **Precision:** % of high-relevance articles that user reads (target: >70%)
- **Recall:** % of user-read articles that were marked high-relevance (target: >60%)
- **Diversity:** % of topics covered in top recommendations (target: >5 topics)

## 8. Future Enhancements

### 8.1 Advanced Learning (v2.0)

- Machine learning model for relevance prediction
- Cross-user collaborative filtering (with privacy protections)
- Semantic topic extraction using embeddings
- Multi-dimensional preferences (not just topics)

### 8.2 Social Features (v2.0)

- Share curated feeds with team
- Team context (shared projects/interests)
- Expert following (learn from others' reading patterns)

### 8.3 Integration Expansion (v3.0)

- Browser extension for read tracking
- Mobile app for on-the-go feedback
- Calendar integration (boost topics related to upcoming meetings)
- Email integration (learn from newsletters)

## 9. Dependencies

### 9.1 Required

- Python 3.9+
- SQLite 3.35+
- Existing storage module
- Existing LLM providers

### 9.2 Optional

- `scikit-learn` for advanced ML features (future)
- `sentence-transformers` for semantic similarity (future)

## 10. Testing Strategy

### 10.1 Unit Tests

- Profile CRUD operations
- Relevance scoring calculations
- Decay algorithm
- Interaction tracking

### 10.2 Integration Tests

- End-to-end flow: article fetch → scoring → display
- CLI command execution
- Data migration
- Export/import

### 10.3 User Testing

- Cold start experience
- Feedback loop effectiveness
- Profile management usability
- Performance with real-world data

## 11. Documentation Deliverables

1. **User Guide:** How to use context features
2. **CLI Reference:** All new commands documented
3. **Architecture Doc:** System design and data flow
4. **Privacy Policy:** What data is collected and how it's used
5. **Migration Guide:** Upgrading from non-personalized version

## 12. Acceptance Criteria (from Issue #18)

- [x] User can create/edit context profile → `rss context init/edit`
- [x] Articles scored for personal relevance → Relevance scoring engine
- [x] System prompts for periodic feedback → Weekly check-in command
- [x] Implicit learning from read/skip behavior → Interaction tracking
- [x] Relevance decay for stale topics → Decay algorithm
- [x] Pin feature to prevent decay → Pinned topics list

## 13. Open Questions

1. **UI for Feedback:** Command-line only, or build TUI/web interface?
   - Decision: Start with CLI, add TUI in v2.0

2. **Relevance Threshold:** What's the minimum score to show an article?
   - Decision: User-configurable, default 0.3

3. **Decay Parameters:** Are 14-day and 7-day half-lives appropriate?
   - Decision: Make configurable, these are defaults

4. **Diversity Balance:** Is 15% the right amount of diverse content?
   - Decision: Start with 15%, make configurable

5. **Cold Start Duration:** How long before switching from trend to personal?
   - Decision: Smooth transition over 2 weeks, weighted by data quantity
