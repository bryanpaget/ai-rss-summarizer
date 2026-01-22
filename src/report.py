"""Report generation with self-healing pipeline.

NEW ARCHITECTURE (v2):
- Step 1: Verification - Detect gaps from interrupted runs
- Step 2: LLM Phase - Generate summaries, facts, tags (text model)
- Step 3: Embedding Phase - Embed semantic cards (embedding model)
- Step 4: Story Matching - Match articles to stories

Key principles:
- NO SILENT FAILURES - Every error is surfaced
- Self-healing - Gaps from previous runs are detected and filled
- Semantic embeddings - Embed distilled content, not raw articles
"""

import atexit
import json
import signal
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .storage import Storage, Article, Story
from .utils import format_duration
from .content_filter import filter_articles, cleanup_old_spam
from .knowledge import (
    KnowledgeBase,
    extract_all_from_article,
    detect_connections,
    format_relationship,
)
from .llm_providers import get_best_provider, get_setup_instructions
from .rss import fetch_all_feeds, load_feeds
from .trends import analyze_article
from .signal_tagger import SignalTagger, SignalTags
from .embeddings import EmbeddingService
from .clustering import StoryClusterer
from .storage_perspectives import add_perspective_methods
from .user_context import UserContextStore, UserContextProfile

console = Console(force_terminal=True, legacy_windows=True)


# =============================================================================
# CONFIGURATION - Change these values to tune performance
# =============================================================================

EMBEDDING_BATCH_SIZE = 100  # Number of items per embedding API call


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math
    if not vec1 or not vec2:
        return 0.0
    if len(vec1) != len(vec2):
        # Pad shorter vector
        max_len = max(len(vec1), len(vec2))
        vec1 = list(vec1) + [0.0] * (max_len - len(vec1))
        vec2 = list(vec2) + [0.0] * (max_len - len(vec2))

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product / (mag1 * mag2)


def _timed(name: str, func, *args, **kwargs):
    """Execute a function and print its execution time."""
    start = time.time()
    result = func(*args, **kwargs)
    console.print(f"  [dim]{name} completed in {time.time() - start:.1f}s[/dim]\n")
    return result


class BatchProgress:
    """
    Helper for batch processing with timing and ETA prediction.

    Usage:
        progress = BatchProgress(total_items=100, batch_size=10, label="articles")
        for batch_num, batch in progress.iterate(items):
            progress.start_batch()
            # ... process batch ...
            progress.end_batch(success_count, error_count)
        progress.summary()
    """

    def __init__(self, total_items: int, batch_size: int = 10, label: str = "items"):
        self.total_items = total_items
        self.batch_size = batch_size
        self.label = label
        self.num_batches = (total_items + batch_size - 1) // batch_size
        self.batch_times: list[float] = []
        self.current_batch_start: float = 0
        self.current_batch_num: int = 0
        self.total_processed: int = 0
        self.total_errors: int = 0

    def _get_eta(self) -> str:
        """Calculate estimated time remaining based on average batch time."""
        if not self.batch_times:
            return ""
        avg_time = sum(self.batch_times) / len(self.batch_times)
        remaining_batches = self.num_batches - self.current_batch_num
        eta_seconds = avg_time * remaining_batches
        if eta_seconds < 1:
            return ""
        return f"~{format_duration(eta_seconds)} remaining"

    def iterate(self, items: list):
        """Yield (batch_num, batch) tuples for iteration."""
        for batch_num in range(self.num_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, self.total_items)
            batch = items[start_idx:end_idx]
            self.current_batch_num = batch_num + 1
            yield batch_num, batch

    def start_batch(self):
        """Call before processing a batch."""
        self.current_batch_start = time.time()
        eta = self._get_eta()
        eta_str = f" [{eta}]" if eta else ""
        console.print(
            f"    [dim]Batch {self.current_batch_num}/{self.num_batches}{eta_str}...[/dim]",
            end=""
        )

    def end_batch(self, success_count: int = 0, error_count: int = 0, stopped: bool = False):
        """Call after processing a batch. Returns the batch duration."""
        duration = time.time() - self.current_batch_start
        self.batch_times.append(duration)
        self.total_processed += success_count
        self.total_errors += error_count

        duration_str = f"({format_duration(duration)})"

        if stopped:
            console.print(f" [dim]stopped {duration_str}[/dim]")
        elif error_count == 0:
            console.print(f" [green]done[/green] [dim]{duration_str}[/dim]")
        else:
            console.print(f" [yellow]done ({error_count} errors)[/yellow] [dim]{duration_str}[/dim]")

        return duration

    def summary(self, custom_message: str = None):
        """Print final summary with total time."""
        total_time = sum(self.batch_times)
        if custom_message:
            console.print(f"  [green]{custom_message}[/green] [dim]({format_duration(total_time)} total)[/dim]")
        elif self.total_errors == 0:
            console.print(f"  [green]Processed {self.total_processed} {self.label}[/green] [dim]({format_duration(total_time)} total)[/dim]")
        else:
            console.print(f"  [yellow]Processed {self.total_processed} {self.label} ({self.total_errors} errors)[/yellow] [dim]({format_duration(total_time)} total)[/dim]")


# =============================================================================
# CLEANUP HANDLING - Prevent orphaned gateway requests on cancel
# =============================================================================

_cleanup_registered = False


def _cleanup_gateway():
    """Clean up gateway on exit - cancel pending requests only.

    IMPORTANT: Do NOT unload the model. The gateway manages model lifecycle
    (auto-unloads after 5 minutes idle). Unloading here would kill the model
    for other processes using the same gateway.
    """
    try:
        from safe_loading_gateway import get_gateway
        gateway = get_gateway()
        gateway.clear_queue()  # Cancel our pending requests
        # Do NOT call gateway.unload() - let gateway manage model lifecycle
    except Exception:
        pass  # Best effort cleanup


def _signal_handler(signum, frame):
    """Handle interrupt signals by cleaning up and exiting."""
    console.print("\n[yellow]Interrupted - canceling pending requests...[/yellow]")
    _cleanup_gateway()
    sys.exit(130)  # Standard exit code for SIGINT


def _register_cleanup():
    """Register cleanup handlers (only once)."""
    global _cleanup_registered
    if _cleanup_registered:
        return

    # Register atexit handler
    atexit.register(_cleanup_gateway)

    # Register signal handlers (skip on Windows for SIGTERM)
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _signal_handler)

    _cleanup_registered = True


# =============================================================================
# STEP 1: VERIFICATION (Self-Healing) - Corpus State Snapshot
# =============================================================================

def _make_progress_bar(completed: int, total: int, width: int = 20) -> str:
    """Create a text-based progress bar using ASCII characters for Windows compatibility."""
    if total == 0:
        return "[dim]" + "-" * width + "[/dim]"
    ratio = min(completed / total, 1.0)
    filled = int(ratio * width)
    return "[green]" + "#" * filled + "[/green][dim]" + "-" * (width - filled) + "[/dim]"


