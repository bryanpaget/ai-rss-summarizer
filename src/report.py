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

console = Console(force_terminal=True, legacy_windows=True)


# =============================================================================
# STEP 1: VERIFICATION (Self-Healing)
# =============================================================================

def _run_verification_step(
    storage: Storage,
    kb: KnowledgeBase,
    articles: list[Article],
    embedding_service: EmbeddingService,
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

    # Check each article
    for article in articles:
        needs_llm = False
        needs_embedding = False

        # Check for missing LLM outputs
        if not article.summary:
            gaps["articles_missing_summary"] += 1
            needs_llm = True
        if not article.trend_tags:
            gaps["articles_missing_trends"] += 1
            needs_llm = True
        if not article.signal_tags:
            gaps["articles_missing_signals"] += 1
            needs_llm = True

        # Check for missing embedding
        if storage.get_embedding(article.id) is None:
            gaps["articles_missing_embeddings"] += 1
            needs_embedding = True

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
        if gaps["articles_missing_summary"] > 0:
            console.print(f"    - {gaps['articles_missing_summary']} articles missing summaries")
        if gaps["articles_missing_trends"] > 0:
            console.print(f"    - {gaps['articles_missing_trends']} articles missing trend tags")
        if gaps["articles_missing_signals"] > 0:
            console.print(f"    - {gaps['articles_missing_signals']} articles missing signal tags")
        if gaps["articles_missing_embeddings"] > 0:
            console.print(f"    - {gaps['articles_missing_embeddings']} articles missing embeddings")
        if gaps["stories_missing_embeddings"] > 0:
            console.print(f"    - {gaps['stories_missing_embeddings']} stories missing embeddings")
        if gaps["insights_missing_embeddings"] > 0:
            console.print(f"    - {gaps['insights_missing_embeddings']} insights missing embeddings")
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
) -> None:
    """
    Step 2: Pre-embed existing stories and insights.

    This MUST run BEFORE the LLM phase so that detect_connections
    has embeddings to compare against when finding relationships.
    """
    from .model_manager import ensure_embedding_model

    console.print("[bold]Step 2:[/bold] Pre-embedding existing content...")

    # Ensure embedding model is loaded
    try:
        ensure_embedding_model()
    except Exception as e:
        console.print(f"  [red]ERROR: Cannot load embedding model: {e}[/red]")
        console.print("  [yellow]Connection detection will be limited[/yellow]")
        console.print()
        return

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
) -> list[dict]:
    """
    Step 3: LLM processing for all articles.

    Generates: summaries, insights, facts (triples), signal tags, trend tags.
    Text model is loaded ONCE at the start.
    Uses embedding_service for connection detection and trend categorization.

    NO SILENT FAILURES - Every error is surfaced to the user.
    """
    from .model_manager import ensure_text_model

    console.print("[bold]Step 3:[/bold] LLM Analysis...")

    # Load text model ONCE
    console.print("  [dim]Loading text model...[/dim]")
    try:
        ensure_text_model()
        console.print(f"  [green]Using {provider.name}[/green]")
    except Exception as e:
        console.print(f"  [red]ERROR loading text model: {e}[/red]")
        console.print("  [red]Cannot proceed without LLM. Aborting.[/red]")
        raise RuntimeError(f"LLM unavailable: {e}")

    tagger = SignalTagger(use_llm=True, provider=provider)
    processed_articles = []

    console.print()

    for idx, article in enumerate(articles):
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

        # --- Detect connections between insights ---
        if insights:
            console.print("  [dim]- Finding connections...[/dim]")
            article_connections = []
            for ins in insights:
                try:
                    conns = detect_connections(
                        ins, kb, provider,
                        embedding_service=embedding_service
                    ) or []
                    for conn in conns:
                        connections.append(conn)
                        article_connections.append(conn)
                        stats["connections"] += 1
                except Exception as e:
                    error_msg = f"Connection detection failed: {e}"
                    article_errors.append(error_msg)
                    console.print(f"    [red]ERROR: {error_msg}[/red]")
                    stats["errors"] += 1

            if article_connections:
                for conn in article_connections:
                    formatted = format_relationship(conn, kb)
                    console.print(f"    [cyan]->[/cyan] {formatted}")
            else:
                console.print("    [dim]No connections found[/dim]")

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

        # Summary for this article
        if article_errors:
            console.print(f"  [yellow][!] Completed with {len(article_errors)} errors[/yellow]")
        else:
            console.print(f"  [bold green][OK] Done[/bold green]")
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
# STEP 5: STORY MATCHING
# =============================================================================

