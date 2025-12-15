"""Trend detection and categorization."""

from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from .storage import Storage
from .emergence import detect_emerging_trends, format_emerging_trend


# Predefined trend categories with keywords
TREND_CATEGORIES = {
    "AI & Technology": [
        "ai", "artificial intelligence", "machine learning", "llm", "gpt",
        "neural", "algorithm", "automation", "robot", "tech", "software",
        "startup", "silicon valley", "crypto", "blockchain", "cybersecurity",
        "claude", "openai", "gemini", "copilot", "chatgpt", "anthropic",
    ],
    "Politics & Government": [
        "election", "president", "congress", "senate", "government", "policy",
        "democracy", "republican", "democrat", "vote", "legislation", "law",
        "minister", "parliament", "biden", "trump",
    ],
    "Business & Economy": [
        "market", "stock", "economy", "inflation", "recession", "finance",
        "investment", "startup", "ipo", "merger", "acquisition", "revenue",
        "profit", "gdp", "unemployment", "earnings", "quarter",
    ],
    "Science & Research": [
        "research", "study", "discovery", "scientist", "experiment", "nasa",
        "space", "physics", "biology", "chemistry", "medicine", "vaccine",
        "clinical", "trial", "breakthrough",
    ],
    "Climate & Environment": [
        "climate", "environment", "pollution", "carbon", "renewable", "solar",
        "wind", "sustainable", "emission", "warming", "biodiversity",
        "conservation", "wildfire", "flood", "hurricane", "ev", "electric vehicle",
    ],
    "Health & Medicine": [
        "health", "medical", "hospital", "disease", "treatment", "drug",
        "fda", "pandemic", "virus", "cancer", "mental health", "therapy",
        "diagnosis", "patient", "doctor",
    ],
    "Entertainment & Culture": [
        "movie", "film", "music", "celebrity", "entertainment", "streaming",
        "netflix", "disney", "game", "gaming", "sports", "concert", "art",
        "culture", "award", "oscar",
    ],
    "World & International": [
        "international", "global", "united nations", "war", "conflict",
        "peace", "treaty", "diplomatic", "foreign", "refugee", "humanitarian",
        "ukraine", "china", "russia", "europe",
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
            tags = analyze_article(article)
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
    categories = list(TREND_CATEGORIES.keys())
    prompt = f"""Categorize this article into one of these categories: {', '.join(categories)}

Title: {article.title}
Content: {article.content[:500] if article.content else 'No content'}

Return only the category name, nothing else."""

    try:
        result = provider.summarize(prompt, max_length=50)
        for cat in categories:
            if cat.lower() in result.lower():
                return cat
        return "Uncategorized"
    except Exception:
        return "Uncategorized"