def _run_verification_step(
    storage: Storage,
    kb: KnowledgeBase,
    articles: list[Article],
    embedding_service: EmbeddingService,
    limit: int = 0,
    min_content_length: int = 0,
    new_article_ids: list[str] = None,
) -> dict:
    """
    Step 1: Corpus state snapshot with gap detection.

    Shows:
    - Total corpus state with completion percentages
    - Separates NEW articles (just fetched) from EXISTING gaps (from previous runs)
    - Progress bars for visual clarity
    """
    if new_article_ids is None:
        new_article_ids = []
    new_ids_set = set(new_article_ids)

    gaps = {
        "articles_missing_summary": 0,
        "articles_missing_trends": 0,
        "articles_missing_signals": 0,
        "articles_missing_embeddings": 0,
        "stories_missing_embeddings": 0,
        "insights_missing_embeddings": 0,
        "articles_needing_llm": [],
        "articles_needing_embedding": [],
        # Separate new vs existing
        "new_count": len(new_article_ids),
        "existing_gaps_summary": 0,
        "existing_gaps_trends": 0,
        "existing_gaps_signals": 0,
        "existing_gaps_embeddings": 0,
    }

    console.print("[bold]Step 1:[/bold] Corpus State Snapshot")
    console.print()

    # Get corpus-wide stats
    # Total articles (all, including analyzed)
    all_articles = storage.get_articles(limit=None)
    total_corpus = len(all_articles)

    # Count excluded (suspected ads)
    excluded_count = storage.count_spam_articles() if hasattr(storage, 'count_spam_articles') else 0

    # Count per-step completion for EXISTING articles (not new this session)
    existing_articles = [a for a in all_articles if a.id not in new_ids_set]
    existing_count = len(existing_articles)

    # Completion counts for existing corpus
    existing_with_summary = sum(1 for a in existing_articles if a.summary)
    existing_with_trends = sum(1 for a in existing_articles if a.trend_tags)
    existing_with_signals = sum(1 for a in existing_articles if a.signal_tags)
    existing_with_embeddings = sum(1 for a in existing_articles if storage.get_embedding(a.id) is not None)

    # Fully processed = has all 4 things
    fully_processed = sum(
        1 for a in existing_articles
        if a.summary and a.trend_tags and a.signal_tags and storage.get_embedding(a.id) is not None
    )

    # Calculate gaps for EXISTING articles only (not new)
    gaps["existing_gaps_summary"] = existing_count - existing_with_summary
    gaps["existing_gaps_trends"] = existing_count - existing_with_trends
    gaps["existing_gaps_signals"] = existing_count - existing_with_signals
    gaps["existing_gaps_embeddings"] = existing_count - existing_with_embeddings

    # For backward compatibility, set total gap counts
    gaps["articles_missing_summary"] = gaps["existing_gaps_summary"]
    gaps["articles_missing_trends"] = gaps["existing_gaps_trends"]
    gaps["articles_missing_signals"] = gaps["existing_gaps_signals"]
    gaps["articles_missing_embeddings"] = gaps["existing_gaps_embeddings"]

    # Check story/insight embeddings
    stories = storage.get_active_stories()
    for story in stories:
        if not embedding_service.get_embedding(story.id, "story"):
            gaps["stories_missing_embeddings"] += 1

    insights = kb.get_insights()
    for insight in insights:
        if not embedding_service.get_embedding(insight.id, "insight"):
            gaps["insights_missing_embeddings"] += 1

    # Track what will actually be processed (from limited list)
    # NOTE: trend_tags come from EMBEDDING phase (cosine similarity), NOT LLM
    for article in articles:
        needs_llm = not article.summary or not article.signal_tags
        needs_embedding = storage.get_embedding(article.id) is None
        if needs_llm:
            gaps["articles_needing_llm"].append(article)
        if needs_embedding:
            gaps["articles_needing_embedding"].append(article)

    # ==========================================================================
    # Display corpus state snapshot
    # ==========================================================================

    # Header with total and excluded note
    excluded_note = ""
    if excluded_count > 0:
        excluded_note = f" [dim](excludes {excluded_count} suspected ads - run 'rss ads' to review)[/dim]"
    console.print(f"  [bold]EXISTING CORPUS[/bold] ({existing_count} articles){excluded_note}")

    # Fully processed percentage
    if existing_count > 0:
        fully_pct = (fully_processed / existing_count) * 100
        console.print(f"    Fully processed: {fully_processed:,} ({fully_pct:.0f}%)")
    else:
        console.print(f"    Fully processed: 0")

    console.print()

    # Per-step completion with aligned progress bars
    console.print("    [bold]Per-step completion:[/bold]")

    def show_step_progress(label: str, completed: int, total: int) -> None:
        if total == 0:
            pct_str = "  -"
            count_str = "0/0"
        else:
            pct = (completed / total) * 100
            pct_str = f"{pct:3.0f}%"
            count_str = f"{completed:,}/{total:,}"
        bar = _make_progress_bar(completed, total)
        # Align: label (12 chars), bar (20 chars), count, percentage
        console.print(f"      {label:<12} {bar}  {count_str:>13}  ({pct_str})")

    show_step_progress("Summaries", existing_with_summary, existing_count)
    show_step_progress("Trend tags", existing_with_trends, existing_count)
    show_step_progress("Signal tags", existing_with_signals, existing_count)
    show_step_progress("Embeddings", existing_with_embeddings, existing_count)

    # Show gaps from previous runs (if any)
    total_existing_gaps = (
        gaps["existing_gaps_summary"] +
        gaps["existing_gaps_trends"] +
        gaps["existing_gaps_signals"] +
        gaps["existing_gaps_embeddings"]
    )

    if total_existing_gaps > 0:
        console.print()
        console.print(f"    [yellow]Gaps to fill (from previous runs):[/yellow]")
        if gaps["existing_gaps_summary"] > 0:
            console.print(f"      - {gaps['existing_gaps_summary']} missing summaries")
        if gaps["existing_gaps_trends"] > 0:
            console.print(f"      - {gaps['existing_gaps_trends']} missing trend tags")
        if gaps["existing_gaps_signals"] > 0:
            console.print(f"      - {gaps['existing_gaps_signals']} missing signal tags")
        if gaps["existing_gaps_embeddings"] > 0:
            console.print(f"      - {gaps['existing_gaps_embeddings']} missing embeddings")
        if gaps["stories_missing_embeddings"] > 0:
            console.print(f"      - {gaps['stories_missing_embeddings']} stories missing embeddings")
        if gaps["insights_missing_embeddings"] > 0:
            console.print(f"      - {gaps['insights_missing_embeddings']} insights missing embeddings")

    # New articles this session
    console.print()
    if len(new_article_ids) > 0:
        console.print(f"  [bold]NEW THIS SESSION[/bold]: {len(new_article_ids)} articles fetched")
        console.print(f"    [dim](Expected to need processing - not counted as gaps)[/dim]")
    else:
        console.print(f"  [bold]NEW THIS SESSION[/bold]: No new articles")

    # Overall processing score
    console.print()
    if existing_count > 0:
        # Calculate total steps done vs total steps needed
        # 4 steps per article: summary, trends, signals, embedding
        total_steps = existing_count * 4
        completed_steps = existing_with_summary + existing_with_trends + existing_with_signals + existing_with_embeddings
        overall_pct = (completed_steps / total_steps) * 100
        console.print(f"  [bold]OVERALL SCORE[/bold]: {overall_pct:.0f}% of processing complete on existing corpus")

    console.print()
    return gaps


# =============================================================================
# STEP 2: PRE-EMBEDDING PHASE (Embed existing content first)
# =============================================================================

def _run_pre_embedding_phase(
    storage: Storage,
    kb: KnowledgeBase,
    embedding_service: EmbeddingService,
    stats: dict,
    limit: int = 0,
) -> None:
    """
    Step 2: Pre-embed existing stories and insights.

    This MUST run BEFORE the LLM phase so that detect_connections
    has embeddings to compare against when finding relationships.

    Also initializes category embeddings for trend tagging (done once, stored in FAISS).

    NOTE: Model loading is handled by the gateway - no ensure_*_model() calls needed.
    """
    from .trends import ensure_categories_initialized

    console.print("[bold]Step 2:[/bold] Pre-embedding existing content...")

    # Check if embedding service is available
    if not embedding_service.is_available():
        console.print("  [red]ERROR: Embedding service not available[/red]")
        console.print("  [yellow]Connection detection will be limited[/yellow]")
        console.print()
        return

    provider_info = embedding_service.get_provider_info()
    model_name = provider_info.get('model', '')
    if model_name and model_name != 'unknown':
        console.print(f"  [green]Using {provider_info.get('provider', 'unknown')} ({model_name})[/green]")
    else:
        console.print(f"  [green]Using {provider_info.get('provider', 'unknown')}[/green]")

    # Initialize category embeddings (seeded once, then loaded from FAISS)
    # This also triggers embedding model loading via gateway
    console.print("  [dim]Initializing trend categories...[/dim]", end="")
    if ensure_categories_initialized(embedding_service):
        console.print(" [green]ready[/green]")
    else:
        console.print(" [yellow]failed (trend tagging will be limited)[/yellow]")

    # Embed insights first (these are what detect_connections compares against)
    # Uses TRUE batch embedding - one API call per batch, not one per insight
    insights = kb.get_insights()
    insights_needing_embedding = [i for i in insights if not embedding_service.get_embedding(i.id, "insight")]

    if insights_needing_embedding:
        progress = BatchProgress(len(insights_needing_embedding), batch_size=EMBEDDING_BATCH_SIZE, label="insights")
        console.print(f"  Embedding {progress.total_items} insights in {progress.num_batches} batches...")

        for batch_num, batch in progress.iterate(insights_needing_embedding):
            progress.start_batch()
            batch_success = 0
            batch_errors = 0
            limit_reached = False

            # Check limit before processing batch
            if limit > 0 and progress.total_processed >= limit:
                limit_reached = True
                progress.end_batch(0, 0, stopped=True)
                break

            try:
                # TRUE batch embedding - one API call for all texts in batch
                texts = [insight.content for insight in batch]
                results = embedding_service.embed_batch(texts)

                # Save each result
                for insight, result in zip(batch, results):
                    if limit > 0 and progress.total_processed + batch_success >= limit:
                        limit_reached = True
                        break
                    embedding_service.save_embedding(insight.id, "insight", result)
                    batch_success += 1
            except Exception as e:
                console.print(f"\n  [red]Batch embedding failed: {e}[/red]", end="")
                stats["errors"] += len(batch)
                batch_errors = len(batch)

            progress.end_batch(batch_success, batch_errors, stopped=limit_reached)
            if limit_reached:
                break

        progress.summary(f"Embedded {progress.total_processed} insights")
        stats["insights_embedded"] = progress.total_processed
    else:
        console.print("  [dim]All insights already have embeddings[/dim]")

    # Embed stories - uses TRUE batch embedding
    stories = storage.get_active_stories()
    stories_needing_embedding = [s for s in stories if not embedding_service.get_embedding(s.id, "story")]

    if stories_needing_embedding:
        progress = BatchProgress(len(stories_needing_embedding), batch_size=EMBEDDING_BATCH_SIZE, label="stories")
        console.print(f"  Embedding {progress.total_items} stories in {progress.num_batches} batches...")

        for batch_num, batch in progress.iterate(stories_needing_embedding):
            progress.start_batch()
            batch_success = 0
            batch_errors = 0
            limit_reached = False

            # Check limit before processing batch
            if limit > 0 and progress.total_processed >= limit:
                limit_reached = True
                progress.end_batch(0, 0, stopped=True)
                break

            try:
                # Build semantic card for each story (title + description + keywords)
                def story_to_text(story):
                    keywords_str = ", ".join(story.keywords[:20]) if story.keywords else ""
                    return f"{story.title}\n\n{story.description or ''}\n\nKeywords: {keywords_str}"

                texts = [story_to_text(story) for story in batch]
                results = embedding_service.embed_batch(texts)

                # Save each result
                for story, result in zip(batch, results):
                    if limit > 0 and progress.total_processed + batch_success >= limit:
                        limit_reached = True
                        break
                    embedding_service.save_embedding(story.id, "story", result)
                    batch_success += 1
            except Exception as e:
                console.print(f"\n  [red]Batch embedding failed: {e}[/red]", end="")
                stats["errors"] += len(batch)
                batch_errors = len(batch)

            progress.end_batch(batch_success, batch_errors, stopped=limit_reached)
            if limit_reached:
                break

        progress.summary(f"Embedded {progress.total_processed} stories")
        stats["story_embeddings_generated"] = progress.total_processed
    else:
        console.print("  [dim]All stories already have embeddings[/dim]")

    console.print()


# =============================================================================
# STEP 3: LLM PHASE
# =============================================================================

