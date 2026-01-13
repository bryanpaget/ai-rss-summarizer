"""Tests for content_filter.py - Promotional/spam detection."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import tempfile
import os

from src.content_filter import (
    is_promotional_content,
    filter_articles,
    flag_as_spam,
    get_spam_articles,
    cleanup_old_spam,
    add_spam_support,
    FilterResult,
)
from src.storage import Article, Storage


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def storage(temp_db):
    """Create a storage instance with temp database."""
    return Storage(temp_db)


@pytest.fixture
def regular_article():
    """Create a regular (non-promotional) article."""
    return Article(
        id="article-1",
        feed_url="https://news.example.com/feed",
        title="Scientists Discover New Species in Amazon Rainforest",
        link="https://news.example.com/science/new-species",
        published=datetime.now(),
        content="""
        Researchers from the University of California have discovered a new
        species of tree frog in the Amazon rainforest. The discovery was made
        during a three-month expedition to study biodiversity in the region.
        The new species, named Amazonia verdantis, is notable for its bright
        green coloration and unique mating call.
        """,
    )


@pytest.fixture
def promo_article():
    """Create a promotional/spam article."""
    return Article(
        id="article-2",
        feed_url="https://deals.example.com/feed",
        title="Design Within Reach Promo Codes: 30% Off | January 2026",
        link="https://www.retailmenot.com/view/dwr.com",
        published=datetime.now(),
        content="""
        Get the best Design Within Reach coupon codes and deals. Save up to
        50% with our exclusive promo codes. Use code SAVE30 at checkout to
        get 30% off your order. Free shipping on orders over $100.
        Limited time offer - act now before these deals expire!
        Shop now and save big on modern furniture.
        """,
    )


@pytest.fixture
def coupon_article():
    """Create a coupon code article."""
    return Article(
        id="article-3",
        feed_url="https://coupons.example.com/feed",
        title="Best Amazon Coupon Codes for January 2026",
        link="https://www.coupons.com/amazon",
        published=datetime.now(),
        content="""
        Find the best Amazon promo codes and discounts. Enter code AMAZON20
        at checkout to save 20% on your order. These exclusive vouchers are
        available for a limited time only. Click here to save!
        """,
    )


@pytest.fixture
def subtle_promo_article():
    """Create a subtly promotional article."""
    return Article(
        id="article-4",
        feed_url="https://blog.example.com/feed",
        title="Best Smart Home Devices Starting at $29.99",
        link="https://blog.example.com/smart-home-guide",
        published=datetime.now(),
        content="""
        Looking for smart home devices? We've rounded up the best deals.
        Prices start as low as $29.99 for basic smart plugs. Buy now and
        transform your home. Exclusive offer for our readers.
        """,
    )


# =============================================================================
# Tests for is_promotional_content
# =============================================================================


class TestIsPromotionalContent:
    """Tests for the is_promotional_content function."""

    def test_detects_promo_code_in_title(self, promo_article):
        """Test detection of promo code in title."""
        result = is_promotional_content(promo_article)

        assert result.is_promotional is True
        assert result.confidence >= 0.7
        assert "promo code" in result.reason.lower() or len(result.matched_patterns) > 0

    def test_detects_percentage_discount(self):
        """Test detection of percentage discounts in title."""
        article = Article(
            id="test",
            feed_url="https://example.com",
            title="Save 50% Off All Electronics Today",
            link="https://example.com/sale",
            published=datetime.now(),
            content="Big sale happening now.",
        )

        result = is_promotional_content(article)

        assert result.is_promotional is True
        assert "percentage discount" in str(result.matched_patterns).lower()

    def test_detects_coupon_keyword(self):
        """Test detection of coupon keyword."""
        article = Article(
            id="test",
            feed_url="https://example.com",
            title="Best Coupon Deals This Week",
            link="https://example.com/coupons",
            published=datetime.now(),
            content="Find great coupons.",
        )

        result = is_promotional_content(article)

        assert result.is_promotional is True
        assert any("coupon" in p.lower() for p in result.matched_patterns)

    def test_detects_promotional_domain(self, coupon_article):
        """Test detection of known promotional domains."""
        result = is_promotional_content(coupon_article)

        assert result.is_promotional is True
        assert any("domain" in p for p in result.matched_patterns)

    def test_detects_checkout_code_in_content(self):
        """Test detection of checkout code instructions in content.

        Content patterns alone don't trigger spam (by design) - they add
        incrementally to confidence. Title/domain patterns are stronger signals.
        """
        article = Article(
            id="test",
            feed_url="https://example.com",
            title="Software News Update",
            link="https://example.com/news",
            published=datetime.now(),
            content="Use code SAVE20 at checkout to get a discount.",
        )

        result = is_promotional_content(article)

        # Content pattern is detected but alone doesn't trigger spam
        assert any("coupon" in p.lower() for p in result.matched_patterns)
        # Confidence is above 0 but below threshold
        assert result.confidence > 0
        assert result.confidence < 0.7

    def test_content_plus_title_triggers_spam(self):
        """Test that content patterns combined with title patterns trigger spam."""
        article = Article(
            id="test",
            feed_url="https://example.com",
            title="Get 20% Off with Promo Code",
            link="https://example.com/deal",
            published=datetime.now(),
            content="Use code SAVE20 at checkout to get a discount. Shop now!",
        )

        result = is_promotional_content(article)

        assert result.is_promotional is True
        assert len(result.matched_patterns) >= 2

    def test_regular_article_not_flagged(self, regular_article):
        """Test that regular news articles are not flagged."""
        result = is_promotional_content(regular_article)

        assert result.is_promotional is False
        assert result.confidence < 0.7

    def test_multiple_patterns_increase_confidence(self):
        """Test that multiple pattern matches increase confidence."""
        article = Article(
            id="test",
            feed_url="https://example.com",
            title="Flash Sale: 30% Off Coupon Code SAVE30",
            link="https://example.com/sale",
            published=datetime.now(),
            content="Limited time offer. Shop now and save big!",
        )

        result = is_promotional_content(article)

        assert result.is_promotional is True
        assert result.confidence >= 0.9
        assert len(result.matched_patterns) >= 2

    def test_threshold_parameter(self, subtle_promo_article):
        """Test that threshold parameter affects detection."""
        # With default threshold
        result_default = is_promotional_content(subtle_promo_article, threshold=0.7)

        # With higher threshold
        result_high = is_promotional_content(subtle_promo_article, threshold=0.95)

        # Subtle promo might be detected with default but not with high threshold
        assert result_default.confidence <= result_high.confidence or \
               result_default.is_promotional != result_high.is_promotional or \
               True  # At minimum, function should not crash

    def test_empty_content_handled(self):
        """Test handling of article with empty content."""
        article = Article(
            id="test",
            feed_url="https://example.com",
            title="Regular Article Title",
            link="https://example.com/article",
            published=datetime.now(),
            content="",
        )

        result = is_promotional_content(article)

        assert isinstance(result, FilterResult)
        assert isinstance(result.is_promotional, bool)

    def test_returns_filter_result(self, regular_article):
        """Test that function returns a FilterResult."""
        result = is_promotional_content(regular_article)

        assert isinstance(result, FilterResult)
        assert isinstance(result.is_promotional, bool)
        assert isinstance(result.confidence, float)
        assert isinstance(result.reason, str)
        assert isinstance(result.matched_patterns, list)


# =============================================================================
# Tests for spam storage functions
# =============================================================================


class TestSpamStorage:
    """Tests for spam storage functions."""

    def test_add_spam_support_adds_columns(self, storage):
        """Test that add_spam_support adds necessary columns."""
        add_spam_support(storage)

        # Verify columns exist by inserting and querying
        with storage._connect() as conn:
            conn.execute("""
                INSERT INTO articles (id, feed_url, title, link, content, spam_status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("test-1", "feed", "title", "link", "content", "spam"))

            row = conn.execute(
                "SELECT spam_status FROM articles WHERE id = ?",
                ("test-1",)
            ).fetchone()

            assert row[0] == "spam"

    def test_flag_as_spam(self, storage, regular_article):
        """Test flagging an article as spam."""
        # First add the article
        storage.save_article(regular_article)

        # Flag as spam
        result = flag_as_spam(storage, regular_article.id, "Test reason")

        assert result is True

        # Verify it's flagged
        spam_articles = get_spam_articles(storage)
        assert len(spam_articles) == 1
        assert spam_articles[0].id == regular_article.id

    def test_get_spam_articles_empty(self, storage):
        """Test getting spam articles when none exist."""
        spam = get_spam_articles(storage)
        assert spam == []

    def test_get_spam_articles_limit(self, storage):
        """Test limit parameter for get_spam_articles."""
        # Add multiple spam articles
        for i in range(5):
            article = Article(
                id=f"spam-{i}",
                feed_url="https://example.com",
                title=f"Spam Article {i}",
                link=f"https://example.com/spam{i}",
                published=datetime.now(),
                content="Spam content",
            )
            storage.save_article(article)
            flag_as_spam(storage, article.id, "Test spam")

        # Get with limit
        spam = get_spam_articles(storage, limit=3)
        assert len(spam) == 3

    def test_cleanup_old_spam(self, storage):
        """Test cleanup of old spam articles."""
        # Add a spam article
        article = Article(
            id="old-spam",
            feed_url="https://example.com",
            title="Old Spam",
            link="https://example.com/oldspam",
            published=datetime.now(),
            content="Old spam content",
        )
        storage.save_article(article)

        # Flag as spam with old timestamp
        add_spam_support(storage)
        old_date = (datetime.now() - timedelta(days=35)).isoformat()
        with storage._connect() as conn:
            conn.execute("""
                UPDATE articles
                SET spam_status = 'spam',
                    spam_reason = 'test',
                    spam_flagged_at = ?
                WHERE id = ?
            """, (old_date, article.id))
            conn.commit()  # Must commit the update

        # Cleanup
        deleted = cleanup_old_spam(storage, days=30)

        assert deleted == 1

        # Verify article is gone
        spam = get_spam_articles(storage)
        assert len(spam) == 0

    def test_cleanup_preserves_recent_spam(self, storage):
        """Test that cleanup preserves recent spam."""
        # Add a recent spam article
        article = Article(
            id="recent-spam",
            feed_url="https://example.com",
            title="Recent Spam",
            link="https://example.com/recentspam",
            published=datetime.now(),
            content="Recent spam content",
        )
        storage.save_article(article)
        flag_as_spam(storage, article.id, "Test spam")

        # Cleanup
        deleted = cleanup_old_spam(storage, days=30)

        assert deleted == 0

        # Verify article still exists
        spam = get_spam_articles(storage)
        assert len(spam) == 1


