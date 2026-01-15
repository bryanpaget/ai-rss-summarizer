"""Tests for clustering module."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import MagicMock, patch, Mock

import pytest

from src.clustering import (
    StoryClusterer,
    NewsItemExtractor,
    StoryEvolutionTracker,
    process_article_clustering,
    batch_process_articles,
)
from src.storage import Storage, Article, Story, NewsItem
from src.llm_providers import LLMProvider


# =============================================================================
# Autouse fixture to prevent network calls to embedding providers
# =============================================================================


@pytest.fixture(autouse=True)
def mock_embedding_providers():
    """Automatically mock embedding providers to prevent network calls.

    This fixture is autouse=True, meaning it runs for every test in this module.
    This prevents tests from trying to connect to LM Studio or Ollama.
    """
    with patch('src.embeddings.EmbeddingProviderManager') as mock_manager_class:
        mock_manager = MagicMock()
        mock_provider = MagicMock()
        mock_provider.embed.return_value = [0.5] * 256
        mock_provider.embed_batch.return_value = [[0.5] * 256]
        mock_provider.model_name = "mock-model"
        mock_provider.name = "MockProvider"
        mock_manager.get_provider.return_value = mock_provider
        mock_manager.list_available.return_value = ["mock"]
        mock_manager_class.return_value = mock_manager
        yield mock_manager_class


# =============================================================================
# Fixtures for Temporary Files and Directories
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database path."""
    return os.path.join(temp_dir, "articles.db")


# =============================================================================
# Fixtures for Storage
# =============================================================================


@pytest.fixture
def storage(temp_db):
    """Create a Storage instance with temp database."""
    return Storage(temp_db)


@pytest.fixture
def storage_empty(temp_db):
    """Create an empty Storage instance."""
    return Storage(temp_db)


@pytest.fixture
def storage_with_articles(temp_db):
    """Create a Storage instance pre-populated with sample articles."""
    store = Storage(temp_db)
    articles = [
        Article(
            id=f"article-{i}",
            feed_url="https://example.com/feed.xml",
            title=f"Test Article {i}",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of test article {i}. This is some test content. " * 10,
            summary=f"Summary of article {i}." if i % 2 == 0 else None,
            trend_tags="AI & Technology" if i % 3 == 0 else "Business & Economy",
        )
        for i in range(10)
    ]
    for article in articles:
        store.save_article(article)
    return store


@pytest.fixture
def storage_with_stories(temp_db):
    """Create a Storage instance pre-populated with stories."""
    store = Storage(temp_db)

    # Create sample stories
    stories = [
        Story(
            id=f"story-{i}",
            title=f"Test Story {i}",
            description=f"Description of test story {i}",
            keywords=["tech", "AI", "innovation"] if i % 2 == 0 else ["business", "economy", "finance"],
            first_seen=datetime.now() - timedelta(days=i),
            last_updated=datetime.now() - timedelta(hours=i * 2),
            lifecycle_state="emerging" if i < 2 else "developing" if i < 4 else "peaked",
            article_ids=[f"article-{i}-{j}" for j in range(3)],
            news_item_ids=[],
        )
        for i in range(5)
    ]
    for story in stories:
        store.save_story(story)
    return store


@pytest.fixture
def storage_with_articles_and_stories(temp_db):
    """Create a Storage instance with both articles and stories."""
    store = Storage(temp_db)

    # Create articles
    articles = [
        Article(
            id=f"article-{i}",
            feed_url="https://example.com/feed.xml",
            title=f"Test Article {i}",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of test article {i}. " * 20,
            summary=f"Summary of article {i}." if i % 2 == 0 else None,
            story_id=f"story-{i // 3}" if i < 9 else None,
        )
        for i in range(10)
    ]
    for article in articles:
        store.save_article(article)

    # Create stories
    stories = [
        Story(
            id=f"story-{i}",
            title=f"Test Story {i}",
            description=f"Description of test story {i}",
            keywords=["tech", "AI", "innovation"],
            first_seen=datetime.now() - timedelta(days=i),
            last_updated=datetime.now() - timedelta(hours=i * 2),
            lifecycle_state="emerging" if i < 2 else "developing",
            article_ids=[f"article-{i * 3}", f"article-{i * 3 + 1}", f"article-{i * 3 + 2}"],
            news_item_ids=[],
        )
        for i in range(3)
    ]
    for story in stories:
        store.save_story(story)

    return store