def _run_llm_phase(
    articles: list[Article],
    storage: Storage,
    kb: KnowledgeBase,
    provider,
    stats: dict,
    embedding_service: EmbeddingService,
    limit: int = 0,
) -> list[dict]:
    """
    Step 3: LLM processing for all articles.

    Generates: summaries, insights, facts (triples), signal tags.
    Uses pipelining to keep ~5 requests in flight at all times.
    Both extraction and tagging requests share the same queue.

    NOTE: Model loading is handled by the gateway - no ensure_*_model() calls needed.
    The gateway automatically loads the correct model based on request type.

    NO SILENT FAILURES - Every error is surfaced to the user.
    """
    from safe_loading_gateway import get_gateway
    from .knowledge import build_extraction_prompt, process_extraction_response
    from .constitution import get_constitution_context

    console.print("[bold]Step 3:[/bold] LLM Analysis...")
    console.print(f"  [green]Using {provider.name}[/green]")

    gateway = get_gateway()
    step_start = time.time()
    total_llm_calls = 0

    console.print()

    # Apply limit
    articles_to_process = articles[:limit] if limit > 0 else articles
    total_articles = len(articles_to_process)

    if limit > 0 and len(articles) > limit:
        console.print(f"  [dim]Processing {limit} of {len(articles)} articles (limit)[/dim]")
        console.print()

    # Unified pipeline: keep ~5 LLM requests in flight (extraction OR tagging)
    PIPELINE_SIZE = 5
    in_flight = []  # List of (work_type, idx, article, handle, start_time, extra_data)
    # work_type: "extraction" or "tagging"
    # extra_data: for tagging, contains {"insights": [], "triples": []} from extraction

    next_extraction_idx = 0
    completed_count = 0
    processed_articles = []

    # Track per-article state
    article_data = {}  # idx -> {"insights": [], "triples": [], "errors": [], "start_time": ...}

    def build_tagging_prompt(article: Article) -> str:
        """Build the signal tagging prompt for an article."""
        constitution_context = get_constitution_context()
        return f"""{constitution_context}Analyze this article and assign appropriate tags from each category.

Article Title: {article.title}
Article Content: {article.content}

Tag Categories:
- Source Type: primary, secondary, aggregator, press-release, speculative, satirical
- Evidence: well-sourced, single-source, anonymous-sources, documented, unverified
- Reasoning: logical, non-sequitur, cherry-picked, balanced
- Tone: factual, analytical, opinion, sensational, spicy, unhinged
- Actionability: actionable, awareness, noise

Also determine if this is advertising/promotional content:
- is_ad: true if this is a product roundup, buying guide, sponsored content, affiliate content, or promotional material (e.g. "Best Baby Gear 2024", "Top 10 Products", buyer's guides). false if it's genuine news/analysis.

Guidelines:
- Assign 1-2 tags per category that best describe the article
- Be concise and accurate
- Consider the overall impression, not just individual words

Return ONLY a JSON object in this exact format (no markdown, no explanation):
{{
  "source_type": ["tag1"],
  "evidence": ["tag1"],
  "reasoning": ["tag1"],
  "tone": ["tag1"],
  "actionability": ["tag1"],
  "is_ad": false
}}"""

    def parse_tagging_response(response: str) -> Optional[dict]:
        """Parse tagging LLM response into dict. Returns None on failure."""
        try:
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(line for line in lines if not line.startswith("```"))
            return json.loads(text)
        except Exception:
            return None

    def submit_article(idx: int):
        """Submit BOTH extraction and tagging for an article at once.

        Tagging doesn't depend on extraction results - both just need article content.
        Submitting both together keeps the queue mixed and avoids batch-by-type behavior.
        """
        article = articles_to_process[idx]
        start_time = time.time()
        article_data[idx] = {
            "insights": [], "triples": [], "errors": [], "start_time": start_time,
            "extraction_done": False, "tagging_done": False
        }

        # Submit extraction
        extraction_prompt = build_extraction_prompt(article)
        if extraction_prompt:
            handle = gateway.submit_text(extraction_prompt, temperature=0.3)
            in_flight.append(("extraction", idx, article, handle, start_time, None))
        else:
            # Article too short - mark extraction as done
            article_data[idx]["extraction_done"] = True
            console.print(f"[dim][{idx + 1}/{total_articles}] {article.title[:50]}... (too short, skipped)[/dim]")

        # Submit tagging (if not already tagged)
        if not article.signal_tags:
            tagging_prompt = build_tagging_prompt(article)
            handle = gateway.submit_text(tagging_prompt, temperature=0.3)
            in_flight.append(("tagging", idx, article, handle, start_time, None))
        else:
            # Already tagged - mark tagging as done
            article_data[idx]["tagging_done"] = True

        # If BOTH are already done (too short + already tagged), finalize immediately
        # Otherwise this article would never be finalized since no completion event fires
        if article_data[idx]["extraction_done"] and article_data[idx]["tagging_done"]:
            maybe_finalize_article(idx, article)

    def fill_pipeline():
        """Submit new articles to keep pipeline full."""
        nonlocal next_extraction_idx
        # Each article adds up to 2 requests, so check against PIPELINE_SIZE
        while len(in_flight) < PIPELINE_SIZE and next_extraction_idx < total_articles:
            submit_article(next_extraction_idx)
            next_extraction_idx += 1

    def process_extraction_complete(idx: int, article: Article, response: str):
        """Handle completed extraction - process results."""
        nonlocal total_llm_calls

        data = article_data[idx]
        data["extraction_done"] = True

        # Article header
        console.print(f"[bold cyan][{idx + 1}/{total_articles}][/bold cyan] {article.title}")
        console.print("  [dim]- Extraction complete...[/dim]")

        if response is None:
            console.print("    [dim]Article too short, skipped[/dim]")
        else:
            total_llm_calls += 1
            try:
                extraction = process_extraction_response(response, article, kb)
                data["insights"] = extraction.insights
                data["triples"] = extraction.new_triples

                # Report insights
                for ins in extraction.insights:
                    stats["insights"] += 1
                    console.print(f"    [green]+[/green] {ins.content}")
                if not extraction.insights:
                    console.print("    [dim]No insights extracted[/dim]")

                # Report triples
                if extraction.new_triples:
                    console.print(f"    [green]+{len(extraction.new_triples)} new facts:[/green]")
                    for t in extraction.new_triples[:5]:
                        console.print(f"      [green]*[/green] {t.subject} -> {t.predicate} -> {t.object}")
                    if len(extraction.new_triples) > 5:
                        console.print(f"      [dim]...and {len(extraction.new_triples) - 5} more[/dim]")
                    stats["triples_new"] += len(extraction.new_triples)
                else:
                    console.print("    [dim]No new facts[/dim]")

                if extraction.existing_triples:
                    console.print(f"    [dim]~{len(extraction.existing_triples)} already known[/dim]")
                    stats["triples_existing"] += len(extraction.existing_triples)
                stats["triples"] += len(extraction.new_triples) + len(extraction.existing_triples)

                # Save extracted metadata
                if extraction.summary:
                    storage.update_summary(article.id, extraction.summary)
                    article.summary = extraction.summary
                if extraction.headline:
                    storage.update_headline(article.id, extraction.headline)
                    article.headline = extraction.headline
                if extraction.keywords:
                    storage.update_keywords(article.id, extraction.keywords)
                    article.keywords = json.dumps(extraction.keywords)

            except Exception as e:
                error_msg = f"Extraction failed: {e}"
                data["errors"].append(error_msg)
                console.print(f"    [red]ERROR: {error_msg}[/red]")
                stats["errors"] += 1

        # Check if article is fully done
        maybe_finalize_article(idx, article)

    def process_tagging_complete(idx: int, article: Article, response: str):
        """Handle completed tagging - store tags."""
        nonlocal total_llm_calls

        data = article_data[idx]
        data["tagging_done"] = True

        console.print(f"  [dim]- Tagging complete for [{idx + 1}]...[/dim]")

        if response:
            total_llm_calls += 1
            tags_data = parse_tagging_response(response)
            if tags_data:
                signal_tags = SignalTags(
                    source_type=tags_data.get("source_type", ["secondary"]),
                    evidence=tags_data.get("evidence", ["single-source"]),
                    reasoning=tags_data.get("reasoning", ["logical"]),
                    tone=tags_data.get("tone", ["factual"]),
                    actionability=tags_data.get("actionability", ["awareness"]),
                    is_ad=tags_data.get("is_ad", False),
                )
                storage.update_signal_tags(article.id, signal_tags.to_json())
                article.signal_tags = signal_tags.to_json()
                compact = signal_tags.to_compact_string()
                if compact:
                    console.print(f"    [magenta]signal: {compact}[/magenta]")
            else:
                data["errors"].append("Failed to parse tagging response")
                console.print(f"    [yellow]Could not parse tagging response[/yellow]")

        # Check if article is fully done
        maybe_finalize_article(idx, article)

    def maybe_finalize_article(idx: int, article: Article):
        """Finalize article if both extraction and tagging are complete."""
        nonlocal completed_count

        data = article_data[idx]

        # Only finalize when both are done
        if not (data["extraction_done"] and data["tagging_done"]):
            return

        # Mark article as analyzed and complete
        stats["processed"] += 1
        storage.mark_as_analyzed(article.id)
        completed_count += 1

        # Store processed data
        processed_articles.append({
            "article": article,
            "insights": data["insights"],
            "triples": data["triples"],
            "connections": [],
            "errors": data["errors"],
        })

        # Summary with timing and ETA
        article_elapsed = time.time() - data["start_time"]
        articles_remaining = total_articles - completed_count

        if articles_remaining > 0 and completed_count > 0:
            step_elapsed = time.time() - step_start
            rate_per_article = step_elapsed / completed_count
            eta_seconds = articles_remaining * rate_per_article
            eta_str = f"~{format_duration(eta_seconds)} remaining"

            if data["errors"]:
                console.print(f"  [yellow][!] {article_elapsed:.1f}s | {eta_str}[/yellow]")
            else:
                console.print(f"  [bold green][OK][/bold green] [dim]{article_elapsed:.1f}s | {eta_str}[/dim]")
        else:
            if data["errors"]:
                console.print(f"  [yellow][!] {article_elapsed:.1f}s[/yellow]")
            else:
                console.print(f"  [bold green][OK][/bold green] [dim]{article_elapsed:.1f}s[/dim]")
        console.print()

    # Initial submission: fill the pipeline
    fill_pipeline()

    # Process until all complete
    while in_flight:
        # Check each in-flight request
        for i, (work_type, idx, article, handle, start_time, extra) in enumerate(in_flight):
            if handle is None:
                # No LLM call needed (article too short) - shouldn't happen with new logic
                in_flight.pop(i)
                if work_type == "extraction":
                    process_extraction_complete(idx, article, None)
                else:
                    process_tagging_complete(idx, article, None)
                fill_pipeline()
                break

            # Try non-blocking collect
            response = gateway.try_collect_text(handle)
            if response is not None:
                in_flight.pop(i)
                if work_type == "extraction":
                    process_extraction_complete(idx, article, response)
                else:  # tagging
                    process_tagging_complete(idx, article, response)
                fill_pipeline()
                break
        else:
            # None completed yet, wait a bit
            time.sleep(0.1)

    # Summary with call counts
    step_elapsed = time.time() - step_start
    console.print(f"  [dim]Processed {completed_count} articles with {total_llm_calls} LLM calls ({step_elapsed:.1f}s)[/dim]")

    return processed_articles


