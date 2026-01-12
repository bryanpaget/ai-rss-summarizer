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
    """Create a mock Storage object with common methods."""
    storage = MagicMock(spec=Storage)
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
    """Create a mock Storage with articles for perspective synthesis."""
    storage = MagicMock(spec=Storage)

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
    """Create a mock Storage with a cached perspective."""
    storage = MagicMock(spec=Storage)

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
    """Create a mock Storage with a stale cached perspective."""
    storage = MagicMock(spec=Storage)

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
