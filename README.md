# AI RSS Summarizer

An AI-powered RSS feed summarizer with trend prediction. Fetch articles from multiple RSS feeds, generate summaries, and analyze trending topics.

## Features

- **RSS Feed Ingestion**: Fetch and store articles from multiple RSS feeds
- **Summarization**: Generate concise summaries (simple extractive or LLM-powered)
- **Trend Detection**: Categorize articles and identify trending topics
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
# Main command: fetch, summarize, and show what's new
rss update

# Filter by topic
rss update --topic tech
rss update --topic politics

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
| `rss update` | Main command: fetch, summarize, and display digest |
| `rss setup` | Interactive setup wizard for LLM providers |
| `rss providers` | List available LLM providers and their status |
| `rss fetch` | Fetch articles from all configured RSS feeds |
| `rss summarize` | Generate summaries for unsummarized articles |
| `rss trends` | Analyze and display trending topics |
| `rss list` | List fetched articles |
| `rss stats` | Show database statistics |
| `rss add-feed URL` | Add a new RSS feed |

### Options

Most commands support these options:

- `--db`, `-d`: Path to database file (default: `articles.db`)
- `--limit`, `-n`: Limit number of items to process
- `--topic`, `-t`: Filter by topic (for `update` command)
- `--help`: Show command help

## LLM Providers

The summarizer supports multiple LLM providers. Run `rss setup` for guided configuration.

### Local Providers (Free, No API Key)

| Provider | Description |
|----------|-------------|
| **LM Studio** | Local LLM server (auto-detected at localhost:1234) |
| **Ollama** | Local LLM runner (auto-detected at localhost:11434) |
| **Transformers** | HuggingFace models (requires `pip install transformers torch`) |

### Cloud Providers (API-based)

| Provider | Setup |
|----------|-------|
| **Gemini** | Free tier available. `pip install google-generativeai`, set `GOOGLE_API_KEY` |
| **Claude Agent SDK** | Uses Claude Code auth (no API key!). `pip install claude-agent-sdk` |
| **Claude API** | Requires separate API key. `pip install anthropic`, set `ANTHROPIC_API_KEY` |
| **Grok** | xAI API. Set `XAI_API_KEY` |
| **OpenAI** | Set `OPENAI_API_KEY` |

### Quick Setup Examples

```bash
# Gemini (free tier - recommended for new users)
pip install google-generativeai
export GOOGLE_API_KEY="your-api-key"
rss setup

# Claude Agent SDK (for Claude Code users - no API key needed!)
pip install claude-agent-sdk
rss setup

# Local with LM Studio
# 1. Download LM Studio from https://lmstudio.ai
# 2. Load a model and start the server
# 3. Run: rss setup (it auto-detects)
```

## Project Structure

```
ai-rss-summarizer/
├── src/
│   ├── __init__.py
│   ├── cli.py           # CLI entry point (Typer)
│   ├── commands.py      # User-facing commands (update, setup)
│   ├── llm_providers.py # LLM provider abstraction layer
│   ├── rss.py           # RSS feed fetching
│   ├── storage.py       # SQLite storage layer
│   ├── summarizer.py    # Legacy summarization (use llm_providers)
│   └── trends.py        # Trend detection
├── config/
│   ├── feeds.txt        # RSS feed URLs
│   └── llm.json         # LLM provider configuration (generated)
├── tests/
│   ├── test_storage.py
│   ├── test_rss.py
│   ├── test_summarizer.py
│   └── test_trends.py
├── pyproject.toml
├── requirements.txt
├── requirements-llm.txt # Optional LLM dependencies
└── README.md
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

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

Trend categories are defined in `src/trends.py`. Edit `TREND_CATEGORIES` to customize.

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

### Future
- [ ] Advanced trend analysis (see [docs/TREND_ANALYSIS_FEATURES.md](docs/TREND_ANALYSIS_FEATURES.md))
  - Story clustering & evolution tracking
  - Signal tagging system
  - Perspective synthesis
  - Personal context engine
  - Emergence detection
  - Knowledge extraction
  - Intelligence briefs
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
