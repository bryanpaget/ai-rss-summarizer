"""Tests for perspectives module - perspective synthesis and multi-source analysis."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import MagicMock, patch, Mock

import pytest

from src.perspectives import (
    PERSPECTIVE_CATEGORIES,
    DEFAULT_CATEGORIES,
    Perspective,
    PerspectiveError,
    InsufficientSourcesError,
    CategoryNotApplicableError,
    LLMProviderError,
    build_perspective_prompt,
    estimate_confidence,
    generate_fallback_perspective,
    synthesize_perspective,
    synthesize_perspectives,
    is_cache_fresh,
    get_user_perspective_config,
    update_user_perspective_config,
)
from src.storage import Storage, Article, Story
from src.llm_providers import LLMProvider


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
            feed_url=f"https://source{i % 3}.example.com/feed.xml",
            title=f"Test Article {i} About AI Technology",
            link=f"https://example.com/article-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of test article {i}. This article discusses AI technology developments. " * 10,
            summary=f"Summary of article {i} about AI." if i % 2 == 0 else None,
            story_id="story-cluster-1" if i < 5 else None,
        )
        for i in range(10)
    ]
    for article in articles:
        store.save_article(article)
    return store


@pytest.fixture
def storage_with_cluster(temp_db):
    """Create a Storage instance with articles in a cluster."""
    store = Storage(temp_db)

    # Create clustered articles for perspective synthesis
    cluster_articles = [
        Article(
            id="article-cluster-1",
            feed_url="https://techblog.example.com/feed.xml",
            title="New AI Model Achieves Breakthrough in Language Understanding",
            link="https://techblog.example.com/ai-breakthrough",
            published=datetime.now() - timedelta(hours=2),
            content="Researchers have developed a new AI model that shows remarkable capabilities in language understanding. "
                    "The model uses a novel architecture that improves performance by 30%. Industry experts are excited.",
            summary="New AI model shows breakthrough performance.",
            story_id="story-ai-1",
        ),
        Article(
            id="article-cluster-2",
            feed_url="https://business.example.com/feed.xml",
            title="Tech Company Stock Surges on AI Announcement",
            link="https://business.example.com/stock-surge",
            published=datetime.now() - timedelta(hours=1),
            content="Tech company shares rose 15% following the announcement of their new AI technology. "
                    "Analysts predict continued growth. Some experts question the hype around AI capabilities.",
            summary="Stock prices rise on AI news.",
            story_id="story-ai-1",
        ),
        Article(
            id="article-cluster-3",
            feed_url="https://mainstream.example.com/feed.xml",
            title="What the New AI Means for Everyday Users",
            link="https://mainstream.example.com/ai-users",
            published=datetime.now() - timedelta(minutes=30),
            content="The latest AI developments will impact how people work and live. "
                    "Privacy concerns have been raised by advocacy groups. The technology could help or harm society.",
            summary="AI impact on everyday life.",
            story_id="story-ai-1",
        ),
    ]

    # Create story for the cluster
    story = Story(
        id="story-ai-1",
        title="AI Technology Breakthrough Coverage",
        description="Multi-source coverage of new AI developments",
        keywords=["AI", "technology", "breakthrough", "machine learning"],
        first_seen=datetime.now() - timedelta(hours=3),
        last_updated=datetime.now() - timedelta(minutes=30),
        lifecycle_state="developing",
        article_ids=["article-cluster-1", "article-cluster-2", "article-cluster-3"],
        news_item_ids=[],
    )

    for article in cluster_articles:
        store.save_article(article)
    store.save_story(story)

    return store


@pytest.fixture
def storage_with_single_article(temp_db):
    """Create a Storage instance with only one article."""
    store = Storage(temp_db)
    article = Article(
        id="article-single-1",
        feed_url="https://example.com/feed.xml",
        title="Single Source Article",
        link="https://example.com/single",
        published=datetime.now(),
        content="This is a single source article with no other perspectives.",
        summary="Single source only.",
        story_id="story-single-1",
    )
    story = Story(
        id="story-single-1",
        title="Single Source Story",
        description="Story with only one source",
        keywords=["single", "source"],
        first_seen=datetime.now(),
        last_updated=datetime.now(),
        lifecycle_state="emerging",
        article_ids=["article-single-1"],
        news_item_ids=[],
    )
    store.save_article(article)
    store.save_story(story)
    return store


# =============================================================================
# Fixtures for Mock Storage
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock Storage object with common methods.

    Note: Does not use spec=Storage because perspectives.py expects
    get_articles_by_cluster method which may not exist on Storage.
    """
    storage = MagicMock()
    storage.get_articles.return_value = []
    storage.get_article.return_value = None
    storage.get_articles_by_cluster.return_value = []
    storage.get_cached_perspective.return_value = None
    storage.cache_perspective.return_value = None
    storage.get_perspective_config.return_value = None
    storage.save_perspective_config.return_value = None
    return storage


@pytest.fixture
def mock_storage_with_articles():
    """Create a mock Storage with articles for perspective synthesis.

    Note: Does not use spec=Storage because perspectives.py expects
    get_articles_by_cluster method which may not exist on Storage.
    """
    storage = MagicMock()

    sample_articles = [
        Article(
            id=f"mock-article-{i}",
            feed_url=f"https://source{i}.example.com/feed.xml",
            title=f"Mock Article {i} Title",
            link=f"https://source{i}.example.com/article",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of mock article {i}. " * 20,
            summary=f"Summary of mock article {i}.",
            story_id="mock-story-1",
        )
        for i in range(5)
    ]

    storage.get_articles.return_value = sample_articles
    storage.get_articles_by_cluster.return_value = sample_articles
    storage.get_cached_perspective.return_value = None
    storage.cache_perspective.return_value = None
    storage.get_perspective_config.return_value = None
    return storage


@pytest.fixture
def mock_storage_with_cached_perspective():
    """Create a mock Storage with a cached perspective.

    Note: Does not use spec=Storage because perspectives.py expects
    get_articles_by_cluster method which may not exist on Storage.
    """
    storage = MagicMock()

    cached_perspective = Perspective(
        category="consensus",
        content="Cached perspective content: All sources agree on the main facts.",
        source_articles=["article-1", "article-2"],
        confidence=0.8,
        generated_at=datetime.now() - timedelta(hours=1),  # Fresh cache
    )

    storage.get_cached_perspective.return_value = cached_perspective
    storage.get_articles_by_cluster.return_value = []
    return storage


@pytest.fixture
def mock_storage_with_stale_cache():
    """Create a mock Storage with a stale cached perspective.

    Note: Does not use spec=Storage because perspectives.py expects
    get_articles_by_cluster method which may not exist on Storage.
    """
    storage = MagicMock()

    stale_perspective = Perspective(
        category="consensus",
        content="Stale cached perspective content.",
        source_articles=["article-1"],
        confidence=0.5,
        generated_at=datetime.now() - timedelta(hours=24),  # Stale cache
    )

    storage.get_cached_perspective.return_value = stale_perspective
    storage.get_articles_by_cluster.return_value = []
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
    )


@pytest.fixture
def sample_article_business():
    """Create a business-focused sample article."""
    return Article(
        id="article-business-1",
        feed_url="https://finance.example.com/feed.xml",
        title="Stock Market Reacts to AI News with Record Gains",
        link="https://finance.example.com/article-1",
        published=datetime.now() - timedelta(hours=1),
        content="The stock market reached new highs following AI announcements. "
                "Investors are optimistic about AI-driven growth. "
                "Some analysts warn of potential overvaluation.",
        summary="Stock market hits record high on AI news.",
    )


@pytest.fixture
def sample_article_mainstream():
    """Create a mainstream news sample article."""
    return Article(
        id="article-mainstream-1",
        feed_url="https://news.example.com/feed.xml",
        title="How AI Will Change Your Daily Life",
        link="https://news.example.com/ai-daily-life",
        published=datetime.now() - timedelta(minutes=30),
        content="AI technology is set to transform how we live and work. "
                "From smart homes to healthcare, the impact will be widespread. "
                "Experts debate the implications for privacy and employment.",
        summary="AI to transform daily life.",
    )


@pytest.fixture
def sample_article_political():
    """Create a politically-focused sample article."""
    return Article(
        id="article-political-1",
        feed_url="https://policy.example.com/feed.xml",
        title="Government Proposes New AI Regulations",
        link="https://policy.example.com/ai-regulations",
        published=datetime.now() - timedelta(hours=3),
        content="Lawmakers are considering new regulations for AI technology. "
                "The proposed rules would require transparency and safety testing. "
                "Industry groups have expressed concerns about innovation impact.",
        summary="New AI regulations proposed.",
    )


@pytest.fixture
def sample_article_academic():
    """Create an academic-focused sample article."""
    return Article(
        id="article-academic-1",
        feed_url="https://research.example.edu/feed.xml",
        title="Peer-Reviewed Study Confirms AI Capabilities",
        link="https://research.example.edu/ai-study",
        published=datetime.now() - timedelta(hours=6),
        content="A peer-reviewed study has validated claims about AI performance. "
                "The research methodology was rigorous and reproducible. "
                "Further research is needed to understand long-term implications.",
        summary="Study validates AI capabilities.",
    )


@pytest.fixture
def sample_article_controversial():
    """Create a controversial sample article with strong opinions."""
    return Article(
        id="article-controversial-1",
        feed_url="https://opinion.example.com/feed.xml",
        title="AI is Either Our Salvation or Doom - Expert Claims",
        link="https://opinion.example.com/ai-extreme",
        published=datetime.now() - timedelta(hours=4),
        content="A prominent expert made bold claims about AI's future. "
                "'AI will either solve all our problems or destroy civilization,' they said. "
                "Critics call the prediction unhinged speculation.",
        summary="Expert makes extreme AI predictions.",
    )


@pytest.fixture
def sample_article_unicode():
    """Create an article with unicode content."""
    return Article(
        id="article-unicode-1",
        feed_url="https://example.com/feed.xml",
        title="AI研究の突破口: 中文技术发展 🤖",
        link="https://example.com/unicode",
        published=datetime.now(),
        content="This article contains unicode: 人工智能, 機械学習, 🚀💡🎯",
        summary="Unicode content test.",
    )


@pytest.fixture
def sample_article_empty_content():
    """Create an article with empty content."""
    return Article(
        id="article-empty-1",
        feed_url="https://example.com/feed.xml",
        title="Article With No Content",
        link="https://example.com/empty",
        published=datetime.now(),
        content="",
        summary=None,
    )


@pytest.fixture
def sample_article_very_long():
    """Create an article with very long content."""
    return Article(
        id="article-long-1",
        feed_url="https://example.com/feed.xml",
        title="Comprehensive Deep Dive into AI Technology",
        link="https://example.com/long",
        published=datetime.now(),
        content="This is a very detailed article about AI technology. " * 500,
        summary="Very long article about AI.",
    )


@pytest.fixture
def sample_article_old():
    """Create an old article (published more than 24 hours ago)."""
    return Article(
        id="article-old-1",
        feed_url="https://example.com/feed.xml",
        title="Old AI Article From Last Week",
        link="https://example.com/old",
        published=datetime.now() - timedelta(days=7),
        content="This is an older article about AI developments from last week.",
        summary="Week-old AI article.",
    )


@pytest.fixture
def sample_article_string_date():
    """Create an article with a string-formatted published date."""
    return Article(
        id="article-string-date-1",
        feed_url="https://example.com/feed.xml",
        title="Article With String Date",
        link="https://example.com/string-date",
        published="2024-01-15T10:30:00Z",  # String format instead of datetime
        content="This article has a string-formatted date.",
        summary="String date article.",
    )


@pytest.fixture
def sample_articles_bulk():
    """Create a list of articles for bulk testing."""
    return [
        Article(
            id=f"bulk-article-{i}",
            feed_url=f"https://source{i % 5}.example.com/feed.xml",
            title=f"Bulk Test Article {i} About Technology",
            link=f"https://example.com/bulk-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Content of bulk article {i}. Technology discussion. " * 15,
            summary=f"Summary of bulk article {i}." if i % 2 == 0 else None,
        )
        for i in range(20)
    ]


# =============================================================================
# Fixtures for Article Clusters
# =============================================================================


@pytest.fixture
def article_cluster_tech_news(sample_article_tech, sample_article_business, sample_article_mainstream):
    """Create a cluster of articles about tech news from different perspectives."""
    return [sample_article_tech, sample_article_business, sample_article_mainstream]


@pytest.fixture
def article_cluster_diverse(
    sample_article_tech,
    sample_article_business,
    sample_article_mainstream,
    sample_article_political,
    sample_article_academic,
):
    """Create a diverse cluster with many perspectives."""
    return [
        sample_article_tech,
        sample_article_business,
        sample_article_mainstream,
        sample_article_political,
        sample_article_academic,
    ]


@pytest.fixture
def article_cluster_two_sources(sample_article_tech, sample_article_business):
    """Create a minimal cluster with exactly two sources (minimum for consensus/contested)."""
    return [sample_article_tech, sample_article_business]


@pytest.fixture
def article_cluster_single_source(sample_article):
    """Create a cluster with only one source."""
    return [sample_article]


@pytest.fixture
def article_cluster_empty():
    """Create an empty article cluster."""
    return []


@pytest.fixture
def article_cluster_with_controversial(sample_article_tech, sample_article_controversial):
    """Create a cluster with controversial content for spicy takes testing."""
    return [sample_article_tech, sample_article_controversial]


@pytest.fixture
def article_cluster_all_old(sample_article_old):
    """Create a cluster with only old articles."""
    return [
        sample_article_old,
        Article(
            id="article-old-2",
            feed_url="https://example.com/feed.xml",
            title="Another Old Article",
            link="https://example.com/old-2",
            published=datetime.now() - timedelta(days=5),
            content="Another old article content.",
            summary="Another old article.",
        ),
    ]


@pytest.fixture
def article_cluster_all_recent():
    """Create a cluster with only recent articles (within 24 hours)."""
    return [
        Article(
            id=f"recent-article-{i}",
            feed_url=f"https://source{i}.example.com/feed.xml",
            title=f"Recent Article {i}",
            link=f"https://example.com/recent-{i}",
            published=datetime.now() - timedelta(hours=i),
            content=f"Recent article {i} content.",
            summary=f"Recent article {i}.",
        )
        for i in range(5)
    ]


