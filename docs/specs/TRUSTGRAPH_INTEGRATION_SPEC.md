# TrustGraph Integration Specification

**Status:** Future Enhancement (Option C)
**Priority:** Long-term
**Depends on:** Option B (enhanced knowledge.py) completion

## Overview

Optional heavyweight knowledge graph backend using [TrustGraph](https://github.com/trustgraph-ai/trustgraph) for users who need enterprise-grade graph capabilities.

## Motivation

The built-in `knowledge.py` provides lightweight graph features suitable for most users. However, power users with large article collections or complex analysis needs may benefit from:

- RDF triple stores (Neo4j, Cassandra)
- Vector databases (Qdrant, Pinecone)
- 3D graph visualization
- Advanced semantic search
- Multi-agent reasoning pipelines

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    RSS Summarizer                        │
├─────────────────────────────────────────────────────────┤
│                  KnowledgeBackend ABC                    │
├─────────────────┬───────────────────────────────────────┤
│  SQLiteBackend  │        TrustGraphBackend              │
│  (default)      │        (optional)                     │
│                 │                                       │
│  - knowledge.py │  - trustgraph_backend.py              │
│  - SQLite DB    │  - Neo4j/Cassandra                    │
│  - Local embeds │  - Qdrant/Pinecone                    │
└─────────────────┴───────────────────────────────────────┘
```

## Configuration

```json
// config/llm.json
{
  "provider": "gemini",
  "knowledge_backend": "sqlite",  // or "trustgraph"
  "trustgraph": {
    "enabled": false,
    "graph_store": "neo4j",
    "vector_store": "qdrant",
    "neo4j_url": "bolt://localhost:7687",
    "qdrant_url": "http://localhost:6333"
  }
}
```

## CLI Flag

```bash
# Use TrustGraph backend for this session
rss update --knowledge-backend trustgraph

# Configure TrustGraph
rss setup --trustgraph
```

## Implementation Steps

1. **Define KnowledgeBackend ABC** - Abstract interface both backends implement
2. **Refactor knowledge.py** - Extract interface, rename to SQLiteKnowledgeBackend
3. **Create trustgraph_backend.py** - TrustGraph implementation
4. **Add backend selection** - Config and CLI flag support
5. **Migration tool** - Export SQLite to TrustGraph format

## TrustGraph Features to Leverage

| Feature | RSS Summarizer Use Case |
|---------|------------------------|
| RDF Triples | Article -> mentions -> Entity relationships |
| Graph Queries | "Show all articles connected to AI regulation" |
| Vector Search | Semantic similarity across articles |
| Visualization | Interactive knowledge graph explorer |
| MCP Integration | Tool access for Claude/other LLMs |

## Dependencies

```
# Optional TrustGraph dependencies (not required for basic use)
trustgraph>=0.1.0
neo4j>=5.0.0
qdrant-client>=1.0.0
```

## Decision Log

- **2025-01-07:** Created spec. Option B (SQLite enhancements) prioritized first.
- TrustGraph adds significant complexity (external services, Docker deployment)
- Will revisit after Option B proves the graph model works for RSS use case

## References

- [TrustGraph GitHub](https://github.com/trustgraph-ai/trustgraph)
- [TrustGraph Docs](https://docs.trustgraph.ai/)
- [Config Builder](https://config-ui.demo.trustgraph.ai/)