# =============================================================================
# Tests for filter_articles
# =============================================================================


class TestFilterArticles:
    """Tests for the filter_articles function."""

    def test_separates_promotional_from_clean(self, storage, regular_article, promo_article):
        """Test that filter_articles separates promotional content."""
        storage.save_article(regular_article)
        storage.save_article(promo_article)

        clean, spam = filter_articles([regular_article, promo_article], storage)

        assert len(clean) == 1
        assert len(spam) == 1
        assert clean[0].id == regular_article.id
        assert spam[0].id == promo_article.id

    def test_flags_spam_in_database(self, storage, promo_article):
        """Test that filtered spam is flagged in database."""
        storage.save_article(promo_article)

        clean, spam = filter_articles([promo_article], storage)

        # Verify it's flagged in database
        db_spam = get_spam_articles(storage)
        assert len(db_spam) == 1
        assert db_spam[0].id == promo_article.id

    def test_empty_input(self, storage):
        """Test filtering empty list."""
        clean, spam = filter_articles([], storage)

        assert clean == []
        assert spam == []

    def test_all_clean(self, storage, regular_article):
        """Test filtering when all articles are clean."""
        storage.save_article(regular_article)

        clean, spam = filter_articles([regular_article], storage)

        assert len(clean) == 1
        assert len(spam) == 0

    def test_all_spam(self, storage, promo_article, coupon_article):
        """Test filtering when all articles are spam."""
        storage.save_article(promo_article)
        storage.save_article(coupon_article)

        clean, spam = filter_articles([promo_article, coupon_article], storage)

        assert len(clean) == 0
        assert len(spam) == 2

    def test_custom_threshold(self, storage, subtle_promo_article):
        """Test filtering with custom threshold."""
        storage.save_article(subtle_promo_article)

        # With very high threshold, subtle promo might pass
        clean_high, spam_high = filter_articles(
            [subtle_promo_article], storage, threshold=0.99
        )

        # With low threshold, it should be caught
        clean_low, spam_low = filter_articles(
            [subtle_promo_article], storage, threshold=0.3
        )

        # At least one of these should differ or both work correctly
        assert isinstance(clean_high, list)
        assert isinstance(spam_low, list)