# =============================================================================
# Fixtures for Mock Storage
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock Storage object with common methods."""
    storage = MagicMock(spec=Storage)
    storage.get_articles.return_value = []
    storage.get_article.return_value = None
    storage.save_article.return_value = True
    storage.get_active_stories.return_value = []
    storage.get_all_stories.return_value = []
    storage.save_story.return_value = None
    storage.update_story.return_value = None
    storage.update_article_story.return_value = None
    storage.get_news_items.return_value = []
    storage.save_news_item.return_value = None
    storage.update_news_item.return_value = None
    return storage


@pytest.fixture
def mock_storage_with_stories():
    """Create a mock Storage with pre-populated stories."""
    storage = MagicMock(spec=Storage)

    sample_stories = [
        MagicMock(
            id=f"story-{i}",
            title=f"Test Story {i}",
            description=f"Description of story {i}",
            keywords=["tech", "AI", "innovation"] if i % 2 == 0 else ["business", "economy"],
            first_seen=datetime.now() - timedelta(days=i),
            last_updated=datetime.now() - timedelta(hours=i * 2),
            lifecycle_state="emerging" if i < 2 else "developing",
            article_ids=[f"article-{i}-{j}" for j in range(3)],
            news_item_ids=[],
        )
        for i in range(5)
    ]

    storage.get_active_stories.return_value = sample_stories
    storage.get_all_stories.return_value = sample_stories
    storage.get_articles.return_value = []
    storage.save_story.return_value = None
    storage.update_story.return_value = None
    storage.update_article_story.return_value = None

    return storage


@pytest.fixture
def mock_storage_with_news_items():
    """Create a mock Storage with pre-populated news items."""
    storage = MagicMock(spec=Storage)

    sample_news_items = [
        NewsItem(
            id=f"news-item-{i}",
            story_id="story-1",
            title=f"News Item {i}",
            description=f"Description of news item {i}",
            first_reported_by="https://example.com/feed.xml",
            first_seen=datetime.now() - timedelta(hours=i),
            article_ids=[f"article-{i}"],
            item_type="new_info" if i % 2 == 0 else "analysis",
            confidence=0.9 - (i * 0.1),
        )
        for i in range(5)
    ]

    storage.get_news_items.return_value = sample_news_items
    storage.save_news_item.return_value = None
    storage.update_news_item.return_value = None
    storage.get_active_stories.return_value = []

    return storage


# =============================================================================
# Fixtures for Sample Articles
# =============================================================================


@pytest.fixture
def sample_article():
    """Create a sample article for testing."""
    return Article(
        id="article-test-1",
        feed_url="https://example.com/feed.xml",
        title="Breaking: Major Tech Company Announces New AI Product",
        link="https://example.com/article-1",
        published=datetime.now(),
        content="A major technology company has announced a groundbreaking new AI product. "
                "The product uses advanced machine learning techniques to solve complex problems. "
                "Industry experts are calling it a significant advancement in artificial intelligence. "
                "The company plans to release the product next quarter.",
        summary="Major tech company announces new AI product launch.",
    )


@pytest.fixture
def sample_article_tech():
    """Create a tech-focused sample article."""
    return Article(
        id="article-tech-1",
        feed_url="https://techblog.example.com/feed.xml",
        title="AI Breakthrough: Neural Networks Achieve Human-Level Performance",
        link="https://techblog.example.com/article-1",
        published=datetime.now() - timedelta(hours=2),
        content="Researchers have achieved a breakthrough in neural network technology. "
                "The new architecture demonstrates human-level performance on complex tasks. "
                "This development could have implications for healthcare, finance, and more.",
        summary="Neural networks achieve human-level performance.",
        trend_tags="AI & Technology",
    )


@pytest.fixture
def sample_article_business():
    """Create a business-focused sample article."""
    return Article(
        id="article-business-1",
        feed_url="https://finance.example.com/feed.xml",
        title="Stock Market Hits Record High Amid Economic Optimism",
        link="https://finance.example.com/article-1",
        published=datetime.now() - timedelta(hours=1),
        content="The stock market reached a new all-time high today. "
                "Investors are optimistic about the economic outlook. "
                "Major indices posted gains across all sectors.",
        summary="Stock market hits record high.",
        trend_tags="Business & Economy",
    )


@pytest.fixture
def sample_article_unsummarized():
    """Create an article without a summary."""
    return Article(
        id="article-unsummarized-1",
        feed_url="https://example.com/feed.xml",
        title="New Development in Tech Sector",
        link="https://example.com/article-unsummarized-1",
        published=datetime.now() - timedelta(hours=3),
        content="This is a new development in the technology sector that has not been summarized yet. " * 10,
        summary=None,
    )


@pytest.fixture
def sample_article_no_published():
    """Create an article without a published date."""
    return Article(
        id="article-no-published-1",
        feed_url="https://example.com/feed.xml",
        title="Article Without Published Date",
        link="https://example.com/article-no-published-1",
        published=None,
        content="This is an article without a published date. Content here.",
        summary="Article without date.",
    )


@pytest.fixture
def sample_article_unicode():
    """Create an article with unicode content."""
    return Article(
        id="article-unicode-1",
        feed_url="https://example.com/feed.xml",
        title="Unicode Test: Caf\u00e9 \u4e2d\u6587 \ud83d\ude80",
        link="https://example.com/article-unicode-1",
        published=datetime.now(),
        content="This article contains unicode characters: \u4e2d\u6587\u6d4b\u8bd5, \u65e5\u672c\u8a9e, \ud83d\ude00\ud83d\udc4d\ud83c\udf89",
        summary="Unicode content test.",
    )


@pytest.fixture
def sample_article_special_chars():
    """Create an article with special characters."""
    return Article(
        id="article-special-1",
        feed_url="https://example.com/feed.xml",
        title='Article with "quotes" & <special> chars',
        link="https://example.com/article-special-1",
        published=datetime.now(),
        content='Content with "quotes", <brackets>, & ampersands. Plus $dollar$ and @at@ signs.',
        summary="Special characters test.",
    )


@pytest.fixture
def sample_article_very_long():
    """Create an article with very long content."""
    return Article(
        id="article-long-1",
        feed_url="https://example.com/feed.xml",
        title="Very Long Article for Testing Content Limits",
        link="https://example.com/article-long-1",
        published=datetime.now(),
        content="This is a very long article. " * 500,  # ~5000 words
        summary="Very long article test.",
    )


@pytest.fixture
def sample_article_minimal():
    """Create a minimal article with only required fields."""
    return Article(
        id="article-minimal-1",
        feed_url="https://example.com/feed.xml",
        title="Minimal Article",
        link="https://example.com/article-minimal-1",
        published=None,
        content="",
        summary=None,
    )


@pytest.fixture
def sample_articles_bulk():
    """Create a list of articles for bulk testing."""
    return [
        Article(
            id=f"bulk-article-{i}",
            feed_url="https://example.com/feed.xml",
            title=f"Bulk Test Article {i}",
            link=f"https://example.com/bulk-article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of bulk article {i}. " * 15,
            summary=f"Summary of bulk article {i}." if i % 2 == 0 else None,
        )
        for i in range(20)
    ]


# =============================================================================
# Fixtures for Sample Stories
# =============================================================================


@pytest.fixture
def sample_story():
    """Create a sample story for testing."""
    return Story(
        id="story-test-1",
        title="AI Technology Developments",
        description="Coverage of recent developments in AI technology and machine learning.",
        keywords=["AI", "technology", "machine learning", "neural networks"],
        first_seen=datetime.now() - timedelta(days=2),
        last_updated=datetime.now() - timedelta(hours=1),
        lifecycle_state="developing",
        article_ids=["article-1", "article-2", "article-3"],
        news_item_ids=["news-1", "news-2"],
    )


@pytest.fixture
def sample_story_emerging():
    """Create an emerging story."""
    return Story(
        id="story-emerging-1",
        title="New Startup Launches",
        description="A new startup has just launched with innovative technology.",
        keywords=["startup", "innovation", "technology"],
        first_seen=datetime.now() - timedelta(hours=6),
        last_updated=datetime.now() - timedelta(minutes=30),
        lifecycle_state="emerging",
        article_ids=["article-startup-1"],
        news_item_ids=[],
    )


@pytest.fixture
def sample_story_developing():
    """Create a developing story."""
    return Story(
        id="story-developing-1",
        title="Market Trends Analysis",
        description="Ongoing analysis of market trends and economic indicators.",
        keywords=["market", "economy", "trends", "analysis", "stocks"],
        first_seen=datetime.now() - timedelta(days=3),
        last_updated=datetime.now() - timedelta(hours=2),
        lifecycle_state="developing",
        article_ids=["article-m1", "article-m2", "article-m3", "article-m4", "article-m5"],
        news_item_ids=["news-m1", "news-m2"],
    )


@pytest.fixture
def sample_story_peaked():
    """Create a peaked story."""
    return Story(
        id="story-peaked-1",
        title="Major Conference Coverage",
        description="Coverage of a major tech conference that has concluded.",
        keywords=["conference", "tech", "announcements", "keynote"],
        first_seen=datetime.now() - timedelta(days=7),
        last_updated=datetime.now() - timedelta(days=1),
        lifecycle_state="peaked",
        article_ids=[f"article-conf-{i}" for i in range(15)],
        news_item_ids=[f"news-conf-{i}" for i in range(8)],
    )


@pytest.fixture
def sample_story_declining():
    """Create a declining story."""
    return Story(
        id="story-declining-1",
        title="Old News Event",
        description="An older news event that is no longer actively covered.",
        keywords=["old", "news", "event"],
        first_seen=datetime.now() - timedelta(days=10),
        last_updated=datetime.now() - timedelta(days=3),
        lifecycle_state="declining",
        article_ids=["article-old-1", "article-old-2"],
        news_item_ids=["news-old-1"],
    )


@pytest.fixture
def sample_story_resolved():
    """Create a resolved story."""
    return Story(
        id="story-resolved-1",
        title="Completed Event",
        description="An event that has been fully resolved.",
        keywords=["completed", "resolved", "final"],
        first_seen=datetime.now() - timedelta(days=14),
        last_updated=datetime.now() - timedelta(days=8),
        lifecycle_state="resolved",
        article_ids=["article-resolved-1", "article-resolved-2", "article-resolved-3"],
        news_item_ids=["news-resolved-1"],
    )


@pytest.fixture
def sample_story_no_keywords():
    """Create a story without keywords."""
    return Story(
        id="story-no-keywords-1",
        title="Story Without Keywords",
        description="A story that has no extracted keywords.",
        keywords=[],
        first_seen=datetime.now() - timedelta(hours=12),
        last_updated=datetime.now() - timedelta(hours=6),
        lifecycle_state="emerging",
        article_ids=["article-nk-1"],
        news_item_ids=[],
    )


@pytest.fixture
def sample_stories_active():
    """Create a list of active stories for testing."""
    return [
        Story(
            id=f"active-story-{i}",
            title=f"Active Story {i}",
            description=f"Description of active story {i}",
            keywords=["keyword1", "keyword2", f"keyword{i}"],
            first_seen=datetime.now() - timedelta(days=i),
            last_updated=datetime.now() - timedelta(hours=i),
            lifecycle_state="emerging" if i < 2 else "developing",
            article_ids=[f"article-{i}-{j}" for j in range(i + 1)],
            news_item_ids=[],
        )
        for i in range(10)
    ]


# =============================================================================
# Fixtures for Sample News Items
# =============================================================================


@pytest.fixture
def sample_news_item():
    """Create a sample news item."""
    return NewsItem(
        id="news-item-1",
        story_id="story-1",
        title="New Development Announced",
        description="A significant new development was announced by the company.",
        first_reported_by="https://example.com/feed.xml",
        first_seen=datetime.now() - timedelta(hours=2),
        article_ids=["article-1"],
        item_type="new_info",
        confidence=0.9,
    )


@pytest.fixture
def sample_news_item_recap():
    """Create a recap news item."""
    return NewsItem(
        id="news-item-recap-1",
        story_id="story-1",
        title="Background Context",
        description="Background information about the ongoing situation.",
        first_reported_by="https://example.com/feed.xml",
        first_seen=datetime.now() - timedelta(hours=5),
        article_ids=["article-2"],
        item_type="recap",
        confidence=0.85,
    )


@pytest.fixture
def sample_news_item_analysis():
    """Create an analysis news item."""
    return NewsItem(
        id="news-item-analysis-1",
        story_id="story-1",
        title="Expert Analysis",
        description="Industry experts analyze the implications of the announcement.",
        first_reported_by="https://analysis.example.com/feed.xml",
        first_seen=datetime.now() - timedelta(hours=1),
        article_ids=["article-3"],
        item_type="analysis",
        confidence=0.8,
    )


@pytest.fixture
def sample_news_item_opinion():
    """Create an opinion news item."""
    return NewsItem(
        id="news-item-opinion-1",
        story_id="story-1",
        title="Editorial Perspective",
        description="An editorial perspective on the recent developments.",
        first_reported_by="https://opinion.example.com/feed.xml",
        first_seen=datetime.now() - timedelta(hours=3),
        article_ids=["article-4"],
        item_type="opinion",
        confidence=0.75,
    )


@pytest.fixture
def sample_news_items_bulk():
    """Create a list of news items for bulk testing."""
    return [
        NewsItem(
            id=f"bulk-news-{i}",
            story_id="story-1",
            title=f"Bulk News Item {i}",
            description=f"Description of bulk news item {i}",
            first_reported_by="https://example.com/feed.xml",
            first_seen=datetime.now() - timedelta(hours=i),
            article_ids=[f"article-{i}"],
            item_type=["new_info", "recap", "analysis", "opinion"][i % 4],
            confidence=0.9 - (i * 0.02),
        )
        for i in range(15)
    ]


# =============================================================================
# Fixtures for Mock LLM Provider
# =============================================================================


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider that is available."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    # Default generate response for similarity checking
    provider.generate.return_value = json.dumps({
        "is_same_story": True,
        "confidence": 0.85,
        "reasoning": "Both articles discuss the same topic."
    })

    # Default summarize response
    provider.summarize.return_value = "This is a test summary."

    return provider


@pytest.fixture
def mock_llm_provider_unavailable():
    """Create a mock LLM provider that is unavailable."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = False
    provider.name = "unavailable-provider"
    provider.model = "unavailable-model"
    provider.generate.side_effect = RuntimeError("Provider not available")
    provider.summarize.side_effect = RuntimeError("Provider not available")
    return provider


