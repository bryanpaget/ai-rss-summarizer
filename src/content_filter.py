"""Content filtering for promotional/spam detection.

Detects advertisements, promotional content, and spam based on:
- Title patterns (promo codes, discounts, deals)
- Content patterns (promotional language)
- Source patterns (known affiliate/coupon domains)

Flagged content goes to spam box and is deleted after 30 days.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .storage import Article, Storage


@dataclass
class FilterResult:
    """Result of content filtering."""
    is_promotional: bool
    confidence: float  # 0.0 to 1.0
    reason: str
    matched_patterns: list[str]


# Title patterns that strongly indicate promotional content
TITLE_PATTERNS = [
    # Discount patterns
    (r'\b\d{1,2}%\s*off\b', 0.9, 'percentage discount'),
    (r'\bpromo\s*code', 0.95, 'promo code'),
    (r'\bcoupon', 0.9, 'coupon'),
    (r'\bdiscount\s*code', 0.95, 'discount code'),
    (r'\bvoucher', 0.85, 'voucher'),

    # Sale patterns
    (r'\bsale\b.*\boff\b', 0.7, 'sale'),
    (r'\bclearance', 0.8, 'clearance'),
    (r'\bflash\s*sale', 0.85, 'flash sale'),
    (r'\bdeal\s*of\s*the\s*day', 0.9, 'deal of the day'),
    (r'\blimited\s*time\s*offer', 0.85, 'limited time offer'),

    # Free stuff patterns
    (r'\bfree\s*shipping', 0.7, 'free shipping'),
    (r'\bbuy\s*one\s*get\s*one', 0.85, 'BOGO'),
    (r'\bbonus\s*offer', 0.8, 'bonus offer'),

    # Affiliate patterns
    (r'\baffiliate', 0.9, 'affiliate'),
    (r'\bsponsored\s*(?:post|content|article)', 0.95, 'sponsored content'),

    # Price patterns (e.g., "Starting at $19.99", "Save $50")
    # Note: Can't use \b before $ since both space and $ are non-word characters
    (r'\bstarting\s*at\s*\$\d+', 0.7, 'price promotion'),
    (r'\bas\s*low\s*as\s*\$\d+', 0.75, 'price promotion'),
    (r'\bonly\s*\$\d+', 0.6, 'price promotion'),
    (r'\bsave\s*\$\d+', 0.85, 'dollar savings'),
    (r'(?:^|\s)\$\d+\s*off\b', 0.85, 'dollar discount'),
    (r'\bget\s*\$\d+\s*off', 0.9, 'dollar off promotion'),
    (r'\bextra\s*\$\d+\s*off', 0.9, 'extra dollar off'),
    (r'\bwith\s*(?:this\s*)?code\b', 0.85, 'promo code reference'),

    # Urgency patterns
    (r'\bact\s*now', 0.7, 'urgency'),
    (r'\bhurry', 0.6, 'urgency'),
    (r'\bexpires?\s*(?:soon|today)', 0.8, 'expiration urgency'),

    # Product roundup/review patterns (often affiliate/ad content)
    (r'\bbest\s+\d*\s*(?:of\s+\d+\s*)?(?:baby|kid|pet|home|kitchen|outdoor|tech|gadget)', 0.85, 'product roundup'),
    (r'\btop\s+\d+\s+(?:best\s+)?(?:products?|picks?|choices?|options?)', 0.8, 'product list'),
    (r'\bbest\s+(?:gear|products?|items?|picks?|buys?)\s+(?:for|of|in)', 0.8, 'product roundup'),
    (r'\b(?:buyer|buying|gift)\s*(?:\'s)?\s*guide', 0.85, 'buying guide'),
    (r'\bproduct\s*review', 0.6, 'product review'),
    (r'\b(?:stroller|crib|bassinet|car\s*seat|baby\s*monitor|high\s*chair)s?\s*(?:review|guide|best)', 0.9, 'baby product ad'),
    (r'\b(?:mattress|furniture|appliance)s?\s*(?:review|guide|best)', 0.8, 'home product ad'),
    (r'\bwe\s*(?:tested|reviewed|tried)\s*\d+\s+(?:products?|items?)', 0.75, 'product testing'),
    (r'\b(?:editor|expert|staff)(?:\'s)?\s*(?:pick|choice|favorite)', 0.7, 'editorial pick'),
]

# Known promotional/affiliate domain patterns
PROMOTIONAL_DOMAINS = [
    r'retailmenot\.com',
    r'groupon\.com',
    r'slickdeals\.net',
    r'coupons\.com',
    r'offers\.com',
    r'dealnews\.com',
    r'bradsdeal\.com',
    r'savings\.com',
    r'promocode',
    r'couponcode',
    r'dealscove',
    r'goodshop',
    r'rakuten',
    r'honey\.com',
]

# Content patterns that indicate promotional material
CONTENT_PATTERNS = [
    (r'\buse\s*(?:code|coupon)\s*[A-Z0-9]+', 0.9, 'coupon code usage'),
    (r'\benter\s*(?:code|coupon)\s*at\s*checkout', 0.9, 'checkout code'),
    (r'\bshop\s*now', 0.5, 'call to action'),
    (r'\bbuy\s*now', 0.5, 'call to action'),
    (r'\bclick\s*here\s*to\s*(?:save|get)', 0.7, 'click bait'),
    (r'\bexclusive\s*(?:offer|deal|discount)', 0.75, 'exclusive offer'),
    (r'\bsave\s*(?:up\s*to\s*)?\d+%', 0.8, 'save percentage'),
    (r'\b(?:terms|conditions)\s*(?:apply|may\s*vary)', 0.6, 'terms disclaimer'),
]


def is_promotional_content(article: Article, threshold: float = 0.7) -> FilterResult:
    """Check if an article is promotional/advertising content.

    Args:
        article: Article to check
        threshold: Confidence threshold (0.0-1.0) to classify as promotional

    Returns:
        FilterResult with detection details
    """
    matched_patterns = []
    max_confidence = 0.0
    reasons = []

    title_lower = article.title.lower()
    content_lower = (article.content or "").lower()
    link_lower = article.link.lower()

    # Check title patterns
    for pattern, confidence, reason in TITLE_PATTERNS:
        if re.search(pattern, title_lower, re.IGNORECASE):
            matched_patterns.append(f"title:{reason}")
            if confidence > max_confidence:
                max_confidence = confidence
                reasons = [f"Title contains '{reason}'"]
            elif confidence == max_confidence:
                reasons.append(f"Title contains '{reason}'")

    # Check for promotional domains
    for domain_pattern in PROMOTIONAL_DOMAINS:
        if re.search(domain_pattern, link_lower, re.IGNORECASE):
            matched_patterns.append(f"domain:{domain_pattern}")
            if 0.95 > max_confidence:
                max_confidence = 0.95
                reasons = [f"From promotional domain"]
            break

    # Check content patterns (only if we haven't hit threshold yet)
    if max_confidence < threshold:
        for pattern, confidence, reason in CONTENT_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                matched_patterns.append(f"content:{reason}")
                # Content patterns add incrementally
                max_confidence = min(1.0, max_confidence + confidence * 0.3)
                reasons.append(f"Content contains '{reason}'")

    # Multiple pattern matches increase confidence
    if len(matched_patterns) >= 3:
        max_confidence = min(1.0, max_confidence + 0.1)
    if len(matched_patterns) >= 5:
        max_confidence = min(1.0, max_confidence + 0.1)

    is_promo = max_confidence >= threshold
    reason_str = "; ".join(reasons[:3]) if reasons else "No promotional patterns detected"

    return FilterResult(
        is_promotional=is_promo,
        confidence=max_confidence,
        reason=reason_str,
        matched_patterns=matched_patterns,
    )


def add_spam_support(storage: Storage) -> None:
    """Legacy function - spam columns are now added by Storage schema migrations.

    Kept for backwards compatibility but does nothing as schema is managed centrally.
    """
    pass  # Schema is now managed by Storage._migrate_to_v1()


def flag_as_spam(storage: Storage, article_id: str, reason: str) -> bool:
    """Flag an article as spam.

    Args:
        storage: Storage instance
        article_id: ID of article to flag
        reason: Why it was flagged

    Returns:
        True if flagged successfully
    """
    add_spam_support(storage)
    with storage._connect() as conn:
        cursor = conn.execute("""
            UPDATE articles
            SET spam_status = 'spam',
                spam_reason = ?,
                spam_flagged_at = ?
            WHERE id = ?
        """, (reason, datetime.now().isoformat(), article_id))
        changed = cursor.rowcount > 0
        conn.commit()
        return changed


def get_spam_articles(storage: Storage, limit: int = 100) -> list[Article]:
    """Get articles flagged as spam.

    Args:
        storage: Storage instance
        limit: Maximum articles to return

    Returns:
        List of spam articles
    """
    add_spam_support(storage)
    with storage._connect() as conn:
        rows = conn.execute("""
            SELECT id, feed_url, title, link, published, content,
                   summary, trend_tags, signal_tags, story_id, created_at
            FROM articles
            WHERE spam_status = 'spam'
            ORDER BY spam_flagged_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            Article(
                id=row[0],
                feed_url=row[1],
                title=row[2],
                link=row[3],
                published=row[4],
                content=row[5],
                summary=row[6],
                trend_tags=row[7],
                signal_tags=row[8],
                story_id=row[9],
                created_at=row[10],
            )
            for row in rows
        ]


