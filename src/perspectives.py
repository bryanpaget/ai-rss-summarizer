"""Perspective synthesis for multi-source story analysis."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .storage import Storage, Article
from .constitution import get_constitution_context


# Perspective category definitions
PERSPECTIVE_CATEGORIES = {
    # Factual perspectives
    'consensus': {
        'name': 'Consensus',
        'description': 'What all sources agree on',
        'min_sources': 2,
    },
    'contested': {
        'name': 'Contested',
        'description': 'Where sources disagree',
        'min_sources': 2,
    },
    'gaps': {
        'name': 'Gaps',
        'description': 'What no one is covering',
        'min_sources': 1,
    },
    'timeline': {
        'name': 'Timeline',
        'description': 'Chronological fact sequence',
        'min_sources': 1,
    },
    # Source framing perspectives
    'tech-industry': {
        'name': 'Tech Industry',
        'description': 'How tech press frames it',
        'min_sources': 1,
    },
    'mainstream': {
        'name': 'Mainstream',
        'description': 'General news framing',
        'min_sources': 1,
    },
    'financial': {
        'name': 'Financial',
        'description': 'Business/market angle',
        'min_sources': 1,
    },
    'political': {
        'name': 'Political',
        'description': 'Policy/government angle',
        'min_sources': 1,
    },
    'academic': {
        'name': 'Academic',
        'description': 'Research perspective',
        'min_sources': 1,
    },
    # Fun/entertainment perspectives
    'spiciest-takes': {
        'name': 'Spiciest Takes',
        'description': 'Most provocative opinions',
        'min_sources': 1,
    },
    'unhinged-speculation': {
        'name': 'Unhinged Speculation',
        'description': 'Wildest predictions',
        'min_sources': 1,
    },
    'contrarian': {
        'name': 'Contrarian',
        'description': 'Against-the-grain views',
        'min_sources': 1,
    },
    'doom': {
        'name': 'Doom',
        'description': 'Pessimistic takes',
        'min_sources': 1,
    },
    'hype': {
        'name': 'Hype',
        'description': 'Most optimistic takes',
        'min_sources': 1,
    },
    # Analysis perspectives
    'expert-quotes': {
        'name': 'Expert Quotes',
        'description': 'What experts say',
        'min_sources': 1,
    },
    'prediction-track-record': {
        'name': 'Prediction Track Record',
        'description': 'How past predictions held up',
        'min_sources': 2,
    },
}

# Default categories to show
DEFAULT_CATEGORIES = ['consensus', 'contested', 'gaps']


@dataclass
class Perspective:
    """A synthesized perspective on a story."""
    category: str
    content: str
    source_articles: list[str]
    confidence: float
    generated_at: datetime


class PerspectiveError(Exception):
    """Base exception for perspective synthesis errors."""
    pass


class InsufficientSourcesError(PerspectiveError):
    """Not enough articles to generate perspective."""
    pass


class CategoryNotApplicableError(PerspectiveError):
    """Requested category doesn't apply to this story."""
    pass


class LLMProviderError(PerspectiveError):
    """LLM provider failed to generate perspective."""
    pass


