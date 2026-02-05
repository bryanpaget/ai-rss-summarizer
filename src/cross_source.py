"""Cross-source comparison for multi-outlet story analysis.

PREMIUM FEATURE: Shows how different sources cover the same story.
Enables detection of bias, framing differences, and fact checking.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from .storage import Storage, Story, Article
from .knowledge import KnowledgeBase


@dataclass
class SourcePerspective:
    """A single source's take on a story."""
    source_name: str
    source_domain: str
    article: Article
    key_claims: list[str]
    framing: str  # e.g., "positive", "negative", "neutral", "alarmist"
    emphasis: list[str]  # What aspects the source emphasizes


@dataclass
class CrossSourceComparison:
    """Comparison of how multiple sources cover a story."""
    story: Story
    sources: list[SourcePerspective]
    common_facts: list[str]
    divergent_claims: list[tuple[str, str, str]]  # (source1, source2, difference)
    coverage_gap: list[str]  # Facts mentioned by some but not all
    bias_indicators: dict[str, str]  # source -> detected bias direction


def extract_domain(url: str) -> str:
    """Extract clean domain name from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url


def get_source_name(domain: str) -> str:
    """Get human-readable source name from domain."""
    # Common news sources
    source_names = {
        "nytimes.com": "New York Times",
        "washingtonpost.com": "Washington Post",
        "wsj.com": "Wall Street Journal",
        "cnn.com": "CNN",
        "foxnews.com": "Fox News",
        "bbc.com": "BBC",
        "bbc.co.uk": "BBC",
        "reuters.com": "Reuters",
        "apnews.com": "Associated Press",
        "theguardian.com": "The Guardian",
        "npr.org": "NPR",
        "nbcnews.com": "NBC News",
        "cbsnews.com": "CBS News",
        "abcnews.go.com": "ABC News",
        "msnbc.com": "MSNBC",
        "politico.com": "Politico",
        "thehill.com": "The Hill",
        "breitbart.com": "Breitbart",
        "huffpost.com": "HuffPost",
        "vox.com": "Vox",
        "slate.com": "Slate",
        "nationalreview.com": "National Review",
        "thedailywire.com": "Daily Wire",
        "dailykos.com": "Daily Kos",
        "theatlantic.com": "The Atlantic",
        "newyorker.com": "The New Yorker",
        "economist.com": "The Economist",
        "ft.com": "Financial Times",
        "bloomberg.com": "Bloomberg",
        "techcrunch.com": "TechCrunch",
        "wired.com": "Wired",
        "arstechnica.com": "Ars Technica",
        "theverge.com": "The Verge",
        "engadget.com": "Engadget",
    }
    return source_names.get(domain, domain.replace(".", " ").title())


# Known source political leanings (for suggesting diverse sources)
SOURCE_LEANINGS = {
    # Left-leaning
    "nytimes.com": "left-center",
    "washingtonpost.com": "left-center",
    "cnn.com": "left",
    "msnbc.com": "left",
    "huffpost.com": "left",
    "vox.com": "left",
    "slate.com": "left",
    "dailykos.com": "far-left",
    "theguardian.com": "left-center",
    "npr.org": "center-left",

    # Center
    "reuters.com": "center",
    "apnews.com": "center",
    "bbc.com": "center",
    "bbc.co.uk": "center",
    "thehill.com": "center",
    "politico.com": "center",

    # Right-leaning
    "wsj.com": "center-right",
    "foxnews.com": "right",
    "breitbart.com": "far-right",
    "nationalreview.com": "right",
    "thedailywire.com": "right",
    "nypost.com": "right",
    "washingtontimes.com": "right",
    "townhall.com": "right",
}


def get_source_leaning(domain: str) -> str:
    """Get political leaning of a source."""
    return SOURCE_LEANINGS.get(domain, "unknown")


def get_stories_with_multiple_sources(
    storage: Storage,
    min_sources: int = 2,
    limit: int = 10,
) -> list[Story]:
    """Find stories covered by multiple different sources.

    Args:
        storage: Storage instance
        min_sources: Minimum number of unique sources
        limit: Maximum stories to return

    Returns:
        Stories with multi-source coverage, sorted by source count
    """
    stories = storage.get_active_stories(limit=200)
    multi_source_stories = []

    for story in stories:
        if not story.article_ids:
            continue

        # Get unique sources for this story
        articles = storage.get_articles_by_ids(story.article_ids)
        unique_domains = set()

        for article in articles:
            domain = extract_domain(article.feed_url)
            unique_domains.add(domain)

        if len(unique_domains) >= min_sources:
            # Store source count for sorting
            story._source_count = len(unique_domains)
            multi_source_stories.append(story)

    # Sort by number of sources (most first)
    multi_source_stories.sort(key=lambda s: getattr(s, '_source_count', 0), reverse=True)

    return multi_source_stories[:limit]


def compare_story_coverage(
    story: Story,
    storage: Storage,
    kb: KnowledgeBase,
    provider=None,
) -> CrossSourceComparison:
    """Compare how different sources cover a story.

    Args:
        story: Story to analyze
        storage: Storage instance
        kb: Knowledge base
        provider: Optional LLM provider for deeper analysis

    Returns:
        CrossSourceComparison with detailed analysis
    """
    articles = storage.get_articles_by_ids(story.article_ids)

    # Group articles by source
    by_source: dict[str, list[Article]] = {}
    for article in articles:
        domain = extract_domain(article.feed_url)
        if domain not in by_source:
            by_source[domain] = []
        by_source[domain].append(article)

    # Build perspectives
    perspectives = []
    all_claims = []  # Collect all claims for comparison

    for domain, source_articles in by_source.items():
        # Use most recent article from this source
        source_articles.sort(key=lambda a: a.published or datetime.min, reverse=True)
        article = source_articles[0]

        # Extract claims from this article's triples
        article_triples = kb.get_triples_by_article(article.id, limit=10)
        claims = [f"{t.subject} {t.predicate} {t.object}" for t in article_triples]
        all_claims.extend([(domain, claim) for claim in claims])

        # Determine framing from signal tags
        framing = "neutral"
        if article.signal_tags:
            tags_lower = article.signal_tags.lower()
            if "alarmist" in tags_lower or "sensational" in tags_lower:
                framing = "alarmist"
            elif "optimistic" in tags_lower or "positive" in tags_lower:
                framing = "positive"
            elif "critical" in tags_lower or "negative" in tags_lower:
                framing = "negative"

        # Extract emphasis from trend tags
        emphasis = []
        if article.trend_tags:
            emphasis = [t.strip() for t in article.trend_tags.split(",")][:3]

        perspective = SourcePerspective(
            source_name=get_source_name(domain),
            source_domain=domain,
            article=article,
            key_claims=claims,
            framing=framing,
            emphasis=emphasis,
        )
        perspectives.append(perspective)

    # Find common facts (mentioned by 2+ sources)
    claim_counts: dict[str, int] = {}
    for domain, claim in all_claims:
        claim_lower = claim.lower()
        claim_counts[claim_lower] = claim_counts.get(claim_lower, 0) + 1

    common_facts = [claim for claim, count in claim_counts.items() if count >= 2]

    # Find coverage gaps (mentioned by some but not all)
    all_domains = set(by_source.keys())
    claims_by_source: dict[str, set] = {d: set() for d in all_domains}
    for domain, claim in all_claims:
        claims_by_source[domain].add(claim.lower())

    coverage_gaps = []
    for claim, count in claim_counts.items():
        if 0 < count < len(all_domains):
            coverage_gaps.append(claim)

    # Build bias indicators
    bias_indicators = {}
    for perspective in perspectives:
        leaning = get_source_leaning(perspective.source_domain)
        if leaning != "unknown":
            bias_indicators[perspective.source_name] = leaning

    return CrossSourceComparison(
        story=story,
        sources=perspectives,
        common_facts=common_facts[:10],
        divergent_claims=[],  # Would need LLM for deep divergence analysis
        coverage_gap=coverage_gaps[:10],
        bias_indicators=bias_indicators,
    )


def format_comparison(comparison: CrossSourceComparison) -> str:
    """Format a comparison for display."""
    lines = []

    lines.append(f"Story: {comparison.story.title}")
    lines.append(f"Sources: {len(comparison.sources)}")
    lines.append("")

    # Show each source's perspective
    for perspective in comparison.sources:
        leaning = comparison.bias_indicators.get(perspective.source_name, "")
        leaning_str = f" [{leaning}]" if leaning else ""

        lines.append(f"  {perspective.source_name}{leaning_str}")
        lines.append(f"    Framing: {perspective.framing}")
        if perspective.emphasis:
            lines.append(f"    Emphasis: {', '.join(perspective.emphasis)}")
        if perspective.key_claims:
            lines.append(f"    Key claims:")
            for claim in perspective.key_claims[:3]:
                lines.append(f"      - {claim}")
        lines.append("")

    # Show common ground
    if comparison.common_facts:
        lines.append("  Common facts (mentioned by multiple sources):")
        for fact in comparison.common_facts[:5]:
            lines.append(f"    - {fact}")
        lines.append("")

    # Show coverage gaps
    if comparison.coverage_gap:
        lines.append("  Coverage gaps (mentioned by some, not all):")
        for gap in comparison.coverage_gap[:5]:
            lines.append(f"    - {gap}")

    return "\n".join(lines)


# =============================================================================
# DIVERSE SOURCE SUGGESTIONS
# =============================================================================

# Pre-curated diverse RSS feeds across the political spectrum
DIVERSE_FEEDS = {
    "left": [
        ("https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "New York Times", "left-center"),
        ("https://feeds.washingtonpost.com/rss/politics", "Washington Post", "left-center"),
        ("http://rss.cnn.com/rss/cnn_topstories.rss", "CNN", "left"),
        ("https://www.huffpost.com/section/front-page/feed", "HuffPost", "left"),
        ("https://www.vox.com/rss/index.xml", "Vox", "left"),
    ],
    "center": [
        ("https://feeds.reuters.com/reuters/topNews", "Reuters", "center"),
        ("https://feeds.bbci.co.uk/news/rss.xml", "BBC News", "center"),
        ("https://apnews.com/apf-topnews/feed", "Associated Press", "center"),
        ("https://thehill.com/feed/", "The Hill", "center"),
        ("https://www.politico.com/rss/politicopicks.xml", "Politico", "center"),
    ],
    "right": [
        ("https://feeds.feedburner.com/foxnews/latest", "Fox News", "right"),
        ("https://www.wsj.com/xml/rss/3_7085.xml", "Wall Street Journal", "center-right"),
        ("https://www.nationalreview.com/feed/", "National Review", "right"),
        ("https://www.dailywire.com/feeds/rss.xml", "Daily Wire", "right"),
        ("https://nypost.com/feed/", "New York Post", "right"),
    ],
}


def get_current_feed_leanings(feeds_file: str = "config/feeds.txt") -> dict[str, list[str]]:
    """Analyze political leaning distribution of current feeds.

    Returns dict with 'left', 'center', 'right', 'unknown' lists.
    """
    from .rss import load_feeds

    feeds = load_feeds(feeds_file)
    distribution = {"left": [], "center": [], "right": [], "unknown": []}

    for feed_url in feeds:
        domain = extract_domain(feed_url)
        leaning = get_source_leaning(domain)

        if leaning in ("far-left", "left", "left-center", "center-left"):
            distribution["left"].append(domain)
        elif leaning in ("center",):
            distribution["center"].append(domain)
        elif leaning in ("center-right", "right", "far-right"):
            distribution["right"].append(domain)
        else:
            distribution["unknown"].append(domain)

    return distribution


def suggest_diverse_sources(
    feeds_file: str = "config/feeds.txt",
    limit_per_category: int = 3,
) -> dict[str, list[tuple[str, str, str]]]:
    """Suggest sources to balance the user's feed mix.

    Returns dict with suggested feeds by category.
    """
    current = get_current_feed_leanings(feeds_file)

    # Count current distribution
    left_count = len(current["left"])
    center_count = len(current["center"])
    right_count = len(current["right"])

    suggestions = {"left": [], "center": [], "right": []}

    # Suggest underrepresented categories
    if left_count < right_count:
        suggestions["left"] = DIVERSE_FEEDS["left"][:limit_per_category]
    if right_count < left_count:
        suggestions["right"] = DIVERSE_FEEDS["right"][:limit_per_category]
    if center_count < max(left_count, right_count):
        suggestions["center"] = DIVERSE_FEEDS["center"][:limit_per_category]

    # If no imbalance, suggest one from each
    if not any(suggestions.values()):
        suggestions["left"] = DIVERSE_FEEDS["left"][:1]
        suggestions["center"] = DIVERSE_FEEDS["center"][:1]
        suggestions["right"] = DIVERSE_FEEDS["right"][:1]

    return suggestions
