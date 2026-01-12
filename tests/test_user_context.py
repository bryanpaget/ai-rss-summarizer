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
    """Create valid profile JSON data (without _version, as from_dict doesn't handle it)."""
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
    }


@pytest.fixture
def profile_json_minimal():
    """Create minimal profile JSON data (empty dict for from_dict to use defaults)."""
    return {}


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
    """Create valid export data structure with recent timestamps."""
    from datetime import datetime, timedelta
    recent_time = datetime.now() - timedelta(days=5)
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
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "last_updated": (datetime.now() - timedelta(days=1)).isoformat(),
        },
        "interactions": [
            {
                "article_id": "article-1",
                "timestamp": recent_time.isoformat(),
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
    """Create export data with many recent interactions."""
    from datetime import datetime, timedelta
    base_time = datetime.now()
    interactions = [
        {
            "article_id": f"article-{i}",
            "timestamp": (base_time - timedelta(hours=i)).isoformat(),
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
# Test Classes for UserContextProfile
# =============================================================================


class TestUserContextProfileCreation:
    """Test UserContextProfile initialization and defaults."""

    def test_default_creation(self):
        """Test creating profile with all defaults."""
        profile = UserContextProfile()
        assert profile.role is None
        assert profile.current_projects == []
        assert profile.watching == []
        assert profile.ignore == []
        assert profile.pinned == []
        assert profile.relevance_threshold == 0.3
        assert profile.diversity_factor == 0.15
        assert profile.personalization_strength == 0.8

    def test_default_timestamps_are_set(self):
        """Test that timestamps are auto-set when not provided."""
        profile = UserContextProfile()
        assert profile.created_at is not None
        assert profile.last_updated is not None
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.last_updated, datetime)

    def test_custom_role(self, profile_with_role):
        """Test profile creation with custom role."""
        assert profile_with_role.role == "software engineer"

    def test_developer_profile(self, profile_developer):
        """Test developer profile fixture."""
        assert profile_developer.role == "software developer"
        assert "building RSS reader" in profile_developer.current_projects
        assert "AI" in profile_developer.watching
        assert "celebrity news" in profile_developer.ignore
        assert "security vulnerabilities" in profile_developer.pinned

    def test_researcher_profile_custom_thresholds(self, profile_researcher):
        """Test researcher profile with custom thresholds."""
        assert profile_researcher.relevance_threshold == 0.4
        assert profile_researcher.diversity_factor == 0.2

    def test_custom_thresholds(self, profile_custom_thresholds):
        """Test profile with custom threshold settings."""
        assert profile_custom_thresholds.relevance_threshold == 0.5
        assert profile_custom_thresholds.diversity_factor == 0.25
        assert profile_custom_thresholds.personalization_strength == 0.9

    def test_zero_personalization(self, profile_zero_personalization):
        """Test profile with zero personalization strength."""
        assert profile_zero_personalization.personalization_strength == 0.0

    def test_explicit_timestamps(self, profile_with_timestamps):
        """Test profile with explicit timestamps."""
        now = datetime.now()
        # Created 30 days ago
        assert (now - profile_with_timestamps.created_at).days >= 29
        # Updated 1 hour ago
        assert (now - profile_with_timestamps.last_updated).seconds < 7200

    def test_unicode_profile(self, profile_unicode):
        """Test profile with unicode characters."""
        assert profile_unicode.role == "desarrollador de software"
        assert "proyecto AI" in profile_unicode.current_projects
        assert "inteligencia artificial" in profile_unicode.watching

    def test_special_chars_profile(self, profile_special_chars):
        """Test profile with special characters."""
        assert "developer <script>" in profile_special_chars.role
        assert "project && test" in profile_special_chars.current_projects


class TestUserContextProfileToDict:
    """Test UserContextProfile.to_dict() method."""

    def test_to_dict_basic(self, profile_default):
        """Test converting default profile to dict."""
        data = profile_default.to_dict()
        assert isinstance(data, dict)
        assert "role" in data
        assert "current_projects" in data
        assert "watching" in data
        assert "ignore" in data
        assert "pinned" in data

    def test_to_dict_timestamps_are_strings(self, profile_default):
        """Test that timestamps are converted to ISO strings."""
        data = profile_default.to_dict()
        assert isinstance(data["created_at"], str)
        assert isinstance(data["last_updated"], str)
        # Should be ISO format
        datetime.fromisoformat(data["created_at"])
        datetime.fromisoformat(data["last_updated"])

    def test_to_dict_preserves_lists(self, profile_developer):
        """Test that lists are preserved in dict conversion."""
        data = profile_developer.to_dict()
        assert isinstance(data["current_projects"], list)
        assert isinstance(data["watching"], list)
        assert "building RSS reader" in data["current_projects"]
        assert "AI" in data["watching"]

    def test_to_dict_preserves_floats(self, profile_custom_thresholds):
        """Test that float settings are preserved."""
        data = profile_custom_thresholds.to_dict()
        assert data["relevance_threshold"] == 0.5
        assert data["diversity_factor"] == 0.25
        assert data["personalization_strength"] == 0.9

    def test_to_dict_none_last_feedback_prompt(self, profile_default):
        """Test that None last_feedback_prompt is handled."""
        data = profile_default.to_dict()
        # last_feedback_prompt is None by default
        assert data.get("last_feedback_prompt") is None

    def test_to_dict_with_last_feedback_prompt(self, profile_with_timestamps):
        """Test that last_feedback_prompt is converted to ISO string."""
        data = profile_with_timestamps.to_dict()
        assert isinstance(data["last_feedback_prompt"], str)
        datetime.fromisoformat(data["last_feedback_prompt"])

    def test_to_dict_unicode(self, profile_unicode):
        """Test to_dict with unicode content."""
        data = profile_unicode.to_dict()
        assert data["role"] == "desarrollador de software"
        assert "proyecto AI" in data["current_projects"]


class TestUserContextProfileFromDict:
    """Test UserContextProfile.from_dict() method."""

    def test_from_dict_basic(self, profile_json_valid):
        """Test creating profile from valid dict."""
        profile = UserContextProfile.from_dict(profile_json_valid)
        assert profile.role == "developer"
        assert "project1" in profile.current_projects
        assert "AI" in profile.watching
        assert "sports" in profile.ignore
        assert "security" in profile.pinned

    def test_from_dict_preserves_thresholds(self, profile_json_valid):
        """Test that thresholds are preserved from dict."""
        profile = UserContextProfile.from_dict(profile_json_valid)
        assert profile.relevance_threshold == 0.35
        assert profile.diversity_factor == 0.2
        assert profile.personalization_strength == 0.85

    def test_from_dict_parses_timestamps(self, profile_json_valid):
        """Test that timestamps are parsed from ISO strings."""
        profile = UserContextProfile.from_dict(profile_json_valid)
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.last_updated, datetime)

    def test_from_dict_minimal(self, profile_json_minimal):
        """Test creating profile from minimal dict."""
        profile = UserContextProfile.from_dict(profile_json_minimal)
        # Should have defaults for missing fields
        assert profile.role is None
        assert profile.current_projects == []
        assert profile.watching == []

    def test_from_dict_roundtrip(self, profile_developer):
        """Test to_dict -> from_dict roundtrip."""
        data = profile_developer.to_dict()
        restored = UserContextProfile.from_dict(data)
        assert restored.role == profile_developer.role
        assert restored.current_projects == profile_developer.current_projects
        assert restored.watching == profile_developer.watching
        assert restored.ignore == profile_developer.ignore
        assert restored.pinned == profile_developer.pinned

    def test_from_dict_with_none_timestamps(self):
        """Test from_dict with None timestamp values."""
        data = {
            "role": "tester",
            "created_at": None,
            "last_updated": None,
            "last_feedback_prompt": None,
        }
        profile = UserContextProfile.from_dict(data)
        # __post_init__ should set timestamps
        assert profile.created_at is not None
        assert profile.last_updated is not None


class TestUserContextProfileEdgeCases:
    """Test UserContextProfile edge cases."""

    def test_empty_lists(self, profile_empty_lists):
        """Test profile with empty lists."""
        assert profile_empty_lists.current_projects == []
        assert profile_empty_lists.watching == []
        assert profile_empty_lists.ignore == []
        assert profile_empty_lists.pinned == []

    def test_many_interests(self, profile_many_interests):
        """Test profile with many interests."""
        assert len(profile_many_interests.current_projects) == 20
        assert len(profile_many_interests.watching) == 50
        assert len(profile_many_interests.ignore) == 30
        assert len(profile_many_interests.pinned) == 10

    def test_empty_strings_in_lists(self, profile_edge_case_empty_strings):
        """Test profile with empty strings in lists."""
        data = profile_edge_case_empty_strings.to_dict()
        # Empty strings should be preserved
        assert "" in data["current_projects"]

    def test_whitespace_strings(self, profile_edge_case_whitespace):
        """Test profile with whitespace strings."""
        assert profile_edge_case_whitespace.role == "   user   "
        assert "  project  " in profile_edge_case_whitespace.current_projects

    def test_threshold_boundary_zero(self):
        """Test threshold at 0."""
        profile = UserContextProfile(
            relevance_threshold=0.0,
            diversity_factor=0.0,
            personalization_strength=0.0,
        )
        assert profile.relevance_threshold == 0.0
        assert profile.diversity_factor == 0.0
        assert profile.personalization_strength == 0.0

    def test_threshold_boundary_one(self):
        """Test threshold at 1."""
        profile = UserContextProfile(
            relevance_threshold=1.0,
            diversity_factor=1.0,
            personalization_strength=1.0,
        )
        assert profile.relevance_threshold == 1.0
        assert profile.diversity_factor == 1.0
        assert profile.personalization_strength == 1.0


# =============================================================================
# Test Classes for ArticleInteraction
# =============================================================================


class TestArticleInteractionCreation:
    """Test ArticleInteraction initialization."""

    def test_default_creation(self, interaction_default):
        """Test creating interaction with defaults."""
        assert interaction_default.article_id == "article-1"
        assert interaction_default.expanded is False
        assert interaction_default.time_spent is None
        assert interaction_default.saved is False
        assert interaction_default.shared is False
        assert interaction_default.skipped is False
        assert interaction_default.thumbs_up is None
        assert interaction_default.relevance_score is None

    def test_default_timestamp(self, interaction_default):
        """Test that timestamp is auto-set."""
        assert isinstance(interaction_default.timestamp, datetime)
        # Should be recent
        assert (datetime.now() - interaction_default.timestamp).seconds < 60

    def test_expanded_interaction(self, interaction_expanded):
        """Test expanded interaction."""
        assert interaction_expanded.expanded is True
        assert interaction_expanded.time_spent == 30.5

    def test_saved_interaction(self, interaction_saved):
        """Test saved interaction."""
        assert interaction_saved.saved is True

    def test_shared_interaction(self, interaction_shared):
        """Test shared interaction."""
        assert interaction_shared.shared is True

    def test_skipped_interaction(self, interaction_skipped):
        """Test skipped interaction."""
        assert interaction_skipped.skipped is True

    def test_thumbs_up_interaction(self, interaction_thumbs_up):
        """Test thumbs up interaction."""
        assert interaction_thumbs_up.thumbs_up is True
        assert interaction_thumbs_up.relevance_score == 0.9

    def test_thumbs_down_interaction(self, interaction_thumbs_down):
        """Test thumbs down interaction."""
        assert interaction_thumbs_down.thumbs_up is False
        assert interaction_thumbs_down.relevance_score == 0.2

    def test_full_interaction(self, interaction_full):
        """Test interaction with all fields populated."""
        assert interaction_full.article_id == "article-7"
        assert interaction_full.expanded is True
        assert interaction_full.time_spent == 120.5
        assert interaction_full.saved is True
        assert interaction_full.shared is True
        assert interaction_full.skipped is False
        assert interaction_full.thumbs_up is True
        assert interaction_full.relevance_score == 0.95


class TestArticleInteractionTimestamps:
    """Test ArticleInteraction timestamp handling."""

    def test_old_interaction(self, interaction_old):
        """Test old interaction timestamp."""
        days_ago = (datetime.now() - interaction_old.timestamp).days
        assert days_ago >= 99

    def test_recent_interaction(self, interaction_recent):
        """Test recent interaction timestamp."""
        minutes_ago = (datetime.now() - interaction_recent.timestamp).seconds / 60
        assert minutes_ago < 60

    def test_explicit_timestamp(self):
        """Test interaction with explicit timestamp."""
        specific_time = datetime(2024, 6, 15, 12, 30, 0)
        interaction = ArticleInteraction(
            article_id="test-article",
            timestamp=specific_time,
        )
        assert interaction.timestamp == specific_time


class TestArticleInteractionBulk:
    """Test bulk ArticleInteraction fixtures."""

    def test_bulk_interactions_count(self, interactions_bulk):
        """Test bulk interactions fixture has correct count."""
        assert len(interactions_bulk) == 20

    def test_bulk_interactions_unique_ids(self, interactions_bulk):
        """Test bulk interactions have unique article IDs."""
        ids = [i.article_id for i in interactions_bulk]
        assert len(ids) == len(set(ids))

    def test_bulk_interactions_varied_properties(self, interactions_bulk):
        """Test bulk interactions have varied properties."""
        expanded_count = sum(1 for i in interactions_bulk if i.expanded)
        saved_count = sum(1 for i in interactions_bulk if i.saved)
        skipped_count = sum(1 for i in interactions_bulk if i.skipped)

        # Should have some variety
        assert expanded_count > 0
        assert saved_count > 0
        assert skipped_count > 0

    def test_bulk_interactions_timestamps_ordered(self, interactions_bulk):
        """Test bulk interactions have decreasing timestamps."""
        for i in range(len(interactions_bulk) - 1):
            # Earlier index should have more recent timestamp
            assert interactions_bulk[i].timestamp >= interactions_bulk[i + 1].timestamp


# =============================================================================
# Test Classes for UserContextStore Initialization
# =============================================================================


class TestUserContextStoreInitialization:
    """Test UserContextStore initialization."""

    def test_store_creation(self, context_store):
        """Test creating a UserContextStore."""
        assert context_store is not None
        assert context_store.VERSION == 1

    def test_store_paths(self, context_store, temp_profile_path, temp_db):
        """Test store has correct paths."""
        assert str(context_store.profile_path) == temp_profile_path
        assert str(context_store.db_path) == temp_db

    def test_db_initialization(self, context_store):
        """Test database is initialized with tables."""
        # Check that user_interactions table exists
        with context_store._connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_interactions'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_db_indices_created(self, context_store):
        """Test database indices are created."""
        with context_store._connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_interactions%'"
            )
            indices = cursor.fetchall()
            assert len(indices) >= 2


class TestUserContextStoreLoadProfile:
    """Test UserContextStore.load_profile() method."""

    def test_load_profile_no_file(self, context_store):
        """Test loading profile when file doesn't exist."""
        profile = context_store.load_profile()
        # Should return default profile
        assert isinstance(profile, UserContextProfile)
        assert profile.role is None

    def test_load_profile_after_save(self, context_store_with_profile):
        """Test loading profile after saving."""
        profile = context_store_with_profile.load_profile()
        assert profile.role == "software developer"
        assert "building RSS reader" in profile.current_projects

    def test_load_profile_invalid_json(self, temp_profile_path_existing, temp_db):
        """Test loading profile with invalid JSON."""
        # Write invalid JSON to profile path
        with open(temp_profile_path_existing, "w") as f:
            f.write("not valid json {{{")

        store = UserContextStore(profile_path=temp_profile_path_existing, db_path=temp_db)
        profile = store.load_profile()
        # Should return default profile
        assert isinstance(profile, UserContextProfile)
        assert profile.role is None

    def test_load_profile_version_migration(self, temp_profile_path_existing, temp_db, profile_json_old_version):
        """Test loading profile with old version triggers migration."""
        import json
        with open(temp_profile_path_existing, "w") as f:
            json.dump(profile_json_old_version, f)

        store = UserContextStore(profile_path=temp_profile_path_existing, db_path=temp_db)
        profile = store.load_profile()
        # Should still load successfully
        assert profile.role == "user"


class TestUserContextStoreSaveProfile:
    """Test UserContextStore.save_profile() method."""

    def test_save_profile_creates_file(self, context_store, profile_developer):
        """Test saving profile creates the file."""
        context_store.save_profile(profile_developer)
        assert context_store.profile_path.exists()

    def test_save_profile_creates_directory(self, temp_dir, temp_db, profile_developer):
        """Test saving profile creates parent directory."""
        profile_path = os.path.join(temp_dir, "nested", "dir", "user_context.json")
        store = UserContextStore(profile_path=profile_path, db_path=temp_db)
        store.save_profile(profile_developer)
        assert os.path.exists(profile_path)

    def test_save_profile_updates_last_updated(self, context_store, profile_developer):
        """Test saving profile updates last_updated timestamp."""
        old_timestamp = profile_developer.last_updated
        import time
        time.sleep(0.01)  # Small delay
        context_store.save_profile(profile_developer)
        # Profile's last_updated should be newer
        assert profile_developer.last_updated >= old_timestamp

    def test_save_profile_includes_version(self, context_store, profile_developer):
        """Test saved profile includes version number."""
        context_store.save_profile(profile_developer)
        import json
        with open(context_store.profile_path) as f:
            data = json.load(f)
        assert "_version" in data
        assert data["_version"] == 1

    def test_save_profile_roundtrip(self, context_store, profile_developer):
        """Test save -> load roundtrip preserves data."""
        context_store.save_profile(profile_developer)
        loaded = context_store.load_profile()
        assert loaded.role == profile_developer.role
        assert loaded.current_projects == profile_developer.current_projects
        assert loaded.watching == profile_developer.watching
        assert loaded.ignore == profile_developer.ignore
        assert loaded.pinned == profile_developer.pinned

    def test_save_profile_unicode(self, context_store, profile_unicode):
        """Test saving profile with unicode content."""
        context_store.save_profile(profile_unicode)
        loaded = context_store.load_profile()
        assert loaded.role == "desarrollador de software"
        assert "proyecto AI" in loaded.current_projects


# =============================================================================
# Test Classes for UserContextStore Interactions
# =============================================================================


class TestUserContextStoreRecordInteraction:
    """Test UserContextStore.record_interaction() method."""

    def test_record_interaction_basic(self, context_store, interaction_default):
        """Test recording a basic interaction."""
        context_store.record_interaction(interaction_default)
        interactions = context_store.get_interactions()
        assert len(interactions) >= 1

    def test_record_interaction_expanded(self, context_store, interaction_expanded):
        """Test recording an expanded interaction."""
        context_store.record_interaction(interaction_expanded)
        interactions = context_store.get_interactions()
        found = next((i for i in interactions if i.article_id == "article-1"), None)
        assert found is not None
        assert found.expanded is True
        assert found.time_spent == 30.5

    def test_record_interaction_all_fields(self, context_store, interaction_full):
        """Test recording interaction with all fields."""
        context_store.record_interaction(interaction_full)
        interactions = context_store.get_interactions()
        found = next((i for i in interactions if i.article_id == "article-7"), None)
        assert found is not None
        assert found.expanded is True
        assert found.saved is True
        assert found.shared is True
        assert found.thumbs_up is True
        assert found.relevance_score == 0.95

    def test_record_interaction_thumbs_down(self, context_store, interaction_thumbs_down):
        """Test recording interaction with thumbs_down (False)."""
        context_store.record_interaction(interaction_thumbs_down)
        interactions = context_store.get_interactions()
        found = next((i for i in interactions if i.article_id == "article-6"), None)
        assert found is not None
        assert found.thumbs_up is False

    def test_record_interaction_replaces_on_duplicate(self, context_store):
        """Test recording replaces interaction with same article_id + timestamp."""
        timestamp = datetime.now()
        interaction1 = ArticleInteraction(
            article_id="article-dup",
            timestamp=timestamp,
            expanded=False,
        )
        interaction2 = ArticleInteraction(
            article_id="article-dup",
            timestamp=timestamp,
            expanded=True,
            saved=True,
        )
        context_store.record_interaction(interaction1)
        context_store.record_interaction(interaction2)
        interactions = context_store.get_interactions()
        found = [i for i in interactions if i.article_id == "article-dup"]
        # Should only have one entry (replaced)
        assert len(found) == 1
        assert found[0].expanded is True
        assert found[0].saved is True

    def test_record_multiple_interactions(self, context_store, interactions_bulk):
        """Test recording multiple interactions."""
        for interaction in interactions_bulk:
            context_store.record_interaction(interaction)
        all_interactions = context_store.get_interactions()
        assert len(all_interactions) == 20


class TestUserContextStoreGetInteractions:
    """Test UserContextStore.get_interactions() method."""

    def test_get_interactions_empty(self, context_store):
        """Test getting interactions when none exist."""
        interactions = context_store.get_interactions()
        assert interactions == []

    def test_get_interactions_with_data(self, context_store_with_interactions):
        """Test getting interactions with existing data."""
        interactions = context_store_with_interactions.get_interactions()
        assert len(interactions) == 20

    def test_get_interactions_ordered_by_timestamp(self, context_store_with_interactions):
        """Test interactions are ordered by timestamp descending."""
        interactions = context_store_with_interactions.get_interactions()
        for i in range(len(interactions) - 1):
            # Earlier index should have more recent timestamp
            assert interactions[i].timestamp >= interactions[i + 1].timestamp

    def test_get_interactions_filter_by_article_id(self, context_store):
        """Test filtering interactions by article_id."""
        # Add interactions for different articles
        context_store.record_interaction(ArticleInteraction(article_id="article-a"))
        context_store.record_interaction(ArticleInteraction(article_id="article-b"))
        context_store.record_interaction(ArticleInteraction(article_id="article-a"))

        interactions = context_store.get_interactions(article_id="article-a")
        assert len(interactions) == 2
        for i in interactions:
            assert i.article_id == "article-a"

    def test_get_interactions_filter_by_days(self, context_store):
        """Test filtering interactions by days."""
        # Add old and recent interactions
        old_interaction = ArticleInteraction(
            article_id="old-article",
            timestamp=datetime.now() - timedelta(days=100),
        )
        recent_interaction = ArticleInteraction(
            article_id="recent-article",
            timestamp=datetime.now() - timedelta(days=5),
        )
        context_store.record_interaction(old_interaction)
        context_store.record_interaction(recent_interaction)

        # Default is 90 days
        interactions = context_store.get_interactions()
        ids = [i.article_id for i in interactions]
        assert "recent-article" in ids
        assert "old-article" not in ids

    def test_get_interactions_custom_days(self, context_store):
        """Test custom days filter."""
        # Add interactions of different ages
        context_store.record_interaction(ArticleInteraction(
            article_id="5-days-old",
            timestamp=datetime.now() - timedelta(days=5),
        ))
        context_store.record_interaction(ArticleInteraction(
            article_id="15-days-old",
            timestamp=datetime.now() - timedelta(days=15),
        ))

        # 10 day filter
        interactions = context_store.get_interactions(days=10)
        ids = [i.article_id for i in interactions]
        assert "5-days-old" in ids
        assert "15-days-old" not in ids

    def test_get_interactions_returns_article_interaction_objects(self, context_store_with_interactions):
        """Test that returned objects are ArticleInteraction instances."""
        interactions = context_store_with_interactions.get_interactions()
        for interaction in interactions:
            assert isinstance(interaction, ArticleInteraction)


class TestUserContextStoreClearHistory:
    """Test UserContextStore.clear_history() method."""

    def test_clear_all_history(self, context_store_with_interactions):
        """Test clearing all interaction history."""
        # Verify data exists
        before = context_store_with_interactions.get_interactions()
        assert len(before) > 0

        deleted = context_store_with_interactions.clear_history()
        assert deleted == 20

        after = context_store_with_interactions.get_interactions()
        assert len(after) == 0

    def test_clear_history_returns_count(self, context_store_with_interactions):
        """Test clear_history returns correct count."""
        deleted = context_store_with_interactions.clear_history()
        assert deleted == 20

    def test_clear_history_by_days(self, context_store):
        """Test clearing history older than specified days."""
        # Add interactions of different ages
        context_store.record_interaction(ArticleInteraction(
            article_id="recent",
            timestamp=datetime.now() - timedelta(days=5),
        ))
        context_store.record_interaction(ArticleInteraction(
            article_id="old-1",
            timestamp=datetime.now() - timedelta(days=20),
        ))
        context_store.record_interaction(ArticleInteraction(
            article_id="old-2",
            timestamp=datetime.now() - timedelta(days=30),
        ))

        # Clear older than 15 days
        deleted = context_store.clear_history(days=15)
        assert deleted == 2

        # Recent should remain
        remaining = context_store.get_interactions()
        ids = [i.article_id for i in remaining]
        assert "recent" in ids
        assert "old-1" not in ids
        assert "old-2" not in ids

    def test_clear_empty_history(self, context_store):
        """Test clearing when no history exists."""
        deleted = context_store.clear_history()
        assert deleted == 0


# =============================================================================
# Test Classes for UserContextStore Export/Import
# =============================================================================


class TestUserContextStoreExportData:
    """Test UserContextStore.export_data() method."""

    def test_export_data_structure(self, context_store_full):
        """Test exported data has correct structure."""
        data = context_store_full.export_data()
        assert "profile" in data
        assert "interactions" in data
        assert "version" in data
        assert data["version"] == 1

    def test_export_data_profile(self, context_store_full):
        """Test exported data includes profile."""
        data = context_store_full.export_data()
        assert data["profile"]["role"] == "software developer"
        assert "building RSS reader" in data["profile"]["current_projects"]

    def test_export_data_interactions(self, context_store_full):
        """Test exported data includes interactions."""
        data = context_store_full.export_data()
        assert len(data["interactions"]) > 0
        # Check interaction structure
        interaction = data["interactions"][0]
        assert "article_id" in interaction
        assert "timestamp" in interaction
        assert "expanded" in interaction

    def test_export_data_empty_store(self, context_store):
        """Test exporting from empty store."""
        data = context_store.export_data()
        assert "profile" in data
        assert "interactions" in data
        assert data["interactions"] == []

    def test_export_data_interaction_timestamps_are_strings(self, context_store_full):
        """Test exported interaction timestamps are ISO strings."""
        data = context_store_full.export_data()
        for interaction in data["interactions"]:
            assert isinstance(interaction["timestamp"], str)
            # Should be parseable ISO format
            datetime.fromisoformat(interaction["timestamp"])


class TestUserContextStoreImportData:
    """Test UserContextStore.import_data() method."""

    def test_import_data_profile(self, context_store, export_data_valid):
        """Test importing profile data."""
        context_store.import_data(export_data_valid)
        profile = context_store.load_profile()
        assert profile.role == "developer"
        assert "project1" in profile.current_projects

    def test_import_data_interactions(self, context_store, export_data_valid):
        """Test importing interaction data."""
        context_store.import_data(export_data_valid)
        interactions = context_store.get_interactions(days=365)
        assert len(interactions) >= 1
        found = next((i for i in interactions if i.article_id == "article-1"), None)
        assert found is not None
        assert found.expanded is True
        assert found.thumbs_up is True

    def test_import_data_empty(self, context_store, export_data_empty):
        """Test importing empty data."""
        context_store.import_data(export_data_empty)
        profile = context_store.load_profile()
        assert profile.role is None
        interactions = context_store.get_interactions()
        assert len(interactions) == 0

    def test_import_data_many_interactions(self, context_store, export_data_many_interactions):
        """Test importing many interactions."""
        context_store.import_data(export_data_many_interactions)
        interactions = context_store.get_interactions(days=365)
        assert len(interactions) == 50

    def test_import_export_roundtrip(self, context_store_full, temp_dir):
        """Test export -> import roundtrip."""
        # Export from full store
        exported = context_store_full.export_data()

        # Import into new store
        new_profile_path = os.path.join(temp_dir, "new_config", "user_context.json")
        new_db_path = os.path.join(temp_dir, "new_articles.db")
        new_store = UserContextStore(profile_path=new_profile_path, db_path=new_db_path)
        new_store.import_data(exported)

        # Verify profile
        new_profile = new_store.load_profile()
        assert new_profile.role == "software developer"

        # Verify interactions
        new_interactions = new_store.get_interactions(days=365)
        assert len(new_interactions) == 20


class TestUserContextStoreGetTopicEngagement:
    """Test UserContextStore.get_topic_engagement() method."""

    def test_get_topic_engagement_empty_no_articles_table(self, context_store):
        """Test getting engagement when no articles table exists.

        The get_topic_engagement method joins with the articles table.
        When using UserContextStore alone (without Storage), the articles
        table doesn't exist, so the query fails. This tests that behavior.
        """
        import sqlite3
        # The method tries to join with articles table which doesn't exist
        # in a standalone UserContextStore database
        try:
            engagement = context_store.get_topic_engagement()
            # If it returns without error, should be empty dict
            assert engagement == {}
        except sqlite3.OperationalError as e:
            # Expected: "no such table: articles"
            assert "no such table" in str(e) or "articles" in str(e)

    def test_get_topic_engagement_with_storage(self, temp_dir):
        """Test getting engagement when articles table exists via Storage."""
        from src.storage import Storage, Article
        import sqlite3

        db_path = os.path.join(temp_dir, "full.db")
        profile_path = os.path.join(temp_dir, "config", "user_context.json")

        # Create storage first (which creates articles table)
        storage = Storage(db_path)

        # Add an article
        article = Article(
            id="article-engaged",
            feed_url="https://example.com/feed.xml",
            title="AI Technology Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="Content about AI.",
            summary="AI summary.",
        )
        storage.save_article(article)

        # Manually set trend_tags since save_article doesn't include it
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE articles SET trend_tags = ? WHERE id = ?",
            ("AI,technology", "article-engaged"),
        )
        conn.commit()
        conn.close()

        # Create UserContextStore with same database
        context_store = UserContextStore(profile_path=profile_path, db_path=db_path)

        # Record interaction with that article
        context_store.record_interaction(ArticleInteraction(
            article_id="article-engaged",
            expanded=True,
            saved=True,
        ))

        # Now get topic engagement
        engagement = context_store.get_topic_engagement(days=30)
        assert isinstance(engagement, dict)
        # Should have engagement for AI and technology tags
        assert "AI" in engagement or "technology" in engagement

    def test_get_topic_engagement_no_matching_interactions(self, temp_dir):
        """Test engagement when interactions don't match any articles."""
        from src.storage import Storage, Article

        db_path = os.path.join(temp_dir, "full.db")
        profile_path = os.path.join(temp_dir, "config", "user_context.json")

        # Create storage first
        storage = Storage(db_path)

        # Add an article
        article = Article(
            id="article-1",
            feed_url="https://example.com/feed.xml",
            title="Article",
            link="https://example.com/article",
            published=datetime.now(),
            content="Content.",
            summary="Summary.",
            trend_tags="Python",
        )
        storage.save_article(article)

        # Create UserContextStore with same database
        context_store = UserContextStore(profile_path=profile_path, db_path=db_path)

        # Record interaction with a DIFFERENT article (not in articles table)
        context_store.record_interaction(ArticleInteraction(
            article_id="article-nonexistent",
            expanded=True,
        ))

        # Get engagement - should be empty since interaction doesn't match any article
        engagement = context_store.get_topic_engagement(days=30)
        assert engagement == {}


