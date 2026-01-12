"""Tests for user_context module - user context management and relevance engine."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, List
from unittest.mock import MagicMock, patch, Mock

import pytest

from src.user_context import (
    UserContextProfile,
    ArticleInteraction,
    UserContextStore,
    RelevanceEngine,
    sort_by_relevance,
    apply_diversity_filter,
)
from src.storage import Article


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


@pytest.fixture
def temp_profile_path(temp_dir):
    """Create a temporary profile path."""
    return os.path.join(temp_dir, "config", "user_context.json")


@pytest.fixture
def temp_profile_path_existing(temp_dir):
    """Create a temporary profile path with parent directories created."""
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "user_context.json")


# =============================================================================
# Fixtures for UserContextProfile
# =============================================================================


@pytest.fixture
def profile_default():
    """Create a default UserContextProfile with all defaults."""
    return UserContextProfile()


@pytest.fixture
def profile_with_role():
    """Create a UserContextProfile with a role set."""
    return UserContextProfile(role="software engineer")


@pytest.fixture
def profile_developer():
    """Create a UserContextProfile for a developer."""
    return UserContextProfile(
        role="software developer",
        current_projects=["building RSS reader", "learning Rust"],
        watching=["AI", "Python", "web development"],
        ignore=["celebrity news", "sports"],
        pinned=["security vulnerabilities"],
    )


@pytest.fixture
def profile_researcher():
    """Create a UserContextProfile for a researcher."""
    return UserContextProfile(
        role="data scientist",
        current_projects=["machine learning research", "NLP paper"],
        watching=["AI", "deep learning", "transformers", "LLMs"],
        ignore=["entertainment", "politics"],
        pinned=["academic papers", "research breakthroughs"],
        relevance_threshold=0.4,
        diversity_factor=0.2,
    )


@pytest.fixture
def profile_journalist():
    """Create a UserContextProfile for a journalist."""
    return UserContextProfile(
        role="tech journalist",
        current_projects=["AI industry report", "startup coverage"],
        watching=["startups", "funding rounds", "tech policy"],
        ignore=[],
        pinned=["breaking news"],
        personalization_strength=0.6,
    )


@pytest.fixture
def profile_custom_thresholds():
    """Create a UserContextProfile with custom threshold settings."""
    return UserContextProfile(
        role="analyst",
        relevance_threshold=0.5,
        diversity_factor=0.25,
        personalization_strength=0.9,
    )


@pytest.fixture
def profile_low_personalization():
    """Create a UserContextProfile with low personalization strength."""
    return UserContextProfile(
        role="general reader",
        personalization_strength=0.2,
    )


@pytest.fixture
def profile_zero_personalization():
    """Create a UserContextProfile with zero personalization (neutral scores)."""
    return UserContextProfile(
        role="explorer",
        personalization_strength=0.0,
    )


@pytest.fixture
def profile_with_timestamps():
    """Create a UserContextProfile with explicit timestamps."""
    now = datetime.now()
    return UserContextProfile(
        role="user",
        created_at=now - timedelta(days=30),
        last_updated=now - timedelta(hours=1),
        last_feedback_prompt=now - timedelta(days=7),
    )


@pytest.fixture
def profile_unicode():
    """Create a UserContextProfile with unicode characters."""
    return UserContextProfile(
        role="desarrollador de software",
        current_projects=["proyecto AI", "desenvolvimento web"],
        watching=["inteligencia artificial", "tecnologia"],
        ignore=["noticias de celebridades"],
        pinned=["seguridad"],
    )


@pytest.fixture
def profile_special_chars():
    """Create a UserContextProfile with special characters."""
    return UserContextProfile(
        role="developer <script>",
        current_projects=["project && test", "project || other"],
        watching=["topic; select *", "topic' OR '1'='1"],
        ignore=["ignore&topic"],
        pinned=["pinned\\topic"],
    )


@pytest.fixture
def profile_empty_lists():
    """Create a UserContextProfile with empty lists."""
    return UserContextProfile(
        role="minimal user",
        current_projects=[],
        watching=[],
        ignore=[],
        pinned=[],
    )


@pytest.fixture
def profile_many_interests():
    """Create a UserContextProfile with many items in each list."""
    return UserContextProfile(
        role="omnivore",
        current_projects=[f"project-{i}" for i in range(20)],
        watching=[f"topic-{i}" for i in range(50)],
        ignore=[f"ignore-{i}" for i in range(30)],
        pinned=[f"pinned-{i}" for i in range(10)],
    )


# =============================================================================
# Fixtures for ArticleInteraction
# =============================================================================


@pytest.fixture
def interaction_default():
    """Create a default ArticleInteraction."""
    return ArticleInteraction(article_id="article-1")


@pytest.fixture
def interaction_expanded():
    """Create an ArticleInteraction with expanded=True."""
    return ArticleInteraction(
        article_id="article-1",
        expanded=True,
        time_spent=30.5,
    )


@pytest.fixture
def interaction_saved():
    """Create an ArticleInteraction with saved=True."""
    return ArticleInteraction(
        article_id="article-2",
        saved=True,
    )


@pytest.fixture
def interaction_shared():
    """Create an ArticleInteraction with shared=True."""
    return ArticleInteraction(
        article_id="article-3",
        shared=True,
    )


@pytest.fixture
def interaction_skipped():
    """Create an ArticleInteraction with skipped=True."""
    return ArticleInteraction(
        article_id="article-4",
        skipped=True,
    )


@pytest.fixture
def interaction_thumbs_up():
    """Create an ArticleInteraction with positive feedback."""
    return ArticleInteraction(
        article_id="article-5",
        expanded=True,
        thumbs_up=True,
        relevance_score=0.9,
    )


@pytest.fixture
def interaction_thumbs_down():
    """Create an ArticleInteraction with negative feedback."""
    return ArticleInteraction(
        article_id="article-6",
        thumbs_up=False,
        relevance_score=0.2,
    )


@pytest.fixture
def interaction_full():
    """Create an ArticleInteraction with all fields populated."""
    return ArticleInteraction(
        article_id="article-7",
        timestamp=datetime.now() - timedelta(hours=1),
        expanded=True,
        time_spent=120.5,
        saved=True,
        shared=True,
        skipped=False,
        thumbs_up=True,
        relevance_score=0.95,
    )


@pytest.fixture
def interaction_old():
    """Create an old ArticleInteraction."""
    return ArticleInteraction(
        article_id="article-old",
        timestamp=datetime.now() - timedelta(days=100),
        expanded=True,
    )


@pytest.fixture
def interaction_recent():
    """Create a recent ArticleInteraction."""
    return ArticleInteraction(
        article_id="article-recent",
        timestamp=datetime.now() - timedelta(minutes=30),
        expanded=True,
        saved=True,
    )


@pytest.fixture
def interactions_bulk():
    """Create multiple ArticleInteractions for bulk testing."""
    base_time = datetime.now()
    return [
        ArticleInteraction(
            article_id=f"article-bulk-{i}",
            timestamp=base_time - timedelta(hours=i),
            expanded=i % 2 == 0,
            saved=i % 3 == 0,
            skipped=i % 5 == 0,
            time_spent=float(i * 10) if i % 2 == 0 else None,
        )
        for i in range(20)
    ]


# =============================================================================
# Fixtures for UserContextStore
# =============================================================================


@pytest.fixture
def context_store(temp_profile_path, temp_db):
    """Create a UserContextStore with temp paths."""
    return UserContextStore(profile_path=temp_profile_path, db_path=temp_db)


@pytest.fixture
def context_store_empty(temp_profile_path, temp_db):
    """Create an empty UserContextStore."""
    return UserContextStore(profile_path=temp_profile_path, db_path=temp_db)


@pytest.fixture
def context_store_with_profile(temp_profile_path_existing, temp_db, profile_developer):
    """Create a UserContextStore with a saved profile."""
    store = UserContextStore(profile_path=temp_profile_path_existing, db_path=temp_db)
    store.save_profile(profile_developer)
    return store


@pytest.fixture
def context_store_with_interactions(temp_profile_path, temp_db, interactions_bulk):
    """Create a UserContextStore with recorded interactions."""
    store = UserContextStore(profile_path=temp_profile_path, db_path=temp_db)
    for interaction in interactions_bulk:
        store.record_interaction(interaction)
    return store


@pytest.fixture
def context_store_full(temp_profile_path_existing, temp_db, profile_developer, interactions_bulk):
    """Create a UserContextStore with profile and interactions."""
    store = UserContextStore(profile_path=temp_profile_path_existing, db_path=temp_db)
    store.save_profile(profile_developer)
    for interaction in interactions_bulk:
        store.record_interaction(interaction)
    return store


# =============================================================================
# Fixtures for Mock UserContextStore
# =============================================================================


@pytest.fixture
def mock_context_store():
    """Create a mock UserContextStore."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    store.get_interactions.return_value = []
    store.get_topic_engagement.return_value = {}
    return store


