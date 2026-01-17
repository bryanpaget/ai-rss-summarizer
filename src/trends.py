"""Trend detection and categorization.

ARCHITECTURE:
- Category embeddings are pre-computed ONCE and stored in FAISS as type "category"
- Article categorization uses STORED article embeddings (never re-embeds)
- FAISS ANN search finds nearest categories efficiently

NO embedding calls happen during categorization - all embeddings must be pre-computed.
"""

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from .storage import Storage
from .emergence import detect_emerging_trends, format_emerging_trend
from .knowledge import KnowledgeBase
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)


# Category descriptions for embedding-based matching
# Each category has a representative description that captures its semantic meaning
TREND_CATEGORY_DESCRIPTIONS = {
    "AI": "artificial intelligence, machine learning, neural networks, deep learning, large language models, GPT, ChatGPT, generative AI, AI assistants, transformers",
    "Technology": "technology, software development, hardware, startups, programming, cybersecurity, cloud computing, data centers, tech industry, digital transformation",
    "Politics & Government": "politics, government, elections, legislation, congress, senate, democracy, political parties, policy making, international relations",
    "Business & Economy": "business, economy, stock market, finance, investment, startups, mergers, acquisitions, corporate earnings, economic indicators",
    "Science & Research": "scientific research, discoveries, experiments, space exploration, physics, biology, chemistry, academic studies, breakthroughs",
    "Climate & Environment": "climate change, environment, renewable energy, sustainability, carbon emissions, conservation, pollution, natural disasters",
    "Health & Medicine": "health, medicine, medical research, hospitals, disease treatment, pharmaceuticals, healthcare, mental health, public health",
    "Entertainment & Culture": "entertainment, movies, music, gaming, streaming, celebrities, cultural events, arts, sports, media",
    "World & International": "international affairs, global events, diplomacy, conflicts, humanitarian issues, foreign policy, world news",
}

# Similarity threshold for category matching
CATEGORY_SIMILARITY_THRESHOLD = 0.45

# In-memory cache for category embeddings (loaded from FAISS, never created fresh)
_category_embeddings_cache: dict[str, list[float]] = {}
_categories_initialized: bool = False


def ensure_categories_initialized(embedding_service: "EmbeddingService") -> bool:
    """
    Ensure category embeddings exist in FAISS.

    This should be called ONCE during pipeline initialization (pre-embedding phase),
    NOT during article categorization.

    Returns True if categories are ready, False if embedding service unavailable.
    """
    global _categories_initialized, _category_embeddings_cache

    if _categories_initialized:
        return True

    if embedding_service is None or not embedding_service.is_available():
        logger.warning("Cannot initialize categories - embedding service unavailable")
        return False

    # Check if categories already exist in FAISS
    categories_found = 0
    for category in TREND_CATEGORY_DESCRIPTIONS.keys():
        emb = embedding_service.get_embedding(f"category:{category}", "category")
        if emb:
            _category_embeddings_cache[category] = emb
            categories_found += 1

    if categories_found == len(TREND_CATEGORY_DESCRIPTIONS):
        logger.info(f"Loaded {categories_found} category embeddings from FAISS")
        _categories_initialized = True
        return True

    # Need to create category embeddings - this is the ONLY place embed_text is allowed
    logger.info(f"Seeding {len(TREND_CATEGORY_DESCRIPTIONS)} category embeddings into FAISS...")
    for category, description in TREND_CATEGORY_DESCRIPTIONS.items():
        if category in _category_embeddings_cache:
            continue  # Already loaded
        try:
            result = embedding_service.embed_text(description)
            embedding_service.save_embedding(f"category:{category}", "category", result)
            _category_embeddings_cache[category] = result.vector
        except Exception as e:
            logger.error(f"Failed to seed category '{category}': {e}")
            return False

    _categories_initialized = True
    logger.info("Category embeddings initialized successfully")
    return True