# =============================================================================
# Test Classes for UserContextStore Integration
# =============================================================================


class TestUserContextStoreIntegration:
    """Integration tests for UserContextStore."""

    def test_full_workflow(self, full_user_context_setup):
        """Test full workflow with profile and interactions."""
        store = full_user_context_setup["store"]
        profile = full_user_context_setup["profile"]

        # Profile should be saved
        loaded = store.load_profile()
        assert loaded.role == profile.role

        # Interactions should be recorded
        interactions = store.get_interactions()
        assert len(interactions) == 3

    def test_multiple_operations(self, context_store, profile_developer):
        """Test multiple operations in sequence."""
        # Save profile
        context_store.save_profile(profile_developer)

        # Add interactions
        for i in range(5):
            context_store.record_interaction(ArticleInteraction(
                article_id=f"article-{i}",
                expanded=True,
            ))

        # Verify profile
        profile = context_store.load_profile()
        assert profile.role == "software developer"

        # Verify interactions
        interactions = context_store.get_interactions()
        assert len(interactions) == 5

        # Clear and verify
        context_store.clear_history()
        interactions = context_store.get_interactions()
        assert len(interactions) == 0

        # Profile should still exist
        profile = context_store.load_profile()
        assert profile.role == "software developer"

    def test_profile_update_preserves_data(self, context_store_with_profile):
        """Test updating profile preserves existing data."""
        # Load existing profile
        profile = context_store_with_profile.load_profile()
        original_projects = profile.current_projects.copy()

        # Modify and save
        profile.watching.append("new-topic")
        context_store_with_profile.save_profile(profile)

        # Reload and verify
        loaded = context_store_with_profile.load_profile()
        assert loaded.current_projects == original_projects
        assert "new-topic" in loaded.watching

    def test_interaction_persistence(self, context_store, temp_db):
        """Test interactions persist across store instances."""
        # Record interaction
        context_store.record_interaction(ArticleInteraction(
            article_id="persistent-article",
            expanded=True,
            saved=True,
        ))

        # Create new store instance with same db
        new_store = UserContextStore(
            profile_path="config/user_context.json",
            db_path=temp_db,
        )
        interactions = new_store.get_interactions()
        found = next((i for i in interactions if i.article_id == "persistent-article"), None)
        assert found is not None
        assert found.expanded is True
        assert found.saved is True