@pytest.fixture
def mock_llm_provider_error():
    """Create a mock LLM provider that raises errors."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "error-provider"
    provider.model = "error-model"
    provider.generate.side_effect = Exception("LLM generation failed")
    provider.summarize.side_effect = Exception("LLM summarization failed")
    return provider


@pytest.fixture
def mock_llm_provider_not_same_story():
    """Create a mock LLM provider that returns 'not same story'."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    provider.generate.return_value = json.dumps({
        "is_same_story": False,
        "confidence": 0.2,
        "reasoning": "These articles discuss different topics."
    })

    return provider


@pytest.fixture
def mock_llm_provider_high_confidence():
    """Create a mock LLM provider that returns high confidence matches."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    provider.generate.return_value = json.dumps({
        "is_same_story": True,
        "confidence": 0.95,
        "reasoning": "These are clearly about the same story."
    })

    return provider


@pytest.fixture
def mock_llm_provider_low_confidence():
    """Create a mock LLM provider that returns low confidence matches."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    provider.generate.return_value = json.dumps({
        "is_same_story": True,
        "confidence": 0.5,  # Below threshold
        "reasoning": "Some similarities but not certain."
    })

    return provider


@pytest.fixture
def mock_llm_provider_invalid_json():
    """Create a mock LLM provider that returns invalid JSON."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    # Return invalid JSON that should trigger fallback
    provider.generate.return_value = "This is not valid JSON, but yes they are the same story."

    return provider


@pytest.fixture
def mock_llm_provider_with_title():
    """Create a mock LLM provider for story title generation."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    provider.generate.return_value = "AI Technology Breakthrough Announced"

    return provider


@pytest.fixture
def mock_llm_provider_with_keywords():
    """Create a mock LLM provider for keyword extraction."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    # Return comma-separated keywords
    provider.generate.return_value = "AI, technology, machine learning, neural networks, breakthrough"

    return provider


@pytest.fixture
def mock_llm_provider_news_extraction():
    """Create a mock LLM provider for news item extraction."""
    provider = MagicMock(spec=LLMProvider)
    provider.is_available.return_value = True
    provider.name = "mock-provider"
    provider.model = "mock-model"

    provider.generate.return_value = json.dumps([
        {
            "title": "New AI Feature Announced",
            "description": "Company announces new AI feature",
            "type": "new_info",
            "confidence": 0.9
        },
        {
            "title": "Background on Company",
            "description": "Background information about the company",
            "type": "recap",
            "confidence": 0.85
        }
    ])

    return provider


@pytest.fixture
def mock_llm_provider_configurable():
    """Create a configurable mock LLM provider."""
    def _create(responses=None, available=True, error=None):
        provider = MagicMock(spec=LLMProvider)
        provider.is_available.return_value = available
        provider.name = "configurable-provider"
        provider.model = "configurable-model"

        if error:
            provider.generate.side_effect = error
            provider.summarize.side_effect = error
        elif responses:
            provider.generate.side_effect = responses
        else:
            provider.generate.return_value = json.dumps({
                "is_same_story": True,
                "confidence": 0.85,
                "reasoning": "Default response"
            })

        return provider

    return _create


# =============================================================================
# Fixtures for StoryClusterer
# =============================================================================


@pytest.fixture
def mock_kb():
    """Create a mock KnowledgeBase for clustering tests."""
    kb = MagicMock()
    kb.get_embedding.return_value = None
    kb.save_embedding.return_value = True
    kb._connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = []
    return kb


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service for clustering tests."""
    mock_service = MagicMock()
    mock_service.get_embedding.return_value = None
    mock_service.embed_article.return_value = MagicMock(vector=[0.5] * 256)
    mock_service.embed_story.return_value = MagicMock(vector=[0.5] * 256)
    mock_service.save_embedding.return_value = True
    mock_service.cosine_similarity.return_value = 0.8  # Default high similarity
    return mock_service


@pytest.fixture
def story_clusterer(mock_llm_provider, mock_storage, mock_kb, mock_embedding_service):
    """Create a StoryClusterer with mock dependencies."""
    return StoryClusterer(
        mock_llm_provider, mock_storage, mock_kb,
        embedding_service=mock_embedding_service
    )


@pytest.fixture
def story_clusterer_real_storage(mock_llm_provider, storage, mock_kb, mock_embedding_service):
    """Create a StoryClusterer with real storage and mock LLM."""
    return StoryClusterer(
        mock_llm_provider, storage, mock_kb,
        embedding_service=mock_embedding_service
    )


@pytest.fixture
def story_clusterer_with_stories(mock_llm_provider, mock_storage_with_stories, mock_kb, mock_embedding_service):
    """Create a StoryClusterer with mock storage containing stories."""
    return StoryClusterer(
        mock_llm_provider, mock_storage_with_stories, mock_kb,
        embedding_service=mock_embedding_service
    )


@pytest.fixture
def story_clusterer_error_llm(mock_llm_provider_error, mock_storage, mock_kb, mock_embedding_service):
    """Create a StoryClusterer with an error-prone LLM."""
    return StoryClusterer(
        mock_llm_provider_error, mock_storage, mock_kb,
        embedding_service=mock_embedding_service
    )


@pytest.fixture
def story_clusterer_unavailable_llm(mock_llm_provider_unavailable, mock_storage, mock_kb, mock_embedding_service):
    """Create a StoryClusterer with an unavailable LLM."""
    return StoryClusterer(
        mock_llm_provider_unavailable, mock_storage, mock_kb,
        embedding_service=mock_embedding_service
    )


# =============================================================================
# Fixtures for NewsItemExtractor
# =============================================================================


@pytest.fixture
def news_item_extractor(mock_llm_provider_news_extraction, mock_storage):
    """Create a NewsItemExtractor with mock dependencies."""
    return NewsItemExtractor(mock_llm_provider_news_extraction, mock_storage)


@pytest.fixture
def news_item_extractor_real_storage(mock_llm_provider_news_extraction, storage):
    """Create a NewsItemExtractor with real storage and mock LLM."""
    return NewsItemExtractor(mock_llm_provider_news_extraction, storage)


@pytest.fixture
def news_item_extractor_with_items(mock_llm_provider_news_extraction, mock_storage_with_news_items):
    """Create a NewsItemExtractor with mock storage containing news items."""
    return NewsItemExtractor(mock_llm_provider_news_extraction, mock_storage_with_news_items)


@pytest.fixture
def news_item_extractor_error_llm(mock_llm_provider_error, mock_storage):
    """Create a NewsItemExtractor with an error-prone LLM."""
    return NewsItemExtractor(mock_llm_provider_error, mock_storage)


# =============================================================================
# Fixtures for StoryEvolutionTracker
# =============================================================================


@pytest.fixture
def story_evolution_tracker(mock_storage):
    """Create a StoryEvolutionTracker with mock storage."""
    return StoryEvolutionTracker(mock_storage)


@pytest.fixture
def story_evolution_tracker_real_storage(storage):
    """Create a StoryEvolutionTracker with real storage."""
    return StoryEvolutionTracker(storage)


@pytest.fixture
def story_evolution_tracker_with_stories(mock_storage_with_stories):
    """Create a StoryEvolutionTracker with mock storage containing stories."""
    return StoryEvolutionTracker(mock_storage_with_stories)


