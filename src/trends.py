"""Trend detection and categorization."""

from collections import Counter
from typing import Optional

from .storage import Storage


# Predefined trend categories with keywords
TREND_CATEGORIES = {
    "AI & Technology": [
        "ai", "artificial intelligence", "machine learning", "llm", "gpt",
        "neural", "algorithm", "automation", "robot", "tech", "software",
        "startup", "silicon valley", "crypto", "blockchain", "cybersecurity",
    ],
    "Politics & Government": [
        "election", "president", "congress", "senate", "government", "policy",
        "democracy", "republican", "democrat", "vote", "legislation", "law",
        "minister", "parliament",
    ],
    "Business & Economy": [
        "market", "stock", "economy", "inflation", "recession", "finance",
        "investment", "startup", "ipo", "merger", "acquisition", "revenue",
        "profit", "gdp", "unemployment",
    ],
    "Science & Research": [
        "research", "study", "discovery", "scientist", "experiment", "nasa",
        "space", "physics", "biology", "chemistry", "medicine", "vaccine",
        "clinical", "trial",
    ],
    "Climate & Environment": [
        "climate", "environment", "pollution", "carbon", "renewable", "solar",
        "wind", "sustainable", "emission", "warming", "biodiversity",
        "conservation", "wildfire", "flood", "hurricane",
    ],
    "Health & Medicine": [
        "health", "medical", "hospital", "disease", "treatment", "drug",
        "fda", "pandemic", "virus", "cancer", "mental health", "therapy",
        "diagnosis",
    ],
    "Entertainment & Culture": [
        "movie", "film", "music", "celebrity", "entertainment", "streaming",
        "netflix", "disney", "game", "gaming", "sports", "concert", "art",
        "culture",
    ],
    "World & International": [
        "international", "global", "united nations", "war", "conflict",
        "peace", "treaty", "diplomatic", "foreign", "refugee", "humanitarian",
    ],
}


def categorize_text(text: str) -> list[str]:
    """
    Categorize text into trend categories based on keyword matching.
    Returns list of matching categories.
    """
    if not text:
        return ["Uncategorized"]

    text_lower = text.lower()
    matches = []

    for category, keywords in TREND_CATEGORIES.items():
        for keyword in keywords:
            if keyword in text_lower:
                matches.append(category)
                break

    return matches if matches else ["Uncategorized"]


def analyze_article(article) -> str:
    """
    Analyze an article and return trend tags.
    Combines title and content for better categorization.
    """
    combined_text = f"{article.title} {article.content}"
    categories = categorize_text(combined_text)
    return ", ".join(categories)


def analyze_trends(
    storage: Optional[Storage] = None,
    limit: int = 100,
) -> dict:
    """
    Analyze trends across articles in storage.

    Returns:
        Dictionary with trend statistics and top categories.
    """
    if storage is None:
        storage = Storage()

    articles = storage.get_articles(limit=limit)

    # Count categories
    category_counts = Counter()
    processed = 0

    for article in articles:
        # Get or compute trend tags
        if not article.trend_tags:
            tags = analyze_article(article)
            storage.update_trends(article.id, tags)
        else:
            tags = article.trend_tags

        for tag in tags.split(", "):
            category_counts[tag] += 1
        processed += 1

    # Get top trends
    top_trends = category_counts.most_common(10)

    return {
        "processed": processed,
        "top_trends": top_trends,
        "category_counts": dict(category_counts),
    }


def get_articles_by_trend(
    storage: Storage,
    trend: str,
    limit: int = 20,
) -> list:
    """Get articles matching a specific trend category."""
    articles = storage.get_articles(limit=500)  # Get more to filter
    matching = []

    for article in articles:
        if article.trend_tags and trend.lower() in article.trend_tags.lower():
            matching.append(article)
            if len(matching) >= limit:
                break

    return matching