# =============================================================================
# STEP 3: EMBEDDING PHASE
# =============================================================================

def _create_semantic_card(article: Article) -> str:
    """
    Create a semantic card for embedding.

    Combines LLM outputs into a structured text that embeds well.
    This is what we embed instead of the raw article.
    """
    parts = []

    # Title is always included
    parts.append(article.title)

    # Summary if available
    if article.summary:
        parts.append(article.summary)
    else:
        # Fallback to first 200 chars of content
        if article.content:
            parts.append(article.content[:200])

    # Trend categories
    if article.trend_tags:
        parts.append(f"Categories: {article.trend_tags}")

    # Signal type
    if article.signal_tags:
        try:
            import json
            tags = json.loads(article.signal_tags)
            if tags.get("source_type"):
                parts.append(f"Source type: {', '.join(tags['source_type'])}")
        except (json.JSONDecodeError, TypeError) as e:
            import sys
            print(f"Malformed signal tags for semantic card: {e}", file=sys.stderr)

    return ". ".join(parts)


def _run_embedding_phase(
    articles: list[Article],
    storage: Storage,
    kb: KnowledgeBase,
    stats: dict,
    embedding_service: EmbeddingService,
    limit: int = 0,
) -> int:
    """
    Step 4: Generate embeddings for new articles using semantic cards.

    Embeds the distilled semantic content, not raw article text.
    Uses shared embedding_service (model already loaded in pre-embedding phase).
    """
    console.print("[bold]Step 4:[/bold] Embedding new articles...")

    # Check embedding service availability
    if not embedding_service.is_available():
        console.print("  [red]ERROR: Embedding service not available[/red]")
        console.print("  [yellow]Story matching will be limited[/yellow]")
        console.print()
        return 0

    provider_info = embedding_service.get_provider_info()
    model_name = provider_info.get('model', '')
    if model_name and model_name != 'unknown':
        console.print(f"  [green]Using {provider_info.get('provider', 'unknown')} ({model_name})[/green]")
    else:
        console.print(f"  [green]Using {provider_info.get('provider', 'unknown')}[/green]")

    # Filter to articles needing embeddings
    needs_embedding = [a for a in articles if storage.get_embedding(a.id) is None]

    if not needs_embedding:
        console.print("  [dim]All articles already have embeddings[/dim]")
    else:
        progress = BatchProgress(len(needs_embedding), batch_size=EMBEDDING_BATCH_SIZE, label="articles")
        console.print(f"  Embedding {progress.total_items} articles in {progress.num_batches} batches...")

        for batch_num, batch in progress.iterate(needs_embedding):
            progress.start_batch()
            batch_success = 0
            batch_errors = 0
            limit_reached = False

            # Check limit before processing batch
            if limit > 0 and progress.total_processed >= limit:
                progress.end_batch(0, 0, stopped=True)
                break

            # Apply limit to batch
            if limit > 0:
                remaining = limit - progress.total_processed
                batch = batch[:remaining]

            try:
                # Create semantic cards for all articles in batch
                semantic_cards = [_create_semantic_card(article) for article in batch]
                # ONE API call for entire batch, preserving chunk data
                results = embedding_service.embed_batch_with_chunks(semantic_cards)

                # Save each result
                for article, (result, chunk_data) in zip(batch, results):
                    storage.save_embedding(article.id, result.vector)
                    storage.save_chunk_embeddings(article.id, chunk_data)
                    batch_success += 1
            except Exception as e:
                console.print(f"\n  [red]Batch embedding failed: {e}[/red]", end="")
                stats["errors"] += len(batch)
                batch_errors = len(batch)

            progress.end_batch(batch_success, batch_errors, stopped=limit_reached)

        progress.summary(f"Embedded {progress.total_processed} articles")
        stats["embeddings_generated"] = progress.total_processed

    # Trend tagging (embedding-based categorization)
    # This belongs in embedding phase because it uses embeddings
    # Only tag articles that HAVE embeddings - skip those that don't
    needs_trends = [a for a in articles if not a.trend_tags and storage.get_embedding(a.id) is not None]
    if needs_trends:
        progress = BatchProgress(len(needs_trends), batch_size=EMBEDDING_BATCH_SIZE, label="articles")
        console.print(f"  Tagging {progress.total_items} articles with trend categories...")

        for batch_num, batch in progress.iterate(needs_trends):
            progress.start_batch()
            batch_success = 0
            batch_errors = 0

            for article in batch:
                try:
                    tags = analyze_article(article, embedding_service=embedding_service, storage=storage)
                    storage.update_trends(article.id, tags)
                    article.trend_tags = tags
                    batch_success += 1
                except Exception as e:
                    console.print(f"\n      [red]ERROR tagging {article.title[:30]}: {e}[/red]")
                    stats["errors"] += 1
                    batch_errors += 1

            progress.end_batch(batch_success, batch_errors)

        progress.summary(f"Tagged {progress.total_processed} articles with trends")

    # Any new stories created during LLM phase need embeddings
    stories = storage.get_active_stories()
    stories_needing_embedding = [s for s in stories if not embedding_service.get_embedding(s.id, "story")]

    if stories_needing_embedding:
        progress = BatchProgress(len(stories_needing_embedding), batch_size=EMBEDDING_BATCH_SIZE, label="stories")
        console.print(f"  Embedding {progress.total_items} new stories in {progress.num_batches} batches...")

        for batch_num, batch in progress.iterate(stories_needing_embedding):
            progress.start_batch()
            batch_success = 0
            batch_errors = 0
            limit_reached = False

            for story in batch:
                if limit > 0 and progress.total_processed + batch_success >= limit:
                    limit_reached = True
                    break
                try:
                    result = embedding_service.embed_story(story)
                    embedding_service.save_embedding(story.id, "story", result)
                    batch_success += 1
                except Exception as e:
                    console.print(f"\n  [red]ERROR: {e}[/red]", end="")
                    stats["errors"] += 1
                    batch_errors += 1

            progress.end_batch(batch_success, batch_errors, stopped=limit_reached)
            if limit_reached:
                break

        if progress.total_processed > 0:
            progress.summary(f"Embedded {progress.total_processed} new stories")
            stats["story_embeddings_generated"] = stats.get("story_embeddings_generated", 0) + progress.total_processed

    console.print()
    return len(needs_embedding)


# =============================================================================
# STEP 4.5: CLUSTER-BASED CONNECTION DETECTION
# =============================================================================

def _cluster_insights_by_similarity(
    insights: list,
    embedding_service: EmbeddingService,
    similarity_threshold: float = 0.75,
) -> list[list]:
    """Cluster insights by embedding similarity using FAISS.

    Uses a greedy clustering approach:
    1. Pick first unassigned insight
    2. Find all similar insights above threshold
    3. Group them as a cluster
    4. Repeat with remaining unassigned

    Args:
        insights: List of Insight objects to cluster
        embedding_service: EmbeddingService for similarity search
        similarity_threshold: Minimum similarity to be in same cluster

    Returns:
        List of clusters, where each cluster is a list of (insight, embedding) tuples
    """
    # Get embeddings for all insights
    insight_embeddings = []
    for ins in insights:
        emb = embedding_service.get_embedding(ins.id, "insight")
        if emb:
            insight_embeddings.append((ins, emb))

    if not insight_embeddings:
        return []

    clusters = []
    assigned = set()

    for ins, emb in insight_embeddings:
        if ins.id in assigned:
            continue

        # Start new cluster with this insight
        cluster = [(ins, emb)]
        assigned.add(ins.id)

        # Find similar insights via FAISS
        similar_results = embedding_service.find_similar(
            query_vector=emb,
            target_type="insight",
            threshold=similarity_threshold,
            limit=50,
        )

        # Add similar unassigned insights to this cluster
        for target_id, similarity in similar_results:
            if target_id in assigned or target_id == ins.id:
                continue

            # Find the insight in our list
            for other_ins, other_emb in insight_embeddings:
                if other_ins.id == target_id and other_ins.id not in assigned:
                    cluster.append((other_ins, other_emb))
                    assigned.add(other_ins.id)
                    break

        if len(cluster) >= 2:  # Only keep clusters with 2+ insights
            clusters.append(cluster)

    return clusters