@pytest.fixture
def story_evolution_tracker_with_articles(storage_with_articles_and_stories):
    """Create a StoryEvolutionTracker with storage containing articles and stories."""
    return StoryEvolutionTracker(storage_with_articles_and_stories)


# =============================================================================
# Fixtures for LLM Response Variations
# =============================================================================


@pytest.fixture
def llm_similarity_response_same_story():
    """LLM response indicating articles are about the same story."""
    return json.dumps({
        "is_same_story": True,
        "confidence": 0.85,
        "reasoning": "Both articles discuss the same event."
    })


@pytest.fixture
def llm_similarity_response_different_story():
    """LLM response indicating articles are about different stories."""
    return json.dumps({
        "is_same_story": False,
        "confidence": 0.2,
        "reasoning": "Articles discuss completely different topics."
    })


@pytest.fixture
def llm_similarity_response_uncertain():
    """LLM response with uncertain confidence."""
    return json.dumps({
        "is_same_story": True,
        "confidence": 0.6,
        "reasoning": "Some overlap but not clearly the same story."
    })


@pytest.fixture
def llm_keywords_response():
    """LLM response for keyword extraction."""
    return "AI, technology, machine learning, innovation, breakthrough"


@pytest.fixture
def llm_news_items_response():
    """LLM response for news item extraction."""
    return json.dumps([
        {
            "title": "New Development",
            "description": "A new development was announced",
            "type": "new_info",
            "confidence": 0.9
        },
        {
            "title": "Background Info",
            "description": "Background context for the story",
            "type": "recap",
            "confidence": 0.8
        },
        {
            "title": "Expert Opinion",
            "description": "Experts weigh in on the development",
            "type": "analysis",
            "confidence": 0.75
        }
    ])


@pytest.fixture
def llm_news_items_response_empty():
    """LLM response with no news items."""
    return json.dumps([])


@pytest.fixture
def llm_response_malformed_json():
    """Malformed JSON response from LLM."""
    return "{ invalid json here }"


@pytest.fixture
def llm_response_text_only():
    """Text-only response from LLM (no JSON)."""
    return "Yes, these articles appear to be about the same story."


# =============================================================================
# Fixtures for Edge Cases
# =============================================================================


@pytest.fixture
def empty_article():
    """Article with empty content."""
    return Article(
        id="empty-article-1",
        feed_url="https://example.com/feed.xml",
        title="Empty Article",
        link="https://example.com/empty-article-1",
        published=datetime.now(),
        content="",
        summary=None,
    )


@pytest.fixture
def article_with_published_string():
    """Article with published date as ISO string."""
    return Article(
        id="article-string-date-1",
        feed_url="https://example.com/feed.xml",
        title="Article with String Date",
        link="https://example.com/article-string-date-1",
        published="2025-01-07T12:00:00Z",  # String instead of datetime
        content="Content here.",
        summary="Summary here.",
    )


@pytest.fixture
def article_with_invalid_published():
    """Article with invalid published date string."""
    return Article(
        id="article-invalid-date-1",
        feed_url="https://example.com/feed.xml",
        title="Article with Invalid Date",
        link="https://example.com/article-invalid-date-1",
        published="not-a-valid-date",  # Invalid date string
        content="Content here.",
        summary="Summary here.",
    )


@pytest.fixture
def story_with_many_articles():
    """Story with many article IDs."""
    return Story(
        id="story-many-articles-1",
        title="Story with Many Articles",
        description="A story that has accumulated many articles.",
        keywords=["popular", "trending", "viral"],
        first_seen=datetime.now() - timedelta(days=5),
        last_updated=datetime.now() - timedelta(hours=1),
        lifecycle_state="developing",
        article_ids=[f"article-{i}" for i in range(50)],
        news_item_ids=[f"news-{i}" for i in range(20)],
    )


@pytest.fixture
def story_with_many_keywords():
    """Story with many keywords."""
    return Story(
        id="story-many-keywords-1",
        title="Story with Many Keywords",
        description="A story with many extracted keywords.",
        keywords=[f"keyword-{i}" for i in range(30)],
        first_seen=datetime.now() - timedelta(days=2),
        last_updated=datetime.now() - timedelta(hours=3),
        lifecycle_state="developing",
        article_ids=["article-1", "article-2"],
        news_item_ids=[],
    )


@pytest.fixture
def similar_articles():
    """Two articles that are clearly about the same story."""
    return [
        Article(
            id="similar-1",
            feed_url="https://example.com/feed.xml",
            title="Company X Announces New Product",
            link="https://example.com/similar-1",
            published=datetime.now() - timedelta(hours=2),
            content="Company X has announced a new product. The product will launch next month.",
            summary="Company X announces new product.",
        ),
        Article(
            id="similar-2",
            feed_url="https://other.example.com/feed.xml",
            title="Company X's New Product Launch Date Revealed",
            link="https://other.example.com/similar-2",
            published=datetime.now() - timedelta(hours=1),
            content="Company X revealed the launch date for their new product. It will be available next month.",
            summary="Company X reveals product launch date.",
        ),
    ]


@pytest.fixture
def dissimilar_articles():
    """Two articles that are clearly about different stories."""
    return [
        Article(
            id="dissimilar-1",
            feed_url="https://tech.example.com/feed.xml",
            title="New AI Technology Breakthrough",
            link="https://tech.example.com/dissimilar-1",
            published=datetime.now() - timedelta(hours=2),
            content="Scientists have achieved a breakthrough in AI technology. Neural networks now perform better.",
            summary="AI breakthrough announced.",
        ),
        Article(
            id="dissimilar-2",
            feed_url="https://sports.example.com/feed.xml",
            title="Local Team Wins Championship",
            link="https://sports.example.com/dissimilar-2",
            published=datetime.now() - timedelta(hours=1),
            content="The local basketball team won the championship game. Fans celebrated in the streets.",
            summary="Team wins championship.",
        ),
    ]


# =============================================================================
# Fixtures for Integration Testing
# =============================================================================


@pytest.fixture
def full_clustering_setup(temp_db):
    """Set up a complete clustering environment for integration testing."""
    storage = Storage(temp_db)
    llm_provider = MagicMock(spec=LLMProvider)
    llm_provider.is_available.return_value = True
    llm_provider.name = "test-provider"
    llm_provider.model = "test-model"

    # Configure LLM responses for different operations
    def generate_side_effect(prompt, max_tokens=None):
        if "Compare this article" in prompt:
            return json.dumps({
                "is_same_story": False,
                "confidence": 0.2,
                "reasoning": "Different topics"
            })
        elif "Generate a concise story title" in prompt:
            return "Generated Story Title"
        elif "Describe what this story is about" in prompt:
            return "Generated story description."
        elif "Extract" in prompt and "key terms" in prompt:
            return "keyword1, keyword2, keyword3"
        elif "Extract new information" in prompt:
            return json.dumps([{
                "title": "New Info",
                "description": "Description",
                "type": "new_info",
                "confidence": 0.85
            }])
        else:
            return "Default response"

    llm_provider.generate.side_effect = generate_side_effect

    return {
        "storage": storage,
        "llm_provider": llm_provider,
        "clusterer": StoryClusterer(llm_provider, storage),
        "extractor": NewsItemExtractor(llm_provider, storage),
        "tracker": StoryEvolutionTracker(storage),
    }


@pytest.fixture
def clustering_with_data(full_clustering_setup, sample_articles_bulk):
    """Full clustering setup with pre-populated articles."""
    storage = full_clustering_setup["storage"]

    for article in sample_articles_bulk:
        storage.save_article(article)

    return full_clustering_setup


# =============================================================================
# Fixtures for Process Functions
# =============================================================================


@pytest.fixture
def mock_process_dependencies():
    """Mock dependencies for process_article_clustering and batch_process_articles."""
    with patch('src.clustering.StoryClusterer') as mock_clusterer_class, \
         patch('src.clustering.NewsItemExtractor') as mock_extractor_class:

        mock_clusterer = MagicMock()
        mock_extractor = MagicMock()

        mock_story = MagicMock()
        mock_story.id = "test-story-1"
        mock_story.article_ids = ["test-article-1"]

        mock_clusterer.cluster_article.return_value = mock_story
        mock_extractor.extract_news_items.return_value = []

        mock_clusterer_class.return_value = mock_clusterer
        mock_extractor_class.return_value = mock_extractor

        yield {
            "clusterer_class": mock_clusterer_class,
            "extractor_class": mock_extractor_class,
            "clusterer": mock_clusterer,
            "extractor": mock_extractor,
            "story": mock_story,
        }


# =============================================================================
# Tests for StoryClusterer Initialization
# =============================================================================


