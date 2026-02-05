# Knowledge Extraction & Accumulation - Technical Specification

## Overview

This feature builds a queryable personal knowledge base from articles that users read through the RSS summarizer. It extracts structured insights, detects connections to existing knowledge, identifies contradictions, and provides a natural language interface for querying accumulated learnings.

## Design Principles

Following the KB Philosophy (from TREND_ANALYSIS_FEATURES.md):
- **Uncertainty Reduction**: Provide confidence levels for all extracted knowledge
- **Back-propagation**: Learning compounds over time through accumulated insights
- **Specifics Matter**: Track concrete facts, not generic categories
- **Full Understanding**: Clearly separate what's certain, contested, and unknown

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Summarization Flow                       │
│  (fetch → summarize → analyze trends → EXTRACT KNOWLEDGE)   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Knowledge Extractor                         │
│  - Extracts facts, tools, learnings from articles          │
│  - Assigns confidence levels                                │
│  - Detects entity mentions (tools, people, companies)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Knowledge Storage                          │
│  - SQLite database with knowledge graph structure          │
│  - Tracks: insights, entities, relationships, sources      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│               Connection Detector                           │
│  - Links new knowledge to existing insights                │
│  - Identifies contradictions and confirmations             │
│  - Tracks knowledge evolution over time                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Query Interface                            │
│  - Natural language queries                                │
│  - Aggregates insights from multiple sources               │
│  - Surfaces contradictions and confidence levels           │
└─────────────────────────────────────────────────────────────┘
```

## Data Model

### Database Schema

```sql
-- Core knowledge insights table
CREATE TABLE knowledge_insights (
    id TEXT PRIMARY KEY,
    article_id TEXT NOT NULL,
    content TEXT NOT NULL,              -- The actual insight/learning
    insight_type TEXT NOT NULL,         -- 'technical', 'tool', 'statistic', 'opinion'
    confidence TEXT NOT NULL,           -- 'high', 'medium', 'low'
    confidence_reason TEXT,             -- Why this confidence level?
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

-- Entities mentioned in articles (tools, people, companies, concepts)
CREATE TABLE knowledge_entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL,          -- 'tool', 'person', 'company', 'concept'
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mention_count INTEGER DEFAULT 1
);

-- Link insights to entities
CREATE TABLE insight_entities (
    insight_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    relevance TEXT,                     -- How central is this entity to the insight?
    PRIMARY KEY (insight_id, entity_id),
    FOREIGN KEY (insight_id) REFERENCES knowledge_insights(id),
    FOREIGN KEY (entity_id) REFERENCES knowledge_entities(id)
);

-- Relationships between insights (confirmations, contradictions, refinements)
CREATE TABLE knowledge_relationships (
    id TEXT PRIMARY KEY,
    source_insight_id TEXT NOT NULL,
    target_insight_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,    -- 'confirms', 'contradicts', 'refines', 'extends'
    strength REAL DEFAULT 1.0,          -- 0.0 to 1.0 - how strong is this relationship?
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_insight_id) REFERENCES knowledge_insights(id),
    FOREIGN KEY (target_insight_id) REFERENCES knowledge_insights(id)
);