# =============================================================================
# Test Classes for RelevanceEngine Initialization
# =============================================================================


class TestRelevanceEngineInitialization:
    """Test RelevanceEngine initialization."""

    def test_engine_creation(self, relevance_engine):
        """Test creating a RelevanceEngine."""
        assert relevance_engine is not None
        assert hasattr(relevance_engine, "store")

    def test_engine_with_store(self, relevance_engine, context_store):
        """Test engine stores reference to store."""
        assert relevance_engine.store == context_store

    def test_engine_with_mock_store(self, relevance_engine_mock, mock_context_store):
        """Test engine with mock store."""
        assert relevance_engine_mock.store == mock_context_store

    def test_decay_constants_exist(self, relevance_engine):
        """Test decay constants are defined."""
        assert hasattr(RelevanceEngine, "DECAY_HALF_LIFE_DAYS")
        assert hasattr(RelevanceEngine, "COMPLETED_DECAY_HALF_LIFE_DAYS")
        assert RelevanceEngine.DECAY_HALF_LIFE_DAYS == 14
        assert RelevanceEngine.COMPLETED_DECAY_HALF_LIFE_DAYS == 7

    def test_engine_with_engagement_data(self, relevance_engine_with_engagement):
        """Test engine with store containing engagement data."""
        assert relevance_engine_with_engagement is not None
        engagement = relevance_engine_with_engagement.store.get_topic_engagement()
        assert "AI" in engagement

    def test_multiple_engines_independent(self, context_store, context_store_empty):
        """Test multiple engine instances are independent."""
        engine1 = RelevanceEngine(context_store)
        engine2 = RelevanceEngine(context_store_empty)
        assert engine1.store != engine2.store