class TestStoryClustererInitialization:
    """Tests for StoryClusterer __init__ and basic setup."""

    def test_clusterer_initialization_with_mock_dependencies(
        self, mock_llm_provider, mock_storage
    ):
        """Test that StoryClusterer can be initialized with mock dependencies."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider
        assert clusterer.storage is mock_storage

    def test_clusterer_initialization_with_real_storage(
        self, mock_llm_provider, storage
    ):
        """Test that StoryClusterer can be initialized with real storage."""
        clusterer = StoryClusterer(mock_llm_provider, storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider
        assert clusterer.storage is storage

    def test_clusterer_stores_llm_provider_reference(
        self, mock_llm_provider, mock_storage
    ):
        """Test that the LLM provider reference is properly stored."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        assert clusterer.llm is mock_llm_provider
        assert clusterer.llm.is_available() is True
        assert clusterer.llm.name == "mock-provider"

    def test_clusterer_stores_storage_reference(
        self, mock_llm_provider, mock_storage
    ):
        """Test that the storage reference is properly stored."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        assert clusterer.storage is mock_storage
        # Verify storage methods are accessible
        assert hasattr(clusterer.storage, 'get_active_stories')
        assert hasattr(clusterer.storage, 'save_story')

    def test_clusterer_with_unavailable_provider(
        self, mock_llm_provider_unavailable, mock_storage
    ):
        """Test that StoryClusterer can be initialized with unavailable provider."""
        # Initialization should succeed even if provider is unavailable
        clusterer = StoryClusterer(mock_llm_provider_unavailable, mock_storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider_unavailable
        assert clusterer.llm.is_available() is False

    def test_clusterer_with_error_prone_provider(
        self, mock_llm_provider_error, mock_storage
    ):
        """Test that StoryClusterer can be initialized with error-prone provider."""
        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider_error

    def test_clusterer_fixture_creation(self, story_clusterer):
        """Test that the story_clusterer fixture works correctly."""
        assert story_clusterer is not None
        assert isinstance(story_clusterer, StoryClusterer)

    def test_clusterer_real_storage_fixture_creation(
        self, story_clusterer_real_storage
    ):
        """Test that the story_clusterer_real_storage fixture works correctly."""
        assert story_clusterer_real_storage is not None
        assert isinstance(story_clusterer_real_storage, StoryClusterer)


class TestStoryClustererSimilarityThreshold:
    """Tests for similarity threshold configuration."""

    def test_default_similarity_threshold_value(
        self, mock_llm_provider, mock_storage
    ):
        """Test that the default similarity threshold is 0.7."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        assert clusterer.similarity_threshold == 0.7

    def test_similarity_threshold_type(self, mock_llm_provider, mock_storage):
        """Test that similarity threshold is a float."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        assert isinstance(clusterer.similarity_threshold, float)

    def test_similarity_threshold_is_valid_probability(
        self, mock_llm_provider, mock_storage
    ):
        """Test that similarity threshold is within valid probability range [0, 1]."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        assert 0.0 <= clusterer.similarity_threshold <= 1.0

    def test_similarity_threshold_can_be_modified(
        self, mock_llm_provider, mock_storage
    ):
        """Test that similarity threshold can be modified after initialization."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        # Modify the threshold
        clusterer.similarity_threshold = 0.5

        assert clusterer.similarity_threshold == 0.5

    def test_similarity_threshold_modification_to_higher_value(
        self, mock_llm_provider, mock_storage
    ):
        """Test modifying threshold to a higher value (more strict matching)."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        clusterer.similarity_threshold = 0.9

        assert clusterer.similarity_threshold == 0.9

    def test_similarity_threshold_modification_to_lower_value(
        self, mock_llm_provider, mock_storage
    ):
        """Test modifying threshold to a lower value (more lenient matching)."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        clusterer.similarity_threshold = 0.3

        assert clusterer.similarity_threshold == 0.3

    def test_similarity_threshold_edge_case_zero(
        self, mock_llm_provider, mock_storage
    ):
        """Test setting threshold to 0 (match everything)."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        clusterer.similarity_threshold = 0.0

        assert clusterer.similarity_threshold == 0.0

    def test_similarity_threshold_edge_case_one(
        self, mock_llm_provider, mock_storage
    ):
        """Test setting threshold to 1 (match only perfect similarity)."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        clusterer.similarity_threshold = 1.0

        assert clusterer.similarity_threshold == 1.0

    def test_similarity_threshold_persists_across_operations(
        self, mock_llm_provider, mock_storage
    ):
        """Test that threshold persists when operations are performed."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer.similarity_threshold = 0.8

        # Perform some operation (even if it doesn't change threshold)
        _ = clusterer.storage

        assert clusterer.similarity_threshold == 0.8


class TestStoryClustererMultipleInstances:
    """Tests for multiple StoryClusterer instances."""

    def test_multiple_clusterers_independent_thresholds(
        self, mock_llm_provider, mock_storage
    ):
        """Test that multiple clusterer instances have independent thresholds."""
        clusterer1 = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer2 = StoryClusterer(mock_llm_provider, mock_storage)

        # Modify one instance's threshold
        clusterer1.similarity_threshold = 0.5

        # The other instance should be unaffected
        assert clusterer1.similarity_threshold == 0.5
        assert clusterer2.similarity_threshold == 0.7  # Default

    def test_multiple_clusterers_same_storage(self, mock_llm_provider, mock_storage):
        """Test that multiple clusterers can share the same storage."""
        clusterer1 = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer2 = StoryClusterer(mock_llm_provider, mock_storage)

        assert clusterer1.storage is clusterer2.storage
        assert clusterer1.storage is mock_storage

    def test_multiple_clusterers_same_llm(self, mock_llm_provider, mock_storage):
        """Test that multiple clusterers can share the same LLM provider."""
        clusterer1 = StoryClusterer(mock_llm_provider, mock_storage)
        clusterer2 = StoryClusterer(mock_llm_provider, mock_storage)

        assert clusterer1.llm is clusterer2.llm
        assert clusterer1.llm is mock_llm_provider


class TestStoryClustererAttributeAccess:
    """Tests for StoryClusterer attribute access patterns."""

    def test_llm_attribute_is_accessible(self, story_clusterer):
        """Test that llm attribute is accessible."""
        assert hasattr(story_clusterer, 'llm')
        assert story_clusterer.llm is not None

    def test_storage_attribute_is_accessible(self, story_clusterer):
        """Test that storage attribute is accessible."""
        assert hasattr(story_clusterer, 'storage')
        assert story_clusterer.storage is not None

    def test_similarity_threshold_attribute_is_accessible(self, story_clusterer):
        """Test that similarity_threshold attribute is accessible."""
        assert hasattr(story_clusterer, 'similarity_threshold')
        assert story_clusterer.similarity_threshold is not None

    def test_all_public_methods_exist(self, story_clusterer):
        """Test that all expected public methods exist."""
        assert hasattr(story_clusterer, 'cluster_article')
        assert hasattr(story_clusterer, 'find_matching_story')
        assert hasattr(story_clusterer, 'create_new_story')
        assert hasattr(story_clusterer, 'update_story_with_article')

    def test_all_private_methods_exist(self, story_clusterer):
        """Test that expected private methods exist."""
        assert hasattr(story_clusterer, '_calculate_similarity')
        assert hasattr(story_clusterer, '_generate_comparison_prompt')
        assert hasattr(story_clusterer, '_parse_similarity_response')
        assert hasattr(story_clusterer, '_keyword_similarity')
        assert hasattr(story_clusterer, '_generate_story_title')
        assert hasattr(story_clusterer, '_generate_story_description')
        assert hasattr(story_clusterer, '_extract_keywords')