def _get_category_embeddings(embedding_service: "EmbeddingService") -> dict[str, list[float]]:
    """
    Get category embeddings from cache.

    IMPORTANT: Does NOT create embeddings. Categories must be initialized first
    via ensure_categories_initialized() during pre-embedding phase.
    """
    global _category_embeddings_cache

    if _category_embeddings_cache:
        return _category_embeddings_cache

    # Try to load from FAISS (but don't create)
    for category in TREND_CATEGORY_DESCRIPTIONS.keys():
        emb = embedding_service.get_embedding(f"category:{category}", "category")
        if emb:
            _category_embeddings_cache[category] = emb

    if not _category_embeddings_cache:
        logger.error(
            "Category embeddings not found! Call ensure_categories_initialized() "
            "during pre-embedding phase before categorizing articles."
        )

    return _category_embeddings_cache


def categorize_by_stored_embedding(
    article_embedding: list[float],
    embedding_service: "EmbeddingService",
) -> list[str]:
    """
    Categorize using a PRE-COMPUTED embedding vector.

    This is the correct way to categorize - using stored embeddings,
    never creating new ones.

    Args:
        article_embedding: Pre-computed embedding vector for the article
        embedding_service: For cosine similarity calculation only (no embed calls)

    Returns:
        List of matching category names
    """
    category_embeddings = _get_category_embeddings(embedding_service)
    if not category_embeddings:
        return ["Uncategorized"]

    matches = []
    for category, cat_embedding in category_embeddings.items():
        similarity = embedding_service.cosine_similarity(article_embedding, cat_embedding)
        if similarity >= CATEGORY_SIMILARITY_THRESHOLD:
            matches.append((category, similarity))

    matches.sort(key=lambda x: x[1], reverse=True)
    return [cat for cat, _ in matches] if matches else ["Uncategorized"]


def categorize_text(
    text: str,
    embedding_service: Optional["EmbeddingService"] = None,
) -> list[str]:
    """
    DEPRECATED: This function creates new embeddings which violates architecture.

    Use categorize_by_stored_embedding() with a pre-computed embedding instead.

    This remains for backwards compatibility but logs a warning.
    """
    logger.warning(
        "categorize_text() called - this creates new embeddings and is deprecated. "
        "Use categorize_by_stored_embedding() with stored article embeddings instead."
    )

    if not text:
        return ["Uncategorized"]

    if embedding_service is None or not embedding_service.is_available():
        return ["Uncategorized"]

    try:
        # DEPRECATED: Creates new embedding - should use stored
        text_result = embedding_service.embed_text(text[:1000])
        return categorize_by_stored_embedding(text_result.vector, embedding_service)
    except Exception as e:
        logger.error(f"Categorization failed: {e}")
        return ["Uncategorized"]


def analyze_article(
    article,
    embedding_service: Optional["EmbeddingService"] = None,
    storage: Optional["Storage"] = None,
) -> str:
    """
    Categorize an article using its STORED embedding.

    ARCHITECTURE: This function NEVER creates new embeddings.
    It retrieves the article's pre-computed embedding from storage
    and compares against pre-computed category embeddings.

    Args:
        article: Article with .id attribute
        embedding_service: For similarity calculation (not embedding retrieval)
        storage: Storage instance for retrieving article embeddings

    Returns:
        Comma-separated category names
    """
    if embedding_service is None or not embedding_service.is_available():
        return "Uncategorized"

    # Get the article's STORED embedding from storage (articles.db)
    # NOT from embedding_service (knowledge.db) - that's a different database!
    article_embedding = None
    if storage is not None:
        article_embedding = storage.get_embedding(article.id)

    # Fallback to embedding_service for backwards compatibility
    if article_embedding is None:
        article_embedding = embedding_service.get_embedding(article.id, "article")

    if article_embedding is None:
        logger.warning(
            f"Article '{article.id}' has no stored embedding. "
            f"Run embedding phase first before categorization."
        )
        return "Uncategorized"

    categories = categorize_by_stored_embedding(article_embedding, embedding_service)
    return ", ".join(categories)


