"""ARCHIVED: Deprecated LLM-based similarity tests.

These tests were for the old LLM-based story matching that has been
replaced with embedding-based similarity. Kept for historical reference.
See tests/test_embeddings.py for current tests.
"""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock

import pytest

from src.clustering import StoryClusterer
from src.storage import Storage, Article, Story, NewsItem
from src.llm_providers import LLMProvider


@pytest.mark.skip(reason="Threshold tests depend on LLM mocking. See test_embeddings.py for new tests.")
class TestStoryClustererThresholdUsage:
    """Tests for how similarity threshold is used in matching logic."""

    def test_threshold_used_in_find_matching_story(
        self, mock_llm_provider, mock_storage_with_stories
    ):
        """Test that threshold is used when finding matching stories."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)

        # Default threshold is 0.7, mock returns 0.85 confidence
        # So it should find a match
        assert clusterer.similarity_threshold == 0.7

    def test_threshold_affects_match_decisions(
        self, mock_llm_provider_low_confidence, mock_storage_with_stories
    ):
        """Test that threshold affects whether stories are matched."""
        # Low confidence provider returns 0.5 confidence
        clusterer = StoryClusterer(mock_llm_provider_low_confidence, mock_storage_with_stories)

        # With default threshold of 0.7, the 0.5 confidence should not match
        assert clusterer.similarity_threshold == 0.7

    def test_lowering_threshold_allows_more_matches(
        self, mock_llm_provider_low_confidence, mock_storage_with_stories
    ):
        """Test that lowering threshold can allow more matches."""
        clusterer = StoryClusterer(mock_llm_provider_low_confidence, mock_storage_with_stories)

        # Lower the threshold to allow the 0.5 confidence to match
        clusterer.similarity_threshold = 0.4

        assert clusterer.similarity_threshold == 0.4

    def test_raising_threshold_prevents_matches(
        self, mock_llm_provider, mock_storage_with_stories
    ):
        """Test that raising threshold can prevent matches."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)

        # Raise the threshold above the 0.85 confidence
        clusterer.similarity_threshold = 0.9

        assert clusterer.similarity_threshold == 0.9


# =============================================================================
# Tests for cluster_article Method - Creating New Stories
# =============================================================================