@pytest.fixture
def article_cluster_mixed_dates():
    """Create a cluster with a mix of recent and old articles."""
    recent = [
        Article(
            id=f"mixed-recent-{i}",
            feed_url=f"https://source{i}.example.com/feed.xml",
            title=f"Recent Mixed Article {i}",
            link=f"https://example.com/mixed-recent-{i}",
            published=datetime.now() - timedelta(hours=i * 2),
            content=f"Recent mixed article {i}.",
            summary=f"Recent {i}.",
        )
        for i in range(3)
    ]
    old = [
        Article(
            id=f"mixed-old-{i}",
            feed_url=f"https://source{i + 3}.example.com/feed.xml",
            title=f"Old Mixed Article {i}",
            link=f"https://example.com/mixed-old-{i}",
            published=datetime.now() - timedelta(days=i + 2),
            content=f"Old mixed article {i}.",
            summary=f"Old {i}.",
        )
        for i in range(2)
    ]
    return recent + old


# =============================================================================
# Fixtures for Mock LLM Provider
# =============================================================================


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm"
    provider.model = "mock-model"
    provider.is_available.return_value = True
    provider.summarize.return_value = "Mock synthesized perspective content."
    return provider


@pytest.fixture
def mock_llm_provider_verbose():
    """Create a mock LLM provider that returns verbose responses."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm-verbose"
    provider.model = "mock-model"
    provider.is_available.return_value = True
    provider.summarize.return_value = (
        "This is a comprehensive analysis of the articles provided.\n\n"
        "- Point 1: All sources agree on the main facts about AI development.\n"
        "- Point 2: There is consensus about the technological breakthrough.\n"
        "- Point 3: Industry impact is acknowledged across all sources.\n\n"
        "The synthesis shows strong agreement on core issues."
    )
    return provider


@pytest.fixture
def mock_llm_provider_unavailable():
    """Create a mock LLM provider that is unavailable."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm-unavailable"
    provider.is_available.return_value = False
    provider.summarize.side_effect = RuntimeError("Provider not available")
    return provider


@pytest.fixture
def mock_llm_provider_error():
    """Create a mock LLM provider that raises errors."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm-error"
    provider.is_available.return_value = True
    provider.summarize.side_effect = Exception("LLM synthesis failed")
    return provider


@pytest.fixture
def mock_llm_provider_empty():
    """Create a mock LLM provider that returns empty responses."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm-empty"
    provider.is_available.return_value = True
    provider.summarize.return_value = ""
    return provider


@pytest.fixture
def mock_llm_provider_short():
    """Create a mock LLM provider that returns very short responses."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm-short"
    provider.is_available.return_value = True
    provider.summarize.return_value = "Too short"
    return provider


@pytest.fixture
def mock_llm_provider_uncertain():
    """Create a mock LLM provider that returns uncertain responses."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm-uncertain"
    provider.is_available.return_value = True
    provider.summarize.return_value = (
        "The information is unclear from the sources provided.\n"
        "There is insufficient data to draw conclusions.\n"
        "Many aspects are unknown at this time."
    )
    return provider


@pytest.fixture
def mock_llm_provider_category_specific():
    """Create a mock LLM provider with category-specific responses."""
    provider = MagicMock(spec=LLMProvider)
    provider.name = "mock-llm-category"
    provider.is_available.return_value = True

    def category_response(prompt, **kwargs):
        if "consensus" in prompt.lower():
            return "All sources agree: AI represents a major technological breakthrough."
        elif "contested" in prompt.lower():
            return "Sources disagree on: timeline for implementation, regulatory approach."
        elif "gaps" in prompt.lower():
            return "Coverage gaps: long-term employment impact, environmental costs."
        elif "spiciest" in prompt.lower():
            return "'AI will replace all human workers!' - Controversial Expert"
        else:
            return "Generic perspective analysis content."

    provider.summarize.side_effect = category_response
    return provider


# =============================================================================
# Fixtures for Perspective Objects
# =============================================================================


@pytest.fixture
def sample_perspective():
    """Create a sample Perspective object."""
    return Perspective(
        category="consensus",
        content="All sources agree on the core facts about the AI breakthrough.",
        source_articles=["article-1", "article-2", "article-3"],
        confidence=0.8,
        generated_at=datetime.now(),
    )


@pytest.fixture
def sample_perspective_contested():
    """Create a contested perspective."""
    return Perspective(
        category="contested",
        content="Sources disagree on the timeline and impact of AI development.",
        source_articles=["article-1", "article-2"],
        confidence=0.7,
        generated_at=datetime.now(),
    )


@pytest.fixture
def sample_perspective_gaps():
    """Create a gaps perspective."""
    return Perspective(
        category="gaps",
        content="No source covers the environmental impact or long-term societal effects.",
        source_articles=["article-1"],
        confidence=0.6,
        generated_at=datetime.now(),
    )


@pytest.fixture
def sample_perspective_low_confidence():
    """Create a low-confidence perspective."""
    return Perspective(
        category="consensus",
        content="Limited agreement found between sources.",
        source_articles=["article-1"],
        confidence=0.2,
        generated_at=datetime.now(),
    )


@pytest.fixture
def sample_perspective_fresh():
    """Create a freshly generated perspective (within TTL)."""
    return Perspective(
        category="consensus",
        content="Fresh perspective content.",
        source_articles=["article-1", "article-2"],
        confidence=0.75,
        generated_at=datetime.now() - timedelta(hours=1),
    )


@pytest.fixture
def sample_perspective_stale():
    """Create a stale perspective (outside TTL)."""
    return Perspective(
        category="consensus",
        content="Stale perspective content.",
        source_articles=["article-1", "article-2"],
        confidence=0.75,
        generated_at=datetime.now() - timedelta(hours=12),
    )


@pytest.fixture
def sample_perspective_very_old():
    """Create a very old perspective."""
    return Perspective(
        category="consensus",
        content="Very old perspective content.",
        source_articles=["article-1"],
        confidence=0.5,
        generated_at=datetime.now() - timedelta(days=7),
    )


# =============================================================================
# Fixtures for Perspective Configuration
# =============================================================================


@pytest.fixture
def default_perspective_config():
    """Create a default perspective configuration."""
    return {
        'enabled_categories': list(PERSPECTIVE_CATEGORIES.keys()),
        'default_categories': DEFAULT_CATEGORIES,
        'category_order': list(PERSPECTIVE_CATEGORIES.keys()),
    }


@pytest.fixture
def custom_perspective_config():
    """Create a custom perspective configuration."""
    return {
        'enabled_categories': ['consensus', 'contested', 'gaps', 'tech-industry'],
        'default_categories': ['consensus', 'gaps'],
        'category_order': ['consensus', 'gaps', 'contested', 'tech-industry'],
    }


@pytest.fixture
def minimal_perspective_config():
    """Create a minimal perspective configuration."""
    return {
        'enabled_categories': ['consensus'],
        'default_categories': ['consensus'],
        'category_order': ['consensus'],
    }


@pytest.fixture
def fun_perspective_config():
    """Create a fun/entertainment perspective configuration."""
    return {
        'enabled_categories': ['spiciest-takes', 'unhinged-speculation', 'doom', 'hype'],
        'default_categories': ['spiciest-takes', 'doom', 'hype'],
        'category_order': ['spiciest-takes', 'unhinged-speculation', 'doom', 'hype'],
    }


# =============================================================================
# Fixtures for Category Lists
# =============================================================================


@pytest.fixture
def all_category_ids():
    """Return all valid category IDs."""
    return list(PERSPECTIVE_CATEGORIES.keys())


@pytest.fixture
def factual_categories():
    """Return factual perspective categories."""
    return ['consensus', 'contested', 'gaps', 'timeline']


@pytest.fixture
def framing_categories():
    """Return source framing perspective categories."""
    return ['tech-industry', 'mainstream', 'financial', 'political', 'academic']


@pytest.fixture
def fun_categories():
    """Return fun/entertainment perspective categories."""
    return ['spiciest-takes', 'unhinged-speculation', 'contrarian', 'doom', 'hype']


@pytest.fixture
def analysis_categories():
    """Return analysis perspective categories."""
    return ['expert-quotes', 'prediction-track-record']


@pytest.fixture
def categories_requiring_two_sources():
    """Return categories that require at least 2 sources."""
    return ['consensus', 'contested', 'prediction-track-record']


@pytest.fixture
def categories_requiring_one_source():
    """Return categories that require only 1 source."""
    return [
        cat for cat, info in PERSPECTIVE_CATEGORIES.items()
        if info.get('min_sources', 1) == 1
    ]


# =============================================================================
# Fixtures for Error Scenarios
# =============================================================================


@pytest.fixture
def invalid_category_id():
    """Return an invalid category ID."""
    return "nonexistent-category"


@pytest.fixture
def empty_string_category():
    """Return an empty string category."""
    return ""


# =============================================================================
# Fixtures for Synthesis Testing
# =============================================================================


@pytest.fixture
def synthesis_request_consensus(article_cluster_two_sources):
    """Create a synthesis request for consensus perspective."""
    return {
        'category': 'consensus',
        'articles': article_cluster_two_sources,
    }


@pytest.fixture
def synthesis_request_contested(article_cluster_diverse):
    """Create a synthesis request for contested perspective."""
    return {
        'category': 'contested',
        'articles': article_cluster_diverse,
    }


@pytest.fixture
def synthesis_request_gaps(sample_article):
    """Create a synthesis request for gaps perspective."""
    return {
        'category': 'gaps',
        'articles': [sample_article],
    }


# =============================================================================
# Fixtures for Integration Testing
# =============================================================================


@pytest.fixture
def full_perspective_setup(temp_db, mock_llm_provider_verbose):
    """Create a full setup for perspective synthesis integration testing."""
    store = Storage(temp_db)

    # Create articles from different sources
    articles = [
        Article(
            id="int-article-1",
            feed_url="https://tech.example.com/feed.xml",
            title="Tech Source: AI Makes Breakthrough",
            link="https://tech.example.com/ai",
            published=datetime.now() - timedelta(hours=1),
            content="From a technology perspective, the AI breakthrough is significant. Technical details here.",
            summary="Tech perspective on AI.",
            story_id="int-story-1",
        ),
        Article(
            id="int-article-2",
            feed_url="https://business.example.com/feed.xml",
            title="Business Source: AI Investment Grows",
            link="https://business.example.com/ai",
            published=datetime.now() - timedelta(hours=2),
            content="From a business perspective, AI investment is growing rapidly. Financial impact discussed.",
            summary="Business perspective on AI.",
            story_id="int-story-1",
        ),
        Article(
            id="int-article-3",
            feed_url="https://policy.example.com/feed.xml",
            title="Policy Source: AI Regulations Debated",
            link="https://policy.example.com/ai",
            published=datetime.now() - timedelta(hours=3),
            content="From a policy perspective, AI regulations are being debated. Government response analyzed.",
            summary="Policy perspective on AI.",
            story_id="int-story-1",
        ),
    ]

    story = Story(
        id="int-story-1",
        title="AI Development Multi-Perspective Coverage",
        description="Coverage from tech, business, and policy perspectives",
        keywords=["AI", "technology", "business", "policy"],
        first_seen=datetime.now() - timedelta(hours=3),
        last_updated=datetime.now() - timedelta(hours=1),
        lifecycle_state="developing",
        article_ids=["int-article-1", "int-article-2", "int-article-3"],
        news_item_ids=[],
    )

    for article in articles:
        store.save_article(article)
    store.save_story(story)

    return {
        'storage': store,
        'llm_provider': mock_llm_provider_verbose,
        'story_id': "int-story-1",
        'articles': articles,
    }


@pytest.fixture
def perspective_synthesis_mocks(mock_storage_with_articles, mock_llm_provider_verbose):
    """Create combined mocks for perspective synthesis testing."""
    return {
        'storage': mock_storage_with_articles,
        'llm_provider': mock_llm_provider_verbose,
    }


# =============================================================================
# Fixtures for Edge Cases
# =============================================================================


@pytest.fixture
def article_with_no_url_parts():
    """Create an article with a simple feed URL (no slashes)."""
    return Article(
        id="no-url-parts-1",
        feed_url="simple-feed",
        title="Simple Feed Article",
        link="simple-feed/article",
        published=datetime.now(),
        content="Article from a simple feed URL.",
        summary="Simple feed.",
    )


@pytest.fixture
def article_with_none_content():
    """Create an article with None content."""
    return Article(
        id="none-content-1",
        feed_url="https://example.com/feed.xml",
        title="Article With None Content",
        link="https://example.com/none-content",
        published=datetime.now(),
        content=None,
        summary="None content article.",
    )


@pytest.fixture
def perspective_with_none_generated_at():
    """Create a perspective with None generated_at."""
    return Perspective(
        category="consensus",
        content="Perspective without timestamp.",
        source_articles=["article-1"],
        confidence=0.5,
        generated_at=None,
    )


@pytest.fixture
def empty_synthesis_result():
    """Create an empty synthesis result."""
    return ""


@pytest.fixture
def whitespace_synthesis_result():
    """Create a whitespace-only synthesis result."""
    return "   \n\t  "


# =============================================================================
# Fixtures for Confidence Estimation Testing
# =============================================================================


@pytest.fixture
def high_confidence_synthesis():
    """Create a long, structured synthesis result for high confidence."""
    return (
        "Comprehensive analysis of the situation:\n\n"
        "- Point 1: All sources agree on the fundamental aspects.\n"
        "- Point 2: Clear consensus on the timeline.\n"
        "- Point 3: Agreement on the key stakeholders involved.\n"
        "- Point 4: Consistent reporting of the main facts.\n\n"
        "In conclusion, there is strong agreement across all sources."
    )


@pytest.fixture
def low_confidence_synthesis():
    """Create a short synthesis result for low confidence."""
    return "Brief analysis."


@pytest.fixture
def uncertain_synthesis():
    """Create a synthesis with uncertainty markers."""
    return (
        "The situation is unclear from the available sources.\n"
        "There is insufficient information to draw conclusions.\n"
        "Many details are unknown at this time."
    )


@pytest.fixture
def structured_synthesis():
    """Create a well-structured synthesis with bullet points."""
    return (
        "Key findings:\n"
        "• Finding 1\n"
        "• Finding 2\n"
        "• Finding 3\n"
        "- Additional point 1\n"
        "- Additional point 2"
    )


# =============================================================================
# Fixtures for Prompt Building Testing
# =============================================================================


@pytest.fixture
def prompt_test_articles():
    """Create articles specifically for prompt building tests."""
    return [
        Article(
            id="prompt-test-1",
            feed_url="https://source1.example.com/rss/feed.xml",
            title="First Source Title",
            link="https://source1.example.com/article",
            published=datetime.now(),
            content="First source content for prompt testing. " * 50,
            summary="First source summary.",
        ),
        Article(
            id="prompt-test-2",
            feed_url="https://source2.example.com/api/feed.xml",
            title="Second Source Title",
            link="https://source2.example.com/article",
            published=datetime.now(),
            content="Second source content for prompt testing. " * 50,
            summary="Second source summary.",
        ),
    ]


