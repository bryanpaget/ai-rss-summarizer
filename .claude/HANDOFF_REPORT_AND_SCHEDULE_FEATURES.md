# Handoff: Report Command and Schedule Feature Implementation

**Date**: 2026-01-12
**Context**: End-to-end testing of RSS Summarizer revealed UX issues and missing features

---

## Project Overview

This is an AI-powered RSS feed summarizer CLI tool. It fetches articles from RSS feeds, uses LLMs to summarize/analyze them, builds a knowledge graph, clusters articles into stories, and provides various analysis views.

**Repository**: Local at `C:\Users\jpswi\personal projects\RSSsummarizer`
**Upstream**: bryanpaget/ai-rss-summarizer (PR #30 open from fork KatsuJinCode)
**Test Suite**: 2466 tests, all passing

---

## Current State

### What Works
- `rss fetch` - Fetches articles from configured RSS feeds (fast, HTTP only)
- `rss list` - Lists articles in database
- `rss stats` - Shows database statistics
- `rss trends` - Rule-based keyword categorization (fast, no LLM)
- `rss providers` - Shows available LLM providers
- `rss help` - Shows organized command help

### What's Slow/Broken
- `rss cluster-stories` - Hangs because it makes LLM calls per article (485 unclustered articles = hundreds of LLM calls)
- `rss update` - Tries to summarize, very slow
- `rss summarize` - Works but slow (LLM per article)

### Key Discovery
The "smart" LLM features (knowledge extraction, clustering, summarization) are **not integrated** into any main workflow. User has to manually run many separate commands. There's no single "give me my daily briefing" command.

---

## Features to Build

### Feature 1: `rss report` Command

**Purpose**: Single command that does the full LLM-powered analysis workflow with rich live output.

**User Experience**:
- User runs `rss report`
- Sees live progress as each article is processed
- Output shows actual content so user can "read along" like watching over someone's shoulder

**Live Output Design** (scrolling/updating display):
```
Processing: "UK to bring into force law to tackle Grok AI deepfakes"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/50

The UK government announced legislation targeting AI-generated
deepfakes, specifically mentioning Grok. The law would require
platforms to label AI content and provide takedown mechanisms...

→ Entities: UK Government, Grok, Deepfake Legislation
→ Relationships: UK Government → regulates → AI deepfakes
→ Connects to: Previous EU AI Act coverage (5 articles)

[next article scrolls up, previous fades/moves up]
```

**Key Points**:
- NO "instant" or "quick" version - if meaningful analysis requires LLM, just do it
- Show truncated article content/summary so user can read along
- Show what was extracted (entities, relationships)
- Show connections to other articles/knowledge
- Progress bar showing X/total
- Like a "digital billboard" rotating through articles as they're processed

**Implementation Notes**:
- Should auto-fetch if articles are stale (configurable threshold)
- Use Rich library for live updating display (already in project)
- Process articles through: summarization → knowledge extraction → clustering
- At end, show synthesized insights/report

### Feature 2: `rss schedule` Command

**Purpose**: Allow background fetching even when user isn't running the app, so articles accumulate during gaps.

**Problem Solved**: RSS feeds only serve recent items (10-50). If user doesn't run app for a month, they miss everything in between. Background fetch solves this.

**Commands**:
```bash
rss schedule enable --every 3d    # Fetch every 3 days
rss schedule enable --every 12h   # Fetch every 12 hours
rss schedule disable              # Remove scheduled task
rss schedule status               # Show current schedule status
```

**Implementation**:
- On Windows: Use Task Scheduler (schtasks.exe or Python's schedule library with a background service)
- On Linux/Mac: Use cron
- The scheduled task just runs `rss fetch` - cheap HTTP operation
- Processing waits until user runs `rss report`

**Running `rss schedule` with no argument**: Must show help or interactive menu (see Design Principle below)

### Feature 3: CLI Subcommand UX Pattern

**Design Principle**: When a command requires a subcommand and none is provided, NEVER show a cryptic error. Instead:

**Option A - Interactive Mode** (preferred if feasible):
```
Schedule background fetching:

> enable     Set up automatic fetching
  disable    Turn off automatic fetching
  status     Check current schedule

Use ↑↓ to select, Enter to confirm
```

**Option B - Contextual Help** (minimum acceptable):
```
Usage: rss schedule <command>

Commands:
  enable   Set up automatic fetching (e.g., --every 3d)
  disable  Remove scheduled fetching
  status   Show if background fetch is active

Run 'rss schedule enable --help' for more details.
```

**Apply this pattern to ALL commands with required subcommands**, including:
- `rss schedule`
- `rss tag` (currently has: articles, stats, filter)
- `rss context` (has: add, list)
- Any future grouped commands

---

## Technical Context

### LLM Provider
- LM Studio is available and working at localhost:1234
- Test with: `provider.summarize('text')` (no max_tokens kwarg)
- Get provider with: `from src.llm_providers import get_best_provider; provider, is_llm = get_best_provider()`

### Database
- SQLite at `articles.db`
- 635 total articles currently
- 485 unclustered
- Use `Storage` class from `src.storage`

### Key Files
- `src/cli.py` - Main CLI entry point, uses Typer
- `src/commands.py` - Most command implementations
- `src/llm_providers.py` - LLM provider abstraction
- `src/storage.py` - Database operations
- `src/clustering.py` - Story clustering (has `update_story_clusters()`)
- `src/knowledge.py` - Knowledge graph extraction
- `src/summarizer.py` - Article summarization

### Rich Library
Already used throughout for tables, panels, progress bars. See existing usage in `src/cli.py` and `src/commands.py`.

For live updating display, look into:
- `rich.live.Live` for live updating
- `rich.progress.Progress` for progress bars
- `rich.panel.Panel` for bordered content
- `rich.console.Console` for output

---

## Testing Requirements

After implementing:

1. **Unit tests** for new functions (follow existing patterns in `tests/`)
2. **Integration test**: Run `rss report` with mocked LLM, verify output format
3. **Schedule tests**: Mock the OS scheduler calls, verify correct commands generated
4. **Subcommand UX tests**: Verify `rss schedule` with no args shows help/interactive

Use the global test harness - all tests must complete within 5 seconds (mark slow tests with `@pytest.mark.slow`).

---

## Definition of Done

1. `rss report` shows live progress with article content, extracted knowledge, connections
2. `rss schedule enable/disable/status` manages OS-level scheduled tasks
3. `rss schedule` with no args shows help or interactive menu
4. Same UX pattern applied to `rss tag` and `rss context`
5. All new code has tests
6. Full test suite still passes

---

## Questions to Resolve During Implementation

1. How many articles should `rss report` process by default? All unprocessed? Last N days? Top N by relevance?
2. Should `rss report` re-process already-summarized articles or skip them?
3. What's the final summary/synthesis format after all articles are processed?
4. For Windows Task Scheduler - run as current user or create a service?

---

## Commands Reference

Current working commands for testing:
```bash
cd "C:\Users\jpswi\personal projects\RSSsummarizer"
python -m src.cli help
python -m src.cli providers
python -m src.cli stats
python -m src.cli fetch
python -m src.cli list --limit 10
python -m src.cli trends
```

Run tests:
```bash
python -m pytest tests/ -v --tb=short
```
