"""Trend detection and categorization."""

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

# Cache for category embeddings (populated on first use)
_category_embeddings_cache: dict[str, list[float]] = {}


def _get_category_embeddings(embedding_service: "EmbeddingService") -> dict[str, list[float]]:
    """Get or create embeddings for all categories."""
    global _category_embeddings_cache

    if _category_embeddings_cache:
        return _category_embeddings_cache

    for category, description in TREND_CATEGORY_DESCRIPTIONS.items():
        try:
            result = embedding_service.embed_text(description)
            _category_embeddings_cache[category] = result.vector
        except Exception as e:
            logger.warning(f"Failed to embed category '{category}': {e}")

    return _category_embeddings_cache


def categorize_text(
    text: str,
    embedding_service: Optional["EmbeddingService"] = None,
) -> list[str]:
    """
    Categorize text into trend categories using embedding similarity.

    Args:
        text: Text to categorize
        embedding_service: EmbeddingService for semantic matching.
                          If not available, returns ["Uncategorized"].

    Returns:
        List of matching category names, or ["Uncategorized"] if none match.
    """
    if not text:
        return ["Uncategorized"]

    # Require embedding service
    if embedding_service is None or not embedding_service.is_available():
        logger.error("EmbeddingService required but not available for trend categorization")
        return ["Uncategorized"]

    try:
        # Embed the input text
        text_result = embedding_service.embed_text(text[:1000])  # Limit text length
        text_embedding = text_result.vector

        # Get category embeddings
        category_embeddings = _get_category_embeddings(embedding_service)
        if not category_embeddings:
            logger.error("Failed to create category embeddings")
            return ["Uncategorized"]

        # Find matching categories by similarity
        matches = []
        all_scores = []  # Track all scores for debugging
        for category, cat_embedding in category_embeddings.items():
            similarity = embedding_service.cosine_similarity(text_embedding, cat_embedding)
            all_scores.append((category, similarity))
            if similarity >= CATEGORY_SIMILARITY_THRESHOLD:
                matches.append((category, similarity))

        # Sort all scores for potential logging
        all_scores.sort(key=lambda x: x[1], reverse=True)

        # Sort by similarity and return category names
        matches.sort(key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in matches] if matches else ["Uncategorized"]

    except Exception as e:
        logger.error(f"Categorization failed: {e}")
        return ["Uncategorized"]


def analyze_article(
    article,
    embedding_service: Optional["EmbeddingService"] = None,
) -> str:
    """
    Analyze an article and return trend tags using embedding similarity.

    Args:
        article: Article to analyze
        embedding_service: EmbeddingService for semantic categorization

    Returns:
        Comma-separated category names
    """
    combined_text = f"{article.title} {article.content}"
    categories = categorize_text(combined_text, embedding_service=embedding_service)
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
            tags = analyze_article(article, embedding_service=embedding_service)
            storage.update_trends(article.id, tags)
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