def analyze_trends(
    storage: Optional[Storage] = None,
    limit: int = 100,
    hours: int = 24,
) -> dict:
    """
    Analyze trends across articles in storage.

    Args:
        storage: Storage instance
        limit: Max articles to analyze
        hours: Time window for "recent" trends (default 24h)

    Returns:
        Dictionary with trend statistics, top categories, and velocity data.
    """
    if storage is None:
        storage = Storage()

    # Initialize embedding service for trend categorization
    kb = KnowledgeBase()
    embedding_service = EmbeddingService(kb)

    articles = storage.get_articles(limit=limit)

    now = datetime.now()
    recent_cutoff = now - timedelta(hours=hours)
    older_cutoff = now - timedelta(hours=hours * 2)

    # Count categories for different time periods
    all_counts = Counter()
    recent_counts = Counter()  # Last 24h (or specified hours)
    older_counts = Counter()   # Previous period for comparison
    processed = 0

    for article in articles:
        # Get or compute trend tags
        if not article.trend_tags:
            # Only tag if article has an embedding
            if storage.get_embedding(article.id) is not None:
                tags = analyze_article(article, embedding_service=embedding_service, storage=storage)
                storage.update_trends(article.id, tags)
            else:
                tags = "Uncategorized"
        else:
            tags = article.trend_tags

        tag_list = [t.strip() for t in tags.split(",")]

        for tag in tag_list:
            all_counts[tag] += 1

            # Time-based bucketing
            if article.published:
                try:
                    pub_str = article.published
                    if "Z" in pub_str:
                        pub_str = pub_str.replace("Z", "+00:00")
                    pub_time = datetime.fromisoformat(pub_str)
                    pub_time = pub_time.replace(tzinfo=None)

                    if pub_time >= recent_cutoff:
                        recent_counts[tag] += 1
                    elif pub_time >= older_cutoff:
                        older_counts[tag] += 1
                except (ValueError, TypeError):
                    recent_counts[tag] += 1
            else:
                recent_counts[tag] += 1

        processed += 1

    # Calculate velocity (trending up/down)
    velocity = {}
    for tag in set(list(recent_counts.keys()) + list(older_counts.keys())):
        recent = recent_counts.get(tag, 0)
        older = older_counts.get(tag, 0)
        if older > 0:
            velocity[tag] = ((recent - older) / older) * 100
        elif recent > 0:
            velocity[tag] = 100  # New trend
        else:
            velocity[tag] = 0

    # Get top trends
    top_trends = all_counts.most_common(10)

    # Find emerging trends (high velocity, at least 2 recent articles)
    emerging = sorted(
        [(tag, vel) for tag, vel in velocity.items()
         if vel > 0 and recent_counts.get(tag, 0) >= 2],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # Find declining trends
    declining = sorted(
        [(tag, vel) for tag, vel in velocity.items() if vel < 0],
        key=lambda x: x[1]
    )[:5]

    # Get enhanced emerging trends from emergence detection
    emerging_trends_enhanced = []
    try:
        emerging_trends_enhanced = detect_emerging_trends(
            storage,
            limit=limit,
            min_confidence="Low"
        )
    except Exception as e:
        # If emergence detection fails, fall back to basic emerging
        print(f"Emergence detection failed: {e}")

    return {
        "processed": processed,
        "top_trends": top_trends,
        "category_counts": dict(all_counts),
        "recent_counts": dict(recent_counts),
        "emerging": emerging,  # Keep basic emerging for backwards compatibility
        "emerging_enhanced": emerging_trends_enhanced,  # New enhanced format
        "declining": declining,
        "hours": hours,
    }


def get_articles_by_trend(
    storage: Storage,
    trend: str,
    limit: int = 20,
) -> list:
    """Get articles matching a specific trend category."""
    articles = storage.get_articles(limit=500)
    matching = []

    for article in articles:
        if article.trend_tags and trend.lower() in article.trend_tags.lower():
            matching.append(article)
            if len(matching) >= limit:
                break

    return matching


def llm_categorize(article, provider) -> str:
    """
    Use LLM to categorize an article that keyword matching missed.
    Only called for uncategorized articles when LLM is available.
    """
    categories = list(TREND_CATEGORY_DESCRIPTIONS.keys())
    prompt = f"""Categorize this article into one of these categories: {', '.join(categories)}

Title: {article.title}
Content: {article.content or 'No content'}

Return only the category name, nothing else."""

    try:
        result = provider.summarize(prompt, max_length=50)
        for cat in categories:
            if cat.lower() in result.lower():
                return cat
        return "Uncategorized"
    except Exception:
        return "Uncategorized"