@pytest.fixture
def mock_context_store_with_profile(profile_developer):
    """Create a mock UserContextStore with a profile."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = profile_developer
    store.get_interactions.return_value = []
    store.get_topic_engagement.return_value = {}
    return store


@pytest.fixture
def mock_context_store_with_engagement():
    """Create a mock UserContextStore with topic engagement data."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    store.get_interactions.return_value = []
    store.get_topic_engagement.return_value = {
        "AI": 0.8,
        "Python": 0.7,
        "technology": 0.6,
        "security": 0.5,
    }
    return store


@pytest.fixture
def mock_context_store_with_history(interactions_bulk):
    """Create a mock UserContextStore with interaction history."""
    store = MagicMock(spec=UserContextStore)
    store.load_profile.return_value = UserContextProfile()
    store.get_interactions.return_value = interactions_bulk[:10]
    store.get_topic_engagement.return_value = {"AI": 0.6, "tech": 0.4}
    return store


# =============================================================================
# Fixtures for Sample Articles (for relevance testing)
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
        content="A major technology company has announced a groundbreaking new AI product.",
        summary="Major tech company announces new AI product launch.",
        trend_tags="AI,technology,product launch",
    )


@pytest.fixture
def sample_article_ai():
    """Create an AI-focused sample article."""
    return Article(
        id="article-ai-1",
        feed_url="https://techblog.example.com/feed.xml",
        title="New Advances in Machine Learning and AI Research",
        link="https://techblog.example.com/article-1",
        published=datetime.now() - timedelta(hours=2),
        content="Researchers have made significant advances in machine learning.",
        summary="ML research advances.",
        trend_tags="AI,machine learning,research",
    )