# =============================================================================
# Tests for PERSPECTIVE_CATEGORIES Structure
# =============================================================================


class TestPerspectiveCategoriesStructure:
    """Tests for PERSPECTIVE_CATEGORIES dictionary structure."""

    def test_perspective_categories_is_dict(self):
        """Test that PERSPECTIVE_CATEGORIES is a dictionary."""
        assert isinstance(PERSPECTIVE_CATEGORIES, dict)

    def test_perspective_categories_not_empty(self):
        """Test that PERSPECTIVE_CATEGORIES is not empty."""
        assert len(PERSPECTIVE_CATEGORIES) > 0

    def test_perspective_categories_count(self):
        """Test that PERSPECTIVE_CATEGORIES has expected number of categories."""
        # Based on source code: 16 categories defined
        assert len(PERSPECTIVE_CATEGORIES) == 16

    def test_all_categories_have_required_keys(self):
        """Test that each category has all required keys."""
        required_keys = {'name', 'description', 'min_sources'}
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            assert isinstance(category_info, dict), f"Category '{category_id}' is not a dict"
            missing_keys = required_keys - set(category_info.keys())
            assert not missing_keys, f"Category '{category_id}' missing keys: {missing_keys}"

    def test_all_category_ids_are_strings(self):
        """Test that all category IDs are non-empty strings."""
        for category_id in PERSPECTIVE_CATEGORIES.keys():
            assert isinstance(category_id, str), f"Category ID '{category_id}' is not a string"
            assert len(category_id) > 0, "Found empty category ID"

    def test_all_category_names_are_strings(self):
        """Test that all category names are non-empty strings."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            name = category_info.get('name')
            assert isinstance(name, str), f"Category '{category_id}' name is not a string"
            assert len(name) > 0, f"Category '{category_id}' has empty name"

    def test_all_category_descriptions_are_strings(self):
        """Test that all category descriptions are non-empty strings."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            description = category_info.get('description')
            assert isinstance(description, str), f"Category '{category_id}' description is not a string"
            assert len(description) > 0, f"Category '{category_id}' has empty description"

    def test_all_min_sources_are_positive_integers(self):
        """Test that all min_sources values are positive integers."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            min_sources = category_info.get('min_sources')
            assert isinstance(min_sources, int), f"Category '{category_id}' min_sources is not an int"
            assert min_sources > 0, f"Category '{category_id}' min_sources must be positive"


class TestPerspectiveCategoriesContent:
    """Tests for PERSPECTIVE_CATEGORIES content and values."""

    def test_factual_categories_exist(self):
        """Test that all factual categories are defined."""
        factual_cats = ['consensus', 'contested', 'gaps', 'timeline']
        for cat in factual_cats:
            assert cat in PERSPECTIVE_CATEGORIES, f"Factual category '{cat}' not found"

    def test_framing_categories_exist(self):
        """Test that all source framing categories are defined."""
        framing_cats = ['tech-industry', 'mainstream', 'financial', 'political', 'academic']
        for cat in framing_cats:
            assert cat in PERSPECTIVE_CATEGORIES, f"Framing category '{cat}' not found"

    def test_fun_categories_exist(self):
        """Test that all fun/entertainment categories are defined."""
        fun_cats = ['spiciest-takes', 'unhinged-speculation', 'contrarian', 'doom', 'hype']
        for cat in fun_cats:
            assert cat in PERSPECTIVE_CATEGORIES, f"Fun category '{cat}' not found"

    def test_analysis_categories_exist(self):
        """Test that all analysis categories are defined."""
        analysis_cats = ['expert-quotes', 'prediction-track-record']
        for cat in analysis_cats:
            assert cat in PERSPECTIVE_CATEGORIES, f"Analysis category '{cat}' not found"

    def test_category_names_are_human_readable(self):
        """Test that category names are properly formatted (title case, no hyphens)."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            name = category_info['name']
            # Name should not contain underscores or hyphens
            assert '-' not in name or name == name.replace('-', ' ').title().replace(' ', '-'), \
                f"Category '{category_id}' name '{name}' should be human-readable"

    def test_consensus_category_content(self):
        """Test consensus category has correct content."""
        assert 'consensus' in PERSPECTIVE_CATEGORIES
        cat = PERSPECTIVE_CATEGORIES['consensus']
        assert cat['name'] == 'Consensus'
        assert 'agree' in cat['description'].lower()

    def test_contested_category_content(self):
        """Test contested category has correct content."""
        assert 'contested' in PERSPECTIVE_CATEGORIES
        cat = PERSPECTIVE_CATEGORIES['contested']
        assert cat['name'] == 'Contested'
        assert 'disagree' in cat['description'].lower()

    def test_gaps_category_content(self):
        """Test gaps category has correct content."""
        assert 'gaps' in PERSPECTIVE_CATEGORIES
        cat = PERSPECTIVE_CATEGORIES['gaps']
        assert cat['name'] == 'Gaps'
        assert 'covering' in cat['description'].lower() or 'not' in cat['description'].lower()


class TestMinSourcesRequirements:
    """Tests for min_sources requirements across categories."""

    def test_min_sources_values_are_one_or_two(self):
        """Test that min_sources values are either 1 or 2."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            min_sources = category_info['min_sources']
            assert min_sources in (1, 2), \
                f"Category '{category_id}' has unexpected min_sources value: {min_sources}"

    def test_consensus_requires_two_sources(self):
        """Test that consensus category requires at least 2 sources."""
        assert PERSPECTIVE_CATEGORIES['consensus']['min_sources'] == 2

    def test_contested_requires_two_sources(self):
        """Test that contested category requires at least 2 sources."""
        assert PERSPECTIVE_CATEGORIES['contested']['min_sources'] == 2

    def test_prediction_track_record_requires_two_sources(self):
        """Test that prediction-track-record category requires at least 2 sources."""
        assert PERSPECTIVE_CATEGORIES['prediction-track-record']['min_sources'] == 2

    def test_gaps_requires_one_source(self):
        """Test that gaps category requires only 1 source."""
        assert PERSPECTIVE_CATEGORIES['gaps']['min_sources'] == 1

    def test_timeline_requires_one_source(self):
        """Test that timeline category requires only 1 source."""
        assert PERSPECTIVE_CATEGORIES['timeline']['min_sources'] == 1

    def test_categories_requiring_two_sources_list(self):
        """Test the list of categories requiring 2 sources."""
        two_source_cats = [
            cat_id for cat_id, info in PERSPECTIVE_CATEGORIES.items()
            if info['min_sources'] == 2
        ]
        expected = ['consensus', 'contested', 'prediction-track-record']
        assert sorted(two_source_cats) == sorted(expected)

    def test_categories_requiring_one_source_list(self):
        """Test the list of categories requiring only 1 source."""
        one_source_cats = [
            cat_id for cat_id, info in PERSPECTIVE_CATEGORIES.items()
            if info['min_sources'] == 1
        ]
        # Should be all categories except consensus, contested, prediction-track-record
        expected_count = len(PERSPECTIVE_CATEGORIES) - 3  # 16 - 3 = 13
        assert len(one_source_cats) == expected_count

    def test_framing_categories_require_one_source(self):
        """Test that all framing categories require only 1 source."""
        framing_cats = ['tech-industry', 'mainstream', 'financial', 'political', 'academic']
        for cat_id in framing_cats:
            assert PERSPECTIVE_CATEGORIES[cat_id]['min_sources'] == 1, \
                f"Framing category '{cat_id}' should require only 1 source"

    def test_fun_categories_require_one_source(self):
        """Test that all fun categories require only 1 source."""
        fun_cats = ['spiciest-takes', 'unhinged-speculation', 'contrarian', 'doom', 'hype']
        for cat_id in fun_cats:
            assert PERSPECTIVE_CATEGORIES[cat_id]['min_sources'] == 1, \
                f"Fun category '{cat_id}' should require only 1 source"

    def test_expert_quotes_requires_one_source(self):
        """Test that expert-quotes category requires only 1 source."""
        assert PERSPECTIVE_CATEGORIES['expert-quotes']['min_sources'] == 1


class TestMinSourcesRationale:
    """Tests for the rationale behind min_sources requirements."""

    def test_consensus_needs_multiple_sources_for_agreement(self):
        """Test that consensus logically requires multiple sources to find agreement."""
        # Consensus by definition requires comparing multiple sources
        min_sources = PERSPECTIVE_CATEGORIES['consensus']['min_sources']
        assert min_sources >= 2, "Consensus requires at least 2 sources to find agreement"

    def test_contested_needs_multiple_sources_for_disagreement(self):
        """Test that contested logically requires multiple sources to find disagreement."""
        # Disagreement by definition requires comparing multiple sources
        min_sources = PERSPECTIVE_CATEGORIES['contested']['min_sources']
        assert min_sources >= 2, "Contested requires at least 2 sources to find disagreement"

    def test_prediction_track_record_needs_multiple_sources(self):
        """Test that prediction-track-record needs multiple sources for comparison."""
        # Comparing predictions requires multiple data points
        min_sources = PERSPECTIVE_CATEGORIES['prediction-track-record']['min_sources']
        assert min_sources >= 2, "Prediction track record requires multiple sources for comparison"

    def test_single_source_categories_can_extract_from_one(self):
        """Test that single-source categories can meaningfully analyze just one article."""
        single_source_cats = ['gaps', 'timeline', 'spiciest-takes', 'expert-quotes']
        for cat_id in single_source_cats:
            assert PERSPECTIVE_CATEGORIES[cat_id]['min_sources'] == 1, \
                f"'{cat_id}' can be derived from a single article"


class TestDefaultCategories:
    """Tests for DEFAULT_CATEGORIES configuration."""

    def test_default_categories_is_list(self):
        """Test that DEFAULT_CATEGORIES is a list."""
        assert isinstance(DEFAULT_CATEGORIES, list)

    def test_default_categories_not_empty(self):
        """Test that DEFAULT_CATEGORIES is not empty."""
        assert len(DEFAULT_CATEGORIES) > 0

    def test_default_categories_count(self):
        """Test that DEFAULT_CATEGORIES has expected number of categories."""
        # Based on source code: ['consensus', 'contested', 'gaps']
        assert len(DEFAULT_CATEGORIES) == 3

    def test_default_categories_are_valid_category_ids(self):
        """Test that all default categories exist in PERSPECTIVE_CATEGORIES."""
        for cat_id in DEFAULT_CATEGORIES:
            assert cat_id in PERSPECTIVE_CATEGORIES, \
                f"Default category '{cat_id}' not found in PERSPECTIVE_CATEGORIES"

    def test_default_categories_are_strings(self):
        """Test that all default category IDs are strings."""
        for cat_id in DEFAULT_CATEGORIES:
            assert isinstance(cat_id, str), f"Default category '{cat_id}' is not a string"

    def test_default_categories_contain_consensus(self):
        """Test that consensus is in default categories."""
        assert 'consensus' in DEFAULT_CATEGORIES

    def test_default_categories_contain_contested(self):
        """Test that contested is in default categories."""
        assert 'contested' in DEFAULT_CATEGORIES

    def test_default_categories_contain_gaps(self):
        """Test that gaps is in default categories."""
        assert 'gaps' in DEFAULT_CATEGORIES

    def test_default_categories_exact_list(self):
        """Test that DEFAULT_CATEGORIES matches expected list."""
        expected = ['consensus', 'contested', 'gaps']
        assert DEFAULT_CATEGORIES == expected

    def test_default_categories_are_factual(self):
        """Test that default categories are from the factual category group."""
        factual_cats = ['consensus', 'contested', 'gaps', 'timeline']
        for cat_id in DEFAULT_CATEGORIES:
            assert cat_id in factual_cats, \
                f"Default category '{cat_id}' is not a factual category"


class TestDefaultCategoriesRationale:
    """Tests for the rationale behind default category selection."""

    def test_defaults_provide_balanced_view(self):
        """Test that default categories provide agreement, disagreement, and missing info."""
        # consensus - what sources agree on
        # contested - what sources disagree on
        # gaps - what no one is covering
        assert 'consensus' in DEFAULT_CATEGORIES  # Agreement
        assert 'contested' in DEFAULT_CATEGORIES  # Disagreement
        assert 'gaps' in DEFAULT_CATEGORIES  # Missing coverage

    def test_defaults_include_single_and_multi_source(self):
        """Test that defaults include categories with different source requirements."""
        requirements = [
            PERSPECTIVE_CATEGORIES[cat_id]['min_sources']
            for cat_id in DEFAULT_CATEGORIES
        ]
        # Should have at least one category requiring 2 sources
        assert 2 in requirements
        # Should have at least one category requiring 1 source
        assert 1 in requirements

    def test_defaults_are_most_useful_for_news_analysis(self):
        """Test that defaults are the most useful categories for general news analysis."""
        # These are arguably the most universally useful perspectives
        essential_perspectives = ['consensus', 'contested', 'gaps']
        for perspective in essential_perspectives:
            assert perspective in DEFAULT_CATEGORIES


class TestCategoryIdsFormat:
    """Tests for category ID format and naming conventions."""

    def test_all_category_ids_are_lowercase(self):
        """Test that all category IDs use lowercase letters."""
        for category_id in PERSPECTIVE_CATEGORIES.keys():
            assert category_id == category_id.lower(), \
                f"Category ID '{category_id}' should be lowercase"

    def test_category_ids_use_hyphen_separator(self):
        """Test that multi-word category IDs use hyphen as separator."""
        for category_id in PERSPECTIVE_CATEGORIES.keys():
            # Should not contain spaces or underscores
            assert ' ' not in category_id, f"Category ID '{category_id}' should not contain spaces"
            assert '_' not in category_id, f"Category ID '{category_id}' should not contain underscores"

    def test_category_ids_are_kebab_case(self):
        """Test that multi-word category IDs are in kebab-case."""
        multi_word_cats = [cat_id for cat_id in PERSPECTIVE_CATEGORIES.keys() if '-' in cat_id]
        for cat_id in multi_word_cats:
            # Each part should be lowercase
            parts = cat_id.split('-')
            for part in parts:
                assert part == part.lower(), f"Category '{cat_id}' part '{part}' should be lowercase"
                assert part.isalpha() or part.isalnum(), f"Category '{cat_id}' has invalid part '{part}'"

    def test_no_duplicate_category_ids(self):
        """Test that there are no duplicate category IDs."""
        ids = list(PERSPECTIVE_CATEGORIES.keys())
        assert len(ids) == len(set(ids)), "Found duplicate category IDs"


class TestCategoryGroupings:
    """Tests for category groupings and organization."""

    def test_factual_categories_are_four(self):
        """Test that there are exactly 4 factual categories."""
        factual = ['consensus', 'contested', 'gaps', 'timeline']
        for cat_id in factual:
            assert cat_id in PERSPECTIVE_CATEGORIES
        # Verify these are the expected factual categories based on source comments

    def test_framing_categories_are_five(self):
        """Test that there are exactly 5 source framing categories."""
        framing = ['tech-industry', 'mainstream', 'financial', 'political', 'academic']
        for cat_id in framing:
            assert cat_id in PERSPECTIVE_CATEGORIES
        assert len(framing) == 5

    def test_fun_categories_are_five(self):
        """Test that there are exactly 5 fun/entertainment categories."""
        fun = ['spiciest-takes', 'unhinged-speculation', 'contrarian', 'doom', 'hype']
        for cat_id in fun:
            assert cat_id in PERSPECTIVE_CATEGORIES
        assert len(fun) == 5

    def test_analysis_categories_are_two(self):
        """Test that there are exactly 2 analysis categories."""
        analysis = ['expert-quotes', 'prediction-track-record']
        for cat_id in analysis:
            assert cat_id in PERSPECTIVE_CATEGORIES
        assert len(analysis) == 2

    def test_all_groupings_cover_all_categories(self):
        """Test that groupings cover all defined categories."""
        factual = {'consensus', 'contested', 'gaps', 'timeline'}
        framing = {'tech-industry', 'mainstream', 'financial', 'political', 'academic'}
        fun = {'spiciest-takes', 'unhinged-speculation', 'contrarian', 'doom', 'hype'}
        analysis = {'expert-quotes', 'prediction-track-record'}

        all_grouped = factual | framing | fun | analysis
        all_categories = set(PERSPECTIVE_CATEGORIES.keys())

        assert all_grouped == all_categories, \
            f"Ungrouped categories: {all_categories - all_grouped}"


class TestCategoryDescriptions:
    """Tests for category description quality."""

    def test_descriptions_are_concise(self):
        """Test that descriptions are concise (under 50 characters)."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            description = category_info['description']
            assert len(description) <= 50, \
                f"Category '{category_id}' description is too long: {len(description)} chars"

    def test_descriptions_are_meaningful(self):
        """Test that descriptions are at least 10 characters (meaningful)."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            description = category_info['description']
            assert len(description) >= 10, \
                f"Category '{category_id}' description is too short: '{description}'"

    def test_descriptions_do_not_end_with_period(self):
        """Test that descriptions don't end with a period (consistent style)."""
        for category_id, category_info in PERSPECTIVE_CATEGORIES.items():
            description = category_info['description']
            # This is a style check - descriptions should be sentence fragments
            assert not description.endswith('.'), \
                f"Category '{category_id}' description ends with period: '{description}'"


