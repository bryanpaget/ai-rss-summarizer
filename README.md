# AI RSS Summarizer

Transform your RSS feeds into personalized intelligence briefings. This tool fetches articles, extracts insights, builds a knowledge graph, clusters related stories, and generates daily briefings tailored to your interests.

**Best with [LM Studio](https://lmstudio.ai)** - Run everything locally, completely free, with no API costs or rate limits.

## Why Local LLMs?

This tool makes **hundreds of LLM calls per session**. Here's what happens when you process articles:

**Per Article:**
| Operation | LLM Calls | Embeddings | Tokens (approx) |
|-----------|-----------|------------|-----------------|
| Extract insights & triples | 1 | 0 | 500-2000 |
| Generate summary | 0 (included above) | 0 | - |
| Embed semantic card | 0 | 1 | - |
| Trend categorization | 0 | 0 (uses stored) | - |

**Per Session (after articles):**
| Operation | LLM Calls | Embeddings |
|-----------|-----------|------------|
| Cluster analysis | 1 per cluster | batch at start |
| Connection detection | varies | 0 |

**Real-world example:** Processing 50 articles generates ~50 LLM calls + ~50 embeddings + ~100 cluster analysis calls = **200+ API calls**. At typical API pricing ($0.01-0.03 per 1K tokens), that's $5-20 per session.

**With LM Studio (tested on RTX 3080):**
- 50 articles: ~15 minutes total
- Embeddings: ~0.3 seconds each (batched)
- Text generation: ~2-5 seconds per call
- **Cost: $0**

| Benefit | Cloud APIs | LM Studio |
|---------|-----------|-----------|
| Cost per 50 articles | $5-20 | **$0** |
| Rate limits | Yes | **None** |
| Privacy | Data sent to cloud | **100% local** |
| Speed | Network latency | **Local only** |
| Availability | Depends on provider | **Always on** |

The app includes a **smart gateway system** that automatically:
- Loads the right model for each task (text vs embeddings)
- Batches requests to minimize model switching (27x faster than naive approach)
- Uses sliding window to prevent queue saturation
- Retries on failures

**Recommended models for LM Studio:**
- **Text:** `google/gemma-3n-e4b` (4GB, fast) or any instruct model you prefer
- **Embeddings:** `nomic-embed-text-v1.5` (274MB, excellent quality)

## Features

- **RSS Feed Ingestion**: Fetch and store articles from multiple RSS feeds
- **AI-Powered Analysis**: Generate summaries, extract insights, detect connections
- **Embedding-Based Similarity**: Semantic matching using vector embeddings (requires LM Studio or Ollama)
- **Story Clustering**: Automatically group related articles into stories
- **Knowledge Extraction**: Build a knowledge base of facts, entities, and relationships
- **Trend Detection**: Categorize articles using embedding similarity
- **Signal Tagging**: Classify article quality (primary/secondary sources, factual/opinion, etc.)
- **Multi-Perspective Synthesis**: See how different sources cover the same story
- **CLI Interface**: Easy-to-use command-line interface

## Quick Start

### Installation

**Easiest (Auto-installer):**
```bash
# Clone and run the installer
git clone https://github.com/bryanpaget/ai-rss-summarizer.git
cd ai-rss-summarizer

# Windows:
install.bat

# Mac/Linux:
chmod +x install.sh && ./install.sh
```

**Manual (using pipx - recommended):**
```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath
# Restart your terminal

# Install RSS Summarizer globally
pipx install git+https://github.com/bryanpaget/ai-rss-summarizer.git

# Now 'rss' works from anywhere
rss --help
```

**For Development:**
```bash
git clone https://github.com/bryanpaget/ai-rss-summarizer.git
cd ai-rss-summarizer
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
pip install -e .
```

### Setup

```bash
# Run the interactive setup wizard
rss setup
```

The setup wizard will:
- Detect available LLM providers
- Guide you through API key configuration
- Save your preferences

### Basic Usage

```bash
# Main command: generate an intelligence briefing
rss report

# Limit processing for large backlogs (process 5 at a time)
rss report -m 5

# Fetch, summarize, and show what's new (quick update)
rss update

# Filter by topic
rss update --topic tech
rss update --topic politics
```

### Intelligence Briefing (`rss report`)

The main interaction loop. Produces a personalized 6-section briefing:

1. **Top Priority** - 1-3 must-read items with insights and context
2. **Your Interest Areas** - Articles matching your tracked topics
3. **Discovered Connections** - Cross-source synthesis
4. **Knowledge Graph Updates** - New facts extracted
5. **Quick Scan** - Everything else by relevance
6. **Session Stats** - Processing summary

**Incremental Processing:** If you have a large backlog (50+ unprocessed articles), the system will warn you and suggest using `-m 5` to process 5 articles at a time. Run `rss report -m 5` multiple times to catch up gradually.

### Other Commands

```bash
# Fetch articles from configured feeds
rss fetch

# Generate summaries for articles
rss summarize

# Analyze trending topics
rss trends

# List recent articles
rss list

# Check provider status
rss providers

# Show database statistics
rss stats
```

### Add a New Feed

```bash
rss add-feed https://example.com/feed.xml
```

Or edit `config/feeds.txt` directly.

## CLI Commands

| Command | Description |
|---------|-------------|
| `rss report` | **Main command**: Generate intelligence briefing with all 6 sections |
| `rss report -m 5` | Process incrementally (5 articles at a time) for large backlogs |
| `rss update` | Quick fetch + summarize + display digest |
| `rss setup` | Interactive setup wizard for LLM providers |
| `rss providers` | List available LLM providers and their status |
| `rss fetch` | Fetch articles from all configured RSS feeds |
| `rss discover` | Find new RSS feeds based on your interests |
| `rss stories list` | View story clusters with lifecycle states |
| `rss stories stats` | Show embedding coverage for stories |
| `rss stories backfill-embeddings` | Embed stories missing vectors |
| `rss context add watching "Topic"` | Track a topic for personalized briefings |
| `rss context add project "Project"` | Track a project you're working on |
| `rss context list` | View your tracked topics and projects |
| `rss constitution` | View/edit your analysis guidelines |
| `rss graph "Entity"` | Explore knowledge graph around an entity |
| `rss contradictions` | Show contradictions in the knowledge base |
| `rss perspectives` | Generate multi-perspective synthesis for stories |
| `rss schedule start` | Run scheduled background fetches |
| `rss list` | List fetched articles |
| `rss stats` | Show database statistics |
| `rss add-feed URL` | Add a new RSS feed |

### Key Options

| Option | Description |
|--------|-------------|
| `-m`, `--max-per-step` | Limit items per step (use `-m 5` for incremental processing) |
| `-n`, `--limit` | Limit total items to process |
| `-d`, `--db` | Path to database file (default: `articles.db`) |
| `-k`, `--kb` | Path to knowledge database (default: `knowledge.db`) |
| `--help` | Show command help |

## LLM Providers

### Recommended: LM Studio (Free, Local, Fast)

**LM Studio is the best choice for this tool.** Here's why:

1. **Cost:** $0 forever vs $5-20+ per session with APIs
2. **Speed:** No network latency, parallel requests
3. **Privacy:** Your data never leaves your machine
4. **Reliability:** No rate limits, no outages, no API changes

**Quick Setup:**
```bash
# 1. Download LM Studio from https://lmstudio.ai
# 2. In LM Studio, download these models:
#    - Text: google/gemma-3n-e4b (or any instruct model)
#    - Embeddings: nomic-embed-text-v1.5
# 3. Start the local server (click "Start Server")
# 4. Run:
rss setup  # Auto-detects LM Studio
```

**Hardware Requirements:**
- Minimum: 8GB RAM, any modern CPU
- Recommended: 16GB+ RAM, GPU optional but helpful
- The `gemma-3n-e4b` model runs well on modest hardware

### Alternative: Ollama

```bash
# Install Ollama from https://ollama.ai
ollama pull gemma:2b
ollama serve
rss setup  # Auto-detects Ollama
```

### Cloud Providers (For Light Use Only)

Cloud APIs work but get expensive fast. Only recommended for testing or occasional use.

| Provider | Setup | Note |
|----------|-------|------|
| **Gemini** | `pip install google-generativeai`, set `GOOGLE_API_KEY` | Free tier has limits |
| **Claude** | `pip install anthropic`, set `ANTHROPIC_API_KEY` | Expensive for heavy use |
| **OpenAI** | Set `OPENAI_API_KEY` | Expensive for heavy use |

## Project Structure

```
ai-rss-summarizer/
├── src/
│   ├── __init__.py
│   ├── cli.py             # CLI entry point (Typer)
│   ├── cli_*.py           # CLI subcommand modules (context, perspectives, signals, etc.)
│   ├── commands.py        # User-facing commands (update, setup)
│   ├── clustering.py      # Story clustering and evolution tracking
│   ├── embeddings.py      # Embedding service for semantic similarity
│   ├── embedding_providers.py  # Embedding provider abstraction
│   ├── emergence.py       # Emergence detection (novel patterns)
│   ├── knowledge.py       # Knowledge base (facts, entities, relationships)
│   ├── llm_providers.py   # LLM provider abstraction layer
│   ├── model_manager.py   # LM Studio model management
│   ├── perspectives.py    # Multi-perspective synthesis
│   ├── report.py          # Intelligence report generation
│   ├── rss.py             # RSS feed fetching
│   ├── signal_tagger.py   # Signal tagging (source type, factuality)
│   ├── storage.py         # SQLite storage layer
│   ├── summarizer.py      # Article summarization
│   ├── trends.py          # Embedding-based trend detection
│   └── user_context.py    # Personal context engine
├── config/
│   ├── feeds.txt          # RSS feed URLs
│   └── llm.json           # LLM provider configuration (generated)
├── tests/
│   └── test_*.py          # Comprehensive test suite
├── pyproject.toml
├── requirements.txt
├── requirements-llm.txt   # Optional LLM dependencies
└── README.md
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Architectural Tests

The pipeline enforces strict phase isolation to prevent model switching:

```bash
# Run architectural tests
pytest tests/test_pipeline_architecture.py -v -s
```

These tests enforce:
- **LLM phase has 0 embedding calls** - embedding-based categorization moved to embedding phase
- **LLM phase has 0 model switches** - no LLM->EMBED->LLM patterns
- **1 LLM call per article** - consolidated extraction (insights + triples in one call)

Tests always print the full call log showing which function made each call, making violations easy to diagnose.

### Code Style

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Configuration

### Feed Sources

Edit `config/feeds.txt` to add or remove RSS feeds. One URL per line, comments start with `#`.

```text
# Tech News
https://news.ycombinator.com/rss
https://feeds.arstechnica.com/arstechnica/technology-lab

# World News
http://feeds.bbci.co.uk/news/rss.xml
```

### Trend Categories

Trend categories are defined in `src/trends.py`. Edit `TREND_CATEGORY_DESCRIPTIONS` to customize. Categories are matched using embedding-based semantic similarity rather than keyword matching.

## Roadmap

See [Issue #7](https://github.com/bryanpaget/ai-rss-summarizer/issues/7) for the full project roadmap.

### MVP (Complete)
- [x] RSS feed fetching
- [x] SQLite storage
- [x] Simple summarization
- [x] Trend detection
- [x] CLI interface
- [x] Multiple LLM providers (Gemini, Claude, Grok, OpenAI, local)
- [x] Interactive setup wizard
- [x] Provider transparency footer
- [x] Claude Agent SDK integration

### Advanced Features (Complete)
- [x] Story clustering & evolution tracking
- [x] Signal tagging system (primary/secondary sources, factual/opinion)
- [x] Multi-perspective synthesis
- [x] Personal context engine
- [x] Emergence detection (novel patterns)
- [x] Knowledge extraction (facts, entities, relationships)
- [x] Intelligence report generation
- [x] Embedding-based semantic similarity

### Future
- [ ] Standalone executable (PyInstaller) - no Python required
- [ ] FastAPI web interface
- [ ] Docker containerization
- [ ] Email digest notifications

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.
