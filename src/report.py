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
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .storage import Storage, Article
from .content_filter import filter_articles, cleanup_old_spam
from .knowledge import (
    KnowledgeBase,
    extract_insights_from_article,
    extract_triples_with_comparison,
    detect_connections,
    format_relationship,
)
from .llm_providers import get_best_provider, get_setup_instructions
from .rss import fetch_all_feeds, load_feeds
from .trends import analyze_article
from .signal_tagger import SignalTagger
from .embeddings import EmbeddingService
from .clustering import StoryClusterer
from .storage_perspectives import add_perspective_methods
from .user_context import UserContextStore, UserContextProfile

console = Console(force_terminal=True, legacy_windows=True)


# =============================================================================
# CLEANUP HANDLING - Prevent orphaned gateway requests on cancel
# =============================================================================

_cleanup_registered = False


def _cleanup_gateway():
    """Clean up gateway on exit to prevent orphaned requests."""
    try:
        from .gateway import get_gateway
        gateway = get_gateway()
        gateway.clear_queue()
    except Exception:
        pass  # Best effort cleanup


def _signal_handler(signum, frame):
    """Handle interrupt signals by cleaning up and exiting."""
    console.print("\n[yellow]Interrupted - cleaning up gateway...[/yellow]")
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
# STEP 1: VERIFICATION (Self-Healing)
# =============================================================================