class TestCategoryEdgeCases:
    """Tests for edge cases in category handling."""

    def test_unknown_category_not_in_dict(self):
        """Test that accessing unknown category returns None or raises KeyError."""
        assert 'nonexistent-category' not in PERSPECTIVE_CATEGORIES

    def test_empty_string_not_valid_category(self):
        """Test that empty string is not a valid category."""
        assert '' not in PERSPECTIVE_CATEGORIES

    def test_none_not_valid_category(self):
        """Test that None is not a valid category key."""
        assert None not in PERSPECTIVE_CATEGORIES

    def test_category_lookup_case_sensitive(self):
        """Test that category lookup is case-sensitive."""
        # 'Consensus' (capitalized) should not be found
        assert 'Consensus' not in PERSPECTIVE_CATEGORIES
        assert 'CONSENSUS' not in PERSPECTIVE_CATEGORIES
        # 'consensus' (lowercase) should be found
        assert 'consensus' in PERSPECTIVE_CATEGORIES

    def test_category_with_extra_spaces_not_found(self):
        """Test that category with extra spaces is not found."""
        assert ' consensus' not in PERSPECTIVE_CATEGORIES
        assert 'consensus ' not in PERSPECTIVE_CATEGORIES
        assert ' consensus ' not in PERSPECTIVE_CATEGORIES


class TestCategoryUsageWithFixtures:
    """Tests for category usage with test fixtures."""

    def test_all_category_ids_fixture_matches(self, all_category_ids):
        """Test that all_category_ids fixture matches actual categories."""
        assert set(all_category_ids) == set(PERSPECTIVE_CATEGORIES.keys())

    def test_categories_requiring_two_sources_fixture(self, categories_requiring_two_sources):
        """Test that fixture for two-source categories is accurate."""
        for cat_id in categories_requiring_two_sources:
            assert PERSPECTIVE_CATEGORIES[cat_id]['min_sources'] == 2

    def test_categories_requiring_one_source_fixture(self, categories_requiring_one_source):
        """Test that fixture for one-source categories is accurate."""
        for cat_id in categories_requiring_one_source:
            assert PERSPECTIVE_CATEGORIES[cat_id]['min_sources'] == 1

    def test_factual_categories_fixture(self, factual_categories):
        """Test that factual_categories fixture contains valid categories."""
        for cat_id in factual_categories:
            assert cat_id in PERSPECTIVE_CATEGORIES

    def test_framing_categories_fixture(self, framing_categories):
        """Test that framing_categories fixture contains valid categories."""
        for cat_id in framing_categories:
            assert cat_id in PERSPECTIVE_CATEGORIES

    def test_fun_categories_fixture(self, fun_categories):
        """Test that fun_categories fixture contains valid categories."""
        for cat_id in fun_categories:
            assert cat_id in PERSPECTIVE_CATEGORIES

    def test_analysis_categories_fixture(self, analysis_categories):
        """Test that analysis_categories fixture contains valid categories."""
        for cat_id in analysis_categories:
            assert cat_id in PERSPECTIVE_CATEGORIES


class TestCategoryIntegration:
    """Integration tests for category definitions with other functions."""

    def test_synthesize_perspective_accepts_all_categories(self, sample_article):
        """Test that synthesize_perspective accepts all defined categories."""
        from src.perspectives import synthesize_perspective

        for category_id in PERSPECTIVE_CATEGORIES.keys():
            min_sources = PERSPECTIVE_CATEGORIES[category_id]['min_sources']
            articles = [sample_article] * min_sources  # Provide enough articles

            # Should not raise CategoryNotApplicableError
            try:
                perspective = synthesize_perspective(
                    category=category_id,
                    articles=articles,
                    llm_provider=None,  # Will use fallback
                )
                assert perspective is not None
                assert perspective.category == category_id
            except InsufficientSourcesError:
                # This is expected if we don't have enough sources
                pass
            except CategoryNotApplicableError:
                pytest.fail(f"Category '{category_id}' should be valid")

    def test_build_perspective_prompt_handles_all_categories(self, prompt_test_articles):
        """Test that build_perspective_prompt handles all defined categories."""
        from src.perspectives import build_perspective_prompt

        for category_id in PERSPECTIVE_CATEGORIES.keys():
            prompt = build_perspective_prompt(category_id, prompt_test_articles)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_estimate_confidence_uses_min_sources(self, article_cluster_diverse):
        """Test that estimate_confidence uses min_sources from category definitions."""
        from src.perspectives import estimate_confidence

        # Category with min_sources=2
        confidence_2 = estimate_confidence('consensus', "Some synthesis", article_cluster_diverse)

        # Category with min_sources=1
        confidence_1 = estimate_confidence('gaps', "Some synthesis", article_cluster_diverse)

        # Both should return valid confidence scores
        assert 0 <= confidence_2 <= 1
        assert 0 <= confidence_1 <= 1

    def test_default_categories_work_with_synthesize_perspectives(self, mock_storage_with_articles):
        """Test that DEFAULT_CATEGORIES work with synthesize_perspectives."""
        from src.perspectives import synthesize_perspectives

        perspectives = synthesize_perspectives(
            cluster_id="mock-story-1",
            categories=DEFAULT_CATEGORIES,
            storage=mock_storage_with_articles,
            llm_provider=None,  # Will use fallback
        )

        # Should return perspectives for all requested categories
        assert isinstance(perspectives, dict)
        for cat_id in DEFAULT_CATEGORIES:
            assert cat_id in perspectives


# =============================================================================
# Tests for build_perspective_prompt Function
# =============================================================================