def build_perspective_prompt(category: str, articles: list[Article]) -> str:
    """
    Build an LLM prompt for generating a specific perspective.

    Args:
        category: Perspective category
        articles: List of articles in the story cluster

    Returns:
        Prompt string for LLM
    """
    # Extract article information
    article_texts = []
    for i, article in enumerate(articles, 1):
        source = article.feed_url.split('/')[2] if '/' in article.feed_url else article.feed_url
        text = f"[Article {i} - {source}]\n"
        text += f"Title: {article.title}\n"
        text += f"Content: {article.content or ''}\n"
        article_texts.append(text)

    articles_section = "\n\n".join(article_texts)

    # Category-specific prompts
    prompts = {
        'consensus': f"""Given these articles about the same story, identify what facts ALL sources agree on.

{articles_section}

List only points where there is unanimous agreement across all articles. Be specific and cite evidence.
Format as a bullet list. If there are very few consensus points, that's okay - accuracy matters more than quantity.""",

        'contested': f"""Given these articles about the same story, identify specific claims or interpretations where the sources DISAGREE.

{articles_section}

For each disagreement, clearly state:
1. What is being contested
2. Which sources say what
3. The nature of the disagreement

Format as a bullet list. Focus on substantive disagreements, not minor details.""",

        'gaps': f"""Given these articles about the same story, identify what important aspects are NOT being covered by any source.

{articles_section}

Think about:
- What key questions remain unanswered?
- What perspectives are missing?
- What context or background is not provided?

Format as a bullet list.""",

        'timeline': f"""Given these articles about the same story, construct a chronological timeline of events.

{articles_section}

Include only factual events with timestamps, not opinions or speculation.
Format as a timeline with dates/times where available.
If exact timing is unclear, note that.""",

        'spiciest-takes': f"""Given these articles about the same story, extract the most PROVOCATIVE, bold, or inflammatory opinions.

{articles_section}

Find quotes or claims that are:
- Controversial
- Strongly opinionated
- Attention-grabbing
- Potentially polarizing

Quote directly and cite which article. The spicier, the better!""",

        'tech-industry': f"""Given these articles about the same story, analyze how it's being framed from a TECH INDUSTRY perspective.

{articles_section}

Focus on:
- Technical implications
- Impact on tech companies/products
- Developer/engineer concerns
- Innovation and technical progress angles

What unique concerns does the tech industry perspective emphasize?""",

        'mainstream': f"""Given these articles about the same story, analyze how it's being framed from a MAINSTREAM MEDIA perspective.

{articles_section}

Focus on:
- Human interest angles
- Broad societal impact
- Accessibility to general audience
- Established authority sources

How is this packaged for general public consumption?""",

        'financial': f"""Given these articles about the same story, analyze how it's being framed from a FINANCIAL/BUSINESS perspective.

{articles_section}

Focus on:
- Market implications
- Financial performance impact
- Investor concerns
- Economic consequences
- Stock/valuation effects

What business/financial angles are emphasized?""",

        'political': f"""Given these articles about the same story, analyze how it's being framed from a POLITICAL/POLICY perspective.

{articles_section}

Focus on:
- Regulatory implications
- Government policy
- Political positions
- Governance concerns
- Legal/legislative aspects

What political angles are emphasized?""",

        'academic': f"""Given these articles about the same story, analyze how it's being framed from an ACADEMIC/RESEARCH perspective.

{articles_section}

Focus on:
- Research findings
- Scholarly analysis
- Methodological concerns
- Long-term implications
- Evidence-based reasoning

What scholarly perspectives are present?""",

        'expert-quotes': f"""Given these articles about the same story, extract all quotes from DOMAIN EXPERTS.

{articles_section}

For each quote:
1. The exact quote
2. Who said it (name and credentials)
3. Which article it's from

Only include people with relevant expertise or authority on this topic.""",

        'contrarian': f"""Given these articles about the same story, find views that go AGAINST the prevailing narrative.

{articles_section}

Look for:
- Skeptical voices
- Alternative interpretations
- Pushback against consensus
- Devil's advocate positions

What contrarian views are present?""",

        'unhinged-speculation': f"""Given these articles about the same story, find the WILDEST predictions and speculation.

{articles_section}

Look for:
- Far-fetched theories
- Dramatic predictions
- Speculative leaps
- Conspiracy-adjacent thinking

The more unhinged, the better! This is for entertainment.""",

        'doom': f"""Given these articles about the same story, find the most PESSIMISTIC takes.

{articles_section}

Look for:
- Worst-case scenarios
- Negative predictions
- Concerns and warnings
- Doom-and-gloom perspectives

What are people worried about?""",

        'hype': f"""Given these articles about the same story, find the most OPTIMISTIC and hyped-up takes.

{articles_section}

Look for:
- Best-case scenarios
- Enthusiastic predictions
- Revolutionary claims
- Excitement and hype

What are people most excited about?""",

        'prediction-track-record': f"""Given these articles about the same story, identify any PAST PREDICTIONS and how they held up.

{articles_section}

Look for:
- References to previous predictions
- Comparisons to past forecasts
- Track record of experts/sources
- What was predicted vs what happened

This requires the articles to reference past predictions.""",
    }

    # Get user's analysis principles if configured
    constitution_context = get_constitution_context()

    prompt = prompts.get(category, f"Analyze these articles from a {category} perspective:\n\n{articles_section}")

    # Prepend constitution context if available
    if constitution_context:
        return constitution_context + prompt
    return prompt