def _run_verification_step(
    storage: Storage,
    kb: KnowledgeBase,
    articles: list[Article],
    embedding_service: EmbeddingService,
    max_per_step: int = 0,
) -> dict:
    """
    Step 1: Verify data completeness and report gaps.

    Detects missing data from interrupted runs so we can fill gaps.
    Returns dict with counts of what needs to be done.
    """
    gaps = {
        "articles_missing_summary": 0,
        "articles_missing_trends": 0,
        "articles_missing_signals": 0,
        "articles_missing_embeddings": 0,
        "stories_missing_embeddings": 0,
        "insights_missing_embeddings": 0,
        "articles_needing_llm": [],  # Articles that need LLM processing
        "articles_needing_embedding": [],  # Articles that need embedding
    }

    console.print("[bold]Step 1:[/bold] Verifying data completeness...")

    # Count TRUE backlog from DB (not just the limited articles list)
    all_unanalyzed = storage.get_unanalyzed_articles(exclude_spam=True)
    for article in all_unanalyzed:
        if not article.summary:
            gaps["articles_missing_summary"] += 1
        if not article.trend_tags:
            gaps["articles_missing_trends"] += 1
        if not article.signal_tags:
            gaps["articles_missing_signals"] += 1
        if storage.get_embedding(article.id) is None:
            gaps["articles_missing_embeddings"] += 1

    # Track what will actually be processed (from limited list)
    for article in articles:
        needs_llm = not article.summary or not article.trend_tags or not article.signal_tags
        needs_embedding = storage.get_embedding(article.id) is None

        if needs_llm:
            gaps["articles_needing_llm"].append(article)
        if needs_embedding:
            gaps["articles_needing_embedding"].append(article)

    # Check story embeddings (using shared service)
    stories = storage.get_active_stories(limit=500)
    for story in stories:
        if not embedding_service.get_embedding(story.id, "story"):
            gaps["stories_missing_embeddings"] += 1

    # Check insight embeddings
    insights = kb.get_insights(limit=500)
    for insight in insights:
        if not embedding_service.get_embedding(insight.id, "insight"):
            gaps["insights_missing_embeddings"] += 1

    # Report findings
    total_gaps = (
        gaps["articles_missing_summary"] +
        gaps["articles_missing_trends"] +
        gaps["articles_missing_signals"] +
        gaps["articles_missing_embeddings"] +
        gaps["stories_missing_embeddings"] +
        gaps["insights_missing_embeddings"]
    )

    if total_gaps > 0:
        console.print(f"  [yellow]Found {total_gaps} gaps from previous runs:[/yellow]")

        def show_gap(label: str, total: int) -> None:
            if total > 0:
                if max_per_step > 0 and total > max_per_step:
                    console.print(f"    - {total} {label} [dim](processing {max_per_step})[/dim]")
                else:
                    console.print(f"    - {total} {label}")

        show_gap("articles missing summaries", gaps["articles_missing_summary"])
        show_gap("articles missing trend tags", gaps["articles_missing_trends"])
        show_gap("articles missing signal tags", gaps["articles_missing_signals"])
        show_gap("articles missing embeddings", gaps["articles_missing_embeddings"])
        show_gap("stories missing embeddings", gaps["stories_missing_embeddings"])
        show_gap("insights missing embeddings", gaps["insights_missing_embeddings"])

        if max_per_step > 0:
            console.print(f"  [dim]Limited to {max_per_step} items per step[/dim]")
        else:
            console.print("  [dim]These will be filled during processing[/dim]")
    else:
        console.print("  [green]All data complete, no gaps found[/green]")

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
    max_per_step: int = 0,
) -> None:
    """
    Step 2: Pre-embed existing stories and insights.

    This MUST run BEFORE the LLM phase so that detect_connections
    has embeddings to compare against when finding relationships.

    NOTE: Model loading is handled by the gateway - no ensure_*_model() calls needed.
    """
    console.print("[bold]Step 2:[/bold] Pre-embedding existing content...")

    # Check if embedding service is available
    if not embedding_service.is_available():
        console.print("  [red]ERROR: Embedding service not available[/red]")
        console.print("  [yellow]Connection detection will be limited[/yellow]")
        console.print()
        return

    provider_info = embedding_service.get_provider_info()
    console.print(f"  [green]Using {provider_info.get('provider', 'unknown')} ({provider_info.get('model', 'unknown')})[/green]")

    # Embed insights first (these are what detect_connections compares against)
    insights = kb.get_insights(limit=500)
    insights_needing_embedding = [i for i in insights if not embedding_service.get_embedding(i.id, "insight")]
    if max_per_step > 0:
        insights_needing_embedding = insights_needing_embedding[:max_per_step]

    BATCH_SIZE = 10

    if insights_needing_embedding:
        total = len(insights_needing_embedding)
        num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        embedded_count = 0
        errors = 0

        console.print(f"  Embedding {total} insights in {num_batches} batches...")

        for batch_num in range(num_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, total)
            batch = insights_needing_embedding[start_idx:end_idx]

            console.print(f"    [dim]Batch {batch_num + 1}/{num_batches} ({len(batch)} items)...[/dim]", end="")

            batch_errors = 0
            for insight in batch:
                try:
                    result = embedding_service.embed_text(insight.content)
                    embedding_service.save_embedding(insight.id, "insight", result)
                    embedded_count += 1
                except Exception as e:
                    console.print(f"\n  [red]ERROR: {e}[/red]", end="")
                    stats["errors"] += 1
                    errors += 1
                    batch_errors += 1

            if batch_errors == 0:
                console.print(f" [green]done[/green]")
            else:
                console.print(f" [yellow]done ({batch_errors} errors)[/yellow]")

        console.print(f"  [green]Embedded {embedded_count} insights[/green]")
        stats["insights_embedded"] = embedded_count
    else:
        console.print("  [dim]All insights already have embeddings[/dim]")

    # Embed stories
    stories = storage.get_active_stories(limit=200)
    stories_needing_embedding = [s for s in stories if not embedding_service.get_embedding(s.id, "story")]
    if max_per_step > 0:
        stories_needing_embedding = stories_needing_embedding[:max_per_step]

    if stories_needing_embedding:
        total = len(stories_needing_embedding)
        num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        embedded_count = 0
        errors = 0

        console.print(f"  Embedding {total} stories in {num_batches} batches...")

        for batch_num in range(num_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, total)
            batch = stories_needing_embedding[start_idx:end_idx]

            console.print(f"    [dim]Batch {batch_num + 1}/{num_batches} ({len(batch)} items)...[/dim]", end="")

            batch_errors = 0
            for story in batch:
                try:
                    result = embedding_service.embed_story(story)
                    embedding_service.save_embedding(story.id, "story", result)
                    embedded_count += 1
                except Exception as e:
                    console.print(f"\n  [red]ERROR: {e}[/red]", end="")
                    stats["errors"] += 1
                    errors += 1
                    batch_errors += 1

            if batch_errors == 0:
                console.print(f" [green]done[/green]")
            else:
                console.print(f" [yellow]done ({batch_errors} errors)[/yellow]")

        console.print(f"  [green]Embedded {embedded_count} stories[/green]")
        stats["story_embeddings_generated"] = embedded_count
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
    max_per_step: int = 0,
) -> list[dict]:
    """
    Step 3: LLM processing for all articles.

    Generates: summaries, insights, facts (triples), signal tags, trend tags.
    Uses embedding_service for connection detection and trend categorization.

    NOTE: Model loading is handled by the gateway - no ensure_*_model() calls needed.
    The gateway automatically loads the correct model based on request type.

    NO SILENT FAILURES - Every error is surfaced to the user.
    """
    console.print("[bold]Step 3:[/bold] LLM Analysis...")
    console.print(f"  [green]Using {provider.name}[/green]")

    tagger = SignalTagger(use_llm=True, provider=provider)
    processed_articles = []
    step_start = time.time()  # For ETA calculation

    console.print()

    for idx, article in enumerate(articles):
        article_start = time.time()
        insights = []
        triples = []
        connections = []
        triple_result = None

        # Article header
        console.print(f"[bold cyan][{idx + 1}/{len(articles)}][/bold cyan] {article.title}")

        article_errors = []  # Collect errors for this article

        # --- Extract insights (LLM call) ---
        console.print("  [dim]- Extracting insights...[/dim]")
        try:
            insights = extract_insights_from_article(article, provider, kb) or []
            for ins in insights:
                stats["insights"] += 1
                console.print(f"    [green]+[/green] {ins.content}")
            if not insights:
                console.print("    [dim]No insights extracted[/dim]")
        except Exception as e:
            error_msg = f"Insight extraction failed: {e}"
            article_errors.append(error_msg)
            console.print(f"    [red]ERROR: {error_msg}[/red]")
            stats["errors"] += 1

        # --- Connection detection DEFERRED ---
        # Connections are detected AFTER Step 4 (embedding phase) to avoid model switching.
        # The insights are collected and connections will be found in batch later.

        # --- Extract facts/triples (LLM call) ---
        console.print("  [dim]- Extracting facts...[/dim]")
        try:
            triple_result = extract_triples_with_comparison(article, provider, kb)
            triples = triple_result.new_triples

            if triple_result.new_triples:
                console.print(f"    [green]+{len(triple_result.new_triples)} new facts:[/green]")
                for t in triple_result.new_triples[:5]:
                    console.print(f"      [green]*[/green] {t.subject} -> {t.predicate} -> {t.object}")
                if len(triple_result.new_triples) > 5:
                    console.print(f"      [dim]...and {len(triple_result.new_triples) - 5} more[/dim]")
                stats["triples_new"] += len(triple_result.new_triples)
            else:
                console.print("    [dim]No new facts[/dim]")

            if triple_result.existing_triples:
                console.print(f"    [dim]~{len(triple_result.existing_triples)} already known[/dim]")
                stats["triples_existing"] += len(triple_result.existing_triples)
            stats["triples"] += triple_result.total_extracted
        except Exception as e:
            error_msg = f"Fact extraction failed: {e}"
            article_errors.append(error_msg)
            console.print(f"    [red]ERROR: {error_msg}[/red]")
            stats["errors"] += 1

        # --- Tagging ---
        console.print("  [dim]- Tagging...[/dim]")
        tag_output = []

        # Trend tags (embedding-based categorization)
        if not article.trend_tags:
            try:
                tags = analyze_article(article, embedding_service=embedding_service)
                storage.update_trends(article.id, tags)
                article.trend_tags = tags
                if tags:
                    tag_list = [t.strip() for t in tags.split(",")]
                    tag_output.append(f"trends: {', '.join(tag_list[:3])}")
            except Exception as e:
                error_msg = f"Trend tagging failed: {e}"
                article_errors.append(error_msg)
                console.print(f"    [red]ERROR: {error_msg}[/red]")
                stats["errors"] += 1

        # Signal tags (LLM-based)
        if not article.signal_tags:
            try:
                signal_tags = tagger.tag_article(article)
                storage.update_signal_tags(article.id, signal_tags.to_json())
                article.signal_tags = signal_tags.to_json()
                compact = signal_tags.to_compact_string()
                if compact:
                    tag_output.append(f"signal: {compact}")
            except Exception as e:
                error_msg = f"Signal tagging failed: {e}"
                article_errors.append(error_msg)
                console.print(f"    [red]ERROR: {error_msg}[/red]")
                stats["errors"] += 1

        if tag_output:
            console.print(f"    [magenta]{' | '.join(tag_output)}[/magenta]")
        else:
            existing = []
            if article.trend_tags:
                existing.append(f"trends: {article.trend_tags[:40]}")
            if article.signal_tags:
                existing.append("signal: set")
            if existing:
                console.print(f"    [dim]Already tagged ({', '.join(existing)})[/dim]")

        # Mark as analyzed
        stats["processed"] += 1
        storage.mark_as_analyzed(article.id)

        # Store processed data
        processed_articles.append({
            "article": article,
            "insights": insights,
            "triples": triples,
            "connections": connections,
            "errors": article_errors,
        })

        # Summary for this article with timing and ETA
        article_elapsed = time.time() - article_start
        articles_done = idx + 1
        articles_remaining = len(articles) - articles_done

        # Calculate ETA based on current rate
        if articles_remaining > 0 and articles_done > 0:
            # Use cumulative time from step start for more stable rate
            step_elapsed = time.time() - step_start
            rate_per_article = step_elapsed / articles_done
            eta_seconds = articles_remaining * rate_per_article

            if eta_seconds > 60:
                eta_str = f"~{eta_seconds / 60:.1f}m remaining"
            else:
                eta_str = f"~{eta_seconds:.0f}s remaining"

            if article_errors:
                console.print(f"  [yellow][!] {article_elapsed:.1f}s | {eta_str}[/yellow]")
            else:
                console.print(f"  [bold green][OK][/bold green] [dim]{article_elapsed:.1f}s | {eta_str}[/dim]")
        else:
            if article_errors:
                console.print(f"  [yellow][!] {article_elapsed:.1f}s[/yellow]")
            else:
                console.print(f"  [bold green][OK][/bold green] [dim]{article_elapsed:.1f}s[/dim]")
        console.print()

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
    max_per_step: int = 0,
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
    console.print(f"  [green]Using {provider_info.get('provider', 'unknown')} ({provider_info.get('model', 'unknown')})[/green]")

    # Filter to articles needing embeddings
    needs_embedding = [a for a in articles if storage.get_embedding(a.id) is None]

    BATCH_SIZE = 10

    if not needs_embedding:
        console.print("  [dim]All articles already have embeddings[/dim]")
    else:
        total = len(needs_embedding)
        num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        embedded_count = 0

        console.print(f"  Embedding {total} articles in {num_batches} batches...")

        for batch_num in range(num_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, total)
            batch = needs_embedding[start_idx:end_idx]

            console.print(f"    [dim]Batch {batch_num + 1}/{num_batches} ({len(batch)} items)...[/dim]", end="")

            batch_errors = 0
            for article in batch:
                try:
                    semantic_card = _create_semantic_card(article)
                    result = embedding_service.embed_text(semantic_card)
                    storage.save_embedding(article.id, result.vector)
                    embedded_count += 1
                except Exception as e:
                    console.print(f"\n  [red]ERROR: {e}[/red]", end="")
                    stats["errors"] += 1
                    batch_errors += 1

            if batch_errors == 0:
                console.print(f" [green]done[/green]")
            else:
                console.print(f" [yellow]done ({batch_errors} errors)[/yellow]")

        console.print(f"  [green]Embedded {embedded_count} articles[/green]")
        stats["embeddings_generated"] = embedded_count

    # Any new stories created during LLM phase need embeddings
    stories = storage.get_active_stories(limit=200)
    stories_needing_embedding = [s for s in stories if not embedding_service.get_embedding(s.id, "story")]
    if max_per_step > 0:
        stories_needing_embedding = stories_needing_embedding[:max_per_step]

    if stories_needing_embedding:
        total = len(stories_needing_embedding)
        num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        story_embedded = 0

        console.print(f"  Embedding {total} new stories in {num_batches} batches...")

        for batch_num in range(num_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, total)
            batch = stories_needing_embedding[start_idx:end_idx]

            console.print(f"    [dim]Batch {batch_num + 1}/{num_batches} ({len(batch)} items)...[/dim]", end="")

            batch_errors = 0
            for story in batch:
                try:
                    result = embedding_service.embed_story(story)
                    embedding_service.save_embedding(story.id, "story", result)
                    story_embedded += 1
                except Exception as e:
                    console.print(f"\n  [red]ERROR: {e}[/red]", end="")
                    stats["errors"] += 1
                    batch_errors += 1

            if batch_errors == 0:
                console.print(f" [green]done[/green]")
            else:
                console.print(f" [yellow]done ({batch_errors} errors)[/yellow]")

        if story_embedded > 0:
            console.print(f"  [green]Embedded {story_embedded} new stories[/green]")
            stats["story_embeddings_generated"] = stats.get("story_embeddings_generated", 0) + story_embedded

    console.print()
    return len(needs_embedding)


