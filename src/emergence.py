"""Emergence detection for identifying trends before they go mainstream."""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .storage import Storage


# Configuration
EMERGENCE_CONFIG = {
    "min_current_mentions": 3,
    "min_historical_mentions": 0,
    "max_historical_mentions": 2,
    "emerging_velocity": 100,  # % change
    "accelerating_velocity": 50,
    "mainstream_velocity": 20,
    "current_window": 7,  # days
    "comparison_windows": [7, 14, 28, 60],  # days
    "min_domains_for_cross": 2,
    "min_weeks_for_trajectory": 3,
}


@dataclass
class EmergingTrend:
    """Represents an emerging trend."""

    term: str
    current_mentions: int
    historical_mentions: dict[str, int]  # {period: count}
    velocity: float
    confidence: str  # "High", "Medium", "Low"
    trajectory: str
    domains: list[str]
    action_recommendation: str
    recent_article_ids: list[str]
    related_trends: list[str]


def extract_terms(text: str, min_words: int = 2, max_words: int = 4) -> list[str]:
    """
    Extract potential emerging terms from text.

    Focuses on:
    - Multi-word phrases (2-4 words)
    - Capitalized terms (likely proper nouns/technical terms)
    - Technical terminology patterns
    """
    if not text:
        return []

    # Common stopwords to filter
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "must", "can", "this",
        "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
    }

    terms = []

    # Pattern 1: Capitalized multi-word phrases
    # Matches: "Constitutional AI", "Mixture of Experts", etc.
    # Updated to handle acronyms like "AI" and mixed case
    capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+(?:of|for|and|the|in|on|with)?\s*[A-Z][A-Za-z]+)+)\b'
    capitalized_matches = re.findall(capitalized_pattern, text)
    terms.extend(capitalized_matches)

    # Pattern 2: Technical terms with common patterns
    # Matches: "neural networks", "machine learning", etc.
    technical_pattern = r'\b([a-z]+\s+(?:learning|network|model|algorithm|system|framework|architecture|intelligence|computing))\b'
    technical_matches = re.findall(technical_pattern, text.lower())
    terms.extend(technical_matches)

    # Pattern 3: Acronyms followed by expansion
    # Matches: "LLM (Large Language Model)" → extracts both
    acronym_pattern = r'\b([A-Z]{2,})\s*\(([^)]+)\)'
    acronym_matches = re.findall(acronym_pattern, text)
    for acronym, expansion in acronym_matches:
        terms.append(acronym)
        terms.append(expansion)

    # Clean and filter terms
    cleaned_terms = []
    for term in terms:
        # Normalize whitespace
        term = " ".join(term.split())

        # Skip if too short or too long
        word_count = len(term.split())
        if word_count < min_words or word_count > max_words:
            continue

        # Skip if all stopwords
        words = term.lower().split()
        if all(w in stopwords for w in words):
            continue

        # Skip if too generic (all lowercase single words)
        if term.islower() and word_count == 1:
            continue

        cleaned_terms.append(term)

    return cleaned_terms


def calculate_velocity(
    current_count: int,
    previous_count: int,
) -> float:
    """
    Calculate velocity (rate of change) between two periods.

    Returns percentage change. Handles division by zero.
    """
    if previous_count == 0:
        if current_count > 0:
            return 100.0  # New term, max velocity
        return 0.0

    return ((current_count - previous_count) / previous_count) * 100


def classify_trajectory(
    historical_counts: dict[str, int],
    domains: list[str],
) -> str:
    """
    Classify the trajectory of a term based on its history and domains.

    Returns trajectory type like:
    - "Research → Blogs → Mainstream"
    - "Technical → General"
    - "Niche → Widespread"
    """
    # Check domain progression
    has_research = any(
        "Research" in d or "Science" in d for d in domains
    )
    has_tech = any("Technology" in d or "AI" in d for d in domains)
    has_business = any("Business" in d or "Economy" in d for d in domains)
    has_mainstream = any(
        "Politics" in d or "World" in d or "Entertainment" in d
        for d in domains
    )

    # Analyze growth pattern
    counts = list(historical_counts.values())
    if len(counts) >= 3:
        # Check if consistently growing
        is_growing = all(
            counts[i] <= counts[i + 1] for i in range(len(counts) - 1)
        )

        if is_growing:
            if has_research and has_tech and has_business:
                return "Research → Blogs → Mainstream"
            elif has_tech and has_business:
                return "Technical → Business adoption"
            elif has_tech and has_mainstream:
                return "Blogs → Mainstream"

    # Check domain spread
    domain_count = len(set(domains))
    if domain_count == 1:
        return "Niche (single domain)"
    elif domain_count >= 3:
        return "Niche → Widespread"
    else:
        return "Cross-domain emergence"