# Adaptive cluster sizing - learns system capacity through retry
# Start optimistic, shrink on timeout, track what works
_learned_max_cluster_size = 50  # Start optimistic, will shrink on failures
_min_cluster_size = 5  # Don't go below this


def split_cluster_in_half(cluster: list) -> list[list]:
    """Split a cluster into two halves for retry after timeout.

    Args:
        cluster: List of (insight, embedding) tuples

    Returns:
        List of two cluster halves (or single cluster if too small to split)
    """
    if len(cluster) <= _min_cluster_size:
        return [cluster]  # Can't split further

    mid = len(cluster) // 2
    first_half = cluster[:mid]
    second_half = cluster[mid:]

    result = []
    if len(first_half) >= 2:
        result.append(first_half)
    if len(second_half) >= 2:
        result.append(second_half)

    return result if result else [cluster]


def update_learned_max_size(failed_size: int):
    """Update learned max size after a timeout failure.

    Only learns from clusters large enough to be meaningful indicators.
    Small cluster timeouts suggest LLM issues, not capacity limits.
    """
    global _learned_max_cluster_size

    # Only learn from clusters that are meaningfully large
    # A size-2 timeout is an LLM problem, not a capacity problem
    min_learning_threshold = 10
    if failed_size < min_learning_threshold:
        console.print(f"      [dim]Timeout on small cluster ({failed_size}) - not adjusting capacity[/dim]")
        return

    # Shrink to 75% of failed size (not half, to find sweet spot faster)
    new_max = max(_min_cluster_size, int(failed_size * 0.75))
    if new_max < _learned_max_cluster_size:
        _learned_max_cluster_size = new_max
        console.print(f"      [yellow]Learned: max cluster size now {_learned_max_cluster_size}[/yellow]")


def chunk_large_cluster(cluster: list, max_size: int = None) -> list[list]:
    """Split large clusters based on learned system capacity.

    Args:
        cluster: List of (insight, embedding) tuples
        max_size: Override max size (uses learned size if None)

    Returns:
        List of cluster chunks
    """
    if max_size is None:
        max_size = _learned_max_cluster_size

    if len(cluster) <= max_size:
        return [cluster]

    # Split into chunks based on learned capacity
    chunks = []
    for i in range(0, len(cluster), max_size):
        chunk = cluster[i:i + max_size]
        if len(chunk) >= 2:
            chunks.append(chunk)

    return chunks if chunks else [cluster[:max_size]]


def build_cluster_analysis_prompt(cluster: list) -> str:
    """Build prompt for analyzing a cluster of similar insights.

    Args:
        cluster: List of (insight, embedding) tuples

    Returns:
        Prompt string for LLM
    """
    if len(cluster) < 2:
        return ""

    # Build cluster content for prompt
    insights_text = ""
    for i, (ins, _) in enumerate(cluster):
        insights_text += f"\n{i+1}. [{ins.insight_type}] {ins.content}"

    return f"""Analyze this cluster of semantically similar insights and extract structured knowledge.

INSIGHTS IN CLUSTER:{insights_text}

Extract:
1. THEME: The overarching topic connecting these insights (1-3 words)
2. SUBCATEGORIES: Specific aspects or subtopics within the theme
3. RELATIONSHIPS: How insights relate to each other as subject-predicate-object triples

Return as JSON:
{{
  "theme": "Main Theme",
  "subcategories": ["subtopic1", "subtopic2"],
  "triples": [
    {{"subject": "Theme or insight concept", "predicate": "contains|relates_to|implies|contradicts|supports", "object": "Related concept or subcategory"}},
    {{"subject": "Insight 1 concept", "predicate": "confirms|refines|extends|contradicts", "object": "Insight 2 concept"}}
  ],
  "insight_relationships": [
    {{"source_index": 1, "target_index": 2, "relationship": "confirms|contradicts|refines|extends"}}
  ]
}}

Return ONLY valid JSON."""


def parse_cluster_analysis_response(
    response: str,
    cluster: list,
    kb: KnowledgeBase,
) -> tuple[list, list]:
    """Parse cluster analysis response and save to knowledge base.

    Args:
        response: LLM response text
        cluster: List of (insight, embedding) tuples
        kb: Knowledge base to save triples to

    Returns:
        Tuple of (new_triples, connections_found)
    """
    import json
    import uuid
    from datetime import datetime
    from .knowledge import Triple, Relationship
    from .schema import extract_json_from_response

    if not response or len(cluster) < 2:
        return [], []

    try:
        json_str = extract_json_from_response(response)
        data = json.loads(json_str)

        new_triples = []
        connections = []

        theme = data.get("theme", "")
        subcategories = data.get("subcategories", [])

        # Create triples for theme -> subcategory relationships
        if theme and subcategories:
            for subcat in subcategories[:5]:  # Limit to 5 subcategories
                triple = Triple(
                    id=str(uuid.uuid4()),
                    subject=theme,
                    predicate="has_aspect",
                    object=subcat,
                    subject_type="concept",
                    object_type="concept",
                    confidence="medium",
                )
                if kb.save_triple(triple):
                    new_triples.append(triple)

        # Create triples from the extracted relationships
        for t_data in data.get("triples", []):
            if not isinstance(t_data, dict):
                continue
            subject = t_data.get("subject", "")
            predicate = t_data.get("predicate", "")
            obj = t_data.get("object", "")

            if subject and predicate and obj:
                triple = Triple(
                    id=str(uuid.uuid4()),
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    subject_type="concept",
                    object_type="concept",
                    confidence="medium",
                )
                if kb.save_triple(triple):
                    new_triples.append(triple)

        # Create insight-to-insight relationships
        for rel_data in data.get("insight_relationships", []):
            if not isinstance(rel_data, dict):
                continue

            src_idx = rel_data.get("source_index", 0) - 1  # 1-indexed in prompt
            tgt_idx = rel_data.get("target_index", 0) - 1
            rel_type = rel_data.get("relationship", "").lower()

            if src_idx < 0 or tgt_idx < 0 or src_idx >= len(cluster) or tgt_idx >= len(cluster):
                continue
            if rel_type not in {"confirms", "contradicts", "refines", "extends"}:
                continue

            src_ins, src_emb = cluster[src_idx]
            tgt_ins, tgt_emb = cluster[tgt_idx]

            # Compute actual similarity from embeddings
            similarity = _cosine_similarity(src_emb, tgt_emb)

            relationship = Relationship(
                id=str(uuid.uuid4()),
                source_insight_id=src_ins.id,
                target_insight_id=tgt_ins.id,
                relationship_type=rel_type,
                strength=similarity,
                detected_at=datetime.now(),
            )
            kb.save_relationship(relationship)
            connections.append(relationship)

        return new_triples, connections

    except json.JSONDecodeError as e:
        import sys
        print(f"JSON parsing failed for cluster analysis: {e}", file=sys.stderr)
        return [], []
    except Exception as e:
        import sys
        print(f"Cluster analysis parsing failed: {e}", file=sys.stderr)
        return [], []


def _analyze_cluster_for_triples(
    cluster: list,
    provider,
    kb: KnowledgeBase,
) -> tuple[list, list]:
    """Analyze a cluster of similar insights and extract theme/relationship triples.

    DEPRECATED: Use build_cluster_analysis_prompt + parse_cluster_analysis_response
    with submit/collect pattern for batching.

    Args:
        cluster: List of (insight, embedding) tuples
        provider: LLM provider
        kb: Knowledge base to save triples to

    Returns:
        Tuple of (new_triples, connections_found)
    """
    prompt = build_cluster_analysis_prompt(cluster)
    if not prompt:
        return [], []

    try:
        response = provider.generate(prompt, max_tokens=800)
        return parse_cluster_analysis_response(response, cluster, kb)
    except Exception as e:
        import sys
        print(f"Cluster analysis failed: {e}", file=sys.stderr)
        return [], []


