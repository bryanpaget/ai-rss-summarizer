"""Story clustering and news item extraction."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .llm_providers import LLMProvider
from .storage import Article, NewsItem, Storage, Story


class StoryClusterer:
    """Handles Level 1 clustering: grouping articles into stories."""

    def __init__(self, llm_provider: LLMProvider, storage: Storage):
        self.llm = llm_provider
        self.storage = storage
        self.similarity_threshold = 0.75

    def cluster_article(self, article: Article) -> Story:
        """
        Cluster an article into a story.
        Either adds to existing story or creates new one.
        """
        # Try to find matching story
        matching_story = self.find_matching_story(article)

        if matching_story:
            # Add article to existing story
            return self.update_story_with_article(matching_story, article)
        else:
            # Create new story
            return self.create_new_story(article)

    def find_matching_story(self, article: Article) -> Optional[Story]:
        """Find an existing story that matches this article."""
        # Get active stories (not resolved)
        active_stories = self.storage.get_active_stories(limit=50)

        if not active_stories:
            return None

        # Compare article with each story
        best_match = None
        best_score = 0.0

        for story in active_stories:
            score = self._calculate_similarity(article, story)
            if score > best_score:
                best_score = score
                best_match = story

        # Return match if above threshold
        if best_score >= self.similarity_threshold:
            return best_match

        return None

    def _calculate_similarity(self, article: Article, story: Story) -> float:
        """Calculate similarity between article and story using LLM."""
        prompt = self._generate_comparison_prompt(article, story)

        try:
            # Get LLM response
            response = self.llm.summarize(prompt, max_length=200)

            # Try to parse JSON response
            result = self._parse_similarity_response(response)
            return result.get("confidence", 0.0) if result.get("is_same_story") else 0.0

        except Exception:
            # Fallback: keyword-based similarity
            return self._keyword_similarity(article, story)

    def _generate_comparison_prompt(self, article: Article, story: Story) -> str:
        """Generate prompt for LLM to compare article with story."""
        return f"""Compare this article to an existing story.

ARTICLE:
Title: {article.title}
Content: {article.content[:500]}

EXISTING STORY:
Title: {story.title}
Description: {story.description}
Keywords: {', '.join(story.keywords[:10])}

Are these about the same ongoing story? Consider:
- Same event or topic
- Related developments in same story
- Same key entities (people, organizations, places)