@pytest.fixture
def sample_article_python():
    """Create a Python-focused sample article."""
    return Article(
        id="article-python-1",
        feed_url="https://pythonblog.example.com/feed.xml",
        title="Python 4.0 Release Candidate Available for Testing",
        link="https://pythonblog.example.com/article-1",
        published=datetime.now() - timedelta(hours=1),
        content="Python 4.0 RC is now available with new features.",
        summary="Python 4.0 RC released.",
        trend_tags="Python,programming,release",
    )


@pytest.fixture
def sample_article_security():
    """Create a security-focused sample article."""
    return Article(
        id="article-security-1",
        feed_url="https://security.example.com/feed.xml",
        title="Critical Security Vulnerability Discovered in Popular Library",
        link="https://security.example.com/article-1",
        published=datetime.now() - timedelta(minutes=30),
        content="A critical vulnerability has been found.",
        summary="Critical security vulnerability found.",
        trend_tags="security,vulnerability,CVE",
    )


@pytest.fixture
def sample_article_celebrity():
    """Create a celebrity news article (typically ignored)."""
    return Article(
        id="article-celebrity-1",
        feed_url="https://entertainment.example.com/feed.xml",
        title="Celebrity Couple Announces Engagement",
        link="https://entertainment.example.com/article-1",
        published=datetime.now(),
        content="Famous celebrity couple announces their engagement.",
        summary="Celebrity engagement announced.",
        trend_tags="celebrity news,entertainment",
    )


@pytest.fixture
def sample_article_sports():
    """Create a sports article (typically ignored)."""
    return Article(
        id="article-sports-1",
        feed_url="https://sports.example.com/feed.xml",
        title="Team Wins Championship in Overtime",
        link="https://sports.example.com/article-1",
        published=datetime.now(),
        content="The team won the championship in dramatic fashion.",
        summary="Team wins championship.",
        trend_tags="sports,championship",
    )


@pytest.fixture
def sample_article_no_tags():
    """Create an article without trend tags."""
    return Article(
        id="article-no-tags-1",
        feed_url="https://example.com/feed.xml",
        title="Interesting Article About Something",
        link="https://example.com/article-1",
        published=datetime.now(),
        content="This article is about something interesting.",
        summary="An interesting article.",
        trend_tags=None,
    )


@pytest.fixture
def sample_article_empty_tags():
    """Create an article with empty trend tags."""
    return Article(
        id="article-empty-tags-1",
        feed_url="https://example.com/feed.xml",
        title="Article With Empty Tags",
        link="https://example.com/article-1",
        published=datetime.now(),
        content="This article has empty tags.",
        summary="Empty tags article.",
        trend_tags="",
    )