def _run_connection_detection(
    processed_articles: list[dict],
    kb: KnowledgeBase,
    provider,
    stats: dict,
    embedding_service: EmbeddingService,
    limit: int = 0,
) -> None:
    """
    Detect connections using cluster-based analysis.

    ARCHITECTURE:
    1. Embed all new insights (EMBEDDING MODEL - batched)
    2. Cluster insights by similarity (NO MODEL - FAISS math)
    3. Analyze each cluster for themes/relationships (TEXT MODEL - O(clusters) calls)

    This is O(clusters) LLM calls instead of O(N) - much more efficient.
    Output goes directly to knowledge graph as queryable triples.

    Args:
        processed_articles: List of dicts from LLM phase, each with "insights" list
        kb: Knowledge base
        provider: LLM provider for cluster analysis
        stats: Statistics dict to update
        embedding_service: Embedding service
    """
    # Collect all insights from this session
    all_insights = []
    for item in processed_articles:
        for ins in item.get("insights", []):
            all_insights.append(ins)

    if not all_insights:
        return

    console.print("[bold]Step 4.5:[/bold] Detecting connections (cluster-based)...")

    # Ensure embedding model is loaded (LLM phase switched to text model)
    # This is required because the _model_loaded flag in LMStudioProvider
    # becomes stale after the LLM phase - the gateway needs to switch back
    from safe_loading_gateway import get_gateway
    gateway = get_gateway()
    if gateway and gateway.is_available():
        try:
            gateway.request_embedding("model_load_trigger")
        except Exception:
            pass  # Best effort - batch embedding will fail more clearly if needed

    # =========================================================================
    # PHASE 1: Batch embed all new insights (EMBEDDING MODEL)
    # =========================================================================
    insights_to_embed = []
    for ins in all_insights:
        existing = embedding_service.get_embedding(ins.id, "insight")
        if not existing:
            insights_to_embed.append(ins)

    if insights_to_embed:
        progress = BatchProgress(len(insights_to_embed), batch_size=EMBEDDING_BATCH_SIZE, label="insights")
        console.print(f"  Embedding {progress.total_items} new insights in {progress.num_batches} batches...")

        for batch_num, batch in progress.iterate(insights_to_embed):
            progress.start_batch()
            batch_success = 0
            batch_errors = 0

            try:
                # Batch embed all insights at once
                texts = [ins.content for ins in batch]
                results = embedding_service.embed_batch(texts)

                # Save each result
                for ins, result in zip(batch, results):
                    embedding_service.save_embedding(ins.id, "insight", result)
                    batch_success += 1
            except Exception as e:
                console.print(f"\n      [red]Batch embedding failed: {e}[/red]")
                stats["errors"] += len(batch)
                batch_errors = len(batch)

            progress.end_batch(batch_success, batch_errors)

        progress.summary(f"Embedded {progress.total_processed} insights")
    else:
        console.print(f"  [dim]All {len(all_insights)} insights already embedded[/dim]")

    # =========================================================================
    # PHASE 2: Cluster insights by similarity (NO MODEL - FAISS only)
    # =========================================================================
    console.print(f"  [dim]Clustering insights by similarity...[/dim]")

    # Cluster ALL historical insights (fast FAISS math)
    all_kb_insights = kb.get_insights()
    clusters = _cluster_insights_by_similarity(
        all_kb_insights,
        embedding_service,
        similarity_threshold=0.75,
    )

    if not clusters:
        console.print(f"  [dim]No insight clusters found[/dim]")
        console.print()
        return

    console.print(f"  [green]Found {len(clusters)} clusters[/green]")

    # =========================================================================
    # PHASE 3: Analyze clusters (TEXT MODEL - sliding window to prevent queue buildup)
    # =========================================================================
    from safe_loading_gateway import get_gateway, GatewayError

    gateway = get_gateway()
    gateway.timeout = 600  # Generous timeout for legitimate long operations

    # Apply limit to clusters
    clusters_to_process = clusters[:limit] if limit > 0 else clusters

    # Sliding window prevents queue buildup that causes queue-based timeouts
    # Keep only MAX_IN_FLIGHT requests pending at once
    MAX_IN_FLIGHT = 10
    total_triples = 0
    total_connections = 0
    total_llm_calls = 0

    # Flatten clusters into work items (chunks)
    work_items = []
    for cluster in clusters_to_process:
        chunks = chunk_large_cluster(cluster)
        for chunk in chunks:
            prompt = build_cluster_analysis_prompt(chunk)
            if prompt:
                work_items.append((chunk, prompt))

    # Process in batches of 10 with timing/ETA like rest of app
    REPORT_BATCH_SIZE = 10
    num_batches = (len(work_items) + REPORT_BATCH_SIZE - 1) // REPORT_BATCH_SIZE
    console.print(f"  Analyzing {len(clusters_to_process)} clusters ({len(work_items)} work items) in {num_batches} batches...")

    # Sliding window: submit up to MAX_IN_FLIGHT, collect as they complete, refill
    pending = []  # (chunk, handle, prompt) tuples
    work_idx = 0
    total_errors = 0
    completed = 0
    batch_times = []
    batch_start = time.time()
    batch_num = 1

    def submit_next():
        """Submit next work item if available."""
        nonlocal work_idx, total_llm_calls
        if work_idx < len(work_items):
            chunk, prompt = work_items[work_idx]
            handle = gateway.submit_text(prompt, temperature=0.3)
            pending.append((chunk, handle, prompt))
            work_idx += 1
            total_llm_calls += 1
            return True
        return False

    def process_result(chunk, handle, prompt):
        """Collect result and handle errors. Returns (triples, connections, should_retry, retry_prompt)."""
        nonlocal total_errors
        try:
            response = gateway.collect_text(handle)
            new_triples, connections = parse_cluster_analysis_response(response, chunk, kb)
            stats["connections"] += len(connections)
            stats["cluster_triples"] += len(new_triples)
            return len(new_triples), len(connections), False, None
        except GatewayError as e:
            if "Timeout" in str(e):
                # Timeout - resubmit (likely never started due to queue)
                return 0, 0, True, prompt
            else:
                console.print(f" [red]error[/red]")
                stats["errors"] += 1
                total_errors += 1
                return 0, 0, False, None
        except Exception as e:
            console.print(f" [red]error: {e}[/red]")
            stats["errors"] += 1
            total_errors += 1
            return 0, 0, False, None

    def get_eta():
        """Calculate ETA based on average batch time."""
        if not batch_times:
            return ""
        avg_time = sum(batch_times) / len(batch_times)
        remaining_batches = num_batches - batch_num
        eta_seconds = avg_time * remaining_batches
        if eta_seconds < 1:
            return ""
        return f"~{format_duration(eta_seconds)} remaining"

    # Initial fill of the window
    while len(pending) < MAX_IN_FLIGHT and submit_next():
        pass

    # Print first batch header
    console.print(f"    [dim]Batch {batch_num}/{num_batches}...[/dim]", end="")

    # Process until all work complete
    retries = 0
    while pending:
        # Collect first pending result
        chunk, handle, prompt = pending.pop(0)
        triples, connections, should_retry, retry_prompt = process_result(chunk, handle, prompt)

        total_triples += triples
        total_connections += connections

        if should_retry:
            # Resubmit timed-out request
            new_handle = gateway.submit_text(retry_prompt, temperature=0.3)
            pending.append((chunk, new_handle, retry_prompt))
            total_llm_calls += 1
            retries += 1
        else:
            # Refill window with new work
            submit_next()
            completed += 1

        # Check if batch complete (every REPORT_BATCH_SIZE completions)
        if completed > 0 and completed % REPORT_BATCH_SIZE == 0:
            batch_duration = time.time() - batch_start
            batch_times.append(batch_duration)

            # Print batch completion
            retry_msg = f", {retries} retries" if retries > 0 else ""
            console.print(f" [green]done[/green] [dim]({format_duration(batch_duration)}){retry_msg}[/dim]")

            batch_num += 1
            retries = 0
            batch_start = time.time()

            # Print next batch header if more work
            if completed < len(work_items):
                eta = get_eta()
                eta_str = f" [{eta}]" if eta else ""
                console.print(f"    [dim]Batch {batch_num}/{num_batches}{eta_str}...[/dim]", end="")

    # Final partial batch
    if completed % REPORT_BATCH_SIZE != 0:
        batch_duration = time.time() - batch_start
        batch_times.append(batch_duration)
        retry_msg = f", {retries} retries" if retries > 0 else ""
        console.print(f" [green]done[/green] [dim]({format_duration(batch_duration)}){retry_msg}[/dim]")

    total_time = sum(batch_times)
    console.print(f"  [green]Added {total_triples} triples, {total_connections} connections[/green] [dim]({format_duration(total_time)} total)[/dim]")
    if total_errors > 0:
        console.print(f"  [yellow]{total_errors} errors[/yellow]")
    console.print()


# =============================================================================
# STEP 5: STORY MATCHING (Batched)
# =============================================================================