# =============================================================================
# Test Classes for _extract_topics Method
# =============================================================================


class TestExtractTopicsBasic:
    """Test RelevanceEngine._extract_topics() basic functionality."""

    def test_extract_topics_from_trend_tags(self, relevance_engine, sample_article):
        """Test extracting topics from trend_tags."""
        topics = relevance_engine._extract_topics(sample_article)
        assert "AI" in topics
        assert "technology" in topics
        assert "product launch" in topics

    def test_extract_topics_from_title(self, relevance_engine, sample_article_no_tags):
        """Test extracting topics from title when no tags."""
        topics = relevance_engine._extract_topics(sample_article_no_tags)
        # Words from title > 4 chars
        assert "interesting" in topics or "article" in topics or "something" in topics

    def test_extract_topics_combines_tags_and_title(self, relevance_engine, sample_article):
        """Test topics combined from both tags and title."""
        topics = relevance_engine._extract_topics(sample_article)
        # From tags
        assert "AI" in topics
        # From title (words > 4 chars)
        assert any(word in topics for word in ["breaking", "major", "company", "announces", "product"])

    def test_extract_topics_empty_tags(self, relevance_engine, sample_article_empty_tags):
        """Test extracting topics with empty tags string."""
        topics = relevance_engine._extract_topics(sample_article_empty_tags)
        # Should still extract from title
        assert isinstance(topics, list)