class TestBuildPerspectivePromptBasic:
    """Basic tests for build_perspective_prompt function."""

    def test_returns_string(self, sample_article):
        """Test that build_perspective_prompt returns a string."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        assert isinstance(prompt, str)

    def test_returns_non_empty_string(self, sample_article):
        """Test that build_perspective_prompt returns a non-empty string."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        assert len(prompt) > 0

    def test_prompt_contains_article_title(self, sample_article):
        """Test that the prompt contains the article title."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        assert sample_article.title in prompt

    def test_prompt_contains_article_content(self, sample_article):
        """Test that the prompt contains article content."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        # Content is truncated to 500 chars, so check for part of it
        assert sample_article.content[:100] in prompt

    def test_prompt_contains_article_number(self, sample_article):
        """Test that the prompt includes article numbering."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        assert '[Article 1' in prompt

    def test_prompt_works_with_empty_articles_list(self):
        """Test that build_perspective_prompt handles empty articles list."""
        prompt = build_perspective_prompt('consensus', [])
        assert isinstance(prompt, str)
        # Should still return a prompt structure

    def test_prompt_handles_multiple_articles(self, article_cluster_tech_news):
        """Test that prompt handles multiple articles correctly."""
        prompt = build_perspective_prompt('consensus', article_cluster_tech_news)
        assert '[Article 1' in prompt
        assert '[Article 2' in prompt
        assert '[Article 3' in prompt

    def test_each_category_returns_different_prompt(self, sample_article):
        """Test that different categories produce different prompts."""
        prompt_consensus = build_perspective_prompt('consensus', [sample_article])
        prompt_contested = build_perspective_prompt('contested', [sample_article])
        prompt_gaps = build_perspective_prompt('gaps', [sample_article])

        # Each should have different instructions
        assert prompt_consensus != prompt_contested
        assert prompt_contested != prompt_gaps
        assert prompt_consensus != prompt_gaps


class TestBuildPerspectivePromptArticleExtraction:
    """Tests for article information extraction in prompts."""

    def test_extracts_source_from_feed_url(self, sample_article):
        """Test that source is extracted from feed_url."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        # feed_url is "https://example.com/feed.xml", source should be "example.com"
        assert 'example.com' in prompt

    def test_extracts_source_from_complex_url(self):
        """Test source extraction from complex feed URLs."""
        article = Article(
            id="test-1",
            feed_url="https://subdomain.example.com/path/to/feed.xml",
            title="Test Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="Test content.",
            summary="Test summary.",
        )
        prompt = build_perspective_prompt('consensus', [article])
        assert 'subdomain.example.com' in prompt

    def test_handles_feed_url_without_slashes(self, article_with_no_url_parts):
        """Test handling of feed URL without standard URL structure."""
        prompt = build_perspective_prompt('consensus', [article_with_no_url_parts])
        # Should use the feed_url as-is if no slashes
        assert 'simple-feed' in prompt

    def test_includes_title_label(self, sample_article):
        """Test that prompt includes 'Title:' label."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        assert 'Title:' in prompt

    def test_includes_content_label(self, sample_article):
        """Test that prompt includes 'Content:' label."""
        prompt = build_perspective_prompt('consensus', [sample_article])
        assert 'Content:' in prompt

    def test_separates_articles_with_newlines(self, article_cluster_two_sources):
        """Test that multiple articles are separated properly."""
        prompt = build_perspective_prompt('consensus', article_cluster_two_sources)
        # Articles should be separated by double newlines
        assert '\n\n' in prompt


class TestBuildPerspectivePromptContentTruncation:
    """Tests for content truncation behavior in prompts."""

    def test_truncates_long_content(self, sample_article_very_long):
        """Test that very long content is truncated."""
        prompt = build_perspective_prompt('consensus', [sample_article_very_long])
        # Content should be truncated to 500 chars + "..."
        # The full content would make the prompt very long

        # Count how many times the repeated phrase appears
        repeated_phrase = "This is a very detailed article about AI technology. "
        original_count = sample_article_very_long.content.count(repeated_phrase)
        prompt_count = prompt.count(repeated_phrase)

        # Prompt should have fewer occurrences due to truncation
        assert prompt_count < original_count

    def test_adds_ellipsis_after_truncation(self, sample_article_very_long):
        """Test that truncated content ends with ellipsis."""
        prompt = build_perspective_prompt('consensus', [sample_article_very_long])
        # The content section should include "..."
        assert '...' in prompt

    def test_short_content_not_truncated(self):
        """Test that short content is not truncated."""
        short_article = Article(
            id="short-1",
            feed_url="https://example.com/feed.xml",
            title="Short Article",
            link="https://example.com/short",
            published=datetime.now(),
            content="This is a short article.",  # Less than 500 chars
            summary="Short summary.",
        )
        prompt = build_perspective_prompt('consensus', [short_article])
        assert "This is a short article." in prompt

    def test_exactly_500_char_content(self):
        """Test handling of exactly 500 character content."""
        content_500 = "A" * 500
        article = Article(
            id="exact-500",
            feed_url="https://example.com/feed.xml",
            title="Exact 500 Content",
            link="https://example.com/exact",
            published=datetime.now(),
            content=content_500,
            summary="Exactly 500 chars.",
        )
        prompt = build_perspective_prompt('consensus', [article])
        # Should include all 500 chars followed by "..."
        assert content_500 in prompt


class TestBuildPerspectivePromptSourceExtraction:
    """Tests for source extraction from feed URLs."""

    def test_extracts_domain_from_https_url(self):
        """Test domain extraction from HTTPS URL."""
        article = Article(
            id="https-1",
            feed_url="https://techcrunch.com/feed.xml",
            title="Test",
            link="https://example.com",
            published=datetime.now(),
            content="Content",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        assert 'techcrunch.com' in prompt

    def test_extracts_domain_from_http_url(self):
        """Test domain extraction from HTTP URL."""
        article = Article(
            id="http-1",
            feed_url="http://legacy.example.com/rss",
            title="Test",
            link="https://example.com",
            published=datetime.now(),
            content="Content",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        assert 'legacy.example.com' in prompt

    def test_handles_url_with_port(self):
        """Test handling of URL with port number."""
        article = Article(
            id="port-1",
            feed_url="https://localhost:8080/feed.xml",
            title="Test",
            link="https://example.com",
            published=datetime.now(),
            content="Content",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        # Source extraction uses split('/')[2] which would get "localhost:8080"
        assert 'localhost' in prompt

    def test_handles_url_with_path(self):
        """Test handling of URL with deep path."""
        article = Article(
            id="path-1",
            feed_url="https://example.com/blog/rss/feed.xml",
            title="Test",
            link="https://example.com",
            published=datetime.now(),
            content="Content",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        # Source should be the domain only
        assert 'example.com' in prompt

    def test_multiple_sources_labeled_correctly(self, article_cluster_diverse):
        """Test that multiple sources are labeled with correct numbers."""
        prompt = build_perspective_prompt('consensus', article_cluster_diverse)

        # Check all 5 articles are numbered
        for i in range(1, 6):
            assert f'[Article {i}' in prompt


class TestBuildPerspectivePromptFactualCategories:
    """Tests for factual category prompts (consensus, contested, gaps, timeline)."""

    def test_consensus_prompt_contains_agreement_keywords(self, article_cluster_two_sources):
        """Test that consensus prompt asks about agreement."""
        prompt = build_perspective_prompt('consensus', article_cluster_two_sources)
        prompt_lower = prompt.lower()
        assert 'agree' in prompt_lower or 'agreement' in prompt_lower or 'consensus' in prompt_lower

    def test_consensus_prompt_mentions_all_sources(self, article_cluster_two_sources):
        """Test that consensus prompt references all sources."""
        prompt = build_perspective_prompt('consensus', article_cluster_two_sources)
        assert 'all sources' in prompt.lower() or 'all articles' in prompt.lower()

    def test_contested_prompt_contains_disagreement_keywords(self, article_cluster_two_sources):
        """Test that contested prompt asks about disagreement."""
        prompt = build_perspective_prompt('contested', article_cluster_two_sources)
        prompt_lower = prompt.lower()
        assert 'disagree' in prompt_lower or 'contest' in prompt_lower or 'differ' in prompt_lower

    def test_contested_prompt_asks_which_sources(self, article_cluster_two_sources):
        """Test that contested prompt asks which sources say what."""
        prompt = build_perspective_prompt('contested', article_cluster_two_sources)
        assert 'which source' in prompt.lower() or 'sources say' in prompt.lower()

    def test_gaps_prompt_asks_about_missing_coverage(self, sample_article):
        """Test that gaps prompt asks about missing coverage."""
        prompt = build_perspective_prompt('gaps', [sample_article])
        prompt_lower = prompt.lower()
        assert 'not being covered' in prompt_lower or 'missing' in prompt_lower or 'not covered' in prompt_lower

    def test_gaps_prompt_asks_about_questions(self, sample_article):
        """Test that gaps prompt asks about unanswered questions."""
        prompt = build_perspective_prompt('gaps', [sample_article])
        prompt_lower = prompt.lower()
        assert 'question' in prompt_lower or 'unanswered' in prompt_lower

    def test_timeline_prompt_asks_for_chronological(self, sample_article):
        """Test that timeline prompt asks for chronological sequence."""
        prompt = build_perspective_prompt('timeline', [sample_article])
        prompt_lower = prompt.lower()
        assert 'chronological' in prompt_lower or 'timeline' in prompt_lower

    def test_timeline_prompt_mentions_dates(self, sample_article):
        """Test that timeline prompt mentions dates/times."""
        prompt = build_perspective_prompt('timeline', [sample_article])
        prompt_lower = prompt.lower()
        assert 'date' in prompt_lower or 'time' in prompt_lower or 'timestamp' in prompt_lower


class TestBuildPerspectivePromptFramingCategories:
    """Tests for source framing category prompts."""

    def test_tech_industry_prompt_focuses_on_tech(self, sample_article_tech):
        """Test that tech-industry prompt focuses on technical perspective."""
        prompt = build_perspective_prompt('tech-industry', [sample_article_tech])
        prompt_lower = prompt.lower()
        assert 'tech' in prompt_lower
        assert 'technical' in prompt_lower or 'developer' in prompt_lower or 'innovation' in prompt_lower

    def test_mainstream_prompt_focuses_on_general_audience(self, sample_article_mainstream):
        """Test that mainstream prompt focuses on general audience."""
        prompt = build_perspective_prompt('mainstream', [sample_article_mainstream])
        prompt_lower = prompt.lower()
        assert 'mainstream' in prompt_lower
        assert 'general' in prompt_lower or 'public' in prompt_lower

    def test_financial_prompt_focuses_on_business(self, sample_article_business):
        """Test that financial prompt focuses on business/market perspective."""
        prompt = build_perspective_prompt('financial', [sample_article_business])
        prompt_lower = prompt.lower()
        assert 'financial' in prompt_lower or 'business' in prompt_lower
        assert 'market' in prompt_lower or 'investor' in prompt_lower

    def test_political_prompt_focuses_on_policy(self, sample_article_political):
        """Test that political prompt focuses on policy perspective."""
        prompt = build_perspective_prompt('political', [sample_article_political])
        prompt_lower = prompt.lower()
        assert 'political' in prompt_lower or 'policy' in prompt_lower
        assert 'government' in prompt_lower or 'regulatory' in prompt_lower

    def test_academic_prompt_focuses_on_research(self, sample_article_academic):
        """Test that academic prompt focuses on research perspective."""
        prompt = build_perspective_prompt('academic', [sample_article_academic])
        prompt_lower = prompt.lower()
        assert 'academic' in prompt_lower or 'research' in prompt_lower
        assert 'scholarly' in prompt_lower or 'evidence' in prompt_lower


class TestBuildPerspectivePromptFunCategories:
    """Tests for fun/entertainment category prompts."""

    def test_spiciest_takes_prompt_asks_for_provocative(self, sample_article_controversial):
        """Test that spiciest-takes prompt asks for provocative opinions."""
        prompt = build_perspective_prompt('spiciest-takes', [sample_article_controversial])
        prompt_lower = prompt.lower()
        assert 'provocative' in prompt_lower or 'spicy' in prompt_lower or 'spiciest' in prompt_lower

    def test_spiciest_takes_prompt_mentions_controversial(self, sample_article_controversial):
        """Test that spiciest-takes prompt mentions controversial content."""
        prompt = build_perspective_prompt('spiciest-takes', [sample_article_controversial])
        prompt_lower = prompt.lower()
        assert 'controversial' in prompt_lower or 'bold' in prompt_lower or 'inflammatory' in prompt_lower

    def test_unhinged_speculation_prompt_asks_for_wild(self, sample_article):
        """Test that unhinged-speculation prompt asks for wild predictions."""
        prompt = build_perspective_prompt('unhinged-speculation', [sample_article])
        prompt_lower = prompt.lower()
        assert 'wild' in prompt_lower or 'unhinged' in prompt_lower

    def test_unhinged_speculation_mentions_entertainment(self, sample_article):
        """Test that unhinged-speculation prompt mentions entertainment purpose."""
        prompt = build_perspective_prompt('unhinged-speculation', [sample_article])
        prompt_lower = prompt.lower()
        assert 'entertainment' in prompt_lower or 'speculation' in prompt_lower

    def test_contrarian_prompt_asks_for_against_grain(self, sample_article):
        """Test that contrarian prompt asks for against-the-grain views."""
        prompt = build_perspective_prompt('contrarian', [sample_article])
        prompt_lower = prompt.lower()
        assert 'contrarian' in prompt_lower or 'against' in prompt_lower
        assert 'skeptical' in prompt_lower or 'alternative' in prompt_lower

    def test_doom_prompt_asks_for_pessimistic(self, sample_article):
        """Test that doom prompt asks for pessimistic takes."""
        prompt = build_perspective_prompt('doom', [sample_article])
        prompt_lower = prompt.lower()
        assert 'pessimistic' in prompt_lower or 'doom' in prompt_lower
        assert 'worst' in prompt_lower or 'negative' in prompt_lower or 'worried' in prompt_lower

    def test_hype_prompt_asks_for_optimistic(self, sample_article):
        """Test that hype prompt asks for optimistic takes."""
        prompt = build_perspective_prompt('hype', [sample_article])
        prompt_lower = prompt.lower()
        assert 'optimistic' in prompt_lower or 'hype' in prompt_lower
        assert 'best' in prompt_lower or 'enthusiastic' in prompt_lower or 'excited' in prompt_lower


class TestBuildPerspectivePromptAnalysisCategories:
    """Tests for analysis category prompts."""

    def test_expert_quotes_prompt_asks_for_experts(self, sample_article_academic):
        """Test that expert-quotes prompt asks for expert quotes."""
        prompt = build_perspective_prompt('expert-quotes', [sample_article_academic])
        prompt_lower = prompt.lower()
        assert 'expert' in prompt_lower
        assert 'quote' in prompt_lower

    def test_expert_quotes_prompt_mentions_credentials(self, sample_article_academic):
        """Test that expert-quotes prompt asks for credentials."""
        prompt = build_perspective_prompt('expert-quotes', [sample_article_academic])
        prompt_lower = prompt.lower()
        assert 'credential' in prompt_lower or 'authority' in prompt_lower or 'expertise' in prompt_lower

    def test_prediction_track_record_asks_about_past(self, article_cluster_two_sources):
        """Test that prediction-track-record prompt asks about past predictions."""
        prompt = build_perspective_prompt('prediction-track-record', article_cluster_two_sources)
        prompt_lower = prompt.lower()
        assert 'prediction' in prompt_lower or 'predicted' in prompt_lower
        assert 'past' in prompt_lower or 'previous' in prompt_lower or 'track record' in prompt_lower

    def test_prediction_track_record_asks_about_accuracy(self, article_cluster_two_sources):
        """Test that prediction-track-record prompt asks about prediction accuracy."""
        prompt = build_perspective_prompt('prediction-track-record', article_cluster_two_sources)
        prompt_lower = prompt.lower()
        assert 'held up' in prompt_lower or 'happened' in prompt_lower or 'forecast' in prompt_lower


class TestBuildPerspectivePromptUnknownCategory:
    """Tests for unknown category handling."""

    def test_unknown_category_returns_fallback_prompt(self, sample_article):
        """Test that unknown category returns a fallback prompt."""
        prompt = build_perspective_prompt('nonexistent-category', [sample_article])
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_unknown_category_mentions_category_name(self, sample_article):
        """Test that fallback prompt includes the category name."""
        unknown_cat = 'my-custom-category'
        prompt = build_perspective_prompt(unknown_cat, [sample_article])
        assert unknown_cat in prompt

    def test_unknown_category_includes_articles(self, sample_article):
        """Test that fallback prompt includes article content."""
        prompt = build_perspective_prompt('unknown-category', [sample_article])
        assert sample_article.title in prompt

    def test_fallback_prompt_has_analyze_instruction(self, sample_article):
        """Test that fallback prompt has generic analyze instruction."""
        prompt = build_perspective_prompt('random-category', [sample_article])
        assert 'analyze' in prompt.lower() or 'perspective' in prompt.lower()

    def test_empty_string_category_uses_fallback(self, sample_article):
        """Test that empty string category uses fallback prompt."""
        prompt = build_perspective_prompt('', [sample_article])
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestBuildPerspectivePromptEdgeCases:
    """Tests for edge cases in prompt building."""

    def test_handles_none_content(self, article_with_none_content):
        """Test handling of article with None content."""
        prompt = build_perspective_prompt('consensus', [article_with_none_content])
        assert isinstance(prompt, str)
        # Should not raise an error

    def test_handles_empty_content(self, sample_article_empty_content):
        """Test handling of article with empty content."""
        prompt = build_perspective_prompt('consensus', [sample_article_empty_content])
        assert isinstance(prompt, str)
        assert sample_article_empty_content.title in prompt

    def test_handles_unicode_content(self, sample_article_unicode):
        """Test handling of article with unicode content."""
        prompt = build_perspective_prompt('consensus', [sample_article_unicode])
        assert isinstance(prompt, str)
        # Should include unicode title
        assert '人工智能' in prompt or 'AI研究' in prompt

    def test_handles_special_characters_in_title(self):
        """Test handling of special characters in article title."""
        article = Article(
            id="special-1",
            feed_url="https://example.com/feed.xml",
            title="Breaking: $$$MAJOR$$$ NEWS!!! <script>alert('test')</script>",
            link="https://example.com/special",
            published=datetime.now(),
            content="Special content.",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        assert '$$$MAJOR$$$' in prompt
        assert '<script>' in prompt  # Raw content, not sanitized

    def test_handles_newlines_in_content(self):
        """Test handling of newlines in article content."""
        article = Article(
            id="newline-1",
            feed_url="https://example.com/feed.xml",
            title="Article With Newlines",
            link="https://example.com/newlines",
            published=datetime.now(),
            content="Line 1.\n\nLine 2.\n\nLine 3.",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        assert isinstance(prompt, str)
        # Content should be preserved
        assert 'Line 1' in prompt

    def test_handles_tabs_in_content(self):
        """Test handling of tabs in article content."""
        article = Article(
            id="tab-1",
            feed_url="https://example.com/feed.xml",
            title="Article With Tabs",
            link="https://example.com/tabs",
            published=datetime.now(),
            content="Column1\tColumn2\tColumn3",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        assert isinstance(prompt, str)

    def test_handles_very_long_title(self):
        """Test handling of very long article title."""
        long_title = "This is a very long title " * 50
        article = Article(
            id="long-title-1",
            feed_url="https://example.com/feed.xml",
            title=long_title,
            link="https://example.com/long-title",
            published=datetime.now(),
            content="Short content.",
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        # Title should be included (not truncated)
        assert long_title in prompt

    def test_handles_article_with_only_title(self):
        """Test handling of article with only title (no content, no summary)."""
        article = Article(
            id="title-only-1",
            feed_url="https://example.com/feed.xml",
            title="Title Only Article",
            link="https://example.com/title-only",
            published=datetime.now(),
            content=None,
            summary=None,
        )
        prompt = build_perspective_prompt('consensus', [article])
        assert 'Title Only Article' in prompt


class TestBuildPerspectivePromptAllCategoriesComprehensive:
    """Comprehensive tests ensuring all 16 categories have proper prompts."""

    def test_all_categories_produce_unique_prompts(self, article_cluster_two_sources):
        """Test that all 16 categories produce unique prompts."""
        prompts = {}
        for category_id in PERSPECTIVE_CATEGORIES.keys():
            prompts[category_id] = build_perspective_prompt(category_id, article_cluster_two_sources)

        # All prompts should be different from each other
        prompt_values = list(prompts.values())
        unique_prompts = set(prompt_values)
        assert len(unique_prompts) == 16, "All category prompts should be unique"

    def test_all_categories_include_articles_section(self, article_cluster_two_sources):
        """Test that all category prompts include the articles section."""
        for category_id in PERSPECTIVE_CATEGORIES.keys():
            prompt = build_perspective_prompt(category_id, article_cluster_two_sources)
            assert '[Article 1' in prompt, f"Category '{category_id}' missing article section"

    def test_all_categories_have_instructions(self, article_cluster_two_sources):
        """Test that all category prompts have meaningful instructions (not just articles)."""
        for category_id in PERSPECTIVE_CATEGORIES.keys():
            prompt = build_perspective_prompt(category_id, article_cluster_two_sources)
            # Prompt should be longer than just the article content
            assert len(prompt) > 200, f"Category '{category_id}' prompt too short"
            # Should contain some instructional words
            instruction_words = ['analyze', 'identify', 'find', 'extract', 'look', 'focus', 'list', 'given']
            has_instruction = any(word in prompt.lower() for word in instruction_words)
            assert has_instruction, f"Category '{category_id}' missing instructions"

    def test_factual_categories_have_bullet_point_format(self, article_cluster_two_sources):
        """Test that factual categories request bullet point format."""
        factual_cats = ['consensus', 'contested', 'gaps']
        for cat_id in factual_cats:
            prompt = build_perspective_prompt(cat_id, article_cluster_two_sources)
            assert 'bullet' in prompt.lower() or 'list' in prompt.lower(), \
                f"Factual category '{cat_id}' should request bullet/list format"

    def test_framing_categories_ask_what_emphasized(self, article_cluster_two_sources):
        """Test that framing categories ask what's emphasized."""
        framing_cats = ['tech-industry', 'mainstream', 'financial', 'political', 'academic']
        for cat_id in framing_cats:
            prompt = build_perspective_prompt(cat_id, article_cluster_two_sources)
            prompt_lower = prompt.lower()
            has_emphasis = 'emphasis' in prompt_lower or 'focus' in prompt_lower or 'angle' in prompt_lower
            assert has_emphasis, f"Framing category '{cat_id}' should ask about emphasis/focus"