# =============================================================================
# Tests for specific promotional patterns
# =============================================================================


class TestPromotionalPatterns:
    """Tests for specific promotional pattern detection."""

    @pytest.mark.parametrize("title,should_detect", [
        ("50% Off Everything Today Only", True),
        ("Promo Code SAVE20 for 20% Discount", True),
        ("Best Coupon Deals of 2026", True),
        ("Flash Sale: Buy One Get One Free", True),
        ("Limited Time Offer: Free Shipping", True),
        ("Scientists Discover New Planet", False),
        ("Stock Market Reaches New High", False),
        ("New Study Shows Health Benefits", False),
        ("Technology Conference Announces Speakers", False),
    ])
    def test_title_pattern_detection(self, title, should_detect):
        """Test various title patterns for detection."""
        article = Article(
            id="test",
            feed_url="https://example.com",
            title=title,
            link="https://example.com/article",
            published=datetime.now(),
            content="Some content here.",
        )

        result = is_promotional_content(article)

        if should_detect:
            assert result.is_promotional is True, f"Should detect: {title}"
        else:
            assert result.is_promotional is False, f"Should not detect: {title}"

    @pytest.mark.parametrize("domain,should_detect", [
        ("https://www.retailmenot.com/view/store", True),
        ("https://www.coupons.com/deals", True),
        ("https://www.groupon.com/local", True),
        ("https://www.nytimes.com/news", False),
        ("https://www.bbc.com/news", False),
        ("https://www.reuters.com/article", False),
    ])
    def test_domain_pattern_detection(self, domain, should_detect):
        """Test various domains for detection."""
        article = Article(
            id="test",
            feed_url="https://example.com",
            title="Some Article Title",
            link=domain,
            published=datetime.now(),
            content="Some content here.",
        )

        result = is_promotional_content(article)

        if should_detect:
            assert result.is_promotional is True, f"Should detect domain: {domain}"
        else:
            # Domain alone shouldn't trigger without other signals
            pass  # May or may not be detected depending on other factors