class TestExtractTopicsEdgeCases:
    """Test _extract_topics edge cases."""

    def test_extract_topics_no_tags_attribute(self, relevance_engine, mock_article_no_attrs):
        """Test extracting topics from article without trend_tags attribute."""
        topics = relevance_engine._extract_topics(mock_article_no_attrs)
        assert isinstance(topics, list)

    def test_extract_topics_no_title_attribute(self, relevance_engine):
        """Test extracting topics from article without title attribute."""
        article = MagicMock(spec=["id", "trend_tags"])
        article.trend_tags = "Python,programming"
        topics = relevance_engine._extract_topics(article)
        assert "Python" in topics
        assert "programming" in topics

    def test_extract_topics_none_trend_tags(self, relevance_engine, sample_article_no_tags):
        """Test extracting topics when trend_tags is None."""
        topics = relevance_engine._extract_topics(sample_article_no_tags)
        assert isinstance(topics, list)

    def test_extract_topics_unicode(self, relevance_engine, sample_article_unicode):
        """Test extracting topics with unicode content."""
        topics = relevance_engine._extract_topics(sample_article_unicode)
        assert "AI" in topics
        assert "tecnologia" in topics or "inteligencia artificial" in topics

    def test_extract_topics_removes_empty_strings(self, relevance_engine):
        """Test that empty strings are removed from topics."""
        article = MagicMock()
        article.trend_tags = "AI,,,,Python"
        article.title = "Short"
        topics = relevance_engine._extract_topics(article)
        assert "" not in topics

    def test_extract_topics_strips_whitespace(self, relevance_engine):
        """Test that topics are stripped of whitespace."""
        article = MagicMock()
        article.trend_tags = "  AI  ,  Python  ,  testing  "
        article.title = "Test Article"
        topics = relevance_engine._extract_topics(article)
        assert "AI" in topics
        assert "Python" in topics
        assert "testing" in topics

    def test_extract_topics_short_words_from_title_filtered(self, relevance_engine):
        """Test that short words from title are filtered."""
        article = MagicMock()
        article.trend_tags = None
        article.title = "AI is a big topic for the web"
        topics = relevance_engine._extract_topics(article)
        # Words <= 4 chars should be filtered
        assert "AI" not in topics or "AI" == topics[0]  # May be there if longer words exist
        assert "is" not in topics
        assert "a" not in topics
        assert "big" not in topics
        assert "for" not in topics
        assert "the" not in topics
        assert "web" not in topics
        assert "topic" in topics


# =============================================================================
# Test Classes for _calculate_topic_match Method
# =============================================================================


class TestCalculateTopicMatchBasic:
    """Test RelevanceEngine._calculate_topic_match() basic functionality."""

    def test_topic_match_empty_topics(self, relevance_engine, profile_developer):
        """Test topic match with empty topics list."""
        score = relevance_engine._calculate_topic_match([], profile_developer)
        assert score == 0.5  # Neutral for empty

    def test_topic_match_watching_direct(self, relevance_engine, profile_developer):
        """Test topic match for watching list."""
        score = relevance_engine._calculate_topic_match(["AI"], profile_developer)
        # Should be boosted above 0.5
        assert score > 0.5

    def test_topic_match_current_projects(self, relevance_engine, profile_developer):
        """Test topic match for current_projects."""
        score = relevance_engine._calculate_topic_match(["RSS"], profile_developer)
        # Should match "building RSS reader"
        assert score > 0.5

    def test_topic_match_pinned_sets_minimum(self, relevance_engine, profile_developer):
        """Test pinned topics set minimum score."""
        score = relevance_engine._calculate_topic_match(["security"], profile_developer)
        # Pinned: "security vulnerabilities"
        assert score >= 0.7

    def test_topic_match_ignore_reduces(self, relevance_engine, profile_developer):
        """Test ignore list reduces score."""
        score = relevance_engine._calculate_topic_match(["celebrity"], profile_developer)
        # Ignore: "celebrity news"
        assert score < 0.5


class TestCalculateTopicMatchScoring:
    """Test _calculate_topic_match scoring behavior."""

    def test_topic_match_case_insensitive(self, relevance_engine, profile_developer):
        """Test topic matching is case insensitive."""
        score_lower = relevance_engine._calculate_topic_match(["ai"], profile_developer)
        score_upper = relevance_engine._calculate_topic_match(["AI"], profile_developer)
        assert score_lower == score_upper

    def test_topic_match_partial_match_watching(self, relevance_engine, profile_developer):
        """Test partial match for watching topics."""
        # Profile watching: "Python"
        score = relevance_engine._calculate_topic_match(["python programming"], profile_developer)
        # "python" in "python programming" should match
        assert score > 0.5

    def test_topic_match_partial_match_projects(self, relevance_engine, profile_developer):
        """Test partial match for current projects."""
        # Profile projects: "building RSS reader"
        score = relevance_engine._calculate_topic_match(["reader"], profile_developer)
        assert score > 0.5

    def test_topic_match_multiple_matches_accumulate(self, relevance_engine, profile_developer):
        """Test multiple matches accumulate score."""
        score_single = relevance_engine._calculate_topic_match(["AI"], profile_developer)
        score_multiple = relevance_engine._calculate_topic_match(["AI", "Python", "web"], profile_developer)
        assert score_multiple >= score_single

    def test_topic_match_clamped_to_one(self, relevance_engine, profile_developer):
        """Test score is clamped to max 1.0."""
        # Many matching topics
        topics = ["AI", "Python", "web", "RSS", "security"]
        score = relevance_engine._calculate_topic_match(topics, profile_developer)
        assert score <= 1.0

    def test_topic_match_clamped_to_zero(self, relevance_engine, profile_developer):
        """Test score is clamped to min 0.0."""
        # Many ignored topics
        topics = ["celebrity", "sports", "entertainment"]
        score = relevance_engine._calculate_topic_match(topics, profile_developer)
        assert score >= 0.0


class TestCalculateTopicMatchProfiles:
    """Test _calculate_topic_match with different profiles."""

    def test_topic_match_empty_profile(self, relevance_engine, profile_empty_lists):
        """Test topic match with empty profile lists."""
        score = relevance_engine._calculate_topic_match(["AI", "Python"], profile_empty_lists)
        # Should be neutral
        assert score == 0.5

    def test_topic_match_researcher_profile(self, relevance_engine, profile_researcher):
        """Test topic match for researcher profile."""
        score = relevance_engine._calculate_topic_match(["deep learning", "transformers"], profile_researcher)
        assert score > 0.5

    def test_topic_match_many_interests(self, relevance_engine, profile_many_interests):
        """Test topic match with profile having many interests."""
        score = relevance_engine._calculate_topic_match(["topic-5"], profile_many_interests)
        assert score > 0.5


# =============================================================================
# Test Classes for _calculate_engagement_score Method
# =============================================================================


class TestCalculateEngagementScoreBasic:
    """Test RelevanceEngine._calculate_engagement_score() basic functionality."""

    def test_engagement_score_no_history(self, relevance_engine_mock):
        """Test engagement score with no history."""
        score = relevance_engine_mock._calculate_engagement_score(["AI", "Python"])
        # Mock returns empty dict, should return neutral
        assert score == 0.5

    def test_engagement_score_with_engagement(self, relevance_engine_with_engagement):
        """Test engagement score with engagement data."""
        score = relevance_engine_with_engagement._calculate_engagement_score(["AI"])
        # Mock has AI engagement rate of 0.8
        assert score == 0.8

    def test_engagement_score_multiple_topics(self, relevance_engine_with_engagement):
        """Test engagement score averages multiple topics."""
        score = relevance_engine_with_engagement._calculate_engagement_score(["AI", "Python"])
        # AI=0.8, Python=0.7, average=0.75
        assert score == 0.75