def assign_confidence(
    velocity: float,
    current_mentions: int,
    domain_count: int,
    weeks_of_data: int,
) -> str:
    """Assign confidence level to an emerging trend prediction."""
    if (
        velocity > 150
        and current_mentions >= 5
        and domain_count >= 3
        and weeks_of_data >= 3
    ):
        return "High"
    elif (
        velocity > 100
        and current_mentions >= 3
        and domain_count >= 2
    ):
        return "Medium"
    elif velocity > 50 and current_mentions >= 3:
        return "Low"
    else:
        return "Watch"


def generate_action_recommendation(
    confidence: str,
    velocity: float,
    trajectory: str,
) -> str:
    """Generate actionable recommendation for user."""
    if confidence == "High":
        return "Learn now before it's everywhere"
    elif confidence == "Medium":
        if "Mainstream" in trajectory:
            return "If unfamiliar, prioritize learning"
        else:
            return "Worth monitoring, may become important"
    elif confidence == "Low":
        return "Early signal, monitor for development"
    else:
        return "Too early to assess, keep watching"


def detect_emerging_trends(
    storage: Storage,
    limit: int = 1000,
    min_confidence: str = "Low",
) -> list[EmergingTrend]:
    """
    Detect emerging trends from stored articles.

    Args:
        storage: Storage instance
        limit: Max articles to analyze
        min_confidence: Minimum confidence level to include

    Returns:
        List of EmergingTrend objects, sorted by confidence and velocity
    """
    # Get recent articles
    articles = storage.get_articles(limit=limit)

    if not articles:
        return []

    # Time windows for analysis
    now = datetime.now()
    windows = {
        "current": (now - timedelta(days=7), now),
        "1_week_ago": (now - timedelta(days=14), now - timedelta(days=7)),
        "2_weeks_ago": (now - timedelta(days=21), now - timedelta(days=14)),
        "1_month_ago": (now - timedelta(days=28), now - timedelta(days=21)),
        "2_months_ago": (now - timedelta(days=60), now - timedelta(days=28)),
    }

    # Track term mentions by time window and domain
    term_data = defaultdict(lambda: {
        "windows": defaultdict(int),
        "domains": set(),
        "article_ids": [],
    })

    # Extract terms from articles
    for article in articles:
        # Parse article date
        if not article.published:
            continue

        try:
            pub_str = article.published
            if "Z" in pub_str:
                pub_str = pub_str.replace("Z", "+00:00")
            pub_time = datetime.fromisoformat(pub_str)
            pub_time = pub_time.replace(tzinfo=None)
        except (ValueError, TypeError) as e:
            import sys
            print(f"Date parsing failed for emergence detection: {e}", file=sys.stderr)
            continue

        # Extract terms from article
        combined_text = f"{article.title} {article.content or ''}"
        terms = extract_terms(combined_text)

        # Get article domains/categories
        article_domains = []
        if article.trend_tags:
            article_domains = [t.strip() for t in article.trend_tags.split(",")]

        # Categorize by time window
        for window_name, (start, end) in windows.items():
            if start <= pub_time < end:
                for term in terms:
                    term_lower = term.lower()
                    term_data[term_lower]["windows"][window_name] += 1
                    term_data[term_lower]["domains"].update(article_domains)
                    if window_name == "current":
                        term_data[term_lower]["article_ids"].append(article.id)
                break

    # Analyze each term for emergence
    emerging_trends = []

    for term, data in term_data.items():
        current = data["windows"].get("current", 0)
        week_ago = data["windows"].get("1_week_ago", 0)
        two_months_ago = data["windows"].get("2_months_ago", 0)

        # Check emergence criteria
        if current < EMERGENCE_CONFIG["min_current_mentions"]:
            continue

        if two_months_ago > EMERGENCE_CONFIG["max_historical_mentions"]:
            continue  # Already established, not emerging

        # Calculate velocity
        velocity = calculate_velocity(current, week_ago)

        if velocity < EMERGENCE_CONFIG["emerging_velocity"]:
            continue  # Not growing fast enough

        # Classify trajectory
        domains = list(data["domains"])
        historical_counts = {
            "2_months_ago": data["windows"].get("2_months_ago", 0),
            "1_month_ago": data["windows"].get("1_month_ago", 0),
            "2_weeks_ago": data["windows"].get("2_weeks_ago", 0),
            "1_week_ago": data["windows"].get("1_week_ago", 0),
            "current": current,
        }

        trajectory = classify_trajectory(historical_counts, domains)

        # Assign confidence
        weeks_of_data = sum(
            1 for count in historical_counts.values() if count > 0
        )
        confidence = assign_confidence(
            velocity,
            current,
            len(set(domains)),
            weeks_of_data,
        )

        # Filter by minimum confidence
        confidence_levels = ["Watch", "Low", "Medium", "High"]
        if confidence_levels.index(confidence) < confidence_levels.index(min_confidence):
            continue

        # Generate recommendation
        action = generate_action_recommendation(confidence, velocity, trajectory)

        # Find related trends (terms that co-occur in articles)
        related = []
        # TODO: Implement co-occurrence analysis

        emerging_trends.append(
            EmergingTrend(
                term=term,
                current_mentions=current,
                historical_mentions=historical_counts,
                velocity=velocity,
                confidence=confidence,
                trajectory=trajectory,
                domains=domains,
                action_recommendation=action,
                recent_article_ids=data["article_ids"],
                related_trends=related,
            )
        )

    # Sort by confidence then velocity
    confidence_order = {"High": 3, "Medium": 2, "Low": 1, "Watch": 0}
    emerging_trends.sort(
        key=lambda t: (confidence_order[t.confidence], t.velocity),
        reverse=True,
    )

    return emerging_trends


