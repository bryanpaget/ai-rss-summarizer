"""Tests for signal tagging functionality."""

import json
import pytest
from datetime import datetime

from src.storage import Article
from src.signal_tagger import SignalTagger, SignalTags


def test_signal_tags_serialization():
    """Test SignalTags JSON serialization."""
    tags = SignalTags(
        source_type=["primary"],
        evidence=["well-sourced", "documented"],
        reasoning=["balanced"],
        tone=["factual"],
        actionability=["actionable"],
    )

    # Test to_json
    json_str = tags.to_json()
    assert isinstance(json_str, str)

    # Test from_json
    restored = SignalTags.from_json(json_str)
    assert restored.source_type == ["primary"]
    assert restored.evidence == ["well-sourced", "documented"]
    assert restored.reasoning == ["balanced"]
    assert restored.tone == ["factual"]
    assert restored.actionability == ["actionable"]


def test_signal_tags_display_string():
    """Test tag display formatting."""
    tags = SignalTags(
        source_type=["primary"],
        evidence=["documented"],
        reasoning=["logical"],
        tone=["analytical"],
        actionability=["actionable"],
    )

    display = tags.to_display_string()
    assert "[primary]" in display
    assert "[documented]" in display
    assert "[logical]" in display
    assert "[analytical]" in display
    assert "[actionable]" in display


def test_signal_tags_has_any_tag():
    """Test tag presence checking."""
    tags = SignalTags(
        source_type=["primary"],
        evidence=["documented"],
        reasoning=["logical"],
        tone=["factual"],
        actionability=["awareness"],
    )

    assert tags.has_any_tag("primary", "secondary")
    assert tags.has_any_tag("documented")
    assert not tags.has_any_tag("speculative", "sensational")


def test_rule_based_tagger_primary_source():
    """Test rule-based tagging for primary source."""
    tagger = SignalTagger(use_llm=False)

    article = Article(
        id="test1",
        feed_url="https://example.com/rss",
        title="Breaking News",
        link="https://example.com/article1",
        published=datetime.now(),
        content="Our reporter witnessed the event first-hand and interviewed three officials.",
    )

    tags = tagger.tag_article(article)

    # Should detect primary source
    assert "primary" in tags.source_type

    # Should detect well-sourced evidence
    assert any(tag in tags.evidence for tag in ["well-sourced", "single-source"])


def test_rule_based_tagger_press_release():
    """Test rule-based tagging for press release."""
    tagger = SignalTagger(use_llm=False)

    article = Article(
        id="test2",
        feed_url="https://example.com/rss",
        title="Company Announcement",
        link="https://example.com/article2",
        published=datetime.now(),
        content="FOR IMMEDIATE RELEASE: Company XYZ announces new product launch.",
    )

    tags = tagger.tag_article(article)

    # Should detect press release
    assert "press-release" in tags.source_type


def test_rule_based_tagger_sensational():
    """Test rule-based tagging for sensational tone."""
    tagger = SignalTagger(use_llm=False)

    article = Article(
        id="test3",
        feed_url="https://example.com/rss",
        title="SHOCKING! You Won't Believe This!",
        link="https://example.com/article3",
        published=datetime.now(),
        content="This is the most incredible, stunning revelation ever!!! You won't believe what happened next!",
    )

    tags = tagger.tag_article(article)

    # Should detect sensational tone
    assert "sensational" in tags.tone


def test_rule_based_tagger_speculative():
    """Test rule-based tagging for speculative content."""
    tagger = SignalTagger(use_llm=False)

    article = Article(
        id="test4",
        feed_url="https://example.com/rss",
        title="Rumored Changes Coming",
        link="https://example.com/article4",
        published=datetime.now(),
        content="Sources say that major changes could possibly happen, though this remains unconfirmed.",
    )

    tags = tagger.tag_article(article)

    # Should detect speculative nature
    assert "speculative" in tags.source_type


def test_rule_based_tagger_balanced():
    """Test rule-based tagging for balanced reasoning."""
    tagger = SignalTagger(use_llm=False)

    article = Article(
        id="test5",
        feed_url="https://example.com/rss",
        title="Analysis of Policy Change",
        link="https://example.com/article5",
        published=datetime.now(),
        content="Supporters argue this will help the economy. However, critics say it may have negative effects.",
    )

    tags = tagger.tag_article(article)

    # Should detect balanced perspective
    assert "balanced" in tags.reasoning


def test_rule_based_tagger_satirical():
    """Test rule-based tagging for satirical content."""
    tagger = SignalTagger(use_llm=False)

    article = Article(
        id="test6",
        feed_url="https://example.com/rss",
        title="Satirical Article",
        link="https://theonion.com/article6",
        published=datetime.now(),
        content="This is clearly satire from The Onion.",
    )

    tags = tagger.tag_article(article)

    # Should detect satire by domain
    assert "satirical" in tags.source_type


def test_rule_based_tagger_actionable():
    """Test rule-based tagging for actionable content."""
    tagger = SignalTagger(use_llm=False)

    article = Article(
        id="test7",
        feed_url="https://example.com/rss",
        title="How to Prepare",
        link="https://example.com/article7",
        published=datetime.now(),
        content="Here's how you should prepare. Follow these steps before the deadline of March 15.",
    )

    tags = tagger.tag_article(article)

    # Should detect actionable content
    assert "actionable" in tags.actionability


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