class TestBuildPerspectivePromptMultipleArticles:
    """Tests for prompt building with multiple articles."""

    def test_handles_two_articles(self, article_cluster_two_sources):
        """Test handling of exactly two articles."""
        prompt = build_perspective_prompt('consensus', article_cluster_two_sources)
        assert '[Article 1' in prompt
        assert '[Article 2' in prompt
        assert '[Article 3' not in prompt

    def test_handles_five_articles(self, article_cluster_diverse):
        """Test handling of five articles."""
        prompt = build_perspective_prompt('contested', article_cluster_diverse)
        for i in range(1, 6):
            assert f'[Article {i}' in prompt

    def test_handles_twenty_articles(self, sample_articles_bulk):
        """Test handling of many articles."""
        prompt = build_perspective_prompt('consensus', sample_articles_bulk)
        # Check first few are present
        assert '[Article 1' in prompt
        assert '[Article 5' in prompt
        assert '[Article 10' in prompt

    def test_articles_separated_properly(self, article_cluster_diverse):
        """Test that articles are properly separated in the prompt."""
        prompt = build_perspective_prompt('consensus', article_cluster_diverse)
        # Count article headers
        article_count = prompt.count('[Article')
        assert article_count == 5

    def test_each_article_has_title_and_content(self, article_cluster_tech_news):
        """Test that each article includes both title and content."""
        prompt = build_perspective_prompt('consensus', article_cluster_tech_news)

        for article in article_cluster_tech_news:
            assert article.title in prompt


class TestBuildPerspectivePromptIntegration:
    """Integration tests for build_perspective_prompt with other functions."""

    def test_prompt_can_be_passed_to_llm_summarize(self, article_cluster_two_sources, mock_llm_provider):
        """Test that generated prompt can be passed to LLM summarize method."""
        prompt = build_perspective_prompt('consensus', article_cluster_two_sources)

        # Should be able to call summarize with the prompt
        result = mock_llm_provider.summarize(prompt)
        assert result is not None

    def test_prompt_used_in_synthesize_perspective(self, mock_storage_with_articles, mock_llm_provider):
        """Test that prompt is properly used in synthesize_perspective."""
        articles = mock_storage_with_articles.get_articles_by_cluster("test")

        # Synthesize should use build_perspective_prompt internally
        perspective = synthesize_perspective(
            category='consensus',
            articles=articles,
            llm_provider=mock_llm_provider,
        )

        # Verify LLM was called (which means prompt was built)
        assert mock_llm_provider.summarize.called
        call_args = mock_llm_provider.summarize.call_args
        prompt_used = call_args[0][0]
        assert 'consensus' in prompt_used.lower() or 'agree' in prompt_used.lower()

    def test_all_categories_work_with_synthesize_perspective(self, sample_article, mock_llm_provider):
        """Test that all category prompts work with synthesize_perspective."""
        # Use 2 articles to satisfy min_sources for consensus/contested
        articles = [sample_article, sample_article]

        for category_id in PERSPECTIVE_CATEGORIES.keys():
            mock_llm_provider.summarize.reset_mock()
            mock_llm_provider.summarize.return_value = f"Synthesis for {category_id}"

            perspective = synthesize_perspective(
                category=category_id,
                articles=articles,
                llm_provider=mock_llm_provider,
            )

            assert perspective.category == category_id
            assert mock_llm_provider.summarize.called

    def test_prompt_quality_verified_by_confidence(self, article_cluster_diverse, mock_llm_provider_verbose):
        """Test that prompt quality affects confidence estimation."""
        # Verbose provider returns structured response
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_diverse,
            llm_provider=mock_llm_provider_verbose,
        )

        # Should have reasonable confidence with good response
        assert perspective.confidence > 0.3


# =============================================================================
# Tests for synthesize_perspective Function
# =============================================================================


class TestSynthesizePerspectiveBasic:
    """Basic tests for synthesize_perspective function."""

    def test_returns_perspective_object(self, article_cluster_two_sources, mock_llm_provider):
        """Test that synthesize_perspective returns a Perspective object."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert isinstance(perspective, Perspective)

    def test_perspective_has_correct_category(self, article_cluster_two_sources, mock_llm_provider):
        """Test that returned perspective has correct category."""
        perspective = synthesize_perspective(
            category='contested',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert perspective.category == 'contested'

    def test_perspective_has_content_from_llm(self, article_cluster_two_sources, mock_llm_provider):
        """Test that perspective content comes from LLM."""
        mock_llm_provider.summarize.return_value = "LLM generated content about consensus"
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert "LLM generated content" in perspective.content

    def test_perspective_has_source_articles(self, article_cluster_two_sources, mock_llm_provider):
        """Test that perspective includes source article IDs."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert len(perspective.source_articles) == len(article_cluster_two_sources)
        for article in article_cluster_two_sources:
            assert article.id in perspective.source_articles

    def test_perspective_has_confidence(self, article_cluster_two_sources, mock_llm_provider):
        """Test that perspective has a confidence score."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert isinstance(perspective.confidence, float)
        assert 0.0 <= perspective.confidence <= 1.0

    def test_perspective_has_generated_at(self, article_cluster_two_sources, mock_llm_provider):
        """Test that perspective has a generated_at timestamp."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert isinstance(perspective.generated_at, datetime)

    def test_llm_provider_summarize_called(self, article_cluster_two_sources, mock_llm_provider):
        """Test that LLM provider's summarize method is called."""
        mock_llm_provider.summarize.reset_mock()
        synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert mock_llm_provider.summarize.called

    def test_llm_provider_called_with_prompt(self, article_cluster_two_sources, mock_llm_provider):
        """Test that LLM provider is called with a properly built prompt."""
        mock_llm_provider.summarize.reset_mock()
        synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        call_args = mock_llm_provider.summarize.call_args
        prompt = call_args[0][0]
        # Prompt should contain article content
        assert '[Article 1' in prompt
        assert '[Article 2' in prompt


class TestSynthesizePerspectiveWithMockedLLM:
    """Tests for perspective synthesis with various mocked LLM responses."""

    def test_handles_structured_llm_response(self, article_cluster_diverse, mock_llm_provider):
        """Test handling of structured LLM response with bullet points."""
        mock_llm_provider.summarize.return_value = (
            "Key points of consensus:\n"
            "- All sources agree on the basic facts\n"
            "- There is alignment on the timeline\n"
            "- Impact assessments are similar"
        )
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_diverse,
            llm_provider=mock_llm_provider,
        )
        assert "Key points of consensus" in perspective.content
        assert "- All sources agree" in perspective.content

    def test_handles_verbose_llm_response(self, article_cluster_diverse, mock_llm_provider_verbose):
        """Test handling of verbose LLM response."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_diverse,
            llm_provider=mock_llm_provider_verbose,
        )
        assert len(perspective.content) > 100
        assert "Point 1" in perspective.content

    def test_handles_short_valid_response(self, article_cluster_two_sources, mock_llm_provider):
        """Test handling of short but valid LLM response."""
        mock_llm_provider.summarize.return_value = "Sources agree on main points."
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert perspective.content == "Sources agree on main points."

    def test_handles_response_with_unicode(self, article_cluster_two_sources, mock_llm_provider):
        """Test handling of LLM response with unicode characters."""
        mock_llm_provider.summarize.return_value = "分析结果: 所有来源都同意 🎯 ✓"
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert "分析结果" in perspective.content
        assert "🎯" in perspective.content

    def test_handles_response_with_special_chars(self, article_cluster_two_sources, mock_llm_provider):
        """Test handling of LLM response with special characters."""
        mock_llm_provider.summarize.return_value = "Analysis: <important>key points</important> & more"
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        assert "<important>" in perspective.content
        assert "&" in perspective.content

    def test_different_categories_get_different_prompts(self, article_cluster_diverse, mock_llm_provider):
        """Test that different categories result in different prompts to LLM."""
        prompts_used = []

        for category in ['consensus', 'contested', 'gaps']:
            mock_llm_provider.summarize.reset_mock()
            mock_llm_provider.summarize.return_value = f"Response for {category}"

            synthesize_perspective(
                category=category,
                articles=article_cluster_diverse,
                llm_provider=mock_llm_provider,
            )

            call_args = mock_llm_provider.summarize.call_args
            prompts_used.append(call_args[0][0])

        # All prompts should be different
        assert len(set(prompts_used)) == 3

    def test_max_length_passed_to_llm(self, article_cluster_two_sources, mock_llm_provider):
        """Test that max_length is passed to LLM summarize."""
        mock_llm_provider.summarize.reset_mock()
        synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )
        call_kwargs = mock_llm_provider.summarize.call_args[1]
        assert 'max_length' in call_kwargs
        assert call_kwargs['max_length'] == 1000


class TestSynthesizePerspectiveInsufficientSources:
    """Tests for InsufficientSourcesError handling."""

    def test_raises_insufficient_sources_for_consensus_with_one_article(self, sample_article, mock_llm_provider):
        """Test that consensus category raises error with only 1 article."""
        with pytest.raises(InsufficientSourcesError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=[sample_article],
                llm_provider=mock_llm_provider,
            )
        assert "consensus" in str(exc_info.value)
        assert "requires at least 2 sources" in str(exc_info.value)

    def test_raises_insufficient_sources_for_contested_with_one_article(self, sample_article, mock_llm_provider):
        """Test that contested category raises error with only 1 article."""
        with pytest.raises(InsufficientSourcesError) as exc_info:
            synthesize_perspective(
                category='contested',
                articles=[sample_article],
                llm_provider=mock_llm_provider,
            )
        assert "contested" in str(exc_info.value)
        assert "requires at least 2 sources" in str(exc_info.value)

    def test_raises_insufficient_sources_for_prediction_track_record(self, sample_article, mock_llm_provider):
        """Test that prediction-track-record raises error with only 1 article."""
        with pytest.raises(InsufficientSourcesError) as exc_info:
            synthesize_perspective(
                category='prediction-track-record',
                articles=[sample_article],
                llm_provider=mock_llm_provider,
            )
        assert "prediction-track-record" in str(exc_info.value)

    def test_raises_insufficient_sources_with_empty_articles(self, mock_llm_provider):
        """Test that any category raises error with empty articles list."""
        with pytest.raises(InsufficientSourcesError) as exc_info:
            synthesize_perspective(
                category='gaps',
                articles=[],
                llm_provider=mock_llm_provider,
            )
        assert "requires at least 1 sources, got 0" in str(exc_info.value)

    def test_error_message_includes_required_count(self, sample_article, mock_llm_provider):
        """Test that error message specifies required article count."""
        with pytest.raises(InsufficientSourcesError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=[sample_article],
                llm_provider=mock_llm_provider,
            )
        error_msg = str(exc_info.value)
        assert "2" in error_msg  # consensus requires 2

    def test_error_message_includes_actual_count(self, sample_article, mock_llm_provider):
        """Test that error message specifies actual article count."""
        with pytest.raises(InsufficientSourcesError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=[sample_article],
                llm_provider=mock_llm_provider,
            )
        error_msg = str(exc_info.value)
        assert "got 1" in error_msg

    def test_single_source_categories_work_with_one_article(self, sample_article, mock_llm_provider):
        """Test that single-source categories work with one article."""
        single_source_cats = ['gaps', 'timeline', 'tech-industry', 'spiciest-takes']
        for category in single_source_cats:
            mock_llm_provider.summarize.return_value = f"Result for {category}"
            perspective = synthesize_perspective(
                category=category,
                articles=[sample_article],
                llm_provider=mock_llm_provider,
            )
            assert perspective.category == category

    def test_all_categories_require_at_least_one_article(self, mock_llm_provider):
        """Test that all categories raise error with zero articles."""
        for category in PERSPECTIVE_CATEGORIES.keys():
            with pytest.raises(InsufficientSourcesError):
                synthesize_perspective(
                    category=category,
                    articles=[],
                    llm_provider=mock_llm_provider,
                )


class TestSynthesizePerspectiveErrorHandling:
    """Tests for error handling in synthesize_perspective."""

    def test_raises_llm_provider_error_on_exception(self, article_cluster_two_sources, mock_llm_provider_error):
        """Test that LLM exceptions are wrapped in LLMProviderError."""
        with pytest.raises(LLMProviderError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=article_cluster_two_sources,
                llm_provider=mock_llm_provider_error,
            )
        assert "LLM synthesis failed" in str(exc_info.value)

    def test_raises_llm_provider_error_on_empty_response(self, article_cluster_two_sources, mock_llm_provider_empty):
        """Test that empty LLM response raises LLMProviderError."""
        with pytest.raises(LLMProviderError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=article_cluster_two_sources,
                llm_provider=mock_llm_provider_empty,
            )
        assert "empty or very short response" in str(exc_info.value)

    def test_raises_llm_provider_error_on_whitespace_only_response(self, article_cluster_two_sources, mock_llm_provider):
        """Test that whitespace-only LLM response raises LLMProviderError."""
        mock_llm_provider.summarize.return_value = "   \n\t  "
        with pytest.raises(LLMProviderError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=article_cluster_two_sources,
                llm_provider=mock_llm_provider,
            )
        assert "empty or very short response" in str(exc_info.value)

    def test_raises_llm_provider_error_on_very_short_response(self, article_cluster_two_sources, mock_llm_provider):
        """Test that very short LLM response raises LLMProviderError."""
        mock_llm_provider.summarize.return_value = "Short"  # < 10 chars
        with pytest.raises(LLMProviderError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=article_cluster_two_sources,
                llm_provider=mock_llm_provider,
            )
        assert "empty or very short response" in str(exc_info.value)

    def test_raises_category_not_applicable_for_unknown_category(self, article_cluster_two_sources, mock_llm_provider):
        """Test that unknown category raises CategoryNotApplicableError."""
        with pytest.raises(CategoryNotApplicableError) as exc_info:
            synthesize_perspective(
                category='nonexistent-category',
                articles=article_cluster_two_sources,
                llm_provider=mock_llm_provider,
            )
        assert "Unknown category" in str(exc_info.value)

    def test_error_message_includes_original_error(self, article_cluster_two_sources, mock_llm_provider):
        """Test that LLMProviderError includes original error message."""
        mock_llm_provider.summarize.side_effect = RuntimeError("API rate limit exceeded")
        with pytest.raises(LLMProviderError) as exc_info:
            synthesize_perspective(
                category='consensus',
                articles=article_cluster_two_sources,
                llm_provider=mock_llm_provider,
            )
        assert "API rate limit exceeded" in str(exc_info.value)


class TestSynthesizePerspectiveFallback:
    """Tests for fallback behavior when no LLM provider is given."""

    def test_works_without_llm_provider(self, article_cluster_two_sources):
        """Test that synthesis works without LLM provider using fallback."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=None,
        )
        assert isinstance(perspective, Perspective)
        assert perspective.category == 'consensus'

    def test_fallback_has_low_confidence(self, article_cluster_two_sources):
        """Test that fallback perspective has low confidence."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=None,
        )
        assert perspective.confidence <= 0.3

    def test_fallback_includes_article_titles(self, article_cluster_two_sources):
        """Test that fallback perspective includes article titles."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=None,
        )
        # Fallback should list article titles
        for article in article_cluster_two_sources[:5]:  # Only first 5 shown
            assert article.title in perspective.content or "Sources" in perspective.content

    def test_fallback_still_requires_minimum_sources(self, sample_article):
        """Test that fallback still enforces minimum source requirements."""
        with pytest.raises(InsufficientSourcesError):
            synthesize_perspective(
                category='consensus',
                articles=[sample_article],
                llm_provider=None,
            )

    def test_fallback_with_single_source_category(self, sample_article):
        """Test fallback with single-source category."""
        perspective = synthesize_perspective(
            category='gaps',
            articles=[sample_article],
            llm_provider=None,
        )
        assert "Limited perspective" in perspective.content or sample_article.title in perspective.content