# =============================================================================
# STEP 4.5: BATCHED CONNECTION DETECTION
# =============================================================================

def _run_connection_detection(
    processed_articles: list[dict],
    kb: KnowledgeBase,
    provider,
    stats: dict,
    embedding_service: EmbeddingService,
) -> None:
    """
    Detect connections between newly extracted insights and existing knowledge.

    BATCHED to prevent model switching:
    1. Embed all new insights (embedding model)
    2. Find all candidates via FAISS (no model - just math)
    3. Classify all relationships (text model)

    Args:
        processed_articles: List of dicts from LLM phase, each with "insights" list
        kb: Knowledge base
        provider: LLM provider for relationship classification
        stats: Statistics dict to update
        embedding_service: Embedding service
    """
    import json
    import uuid
    from datetime import datetime
    from .knowledge import Relationship
    from .schema import extract_json_from_response

    # Collect all insights that need connection detection
    all_insights = []
    for item in processed_articles:
        for ins in item.get("insights", []):
            all_insights.append((item, ins))

    if not all_insights:
        return

    console.print("[bold]Step 4.5:[/bold] Detecting connections...")

    # =========================================================================
    # PHASE 1: Batch embed all new insights (EMBEDDING MODEL)
    # =========================================================================
    console.print(f"  [dim]Embedding {len(all_insights)} new insights...[/dim]")

    insights_to_embed = []
    for item, ins in all_insights:
        existing = embedding_service.get_embedding(ins.id, "insight")
        if not existing:
            insights_to_embed.append(ins)

    if insights_to_embed:
        for ins in insights_to_embed:
            try:
                result = embedding_service.embed_text(ins.content)
                embedding_service.save_embedding(ins.id, "insight", result)
            except Exception as e:
                console.print(f"    [red]Embedding failed for insight: {e}[/red]")
                stats["errors"] += 1
        console.print(f"  [dim]Embedded {len(insights_to_embed)} insights[/dim]")
    else:
        console.print(f"  [dim]All insights already embedded[/dim]")

    # =========================================================================
    # PHASE 2: Find all candidates via FAISS (NO MODEL - just vector math)
    # =========================================================================
    console.print(f"  [dim]Finding similar insights via FAISS...[/dim]")

    # For each insight, find candidates
    all_candidates = []  # List of (item, insight, [(existing_insight, similarity), ...])

    for item, ins in all_insights:
        embedding = embedding_service.get_embedding(ins.id, "insight")
        if not embedding:
            continue

        similar_results = embedding_service.find_similar(
            query_vector=embedding,
            target_type="insight",
            threshold=0.70,
            limit=50,
        )

        if not similar_results:
            continue

        candidates = []
        for target_id, similarity in similar_results:
            if target_id == ins.id:
                continue
            existing = kb.get_insight(target_id)
            if existing:
                candidates.append((existing, similarity))

        if candidates:
            # Limit to top 10 for LLM classification
            all_candidates.append((item, ins, candidates[:10]))

    if not all_candidates:
        console.print(f"  [dim]No similar insights found[/dim]")
        console.print()
        return

    # =========================================================================
    # PHASE 3: Batch classify all relationships (TEXT MODEL)
    # =========================================================================
    console.print(f"  [dim]Classifying {len(all_candidates)} insight groups...[/dim]")

    total_connections = 0

    for item, ins, candidates in all_candidates:
        # Build prompt for this insight's candidates
        pairs_text = ""
        for i, (existing, similarity) in enumerate(candidates):
            pairs_text += f"\nPair {i+1} (similarity: {similarity:.2f}):\n"
            pairs_text += f'- Existing: "{existing.content}"\n'
            pairs_text += f'- New: "{ins.content}"\n'

        prompt = f"""Classify the relationships between these insight pairs.
{pairs_text}
For each pair, determine the relationship from the NEW insight to the EXISTING insight:
- confirms: New says essentially the same thing as existing
- contradicts: New says the opposite of existing
- refines: New adds nuance or detail to existing
- extends: New builds on existing with new information
- none: They are about similar topics but unrelated

Return a JSON array with the relationship for each pair in order:
["confirms", "none", "extends", ...]

Return ONLY the JSON array, no other text."""

        try:
            response = provider.generate(prompt, max_tokens=200)
            json_str = extract_json_from_response(response)
            relationship_types = json.loads(json_str)

            if not isinstance(relationship_types, list):
                relationship_types = [relationship_types]

            # Create relationships for valid classifications
            valid_types = {"confirms", "contradicts", "refines", "extends"}

            if "connections" not in item:
                item["connections"] = []

            for i, (existing, similarity) in enumerate(candidates):
                if i >= len(relationship_types):
                    break

                rel_type = str(relationship_types[i]).lower().strip()
                if rel_type not in valid_types:
                    continue

                relationship = Relationship(
                    id=str(uuid.uuid4()),
                    source_insight_id=ins.id,
                    target_insight_id=existing.id,
                    relationship_type=rel_type,
                    strength=similarity,
                    detected_at=datetime.now(),
                )

                item["connections"].append(relationship)
                total_connections += 1
                stats["connections"] += 1

                formatted = format_relationship(relationship, kb)
                console.print(f"    [cyan]->[/cyan] {formatted}")

        except Exception as e:
            console.print(f"    [red]ERROR: Classification failed: {e}[/red]")
            stats["errors"] += 1

    console.print(f"  [green]Found {total_connections} connections[/green]")
    console.print()