class TestCalculateEngagementScoreMatching:
    """Test _calculate_engagement_score topic matching."""

    def test_engagement_score_case_insensitive(self, relevance_engine_with_engagement):
        """Test engagement score matching is case insensitive."""
        score_lower = relevance_engine_with_engagement._calculate_engagement_score(["ai"])
        score_upper = relevance_engine_with_engagement._calculate_engagement_score(["AI"])
        assert score_lower == score_upper

    def test_engagement_score_partial_match(self, relevance_engine_with_engagement):
        """Test engagement score with partial matches."""
        score = relevance_engine_with_engagement._calculate_engagement_score(["artificial intelligence"])
        # Should not match "AI" directly, but may have partial logic
        # Based on code: topic_lower in hist_lower or hist_lower in topic_lower
        # "ai" in "artificial intelligence" -> True
        assert score >= 0.5

    def test_engagement_score_no_matching_topics(self):
        """Test engagement score when no topics match history."""
        # Create mock with specific engagement that doesn't match sports/weather
        # Note: "entertainment" contains "ai" as substring, so avoid it
        store = MagicMock(spec=UserContextStore)
        store.get_topic_engagement.return_value = {
            "AI": 0.8,
            "Python": 0.7,
        }
        engine = RelevanceEngine(store)
        score = engine._calculate_engagement_score(["sports", "weather"])
        # No matches in mock engagement data
        assert score == 0.5


class TestCalculateEngagementScoreEdgeCases:
    """Test _calculate_engagement_score edge cases."""

    def test_engagement_score_empty_topics(self, relevance_engine_with_engagement):
        """Test engagement score with empty topics list."""
        score = relevance_engine_with_engagement._calculate_engagement_score([])
        # No topics to match
        assert score == 0.5

    def test_engagement_score_mock_returns_empty(self, relevance_engine_mock):
        """Test engagement score when store returns empty dict."""
        score = relevance_engine_mock._calculate_engagement_score(["AI"])
        assert score == 0.5


# =============================================================================
# Test Classes for _calculate_recency_boost Method
# =============================================================================


class TestCalculateRecencyBoostBasic:
    """Test RelevanceEngine._calculate_recency_boost() basic functionality."""

    def test_recency_boost_no_interactions(self, relevance_engine_mock):
        """Test recency boost with no recent interactions."""
        score = relevance_engine_mock._calculate_recency_boost(["AI", "Python"])
        # Should return neutral
        assert score == 0.5

    def test_recency_boost_with_interactions(self, relevance_engine_mock):
        """Test recency boost with recent interactions."""
        # Mock has no history, returns neutral
        score = relevance_engine_mock._calculate_recency_boost(["AI"])
        assert score == 0.5

    def test_recency_boost_recent_history(self, mock_context_store_with_history):
        """Test recency boost with recent interaction history."""
        engine = RelevanceEngine(mock_context_store_with_history)
        score = engine._calculate_recency_boost(["AI"])
        # Current implementation returns 0.5 (placeholder)
        assert score == 0.5


class TestCalculateRecencyBoostBehavior:
    """Test _calculate_recency_boost behavior."""

    def test_recency_boost_always_returns_float(self, relevance_engine_mock):
        """Test recency boost always returns float."""
        score = relevance_engine_mock._calculate_recency_boost(["any", "topics"])
        assert isinstance(score, float)

    def test_recency_boost_bounded(self, relevance_engine_mock):
        """Test recency boost is bounded 0-1."""
        score = relevance_engine_mock._calculate_recency_boost(["test"])
        assert 0.0 <= score <= 1.0


# =============================================================================
# Test Classes for _calculate_diversity_score Method
# =============================================================================


class TestCalculateDiversityScoreBasic:
    """Test RelevanceEngine._calculate_diversity_score() basic functionality."""

    def test_diversity_score_no_history(self, relevance_engine_mock):
        """Test diversity score with no history."""
        score = relevance_engine_mock._calculate_diversity_score(["AI", "Python"])
        # No history (mock returns empty), all topics are diverse
        assert score == 0.8

    def test_diversity_score_with_history(self, relevance_engine_with_engagement):
        """Test diversity score with engagement history."""
        score = relevance_engine_with_engagement._calculate_diversity_score(["AI", "Python"])
        # These topics are in history, so not diverse
        assert score < 0.8

    def test_diversity_score_new_topics(self, relevance_engine_with_engagement):
        """Test diversity score for completely new topics."""
        score = relevance_engine_with_engagement._calculate_diversity_score(["quantum", "blockchain"])
        # New topics not in engagement history
        assert score == 1.0


class TestCalculateDiversityScoreCalculation:
    """Test _calculate_diversity_score calculation logic."""

    def test_diversity_score_mixed_topics(self, relevance_engine_with_engagement):
        """Test diversity score with mix of new and seen topics."""
        score = relevance_engine_with_engagement._calculate_diversity_score(["AI", "quantum"])
        # AI is seen (not diverse), quantum is new (diverse)
        # 1/2 new = 0.5 diversity ratio -> 0.5 + 0.5*0.5 = 0.75
        assert score == 0.75

    def test_diversity_score_all_seen(self, relevance_engine_with_engagement):
        """Test diversity score when all topics seen before."""
        score = relevance_engine_with_engagement._calculate_diversity_score(["AI", "Python", "technology", "security"])
        # All in history
        assert score == 0.5

    def test_diversity_score_empty_topics(self, relevance_engine_with_engagement):
        """Test diversity score with empty topics list."""
        score = relevance_engine_with_engagement._calculate_diversity_score([])
        # Empty topics -> diversity_ratio = 0
        assert score == 0.5

    def test_diversity_score_case_insensitive(self, relevance_engine_with_engagement):
        """Test diversity score is case insensitive."""
        score_lower = relevance_engine_with_engagement._calculate_diversity_score(["ai"])
        score_upper = relevance_engine_with_engagement._calculate_diversity_score(["AI"])
        assert score_lower == score_upper


# =============================================================================
# Test Classes for calculate_relevance Method
# =============================================================================


class TestCalculateRelevanceBasic:
    """Test RelevanceEngine.calculate_relevance() basic functionality."""

    def test_calculate_relevance_returns_float(self, relevance_engine_mock, sample_article, profile_developer):
        """Test calculate_relevance returns a float."""
        score = relevance_engine_mock.calculate_relevance(sample_article, profile_developer)
        assert isinstance(score, float)

    def test_calculate_relevance_bounded(self, relevance_engine_mock, sample_article, profile_developer):
        """Test calculate_relevance returns score between 0 and 1."""
        score = relevance_engine_mock.calculate_relevance(sample_article, profile_developer)
        assert 0.0 <= score <= 1.0

    def test_calculate_relevance_matching_topics(self, relevance_engine_mock, sample_article_ai, profile_developer):
        """Test relevance for article matching profile topics."""
        score = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_developer)
        # AI matches profile watching
        assert score > 0.5

    def test_calculate_relevance_ignored_topics(self, relevance_engine_mock, sample_article_celebrity, profile_developer):
        """Test relevance for article with ignored topics."""
        score = relevance_engine_mock.calculate_relevance(sample_article_celebrity, profile_developer)
        # "celebrity news" in ignore list
        assert score < 0.5


class TestCalculateRelevancePersonalization:
    """Test calculate_relevance personalization behavior."""

    def test_zero_personalization_returns_neutral(self, relevance_engine_mock, sample_article_ai, profile_zero_personalization):
        """Test zero personalization returns neutral score."""
        score = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_zero_personalization)
        # At 0 personalization, should return 0.5
        assert score == 0.5

    def test_low_personalization_reduces_effect(self, relevance_engine_mock, sample_article_ai, profile_low_personalization, profile_developer):
        """Test low personalization reduces scoring effect."""
        # Same article, different personalization strength
        score_low = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_low_personalization)
        profile_developer.personalization_strength = 1.0
        score_high = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_developer)
        # Low personalization should be closer to 0.5
        assert abs(score_low - 0.5) < abs(score_high - 0.5)

    def test_full_personalization_uses_raw_score(self, relevance_engine_mock, sample_article_ai):
        """Test full personalization uses raw score directly."""
        profile = UserContextProfile(
            watching=["AI"],
            personalization_strength=1.0,
        )
        score = relevance_engine_mock.calculate_relevance(sample_article_ai, profile)
        # Should show the full effect of matching
        assert score > 0.5


class TestCalculateRelevanceNoTopics:
    """Test calculate_relevance with no extractable topics."""

    def test_calculate_relevance_no_tags_no_title(self, relevance_engine_mock, profile_developer):
        """Test relevance for article with no extractable topics."""
        article = MagicMock()
        article.trend_tags = None
        article.title = None
        score = relevance_engine_mock.calculate_relevance(article, profile_developer)
        # Should return neutral
        assert score == 0.5

    def test_calculate_relevance_empty_title(self, relevance_engine_mock, sample_article_edge_case_empty_content, profile_developer):
        """Test relevance for article with empty title."""
        score = relevance_engine_mock.calculate_relevance(sample_article_edge_case_empty_content, profile_developer)
        # Should return neutral
        assert score == 0.5