class TestClusterArticleNewStory:
    """Tests for cluster_article method when creating new stories."""

    def test_cluster_article_creates_new_story_with_empty_storage(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that cluster_article creates a new story when storage is empty."""
        # Configure mock to have no active stories
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Should create a new story
        assert result is not None
        assert isinstance(result, Story)
        mock_storage.save_story.assert_called_once()
        mock_storage.update_article_story.assert_called_once()

    def test_cluster_article_new_story_contains_article_id(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that new story contains the clustered article's ID."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        assert sample_article.id in result.article_ids
        assert len(result.article_ids) == 1

    def test_cluster_article_new_story_has_emerging_state(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that new stories start with 'emerging' lifecycle state."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        assert result.lifecycle_state == "emerging"

    def test_cluster_article_new_story_has_generated_title(
        self, mock_llm_provider_with_title, mock_storage, sample_article
    ):
        """Test that new story gets a generated title."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_title, mock_storage)
        result = clusterer.cluster_article(sample_article)

        assert result.title is not None
        assert len(result.title) > 0

    def test_cluster_article_new_story_has_valid_uuid(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that new story has a valid UUID as ID."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Should be a valid UUID format (36 chars with dashes)
        assert result.id is not None
        assert len(result.id) == 36
        assert result.id.count("-") == 4

    def test_cluster_article_new_story_empty_news_items(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that new story starts with empty news_item_ids."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        assert result.news_item_ids == []

    def test_cluster_article_new_story_has_keywords(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that new story has extracted keywords."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        assert result.keywords is not None
        assert len(result.keywords) > 0

    def test_cluster_article_new_story_saves_to_storage(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that new story is saved to storage."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Verify save_story was called with the created story
        mock_storage.save_story.assert_called_once()
        saved_story = mock_storage.save_story.call_args[0][0]
        assert saved_story.id == result.id

    def test_cluster_article_updates_article_story_link(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that article's story_id is updated in storage."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        mock_storage.update_article_story.assert_called_once_with(
            sample_article.id, result.id
        )


class TestClusterArticleNoMatchCreatesNew:
    """Tests for cluster_article when LLM indicates no match found."""

    def test_cluster_article_no_match_creates_new_story(
        self, mock_llm_provider_not_same_story, mock_storage_with_stories, sample_article
    ):
        """Test that a new story is created when no existing stories match."""
        clusterer = StoryClusterer(mock_llm_provider_not_same_story, mock_storage_with_stories)
        result = clusterer.cluster_article(sample_article)

        # Should create new story since provider says "not same story"
        assert result is not None
        mock_storage_with_stories.save_story.assert_called()

    def test_cluster_article_below_threshold_creates_new(
        self, mock_llm_provider_low_confidence, mock_storage_with_stories, sample_article
    ):
        """Test that low confidence (below threshold) creates new story."""
        # Low confidence provider returns 0.5, default threshold is 0.7
        clusterer = StoryClusterer(mock_llm_provider_low_confidence, mock_storage_with_stories)
        result = clusterer.cluster_article(sample_article)

        # Should create new story since confidence < threshold
        assert result is not None
        mock_storage_with_stories.save_story.assert_called()


# =============================================================================
# Tests for cluster_article Method - Adding to Existing Stories
# =============================================================================


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestClusterArticleExistingStory:
    """Tests for cluster_article when adding to existing stories."""

    def test_cluster_article_matches_existing_story(
        self, mock_llm_provider, mock_storage_with_stories, sample_article
    ):
        """Test that article is added to matching existing story."""
        # Mock provider returns is_same_story=True with 0.85 confidence
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        result = clusterer.cluster_article(sample_article)

        # Should update existing story, not create new
        assert result is not None
        mock_storage_with_stories.update_story.assert_called()
        mock_storage_with_stories.update_article_story.assert_called()

    def test_cluster_article_adds_article_id_to_story(
        self, mock_llm_provider, sample_article, sample_story
    ):
        """Test that article ID is added to the matched story's article_ids."""
        # Create mock storage with a specific story
        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]
        mock_storage.update_story.return_value = None
        mock_storage.update_article_story.return_value = None

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Article ID should be in the story
        assert sample_article.id in result.article_ids

    def test_cluster_article_updates_story_timestamp(
        self, mock_llm_provider, sample_article, sample_story
    ):
        """Test that story's last_updated is updated when article is added."""
        mock_storage = MagicMock(spec=Storage)
        original_updated = sample_story.last_updated
        mock_storage.get_active_stories.return_value = [sample_story]
        mock_storage.update_story.return_value = None
        mock_storage.update_article_story.return_value = None

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # last_updated should be more recent
        assert result.last_updated >= original_updated

    def test_cluster_article_no_duplicate_article_ids(
        self, mock_llm_provider, sample_article
    ):
        """Test that article ID is not duplicated if already present."""
        # Create story that already contains the article
        existing_story = Story(
            id="story-existing-1",
            title="Existing Story",
            description="Test story",
            keywords=["test", "story"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=2),
            lifecycle_state="developing",
            article_ids=[sample_article.id],  # Already contains this article
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [existing_story]
        mock_storage.update_story.return_value = None
        mock_storage.update_article_story.return_value = None

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Article ID should appear only once
        assert result.article_ids.count(sample_article.id) == 1

    def test_cluster_article_high_confidence_matches_existing(
        self, mock_llm_provider_high_confidence, mock_storage_with_stories, sample_article
    ):
        """Test that high confidence LLM response matches to existing story."""
        clusterer = StoryClusterer(mock_llm_provider_high_confidence, mock_storage_with_stories)
        result = clusterer.cluster_article(sample_article)

        # Should update existing story (not create new)
        mock_storage_with_stories.update_story.assert_called()

    def test_cluster_article_updates_keywords(
        self, mock_llm_provider_with_keywords, sample_article, sample_story
    ):
        """Test that story keywords are updated with new article keywords."""
        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]
        mock_storage.update_story.return_value = None
        mock_storage.update_article_story.return_value = None

        # Configure LLM to indicate same story AND provide keywords
        mock_llm_provider_with_keywords.generate.side_effect = [
            json.dumps({
                "is_same_story": True,
                "confidence": 0.9,
                "reasoning": "Same topic"
            }),
            "new, unique, keywords, added"  # Keywords extraction
        ]

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Story should have been updated
        mock_storage.update_story.assert_called()


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestClusterArticleWithRealStorage:
    """Tests for cluster_article with real storage (integration-like tests)."""

    def test_cluster_article_real_storage_new_story(
        self, mock_llm_provider_with_keywords, storage_empty, sample_article
    ):
        """Test cluster_article creates story with real storage."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, storage_empty)
        result = clusterer.cluster_article(sample_article)

        # Verify story was saved
        assert result is not None
        saved_story = storage_empty.get_story(result.id)
        assert saved_story is not None
        assert saved_story.id == result.id

    def test_cluster_article_real_storage_add_to_existing(
        self, mock_llm_provider, storage_with_stories, sample_article_tech
    ):
        """Test cluster_article adds to existing story with real storage."""
        # Get existing stories
        existing_stories = storage_with_stories.get_active_stories(limit=10)
        assert len(existing_stories) > 0

        clusterer = StoryClusterer(mock_llm_provider, storage_with_stories)
        result = clusterer.cluster_article(sample_article_tech)

        # Should match one of the existing stories
        assert result is not None

    def test_cluster_multiple_articles_creates_one_story(
        self, mock_llm_provider, storage_empty, similar_articles
    ):
        """Test that similar articles are clustered into one story."""
        # Configure LLM to return same story for second article
        responses = [
            # First article - creates new story
            "AI Technology Coverage",  # Title
            "Coverage of AI developments.",  # Description
            "AI, technology, machine learning",  # Keywords
            # Second article - should match first
            json.dumps({
                "is_same_story": True,
                "confidence": 0.9,
                "reasoning": "Both about same company's product"
            }),
            "new, product, launch",  # Keywords for update
        ]
        mock_llm_provider.generate.side_effect = responses

        clusterer = StoryClusterer(mock_llm_provider, storage_empty)

        # Cluster first article
        story1 = clusterer.cluster_article(similar_articles[0])

        # Cluster second article - should go to same story
        story2 = clusterer.cluster_article(similar_articles[1])

        # Both should be in same story
        assert story1.id == story2.id
        assert similar_articles[0].id in story2.article_ids
        assert similar_articles[1].id in story2.article_ids


# =============================================================================
# Tests for cluster_article Method - Edge Cases
# =============================================================================


class TestClusterArticleEdgeCases:
    """Tests for cluster_article edge cases."""

    def test_cluster_article_with_no_content(
        self, mock_llm_provider_with_keywords, mock_storage, empty_article
    ):
        """Test cluster_article handles article with empty content."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(empty_article)

        # Should still create a story
        assert result is not None
        assert isinstance(result, Story)

    def test_cluster_article_with_minimal_article(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article_minimal
    ):
        """Test cluster_article handles minimal article."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article_minimal)

        assert result is not None
        assert isinstance(result, Story)

    def test_cluster_article_with_unicode_content(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article_unicode
    ):
        """Test cluster_article handles unicode content properly."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article_unicode)

        assert result is not None
        assert isinstance(result, Story)

    def test_cluster_article_with_special_characters(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article_special_chars
    ):
        """Test cluster_article handles special characters."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article_special_chars)

        assert result is not None
        assert isinstance(result, Story)

    def test_cluster_article_with_very_long_content(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article_very_long
    ):
        """Test cluster_article handles very long article content."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article_very_long)

        assert result is not None
        assert isinstance(result, Story)

    def test_cluster_article_with_no_published_date(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article_no_published
    ):
        """Test cluster_article handles article without published date."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(sample_article_no_published)

        assert result is not None
        # first_seen should default to now
        assert result.first_seen is not None

    def test_cluster_article_with_string_published_date(
        self, mock_llm_provider_with_keywords, mock_storage, article_with_published_string
    ):
        """Test cluster_article handles article with ISO string date."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.cluster_article(article_with_published_string)

        assert result is not None
        assert result.first_seen is not None


class TestClusterArticleErrorHandling:
    """Tests for cluster_article error handling."""

    def test_cluster_article_llm_error_uses_keyword_fallback(
        self, mock_llm_provider_error, mock_storage_with_stories, sample_article
    ):
        """Test that LLM errors fall back to keyword matching."""
        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage_with_stories)

        # Should not raise exception - uses keyword fallback
        result = clusterer.cluster_article(sample_article)

        assert result is not None

    def test_cluster_article_invalid_json_response(
        self, mock_llm_provider_invalid_json, mock_storage_with_stories, sample_article
    ):
        """Test handling of invalid JSON response from LLM."""
        clusterer = StoryClusterer(mock_llm_provider_invalid_json, mock_storage_with_stories)

        # Should handle gracefully using fallback parsing
        result = clusterer.cluster_article(sample_article)

        assert result is not None

    def test_cluster_article_with_unavailable_llm(
        self, mock_llm_provider_unavailable, mock_storage, sample_article
    ):
        """Test cluster_article with unavailable LLM provider."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider_unavailable, mock_storage)

        # Should handle unavailable provider (likely creates new story with fallbacks)
        result = clusterer.cluster_article(sample_article)

        # Should still produce a story (with fallback title/description)
        assert result is not None


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestClusterArticleThresholdBehavior:
    """Tests for cluster_article threshold-related behavior."""

    def test_cluster_article_custom_threshold_high(
        self, mock_llm_provider, mock_storage_with_stories, sample_article
    ):
        """Test that high threshold prevents matching."""
        # Mock returns 0.85 confidence, set threshold higher
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        clusterer.similarity_threshold = 0.95

        result = clusterer.cluster_article(sample_article)

        # Should create new story because 0.85 < 0.95
        mock_storage_with_stories.save_story.assert_called()

    def test_cluster_article_custom_threshold_low(
        self, mock_llm_provider_low_confidence, mock_storage_with_stories, sample_article
    ):
        """Test that low threshold allows more matches."""
        # Mock returns 0.5 confidence, set threshold lower
        clusterer = StoryClusterer(mock_llm_provider_low_confidence, mock_storage_with_stories)
        clusterer.similarity_threshold = 0.4

        result = clusterer.cluster_article(sample_article)

        # Should match existing story because 0.5 >= 0.4
        mock_storage_with_stories.update_story.assert_called()

    def test_cluster_article_threshold_exactly_met(
        self, sample_article
    ):
        """Test behavior when confidence exactly equals threshold."""
        # Create provider that returns exactly 0.75 confidence
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.name = "mock-provider"
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.75,  # Exactly at threshold
            "reasoning": "Exactly at threshold"
        })

        mock_storage = MagicMock(spec=Storage)
        sample_story = Story(
            id="story-test",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article-1"],
            news_item_ids=[],
        )
        mock_storage.get_active_stories.return_value = [sample_story]
        mock_storage.update_story.return_value = None
        mock_storage.update_article_story.return_value = None

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        result = clusterer.cluster_article(sample_article)

        # Should match (>= threshold)
        mock_storage.update_story.assert_called()


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestClusterArticleMultipleStories:
    """Tests for cluster_article with multiple existing stories."""

    def test_cluster_article_selects_best_match(self, sample_article):
        """Test that the best matching story is selected."""
        # Create mock provider that returns different scores for different stories
        call_count = [0]

        def generate_response(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "is_same_story": True,
                    "confidence": 0.6,
                    "reasoning": "Moderate match"
                })
            elif call_count[0] == 2:
                return json.dumps({
                    "is_same_story": True,
                    "confidence": 0.9,  # Best match
                    "reasoning": "Strong match"
                })
            else:
                return json.dumps({
                    "is_same_story": True,
                    "confidence": 0.7,
                    "reasoning": "Good match"
                })

        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.side_effect = generate_response

        # Create multiple stories
        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["common", f"keyword{i}"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}-1"],
                news_item_ids=[],
            )
            for i in range(3)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories
        mock_storage.update_story.return_value = None
        mock_storage.update_article_story.return_value = None

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Should select story-1 (the one with 0.9 confidence)
        assert result.id == "story-1"

    def test_cluster_article_no_match_among_many(self, sample_article):
        """Test that no match among many stories creates new story."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": False,
            "confidence": 0.2,
            "reasoning": "Not related"
        })

        # Create multiple stories that won't match
        stories = [
            Story(
                id=f"story-{i}",
                title=f"Different Story {i}",
                description=f"Description {i}",
                keywords=["unrelated", f"topic{i}"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}-1"],
                news_item_ids=[],
            )
            for i in range(5)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories
        mock_storage.save_story.return_value = None
        mock_storage.update_article_story.return_value = None

        # Set up LLM responses for title/description/keywords generation
        responses = [
            json.dumps({"is_same_story": False, "confidence": 0.2, "reasoning": "No"}),
            json.dumps({"is_same_story": False, "confidence": 0.2, "reasoning": "No"}),
            json.dumps({"is_same_story": False, "confidence": 0.2, "reasoning": "No"}),
            json.dumps({"is_same_story": False, "confidence": 0.2, "reasoning": "No"}),
            json.dumps({"is_same_story": False, "confidence": 0.2, "reasoning": "No"}),
            "New Story Title",  # Title generation
            "New story description",  # Description generation
            "keyword1, keyword2",  # Keyword extraction
        ]
        mock_llm_provider.generate.side_effect = responses

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Should create new story
        mock_storage.save_story.assert_called()

    def test_cluster_article_first_above_threshold_wins(self, sample_article):
        """Test that stories are evaluated in order and best is selected."""
        # All above threshold but different scores
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True

        responses = [
            json.dumps({"is_same_story": True, "confidence": 0.85, "reasoning": "Good"}),
            json.dumps({"is_same_story": True, "confidence": 0.95, "reasoning": "Best"}),
            json.dumps({"is_same_story": True, "confidence": 0.8, "reasoning": "OK"}),
        ]
        mock_llm_provider.generate.side_effect = responses

        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(3)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories
        mock_storage.update_story.return_value = None
        mock_storage.update_article_story.return_value = None

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.cluster_article(sample_article)

        # Should select story-1 (0.95 confidence - the best)
        assert result.id == "story-1"


class TestClusterArticleBulkProcessing:
    """Tests for clustering multiple articles."""

    def test_cluster_bulk_articles_creates_and_groups(
        self, mock_llm_provider, storage_empty, sample_articles_bulk
    ):
        """Test clustering multiple articles creates appropriate groupings."""
        # Configure LLM to create new stories for first 3, then group rest
        call_count = [0]

        def generate_response(*args, **kwargs):
            call_count[0] += 1
            # First 3 articles create new stories (no active stories to match)
            if call_count[0] <= 9:  # 3 articles * 3 LLM calls each (title, desc, keywords)
                # This is for new story creation
                if call_count[0] % 3 == 1:
                    return "Generated Title"
                elif call_count[0] % 3 == 2:
                    return "Generated description."
                else:
                    return "keyword1, keyword2, keyword3"
            else:
                # After first 3 articles, match to existing stories
                return json.dumps({
                    "is_same_story": True,
                    "confidence": 0.85,
                    "reasoning": "Same topic"
                })

        mock_llm_provider.generate.side_effect = generate_response

        clusterer = StoryClusterer(mock_llm_provider, storage_empty)

        stories_created = []
        for article in sample_articles_bulk[:5]:
            story = clusterer.cluster_article(article)
            if story.id not in [s.id for s in stories_created]:
                stories_created.append(story)

        # Should have some stories created
        assert len(stories_created) >= 1

    def test_cluster_dissimilar_articles_creates_separate_stories(
        self, mock_llm_provider_not_same_story, storage_empty, dissimilar_articles
    ):
        """Test that dissimilar articles are put in different stories."""
        # Configure to always say not same story, then provide new story metadata
        mock_llm_provider_not_same_story.generate.side_effect = [
            # First article - new story creation
            "AI Breakthrough Story",
            "Coverage of AI technology breakthrough.",
            "AI, technology, neural networks",
            # Second article - check against existing, then create new
            json.dumps({
                "is_same_story": False,
                "confidence": 0.1,
                "reasoning": "Completely different topics"
            }),
            "Championship Victory",
            "Local team wins the championship.",
            "sports, basketball, championship",
        ]

        clusterer = StoryClusterer(mock_llm_provider_not_same_story, storage_empty)

        story1 = clusterer.cluster_article(dissimilar_articles[0])
        story2 = clusterer.cluster_article(dissimilar_articles[1])

        # Should be in different stories
        assert story1.id != story2.id


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestClusterArticleIntegration:
    """Integration tests for cluster_article with full clustering setup."""

    def test_cluster_article_full_integration(
        self, full_clustering_setup, sample_article
    ):
        """Test cluster_article with full clustering environment."""
        clusterer = full_clustering_setup["clusterer"]

        result = clusterer.cluster_article(sample_article)

        assert result is not None
        assert isinstance(result, Story)
        assert sample_article.id in result.article_ids

    def test_cluster_article_integration_with_data(
        self, clustering_with_data
    ):
        """Test cluster_article with pre-populated data."""
        clusterer = clustering_with_data["clusterer"]
        storage = clustering_with_data["storage"]

        # Get an article to cluster
        articles = storage.get_articles(limit=1)
        if articles:
            article = articles[0]
            result = clusterer.cluster_article(article)

            assert result is not None
            assert article.id in result.article_ids

    def test_cluster_article_sequence(self, full_clustering_setup):
        """Test clustering a sequence of related articles."""
        clusterer = full_clustering_setup["clusterer"]

        # Create sequence of related articles
        articles = [
            Article(
                id=f"sequence-article-{i}",
                feed_url="https://example.com/feed.xml",
                title=f"Tech News Update {i}",
                link=f"https://example.com/article-{i}",
                published=datetime.now() - timedelta(hours=i),
                content=f"Update {i} on the ongoing tech story. More details emerging.",
                summary=f"Tech update {i}",
            )
            for i in range(3)
        ]

        # Configure LLM to match subsequent articles to first story
        llm = full_clustering_setup["llm_provider"]

        responses = [
            # First article - new story
            "Generated Story Title",
            "Generated story description.",
            "keyword1, keyword2, keyword3",
            # Second article - match to first
            json.dumps({"is_same_story": True, "confidence": 0.9, "reasoning": "Same story"}),
            "keyword4, keyword5",
            # Third article - match to first
            json.dumps({"is_same_story": True, "confidence": 0.88, "reasoning": "Same story"}),
            "keyword6, keyword7",
        ]
        llm.generate.side_effect = responses

        # Cluster all articles
        results = [clusterer.cluster_article(article) for article in articles]

        # All should be in the same story
        assert results[0].id == results[1].id == results[2].id
        assert len(results[2].article_ids) == 3


# =============================================================================
# Tests for find_matching_story Method
# =============================================================================


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryBasic:
    """Basic tests for find_matching_story method."""

    def test_find_matching_story_returns_none_with_empty_storage(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that find_matching_story returns None when no active stories exist."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        assert result is None
        mock_storage.get_active_stories.assert_called_once_with(limit=50)

    def test_find_matching_story_returns_match_above_threshold(
        self, mock_llm_provider, mock_storage_with_stories, sample_article
    ):
        """Test that find_matching_story returns a match when confidence exceeds threshold."""
        # Mock provider returns high confidence (0.85 > default 0.75 threshold)
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        result = clusterer.find_matching_story(sample_article)

        assert result is not None
        # Should be one of the stories from mock_storage_with_stories

    def test_find_matching_story_returns_none_below_threshold(
        self, mock_llm_provider_low_confidence, mock_storage_with_stories, sample_article
    ):
        """Test that find_matching_story returns None when confidence is below threshold."""
        # Low confidence provider returns 0.5 < default 0.75 threshold
        clusterer = StoryClusterer(mock_llm_provider_low_confidence, mock_storage_with_stories)
        result = clusterer.find_matching_story(sample_article)

        assert result is None

    def test_find_matching_story_returns_none_when_not_same_story(
        self, mock_llm_provider_not_same_story, mock_storage_with_stories, sample_article
    ):
        """Test that find_matching_story returns None when LLM says not same story."""
        clusterer = StoryClusterer(mock_llm_provider_not_same_story, mock_storage_with_stories)
        result = clusterer.find_matching_story(sample_article)

        assert result is None

    def test_find_matching_story_calls_get_active_stories_with_limit(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that find_matching_story calls get_active_stories with limit=50."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.find_matching_story(sample_article)

        mock_storage.get_active_stories.assert_called_once_with(limit=50)

    def test_find_matching_story_compares_with_all_stories(
        self, sample_article
    ):
        """Test that find_matching_story compares article with all active stories."""
        call_count = [0]

        def track_comparisons(*args, **kwargs):
            call_count[0] += 1
            return json.dumps({
                "is_same_story": False,
                "confidence": 0.3,
                "reasoning": "Different"
            })

        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.side_effect = track_comparisons

        # Create 5 stories
        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(5)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.find_matching_story(sample_article)

        # Should call generate once per story
        assert call_count[0] == 5


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryThresholdBehavior:
    """Tests for find_matching_story threshold behavior."""

    def test_find_matching_story_at_exact_threshold(self, sample_article):
        """Test behavior when confidence exactly equals threshold."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.75,  # Exactly at default threshold
            "reasoning": "Exact match"
        })

        sample_story = Story(
            id="story-exact",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should match because >= threshold (not just >)
        assert result is not None
        assert result.id == "story-exact"

    def test_find_matching_story_just_below_threshold(self, sample_article):
        """Test behavior when confidence is just below threshold."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.74,  # Just below default threshold
            "reasoning": "Close match"
        })

        sample_story = Story(
            id="story-close",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should not match because < threshold
        assert result is None

    def test_find_matching_story_with_custom_high_threshold(self, sample_article):
        """Test with custom high threshold that prevents matching."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Good match"
        })

        sample_story = Story(
            id="story-high",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.similarity_threshold = 0.95  # Very high threshold

        result = clusterer.find_matching_story(sample_article)

        # Should not match because 0.85 < 0.95
        assert result is None

    def test_find_matching_story_with_custom_low_threshold(self, sample_article):
        """Test with custom low threshold that allows matching."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.5,  # Would fail default threshold
            "reasoning": "Weak match"
        })

        sample_story = Story(
            id="story-low",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.similarity_threshold = 0.4  # Low threshold

        result = clusterer.find_matching_story(sample_article)

        # Should match because 0.5 >= 0.4
        assert result is not None
        assert result.id == "story-low"

    def test_find_matching_story_threshold_zero_matches_any(self, sample_article):
        """Test that threshold of 0 matches any is_same_story=True."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.01,  # Very low confidence
            "reasoning": "Minimal match"
        })

        sample_story = Story(
            id="story-zero",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.similarity_threshold = 0.0  # Threshold of zero

        result = clusterer.find_matching_story(sample_article)

        # Should match because 0.01 >= 0.0
        assert result is not None

    def test_find_matching_story_threshold_one_requires_perfect(self, sample_article):
        """Test that threshold of 1.0 requires perfect confidence."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.99,  # Very high but not perfect
            "reasoning": "Almost perfect"
        })

        sample_story = Story(
            id="story-one",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.similarity_threshold = 1.0  # Perfect threshold

        result = clusterer.find_matching_story(sample_article)

        # Should not match because 0.99 < 1.0
        assert result is None

    def test_find_matching_story_threshold_one_matches_perfect(self, sample_article):
        """Test that threshold of 1.0 matches confidence of 1.0."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 1.0,  # Perfect confidence
            "reasoning": "Perfect match"
        })

        sample_story = Story(
            id="story-perfect",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.similarity_threshold = 1.0

        result = clusterer.find_matching_story(sample_article)

        # Should match because 1.0 >= 1.0
        assert result is not None


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryBestMatchSelection:
    """Tests for best match selection in find_matching_story."""

    def test_find_matching_story_selects_highest_confidence(self, sample_article):
        """Test that the story with highest confidence is selected."""
        call_count = [0]

        def generate_varied_confidence(*args, **kwargs):
            call_count[0] += 1
            confidences = [0.8, 0.95, 0.85]  # Story 1 has highest confidence
            idx = (call_count[0] - 1) % 3
            return json.dumps({
                "is_same_story": True,
                "confidence": confidences[idx],
                "reasoning": f"Match {idx}"
            })

        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.side_effect = generate_varied_confidence

        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(3)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should select story-1 (0.95 confidence)
        assert result is not None
        assert result.id == "story-1"

    def test_find_matching_story_all_above_threshold_highest_wins(self, sample_article):
        """Test that when all are above threshold, highest still wins."""
        call_count = [0]

        def generate_all_high(*args, **kwargs):
            call_count[0] += 1
            # All above 0.75 threshold but story-2 is highest
            confidences = [0.76, 0.77, 0.99]
            idx = (call_count[0] - 1) % 3
            return json.dumps({
                "is_same_story": True,
                "confidence": confidences[idx],
                "reasoning": f"Match {idx}"
            })

        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.side_effect = generate_all_high

        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(3)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should select story-2 (0.99 confidence)
        assert result is not None
        assert result.id == "story-2"

    def test_find_matching_story_tie_breaker_first_encountered(self, sample_article):
        """Test that equal confidence scores select first story encountered."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,  # Same confidence for all
            "reasoning": "Equal match"
        })

        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(3)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Due to > comparison in _calculate_similarity, first story with max score wins
        # story-0 gets 0.85, story-1 gets 0.85 (not > 0.85, so not updated)
        assert result is not None
        assert result.id == "story-0"

    def test_find_matching_story_some_above_some_below_threshold(self, sample_article):
        """Test when some stories are above and some below threshold."""
        call_count = [0]

        def generate_mixed(*args, **kwargs):
            call_count[0] += 1
            # Story 0: below, Story 1: above, Story 2: below
            confidences = [0.5, 0.9, 0.6]
            idx = (call_count[0] - 1) % 3
            return json.dumps({
                "is_same_story": True,
                "confidence": confidences[idx],
                "reasoning": f"Match {idx}"
            })

        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.side_effect = generate_mixed

        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(3)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should select story-1 (only one with 0.9 >= 0.75)
        assert result is not None
        assert result.id == "story-1"


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryNoMatchesCases:
    """Tests for find_matching_story when no matches are found."""

    def test_find_matching_story_empty_active_stories(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test returns None when no active stories exist."""
        mock_storage.get_active_stories.return_value = []

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        assert result is None

    def test_find_matching_story_all_stories_not_same(self, sample_article):
        """Test returns None when LLM says none are same story."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": False,
            "confidence": 0.2,
            "reasoning": "Not the same"
        })

        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(5)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        assert result is None

    def test_find_matching_story_all_below_threshold(self, sample_article):
        """Test returns None when all confidences are below threshold."""
        call_count = [0]

        def generate_low_confidence(*args, **kwargs):
            call_count[0] += 1
            # All confidences below 0.75
            confidences = [0.3, 0.5, 0.6, 0.7, 0.74]
            idx = (call_count[0] - 1) % 5
            return json.dumps({
                "is_same_story": True,
                "confidence": confidences[idx],
                "reasoning": f"Low match {idx}"
            })

        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.side_effect = generate_low_confidence

        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(5)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # All below 0.75 threshold
        assert result is None

    def test_find_matching_story_is_same_story_false_with_high_confidence(
        self, sample_article
    ):
        """Test that is_same_story=False returns 0 score even with high confidence."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": False,  # Not same story
            "confidence": 0.95,  # High confidence in the "no" answer
            "reasoning": "Definitely not the same"
        })

        sample_story = Story(
            id="story-diff",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should return None because is_same_story is False
        assert result is None

    def test_find_matching_story_zero_confidence_no_match(self, sample_article):
        """Test that confidence of 0 does not match due to > comparison with initial best_score."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.0,  # Zero confidence
            "reasoning": "No confidence"
        })

        sample_story = Story(
            id="story-zero-conf",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.similarity_threshold = 0.0

        result = clusterer.find_matching_story(sample_article)

        # Returns None because: score (0.0) > best_score (0.0) is False,
        # so best_match stays None even though threshold check passes
        assert result is None


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryWithRealStorage:
    """Tests for find_matching_story with real storage (integration-like)."""

    def test_find_matching_story_real_storage_empty(
        self, mock_llm_provider, storage_empty, sample_article
    ):
        """Test find_matching_story with empty real storage."""
        clusterer = StoryClusterer(mock_llm_provider, storage_empty)
        result = clusterer.find_matching_story(sample_article)

        assert result is None

    def test_find_matching_story_real_storage_with_stories(
        self, mock_llm_provider, storage_with_stories, sample_article
    ):
        """Test find_matching_story with real storage containing stories."""
        clusterer = StoryClusterer(mock_llm_provider, storage_with_stories)
        result = clusterer.find_matching_story(sample_article)

        # Mock provider returns high confidence match
        assert result is not None

    def test_find_matching_story_real_storage_no_match(
        self, mock_llm_provider_not_same_story, storage_with_stories, sample_article
    ):
        """Test find_matching_story returns None with real storage when no match."""
        clusterer = StoryClusterer(mock_llm_provider_not_same_story, storage_with_stories)
        result = clusterer.find_matching_story(sample_article)

        assert result is None


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryErrorHandling:
    """Tests for find_matching_story error handling."""

    def test_find_matching_story_llm_error_uses_fallback(
        self, mock_llm_provider_error, sample_article
    ):
        """Test that LLM errors trigger keyword-based fallback."""
        # Create story with keywords that will be in the article
        sample_story = Story(
            id="story-fallback",
            title="AI Technology News",
            description="Tech news about AI",
            keywords=["breaking", "major", "tech", "company", "AI"],  # Matches article
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should use keyword fallback - may or may not match based on keyword overlap
        # The important thing is no exception is raised
        # The result depends on keyword similarity calculation

    def test_find_matching_story_invalid_json_uses_fallback(
        self, mock_llm_provider_invalid_json, sample_article
    ):
        """Test that invalid JSON response triggers fallback parsing."""
        sample_story = Story(
            id="story-invalid",
            title="Test Story",
            description="Test",
            keywords=["test", "article", "content"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider_invalid_json, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Invalid JSON provider returns text with "same" keyword
        # Fallback parser should detect this and return is_same_story=True with confidence=0.7
        # 0.7 is below default 0.75 threshold
        assert result is None

    def test_find_matching_story_llm_returns_empty_string(self, sample_article):
        """Test handling of empty LLM response."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = ""  # Empty response

        sample_story = Story(
            id="story-empty",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Empty response should trigger fallback - returns False with 0.3 confidence
        assert result is None

    def test_find_matching_story_llm_returns_none(self, sample_article):
        """Test handling when LLM returns None."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = None

        sample_story = Story(
            id="story-none",
            title="Test Story",
            description="Test",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        # Should not raise, should use keyword fallback
        try:
            result = clusterer.find_matching_story(sample_article)
            # If no exception, test passes
        except TypeError:
            # If generate returns None, fallback should handle it
            # If TypeError is raised, the code needs to handle None
            pass


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryEdgeCases:
    """Edge case tests for find_matching_story."""

    def test_find_matching_story_with_unicode_content(
        self, mock_llm_provider, mock_storage_with_stories, sample_article_unicode
    ):
        """Test find_matching_story handles unicode content."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        result = clusterer.find_matching_story(sample_article_unicode)

        # Should work without error
        # Result depends on LLM comparison

    def test_find_matching_story_with_special_chars(
        self, mock_llm_provider, mock_storage_with_stories, sample_article_special_chars
    ):
        """Test find_matching_story handles special characters."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        result = clusterer.find_matching_story(sample_article_special_chars)

        # Should work without error

    def test_find_matching_story_with_very_long_content(
        self, mock_llm_provider, mock_storage_with_stories, sample_article_very_long
    ):
        """Test find_matching_story handles very long content."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        result = clusterer.find_matching_story(sample_article_very_long)

        # Should work without error - content is truncated in prompt

    def test_find_matching_story_with_empty_content_article(
        self, mock_llm_provider, mock_storage_with_stories, empty_article
    ):
        """Test find_matching_story handles empty content article."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        result = clusterer.find_matching_story(empty_article)

        # Should work without error

    def test_find_matching_story_with_minimal_article(
        self, mock_llm_provider, mock_storage_with_stories, sample_article_minimal
    ):
        """Test find_matching_story handles minimal article."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)
        result = clusterer.find_matching_story(sample_article_minimal)

        # Should work without error

    def test_find_matching_story_story_without_keywords(self, sample_article):
        """Test find_matching_story handles story with empty keywords."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Match"
        })

        sample_story = Story(
            id="story-no-kw",
            title="Test Story",
            description="Test",
            keywords=[],  # Empty keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [sample_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should still work with LLM comparison
        assert result is not None

    def test_find_matching_story_many_stories(self, sample_article):
        """Test find_matching_story with many stories (near limit)."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True

        # Only the 25th story has high confidence
        call_count = [0]

        def generate_response(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 25:
                return json.dumps({
                    "is_same_story": True,
                    "confidence": 0.95,
                    "reasoning": "Best match"
                })
            return json.dumps({
                "is_same_story": True,
                "confidence": 0.6,  # Below threshold
                "reasoning": "Weak"
            })

        mock_llm_provider.generate.side_effect = generate_response

        # Create 50 stories (at the limit)
        stories = [
            Story(
                id=f"story-{i}",
                title=f"Story {i}",
                description=f"Description {i}",
                keywords=["test"],
                first_seen=datetime.now() - timedelta(days=i),
                last_updated=datetime.now() - timedelta(hours=i),
                lifecycle_state="developing",
                article_ids=[f"article-{i}"],
                news_item_ids=[],
            )
            for i in range(50)
        ]

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = stories

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should find story-24 (the 25th story with 0.95 confidence)
        assert result is not None
        assert result.id == "story-24"

    def test_find_matching_story_single_story(self, sample_article):
        """Test find_matching_story with only one story."""
        mock_llm_provider = MagicMock(spec=LLMProvider)
        mock_llm_provider.is_available.return_value = True
        mock_llm_provider.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Match"
        })

        single_story = Story(
            id="only-story",
            title="Only Story",
            description="The only story",
            keywords=["only"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["article-only"],
            news_item_ids=[],
        )

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [single_story]

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        assert result is not None
        assert result.id == "only-story"


@pytest.mark.skip(reason="Matching now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestFindMatchingStoryIntegration:
    """Integration tests for find_matching_story with full setup."""

    def test_find_matching_story_full_integration(
        self, full_clustering_setup, sample_article
    ):
        """Test find_matching_story with full clustering environment."""
        clusterer = full_clustering_setup["clusterer"]

        # Initially no stories
        result = clusterer.find_matching_story(sample_article)
        assert result is None

    def test_find_matching_story_after_clustering(
        self, full_clustering_setup, sample_article, sample_article_tech
    ):
        """Test find_matching_story after clustering an article."""
        clusterer = full_clustering_setup["clusterer"]
        llm = full_clustering_setup["llm_provider"]

        # First, cluster an article to create a story
        story = clusterer.cluster_article(sample_article)
        assert story is not None

        # Now configure LLM to match the second article
        llm.generate.side_effect = lambda prompt, max_tokens=None: (
            json.dumps({
                "is_same_story": True,
                "confidence": 0.9,
                "reasoning": "Related tech articles"
            })
        )

        # Try to find matching story for similar article
        result = clusterer.find_matching_story(sample_article_tech)

        # Should find the story we just created
        assert result is not None
        assert result.id == story.id

    def test_find_matching_story_clustering_with_data(
        self, clustering_with_data
    ):
        """Test find_matching_story with pre-populated clustering environment."""
        clusterer = clustering_with_data["clusterer"]
        storage = clustering_with_data["storage"]

        # Get an article
        articles = storage.get_articles(limit=1)
        if articles:
            article = articles[0]

            # Before any stories exist
            result = clusterer.find_matching_story(article)
            assert result is None  # No stories yet


# =============================================================================
# Tests for _calculate_similarity
# =============================================================================


@pytest.mark.skip(reason="Similarity now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestCalculateSimilarityBasic:
    """Basic tests for _calculate_similarity method - DEPRECATED."""

    def test_calculate_similarity_returns_float(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that _calculate_similarity returns a float."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert isinstance(result, float)

    def test_calculate_similarity_high_confidence_same_story(
        self, sample_article, sample_story
    ):
        """Test _calculate_similarity with high confidence same story response."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.95,
            "reasoning": "Same topic"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert result == 0.95

    def test_calculate_similarity_low_confidence_same_story(
        self, sample_article, sample_story
    ):
        """Test _calculate_similarity with low confidence same story response."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.5,
            "reasoning": "Some overlap"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert result == 0.5

    def test_calculate_similarity_not_same_story_returns_zero(
        self, sample_article, sample_story
    ):
        """Test _calculate_similarity returns 0 when not same story."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": False,
            "confidence": 0.9,  # High confidence it's NOT the same
            "reasoning": "Different topics"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._calculate_similarity(sample_article, sample_story)

        # is_same_story=False means score is 0 regardless of confidence
        assert result == 0.0

    def test_calculate_similarity_calls_generate_with_prompt(
        self, sample_article, sample_story
    ):
        """Test that _calculate_similarity calls generate with a prompt."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Test"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)
        clusterer._calculate_similarity(sample_article, sample_story)

        # Verify generate was called with a prompt and max_tokens
        mock_llm.generate.assert_called_once()
        call_args = mock_llm.generate.call_args
        assert call_args[0][0]  # Prompt is not empty
        assert call_args[1].get("max_tokens") == 200

    def test_calculate_similarity_zero_confidence(
        self, sample_article, sample_story
    ):
        """Test _calculate_similarity with zero confidence."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.0,
            "reasoning": "No confidence"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert result == 0.0

    def test_calculate_similarity_full_confidence(
        self, sample_article, sample_story
    ):
        """Test _calculate_similarity with full (1.0) confidence."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 1.0,
            "reasoning": "Perfect match"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert result == 1.0


@pytest.mark.skip(reason="Similarity now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestCalculateSimilarityWithFallback:
    """Tests for _calculate_similarity fallback to keyword similarity."""

    def test_calculate_similarity_llm_error_falls_back_to_keywords(
        self, sample_article, sample_story
    ):
        """Test that LLM errors trigger keyword-based fallback."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = Exception("LLM error")

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        # Should not raise, should use fallback
        result = clusterer._calculate_similarity(sample_article, sample_story)

        # Result should be a float from keyword similarity
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_calculate_similarity_llm_timeout_falls_back(
        self, sample_article, sample_story
    ):
        """Test that LLM timeout triggers keyword-based fallback."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = TimeoutError("Request timed out")

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_calculate_similarity_runtime_error_falls_back(
        self, sample_article, sample_story
    ):
        """Test that RuntimeError triggers keyword-based fallback."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = RuntimeError("Provider unavailable")

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_calculate_similarity_fallback_with_matching_keywords(self):
        """Test fallback produces high score when keywords match."""
        # Create article with content containing story keywords
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI Technology Breaking News",
            link="https://example.com/article",
            published=datetime.now(),
            content="This article discusses AI and technology advancements in machine learning.",
            summary=None,
        )

        # Story with keywords that appear in article
        story = Story(
            id="test-story",
            title="AI Technology",
            description="About AI",
            keywords=["AI", "technology", "machine learning"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = Exception("LLM error")

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(article, story)

        # All 3 keywords should match - ai, technology, machine learning
        assert result > 0.5  # Should have high similarity

    def test_calculate_similarity_fallback_with_no_matching_keywords(self):
        """Test fallback produces low score when keywords don't match."""
        # Create article with unrelated content
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="Sports News",
            link="https://example.com/article",
            published=datetime.now(),
            content="Football game results and basketball scores.",
            summary=None,
        )

        # Story with completely different keywords
        story = Story(
            id="test-story",
            title="AI Technology",
            description="About AI",
            keywords=["AI", "technology", "machine learning"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = Exception("LLM error")

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(article, story)

        # No keywords should match
        assert result == 0.0


@pytest.mark.skip(reason="Similarity now uses embeddings, not LLM calls. See test_embeddings.py for new tests.")
class TestCalculateSimilarityEdgeCases:
    """Edge case tests for _calculate_similarity - DEPRECATED."""

    def test_calculate_similarity_with_unicode_content(self, sample_story):
        """Test _calculate_similarity handles unicode content."""
        article = Article(
            id="unicode-article",
            feed_url="https://example.com/feed.xml",
            title="Unicode Test: Café 中文 🚀",
            link="https://example.com/article",
            published=datetime.now(),
            content="This article contains unicode: 中文测试, 日本語, 😀👍🎉",
            summary=None,
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.8,
            "reasoning": "Unicode test"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        # Should not raise
        result = clusterer._calculate_similarity(article, sample_story)
        assert result == 0.8

    def test_calculate_similarity_with_very_long_content(self, sample_story):
        """Test _calculate_similarity handles very long content (truncated in prompt)."""
        article = Article(
            id="long-article",
            feed_url="https://example.com/feed.xml",
            title="Long Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="Very long content. " * 1000,  # Very long
            summary=None,
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Match"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(article, sample_story)
        assert result == 0.85

        # Verify content was truncated in prompt
        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0]
        # Content in prompt should be truncated at 500 chars
        assert len(prompt) < len(article.content)

    def test_calculate_similarity_with_empty_article_content(self, sample_story):
        """Test _calculate_similarity handles empty article content."""
        article = Article(
            id="empty-article",
            feed_url="https://example.com/feed.xml",
            title="Empty Content Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="",
            summary=None,
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.7,
            "reasoning": "Based on title"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(article, sample_story)
        assert result == 0.7

    def test_calculate_similarity_with_story_no_keywords(self, sample_article):
        """Test _calculate_similarity handles story with no keywords."""
        story = Story(
            id="no-keyword-story",
            title="Story Without Keywords",
            description="No keywords",
            keywords=[],  # Empty keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.8,
            "reasoning": "Match"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(sample_article, story)
        assert result == 0.8

    def test_calculate_similarity_with_story_many_keywords(self, sample_article):
        """Test _calculate_similarity handles story with many keywords (truncated)."""
        story = Story(
            id="many-keyword-story",
            title="Story With Many Keywords",
            description="Lots of keywords",
            keywords=[f"keyword{i}" for i in range(50)],  # Many keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=["old-article"],
            news_item_ids=[],
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Match"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(sample_article, story)
        assert result == 0.85

        # Verify only first 10 keywords were used in prompt
        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0]
        # Should only see first 10 keywords
        assert "keyword0" in prompt
        assert "keyword9" in prompt
        # keyword10 and beyond should NOT be in prompt
        assert "keyword10" not in prompt

    def test_calculate_similarity_with_special_characters(self, sample_story):
        """Test _calculate_similarity handles special characters in content."""
        article = Article(
            id="special-chars-article",
            feed_url="https://example.com/feed.xml",
            title='Article with "quotes" & <special> chars',
            link="https://example.com/article",
            published=datetime.now(),
            content='Content with "quotes", <brackets>, & ampersands. Plus $dollar$ and @at@ signs.',
            summary=None,
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.75,
            "reasoning": "Test"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(article, sample_story)
        assert result == 0.7


# =============================================================================
# Tests for _keyword_similarity
# =============================================================================


class TestKeywordSimilarityBasic:
    """Basic tests for _keyword_similarity method."""

    def test_keyword_similarity_returns_float(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that _keyword_similarity returns a float."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(sample_article, sample_story)

        assert isinstance(result, float)

    def test_keyword_similarity_range(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that _keyword_similarity returns value between 0 and 1."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(sample_article, sample_story)

        assert 0.0 <= result <= 1.0

    def test_keyword_similarity_all_keywords_match(self, mock_llm_provider, mock_storage):
        """Test _keyword_similarity when all keywords match."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI Technology Machine Learning",
            link="https://example.com/article",
            published=datetime.now(),
            content="AI technology machine learning article content.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="AI Story",
            description="About AI",
            keywords=["ai", "technology", "machine"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # All 3 keywords should match
        assert result == 1.0

    def test_keyword_similarity_no_keywords_match(self, mock_llm_provider, mock_storage):
        """Test _keyword_similarity when no keywords match."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="Sports News",
            link="https://example.com/article",
            published=datetime.now(),
            content="Football and basketball news.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["ai", "technology", "machine"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # No keywords should match
        assert result == 0.0

    def test_keyword_similarity_partial_match(self, mock_llm_provider, mock_storage):
        """Test _keyword_similarity when some keywords match."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI News",
            link="https://example.com/article",
            published=datetime.now(),
            content="AI article about technology.",  # 2 of 4 keywords
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["ai", "technology", "machine", "learning"],  # 4 keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # 2 of 4 keywords match = 0.5
        assert result == 0.5

    def test_keyword_similarity_empty_story_keywords(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test _keyword_similarity returns 0 when story has no keywords."""
        story = Story(
            id="test-story",
            title="Story",
            description="Description",
            keywords=[],  # Empty keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(sample_article, story)

        # Empty keywords should return 0
        assert result == 0.0


class TestKeywordSimilarityCaseSensitivity:
    """Tests for _keyword_similarity case sensitivity."""

    def test_keyword_similarity_case_insensitive(self, mock_llm_provider, mock_storage):
        """Test that keyword matching is case insensitive."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI TECHNOLOGY",
            link="https://example.com/article",
            published=datetime.now(),
            content="Discussing AI Technology advances.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["ai", "technology"],  # lowercase
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # Should match despite case difference
        assert result == 1.0

    def test_keyword_similarity_mixed_case_keywords(self, mock_llm_provider, mock_storage):
        """Test matching when story keywords have mixed case."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="machine learning article",
            link="https://example.com/article",
            published=datetime.now(),
            content="machine learning and neural networks",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["Machine", "Learning", "Neural"],  # Mixed case
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # All 3 keywords should match (case insensitive)
        assert result == 1.0


class TestKeywordSimilaritySearchBehavior:
    """Tests for _keyword_similarity substring matching behavior."""

    def test_keyword_similarity_substring_in_word(self, mock_llm_provider, mock_storage):
        """Test that keywords match as substrings within words."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="Testing Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="This is about technologies and intelligence systems.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["tech", "intel"],  # 'tech' is in 'technologies', 'intel' in 'intelligence'
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # Both should match as substrings
        assert result == 1.0

    def test_keyword_similarity_title_and_content_combined(
        self, mock_llm_provider, mock_storage
    ):
        """Test that keywords are matched against title + content combined."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI Development",  # 'ai' in title
            link="https://example.com/article",
            published=datetime.now(),
            content="This discusses technology advances.",  # 'technology' in content
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["ai", "technology"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # Both keywords should match (one from title, one from content)
        assert result == 1.0


class TestKeywordSimilarityEdgeCases:
    """Edge case tests for _keyword_similarity."""

    def test_keyword_similarity_empty_article_content(
        self, mock_llm_provider, mock_storage
    ):
        """Test _keyword_similarity with empty article content."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI Article",  # Only title
            link="https://example.com/article",
            published=datetime.now(),
            content="",  # Empty content
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["ai"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # Should still match from title
        assert result == 1.0

    def test_keyword_similarity_empty_article_title(
        self, mock_llm_provider, mock_storage
    ):
        """Test _keyword_similarity with empty article title."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="",  # Empty title
            link="https://example.com/article",
            published=datetime.now(),
            content="AI technology content here.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["ai", "technology"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # Should match from content
        assert result == 1.0

    def test_keyword_similarity_both_empty(self, mock_llm_provider, mock_storage):
        """Test _keyword_similarity with both title and content empty."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="",
            link="https://example.com/article",
            published=datetime.now(),
            content="",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Tech Story",
            description="About tech",
            keywords=["ai", "technology"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # No matches possible
        assert result == 0.0

    def test_keyword_similarity_single_keyword_match(
        self, mock_llm_provider, mock_storage
    ):
        """Test _keyword_similarity with single keyword that matches."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="AI content",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="AI Story",
            description="About AI",
            keywords=["ai"],  # Single keyword
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        assert result == 1.0

    def test_keyword_similarity_unicode_keywords(self, mock_llm_provider, mock_storage):
        """Test _keyword_similarity with unicode keywords."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="中文新闻",
            link="https://example.com/article",
            published=datetime.now(),
            content="This article contains 中文 content and 日本語.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Asian News",
            description="About Asian news",
            keywords=["中文", "日本語", "english"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # 2 of 3 keywords should match (中文 and 日本語)
        assert result == pytest.approx(2/3, rel=0.01)

    def test_keyword_similarity_many_keywords(self, mock_llm_provider, mock_storage):
        """Test _keyword_similarity with many keywords."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="Tech Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="keyword1 keyword2 keyword5 keyword10",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Story",
            description="Description",
            keywords=[f"keyword{i}" for i in range(1, 21)],  # 20 keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # 4 of 20 keywords match = 0.2
        assert result == 0.2

    def test_keyword_similarity_special_chars_in_keywords(
        self, mock_llm_provider, mock_storage
    ):
        """Test _keyword_similarity with special characters in keywords."""
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="C++ and C# Programming",
            link="https://example.com/article",
            published=datetime.now(),
            content="Programming languages like c++ and c# are popular.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="Programming Story",
            description="About programming",
            keywords=["c++", "c#", "python"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._keyword_similarity(article, story)

        # 2 of 3 keywords should match
        assert result == pytest.approx(2/3, rel=0.01)


# =============================================================================
# Tests for LLM-based comparison (_generate_comparison_prompt, _parse_similarity_response)
# =============================================================================


@pytest.mark.skip(reason="Comparison prompts deprecated - similarity now uses embeddings. See test_embeddings.py.")
class TestGenerateComparisonPrompt:
    """Tests for _generate_comparison_prompt method."""

    def test_generate_comparison_prompt_returns_string(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that _generate_comparison_prompt returns a string."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, sample_story)

        assert isinstance(result, str)

    def test_generate_comparison_prompt_contains_article_title(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that prompt contains article title."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, sample_story)

        assert sample_article.title in result

    def test_generate_comparison_prompt_contains_story_title(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that prompt contains story title."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, sample_story)

        assert sample_story.title in result

    def test_generate_comparison_prompt_contains_story_description(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that prompt contains story description."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, sample_story)

        assert sample_story.description in result

    def test_generate_comparison_prompt_contains_keywords(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that prompt contains story keywords."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, sample_story)

        # Should contain at least some keywords
        for keyword in sample_story.keywords[:3]:
            assert keyword in result

    def test_generate_comparison_prompt_truncates_content(
        self, mock_llm_provider, mock_storage, sample_story
    ):
        """Test that prompt truncates very long content."""
        article = Article(
            id="long-article",
            feed_url="https://example.com/feed.xml",
            title="Long Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="X" * 1000,  # 1000 characters
            summary=None,
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(article, sample_story)

        # Content should be truncated at 500 chars
        assert "X" * 500 in result
        assert "X" * 501 not in result

    def test_generate_comparison_prompt_truncates_keywords(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that prompt only includes first 10 keywords."""
        story = Story(
            id="many-keywords-story",
            title="Story",
            description="Description",
            keywords=[f"keyword{i}" for i in range(20)],  # 20 keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, story)

        # Should contain first 10 keywords
        assert "keyword0" in result
        assert "keyword9" in result
        # Should NOT contain keyword10 and beyond
        assert "keyword10" not in result

    def test_generate_comparison_prompt_contains_json_format(
        self, mock_llm_provider, mock_storage, sample_article, sample_story
    ):
        """Test that prompt contains expected JSON format."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, sample_story)

        assert "is_same_story" in result
        assert "confidence" in result
        assert "reasoning" in result

    def test_generate_comparison_prompt_with_empty_story_keywords(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test prompt generation with story that has no keywords."""
        story = Story(
            id="no-keywords-story",
            title="Story",
            description="Description",
            keywords=[],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_comparison_prompt(sample_article, story)

        # Should still work
        assert isinstance(result, str)
        assert "Keywords:" in result


@pytest.mark.skip(reason="Response parsing deprecated - similarity now uses embeddings. See test_embeddings.py.")
class TestParseSimilarityResponse:
    """Tests for _parse_similarity_response method."""

    def test_parse_similarity_response_valid_json(
        self, mock_llm_provider, mock_storage
    ):
        """Test parsing valid JSON response."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Same topic"
        })

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is True
        assert result["confidence"] == 0.85
        assert result["reasoning"] == "Same topic"

    def test_parse_similarity_response_json_with_surrounding_text(
        self, mock_llm_provider, mock_storage
    ):
        """Test parsing JSON embedded in surrounding text."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = '''Here's my analysis:
        {"is_same_story": true, "confidence": 0.9, "reasoning": "Match"}
        Hope that helps!'''

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is True
        assert result["confidence"] == 0.9

    def test_parse_similarity_response_invalid_json_with_true(
        self, mock_llm_provider, mock_storage
    ):
        """Test fallback parsing when response contains 'true'."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = "Yes, these articles are about the same topic. It's true they're related."

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is True
        assert result["confidence"] == 0.7

    def test_parse_similarity_response_invalid_json_with_yes(
        self, mock_llm_provider, mock_storage
    ):
        """Test fallback parsing when response contains 'yes'."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = "Yes, definitely the same story."

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is True
        assert result["confidence"] == 0.7

    def test_parse_similarity_response_invalid_json_with_same(
        self, mock_llm_provider, mock_storage
    ):
        """Test fallback parsing when response contains 'same'."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = "These appear to be the same story about the topic."

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is True
        assert result["confidence"] == 0.7

    def test_parse_similarity_response_invalid_json_negative(
        self, mock_llm_provider, mock_storage
    ):
        """Test fallback parsing when response indicates no match."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = "No, these articles discuss completely different topics."

        result = clusterer._parse_similarity_response(response)

        # Doesn't contain 'true', 'yes', or 'same'
        assert result["is_same_story"] is False
        assert result["confidence"] == 0.3

    def test_parse_similarity_response_empty_string(
        self, mock_llm_provider, mock_storage
    ):
        """Test parsing empty string response."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = ""

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is False
        assert result["confidence"] == 0.3

    def test_parse_similarity_response_malformed_json(
        self, mock_llm_provider, mock_storage
    ):
        """Test parsing malformed JSON response."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = '{"is_same_story": true, "confidence": '  # Incomplete JSON

        result = clusterer._parse_similarity_response(response)

        # Should use fallback (contains 'true')
        assert result["is_same_story"] is True
        assert result["confidence"] == 0.7

    def test_parse_similarity_response_json_missing_fields(
        self, mock_llm_provider, mock_storage
    ):
        """Test parsing JSON with missing fields."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = '{"is_same_story": true}'  # Missing confidence

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is True
        # confidence should be missing from result
        assert "confidence" not in result or result.get("confidence") is None

    def test_parse_similarity_response_case_insensitive_keywords(
        self, mock_llm_provider, mock_storage
    ):
        """Test that fallback keyword matching is case insensitive."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = "YES, they are the SAME story."

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is True
        assert result["confidence"] == 0.7

    def test_parse_similarity_response_json_false(
        self, mock_llm_provider, mock_storage
    ):
        """Test parsing JSON with is_same_story=false."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        response = json.dumps({
            "is_same_story": False,
            "confidence": 0.2,
            "reasoning": "Different"
        })

        result = clusterer._parse_similarity_response(response)

        assert result["is_same_story"] is False
        assert result["confidence"] == 0.2


@pytest.mark.skip(reason="LLM comparison deprecated - similarity now uses embeddings. See test_embeddings.py.")
class TestLLMComparisonIntegration:
    """Integration tests for LLM-based comparison flow."""

    def test_comparison_flow_high_confidence_match(
        self, sample_article, sample_story
    ):
        """Test full comparison flow with high confidence match."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.95,
            "reasoning": "Perfect match"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        # Full flow: generate prompt, call LLM, parse response, return score
        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert result == 0.95
        mock_llm.generate.assert_called_once()

    def test_comparison_flow_low_confidence_no_match(
        self, sample_article, sample_story
    ):
        """Test full comparison flow with low confidence."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.4,
            "reasoning": "Weak match"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(sample_article, sample_story)

        assert result == 0.4

    def test_comparison_flow_different_story(
        self, sample_article, sample_story
    ):
        """Test full comparison flow when not same story."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": False,
            "confidence": 0.9,
            "reasoning": "Different topics"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(sample_article, sample_story)

        # is_same_story=False means score is 0
        assert result == 0.0

    def test_comparison_flow_llm_returns_text(
        self, sample_article, sample_story
    ):
        """Test comparison flow when LLM returns text instead of JSON."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "Yes, I believe these are the same story."

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(sample_article, sample_story)

        # Fallback parser should detect 'yes' and return is_same_story=True with 0.7 confidence
        assert result == 0.7

    def test_comparison_flow_llm_error_keyword_fallback(self):
        """Test comparison flow when LLM errors and keyword fallback is used."""
        # Article with keywords matching story
        article = Article(
            id="test-article",
            feed_url="https://example.com/feed.xml",
            title="AI Technology News",
            link="https://example.com/article",
            published=datetime.now(),
            content="AI and technology advances in machine learning.",
            summary=None,
        )

        story = Story(
            id="test-story",
            title="AI Story",
            description="About AI",
            keywords=["ai", "technology", "machine"],  # 3 keywords
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = Exception("LLM unavailable")

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        result = clusterer._calculate_similarity(article, story)

        # Should fall back to keyword similarity
        # All 3 keywords match = 1.0
        assert result == 1.0

    def test_comparison_uses_generate_not_summarize(
        self, sample_article, sample_story
    ):
        """Test that comparison uses generate() not summarize()."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Test"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        clusterer._calculate_similarity(sample_article, sample_story)

        # Verify generate was called, not summarize
        mock_llm.generate.assert_called_once()
        mock_llm.summarize.assert_not_called()

    def test_comparison_passes_max_tokens(
        self, sample_article, sample_story
    ):
        """Test that comparison passes max_tokens to generate()."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.85,
            "reasoning": "Test"
        })

        mock_storage = MagicMock(spec=Storage)
        clusterer = StoryClusterer(mock_llm, mock_storage)

        clusterer._calculate_similarity(sample_article, sample_story)

        # Verify max_tokens was passed
        call_args = mock_llm.generate.call_args
        assert call_args[1].get("max_tokens") == 200


@pytest.mark.skip(reason="LLM similarity deprecated - similarity now uses embeddings. See test_embeddings.py.")
class TestSimilarityCalculationIntegration:
    """Integration tests combining similarity calculation with find_matching_story."""

    def test_similarity_calculation_affects_matching(
        self, sample_article
    ):
        """Test that similarity calculation directly affects story matching."""
        # Create two stories - one should match better than the other
        story1 = Story(
            id="story-1",
            title="Unrelated Story",
            description="About something else",
            keywords=["sports", "games"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        story2 = Story(
            id="story-2",
            title="Tech News Story",
            description="About technology",
            keywords=["tech", "AI", "company"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        call_count = [0]

        def generate_response(*args, **kwargs):
            call_count[0] += 1
            # Story 1 gets low score, Story 2 gets high score
            if call_count[0] == 1:
                return json.dumps({
                    "is_same_story": True,
                    "confidence": 0.3,  # Low
                    "reasoning": "Weak match"
                })
            else:
                return json.dumps({
                    "is_same_story": True,
                    "confidence": 0.9,  # High
                    "reasoning": "Strong match"
                })

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = generate_response

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [story1, story2]

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should select story-2 with higher similarity
        assert result is not None
        assert result.id == "story-2"

    def test_threshold_boundary_with_similarity(self, sample_article):
        """Test threshold boundary behavior with similarity calculation."""
        story = Story(
            id="story-1",
            title="Story",
            description="Description",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        # Just below threshold
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.74,  # Just below 0.75 threshold
            "reasoning": "Close"
        })

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [story]

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should NOT match (0.74 < 0.75)
        assert result is None

    def test_threshold_exact_boundary(self, sample_article):
        """Test exact threshold boundary."""
        story = Story(
            id="story-1",
            title="Story",
            description="Description",
            keywords=["test"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now(),
            lifecycle_state="developing",
            article_ids=[],
            news_item_ids=[],
        )

        # Exactly at threshold
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = json.dumps({
            "is_same_story": True,
            "confidence": 0.75,  # Exactly at threshold
            "reasoning": "Exact"
        })

        mock_storage = MagicMock(spec=Storage)
        mock_storage.get_active_stories.return_value = [story]

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.find_matching_story(sample_article)

        # Should match (0.75 >= 0.75)
        assert result is not None
        assert result.id == "story-1"