# =============================================================================
# STEP 5: STORY MATCHING
# =============================================================================

def _run_story_matching(
    articles: list[Article],
    storage: Storage,
    kb: KnowledgeBase,
    provider,
    stats: dict,
    embedding_service: EmbeddingService,
    max_per_step: int = 0,
) -> None:
    """
    Step 5: Match articles to stories using embeddings.

    Uses the semantic embeddings generated in Step 4 to find
    related stories for each article.
    """
    console.print("[bold]Step 5:[/bold] Matching articles to stories...")

    clusterer = StoryClusterer(provider, storage, kb, embedding_service=embedding_service)

    matched = 0
    created = 0

    for article in articles:
        try:
            embedding = storage.get_embedding(article.id)
            if not embedding:
                # No embedding - create new story without matching
                try:
                    clusterer.create_new_story(article)
                    created += 1
                except Exception as e:
                    console.print(f"  [red]ERROR creating story for '{article.title[:40]}': {e}[/red]")
                    stats["errors"] += 1
                continue

            # Try to match to existing story
            matched_story = clusterer.find_matching_story_with_embedding(article, embedding)

            if matched_story:
                try:
                    clusterer.update_story_with_article(matched_story, article)
                    matched += 1
                except Exception as e:
                    console.print(f"  [red]ERROR updating story: {e}[/red]")
                    stats["errors"] += 1
            else:
                # Create new story
                try:
                    clusterer.create_new_story(article)
                    created += 1
                except Exception as e:
                    console.print(f"  [red]ERROR creating story: {e}[/red]")
                    stats["errors"] += 1

        except Exception as e:
            console.print(f"  [red]ERROR matching article '{article.title[:40]}': {e}[/red]")
            stats["errors"] += 1

    console.print(f"  [green]Matched {matched} articles to existing stories[/green]")
    console.print(f"  [green]Created {created} new stories[/green]")

    stats["stories_matched"] = matched
    stats["stories_created"] = created

    console.print()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def generate_report(
    limit: int = 20,
    skip_summarized: bool = True,
    db_path: str = "articles.db",
    kb_path: str = "knowledge.db",
    feeds_file: str = "config/feeds.txt",
    max_per_step: int = 0,
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
        "connections": 0,
        "stories_matched": 0,
        "stories_created": 0,
        "errors": 0,
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

    # Fetch latest articles
    console.print("[bold]Fetching:[/bold] Latest articles...")
    feeds = load_feeds(feeds_file)
    new_article_ids = []
    stats["feeds_count"] = len(feeds) if feeds else 0
    stats["time_range"] = datetime.now().strftime("%Y-%m-%d %H:%M")

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

    articles = storage.get_unanalyzed_articles(exclude_spam=True)

    if not articles and new_article_ids:
        articles = storage.get_articles_by_ids(new_article_ids)

    total_unanalyzed = len(articles)

    # Filter by content length
    articles = [a for a in articles if a.content and len(a.content) >= MIN_CONTENT_LENGTH]
    skipped_for_content = total_unanalyzed - len(articles)

    # Filter spam
    articles, spam_articles = filter_articles(articles, storage, threshold=0.7)
    skipped_as_spam = len(spam_articles)

    # Cleanup old spam
    deleted_spam = cleanup_old_spam(storage, days=30)

    # Report filtering
    filter_msgs = []
    if skipped_for_content > 0:
        filter_msgs.append(f"{skipped_for_content} short")
    if skipped_as_spam > 0:
        filter_msgs.append(f"{skipped_as_spam} spam")
    if deleted_spam > 0:
        filter_msgs.append(f"{deleted_spam} old spam deleted")

    if filter_msgs:
        console.print(f"  [dim]Found {total_unanalyzed}, processing {len(articles)} ({', '.join(filter_msgs)})[/dim]")
    else:
        console.print(f"  [dim]Processing {len(articles)} articles[/dim]")

    if not articles:
        console.print()
        console.print("[yellow]No articles to process.[/yellow]")
        return stats

    # Warn about large processing jobs and suggest limit option
    LARGE_BATCH_THRESHOLD = 20
    if len(articles) > LARGE_BATCH_THRESHOLD and max_per_step == 0:
        console.print()
        console.print(f"[yellow]Warning: {len(articles)} articles to process - this could take a while[/yellow]")
        console.print("[yellow]Tip: Use 'rss report -m 5' to process 5 articles before generating the briefing[/yellow]")
        console.print("[dim]     Use 'rss report --help' for more options[/dim]")
        console.print()

    console.print()

    # Apply max_per_step limit to articles if set
    if max_per_step > 0:
        articles = articles[:max_per_step]

    # Track total pipeline time
    pipeline_start = time.time()

    # Step 1: Verification (Self-Healing)
    step_start = time.time()
    gaps = _run_verification_step(storage, kb, articles, embedding_service, max_per_step)
    console.print(f"  [dim]Step 1 completed in {time.time() - step_start:.1f}s[/dim]\n")

    # Step 2: Pre-embed existing stories/insights
    # This MUST happen before LLM phase so detect_connections has embeddings to compare against
    step_start = time.time()
    _run_pre_embedding_phase(storage, kb, embedding_service, stats, max_per_step)
    console.print(f"  [dim]Step 2 completed in {time.time() - step_start:.1f}s[/dim]\n")

    # Step 3: LLM Phase (now has embeddings to compare against)
    step_start = time.time()
    processed_articles = _run_llm_phase(articles, storage, kb, provider, stats, embedding_service, max_per_step)
    console.print(f"  [dim]Step 3 completed in {time.time() - step_start:.1f}s[/dim]\n")

    # Step 4: Embedding Phase (for new articles)
    step_start = time.time()
    _run_embedding_phase(articles, storage, kb, stats, embedding_service, max_per_step)
    console.print(f"  [dim]Step 4 completed in {time.time() - step_start:.1f}s[/dim]\n")

    # Step 4.5: Batched Connection Detection (AFTER embeddings, no model switching)
    step_start = time.time()
    _run_connection_detection(processed_articles, kb, provider, stats, embedding_service)
    console.print(f"  [dim]Step 4.5 completed in {time.time() - step_start:.1f}s[/dim]\n")

    # Step 5: Story Matching
    step_start = time.time()
    _run_story_matching(articles, storage, kb, provider, stats, embedding_service, max_per_step)
    console.print(f"  [dim]Step 5 completed in {time.time() - step_start:.1f}s[/dim]\n")

    # Show total pipeline time
    total_time = time.time() - pipeline_start
    if total_time > 60:
        console.print(f"[green]Pipeline completed in {total_time / 60:.1f} minutes[/green]\n")
    else:
        console.print(f"[green]Pipeline completed in {total_time:.1f}s[/green]\n")

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
                    console.print(f"   [dim]Signal: {', '.join(tag_parts)}[/dim]")
                except (json.JSONDecodeError, TypeError):
                    console.print(f"   [dim]Signal: {article.signal_tags}[/dim]")

            # What we know - relevant facts from knowledge base
            # Extract key terms from title and find related triples
            title_words = [w for w in article.title.split() if len(w) > 4]
            related_triples = []
            for word in title_words[:3]:
                triples = kb.query_triples_pattern(subject_pattern=f"%{word}%")
                related_triples.extend(triples[:1])  # Max 1 per word
                if len(related_triples) >= 2:
                    break

            if related_triples:
                console.print(f"   [blue]What we know:[/blue]")
                for t in related_triples[:2]:
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
                    console.print(f"  - {article.title[:60]}...")
                    if item.get("insights"):
                        insight = item['insights'][0]
                        insight_text = insight.content if hasattr(insight, 'content') else str(insight)
                        console.print(f"    [dim]{insight_text[:80]}...[/dim]")
    else:
        console.print("[dim]No tracked topics. Use 'rss context watch <topic>' to add interests.[/dim]")
    console.print()

    # =========================================================================
    # SECTION 3: DISCOVERED CONNECTIONS
    # =========================================================================
    console.print("[bold cyan]## DISCOVERED CONNECTIONS[/bold cyan]")
    console.print("[dim]Insights from combining multiple sources[/dim]")
    console.print()

    all_connections = []
    for item in processed_articles:
        for conn in item.get("connections", []):
            all_connections.append((item["article"], conn))

    if all_connections:
        for article, conn in all_connections[:5]:
            formatted = format_relationship(conn, kb)
            console.print(f"  - [cyan]{article.title[:40]}...[/cyan]")
            console.print(f"    {formatted}")
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
            console.print(f"{prefix}{article.title[:70]}...")
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
    table.add_row("Time", stats.get("time_range", "-"))
    table.add_row("Insights extracted", str(stats["insights"]))
    table.add_row("Facts added", str(stats.get("triples_new", stats.get("triples", 0))))
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

        # Signal strength - boost non-fluff content
        if article.signal_tags:
            tags_lower = article.signal_tags.lower()
            if "research" in tags_lower or "data-driven" in tags_lower:
                score += 0.2
                reason = "Research-backed"
            if "primary" in tags_lower:
                score += 0.1
                reason = "Primary source"
            if "noise" in tags_lower or "ad" in tags_lower:
                score -= 0.3

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