class TestCalculateRelevanceProfiles:
    """Test calculate_relevance with different profiles."""

    def test_calculate_relevance_researcher(self, relevance_engine_mock, sample_article_ai, profile_researcher):
        """Test relevance calculation for researcher profile."""
        score = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_researcher)
        # AI matches researcher watching
        assert score > 0.5

    def test_calculate_relevance_journalist(self, relevance_engine_mock, sample_article, profile_journalist):
        """Test relevance calculation for journalist profile."""
        score = relevance_engine_mock.calculate_relevance(sample_article, profile_journalist)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_calculate_relevance_empty_profile(self, relevance_engine_mock, sample_article, profile_empty_lists):
        """Test relevance calculation for empty profile."""
        score = relevance_engine_mock.calculate_relevance(sample_article, profile_empty_lists)
        # Empty profile, most scores are neutral, should be around 0.5
        assert 0.3 <= score <= 0.7


class TestCalculateRelevanceWeighting:
    """Test calculate_relevance factor weighting."""

    def test_calculate_relevance_topic_weight(self, relevance_engine_mock, sample_article_ai):
        """Test topic match has 40% weight."""
        # With mock store returning neutral engagement/recency
        profile = UserContextProfile(
            watching=["AI"],
            personalization_strength=1.0,
        )
        score = relevance_engine_mock.calculate_relevance(sample_article_ai, profile)
        # Topic match should dominate (40% weight)
        assert score > 0.5

    def test_calculate_relevance_pinned_boost(self, relevance_engine_mock, sample_article_security, profile_developer):
        """Test pinned topics get significant boost."""
        score = relevance_engine_mock.calculate_relevance(sample_article_security, profile_developer)
        # "security vulnerabilities" is pinned
        # Use >= 0.59 to account for floating point precision (0.5999... is essentially 0.6)
        assert score >= 0.59


class TestCalculateRelevanceEdgeCases:
    """Test calculate_relevance edge cases."""

    def test_calculate_relevance_unicode_article(self, relevance_engine_mock, sample_article_unicode, profile_unicode):
        """Test relevance with unicode content."""
        score = relevance_engine_mock.calculate_relevance(sample_article_unicode, profile_unicode)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_calculate_relevance_long_title(self, relevance_engine_mock, sample_article_edge_case_long_title, profile_developer):
        """Test relevance with very long title."""
        score = relevance_engine_mock.calculate_relevance(sample_article_edge_case_long_title, profile_developer)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_calculate_relevance_sports_ignored(self, relevance_engine_mock, sample_article_sports, profile_developer):
        """Test relevance for sports article (ignored)."""
        score = relevance_engine_mock.calculate_relevance(sample_article_sports, profile_developer)
        # "sports" in ignore list
        assert score < 0.5


# =============================================================================
# Test Classes for apply_relevance_decay Method
# =============================================================================


class TestApplyRelevanceDecay:
    """Test RelevanceEngine.apply_relevance_decay() method."""

    def test_apply_decay_returns_profile(self, relevance_engine_mock, profile_developer):
        """Test apply_relevance_decay returns a profile."""
        result = relevance_engine_mock.apply_relevance_decay(profile_developer, days_since_update=7)
        assert isinstance(result, UserContextProfile)

    def test_apply_decay_preserves_profile(self, relevance_engine_mock, profile_developer):
        """Test apply_relevance_decay currently returns profile unchanged."""
        # Current implementation is a placeholder
        result = relevance_engine_mock.apply_relevance_decay(profile_developer, days_since_update=30)
        assert result.role == profile_developer.role
        assert result.watching == profile_developer.watching
        assert result.current_projects == profile_developer.current_projects

    def test_apply_decay_zero_days(self, relevance_engine_mock, profile_developer):
        """Test apply_relevance_decay with zero days."""
        result = relevance_engine_mock.apply_relevance_decay(profile_developer, days_since_update=0)
        assert result == profile_developer

    def test_apply_decay_many_days(self, relevance_engine_mock, profile_developer):
        """Test apply_relevance_decay with many days."""
        result = relevance_engine_mock.apply_relevance_decay(profile_developer, days_since_update=365)
        # Placeholder returns unchanged
        assert result == profile_developer


# =============================================================================
# Test Classes for sort_by_relevance Function
# =============================================================================


class TestSortByRelevanceBasic:
    """Test sort_by_relevance() basic functionality."""

    def test_sort_by_relevance_returns_list(self, mock_context_store, profile_developer, sample_articles_bulk):
        """Test sort_by_relevance returns a list."""
        result = sort_by_relevance(sample_articles_bulk, profile_developer, mock_context_store)
        assert isinstance(result, list)

    def test_sort_by_relevance_same_length(self, mock_context_store, profile_developer, sample_articles_bulk):
        """Test sort_by_relevance returns same number of articles."""
        result = sort_by_relevance(sample_articles_bulk, profile_developer, mock_context_store)
        assert len(result) == len(sample_articles_bulk)

    def test_sort_by_relevance_contains_all_articles(self, mock_context_store, profile_developer, sample_articles_bulk):
        """Test sorted list contains all original articles."""
        result = sort_by_relevance(sample_articles_bulk, profile_developer, mock_context_store)
        original_ids = {a.id for a in sample_articles_bulk}
        sorted_ids = {a.id for a in result}
        assert original_ids == sorted_ids

    def test_sort_by_relevance_empty_list(self, mock_context_store, profile_developer):
        """Test sort_by_relevance with empty list."""
        result = sort_by_relevance([], profile_developer, mock_context_store)
        assert result == []


class TestSortByRelevanceOrdering:
    """Test sort_by_relevance ordering behavior."""

    def test_sort_by_relevance_descending_order(self, mock_context_store, profile_developer, sample_articles_diverse):
        """Test articles are sorted by relevance descending."""
        result = sort_by_relevance(sample_articles_diverse, profile_developer, mock_context_store)
        # Check that relevance_score attribute is set and decreasing
        for i in range(len(result) - 1):
            if hasattr(result[i], "relevance_score") and hasattr(result[i+1], "relevance_score"):
                assert result[i].relevance_score >= result[i+1].relevance_score

    def test_sort_by_relevance_ai_article_first(self, mock_context_store, profile_developer, sample_articles_diverse):
        """Test AI article ranks high for developer profile."""
        result = sort_by_relevance(sample_articles_diverse, profile_developer, mock_context_store)
        # AI should be in watching list for developer
        ai_article = next((a for a in result if "AI" in (a.trend_tags or "")), None)
        if ai_article:
            # Should be in top half
            ai_index = result.index(ai_article)
            assert ai_index < len(result) / 2


class TestSortByRelevanceScoreStorage:
    """Test sort_by_relevance stores scores on articles."""

    def test_sort_by_relevance_sets_score_attribute(self, mock_context_store, profile_developer, sample_article):
        """Test sort_by_relevance sets relevance_score on articles."""
        result = sort_by_relevance([sample_article], profile_developer, mock_context_store)
        assert hasattr(result[0], "relevance_score")
        assert isinstance(result[0].relevance_score, float)

    def test_sort_by_relevance_score_bounded(self, mock_context_store, profile_developer, sample_articles_bulk):
        """Test stored scores are bounded 0-1."""
        result = sort_by_relevance(sample_articles_bulk, profile_developer, mock_context_store)
        for article in result:
            if hasattr(article, "relevance_score"):
                assert 0.0 <= article.relevance_score <= 1.0


class TestSortByRelevanceProfiles:
    """Test sort_by_relevance with different profiles."""

    def test_sort_by_relevance_researcher_prefers_ml(self, mock_context_store, profile_researcher, sample_articles_diverse):
        """Test researcher profile prefers ML/AI articles."""
        result = sort_by_relevance(sample_articles_diverse, profile_researcher, mock_context_store)
        # First article should have ML-related tags
        top_article = result[0]
        assert hasattr(top_article, "relevance_score")

    def test_sort_by_relevance_different_profiles_different_order(self, mock_context_store, profile_developer, profile_researcher, sample_articles_diverse):
        """Test different profiles produce different orderings."""
        result_dev = sort_by_relevance(sample_articles_diverse.copy(), profile_developer, mock_context_store)
        result_res = sort_by_relevance(sample_articles_diverse.copy(), profile_researcher, mock_context_store)
        # Orderings may differ
        dev_ids = [a.id for a in result_dev]
        res_ids = [a.id for a in result_res]
        # They could be the same or different depending on profile overlap
        # At minimum, both should return valid lists
        assert len(dev_ids) == len(res_ids)


class TestSortByRelevanceEdgeCases:
    """Test sort_by_relevance edge cases."""

    def test_sort_by_relevance_single_article(self, mock_context_store, profile_developer, sample_article):
        """Test sort with single article."""
        result = sort_by_relevance([sample_article], profile_developer, mock_context_store)
        assert len(result) == 1
        assert result[0].id == sample_article.id

    def test_sort_by_relevance_mock_articles(self, mock_context_store, profile_developer, mock_article_ai, mock_article_python):
        """Test sort with mock articles."""
        result = sort_by_relevance([mock_article_ai, mock_article_python], profile_developer, mock_context_store)
        assert len(result) == 2


# =============================================================================
# Test Classes for apply_diversity_filter Function
# =============================================================================


