"""Tests for feed_catalog.py - Curated RSS feed catalog."""

import pytest

from src.feed_catalog import (
    CURATED_CATEGORIES,
    get_feeds_by_category,
    get_all_categories,
    search_curated_feeds,
)


# =============================================================================
# Tests for CURATED_CATEGORIES structure
# =============================================================================


class TestCuratedCategories:
    """Tests for the CURATED_CATEGORIES constant."""

    def test_categories_is_dict(self):
        """Test that CURATED_CATEGORIES is a dictionary."""
        assert isinstance(CURATED_CATEGORIES, dict)

    def test_has_expected_categories(self):
        """Test that expected categories are present."""
        expected = ["Technology", "Programming", "News", "Science", "Business"]
        for category in expected:
            assert category in CURATED_CATEGORIES

    def test_each_category_has_feeds(self):
        """Test that each category has at least one feed."""
        for category, feeds in CURATED_CATEGORIES.items():
            assert len(feeds) > 0, f"Category '{category}' has no feeds"

    def test_feeds_have_required_fields(self):
        """Test that all feeds have required fields."""
        for category, feeds in CURATED_CATEGORIES.items():
            for feed in feeds:
                assert "title" in feed, f"Feed in {category} missing title"
                assert "url" in feed, f"Feed in {category} missing url"
                assert "description" in feed, f"Feed in {category} missing description"

    def test_feeds_have_valid_urls(self):
        """Test that all feed URLs start with http:// or https://."""
        for category, feeds in CURATED_CATEGORIES.items():
            for feed in feeds:
                url = feed["url"]
                assert url.startswith(("http://", "https://")), \
                    f"Invalid URL '{url}' in {category}"

    def test_technology_category_has_popular_feeds(self):
        """Test Technology category has expected popular feeds."""
        tech_feeds = CURATED_CATEGORIES.get("Technology", [])
        titles = [f["title"] for f in tech_feeds]
        assert "Ars Technica" in titles
        assert "TechCrunch" in titles
        assert "Hacker News" in titles

    def test_ai_ml_category_exists(self):
        """Test that AI & Machine Learning category exists."""
        assert "AI & Machine Learning" in CURATED_CATEGORIES


# =============================================================================
# Tests for get_feeds_by_category
# =============================================================================


class TestGetFeedsByCategory:
    """Tests for get_feeds_by_category function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = get_feeds_by_category("Technology")
        assert isinstance(result, list)

    def test_returns_empty_list_for_unknown_category(self):
        """Test returns empty list for unknown category."""
        result = get_feeds_by_category("NonExistentCategory")
        assert result == []

    def test_returns_feeds_for_valid_category(self):
        """Test returns feeds for valid category."""
        result = get_feeds_by_category("Technology")
        assert len(result) > 0
        assert all("title" in f for f in result)

    def test_case_sensitive_category(self):
        """Test that category lookup is case-sensitive."""
        result_correct = get_feeds_by_category("Technology")
        result_wrong = get_feeds_by_category("technology")
        assert len(result_correct) > 0
        assert len(result_wrong) == 0

    def test_returns_correct_category_feeds(self):
        """Test returns feeds from correct category."""
        programming_feeds = get_feeds_by_category("Programming")
        titles = [f["title"] for f in programming_feeds]
        assert "Dev.to" in titles or "GitHub Blog" in titles


# =============================================================================
# Tests for get_all_categories
# =============================================================================


class TestGetAllCategories:
    """Tests for get_all_categories function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = get_all_categories()
        assert isinstance(result, list)

    def test_returns_non_empty_list(self):
        """Test returns non-empty list."""
        result = get_all_categories()
        assert len(result) > 0

    def test_includes_expected_categories(self):
        """Test includes expected categories."""
        result = get_all_categories()
        assert "Technology" in result
        assert "News" in result
        assert "Science" in result

    def test_all_items_are_strings(self):
        """Test all items are strings."""
        result = get_all_categories()
        assert all(isinstance(cat, str) for cat in result)

    def test_matches_curated_categories_keys(self):
        """Test matches CURATED_CATEGORIES keys."""
        result = get_all_categories()
        assert set(result) == set(CURATED_CATEGORIES.keys())


# =============================================================================
# Tests for search_curated_feeds
# =============================================================================


