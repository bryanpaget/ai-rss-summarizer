# AI RSS Summarizer

An AI-powered RSS feed summarizer with trend prediction. Fetch articles from multiple RSS feeds, generate summaries, and analyze trending topics.

## Features

- **RSS Feed Ingestion**: Fetch and store articles from multiple RSS feeds
- **Summarization**: Generate concise summaries (simple extractive or LLM-powered)
- **Trend Detection**: Categorize articles and identify trending topics
- **CLI Interface**: Easy-to-use command-line interface

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/bryanpaget/ai-rss-summarizer.git
cd ai-rss-summarizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Basic Usage

```bash
# Fetch articles from configured feeds
rss fetch

# Generate summaries for articles
rss summarize

# Analyze trending topics
rss trends

# List recent articles
rss list

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
- `--help`: Show command help

### LLM Summarization

For better summaries using AI models:

```bash
# Install LLM dependencies
pip install transformers torch

# Use LLM for summarization
rss summarize --llm
```

Note: First run will download the model (~1.5GB).

## Project Structure

```
ai-rss-summarizer/
├── src/
│   ├── __init__.py
│   ├── cli.py           # CLI entry point (Typer)
│   ├── rss.py           # RSS feed fetching
│   ├── storage.py       # SQLite storage layer
│   ├── summarizer.py    # Summarization backends
│   └── trends.py        # Trend detection
├── config/
│   └── feeds.txt        # RSS feed URLs
├── tests/
│   ├── test_storage.py
│   ├── test_rss.py
│   ├── test_summarizer.py
│   └── test_trends.py
├── pyproject.toml
├── requirements.txt
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

### MVP (Current)
- [x] RSS feed fetching
- [x] SQLite storage
- [x] Simple summarization
- [x] Trend detection
- [x] CLI interface

### Future
- [ ] FastAPI web interface
- [ ] Advanced LLM integration
- [ ] Docker containerization
- [ ] Kubernetes deployment

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.