def _run_story_matching(
    articles: list[Article],
    storage: Storage,
    kb: KnowledgeBase,
    provider,
    stats: dict,
    embedding_service: EmbeddingService,
    limit: int = 0,
) -> None:
    """
    Step 5: Match articles to stories using embeddings.

    Uses the semantic embeddings generated in Step 4 to find
    related stories for each article.

    Architecture (process once, use many times):
    - PASS 1: Find matches (embedding-only, no LLM)
    - PASS 2: Create new stories using ALREADY EXTRACTED data (NO LLM calls)
    """
    console.print("[bold]Step 5:[/bold] Matching articles to stories...")

    clusterer = StoryClusterer(provider, storage, kb, embedding_service=embedding_service)

    # Apply limit
    articles_to_process = articles[:limit] if limit > 0 else articles

    console.print(f"  Processing {len(articles_to_process)} articles...")

    # =========================================================================
    # PASS 1: Find matches (embedding-only, no LLM)
    # =========================================================================
    matched_articles = []  # (article, story)
    needs_new_story = []   # articles that need new stories

    step_start = time.time()
    for article in articles_to_process:
        embedding = storage.get_embedding(article.id)
        if not embedding:
            needs_new_story.append(article)
            continue

        matched_story = clusterer.find_matching_story_with_embedding(article, embedding)
        if matched_story:
            matched_articles.append((article, matched_story))
        else:
            needs_new_story.append(article)

    match_time = time.time() - step_start
    console.print(f"  [dim]Pass 1 (matching): {len(matched_articles)} matched, {len(needs_new_story)} need new stories ({match_time:.1f}s)[/dim]")

    # =========================================================================
    # Update matched articles (no LLM needed)
    # =========================================================================
    matched = 0
    for article, story in matched_articles:
        try:
            clusterer.update_story_with_article(story, article)
            matched += 1
        except Exception as e:
            console.print(f"    [red]ERROR updating story for '{article.title[:40]}': {e}[/red]")
            stats["errors"] += 1

    # =========================================================================
    # PASS 2: Create new stories (NO LLM - uses already extracted data)
    # =========================================================================
    created = 0

    if needs_new_story:
        console.print(f"  Creating {len(needs_new_story)} new stories (using extracted metadata, 0 LLM calls)...")

        create_start = time.time()
        for i, article in enumerate(needs_new_story):
            try:
                # create_new_story uses article's headline/summary/keywords
                # which were extracted during Step 3 - NO LLM calls here
                story = clusterer.create_new_story(article)
                created += 1

                # Progress indicator every 20 stories
                if (i + 1) % 20 == 0:
                    console.print(f"    [dim]Created {i+1}/{len(needs_new_story)} stories...[/dim]")

            except Exception as e:
                console.print(f"    [red]ERROR creating story for '{article.title[:40]}': {e}[/red]")
                stats["errors"] += 1

        create_time = time.time() - create_start
        console.print(f"    [green]Created {created} stories in {create_time:.1f}s (0 LLM calls)[/green]")

    console.print()
    console.print(f"  [green]Matched {matched} articles to existing stories[/green]")
    console.print(f"  [green]Created {created} new stories[/green]")

    stats["stories_matched"] = matched
    stats["stories_created"] = created

    console.print()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def generate_report(
    skip_summarized: bool = True,
    db_path: str = "articles.db",
    kb_path: str = "knowledge.db",
    feeds_file: str = "config/feeds.txt",
    limit: int = 0,  # UNIVERSAL limit for ALL steps (0=unlimited)
    force_setup: bool = False,  # Force setup wizard to run
) -> dict:
    """
    Generate a comprehensive report with self-healing pipeline.

    Pipeline:
    1. Verification - Check for gaps from interrupted runs
    2. LLM Phase - Generate summaries, facts, tags
    3. Embedding Phase - Embed semantic cards
    4. Story Matching - Match articles to stories

    NO SILENT FAILURES - Every error is surfaced.
    """
    # Register cleanup handlers to prevent orphaned gateway requests on cancel
    _register_cleanup()

    storage = Storage(db_path)
    add_perspective_methods(storage)
    kb = KnowledgeBase(kb_path)

    # Create EmbeddingService ONCE - shared across all phases
    embedding_service = EmbeddingService(kb)

    session_start = datetime.now()

    stats = {
        "fetched": 0,
        "new": 0,
        "processed": 0,
        "embeddings_generated": 0,
        "story_embeddings_generated": 0,
        "insights": 0,
        "triples": 0,
        "triples_new": 0,
        "triples_existing": 0,
        "cluster_triples": 0,  # Triples from cluster analysis
        "connections": 0,
        "stories_matched": 0,
        "stories_created": 0,
        "errors": 0,
        "session_start": session_start,  # For filtering session-only data
    }

    # Get LLM provider
    provider, is_llm = get_best_provider()
    if not is_llm:
        console.print("[red]ERROR: No LLM available.[/red]")
        console.print(get_setup_instructions())
        return stats

    console.print()
    console.print(Panel(f"[bold]Generating Report[/bold]\n[dim]Using {provider.name}[/dim]", style="blue"))
    console.print()

    # Check if user has set up interests - auto-launch setup wizard if not
    context_store = UserContextStore()
    profile = context_store.load_profile()
    if force_setup or (not profile.watching and not profile.current_projects):
        if force_setup:
            console.print(Panel(
                "[cyan]Configure your interests and RSS feeds[/cyan]",
                title="[bold]Setup Wizard[/bold]",
                style="cyan"
            ))
        else:
            console.print(Panel(
                "[yellow]No interests configured yet![/yellow]\n\n"
                "Let's set up your interests for personalized briefings.",
                title="[bold]First-Time Setup[/bold]",
                style="yellow"
            ))
        console.print()

        # Try to run interactive setup wizard
        try:
            from .cli_context import run_setup_wizard_inline, QUESTIONARY_AVAILABLE
            if QUESTIONARY_AVAILABLE:
                run_setup_wizard_inline(context_store)
                # Reload profile after wizard completes
                profile = context_store.load_profile()
                console.print()
            else:
                console.print("[dim]Install questionary for interactive setup: pip install questionary[/dim]")
                console.print("[dim]Or use: rss context watch \"AI\" to add topics manually[/dim]")
                console.print()
        except (ImportError, Exception) as e:
            # Fall back to manual instructions if wizard fails
            console.print("[dim]Set up interests with: rss context setup[/dim]")
            console.print("[dim]Or: rss context watch \"AI\"[/dim]")
            console.print()

    # Fetch latest articles
    console.print("[bold]Fetching:[/bold] Latest articles...")
    feeds = load_feeds(feeds_file)
    new_article_ids = []
    stats["feeds_count"] = len(feeds) if feeds else 0

    if feeds:
        fetch_results = fetch_all_feeds(feeds_file, storage)
        for result in fetch_results:
            stats["fetched"] += result["fetched"]
            stats["new"] += result["new"]
            new_article_ids.extend(result.get("new_article_ids", []))

        if stats["new"] > 0:
            console.print(f"  [green]Found {stats['new']} new articles[/green]")
        else:
            console.print(f"  [dim]No new articles (checked {len(feeds)} feeds)[/dim]")
    else:
        console.print("  [yellow]No feeds configured[/yellow]")

    console.print()

    # Select articles to process
    console.print("[bold]Selecting:[/bold] Articles to analyze...")

    MIN_CONTENT_LENGTH = 100

    # Auto-mark short articles as analyzed (skipped) - they'll never be long enough to process
    # This prevents them from accumulating in the unanalyzed backlog forever
    skipped_short = storage.mark_short_articles_as_skipped(MIN_CONTENT_LENGTH)
    if not isinstance(skipped_short, int):
        skipped_short = 0  # Handle mocked storage in tests

    # Get ALL articles with gaps (missing summary, tags, or embedding) - fill the backlog
    articles = storage.get_articles_with_gaps(exclude_spam=True, min_content_length=MIN_CONTENT_LENGTH)

    if not articles and new_article_ids:
        articles = storage.get_articles_by_ids(new_article_ids)
        # Also filter new articles by content length
        articles = [a for a in articles if a.content and len(a.content) >= MIN_CONTENT_LENGTH]

    # Short articles already filtered at DB level - no noise about them

    # Filter spam
    articles, spam_articles = filter_articles(articles, storage, threshold=0.7)
    skipped_as_spam = len(spam_articles)

    # Cleanup old spam
    deleted_spam = cleanup_old_spam(storage, days=30)

    # Report filtering - only actionable info
    filter_msgs = []
    if skipped_short > 0:
        filter_msgs.append(f"{skipped_short} short skipped")
    if skipped_as_spam > 0:
        filter_msgs.append(f"{skipped_as_spam} spam")
    if deleted_spam > 0:
        filter_msgs.append(f"{deleted_spam} old spam deleted")

    if filter_msgs:
        console.print(f"  [dim]Processing {len(articles)} articles ({', '.join(filter_msgs)})[/dim]")
    else:
        console.print(f"  [dim]Processing {len(articles)} articles[/dim]")

    if not articles:
        console.print()
        console.print("[yellow]No articles to process.[/yellow]")
        return stats

    # Warn about large processing jobs and suggest limit option
    LARGE_BATCH_THRESHOLD = 20
    if len(articles) > LARGE_BATCH_THRESHOLD and limit == 0:
        console.print()
        console.print(f"[yellow]Warning: {len(articles)} articles to process - this could take a while[/yellow]")
        console.print("[yellow]Tip: Use 'rss report -m 5' to process 5 articles before generating the briefing[/yellow]")
        console.print("[dim]     Use 'rss report --help' for more options[/dim]")
        console.print()

    console.print()

    # Track total pipeline time
    pipeline_start = time.time()

    # Run pipeline twice - second pass catches anything created in first pass
    for pass_num in range(2):
        if pass_num == 1:
            console.print("[bold]Verification Pass:[/bold]\n")
        gaps = _timed("Step 1", _run_verification_step, storage, kb, articles, embedding_service, limit, MIN_CONTENT_LENGTH, new_article_ids)
        _timed("Step 2", _run_pre_embedding_phase, storage, kb, embedding_service, stats, limit)
        processed_articles = _timed("Step 3", _run_llm_phase, gaps["articles_needing_llm"], storage, kb, provider, stats, embedding_service, limit)
        _timed("Step 4", _run_embedding_phase, gaps["articles_needing_embedding"], storage, kb, stats, embedding_service, limit)
        _timed("Step 4.5", _run_connection_detection, processed_articles, kb, provider, stats, embedding_service, limit)
        _timed("Step 5", _run_story_matching, articles, storage, kb, provider, stats, embedding_service, limit)

    # Show total pipeline time
    total_time = time.time() - pipeline_start
    stats["pipeline_duration"] = total_time  # Store for session stats display
    console.print(f"[green]Pipeline completed in {format_duration(total_time)}[/green]\n")

    # Final Report
    _show_final_report(processed_articles, stats, kb, provider, storage)

    return stats