def estimate_confidence(
    category: str,
    synthesis: str,
    articles: list[Article],
) -> float:
    """
    Estimate confidence in a synthesized perspective.

    Factors:
    - Number of source articles (more is better)
    - Article recency
    - Synthesis quality (length, structure)
    - Category-specific requirements

    Returns:
        Confidence score 0-1
    """
    score = 0.0

    # Base score from article count
    article_count = len(articles)
    category_info = PERSPECTIVE_CATEGORIES.get(category, {})
    min_sources = category_info.get('min_sources', 1)

    if article_count >= min_sources * 2:
        score += 0.4
    elif article_count >= min_sources:
        score += 0.3
    else:
        score += 0.1

    # Recency bonus
    now = datetime.now()
    recent_count = 0
    for article in articles:
        if article.published:
            try:
                if isinstance(article.published, str):
                    pub_str = article.published.replace("Z", "+00:00")
                    pub_time = datetime.fromisoformat(pub_str)
                    pub_time = pub_time.replace(tzinfo=None)
                else:
                    pub_time = article.published

                if now - pub_time < timedelta(hours=24):
                    recent_count += 1
            except (ValueError, TypeError) as e:
                import sys
                print(f"Date parsing failed for perspective confidence: {e}", file=sys.stderr)

    if recent_count >= len(articles) * 0.7:
        score += 0.2
    elif recent_count >= len(articles) * 0.4:
        score += 0.1

    # Synthesis quality
    if synthesis:
        # Check length (not too short)
        if len(synthesis) > 100:
            score += 0.2
        elif len(synthesis) > 50:
            score += 0.1

        # Check structure (has multiple points)
        if '\n' in synthesis or '•' in synthesis or '-' in synthesis:
            score += 0.1

        # Check if synthesis indicates uncertainty
        uncertainty_markers = ['unclear', 'unknown', 'no information', 'not mentioned', 'insufficient']
        if any(marker in synthesis.lower() for marker in uncertainty_markers):
            score -= 0.1

    return max(0.0, min(score, 1.0))


def generate_fallback_perspective(
    category: str,
    articles: list[Article],
) -> Perspective:
    """
    Generate a simple fallback perspective without LLM.

    Uses basic text extraction and aggregation.
    """
    if len(articles) == 0:
        return Perspective(
            category=category,
            content=f"No articles available for {category} perspective.",
            source_articles=[],
            confidence=0.0,
            generated_at=datetime.now(),
        )

    if len(articles) == 1:
        content = f"Limited perspective (only 1 source):\n\n{articles[0].title}"
        if articles[0].summary:
            content += f"\n\n{articles[0].summary}"
    else:
        content = f"Sources ({len(articles)} articles):\n\n"
        for i, article in enumerate(articles[:5], 1):
            content += f"{i}. {article.title}\n"

    return Perspective(
        category=category,
        content=content,
        source_articles=[a.id for a in articles],
        confidence=0.2,
        generated_at=datetime.now(),
    )


def synthesize_perspective(
    category: str,
    articles: list[Article],
    llm_provider=None,
    storage=None,
    cluster_id: Optional[str] = None,
) -> Perspective:
    """
    Generate a single perspective for a story cluster.

    Args:
        category: Perspective category to generate
        articles: Articles in the story cluster
        llm_provider: LLM provider for synthesis (optional)
        storage: Storage instance for caching (optional)
        cluster_id: Story cluster ID for caching (optional)

    Returns:
        Perspective object

    Raises:
        InsufficientSourcesError: Not enough articles
        CategoryNotApplicableError: Category doesn't apply
        LLMProviderError: LLM failed
    """
    # Check if category exists
    if category not in PERSPECTIVE_CATEGORIES:
        raise CategoryNotApplicableError(f"Unknown category: {category}")

    category_info = PERSPECTIVE_CATEGORIES[category]
    min_sources = category_info.get('min_sources', 1)

    # Check cache first
    if storage and cluster_id:
        cached = storage.get_cached_perspective(cluster_id, category)
        if cached and is_cache_fresh(cached):
            return cached

    # Check minimum sources
    if len(articles) < min_sources:
        raise InsufficientSourcesError(
            f"Category '{category}' requires at least {min_sources} sources, got {len(articles)}"
        )

    # Try LLM synthesis
    if llm_provider:
        try:
            prompt = build_perspective_prompt(category, articles)

            # Use provider's summarize method (reuse existing interface)
            synthesis = llm_provider.summarize(prompt, max_length=1000)

            if not synthesis or len(synthesis.strip()) < 10:
                raise LLMProviderError("LLM returned empty or very short response")

            perspective = Perspective(
                category=category,
                content=synthesis,
                source_articles=[a.id for a in articles],
                confidence=estimate_confidence(category, synthesis, articles),
                generated_at=datetime.now(),
            )

            # Cache the result
            if storage and cluster_id:
                storage.cache_perspective(cluster_id, category, perspective)

            return perspective

        except Exception as e:
            raise LLMProviderError(f"LLM synthesis failed: {str(e)}")

    # Fallback without LLM
    perspective = generate_fallback_perspective(category, articles)

    # Cache even fallback
    if storage and cluster_id:
        storage.cache_perspective(cluster_id, category, perspective)

    return perspective