@pytest.fixture
def sample_article_unicode():
    """Create an article with unicode content."""
    return Article(
        id="article-unicode-1",
        feed_url="https://example.com/feed.xml",
        title="Tecnologia de inteligencia artificial avanza",
        link="https://example.com/article-1",
        published=datetime.now(),
        content="La tecnologia de IA ha avanzado significativamente.",
        summary="Avances en IA.",
        trend_tags="AI,tecnologia,inteligencia artificial",
    )


@pytest.fixture
def sample_articles_bulk():
    """Create multiple sample articles for bulk testing."""
    base_time = datetime.now()
    return [
        Article(
            id=f"article-bulk-{i}",
            feed_url=f"https://source{i % 5}.example.com/feed.xml",
            title=f"Article {i} About {'AI' if i % 2 == 0 else 'Python'}",
            link=f"https://example.com/article-{i}",
            published=base_time - timedelta(hours=i),
            content=f"Content of article {i}.",
            summary=f"Summary of article {i}.",
            trend_tags="AI,technology" if i % 2 == 0 else "Python,programming",
        )
        for i in range(20)
    ]


@pytest.fixture
def sample_articles_diverse():
    """Create articles with diverse topics for diversity testing."""
    return [
        Article(
            id="article-div-ai",
            feed_url="https://example.com/feed.xml",
            title="AI Article",
            link="https://example.com/ai",
            published=datetime.now(),
            content="AI content.",
            summary="AI summary.",
            trend_tags="AI",
        ),
        Article(
            id="article-div-python",
            feed_url="https://example.com/feed.xml",
            title="Python Article",
            link="https://example.com/python",
            published=datetime.now(),
            content="Python content.",
            summary="Python summary.",
            trend_tags="Python",
        ),
        Article(
            id="article-div-security",
            feed_url="https://example.com/feed.xml",
            title="Security Article",
            link="https://example.com/security",
            published=datetime.now(),
            content="Security content.",
            summary="Security summary.",
            trend_tags="security",
        ),
        Article(
            id="article-div-new",
            feed_url="https://example.com/feed.xml",
            title="New Topic Article",
            link="https://example.com/new",
            published=datetime.now(),
            content="New topic content.",
            summary="New topic summary.",
            trend_tags="new topic,never seen before",
        ),
    ]


# =============================================================================
# Fixtures for RelevanceEngine
# =============================================================================


@pytest.fixture
def relevance_engine(context_store):
    """Create a RelevanceEngine with default store."""
    return RelevanceEngine(context_store)


@pytest.fixture
def relevance_engine_empty(context_store_empty):
    """Create a RelevanceEngine with empty store."""
    return RelevanceEngine(context_store_empty)


@pytest.fixture
def relevance_engine_with_data(context_store_full):
    """Create a RelevanceEngine with populated store."""
    return RelevanceEngine(context_store_full)


@pytest.fixture
def relevance_engine_mock(mock_context_store):
    """Create a RelevanceEngine with mock store."""
    return RelevanceEngine(mock_context_store)


@pytest.fixture
def relevance_engine_with_engagement(mock_context_store_with_engagement):
    """Create a RelevanceEngine with engagement data."""
    return RelevanceEngine(mock_context_store_with_engagement)


# =============================================================================
# Fixtures for Profile JSON Data
# =============================================================================


@pytest.fixture
def profile_json_valid():
    """Create valid profile JSON data."""
    return {
        "role": "developer",
        "current_projects": ["project1", "project2"],
        "watching": ["AI", "Python"],
        "ignore": ["sports"],
        "pinned": ["security"],
        "relevance_threshold": 0.35,
        "diversity_factor": 0.2,
        "personalization_strength": 0.85,
        "created_at": "2024-01-01T12:00:00",
        "last_updated": "2024-01-15T18:30:00",
        "_version": 1,
    }


@pytest.fixture
def profile_json_minimal():
    """Create minimal profile JSON data."""
    return {
        "_version": 1,
    }


@pytest.fixture
def profile_json_invalid():
    """Create invalid profile JSON data."""
    return {
        "role": 12345,  # Should be string
        "current_projects": "not a list",  # Should be list
        "relevance_threshold": "high",  # Should be float
        "_version": 1,
    }