def _run_story_matching(
    articles: list[Article],
    storage: Storage,
    kb: KnowledgeBase,
    provider,
    stats: dict,
    embedding_service: EmbeddingService,
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

    console.print()

    # Step 1: Verification (Self-Healing)
    gaps = _run_verification_step(storage, kb, articles, embedding_service)

    # Step 2: Pre-embed existing stories/insights
    # This MUST happen before LLM phase so detect_connections has embeddings to compare against
    _run_pre_embedding_phase(storage, kb, embedding_service, stats)

    # Step 3: LLM Phase (now has embeddings to compare against)
    processed_articles = _run_llm_phase(articles, storage, kb, provider, stats, embedding_service)

    # Step 4: Embedding Phase (for new articles)
    _run_embedding_phase(articles, storage, kb, stats, embedding_service)

    # Step 5: Story Matching
    _run_story_matching(articles, storage, kb, provider, stats, embedding_service)

    # Final Report
    _show_final_report(processed_articles, stats, kb, provider)

    return stats


def _show_final_report(
    processed_articles: list,
    stats: dict,
    kb: KnowledgeBase,
    provider,
) -> None:
    """Show the final synthesized report."""

    console.print(Panel("[bold]Report Complete[/bold]", style="green"))
    console.print()

    # Summary statistics
    table = Table(title="Processing Summary", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Articles Processed", str(stats["processed"]))
    if stats.get("embeddings_generated", 0) > 0:
        table.add_row("Article Embeddings", str(stats["embeddings_generated"]))
    if stats.get("story_embeddings_generated", 0) > 0:
        table.add_row("Story Embeddings", str(stats["story_embeddings_generated"]))
    table.add_row("Insights Extracted", str(stats["insights"]))

    if stats.get("triples_new", 0) > 0 or stats.get("triples_existing", 0) > 0:
        table.add_row("New Facts Added", f"[green]{stats.get('triples_new', 0)}[/green]")
        table.add_row("Redundant Facts", f"[dim]{stats.get('triples_existing', 0)}[/dim]")
    else:
        table.add_row("Knowledge Triples", str(stats["triples"]))

    table.add_row("Connections Found", str(stats["connections"]))

    if stats.get("stories_matched", 0) > 0 or stats.get("stories_created", 0) > 0:
        table.add_row("Stories Matched", str(stats.get("stories_matched", 0)))
        table.add_row("New Stories Created", str(stats.get("stories_created", 0)))

    if stats["errors"] > 0:
        table.add_row("Errors", f"[red]{stats['errors']}[/red]")

    console.print(table)
    console.print()

    # Show any errors from processing
    all_errors = []
    for item in processed_articles:
        if item.get("errors"):
            all_errors.extend([(item["article"].title, e) for e in item["errors"]])

    if all_errors:
        console.print("[bold red]Errors During Processing:[/bold red]")
        for title, error in all_errors[:10]:
            console.print(f"  [red]*[/red] {title[:40]}: {error}")
        if len(all_errors) > 10:
            console.print(f"  [dim]...and {len(all_errors) - 10} more[/dim]")
        console.print()

    # Top articles by insight count
    if processed_articles:
        console.print("[bold]Top Articles by Knowledge Extracted:[/bold]")
        console.print()

        sorted_articles = sorted(
            processed_articles,
            key=lambda x: len(x.get("insights", [])) + len(x.get("triples", [])),
            reverse=True
        )[:5]

        for i, item in enumerate(sorted_articles, 1):
            article = item["article"]
            insight_count = len(item.get("insights", []))
            triple_count = len(item.get("triples", []))
            conn_count = len(item.get("connections", []))

            console.print(f"  {i}. [cyan]{article.title}[/cyan]")
            console.print(f"     [dim]{insight_count} insights, {triple_count} new facts, {conn_count} connections[/dim]")

            if article.summary:
                console.print(f"     {article.summary}")
            console.print()

    # Knowledge base stats
    kb_stats = kb.get_stats()
    console.print(f"[dim]Knowledge base: {kb_stats['total_insights']} total insights, {kb_stats['total_entities']} entities[/dim]")
    console.print()

    # Next steps
    console.print("[bold]What's Next:[/bold]")
    console.print("  - [cyan]rss perspectives[/cyan] - View multi-source perspectives on stories")
    console.print("  - [cyan]rss stories list[/cyan] - View story clusters")
    console.print("  - [cyan]rss query \"question\"[/cyan] - Query your knowledge base")
    console.print()
