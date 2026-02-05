"""Tests for emergence detection module."""

import pytest
from datetime import datetime, timedelta

from src.emergence import (
    extract_terms,
    calculate_velocity,
    classify_trajectory,
    assign_confidence,
    generate_action_recommendation,
)


class TestExtractTerms:
    """Test term extraction from text."""

    def test_extracts_capitalized_phrases(self):
        """Test extraction of capitalized multi-word phrases."""
        text = "Constitutional AI is a new approach to AI safety."
        terms = extract_terms(text)
        assert "Constitutional AI" in terms or "constitutional ai" in [t.lower() for t in terms]

    def test_extracts_technical_terms(self):
        """Test extraction of technical terminology."""
        text = "Machine learning and neural networks are advancing rapidly."
        terms = extract_terms(text)
        terms_lower = [t.lower() for t in terms]
        assert "machine learning" in terms_lower or "neural network" in terms_lower

    def test_extracts_acronyms(self):
        """Test extraction of acronyms with expansions."""
        text = "LLM (Large Language Model) technology is evolving."
        terms = extract_terms(text)
        assert "LLM" in terms or "Large Language Model" in terms

    def test_filters_stopwords(self):
        """Test that stopword-only phrases are filtered."""
        text = "The and the or the but the in the on."
        terms = extract_terms(text)
        # Should not extract stopword-only phrases
        assert len([t for t in terms if all(w in ["the", "and", "or", "but", "in", "on"] for w in t.lower().split())]) == 0

    def test_respects_word_count_limits(self):
        """Test that terms respect min/max word count."""
        text = "Single AlongMultiWordPhraseThatIsWayTooLongToExtract"
        terms = extract_terms(text, min_words=2, max_words=4)
        # Should not extract single words or very long phrases
        assert "Single" not in terms

    def test_empty_text(self):
        """Test handling of empty text."""
        assert extract_terms("") == []
        assert extract_terms(None) == []


class TestCalculateVelocity:
    """Test velocity calculation."""

    def test_normal_growth(self):
        """Test velocity calculation for normal growth."""
        velocity = calculate_velocity(10, 5)
        assert velocity == 100.0  # 100% increase

    def test_decline(self):
        """Test velocity calculation for decline."""
        velocity = calculate_velocity(5, 10)
        assert velocity == -50.0  # 50% decrease

    def test_new_term(self):
        """Test velocity for completely new term."""
        velocity = calculate_velocity(5, 0)
        assert velocity == 100.0  # Max velocity for new terms

    def test_no_change(self):
        """Test velocity when counts are equal."""
        velocity = calculate_velocity(5, 5)
        assert velocity == 0.0

    def test_both_zero(self):
        """Test velocity when both counts are zero."""
        velocity = calculate_velocity(0, 0)
        assert velocity == 0.0


class TestClassifyTrajectory:
    """Test trajectory classification."""

    def test_research_to_mainstream(self):
        """Test identification of research to mainstream trajectory."""
        historical_counts = {
            "2_months_ago": 1,
            "1_month_ago": 2,
            "2_weeks_ago": 5,
            "1_week_ago": 8,
            "current": 12,
        }
        domains = ["Science & Research", "AI & Technology", "Business & Economy"]
        trajectory = classify_trajectory(historical_counts, domains)
        assert "Research" in trajectory or "Mainstream" in trajectory

    def test_niche_single_domain(self):
        """Test identification of niche single-domain trend."""
        historical_counts = {"current": 5}
        domains = ["AI & Technology"]
        trajectory = classify_trajectory(historical_counts, domains)
        assert "Niche" in trajectory or "single domain" in trajectory

    def test_cross_domain(self):
        """Test identification of cross-domain emergence."""
        historical_counts = {"current": 5}
        domains = ["AI & Technology", "Business & Economy"]
        trajectory = classify_trajectory(historical_counts, domains)
        assert "Cross-domain" in trajectory or "Widespread" in trajectory


class TestAssignConfidence:
    """Test confidence level assignment."""

    def test_high_confidence(self):
        """Test high confidence assignment."""
        confidence = assign_confidence(
            velocity=200,
            current_mentions=10,
            domain_count=3,
            weeks_of_data=4,
        )
        assert confidence == "High"

    def test_medium_confidence(self):
        """Test medium confidence assignment."""
        confidence = assign_confidence(
            velocity=120,
            current_mentions=5,
            domain_count=2,
            weeks_of_data=2,
        )
        assert confidence == "Medium"

    def test_low_confidence(self):
        """Test low confidence assignment."""
        confidence = assign_confidence(
            velocity=60,
            current_mentions=3,
            domain_count=1,
            weeks_of_data=1,
        )
        assert confidence == "Low"

    def test_watch_confidence(self):
        """Test watch level assignment."""
        confidence = assign_confidence(
            velocity=40,
            current_mentions=2,
            domain_count=1,
            weeks_of_data=1,
        )
        assert confidence == "Watch"


class TestGenerateActionRecommendation:
    """Test action recommendation generation."""

    def test_high_confidence_action(self):
        """Test action for high confidence trend."""
        action = generate_action_recommendation("High", 200, "Research → Mainstream")
        assert "Learn now" in action or "before" in action

    def test_medium_confidence_action(self):
        """Test action for medium confidence trend."""
        action = generate_action_recommendation("Medium", 120, "Technical → General")
        assert "prioritize" in action.lower() or "monitor" in action.lower()

    def test_low_confidence_action(self):
        """Test action for low confidence trend."""
        action = generate_action_recommendation("Low", 60, "Niche")
        assert "monitor" in action.lower() or "watch" in action.lower()

    def test_watch_action(self):
        """Test action for watch level trend."""
        action = generate_action_recommendation("Watch", 40, "Unknown")
        assert "early" in action.lower() or "watch" in action.lower()