def format_emerging_trend(trend: EmergingTrend, storage: Storage) -> str:
    """
    Format an emerging trend for display.

    Returns a nicely formatted string representation.
    """
    # Calculate historical change
    oldest = trend.historical_mentions.get("2_months_ago", 0)
    if oldest == 0:
        oldest = min(
            v for v in trend.historical_mentions.values() if v > 0
        ) if any(trend.historical_mentions.values()) else 1

    output = []
    output.append(f'"{trend.term}" ({trend.current_mentions} mentions, up from {oldest} earlier)')
    output.append(f"  Velocity: +{trend.velocity:.0f}%")
    output.append(f"  Trajectory: {trend.trajectory}")

    if trend.domains:
        domains_str = ", ".join(trend.domains[:3])
        if len(trend.domains) > 3:
            domains_str += f" +{len(trend.domains) - 3} more"
        output.append(f"  Domains: {domains_str}")

    output.append(f"  Action: {trend.action_recommendation}")

    # Show recent article titles (up to 3)
    if trend.recent_article_ids and len(trend.recent_article_ids) > 0:
        output.append("")
        output.append("  Recent articles:")
        for article_id in trend.recent_article_ids[:3]:
            article = storage.get_article(article_id)
            if article:
                # Truncate title if too long
                title = article.title
                if len(title) > 60:
                    title = title[:57] + "..."

                # Format date
                date_str = ""
                if article.published:
                    try:
                        pub_str = article.published
                        if "Z" in pub_str:
                            pub_str = pub_str.replace("Z", "+00:00")
                        pub_time = datetime.fromisoformat(pub_str)
                        date_str = pub_time.strftime("%b %d")
                    except (ValueError, TypeError) as e:
                        import sys
                        print(f"Date formatting failed for trend display: {e}", file=sys.stderr)

                output.append(f'    - "{title}" ({date_str})')

    return "\n".join(output)
