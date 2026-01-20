#!/usr/bin/env python3
"""Diagnostic script to show article routing under different selection strategies.

READ-ONLY: Does not modify any data. Shows what WOULD happen.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage import Storage


def main():
    storage = Storage("articles.db")

    MIN_CONTENT_LENGTH = 100

    print("=" * 70)
    print("ARTICLE ROUTING DIAGNOSTIC")
    print("=" * 70)
    print()

    # Get all articles for analysis
    all_articles = storage.get_articles()
    print(f"Total articles in database: {len(all_articles)}")
    print()

    # =======================================================================
    # VERSION 1: ORIGINAL (get_unanalyzed_articles)
    # =======================================================================
    print("-" * 70)
    print("VERSION 1: ORIGINAL BEHAVIOR (before any changes)")
    print("-" * 70)

    original_selected = storage.get_unanalyzed_articles(
        exclude_spam=True,
        min_content_length=MIN_CONTENT_LENGTH
    )

    print(f"Selection method: get_unanalyzed_articles()")
    print(f"Articles selected: {len(original_selected)}")
    print(f"All {len(original_selected)} go to LLM phase")
    print(f"All {len(original_selected)} go to Embedding phase")
    print()

    # =======================================================================
    # VERSION 2: BROKEN CHANGE (get_articles_with_gaps → all to LLM)
    # =======================================================================
    print("-" * 70)
    print("VERSION 2: BROKEN CHANGE (all gaps → all to LLM)")
    print("-" * 70)

    broken_selected = storage.get_articles_with_gaps(
        exclude_spam=True,
        min_content_length=MIN_CONTENT_LENGTH
    )

    print(f"Selection method: get_articles_with_gaps()")
    print(f"Articles selected: {len(broken_selected)}")
    print(f"All {len(broken_selected)} go to LLM phase (WRONG - overwrites existing!)")
    print(f"All {len(broken_selected)} go to Embedding phase")
    print()

    # Count how many would have existing work overwritten
    has_summary = sum(1 for a in broken_selected if a.summary)
    has_trends = sum(1 for a in broken_selected if a.trend_tags)
    has_signals = sum(1 for a in broken_selected if a.signal_tags)
    has_embedding = sum(1 for a in broken_selected if storage.get_embedding(a.id))

    print(f"DAMAGE: Would overwrite {has_summary} existing summaries")
    print(f"DAMAGE: Would overwrite {has_trends} existing trend tags")
    print(f"DAMAGE: Would overwrite {has_signals} existing signal tags")
    print()

    # =======================================================================
    # VERSION 3: CORRECT FIX (route by need)
    # =======================================================================
    print("-" * 70)
    print("VERSION 3: CORRECT FIX (route by actual need)")
    print("-" * 70)

    correct_selected = storage.get_articles_with_gaps(
        exclude_spam=True,
        min_content_length=MIN_CONTENT_LENGTH
    )

    # Categorize by what they actually need
    needs_llm = []  # Missing summary OR trend_tags OR signal_tags
    needs_embedding_only = []  # Has all tags but missing embedding

    for article in correct_selected:
        needs_summary = not article.summary
        needs_trends = not article.trend_tags
        needs_signals = not article.signal_tags
        needs_embed = storage.get_embedding(article.id) is None

        if needs_summary or needs_trends or needs_signals:
            needs_llm.append(article)
        elif needs_embed:
            needs_embedding_only.append(article)

    print(f"Selection method: get_articles_with_gaps()")
    print(f"Articles selected: {len(correct_selected)}")
    print()
    print(f"ROUTING:")
    print(f"  → LLM phase: {len(needs_llm)} articles (missing summary/tags)")
    print(f"  → Embedding only: {len(needs_embedding_only)} articles (have summary, need embedding)")
    print()
    print(f"EXISTING WORK TOUCHED: 0")
    print()

    # =======================================================================
    # SUMMARY COMPARISON
    # =======================================================================
    print("=" * 70)
    print("SUMMARY COMPARISON")
    print("=" * 70)
    print()
    print(f"{'Version':<20} {'Selected':<12} {'To LLM':<12} {'Overwrites':<12}")
    print("-" * 56)
    print(f"{'ORIGINAL':<20} {len(original_selected):<12} {len(original_selected):<12} {'0':<12}")
    print(f"{'BROKEN':<20} {len(broken_selected):<12} {len(broken_selected):<12} {has_summary:<12}")
    print(f"{'CORRECT':<20} {len(correct_selected):<12} {len(needs_llm):<12} {'0':<12}")
    print()

    # =======================================================================
    # SAMPLE ARTICLES (show routing decisions)
    # =======================================================================
    print("=" * 70)
    print("SAMPLE ARTICLE ROUTING (first 10 from each category)")
    print("=" * 70)
    print()

    # Articles that would be wrongly sent to LLM under broken version
    wrongly_to_llm = [a for a in broken_selected if a.summary and storage.get_embedding(a.id) is None]

    if wrongly_to_llm:
        print("ARTICLES THAT WOULD BE WRONGLY RE-PROCESSED (have summary, need only embedding):")
        for i, article in enumerate(wrongly_to_llm[:10]):
            print(f"  {i+1}. {article.title[:60]}...")
            print(f"      Has summary: YES | Has embedding: NO")
            print(f"      BROKEN: LLM + Embedding (overwrites summary!)")
            print(f"      CORRECT: Embedding only")
        if len(wrongly_to_llm) > 10:
            print(f"  ... and {len(wrongly_to_llm) - 10} more")
        print()

    # Articles that correctly need LLM
    correctly_need_llm = [a for a in needs_llm if not a.summary][:10]
    if correctly_need_llm:
        print("ARTICLES THAT CORRECTLY NEED LLM (missing summary):")
        for i, article in enumerate(correctly_need_llm[:10]):
            print(f"  {i+1}. {article.title[:60]}...")
            print(f"      Has summary: NO")
            print(f"      ROUTING: LLM phase (correct)")
        if len([a for a in needs_llm if not a.summary]) > 10:
            print(f"  ... and {len([a for a in needs_llm if not a.summary]) - 10} more")
        print()


if __name__ == "__main__":
    main()