@pytest.fixture
def profile_json_old_version():
    """Create profile JSON with old version."""
    return {
        "role": "user",
        "_version": 0,
    }


@pytest.fixture
def profile_json_future_version():
    """Create profile JSON with future version."""
    return {
        "role": "user",
        "_version": 99,
    }


# =============================================================================
# Fixtures for Interaction Export/Import Data
# =============================================================================


@pytest.fixture
def export_data_valid():
    """Create valid export data structure."""
    return {
        "profile": {
            "role": "developer",
            "current_projects": ["project1"],
            "watching": ["AI"],
            "ignore": [],
            "pinned": [],
            "relevance_threshold": 0.3,
            "diversity_factor": 0.15,
            "personalization_strength": 0.8,
            "created_at": "2024-01-01T12:00:00",
            "last_updated": "2024-01-15T18:30:00",
        },
        "interactions": [
            {
                "article_id": "article-1",
                "timestamp": "2024-01-15T10:00:00",
                "expanded": True,
                "time_spent": 30.5,
                "saved": False,
                "shared": False,
                "skipped": False,
                "thumbs_up": True,
                "relevance_score": 0.8,
            },
        ],
        "version": 1,
    }


@pytest.fixture
def export_data_empty():
    """Create empty export data structure."""
    return {
        "profile": {
            "role": None,
            "current_projects": [],
            "watching": [],
            "ignore": [],
            "pinned": [],
            "relevance_threshold": 0.3,
            "diversity_factor": 0.15,
            "personalization_strength": 0.8,
        },
        "interactions": [],
        "version": 1,
    }


@pytest.fixture
def export_data_many_interactions():
    """Create export data with many interactions."""
    interactions = [
        {
            "article_id": f"article-{i}",
            "timestamp": f"2024-01-{15 - i % 14:02d}T10:00:00",
            "expanded": i % 2 == 0,
            "time_spent": float(i * 10) if i % 3 == 0 else None,
            "saved": i % 5 == 0,
            "shared": False,
            "skipped": i % 4 == 0,
            "thumbs_up": True if i % 2 == 0 else (False if i % 3 == 0 else None),
            "relevance_score": round(0.5 + (i % 5) * 0.1, 2),
        }
        for i in range(50)
    ]
    return {
        "profile": {"role": "heavy user"},
        "interactions": interactions,
        "version": 1,
    }


# =============================================================================
# Fixtures for Edge Cases
# =============================================================================


@pytest.fixture
def profile_edge_case_empty_strings():
    """Create a profile with empty strings."""
    return UserContextProfile(
        role="",
        current_projects=["", "valid project", ""],
        watching=["", "valid topic"],
        ignore=[""],
        pinned=[""],
    )


@pytest.fixture
def profile_edge_case_whitespace():
    """Create a profile with whitespace strings."""
    return UserContextProfile(
        role="   user   ",
        current_projects=["  project  ", "\tproject2\t"],
        watching=["  topic  "],
        ignore=["  ignored  "],
        pinned=["  pinned  "],
    )


@pytest.fixture
def sample_article_edge_case_long_title():
    """Create an article with very long title."""
    return Article(
        id="article-long-title",
        feed_url="https://example.com/feed.xml",
        title="A" * 500 + " AI Technology " + "B" * 500,
        link="https://example.com/article",
        published=datetime.now(),
        content="Content with long title.",
        summary="Summary.",
        trend_tags="AI",
    )


@pytest.fixture
def sample_article_edge_case_no_content():
    """Create an article with no content."""
    return Article(
        id="article-no-content",
        feed_url="https://example.com/feed.xml",
        title="No Content Article",
        link="https://example.com/article",
        published=datetime.now(),
        content=None,
        summary=None,
        trend_tags=None,
    )


@pytest.fixture
def sample_article_edge_case_empty_content():
    """Create an article with empty content."""
    return Article(
        id="article-empty-content",
        feed_url="https://example.com/feed.xml",
        title="",
        link="https://example.com/article",
        published=datetime.now(),
        content="",
        summary="",
        trend_tags="",
    )


# =============================================================================
# Fixtures for Mock Articles (simpler objects for relevance testing)
# =============================================================================


@pytest.fixture
def mock_article_ai():
    """Create a mock article with AI topic."""
    article = MagicMock()
    article.id = "mock-ai"
    article.title = "AI Technology Breakthrough"
    article.trend_tags = "AI,technology"
    return article