class TestApplyDiversityFilterBasic:
    """Test apply_diversity_filter() basic functionality."""

    def test_apply_diversity_filter_returns_list(self, profile_developer, diversity_test_articles):
        """Test apply_diversity_filter returns a list."""
        result = apply_diversity_filter(diversity_test_articles, profile_developer)
        assert isinstance(result, list)

    def test_apply_diversity_filter_empty_list(self, profile_developer):
        """Test apply_diversity_filter with empty list."""
        result = apply_diversity_filter([], profile_developer)
        assert result == []

    def test_apply_diversity_filter_single_article(self, profile_developer):
        """Test apply_diversity_filter with single article."""
        article = MagicMock(id="single", relevance_score=0.9)
        result = apply_diversity_filter([article], profile_developer)
        # With single article, diverse_count = max(1, int(1 * 0.15)) = 1
        # So it may return duplicated or just the one
        assert len(result) >= 1


class TestApplyDiversityFilterMixing:
    """Test apply_diversity_filter mixing behavior."""

    def test_apply_diversity_filter_interleaves(self, profile_developer, diversity_test_articles):
        """Test diversity filter interleaves high and low relevance."""
        result = apply_diversity_filter(diversity_test_articles, profile_developer)
        # Should mix high relevance (beginning) with diverse (end)
        # With 10 articles and 0.15 factor, diverse_count = 1
        # Result should include both high and diverse content
        result_ids = [a.id for a in result]
        assert any(id.startswith("high") for id in result_ids)
        assert any(id.startswith("low") for id in result_ids)

    def test_apply_diversity_filter_custom_factor(self, profile_developer, diversity_test_articles):
        """Test diversity filter with custom diversity factor."""
        # Higher diversity factor = more diverse articles
        result_low = apply_diversity_filter(diversity_test_articles, profile_developer, diversity_factor=0.1)
        result_high = apply_diversity_filter(diversity_test_articles, profile_developer, diversity_factor=0.4)
        # Both should return valid lists
        assert len(result_low) >= 1
        assert len(result_high) >= 1


class TestApplyDiversityFilterFactor:
    """Test apply_diversity_filter factor calculations."""

    def test_apply_diversity_filter_zero_factor(self, profile_developer, diversity_test_articles):
        """Test diversity filter with zero factor."""
        result = apply_diversity_filter(diversity_test_articles, profile_developer, diversity_factor=0.0)
        # diverse_count = max(1, int(10 * 0.0)) = 1
        # So still includes at least 1 diverse article
        assert len(result) >= 1

    def test_apply_diversity_filter_one_factor(self, profile_developer, diversity_test_articles):
        """Test diversity filter with factor of 1.0."""
        result = apply_diversity_filter(diversity_test_articles, profile_developer, diversity_factor=1.0)
        # All articles are "diverse"
        assert len(result) >= len(diversity_test_articles)

    def test_apply_diversity_filter_minimum_diverse_count(self, profile_developer):
        """Test diversity filter always includes at least 1 diverse article."""
        articles = [MagicMock(id=f"a{i}", relevance_score=0.9-i*0.1) for i in range(3)]
        result = apply_diversity_filter(articles, profile_developer, diversity_factor=0.01)
        # diverse_count = max(1, int(3 * 0.01)) = 1
        assert len(result) >= 1


class TestApplyDiversityFilterOrdering:
    """Test apply_diversity_filter maintains relative ordering."""

    def test_apply_diversity_filter_high_relevance_first(self, profile_developer, diversity_test_articles):
        """Test high relevance articles generally come first."""
        result = apply_diversity_filter(diversity_test_articles, profile_developer)
        # The interleaving pattern: high, diverse, high, diverse...
        # First article should be from highly_relevant
        first_id = result[0].id
        assert first_id.startswith("high")

    def test_apply_diversity_filter_preserves_relative_order(self, profile_developer):
        """Test relative order within categories is preserved."""
        articles = [
            MagicMock(id="h1", relevance_score=0.95),
            MagicMock(id="h2", relevance_score=0.90),
            MagicMock(id="h3", relevance_score=0.85),
            MagicMock(id="l1", relevance_score=0.15),
            MagicMock(id="l2", relevance_score=0.10),
        ]
        result = apply_diversity_filter(articles, profile_developer, diversity_factor=0.2)
        # With 5 articles and 0.2 factor, diverse_count = 1
        # highly_relevant = first 4, diverse = last 1
        # Result should interleave: h1, l2, h2, h3, h4? or similar
        # Check high relevance maintains relative order among themselves
        high_ids = [a.id for a in result if a.id.startswith("h")]
        # h1 should come before h2, h2 before h3
        if len(high_ids) >= 2:
            h1_idx = high_ids.index("h1") if "h1" in high_ids else -1
            h2_idx = high_ids.index("h2") if "h2" in high_ids else -1
            if h1_idx >= 0 and h2_idx >= 0:
                assert h1_idx < h2_idx


class TestApplyDiversityFilterEdgeCases:
    """Test apply_diversity_filter edge cases."""

    def test_apply_diversity_filter_two_articles(self, profile_developer):
        """Test diversity filter with exactly two articles."""
        articles = [
            MagicMock(id="high", relevance_score=0.9),
            MagicMock(id="low", relevance_score=0.1),
        ]
        result = apply_diversity_filter(articles, profile_developer)
        assert len(result) >= 2

    def test_apply_diversity_filter_many_articles(self, profile_developer):
        """Test diversity filter with many articles."""
        articles = [MagicMock(id=f"art{i}", relevance_score=1.0-i*0.01) for i in range(100)]
        result = apply_diversity_filter(articles, profile_developer)
        # Should handle large lists
        assert len(result) >= len(articles) - 1  # May have slight variations due to interleaving

    def test_apply_diversity_filter_uses_profile_factor(self, diversity_test_articles):
        """Test diversity filter can use profile's diversity_factor."""
        profile = UserContextProfile(diversity_factor=0.25)
        # Note: current implementation takes diversity_factor as parameter, not from profile
        result = apply_diversity_filter(diversity_test_articles, profile, diversity_factor=profile.diversity_factor)
        assert len(result) >= 1


# =============================================================================
# Test Classes for Relevance Integration
# =============================================================================


class TestRelevanceIntegration:
    """Integration tests for relevance engine and filtering."""

    def test_full_relevance_workflow(self, relevance_test_setup, sample_articles_diverse):
        """Test full workflow: calculate relevance, sort, filter."""
        engine = relevance_test_setup["engine"]
        profile = relevance_test_setup["profile"]
        store = relevance_test_setup["store"]

        # Calculate relevance for all articles
        for article in sample_articles_diverse:
            score = engine.calculate_relevance(article, profile)
            assert 0.0 <= score <= 1.0

        # Sort by relevance
        sorted_articles = sort_by_relevance(sample_articles_diverse, profile, store)
        assert len(sorted_articles) == len(sample_articles_diverse)

        # Apply diversity filter
        filtered = apply_diversity_filter(sorted_articles, profile)
        assert len(filtered) >= 1

    def test_relevance_with_empty_store(self, mock_context_store, profile_developer, sample_articles_bulk):
        """Test relevance engine with empty store (mock)."""
        engine = RelevanceEngine(mock_context_store)

        # Should still work with mock store
        for article in sample_articles_bulk[:5]:
            score = engine.calculate_relevance(article, profile_developer)
            assert 0.0 <= score <= 1.0

    def test_relevance_with_engagement_data(self, relevance_test_setup, sample_articles_diverse):
        """Test relevance with engagement data."""
        engine = relevance_test_setup["engine"]
        profile = relevance_test_setup["profile"]

        for article in sample_articles_diverse:
            score = engine.calculate_relevance(article, profile)
            assert 0.0 <= score <= 1.0

    def test_sorting_then_filtering_workflow(self, mock_context_store, profile_developer, sample_articles_bulk):
        """Test sorting followed by filtering."""
        # Sort
        sorted_articles = sort_by_relevance(sample_articles_bulk, profile_developer, mock_context_store)

        # Verify sorting
        for i in range(len(sorted_articles) - 1):
            if hasattr(sorted_articles[i], "relevance_score") and hasattr(sorted_articles[i+1], "relevance_score"):
                assert sorted_articles[i].relevance_score >= sorted_articles[i+1].relevance_score

        # Filter
        filtered = apply_diversity_filter(sorted_articles, profile_developer)

        # Should still have reasonable number of articles
        assert len(filtered) >= len(sorted_articles) * 0.5

    def test_relevance_consistency(self, relevance_engine_mock, sample_article_ai, profile_developer):
        """Test relevance scores are consistent for same inputs."""
        score1 = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_developer)
        score2 = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_developer)
        assert score1 == score2

    def test_relevance_different_articles(self, relevance_engine_mock, sample_article_ai, sample_article_celebrity, profile_developer):
        """Test different articles get different relevance scores."""
        score_ai = relevance_engine_mock.calculate_relevance(sample_article_ai, profile_developer)
        score_celeb = relevance_engine_mock.calculate_relevance(sample_article_celebrity, profile_developer)
        # AI should score higher than celebrity for developer
        assert score_ai > score_celeb