class TestSynthesizePerspectiveCaching:
    """Tests for caching behavior in synthesize_perspective."""

    def test_uses_cached_perspective_when_fresh(self, mock_storage_with_cached_perspective, mock_llm_provider):
        """Test that fresh cached perspective is returned without calling LLM."""
        mock_llm_provider.summarize.reset_mock()
        perspective = synthesize_perspective(
            category='consensus',
            articles=[],  # Doesn't matter, should use cache
            llm_provider=mock_llm_provider,
            storage=mock_storage_with_cached_perspective,
            cluster_id='test-cluster',
        )
        # LLM should not be called if cache is fresh
        assert not mock_llm_provider.summarize.called
        assert perspective.content == "Cached perspective content: All sources agree on the main facts."

    def test_regenerates_when_cache_stale(self, mock_storage_with_stale_cache, mock_llm_provider, article_cluster_two_sources):
        """Test that stale cache triggers regeneration."""
        # Mock get_articles_by_cluster for when cache is stale
        mock_storage_with_stale_cache.get_articles_by_cluster.return_value = article_cluster_two_sources

        # But we're passing articles directly, so let's test without storage fetching
        mock_llm_provider.summarize.return_value = "Fresh perspective content"

        # For a stale cache, the is_cache_fresh check should return False
        # Let's verify by calling synthesize_perspective with direct articles
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
            storage=mock_storage_with_stale_cache,
            cluster_id='test-cluster',
        )

        # LLM should be called because cache is stale
        assert mock_llm_provider.summarize.called
        assert perspective.content == "Fresh perspective content"

    def test_caches_new_perspective(self, mock_storage_with_articles, mock_llm_provider):
        """Test that newly generated perspective is cached."""
        mock_llm_provider.summarize.return_value = "New perspective to cache"
        articles = mock_storage_with_articles.get_articles_by_cluster("test")

        synthesize_perspective(
            category='consensus',
            articles=articles,
            llm_provider=mock_llm_provider,
            storage=mock_storage_with_articles,
            cluster_id='test-cluster',
        )

        # Verify cache_perspective was called
        assert mock_storage_with_articles.cache_perspective.called

    def test_caches_fallback_perspective(self, mock_storage_with_articles):
        """Test that fallback perspective is also cached."""
        articles = mock_storage_with_articles.get_articles_by_cluster("test")

        synthesize_perspective(
            category='consensus',
            articles=articles,
            llm_provider=None,  # No LLM, uses fallback
            storage=mock_storage_with_articles,
            cluster_id='test-cluster',
        )

        # Verify cache_perspective was called even for fallback
        assert mock_storage_with_articles.cache_perspective.called