@pytest.fixture
def mock_article_python():
    """Create a mock article with Python topic."""
    article = MagicMock()
    article.id = "mock-python"
    article.title = "Python Programming Guide"
    article.trend_tags = "Python,programming"
    return article


@pytest.fixture
def mock_article_ignored():
    """Create a mock article with ignored topic."""
    article = MagicMock()
    article.id = "mock-ignored"
    article.title = "Celebrity News Today"
    article.trend_tags = "celebrity news,entertainment"
    return article


@pytest.fixture
def mock_article_no_attrs():
    """Create a mock article without trend_tags or title attributes."""
    article = MagicMock(spec=[])  # Empty spec = no attributes
    article.id = "mock-no-attrs"
    return article


# =============================================================================
# Fixtures for Integration Testing
# =============================================================================


@pytest.fixture
def full_user_context_setup(temp_profile_path_existing, temp_db, profile_developer):
    """Create a full user context setup for integration tests."""
    store = UserContextStore(profile_path=temp_profile_path_existing, db_path=temp_db)
    store.save_profile(profile_developer)

    # Add some interactions
    interactions = [
        ArticleInteraction(
            article_id="article-ai-1",
            timestamp=datetime.now() - timedelta(days=1),
            expanded=True,
            saved=True,
        ),
        ArticleInteraction(
            article_id="article-python-1",
            timestamp=datetime.now() - timedelta(days=2),
            expanded=True,
            time_spent=60.0,
        ),
        ArticleInteraction(
            article_id="article-skipped-1",
            timestamp=datetime.now() - timedelta(days=3),
            skipped=True,
        ),
    ]
    for interaction in interactions:
        store.record_interaction(interaction)

    engine = RelevanceEngine(store)
    return {
        "store": store,
        "engine": engine,
        "profile": profile_developer,
    }


@pytest.fixture
def relevance_test_setup(mock_context_store_with_engagement, profile_developer):
    """Create a setup for relevance testing with engagement data."""
    engine = RelevanceEngine(mock_context_store_with_engagement)
    return {
        "engine": engine,
        "profile": profile_developer,
        "store": mock_context_store_with_engagement,
    }


@pytest.fixture
def diversity_test_articles():
    """Create articles for diversity filter testing."""
    return [
        # High relevance articles (first)
        MagicMock(id="high-1", relevance_score=0.95),
        MagicMock(id="high-2", relevance_score=0.90),
        MagicMock(id="high-3", relevance_score=0.85),
        MagicMock(id="high-4", relevance_score=0.80),
        # Medium relevance articles
        MagicMock(id="med-1", relevance_score=0.60),
        MagicMock(id="med-2", relevance_score=0.55),
        # Low relevance articles (diverse)
        MagicMock(id="low-1", relevance_score=0.30),
        MagicMock(id="low-2", relevance_score=0.25),
        MagicMock(id="low-3", relevance_score=0.20),
        MagicMock(id="low-4", relevance_score=0.15),
    ]


# =============================================================================
# Fixtures for Time-based Testing
# =============================================================================


@pytest.fixture
def interaction_one_week_ago():
    """Create an interaction from one week ago."""
    return ArticleInteraction(
        article_id="article-week-old",
        timestamp=datetime.now() - timedelta(days=7),
        expanded=True,
    )


@pytest.fixture
def interaction_one_month_ago():
    """Create an interaction from one month ago."""
    return ArticleInteraction(
        article_id="article-month-old",
        timestamp=datetime.now() - timedelta(days=30),
        expanded=True,
    )


@pytest.fixture
def interaction_three_months_ago():
    """Create an interaction from three months ago."""
    return ArticleInteraction(
        article_id="article-3months-old",
        timestamp=datetime.now() - timedelta(days=90),
        expanded=True,
    )


@pytest.fixture
def interaction_one_year_ago():
    """Create an interaction from one year ago."""
    return ArticleInteraction(
        article_id="article-year-old",
        timestamp=datetime.now() - timedelta(days=365),
        expanded=True,
    )


# =============================================================================
# Test Classes (to be implemented in subsequent subtasks)
# =============================================================================

# Tests for UserContextProfile will be added in subtask 5.2
# Tests for UserContextStore will be added in subtask 5.2
# Tests for RelevanceEngine will be added in subtask 5.3
# Tests for sort_by_relevance will be added in subtask 5.3
# Tests for apply_diversity_filter will be added in subtask 5.3