-- User's personal context (projects, interests, active work)
CREATE TABLE user_context (
    id TEXT PRIMARY KEY,
    context_type TEXT NOT NULL,         -- 'project', 'interest', 'watching'
    name TEXT NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link insights to user context
CREATE TABLE insight_context (
    insight_id TEXT NOT NULL,
    context_id TEXT NOT NULL,
    relevance_score REAL DEFAULT 0.5,   -- How relevant is this insight to this context?
    PRIMARY KEY (insight_id, context_id),
    FOREIGN KEY (insight_id) REFERENCES knowledge_insights(id),
    FOREIGN KEY (context_id) REFERENCES user_context(id)
);

-- Indexes for efficient queries
CREATE INDEX idx_insights_type ON knowledge_insights(insight_type);
CREATE INDEX idx_insights_confidence ON knowledge_insights(confidence);
CREATE INDEX idx_insights_article ON knowledge_insights(article_id);
CREATE INDEX idx_entities_type ON knowledge_entities(entity_type);
CREATE INDEX idx_entities_name ON knowledge_entities(name);
CREATE INDEX idx_relationships_type ON knowledge_relationships(relationship_type);
CREATE INDEX idx_relationships_source ON knowledge_relationships(source_insight_id);
CREATE INDEX idx_relationships_target ON knowledge_relationships(target_insight_id);
```

## Knowledge Extraction

### What to Extract

1. **Technical Learnings**
   - Specific facts with numerical data (e.g., "Streaming reduces perceived latency 40%")
   - Best practices and recommendations
   - Performance characteristics
   - Trade-offs and limitations

2. **Tools and Resources**
   - Tool/library names mentioned
   - Version information if specified
   - Use cases described
   - Alternatives mentioned

3. **Statistical Claims**
   - Quantitative data points
   - Study results
   - Benchmarks and comparisons

4. **Expert Opinions**
   - Quotes from named experts
   - Predictions and forecasts
   - Analysis and commentary

### Confidence Levels

The system assigns confidence based on evidence quality:

- **High Confidence**
  - Cited peer-reviewed studies
  - Official documentation
  - Multiple independent confirmations
  - Primary sources

- **Medium Confidence**
  - Expert opinions from credible sources
  - Industry reports
  - Single credible source
  - Well-reasoned analysis

- **Low Confidence**
  - Anecdotal evidence
  - Unnamed sources
  - Speculative content
  - Single mention without verification

### Extraction Process

```python
def extract_knowledge(article: Article, llm_provider: LLMProvider) -> list[Insight]:
    """
    Extract structured knowledge from an article.

    Process:
    1. Use LLM to identify key insights in the article
    2. For each insight, extract:
       - The insight text
       - Type (technical/tool/statistic/opinion)
       - Confidence level and reasoning
       - Related entities (tools, people, companies)
    3. Return structured list of Insight objects
    """
    prompt = f"""
    Extract key learnings from this article. For each learning:
    1. State the insight clearly and concisely
    2. Classify as: technical, tool, statistic, or opinion
    3. Rate confidence: high/medium/low based on evidence quality
    4. Explain the confidence rating
    5. List any tools, technologies, or key entities mentioned

    Article Title: {article.title}
    Article Content: {article.content}

    Return structured JSON for each insight.
    """
    # LLM processes and returns structured data
    # Parse and create Insight objects
```

## Connection Detection

### Types of Relationships

1. **Confirmations**: New insight agrees with existing knowledge
   - Example: Two articles independently report similar performance gains

2. **Contradictions**: New insight conflicts with existing knowledge
   - Example: Article A says X improves performance, Article B says it doesn't
   - Surface these to the user prominently

3. **Refinements**: New insight adds nuance to existing knowledge
   - Example: Original insight about tool effectiveness, new insight adds caveats

4. **Extensions**: New insight builds on existing knowledge
   - Example: Original about basic usage, new about advanced techniques

### Detection Algorithm

```python
def detect_connections(new_insight: Insight, existing_insights: list[Insight]) -> list[Relationship]:
    """
    Detect relationships between new insight and existing knowledge.

    Strategy:
    1. Semantic similarity: Compare new insight to existing ones
    2. Entity overlap: Check for common entities
    3. Topic clustering: Group related insights
    4. LLM-based analysis: Use LLM to identify subtle connections

    Returns:
    - List of Relationship objects with type and strength
    """
    relationships = []

    # Find similar insights using embedding similarity
    similar = find_similar_insights(new_insight, existing_insights)

    # Use LLM to analyze relationships
    for existing in similar:
        relationship = analyze_relationship(new_insight, existing, llm_provider)
        if relationship:
            relationships.append(relationship)

    return relationships
```

## Querying the Knowledge Base

### Natural Language Queries

Users can query the knowledge base using natural language:

```
> What have I learned about LLM latency?

From 12 articles:

CONSENSUS (High Confidence):
- Streaming reduces perceived latency 30-40% (4 sources)
  └─ "Production LLM Learnings" (Jan 15, 2025)
  └─ "Latency Optimization Guide" (Jan 8, 2025)
  └─ "Building Real-time AI Apps" (Dec 28, 2024)
  └─ "LLM Performance Study" (Dec 20, 2024)

- Prompt caching saves costs and improves latency (3 sources)
  └─ Claude API docs (Jan 10, 2025)
  └─ "Cost Optimization Tips" (Jan 5, 2025)
  └─ "Production AI Best Practices" (Dec 15, 2024)

CONTESTED (Medium Confidence):
- Effect of model size on latency
  └─ "Smaller models always faster" - 2 sources
  └─ "Depends on optimization, not just size" - 2 sources

EMERGING (Low Confidence):
- Speculative decoding for 2x speedup (1 source, needs verification)
```

### Query Implementation

```python
def query_knowledge(query: str, llm_provider: LLMProvider) -> QueryResult:
    """
    Process natural language query against knowledge base.

    Steps:
    1. Extract query intent and key entities
    2. Search for relevant insights using semantic search
    3. Group insights by consensus/contestation
    4. Rank by confidence and recency
    5. Format results with source attribution
    """
    # Extract entities from query
    entities = extract_entities(query, llm_provider)

    # Find relevant insights
    insights = search_insights(entities, query)

    # Cluster by agreement/disagreement
    clusters = cluster_insights(insights)

    # Format for display
    result = format_query_result(clusters)

    return result
```

## Integration with Existing Flow

### Modified Summarization Pipeline

Current flow:
```
fetch_articles() → summarize_articles() → analyze_trends()
```

Enhanced flow:
```
fetch_articles() → summarize_articles() → analyze_trends() → extract_knowledge()
```

### CLI Commands

New commands to add:

```bash
# Extract knowledge from recent articles
rss extract-knowledge [--limit N]

# Query the knowledge base
rss query "What have I learned about X?"

# Show connections for a specific insight
rss connections <insight-id>

# List contradictions in knowledge base
rss contradictions

# Show knowledge summary
rss knowledge-stats

# Manage user context
rss context add project "Project name" "Description"
rss context list
rss context deactivate <context-id>
```

## Edge Cases and Error Handling

### Edge Cases

1. **No LLM Available**
   - Fall back to simpler extraction (entity detection, keyword extraction)
   - Store raw text for later reprocessing when LLM becomes available

2. **Ambiguous Insights**
   - Mark as low confidence
   - Store with uncertainty flags
   - Request more context from future articles

3. **Duplicate Insights**
   - Detect near-duplicates using similarity threshold
   - Merge or increment mention count
   - Track multiple sources

4. **Contradictory Information from Same Source**
   - Flag for manual review
   - Preserve both insights
   - Note internal contradiction

5. **Outdated Information**
   - Track temporal validity
   - Mark older insights that may be superseded
   - Surface recency in queries

### Error Handling

1. **LLM Extraction Failures**
   - Retry with simplified prompt
   - Fall back to rule-based extraction
   - Log for later reprocessing

2. **Database Errors**
   - Transaction rollback on failure
   - Preserve original article data
   - Queue for retry

3. **Query Parsing Failures**
   - Provide suggestions for query reformulation
   - Fall back to keyword search
   - Show example queries

## Performance Considerations

### Optimization Strategies

1. **Batch Processing**
   - Extract knowledge from multiple articles in one LLM call
   - Reduces API costs and latency

2. **Incremental Updates**
   - Only process new articles
   - Cache entity embeddings
   - Update relationships incrementally

3. **Similarity Search**
   - Use embedding-based similarity for connection detection
   - Consider vector database (e.g., SQLite with vector extension)
   - Cache frequent queries

4. **Query Optimization**
   - Index on common query patterns
   - Pre-compute popular aggregations
   - Cache recent query results

## Future Enhancements

1. **Personal Context Integration**
   - Link insights to user's active projects
   - Prioritize relevant insights in queries
   - Track which insights were acted upon

2. **Knowledge Evolution Tracking**
   - Visualize how understanding of a topic changed over time
   - Show confidence progression
   - Highlight paradigm shifts

3. **Export and Sharing**
   - Export knowledge base to markdown/JSON
   - Share specific insights or collections
   - Import from other sources

4. **Advanced Querying**
   - Comparison queries: "Compare X and Y"
   - Temporal queries: "What did I learn about X in December?"
   - Contradiction resolution: "Resolve conflicts about X"

5. **Active Learning**
   - Suggest articles to fill knowledge gaps
   - Identify underexplored topics
   - Recommend areas needing more sources

## Success Metrics

1. **Extraction Quality**
   - Percentage of articles with insights extracted
   - User-validated insight accuracy
   - Confidence calibration (high confidence insights should be correct more often)

2. **Connection Detection**
   - Number of meaningful relationships found
   - Contradiction detection rate
   - User feedback on connection relevance

3. **Query Usefulness**
   - Query success rate
   - Time to find information
   - User satisfaction with results

4. **Knowledge Accumulation**
   - Growth rate of knowledge base
   - Diversity of topics covered
   - Depth of coverage per topic

## Implementation Phases

### Phase 1: Foundation (Current Phase)
- Database schema
- Basic extraction from articles
- Simple storage and retrieval

### Phase 2: Intelligence
- Connection detection
- Contradiction identification
- Confidence scoring

### Phase 3: Querying
- Natural language query interface
- Result aggregation and formatting
- Source attribution

### Phase 4: Integration
- Personal context linking
- CLI commands
- User feedback loop

### Phase 5: Enhancement
- Advanced querying
- Knowledge evolution tracking
- Export and sharing

## References

- Issue #20: Feature: Knowledge Extraction & Accumulation
- docs/TREND_ANALYSIS_FEATURES.md: Feature 6 specification
- Issue #18: Personal Context Engine (dependency)