Respond with JSON:
{{
    "is_same_story": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""

    def _parse_similarity_response(self, response: str) -> dict:
        """Parse LLM response for similarity check."""
        try:
            # Try to find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except Exception:
            pass

        # Fallback: look for keywords
        response_lower = response.lower()
        if "true" in response_lower or "yes" in response_lower or "same" in response_lower:
            return {"is_same_story": True, "confidence": 0.7}
        return {"is_same_story": False, "confidence": 0.3}

    def _keyword_similarity(self, article: Article, story: Story) -> float:
        """Fallback keyword-based similarity calculation."""
        # Simple keyword matching
        article_text = f"{article.title} {article.content}".lower()
        story_keywords = [kw.lower() for kw in story.keywords]

        if not story_keywords:
            return 0.0

        matches = sum(1 for kw in story_keywords if kw in article_text)
        return matches / len(story_keywords)

    def create_new_story(self, article: Article) -> Story:
        """Create a new story from an article."""
        # Generate story metadata
        title = self._generate_story_title(article)
        description = self._generate_story_description(article)
        keywords = self._extract_keywords(article)

        # Parse published timestamp
        if article.published:
            try:
                if isinstance(article.published, str):
                    pub_str = article.published.replace("Z", "+00:00")
                    first_seen = datetime.fromisoformat(pub_str).replace(tzinfo=None)
                else:
                    first_seen = article.published
            except Exception:
                first_seen = datetime.now()
        else:
            first_seen = datetime.now()

        story = Story(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            keywords=keywords,
            first_seen=first_seen,
            last_updated=datetime.now(),
            lifecycle_state="emerging",
            article_ids=[article.id],
            news_item_ids=[],
        )

        # Save to database
        self.storage.save_story(story)
        self.storage.update_article_story(article.id, story.id)

        return story

    def update_story_with_article(self, story: Story, article: Article) -> Story:
        """Add an article to an existing story."""
        # Add article ID if not already present
        if article.id not in story.article_ids:
            story.article_ids.append(article.id)

        # Update last_updated timestamp
        story.last_updated = datetime.now()

        # Update story metadata (keywords may evolve)
        new_keywords = self._extract_keywords(article)
        for kw in new_keywords:
            if kw not in story.keywords:
                story.keywords.append(kw)

        # Keep only top keywords
        story.keywords = story.keywords[:20]

        # Save updates
        self.storage.update_story(story)
        self.storage.update_article_story(article.id, story.id)

        return story

    def _generate_story_title(self, article: Article) -> str:
        """Generate a story title from the article."""
        prompt = f"""Generate a concise story title (5-10 words) for this article.
Focus on the main topic/event, not specific details.

Article Title: {article.title}

Story Title:"""

        try:
            title = self.llm.summarize(prompt, max_length=100).strip()
            # Clean up the title
            title = title.replace('"', '').replace('\n', ' ')
            return title[:100]
        except Exception:
            # Fallback: use article title
            return article.title[:100]

    def _generate_story_description(self, article: Article) -> str:
        """Generate a brief story description."""
        prompt = f"""Describe what this story is about in 1-2 sentences.

Article: {article.title}
Content: {article.content[:300]}

Description:"""

        try:
            desc = self.llm.summarize(prompt, max_length=200).strip()
            return desc[:500]
        except Exception:
            # Fallback: use article summary or beginning of content
            return article.summary or article.content[:200]

    def _extract_keywords(self, article: Article) -> list[str]:
        """Extract keywords from article."""
        prompt = f"""Extract 5-10 key terms from this article.
Include: people, organizations, places, main topics.

Article: {article.title}
Content: {article.content[:400]}

Return as comma-separated list:"""

        try:
            response = self.llm.summarize(prompt, max_length=150).strip()
            # Split and clean keywords
            keywords = [kw.strip() for kw in response.split(',')]
            return [kw for kw in keywords if kw and len(kw) > 2][:10]
        except Exception:
            # Fallback: extract from title
            return [word for word in article.title.split() if len(word) > 4][:5]


class NewsItemExtractor:
    """Handles Level 2: extracting news items within stories."""

    def __init__(self, llm_provider: LLMProvider, storage: Storage):
        self.llm = llm_provider
        self.storage = storage
        self.min_confidence = 0.7

    def extract_news_items(self, article: Article, story: Story) -> list[NewsItem]:
        """Extract new information from article within the context of a story."""
        # Get existing news items for this story
        existing_items = self.storage.get_news_items(story.id)

        # Generate extraction prompt
        prompt = self._generate_extraction_prompt(article, existing_items)

        try:
            # Get LLM response
            response = self.llm.summarize(prompt, max_length=500)

            # Parse news items from response
            items = self._parse_news_items(response, article, story)

            # Deduplicate with existing items
            new_items = self.deduplicate_items(items, existing_items)

            # Save new items
            for item in new_items:
                if item.confidence >= self.min_confidence:
                    self.storage.save_news_item(item)

                    # Add to story's news_item_ids
                    if item.id not in story.news_item_ids:
                        story.news_item_ids.append(item.id)

            return new_items

        except Exception:
            # On error, return empty list
            return []

    def _generate_extraction_prompt(
        self, article: Article, existing_items: list[NewsItem]
    ) -> str:
        """Generate prompt for extracting news items."""
        existing_summary = "\n".join(
            [f"- {item.title}: {item.description}" for item in existing_items[:10]]
        )

        return f"""Extract new information from this article.

ARTICLE:
Title: {article.title}
Content: {article.content[:800]}

ALREADY KNOWN (from previous articles):
{existing_summary if existing_summary else "None"}

Task: Extract distinct pieces of NEW information from this article.
For each piece of information, classify it as:
- new_info: Actually new development or fact
- recap: Background/context from earlier
- analysis: Commentary or interpretation
- opinion: Editorial perspective

Respond with JSON array:
[
    {{
        "title": "brief title of news item",
        "description": "what's new",
        "type": "new_info|recap|analysis|opinion",
        "confidence": 0.0-1.0
    }}
]
"""

    def _parse_news_items(
        self, response: str, article: Article, story: Story
    ) -> list[NewsItem]:
        """Parse news items from LLM response."""
        items = []

        try:
            # Try to find JSON array in response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                # Parse published timestamp
                if article.published:
                    try:
                        if isinstance(article.published, str):
                            pub_str = article.published.replace("Z", "+00:00")
                            first_seen = datetime.fromisoformat(pub_str).replace(tzinfo=None)
                        else:
                            first_seen = article.published
                    except Exception:
                        first_seen = datetime.now()
                else:
                    first_seen = datetime.now()

                for item_data in data:
                    if isinstance(item_data, dict):
                        item = NewsItem(
                            id=str(uuid.uuid4()),
                            story_id=story.id,
                            title=item_data.get("title", "")[:200],
                            description=item_data.get("description", "")[:1000],
                            first_reported_by=article.feed_url,
                            first_seen=first_seen,
                            article_ids=[article.id],
                            item_type=item_data.get("type", "new_info"),
                            confidence=float(item_data.get("confidence", 0.8)),
                        )
                        items.append(item)

        except Exception:
            pass

        return items

    def deduplicate_items(
        self, new_items: list[NewsItem], existing_items: list[NewsItem]
    ) -> list[NewsItem]:
        """Remove items that are already known."""
        unique_items = []

        for new_item in new_items:
            is_duplicate = False

            for existing_item in existing_items:
                # Simple similarity check on titles
                if self._items_similar(new_item, existing_item):
                    is_duplicate = True
                    # Update existing item's article_ids if needed
                    if new_item.article_ids[0] not in existing_item.article_ids:
                        existing_item.article_ids.append(new_item.article_ids[0])
                        self.storage.update_news_item(existing_item)
                    break

            if not is_duplicate:
                unique_items.append(new_item)

        return unique_items

    def _items_similar(self, item1: NewsItem, item2: NewsItem) -> bool:
        """Check if two news items are similar (duplicates)."""
        # Simple keyword overlap
        words1 = set(item1.title.lower().split())
        words2 = set(item2.title.lower().split())

        if len(words1) == 0 or len(words2) == 0:
            return False

        overlap = len(words1 & words2) / max(len(words1), len(words2))
        return overlap > 0.6


class StoryEvolutionTracker:
    """Tracks story lifecycle and state transitions."""

    def __init__(self, storage: Storage):
        self.storage = storage

    def update_all_stories(self) -> dict:
        """Update lifecycle states for all active stories."""
        stories = self.storage.get_active_stories(limit=200)
        stats = {
            "updated": 0,
            "emerging": 0,
            "developing": 0,
            "peaked": 0,
            "declining": 0,
            "resolved": 0,
        }

        for story in stories:
            old_state = story.lifecycle_state
            new_state = self.update_lifecycle_state(story)

            if old_state != new_state:
                story.lifecycle_state = new_state
                self.storage.update_story(story)
                stats["updated"] += 1

            stats[new_state] = stats.get(new_state, 0) + 1

        return stats

    def calculate_velocity(self, story: Story, window_hours: int = 24) -> float:
        """Calculate article velocity (articles per day)."""
        if not story.article_ids:
            return 0.0

        recent_cutoff = datetime.now() - timedelta(hours=window_hours)
        recent_count = 0

        for article_id in story.article_ids:
            article = self.storage.get_article(article_id)
            if article and article.published:
                try:
                    if isinstance(article.published, str):
                        pub_str = article.published.replace("Z", "+00:00")
                        pub_time = datetime.fromisoformat(pub_str).replace(tzinfo=None)
                    else:
                        pub_time = article.published

                    if pub_time > recent_cutoff:
                        recent_count += 1
                except Exception:
                    pass

        return recent_count / (window_hours / 24)

    def update_lifecycle_state(self, story: Story) -> str:
        """Determine story lifecycle state based on activity."""
        age_hours = (datetime.now() - story.first_seen).total_seconds() / 3600
        hours_since_update = (
            datetime.now() - story.last_updated
        ).total_seconds() / 3600
        article_count = len(story.article_ids)
        velocity = self.calculate_velocity(story)

        # Resolved: No activity for 7 days
        if hours_since_update > 168:
            return "resolved"

        # Declining: No recent articles but not resolved yet
        if hours_since_update > 48 and velocity < 0.5:
            return "declining"

        # Peaked: Many articles but velocity declining
        if article_count >= 10 and velocity < 2.0:
            return "peaked"

        # Developing: Multiple articles and growing
        if article_count >= 4 or velocity >= 2.0:
            return "developing"

        # Emerging: New story
        return "emerging"

    def get_evolution_stats(self) -> dict:
        """Get statistics about story evolution."""
        all_stories = self.storage.get_all_stories(limit=500)

        stats = {
            "total_stories": len(all_stories),
            "by_state": {},
            "avg_articles_per_story": 0,
            "avg_news_items_per_story": 0,
        }

        total_articles = 0
        total_items = 0

        for story in all_stories:
            state = story.lifecycle_state
            stats["by_state"][state] = stats["by_state"].get(state, 0) + 1
            total_articles += len(story.article_ids)
            total_items += len(story.news_item_ids)

        if len(all_stories) > 0:
            stats["avg_articles_per_story"] = total_articles / len(all_stories)
            stats["avg_news_items_per_story"] = total_items / len(all_stories)

        return stats


def process_article_clustering(
    article: Article,
    llm_provider: LLMProvider,
    storage: Storage,
    enable_news_extraction: bool = True,
) -> dict:
    """
    Process clustering for a single article.

    Args:
        article: Article to process
        llm_provider: LLM provider for clustering
        storage: Storage instance
        enable_news_extraction: Whether to extract news items

    Returns:
        Dictionary with processing stats
    """
    stats = {
        "story_created": False,
        "story_id": None,
        "news_items_extracted": 0,
    }

    try:
        # Level 1: Cluster article into story
        clusterer = StoryClusterer(llm_provider, storage)
        story = clusterer.cluster_article(article)

        stats["story_id"] = story.id
        stats["story_created"] = len(story.article_ids) == 1  # New story if first article

        # Level 2: Extract news items (if enabled)
        if enable_news_extraction:
            extractor = NewsItemExtractor(llm_provider, storage)
            news_items = extractor.extract_news_items(article, story)
            stats["news_items_extracted"] = len(news_items)

            # Update story with new news items
            if news_items:
                storage.update_story(story)

    except Exception as e:
        # Log error but don't fail
        stats["error"] = str(e)

    return stats


def batch_process_articles(
    articles: list[Article],
    llm_provider: LLMProvider,
    storage: Storage,
    enable_news_extraction: bool = True,
) -> dict:
    """
    Process clustering for multiple articles in batch.

    Args:
        articles: List of articles to process
        llm_provider: LLM provider for clustering
        storage: Storage instance
        enable_news_extraction: Whether to extract news items

    Returns:
        Dictionary with batch processing stats
    """
    stats = {
        "processed": 0,
        "stories_created": 0,
        "articles_added_to_existing": 0,
        "total_news_items": 0,
        "errors": [],
    }

    for article in articles:
        result = process_article_clustering(
            article, llm_provider, storage, enable_news_extraction
        )

        stats["processed"] += 1

        if result.get("story_created"):
            stats["stories_created"] += 1
        else:
            stats["articles_added_to_existing"] += 1

        stats["total_news_items"] += result.get("news_items_extracted", 0)

        if "error" in result:
            stats["errors"].append(f"{article.id}: {result['error']}")

    return stats