def cleanup_old_spam(storage: Storage, days: int = 30) -> int:
    """Delete spam articles older than specified days.

    Args:
        storage: Storage instance
        days: Delete spam older than this many days

    Returns:
        Number of articles deleted
    """
    add_spam_support(storage)
    cutoff = datetime.now() - timedelta(days=days)

    with storage._connect() as conn:
        cursor = conn.execute("""
            DELETE FROM articles
            WHERE spam_status = 'spam'
            AND spam_flagged_at < ?
        """, (cutoff.isoformat(),))
        deleted = cursor.rowcount
        conn.commit()
        return deleted


def filter_articles(
    articles: list[Article],
    storage: Storage,
    threshold: float = 0.7,
) -> tuple[list[Article], list[Article]]:
    """Filter articles, separating promotional content into spam.

    Args:
        articles: List of articles to filter
        storage: Storage instance for flagging spam
        threshold: Confidence threshold for spam detection

    Returns:
        Tuple of (clean_articles, spam_articles)
    """
    add_spam_support(storage)

    clean = []
    spam = []

    for article in articles:
        result = is_promotional_content(article, threshold)

        if result.is_promotional:
            flag_as_spam(storage, article.id, result.reason)
            spam.append(article)
        else:
            clean.append(article)

    return clean, spam