class TestSynthesizePerspectiveConfidence:
    """Tests for confidence estimation in synthesize_perspective."""

    def test_high_confidence_for_good_response(self, article_cluster_diverse, mock_llm_provider_verbose):
        """Test that good LLM response results in higher confidence."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_diverse,
            llm_provider=mock_llm_provider_verbose,
        )
        # Verbose provider returns structured response, should have higher confidence
        assert perspective.confidence >= 0.5

    def test_confidence_affected_by_article_count(self, sample_article, mock_llm_provider):
        """Test that more articles increase confidence."""
        mock_llm_provider.summarize.return_value = "Standard response for testing."

        # Two articles (minimum for consensus)
        perspective_min = synthesize_perspective(
            category='consensus',
            articles=[sample_article, sample_article],
            llm_provider=mock_llm_provider,
        )

        # Many articles
        perspective_many = synthesize_perspective(
            category='consensus',
            articles=[sample_article] * 10,
            llm_provider=mock_llm_provider,
        )

        # More articles should give higher or equal confidence
        assert perspective_many.confidence >= perspective_min.confidence

    def test_confidence_affected_by_response_structure(self, article_cluster_two_sources, mock_llm_provider):
        """Test that structured response affects confidence."""
        # Unstructured response
        mock_llm_provider.summarize.return_value = "All sources agree on the facts."
        perspective_simple = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )

        # Structured response with bullet points
        mock_llm_provider.summarize.return_value = (
            "Key agreements:\n"
            "- Point one\n"
            "- Point two\n"
            "- Point three"
        )
        perspective_structured = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider,
        )

        # Structured should have higher or equal confidence
        assert perspective_structured.confidence >= perspective_simple.confidence

    def test_confidence_reduced_by_uncertainty_markers(self, article_cluster_two_sources, mock_llm_provider_uncertain):
        """Test that uncertainty markers reduce confidence."""
        perspective = synthesize_perspective(
            category='consensus',
            articles=article_cluster_two_sources,
            llm_provider=mock_llm_provider_uncertain,
        )
        # Response with uncertainty markers should have lower confidence
        # (0.7 is the maximum possible with the penalty applied)
        assert perspective.confidence <= 0.7


# =============================================================================
# Tests for synthesize_perspectives Function
# =============================================================================


class TestSynthesizePerspectivesBasic:
    """Basic tests for synthesize_perspectives function."""

    def test_returns_dict(self, mock_storage_with_articles, mock_llm_provider):
        """Test that synthesize_perspectives returns a dictionary."""
        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=['consensus'],
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )
        assert isinstance(result, dict)

    def test_returns_perspective_for_each_category(self, mock_storage_with_articles, mock_llm_provider):
        """Test that result contains perspective for each requested category."""
        categories = ['consensus', 'contested', 'gaps']
        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=categories,
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )
        for category in categories:
            assert category in result
            assert isinstance(result[category], Perspective)

    def test_returns_empty_dict_for_empty_cluster(self, mock_storage, mock_llm_provider):
        """Test that empty cluster returns empty dict."""
        result = synthesize_perspectives(
            cluster_id='nonexistent-cluster',
            categories=['consensus'],
            storage=mock_storage,
            llm_provider=mock_llm_provider,
        )
        assert result == {}

    def test_handles_single_category(self, mock_storage_with_articles, mock_llm_provider):
        """Test handling of single category request."""
        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=['gaps'],
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )
        assert 'gaps' in result
        assert len(result) == 1

    def test_handles_default_categories(self, mock_storage_with_articles, mock_llm_provider):
        """Test handling of DEFAULT_CATEGORIES."""
        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=DEFAULT_CATEGORIES,
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )
        for category in DEFAULT_CATEGORIES:
            assert category in result


class TestSynthesizePerspectivesErrorHandling:
    """Tests for error handling in synthesize_perspectives."""

    def test_handles_insufficient_sources_gracefully(self, mock_storage, mock_llm_provider):
        """Test that insufficient sources creates placeholder perspective."""
        # Mock storage to return only 1 article
        single_article = Article(
            id='single-1',
            feed_url='https://example.com/feed.xml',
            title='Single Article',
            link='https://example.com/single',
            published=datetime.now(),
            content='Single article content.',
            summary=None,
        )
        mock_storage.get_articles_by_cluster.return_value = [single_article]

        result = synthesize_perspectives(
            cluster_id='single-article-cluster',
            categories=['consensus'],  # Requires 2 sources
            storage=mock_storage,
            llm_provider=mock_llm_provider,
        )

        # Should return a low-confidence placeholder
        assert 'consensus' in result
        assert result['consensus'].confidence == 0.1
        assert "Insufficient sources" in result['consensus'].content

    def test_skips_unknown_categories(self, mock_storage_with_articles, mock_llm_provider):
        """Test that unknown categories are skipped."""
        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=['consensus', 'unknown-category', 'gaps'],
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )
        # Unknown category should be skipped
        assert 'unknown-category' not in result
        # Valid categories should be present
        assert 'consensus' in result
        assert 'gaps' in result

    def test_uses_fallback_on_llm_error(self, mock_storage_with_articles, mock_llm_provider_error):
        """Test that LLM error results in fallback perspective."""
        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=['consensus'],
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider_error,
        )
        # Should have a fallback perspective, not empty
        assert 'consensus' in result
        # Fallback has low confidence
        assert result['consensus'].confidence <= 0.3

    def test_continues_processing_after_error(self, mock_storage_with_articles, mock_llm_provider):
        """Test that processing continues after one category fails."""
        # Make first call fail, second succeed
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First call fails")
            return "Second call succeeds"

        mock_llm_provider.summarize.side_effect = side_effect

        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=['consensus', 'gaps'],
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )

        # Both categories should be present (one fallback, one success)
        assert 'consensus' in result
        assert 'gaps' in result


class TestSynthesizePerspectivesIntegration:
    """Integration tests for synthesize_perspectives."""

    def test_full_synthesis_with_mock_storage(self, full_perspective_setup):
        """Test full synthesis with mock storage containing the articles."""
        # Create mock storage that returns the articles from the setup
        mock_storage = MagicMock()
        mock_storage.get_articles_by_cluster.return_value = full_perspective_setup['articles']
        mock_storage.get_cached_perspective.return_value = None
        mock_storage.cache_perspective.return_value = None

        result = synthesize_perspectives(
            cluster_id=full_perspective_setup['story_id'],
            categories=['consensus', 'contested', 'gaps'],
            storage=mock_storage,
            llm_provider=full_perspective_setup['llm_provider'],
        )
        assert len(result) == 3
        for category in ['consensus', 'contested', 'gaps']:
            assert category in result
            assert isinstance(result[category], Perspective)

    def test_synthesis_with_all_category_groups(self, mock_storage_with_articles, mock_llm_provider):
        """Test synthesis with categories from all groups."""
        categories = [
            'consensus',  # factual
            'tech-industry',  # framing
            'spiciest-takes',  # fun
            'expert-quotes',  # analysis
        ]
        result = synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=categories,
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )
        for category in categories:
            assert category in result

    def test_synthesis_uses_storage_articles(self, mock_storage_with_articles, mock_llm_provider):
        """Test that synthesis fetches articles from storage."""
        synthesize_perspectives(
            cluster_id='mock-story-1',
            categories=['consensus'],
            storage=mock_storage_with_articles,
            llm_provider=mock_llm_provider,
        )
        # Verify get_articles_by_cluster was called
        mock_storage_with_articles.get_articles_by_cluster.assert_called_with('mock-story-1')


# =============================================================================
# Tests for generate_fallback_perspective Function
# =============================================================================


class TestGenerateFallbackPerspective:
    """Tests for generate_fallback_perspective function."""

    def test_returns_perspective_object(self, article_cluster_two_sources):
        """Test that fallback returns a Perspective object."""
        result = generate_fallback_perspective('consensus', article_cluster_two_sources)
        assert isinstance(result, Perspective)

    def test_handles_empty_articles(self):
        """Test fallback with empty articles list."""
        result = generate_fallback_perspective('consensus', [])
        assert result.category == 'consensus'
        assert "No articles available" in result.content
        assert result.confidence == 0.0
        assert result.source_articles == []

    def test_handles_single_article(self, sample_article):
        """Test fallback with single article."""
        result = generate_fallback_perspective('gaps', [sample_article])
        assert "Limited perspective" in result.content
        assert sample_article.title in result.content

    def test_includes_summary_for_single_article(self):
        """Test that single article fallback includes summary if available."""
        article = Article(
            id='with-summary',
            feed_url='https://example.com/feed.xml',
            title='Article With Summary',
            link='https://example.com/summary',
            published=datetime.now(),
            content='Full content here.',
            summary='This is the summary.',
        )
        result = generate_fallback_perspective('gaps', [article])
        assert "This is the summary" in result.content

    def test_lists_multiple_articles(self, article_cluster_diverse):
        """Test that multiple articles are listed."""
        result = generate_fallback_perspective('consensus', article_cluster_diverse)
        assert f"Sources ({len(article_cluster_diverse)} articles)" in result.content
        # First 5 articles should be listed
        for i, article in enumerate(article_cluster_diverse[:5], 1):
            assert f"{i}." in result.content

    def test_has_low_confidence(self, article_cluster_two_sources):
        """Test that fallback always has low confidence."""
        result = generate_fallback_perspective('consensus', article_cluster_two_sources)
        assert result.confidence == 0.2

    def test_includes_all_article_ids(self, article_cluster_diverse):
        """Test that all article IDs are in source_articles."""
        result = generate_fallback_perspective('consensus', article_cluster_diverse)
        for article in article_cluster_diverse:
            assert article.id in result.source_articles

    def test_has_generated_at_timestamp(self, article_cluster_two_sources):
        """Test that fallback has generated_at timestamp."""
        before = datetime.now()
        result = generate_fallback_perspective('consensus', article_cluster_two_sources)
        after = datetime.now()
        assert before <= result.generated_at <= after


# =============================================================================
# Tests for is_cache_fresh Function
# =============================================================================


class TestIsCacheFresh:
    """Tests for is_cache_fresh function."""

    def test_returns_true_for_recent_perspective(self, sample_perspective_fresh):
        """Test that recently generated perspective is considered fresh."""
        assert is_cache_fresh(sample_perspective_fresh) is True

    def test_returns_false_for_stale_perspective(self, sample_perspective_stale):
        """Test that old perspective is considered stale."""
        assert is_cache_fresh(sample_perspective_stale) is False

    def test_returns_false_for_very_old_perspective(self, sample_perspective_very_old):
        """Test that very old perspective is considered stale."""
        assert is_cache_fresh(sample_perspective_very_old) is False

    def test_returns_false_for_none_perspective(self):
        """Test that None perspective returns False."""
        assert is_cache_fresh(None) is False

    def test_returns_false_for_none_generated_at(self, perspective_with_none_generated_at):
        """Test that perspective with None generated_at returns False."""
        assert is_cache_fresh(perspective_with_none_generated_at) is False

    def test_custom_ttl_hours(self, sample_perspective):
        """Test with custom TTL hours."""
        # Sample perspective is freshly generated
        assert is_cache_fresh(sample_perspective, ttl_hours=1) is True
        assert is_cache_fresh(sample_perspective, ttl_hours=24) is True

    def test_custom_ttl_makes_fresh_stale(self, sample_perspective_fresh):
        """Test that shorter TTL can make fresh perspective stale."""
        # Fresh perspective was generated 1 hour ago
        # With 0.5 hour TTL, it should be stale
        # But let's check the fixture timing first
        age = datetime.now() - sample_perspective_fresh.generated_at
        hours_old = age.total_seconds() / 3600

        # Use a TTL shorter than the age
        if hours_old > 0:
            assert is_cache_fresh(sample_perspective_fresh, ttl_hours=int(hours_old * 0.5)) is False

    def test_boundary_ttl(self):
        """Test cache freshness at TTL boundary."""
        # Create perspective exactly at boundary
        perspective = Perspective(
            category='consensus',
            content='Test content',
            source_articles=['article-1'],
            confidence=0.5,
            generated_at=datetime.now() - timedelta(hours=6),
        )
        # At exactly 6 hours with 6 hour TTL, should be stale (< not <=)
        assert is_cache_fresh(perspective, ttl_hours=6) is False
        # With 7 hour TTL, should be fresh
        assert is_cache_fresh(perspective, ttl_hours=7) is True


# =============================================================================
# Tests for estimate_confidence Function
# =============================================================================


class TestEstimateConfidenceBasic:
    """Basic tests for estimate_confidence function."""

    def test_returns_float(self, article_cluster_two_sources):
        """Test that estimate_confidence returns a float."""
        result = estimate_confidence('consensus', "Some synthesis text", article_cluster_two_sources)
        assert isinstance(result, float)

    def test_returns_value_between_0_and_1(self, article_cluster_diverse):
        """Test that confidence is between 0 and 1."""
        result = estimate_confidence('consensus', "Some synthesis text", article_cluster_diverse)
        assert 0.0 <= result <= 1.0

    def test_empty_synthesis_gives_lower_confidence(self, article_cluster_two_sources):
        """Test that empty synthesis gives lower confidence."""
        result_empty = estimate_confidence('consensus', "", article_cluster_two_sources)
        result_full = estimate_confidence('consensus', "Full synthesis with content.", article_cluster_two_sources)
        assert result_empty <= result_full

    def test_more_articles_increase_confidence(self, sample_article):
        """Test that more articles increase confidence."""
        few_articles = [sample_article] * 2
        many_articles = [sample_article] * 10

        result_few = estimate_confidence('consensus', "Synthesis text.", few_articles)
        result_many = estimate_confidence('consensus', "Synthesis text.", many_articles)

        assert result_many >= result_few


class TestEstimateConfidenceSynthesisQuality:
    """Tests for synthesis quality impact on confidence."""

    def test_longer_synthesis_increases_confidence(self, article_cluster_two_sources):
        """Test that longer synthesis increases confidence."""
        short = "Short."
        long = "This is a much longer synthesis with detailed analysis and multiple points. " * 3

        result_short = estimate_confidence('consensus', short, article_cluster_two_sources)
        result_long = estimate_confidence('consensus', long, article_cluster_two_sources)

        assert result_long >= result_short

    def test_structured_synthesis_increases_confidence(self, article_cluster_two_sources):
        """Test that structured synthesis (bullet points) increases confidence."""
        unstructured = "All sources agree on the main facts without any structure."
        structured = "Key points:\n- Point 1\n- Point 2\n- Point 3"

        result_unstructured = estimate_confidence('consensus', unstructured, article_cluster_two_sources)
        result_structured = estimate_confidence('consensus', structured, article_cluster_two_sources)

        assert result_structured >= result_unstructured

    def test_uncertainty_markers_decrease_confidence(self, article_cluster_two_sources):
        """Test that uncertainty markers decrease confidence."""
        # Use similar length texts to isolate the effect of uncertainty markers
        confident = (
            "All sources clearly agree on these important facts about the topic. "
            "The agreement is strong across all reporting sources examined."
        )
        # Same length but with uncertainty markers
        uncertain = (
            "It is unclear from the sources what the facts are. No information was found "
            "about the key questions. Unknown aspects remain in this analysis."
        )

        result_confident = estimate_confidence('consensus', confident, article_cluster_two_sources)
        result_uncertain = estimate_confidence('consensus', uncertain, article_cluster_two_sources)

        # Uncertain synthesis should have same or lower confidence due to penalty
        assert result_uncertain <= result_confident


class TestEstimateConfidenceRecency:
    """Tests for article recency impact on confidence."""

    def test_recent_articles_increase_confidence(self, article_cluster_all_recent, article_cluster_all_old):
        """Test that recent articles increase confidence."""
        synthesis = "Standard synthesis text for comparison."

        result_recent = estimate_confidence('consensus', synthesis, article_cluster_all_recent)
        result_old = estimate_confidence('consensus', synthesis, article_cluster_all_old)

        assert result_recent >= result_old

    def test_mixed_recency_has_intermediate_confidence(self, article_cluster_mixed_dates, article_cluster_all_recent):
        """Test that mixed recency has intermediate confidence."""
        synthesis = "Standard synthesis text for comparison."

        result_mixed = estimate_confidence('consensus', synthesis, article_cluster_mixed_dates)
        result_all_recent = estimate_confidence('consensus', synthesis, article_cluster_all_recent)

        # Mixed should be less than or equal to all recent
        assert result_mixed <= result_all_recent


class TestEstimateConfidenceMinSources:
    """Tests for min_sources impact on confidence."""

    def test_exactly_min_sources_gives_base_confidence(self, sample_article):
        """Test that exactly min_sources gives base confidence."""
        # Consensus requires 2
        result = estimate_confidence('consensus', "Synthesis.", [sample_article, sample_article])
        # Should give base confidence for meeting minimum
        assert result >= 0.3

    def test_double_min_sources_gives_higher_confidence(self, sample_article):
        """Test that 2x min_sources gives higher confidence."""
        # Consensus requires 2, so 4 should give higher confidence
        result_min = estimate_confidence('consensus', "Synthesis.", [sample_article] * 2)
        result_double = estimate_confidence('consensus', "Synthesis.", [sample_article] * 4)

        assert result_double >= result_min

    def test_below_min_sources_gives_low_confidence(self, sample_article):
        """Test that below min_sources gives low confidence."""
        # Consensus requires 2, so 1 should give low confidence
        result = estimate_confidence('consensus', "Synthesis.", [sample_article])
        # Use round to handle floating point precision (0.30000000000000004)
        assert round(result, 10) <= 0.3


# =============================================================================
# Tests for Perspective Configuration Functions
# =============================================================================


class TestGetUserPerspectiveConfig:
    """Tests for get_user_perspective_config function."""

    def test_returns_default_when_no_config(self, mock_storage):
        """Test that default config is returned when none stored."""
        mock_storage.get_perspective_config.return_value = None
        config = get_user_perspective_config(mock_storage)

        assert 'enabled_categories' in config
        assert 'default_categories' in config
        assert 'category_order' in config
        assert config['default_categories'] == DEFAULT_CATEGORIES

    def test_returns_stored_config(self, mock_storage, custom_perspective_config):
        """Test that stored config is returned."""
        mock_storage.get_perspective_config.return_value = custom_perspective_config
        config = get_user_perspective_config(mock_storage)

        assert config == custom_perspective_config

    def test_default_enabled_categories_includes_all(self, mock_storage):
        """Test that default config enables all categories."""
        mock_storage.get_perspective_config.return_value = None
        config = get_user_perspective_config(mock_storage)

        assert set(config['enabled_categories']) == set(PERSPECTIVE_CATEGORIES.keys())


class TestUpdateUserPerspectiveConfig:
    """Tests for update_user_perspective_config function."""

    def test_updates_enabled_categories(self, mock_storage):
        """Test updating enabled categories."""
        mock_storage.get_perspective_config.return_value = None
        new_enabled = ['consensus', 'contested']

        update_user_perspective_config(
            mock_storage,
            enabled_categories=new_enabled,
        )

        mock_storage.save_perspective_config.assert_called_once()
        saved_config = mock_storage.save_perspective_config.call_args[0][0]
        assert saved_config['enabled_categories'] == new_enabled

    def test_updates_default_categories(self, mock_storage):
        """Test updating default categories."""
        mock_storage.get_perspective_config.return_value = None
        new_defaults = ['gaps']

        update_user_perspective_config(
            mock_storage,
            default_categories=new_defaults,
        )

        saved_config = mock_storage.save_perspective_config.call_args[0][0]
        assert saved_config['default_categories'] == new_defaults

    def test_updates_category_order(self, mock_storage):
        """Test updating category order."""
        mock_storage.get_perspective_config.return_value = None
        new_order = ['gaps', 'consensus', 'contested']

        update_user_perspective_config(
            mock_storage,
            category_order=new_order,
        )

        saved_config = mock_storage.save_perspective_config.call_args[0][0]
        assert saved_config['category_order'] == new_order

    def test_partial_update_preserves_other_fields(self, mock_storage, custom_perspective_config):
        """Test that partial update preserves other fields."""
        mock_storage.get_perspective_config.return_value = custom_perspective_config

        update_user_perspective_config(
            mock_storage,
            default_categories=['consensus'],  # Only update this
        )

        saved_config = mock_storage.save_perspective_config.call_args[0][0]
        # enabled_categories should be preserved
        assert saved_config['enabled_categories'] == custom_perspective_config['enabled_categories']
        # default_categories should be updated
        assert saved_config['default_categories'] == ['consensus']


# =============================================================================
# Tests for Perspective Dataclass
# =============================================================================


class TestPerspectiveDataclass:
    """Tests for Perspective dataclass."""

    def test_perspective_creation(self):
        """Test creating a Perspective object."""
        perspective = Perspective(
            category='consensus',
            content='Test content',
            source_articles=['article-1', 'article-2'],
            confidence=0.8,
            generated_at=datetime.now(),
        )
        assert perspective.category == 'consensus'
        assert perspective.content == 'Test content'
        assert len(perspective.source_articles) == 2
        assert perspective.confidence == 0.8

    def test_perspective_with_all_fields(self):
        """Test Perspective with all required fields."""
        now = datetime.now()
        perspective = Perspective(
            category='gaps',
            content='Missing coverage areas',
            source_articles=['a1', 'a2', 'a3'],
            confidence=0.65,
            generated_at=now,
        )
        assert perspective.category == 'gaps'
        assert perspective.generated_at == now

    def test_perspective_with_empty_source_articles(self):
        """Test Perspective with empty source articles list."""
        perspective = Perspective(
            category='consensus',
            content='No sources',
            source_articles=[],
            confidence=0.0,
            generated_at=datetime.now(),
        )
        assert perspective.source_articles == []


# =============================================================================
# Tests for Exception Classes
# =============================================================================


class TestPerspectiveExceptions:
    """Tests for perspective-related exceptions."""

    def test_perspective_error_is_base(self):
        """Test that PerspectiveError is base exception."""
        error = PerspectiveError("test error")
        assert isinstance(error, Exception)

    def test_insufficient_sources_error_inherits(self):
        """Test that InsufficientSourcesError inherits from PerspectiveError."""
        error = InsufficientSourcesError("not enough")
        assert isinstance(error, PerspectiveError)

    def test_category_not_applicable_error_inherits(self):
        """Test that CategoryNotApplicableError inherits from PerspectiveError."""
        error = CategoryNotApplicableError("invalid category")
        assert isinstance(error, PerspectiveError)

    def test_llm_provider_error_inherits(self):
        """Test that LLMProviderError inherits from PerspectiveError."""
        error = LLMProviderError("LLM failed")
        assert isinstance(error, PerspectiveError)

    def test_exceptions_preserve_message(self):
        """Test that exceptions preserve their message."""
        msg = "Custom error message"
        assert str(PerspectiveError(msg)) == msg
        assert str(InsufficientSourcesError(msg)) == msg
        assert str(CategoryNotApplicableError(msg)) == msg
        assert str(LLMProviderError(msg)) == msg