def synthesize_perspectives(
    cluster_id: str,
    categories: list[str],
    storage: Storage,
    llm_provider=None,
) -> dict[str, Perspective]:
    """
    Generate multiple perspectives for a story cluster.

    Uses submit/collect pattern for batched LLM calls when gateway is available.

    Args:
        cluster_id: Story cluster ID
        categories: List of perspective categories to generate
        storage: Storage instance
        llm_provider: LLM provider (optional)

    Returns:
        Dictionary mapping category to Perspective
    """
    articles = storage.get_articles_by_cluster(cluster_id)

    if not articles:
        return {}

    perspectives = {}

    # Try to use gateway for batched processing
    try:
        from safe_loading_gateway import get_gateway, GatewayUnavailableError
        gateway = get_gateway()
        use_gateway = gateway.is_available()
    except (ImportError, GatewayUnavailableError):
        use_gateway = False

    if use_gateway and llm_provider:
        # --- BATCHED PATH: Submit all, then collect all ---

        # Step 1: Build prompts and check eligibility
        eligible_categories = []
        for category in categories:
            if category not in PERSPECTIVE_CATEGORIES:
                continue

            category_info = PERSPECTIVE_CATEGORIES[category]
            min_sources = category_info.get('min_sources', 1)

            # Check cache first
            cached = storage.get_cached_perspective(cluster_id, category)
            if cached and is_cache_fresh(cached):
                perspectives[category] = cached
                continue

            # Check minimum sources
            if len(articles) < min_sources:
                perspectives[category] = Perspective(
                    category=category,
                    content=f"Insufficient sources for {category} perspective (need {min_sources}, have {len(articles)})",
                    source_articles=[a.id for a in articles],
                    confidence=0.1,
                    generated_at=datetime.now(),
                )
                continue

            eligible_categories.append(category)

        # Step 2: Submit all prompts
        handles = []
        for category in eligible_categories:
            prompt = build_perspective_prompt(category, articles)
            handle = gateway.submit_text(prompt, temperature=0.3)
            handles.append((category, handle))

        # Step 3: Collect all responses
        for category, handle in handles:
            try:
                synthesis = gateway.collect_text(handle)

                if not synthesis or len(synthesis.strip()) < 10:
                    perspectives[category] = generate_fallback_perspective(category, articles)
                    continue

                perspective = Perspective(
                    category=category,
                    content=synthesis,
                    source_articles=[a.id for a in articles],
                    confidence=estimate_confidence(category, synthesis, articles),
                    generated_at=datetime.now(),
                )

                # Cache the result
                storage.cache_perspective(cluster_id, category, perspective)
                perspectives[category] = perspective

            except Exception:
                perspectives[category] = generate_fallback_perspective(category, articles)

    else:
        # --- SEQUENTIAL PATH: Original behavior for non-gateway providers ---
        for category in categories:
            try:
                perspective = synthesize_perspective(
                    category=category,
                    articles=articles,
                    llm_provider=llm_provider,
                    storage=storage,
                    cluster_id=cluster_id,
                )
                perspectives[category] = perspective

            except InsufficientSourcesError:
                perspectives[category] = Perspective(
                    category=category,
                    content=f"Insufficient sources for {category} perspective (need {PERSPECTIVE_CATEGORIES[category]['min_sources']}, have {len(articles)})",
                    source_articles=[a.id for a in articles],
                    confidence=0.1,
                    generated_at=datetime.now(),
                )

            except CategoryNotApplicableError:
                continue

            except LLMProviderError:
                perspectives[category] = generate_fallback_perspective(category, articles)

    return perspectives


def is_cache_fresh(perspective: Perspective, ttl_hours: int = 6) -> bool:
    """
    Check if a cached perspective is still fresh.

    Args:
        perspective: Cached perspective
        ttl_hours: Time-to-live in hours

    Returns:
        True if cache is fresh
    """
    if not perspective or not perspective.generated_at:
        return False

    age = datetime.now() - perspective.generated_at
    return age < timedelta(hours=ttl_hours)


def get_user_perspective_config(storage: Storage) -> dict:
    """
    Get user's perspective configuration.

    Returns:
        Dictionary with enabled_categories, default_categories, category_order
    """
    config = storage.get_perspective_config()

    if not config:
        # Return defaults
        return {
            'enabled_categories': list(PERSPECTIVE_CATEGORIES.keys()),
            'default_categories': DEFAULT_CATEGORIES,
            'category_order': list(PERSPECTIVE_CATEGORIES.keys()),
        }

    return config


def update_user_perspective_config(
    storage: Storage,
    enabled_categories: Optional[list[str]] = None,
    default_categories: Optional[list[str]] = None,
    category_order: Optional[list[str]] = None,
) -> None:
    """
    Update user's perspective configuration.

    Args:
        storage: Storage instance
        enabled_categories: Categories to enable (None = no change)
        default_categories: Default categories to show (None = no change)
        category_order: Display order (None = no change)
    """
    current = get_user_perspective_config(storage)

    if enabled_categories is not None:
        current['enabled_categories'] = enabled_categories

    if default_categories is not None:
        current['default_categories'] = default_categories

    if category_order is not None:
        current['category_order'] = category_order

    storage.save_perspective_config(current)