class TestStoryClustererWithDifferentProviders:
    """Tests for StoryClusterer with various LLM provider configurations."""

    def test_clusterer_with_high_confidence_provider(
        self, mock_llm_provider_high_confidence, mock_storage
    ):
        """Test initialization with high confidence provider."""
        clusterer = StoryClusterer(mock_llm_provider_high_confidence, mock_storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider_high_confidence

    def test_clusterer_with_low_confidence_provider(
        self, mock_llm_provider_low_confidence, mock_storage
    ):
        """Test initialization with low confidence provider."""
        clusterer = StoryClusterer(mock_llm_provider_low_confidence, mock_storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider_low_confidence

    def test_clusterer_with_not_same_story_provider(
        self, mock_llm_provider_not_same_story, mock_storage
    ):
        """Test initialization with provider that returns 'not same story'."""
        clusterer = StoryClusterer(mock_llm_provider_not_same_story, mock_storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider_not_same_story

    def test_clusterer_with_invalid_json_provider(
        self, mock_llm_provider_invalid_json, mock_storage
    ):
        """Test initialization with provider that returns invalid JSON."""
        clusterer = StoryClusterer(mock_llm_provider_invalid_json, mock_storage)

        assert clusterer is not None
        assert clusterer.llm is mock_llm_provider_invalid_json

    def test_clusterer_with_configurable_provider_available(
        self, mock_llm_provider_configurable, mock_storage
    ):
        """Test initialization with configurable provider that is available."""
        provider = mock_llm_provider_configurable(available=True)
        clusterer = StoryClusterer(provider, mock_storage)

        assert clusterer is not None
        assert clusterer.llm.is_available() is True

    def test_clusterer_with_configurable_provider_unavailable(
        self, mock_llm_provider_configurable, mock_storage
    ):
        """Test initialization with configurable provider that is unavailable."""
        provider = mock_llm_provider_configurable(available=False)
        clusterer = StoryClusterer(provider, mock_storage)

        assert clusterer is not None
        assert clusterer.llm.is_available() is False


class TestStoryClustererWithDifferentStorage:
    """Tests for StoryClusterer with various storage configurations."""

    def test_clusterer_with_empty_storage(self, mock_llm_provider, storage_empty):
        """Test initialization with empty storage."""
        clusterer = StoryClusterer(mock_llm_provider, storage_empty)

        assert clusterer is not None
        assert clusterer.storage is storage_empty

    def test_clusterer_with_storage_containing_articles(
        self, mock_llm_provider, storage_with_articles
    ):
        """Test initialization with storage containing articles."""
        clusterer = StoryClusterer(mock_llm_provider, storage_with_articles)

        assert clusterer is not None
        assert clusterer.storage is storage_with_articles

    def test_clusterer_with_storage_containing_stories(
        self, mock_llm_provider, storage_with_stories
    ):
        """Test initialization with storage containing stories."""
        clusterer = StoryClusterer(mock_llm_provider, storage_with_stories)

        assert clusterer is not None
        assert clusterer.storage is storage_with_stories

    def test_clusterer_with_storage_containing_both(
        self, mock_llm_provider, storage_with_articles_and_stories
    ):
        """Test initialization with storage containing articles and stories."""
        clusterer = StoryClusterer(mock_llm_provider, storage_with_articles_and_stories)

        assert clusterer is not None
        assert clusterer.storage is storage_with_articles_and_stories

    def test_clusterer_with_mock_storage_with_stories(
        self, mock_llm_provider, mock_storage_with_stories
    ):
        """Test initialization with mock storage that has stories."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage_with_stories)

        assert clusterer is not None
        # Verify mock storage returns stories
        stories = clusterer.storage.get_active_stories()
        assert len(stories) == 5


# =============================================================================
# Tests for create_new_story()
# =============================================================================


class TestCreateNewStoryBasic:
    """Basic tests for create_new_story method."""

    def test_create_new_story_returns_story_object(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that create_new_story returns a Story object."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        assert isinstance(result, Story)

    def test_create_new_story_has_uuid_id(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that created story has a valid UUID id."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        # Verify ID is a valid UUID
        assert result.id is not None
        uuid.UUID(result.id)  # Raises if invalid

    def test_create_new_story_has_emerging_lifecycle_state(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that new story starts with 'emerging' lifecycle state."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        assert result.lifecycle_state == "emerging"

    def test_create_new_story_includes_article_id(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that new story includes the article ID."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        assert sample_article.id in result.article_ids
        assert len(result.article_ids) == 1

    def test_create_new_story_has_empty_news_item_ids(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that new story has empty news_item_ids list."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        assert result.news_item_ids == []

    def test_create_new_story_calls_save_story(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that create_new_story calls storage.save_story."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        mock_storage.save_story.assert_called_once_with(result)

    def test_create_new_story_calls_update_article_story(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that create_new_story updates the article's story_id."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        mock_storage.update_article_story.assert_called_once_with(
            sample_article.id, result.id
        )


class TestCreateNewStoryTimestampHandling:
    """Tests for timestamp handling in create_new_story."""

    def test_create_new_story_uses_article_published_datetime(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that first_seen uses article.published when it's a datetime."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article)

        # first_seen should match article.published
        assert result.first_seen is not None

    def test_create_new_story_parses_iso_string_date(
        self, mock_llm_provider, mock_storage
    ):
        """Test that create_new_story parses ISO string dates."""
        article = Article(
            id="article-iso-1",
            feed_url="https://example.com/feed.xml",
            title="Test Article",
            link="https://example.com/article-1",
            published="2025-01-07T12:30:00Z",
            content="Test content.",
            summary="Test summary.",
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(article)

        assert result.first_seen is not None
        assert result.first_seen.year == 2025
        assert result.first_seen.month == 1
        assert result.first_seen.day == 7

    def test_create_new_story_handles_no_published_date(
        self, mock_llm_provider, mock_storage, sample_article_no_published
    ):
        """Test that create_new_story handles article without published date."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        before = datetime.now()
        result = clusterer.create_new_story(sample_article_no_published)
        after = datetime.now()

        # first_seen should default to approximately now
        assert result.first_seen is not None
        assert before <= result.first_seen <= after

    def test_create_new_story_handles_invalid_date_string(
        self, mock_llm_provider, mock_storage
    ):
        """Test that create_new_story handles invalid date strings."""
        article = Article(
            id="article-invalid-date-1",
            feed_url="https://example.com/feed.xml",
            title="Test Article",
            link="https://example.com/article-1",
            published="not-a-valid-date",
            content="Test content.",
            summary="Test summary.",
        )

        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        before = datetime.now()
        result = clusterer.create_new_story(article)
        after = datetime.now()

        # Should default to now on parse failure
        assert result.first_seen is not None
        assert before <= result.first_seen <= after

    def test_create_new_story_sets_last_updated(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that last_updated is set to current time."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        before = datetime.now()
        result = clusterer.create_new_story(sample_article)
        after = datetime.now()

        assert result.last_updated is not None
        assert before <= result.last_updated <= after


class TestCreateNewStoryWithRealStorage:
    """Tests for create_new_story with real storage."""

    def test_create_new_story_persists_to_storage(
        self, mock_llm_provider, storage_empty, sample_article
    ):
        """Test that created story is persisted to real storage."""
        clusterer = StoryClusterer(mock_llm_provider, storage_empty)
        result = clusterer.create_new_story(sample_article)

        # Verify story can be retrieved
        stories = storage_empty.get_all_stories()
        assert len(stories) == 1
        assert stories[0].id == result.id

    def test_create_new_story_updates_article_in_storage(
        self, mock_llm_provider, storage_empty, sample_article
    ):
        """Test that article's story_id is updated in storage."""
        # First save our sample article to ensure it exists
        storage_empty.save_article(sample_article)

        # Verify article was saved
        saved = storage_empty.get_article(sample_article.id)
        assert saved is not None, "Article should be saved before creating story"

        clusterer = StoryClusterer(mock_llm_provider, storage_empty)
        result = clusterer.create_new_story(sample_article)

        # Verify article's story_id is updated
        updated_article = storage_empty.get_article(sample_article.id)
        assert updated_article is not None
        assert updated_article.story_id == result.id


class TestCreateNewStoryEdgeCases:
    """Edge case tests for create_new_story."""

    def test_create_new_story_with_unicode_content(
        self, mock_llm_provider, mock_storage, sample_article_unicode
    ):
        """Test create_new_story with unicode article content."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article_unicode)

        assert result is not None
        mock_storage.save_story.assert_called_once()

    def test_create_new_story_with_special_characters(
        self, mock_llm_provider, mock_storage, sample_article_special_chars
    ):
        """Test create_new_story with special characters in content."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article_special_chars)

        assert result is not None
        mock_storage.save_story.assert_called_once()

    def test_create_new_story_with_very_long_content(
        self, mock_llm_provider, mock_storage, sample_article_very_long
    ):
        """Test create_new_story with very long article content."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article_very_long)

        assert result is not None
        # Title and description should be truncated
        assert len(result.title) <= 100
        assert len(result.description) <= 500

    def test_create_new_story_with_minimal_article(
        self, mock_llm_provider, mock_storage, sample_article_minimal
    ):
        """Test create_new_story with minimal article data."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer.create_new_story(sample_article_minimal)

        assert result is not None
        assert result.title is not None  # Should use fallback

    def test_create_new_story_multiple_stories_unique_ids(
        self, mock_llm_provider, mock_storage, sample_articles_bulk
    ):
        """Test that multiple created stories have unique IDs."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)

        story_ids = []
        for article in sample_articles_bulk[:5]:
            result = clusterer.create_new_story(article)
            story_ids.append(result.id)

        # All IDs should be unique
        assert len(story_ids) == len(set(story_ids))


# =============================================================================
# Tests for update_story_with_article()
# =============================================================================


class TestUpdateStoryWithArticleBasic:
    """Basic tests for update_story_with_article method."""

    def test_update_story_adds_article_id(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article, sample_story
    ):
        """Test that update_story_with_article adds article ID to story."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        assert sample_article.id in result.article_ids

    def test_update_story_preserves_existing_article_ids(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article, sample_story
    ):
        """Test that existing article IDs are preserved."""
        original_ids = sample_story.article_ids.copy()

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        # All original IDs should still be there
        for article_id in original_ids:
            assert article_id in result.article_ids

    def test_update_story_does_not_duplicate_article_id(
        self, mock_llm_provider_with_keywords, mock_storage, sample_story
    ):
        """Test that article ID is not duplicated if already present."""
        # Create article with ID already in story
        article = Article(
            id=sample_story.article_ids[0],  # Use existing ID
            feed_url="https://example.com/feed.xml",
            title="Test Article",
            link="https://example.com/article-1",
            published=datetime.now(),
            content="Test content.",
            summary="Test summary.",
        )

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        original_count = len(sample_story.article_ids)
        result = clusterer.update_story_with_article(sample_story, article)

        # Count should not increase
        assert len(result.article_ids) == original_count

    def test_update_story_updates_last_updated(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article, sample_story
    ):
        """Test that last_updated timestamp is updated."""
        old_last_updated = sample_story.last_updated

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        before = datetime.now()
        result = clusterer.update_story_with_article(sample_story, sample_article)
        after = datetime.now()

        # last_updated should be updated to now
        assert result.last_updated >= old_last_updated
        assert before <= result.last_updated <= after

    def test_update_story_calls_update_story(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article, sample_story
    ):
        """Test that storage.update_story is called."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        mock_storage.update_story.assert_called_once_with(result)

    def test_update_story_calls_update_article_story(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article, sample_story
    ):
        """Test that storage.update_article_story is called."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        mock_storage.update_article_story.assert_called_once_with(
            sample_article.id, sample_story.id
        )

    def test_update_story_returns_story_object(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article, sample_story
    ):
        """Test that update_story_with_article returns a Story object."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        assert isinstance(result, Story)
        assert result.id == sample_story.id


class TestUpdateStoryKeywordHandling:
    """Tests for keyword handling in update_story_with_article."""

    def test_update_story_adds_new_keywords(
        self, mock_storage, sample_article, sample_story
    ):
        """Test that new keywords are added to story."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "newkeyword1, newkeyword2, newkeyword3"

        original_keywords = sample_story.keywords.copy()

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        # Should have original + new keywords
        assert len(result.keywords) > len(original_keywords)
        assert "newkeyword1" in result.keywords
        assert "newkeyword2" in result.keywords

    def test_update_story_does_not_duplicate_keywords(
        self, mock_storage, sample_article, sample_story
    ):
        """Test that duplicate keywords are not added."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        # Return keywords that already exist
        existing = sample_story.keywords[0] if sample_story.keywords else "test"
        mock_llm.generate.return_value = f"{existing}, newkeyword"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        # Should not have duplicate of existing keyword
        keyword_counts = {}
        for kw in result.keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        assert all(count == 1 for count in keyword_counts.values())

    def test_update_story_limits_keywords_to_20(
        self, mock_storage, sample_article
    ):
        """Test that keywords are limited to 20."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        # Return many keywords
        mock_llm.generate.return_value = ", ".join([f"keyword{i}" for i in range(15)])

        # Story with existing keywords
        story = Story(
            id="story-test",
            title="Test Story",
            description="Test description",
            keywords=[f"existing{i}" for i in range(10)],  # 10 existing
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["article-1"],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.update_story_with_article(story, sample_article)

        # Should be limited to 20 keywords
        assert len(result.keywords) <= 20

    def test_update_story_preserves_keyword_order(
        self, mock_storage, sample_article
    ):
        """Test that original keywords maintain their order."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "newkeyword"

        story = Story(
            id="story-test",
            title="Test Story",
            description="Test description",
            keywords=["first", "second", "third"],
            first_seen=datetime.now() - timedelta(days=1),
            last_updated=datetime.now() - timedelta(hours=1),
            lifecycle_state="developing",
            article_ids=["article-1"],
            news_item_ids=[],
        )

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.update_story_with_article(story, sample_article)

        # Original order should be preserved
        assert result.keywords[0] == "first"
        assert result.keywords[1] == "second"
        assert result.keywords[2] == "third"


class TestUpdateStoryWithRealStorage:
    """Tests for update_story_with_article with real storage."""

    def test_update_story_persists_to_storage(
        self, mock_llm_provider_with_keywords, storage_with_stories, sample_article
    ):
        """Test that updated story is persisted to real storage."""
        # Get existing story
        stories = storage_with_stories.get_active_stories()
        story = stories[0]
        original_article_count = len(story.article_ids)

        # Save sample article
        storage_with_stories.save_article(sample_article)

        clusterer = StoryClusterer(mock_llm_provider_with_keywords, storage_with_stories)
        result = clusterer.update_story_with_article(story, sample_article)

        # Verify story is updated in storage
        updated_story = storage_with_stories.get_story(story.id)
        assert len(updated_story.article_ids) == original_article_count + 1
        assert sample_article.id in updated_story.article_ids


class TestUpdateStoryEdgeCases:
    """Edge case tests for update_story_with_article."""

    def test_update_story_with_no_keywords(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article, sample_story_no_keywords
    ):
        """Test updating story that has no keywords."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story_no_keywords, sample_article)

        # Should have new keywords now
        assert len(result.keywords) > 0

    def test_update_story_with_unicode_article(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article_unicode, sample_story
    ):
        """Test updating story with unicode article."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article_unicode)

        assert result is not None
        assert sample_article_unicode.id in result.article_ids

    def test_update_story_with_empty_content_article(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article_minimal, sample_story
    ):
        """Test updating story with minimal/empty content article."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article_minimal)

        assert result is not None
        assert sample_article_minimal.id in result.article_ids

    def test_update_story_multiple_articles_sequential(
        self, mock_llm_provider_with_keywords, mock_storage, sample_articles_bulk, sample_story
    ):
        """Test updating story with multiple articles sequentially."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)

        result = sample_story
        for article in sample_articles_bulk[:3]:
            result = clusterer.update_story_with_article(result, article)

        # All articles should be in story
        for article in sample_articles_bulk[:3]:
            assert article.id in result.article_ids


# =============================================================================
# Tests for metadata generation methods
# =============================================================================


class TestGenerateStoryTitle:
    """Tests for _generate_story_title method."""

    def test_generate_story_title_calls_llm(
        self, mock_storage, sample_article
    ):
        """Test that _generate_story_title calls LLM."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "Generated Title"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._generate_story_title(sample_article)

        mock_llm.generate.assert_called_once()

    def test_generate_story_title_returns_string(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that _generate_story_title returns a string."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_story_title(sample_article)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_story_title_removes_quotes(
        self, mock_storage, sample_article
    ):
        """Test that quotes are removed from generated title."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = '"Title with "quotes" inside"'

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._generate_story_title(sample_article)

        assert '"' not in result

    def test_generate_story_title_removes_newlines(
        self, mock_storage, sample_article
    ):
        """Test that newlines are removed from generated title."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "Title with\nnewlines\nin it"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._generate_story_title(sample_article)

        assert "\n" not in result

    def test_generate_story_title_preserves_full_title(
        self, mock_storage, sample_article
    ):
        """Test that valid title is preserved without arbitrary truncation.

        Note: Code rejects titles > 100 chars as garbage, so test uses 80 chars.
        """
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        valid_title = "Major Tech Development in AI Industry Announced Today"  # 54 chars
        mock_llm.generate.return_value = valid_title

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._generate_story_title(sample_article)

        assert result == valid_title

    def test_generate_story_title_fallback_on_error(
        self, mock_llm_provider_error, mock_storage, sample_article
    ):
        """Test that article title is used as fallback on error."""
        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)
        result = clusterer._generate_story_title(sample_article)

        assert result == sample_article.title

    def test_generate_story_title_prompt_includes_article_title(
        self, mock_storage, sample_article
    ):
        """Test that prompt includes article title."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "Generated Title"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        clusterer._generate_story_title(sample_article)

        # Check that article title is in the prompt
        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0]
        assert sample_article.title in prompt


class TestGenerateStoryDescription:
    """Tests for _generate_story_description method."""

    def test_generate_story_description_calls_llm(
        self, mock_storage, sample_article
    ):
        """Test that _generate_story_description calls LLM."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "Generated Description"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._generate_story_description(sample_article)

        mock_llm.generate.assert_called_once()

    def test_generate_story_description_returns_string(
        self, mock_llm_provider, mock_storage, sample_article
    ):
        """Test that _generate_story_description returns a string."""
        clusterer = StoryClusterer(mock_llm_provider, mock_storage)
        result = clusterer._generate_story_description(sample_article)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_story_description_preserves_full_description(
        self, mock_storage, sample_article
    ):
        """Test that full description is preserved without arbitrary truncation."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        long_desc = "B" * 600
        mock_llm.generate.return_value = long_desc

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._generate_story_description(sample_article)

        assert result == long_desc

    def test_generate_story_description_fallback_to_summary(
        self, mock_llm_provider_error, mock_storage, sample_article
    ):
        """Test that article summary is used as fallback on error."""
        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)
        result = clusterer._generate_story_description(sample_article)

        assert result == sample_article.summary

    def test_generate_story_description_fallback_to_content(
        self, mock_llm_provider_error, mock_storage, sample_article_unsummarized
    ):
        """Test that article content is used if no summary available."""
        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)
        result = clusterer._generate_story_description(sample_article_unsummarized)

        assert result == (sample_article_unsummarized.content or "")

    def test_generate_story_description_prompt_includes_content(
        self, mock_storage, sample_article
    ):
        """Test that prompt includes article content."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "Generated Description"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        clusterer._generate_story_description(sample_article)

        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0]
        # Content is truncated in prompt
        assert sample_article.title in prompt


class TestExtractKeywords:
    """Tests for _extract_keywords method."""

    def test_extract_keywords_calls_llm(
        self, mock_storage, sample_article
    ):
        """Test that _extract_keywords calls LLM."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "keyword1, keyword2, keyword3"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        mock_llm.generate.assert_called_once()

    def test_extract_keywords_returns_list(
        self, mock_llm_provider_with_keywords, mock_storage, sample_article
    ):
        """Test that _extract_keywords returns a list."""
        clusterer = StoryClusterer(mock_llm_provider_with_keywords, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        assert isinstance(result, list)

    def test_extract_keywords_splits_by_comma(
        self, mock_storage, sample_article
    ):
        """Test that keywords are split by comma."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "keyword1, keyword2, keyword3"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        assert "keyword1" in result
        assert "keyword2" in result
        assert "keyword3" in result

    def test_extract_keywords_strips_whitespace(
        self, mock_storage, sample_article
    ):
        """Test that whitespace is stripped from keywords."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "  keyword1  ,  keyword2  ,  keyword3  "

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        for kw in result:
            assert kw == kw.strip()

    def test_extract_keywords_filters_short_keywords(
        self, mock_storage, sample_article
    ):
        """Test that keywords with 2 or fewer characters are filtered."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "a, ab, abc, keyword"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        # "a" and "ab" should be filtered (len <= 2)
        assert "a" not in result
        assert "ab" not in result
        assert "abc" in result
        assert "keyword" in result

    def test_extract_keywords_filters_empty_strings(
        self, mock_storage, sample_article
    ):
        """Test that empty strings are filtered."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "keyword1, , , keyword2, "

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        assert "" not in result
        assert "keyword1" in result
        assert "keyword2" in result

    def test_extract_keywords_preserves_all_keywords(
        self, mock_storage, sample_article
    ):
        """Test that all keywords are preserved without arbitrary limits."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = ", ".join([f"keyword{i}" for i in range(20)])

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        assert len(result) == 20

    def test_extract_keywords_fallback_on_error(
        self, mock_llm_provider_error, mock_storage, sample_article
    ):
        """Test that title words are used as fallback on error."""
        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)
        result = clusterer._extract_keywords(sample_article)

        # Should extract words from title with len > 4
        for kw in result:
            assert len(kw) > 4

    def test_extract_keywords_fallback_preserves_all_words(
        self, mock_llm_provider_error, mock_storage
    ):
        """Test that fallback preserves all qualifying words without arbitrary limits."""
        article = Article(
            id="article-many-words",
            feed_url="https://example.com/feed.xml",
            title="Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10",
            link="https://example.com/article-1",
            published=datetime.now(),
            content="Test content.",
            summary="Test summary.",
        )

        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)
        result = clusterer._extract_keywords(article)

        # All words with len > 4 should be preserved
        assert len(result) == 10