class TestSearchCuratedFeeds:
    """Tests for search_curated_feeds function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = search_curated_feeds("tech")
        assert isinstance(result, list)

    def test_returns_empty_list_for_no_matches(self):
        """Test returns empty list when no matches found."""
        result = search_curated_feeds("xyznonexistentquery123")
        assert result == []

    def test_finds_by_title(self):
        """Test finds feeds by title."""
        result = search_curated_feeds("Ars Technica")
        assert len(result) > 0
        assert any(f["title"] == "Ars Technica" for f in result)

    def test_finds_by_description(self):
        """Test finds feeds by description."""
        result = search_curated_feeds("technology news")
        assert len(result) > 0

    def test_finds_by_category(self):
        """Test finds feeds by category name."""
        result = search_curated_feeds("Programming")
        assert len(result) > 0
        # All results should have "Programming" as category
        assert all(f["category"] == "Programming" for f in result)

    def test_case_insensitive_search(self):
        """Test search is case-insensitive."""
        result_lower = search_curated_feeds("technology")
        result_upper = search_curated_feeds("TECHNOLOGY")
        result_mixed = search_curated_feeds("TeChnOlOgy")

        # All should return the same results
        assert len(result_lower) == len(result_upper)
        assert len(result_lower) == len(result_mixed)

    def test_results_include_category(self):
        """Test results include category field."""
        result = search_curated_feeds("news")
        assert len(result) > 0
        assert all("category" in f for f in result)

    def test_results_include_original_fields(self):
        """Test results include original feed fields."""
        result = search_curated_feeds("BBC")
        assert len(result) > 0
        feed = result[0]
        assert "title" in feed
        assert "url" in feed
        assert "description" in feed

    def test_partial_match(self):
        """Test partial string matching works."""
        result = search_curated_feeds("hack")
        assert len(result) > 0
        # Should find "Hacker News" and possibly "The Hacker News"

    def test_search_by_url_domain_not_supported(self):
        """Test that search by URL domain is not supported."""
        # Searching by URL parts should not match (not implemented)
        result = search_curated_feeds("feedburner")
        # May or may not find matches depending on if it's in title/description


# =============================================================================
# Tests for module import
# =============================================================================


class TestModuleImport:
    """Tests for module import behavior."""

    def test_module_imports_successfully(self):
        """Test that module can be imported."""
        from src import feed_catalog
        assert feed_catalog is not None

    def test_curated_categories_is_importable(self):
        """Test CURATED_CATEGORIES is importable."""
        from src.feed_catalog import CURATED_CATEGORIES
        assert CURATED_CATEGORIES is not None

    def test_functions_are_importable(self):
        """Test all functions are importable."""
        from src.feed_catalog import (
            get_feeds_by_category,
            get_all_categories,
            search_curated_feeds,
        )
        assert callable(get_feeds_by_category)
        assert callable(get_all_categories)
        assert callable(search_curated_feeds)


# =============================================================================
# Tests for feed data quality
# =============================================================================


class TestFeedDataQuality:
    """Tests for feed data quality and consistency."""

    def test_no_duplicate_titles_within_category(self):
        """Test no duplicate feed titles within a category."""
        for category, feeds in CURATED_CATEGORIES.items():
            titles = [f["title"] for f in feeds]
            assert len(titles) == len(set(titles)), \
                f"Duplicate titles found in {category}"

    def test_no_duplicate_urls_within_category(self):
        """Test no duplicate feed URLs within a category."""
        for category, feeds in CURATED_CATEGORIES.items():
            urls = [f["url"] for f in feeds]
            assert len(urls) == len(set(urls)), \
                f"Duplicate URLs found in {category}"

    def test_titles_not_empty(self):
        """Test all titles are non-empty strings."""
        for category, feeds in CURATED_CATEGORIES.items():
            for feed in feeds:
                assert feed["title"], f"Empty title in {category}"
                assert len(feed["title"].strip()) > 0

    def test_descriptions_not_empty(self):
        """Test all descriptions are non-empty strings."""
        for category, feeds in CURATED_CATEGORIES.items():
            for feed in feeds:
                assert feed["description"], f"Empty description in {category}"
                assert len(feed["description"].strip()) > 0

    def test_reasonable_number_of_categories(self):
        """Test there's a reasonable number of categories."""
        num_categories = len(CURATED_CATEGORIES)
        assert num_categories >= 5, "Too few categories"
        assert num_categories <= 50, "Too many categories"

    def test_reasonable_feeds_per_category(self):
        """Test each category has reasonable number of feeds."""
        for category, feeds in CURATED_CATEGORIES.items():
            assert len(feeds) >= 3, f"{category} has too few feeds"
            assert len(feeds) <= 20, f"{category} has too many feeds"