def _show_final_report(
    processed_articles: list,
    stats: dict,
    kb: KnowledgeBase,
    provider,
    storage: Optional[Storage] = None,
) -> None:
    """Generate the intelligence briefing per REPORT_DESIGN_SPEC.md.

    Sections:
    1. Top Priority - 1-3 must-read items
    2. Your Interest Areas - Dynamic sections based on tracked topics
    3. Discovered Connections - Cross-source synthesis
    4. Knowledge Graph Updates - New entities/relationships
    5. Quick Scan - Everything else
    6. Session Stats - Processing summary
    """
    console.print()
    console.print(Panel("[bold]INTELLIGENCE BRIEFING[/bold]", style="blue"))
    console.print()

    # Load user context for personalization
    ctx_store = UserContextStore()
    profile = ctx_store.load_profile()

    # Score articles for priority ranking
    scored_articles = _score_articles_for_briefing(processed_articles, profile, kb)

    # =========================================================================
    # SECTION 1: TOP PRIORITY
    # =========================================================================
    console.print("[bold cyan]## TOP PRIORITY[/bold cyan]")
    console.print("[dim]Items you cannot skip today[/dim]")
    console.print()

    top_items = scored_articles[:3]  # Top 3 by score

    if top_items:
        for i, item in enumerate(top_items, 1):
            article = item["article"]
            insights = item.get("insights", [])

            # Headline (our framing)
            console.print(f"[bold]{i}. {article.title}[/bold]")

            # Why this matters (personalized if possible)
            why_matters = _explain_relevance(article, profile, item.get("relevance_reason", ""))
            if why_matters:
                console.print(f"   [yellow]Why it matters:[/yellow] {why_matters}")

            # Key insight
            if insights:
                insight = insights[0]
                # Handle both Insight objects and strings
                insight_text = insight.content if hasattr(insight, 'content') else str(insight)
                console.print(f"   [green]Key insight:[/green] {insight_text}")

            # Signal tags - parse and display cleanly
            if article.signal_tags:
                try:
                    import json
                    tags = json.loads(article.signal_tags)
                    tag_parts = []
                    for key, val in tags.items():
                        if key != "is_ad" and val:
                            if isinstance(val, list):
                                tag_parts.extend(val)
                            elif val is True:
                                tag_parts.append(key)
                    # Deduplicate while preserving order
                    tag_parts = list(dict.fromkeys(tag_parts))
                    console.print(f"   [dim]Signal: {', '.join(tag_parts)}[/dim]")
                except (json.JSONDecodeError, TypeError):
                    console.print(f"   [dim]Signal: {article.signal_tags}[/dim]")

            # What we know - facts extracted FROM this specific article during this session
            # Use item["triples"] directly - these are the triples we JUST extracted from THIS article
            # Don't query the KB which could return old/wrong data
            article_triples = item.get("triples", [])[:3]  # Show up to 3 facts

            if article_triples:
                console.print(f"   [blue]What we know:[/blue]")
                for t in article_triples:
                    console.print(f"      - {t.subject} {t.predicate} {t.object}")

            # Developing story?
            if article.story_id and storage:
                story = storage.get_story(article.story_id)
                if story and len(story.article_ids) > 1:
                    console.print(f"   [magenta]Developing story ({len(story.article_ids)} articles)[/magenta]")
            elif article.story_id:
                console.print(f"   [magenta]Developing story[/magenta]")

            # Source
            console.print(f"   [dim]{article.link}[/dim]")
            console.print()
    else:
        console.print("   [dim]No high-priority items this session.[/dim]")
        console.print()

    # =========================================================================
    # SECTION 2: YOUR INTEREST AREAS
    # =========================================================================
    console.print("[bold cyan]## YOUR INTEREST AREAS[/bold cyan]")

    # Get user's tracked topics
    tracked_topics = profile.watching + profile.current_projects

    if tracked_topics:
        for topic in tracked_topics[:5]:  # Max 5 interest sections
            matching = [item for item in scored_articles
                       if _article_matches_topic(item["article"], topic)]

            if matching:
                console.print(f"\n[bold]{topic}[/bold]")
                for item in matching[:3]:
                    article = item["article"]
                    console.print(f"  - {article.title}")
                    if item.get("insights"):
                        insight = item['insights'][0]
                        insight_text = insight.content if hasattr(insight, 'content') else str(insight)
                        console.print(f"    [dim]{insight_text}[/dim]")
    else:
        # Prominent notice - interests are key to personalized briefings
        console.print()
        console.print("[yellow]  This section is empty because you haven't set up interests yet.[/yellow]")
        console.print("  [bold]Set up your interests to get personalized content:[/bold]")
        console.print("    rss context watch \"AI Safety\"      - Track a topic")
        console.print("    rss context add project \"My App\"   - Track a project")
        console.print("    rss context list                   - See your interests")
    console.print()

    # =========================================================================
    # SECTION 3: DISCOVERED CONNECTIONS
    # =========================================================================
    console.print("[bold cyan]## DISCOVERED CONNECTIONS[/bold cyan]")
    console.print("[dim]Insights from combining multiple sources[/dim]")
    console.print()

    # First check in-memory connections (from article-level processing)
    all_connections = []
    for item in processed_articles:
        for conn in item.get("connections", []):
            all_connections.append((item["article"], conn))

    if all_connections:
        for article, conn in all_connections[:5]:
            formatted = format_relationship(conn, kb)
            console.print(f"  - [cyan]{article.title}[/cyan]")
            console.print(f"    {formatted}")
    elif stats.get("connections", 0) > 0:
        # Cluster-based connections were found - query KB for THIS SESSION's connections only
        session_start = stats.get("session_start")
        recent_connections = kb.get_relationships(since=session_start)[:10]
        if recent_connections:
            console.print(f"  [green]{stats['connections']} insight connections discovered via clustering:[/green]")
            for conn in recent_connections[:5]:
                formatted = format_relationship(conn, kb)
                console.print(f"    {formatted}")
        else:
            console.print("   [dim]No cross-source connections found this session.[/dim]")
    else:
        console.print("   [dim]No cross-source connections found this session.[/dim]")
    console.print()

    # =========================================================================
    # SECTION 4: KNOWLEDGE GRAPH UPDATES
    # =========================================================================
    console.print("[bold cyan]## KNOWLEDGE GRAPH UPDATES[/bold cyan]")
    console.print("[dim]What we learned worth remembering[/dim]")
    console.print()

    # New facts/triples
    new_facts = stats.get("triples_new", 0)
    if new_facts > 0:
        console.print(f"  [green]+{new_facts} new facts added[/green]")

        # Show sample of new facts
        for item in processed_articles[:3]:
            triples = item.get("triples", [])
            if triples:
                for t in triples[:2]:
                    if hasattr(t, 'subject'):
                        console.print(f"    - {t.subject} -> {t.predicate} -> {t.object}")

    # New insights
    new_insights = stats.get("insights", 0)
    if new_insights > 0:
        console.print(f"  [green]+{new_insights} insights extracted[/green]")

    # Redundant (already known)
    redundant = stats.get("triples_existing", 0)
    if redundant > 0:
        console.print(f"  [dim]{redundant} facts already known (confirms existing knowledge)[/dim]")

    console.print()

    # =========================================================================
    # SECTION 5: QUICK SCAN
    # =========================================================================
    console.print("[bold cyan]## QUICK SCAN[/bold cyan]")
    console.print("[dim]Everything else, by relevance[/dim]")
    console.print()

    # Items not in top 3
    remaining = scored_articles[3:10]  # Next 7
    if remaining:
        for item in remaining:
            article = item["article"]
            score = item.get("score", 0)
            skippable = score < 0.3

            prefix = "[dim]SKIP:[/dim] " if skippable else "  "
            console.print(f"{prefix}{article.title}")
    else:
        console.print("   [dim]No additional items.[/dim]")
    console.print()

    # =========================================================================
    # SECTION 6: SESSION STATS
    # =========================================================================
    console.print("[bold cyan]## SESSION STATS[/bold cyan]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Articles processed", str(stats["processed"]))
    table.add_row("From feeds", str(stats.get("feeds_count", 0)))

    # Show pipeline duration, not timestamp
    duration = stats.get("pipeline_duration", 0)
    table.add_row("Processing time", format_duration(duration))
    table.add_row("Insights extracted", str(stats["insights"]))
    table.add_row("Facts added", str(stats.get("triples_new", stats.get("triples", 0))))
    table.add_row("New graph triples", str(stats.get("cluster_triples", 0)))
    table.add_row("Connections found", str(stats["connections"]))
    table.add_row("Stories updated", str(stats.get("stories_matched", 0) + stats.get("stories_created", 0)))

    if stats["errors"] > 0:
        table.add_row("Errors", f"[red]{stats['errors']}[/red]")

    console.print(table)

    # Knowledge base totals
    kb_stats = kb.get_stats()
    console.print()
    console.print(f"[dim]Total knowledge: {kb_stats['total_insights']} insights, {kb_stats['total_entities']} entities[/dim]")
    console.print()


def _score_articles_for_briefing(
    processed_articles: list,
    profile: UserContextProfile,
    kb: KnowledgeBase,
) -> list:
    """Score articles for priority ranking in the briefing.

    Scoring factors:
    - Signal strength (not ads/fluff)
    - Match to user interests
    - Novelty (not redundant)
    - Cross-referencing (part of multi-source story)
    """
    scored = []

    for item in processed_articles:
        article = item["article"]
        score = 0.5  # Base score
        reason = ""

        # Signal strength - boost non-fluff content, penalize low-quality
        if article.signal_tags:
            tags_lower = article.signal_tags.lower()
            # Positive signals
            if "research" in tags_lower or "data-driven" in tags_lower:
                score += 0.3
                reason = "Research-backed"
            if "primary" in tags_lower:
                score += 0.2
                reason = "Primary source"
            if "documented" in tags_lower:
                score += 0.1
            if "factual" in tags_lower:
                score += 0.1
            # Negative signals - penalize fluff and low-quality content
            if "noise" in tags_lower or "ad" in tags_lower or "promotional" in tags_lower:
                score -= 0.4
            if "aggregator" in tags_lower:
                score -= 0.2
            if "speculative" in tags_lower:
                score -= 0.15
            if "opinion" in tags_lower:
                score -= 0.1
            if "sensational" in tags_lower:
                score -= 0.15
            if "non-sequitur" in tags_lower:
                score -= 0.1

        # User interest match
        tracked = profile.watching + profile.current_projects
        for topic in tracked:
            if topic.lower() in article.title.lower():
                score += 0.3
                reason = f"Matches your interest: {topic}"
                break

        # Novelty - more insights = more novel
        insight_count = len(item.get("insights", []))
        score += insight_count * 0.1

        # Cross-referencing - part of a story
        if article.story_id:
            score += 0.15
            if not reason:
                reason = "Part of developing story"

        # Connections found = high value
        conn_count = len(item.get("connections", []))
        score += conn_count * 0.1

        item["score"] = min(score, 1.0)
        item["relevance_reason"] = reason
        scored.append(item)

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def _explain_relevance(article: Article, profile: UserContextProfile, reason: str) -> str:
    """Generate personalized relevance explanation."""
    if reason:
        return reason

    # Check against user interests
    for topic in profile.watching:
        if topic.lower() in article.title.lower():
            return f"Matches your tracked topic: {topic}"

    for project in profile.current_projects:
        if project.lower() in article.title.lower():
            return f"Related to your project: {project}"

    return ""


def _article_matches_topic(article: Article, topic: str) -> bool:
    """Check if article matches a topic."""
    topic_lower = topic.lower()
    return (
        topic_lower in article.title.lower() or
        (article.trend_tags and topic_lower in article.trend_tags.lower()) or
        (article.content and topic_lower in article.content.lower()[:500])
    )