class TestMetadataGenerationIntegration:
    """Integration tests for metadata generation."""

    def test_create_new_story_uses_all_metadata_methods(
        self, mock_storage, sample_article
    ):
        """Test that create_new_story uses all metadata generation methods."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = [
            "Generated Title",  # _generate_story_title
            "Generated Description",  # _generate_story_description
            "keyword1, keyword2, keyword3",  # _extract_keywords
        ]

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.create_new_story(sample_article)

        assert mock_llm.generate.call_count == 3
        assert result.title == "Generated Title"
        assert result.description == "Generated Description"
        assert "keyword1" in result.keywords

    def test_metadata_fallback_chain_on_llm_error(
        self, mock_llm_provider_error, mock_storage, sample_article
    ):
        """Test that all fallbacks work when LLM fails."""
        clusterer = StoryClusterer(mock_llm_provider_error, mock_storage)
        result = clusterer.create_new_story(sample_article)

        # Title fallback
        assert result.title == sample_article.title[:100]
        # Description fallback
        assert result.description == sample_article.summary or sample_article.content[:200]
        # Keywords fallback (words from title)
        assert len(result.keywords) > 0

    def test_metadata_with_mixed_llm_responses(
        self, mock_storage, sample_article
    ):
        """Test metadata generation with mixed success/failure LLM calls."""
        call_count = [0]

        def generate_response(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "Generated Title"
            elif call_count[0] == 2:
                raise Exception("LLM error")  # Description fails
            else:
                return "keyword1, keyword2"

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = generate_response

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.create_new_story(sample_article)

        # Title from LLM
        assert result.title == "Generated Title"
        # Description from fallback
        assert result.description == sample_article.summary or sample_article.content[:200]
        # Keywords from LLM (third call succeeds)
        assert "keyword1" in result.keywords

    def test_create_story_handles_llm_returning_empty_strings(
        self, mock_storage, sample_article
    ):
        """Test handling of empty string responses from LLM."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = ""

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.create_new_story(sample_article)

        # Should still create a valid story
        assert result is not None
        assert result.title is not None

    def test_update_story_metadata_extraction(
        self, mock_storage, sample_article, sample_story
    ):
        """Test that update_story_with_article extracts keywords properly."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "newkeyword1, newkeyword2"

        clusterer = StoryClusterer(mock_llm, mock_storage)
        result = clusterer.update_story_with_article(sample_story, sample_article)

        # New keywords should be added
        assert "newkeyword1" in result.keywords
        assert "newkeyword2" in result.keywords


class TestCreateNewStoryAndUpdateIntegration:
    """Integration tests for create_new_story and update_story_with_article together."""

    def test_create_then_update_workflow(
        self, storage_empty, sample_articles_bulk
    ):
        """Test creating a story then updating it with more articles."""
        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.return_value = "keyword1, keyword2"

        clusterer = StoryClusterer(mock_llm, storage_empty)

        # Create new story with first article
        for article in sample_articles_bulk[:3]:
            storage_empty.save_article(article)

        story = clusterer.create_new_story(sample_articles_bulk[0])
        assert len(story.article_ids) == 1

        # Update with additional articles
        story = clusterer.update_story_with_article(story, sample_articles_bulk[1])
        story = clusterer.update_story_with_article(story, sample_articles_bulk[2])

        # Should have all 3 articles
        assert len(story.article_ids) == 3

    def test_full_clustering_workflow_with_metadata(
        self, storage_empty, sample_article
    ):
        """Test full clustering workflow including metadata generation."""
        storage_empty.save_article(sample_article)

        call_count = [0]

        def generate_response(*args, **kwargs):
            call_count[0] += 1
            # Check for headline prompt (title generation uses "headline" not "title")
            if "headline" in args[0].lower():
                return "AI Technology Story"
            elif "describe" in args[0].lower():
                return "Story about AI technology developments."
            else:
                # Use keywords with > 2 chars (short ones like "AI" get filtered)
                return "artificial, technology, innovation"

        mock_llm = MagicMock(spec=LLMProvider)
        mock_llm.is_available.return_value = True
        mock_llm.generate.side_effect = generate_response

        clusterer = StoryClusterer(mock_llm, storage_empty)
        story = clusterer.create_new_story(sample_article)

        assert story.title == "AI Technology Story"
        assert "AI technology" in story.description
        # Keywords with len <= 2 are filtered, so check for longer keywords
        assert "technology" in story.keywords

        # Verify persisted
        saved_story = storage_empty.get_story(story.id)
        assert saved_story is not None
        assert saved_story.title == "AI Technology Story"
