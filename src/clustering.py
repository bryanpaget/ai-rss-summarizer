"""Story clustering and news item extraction."""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .llm_providers import LLMProvider
from .storage import Article, NewsItem, Storage, Story
from .embeddings import EmbeddingService, EmbeddingError, embed_and_store_article, embed_and_store_story
from .knowledge import KnowledgeBase
from .content_filter import is_promotional_content


class ClusteringError(Exception):
    """Raised when clustering operations fail."""
    pass


class StoryClusterer:
    """Handles Level 1 clustering: grouping articles into stories.

    Uses vector embeddings for fast similarity comparison (O(n) instead of O(n²)).
    LLM is only used for generating story metadata, not for comparisons.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        storage: Storage,
        kb: Optional[KnowledgeBase] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.llm = llm_provider
        self.storage = storage
        self.kb = kb or KnowledgeBase()
        # Use provided embedding_service or create one
        self._embedding_service = embedding_service or EmbeddingService(self.kb)
        self.similarity_threshold = 0.70  # Cosine similarity threshold

    @property
    def embedding_service(self) -> EmbeddingService:
        """Access the embedding service."""
        return self._embedding_service

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
        """Find an existing story that matches this article using vector similarity.

        This is O(n) vector comparisons, not O(n) LLM calls.

        Raises:
            ClusteringError: If embedding provider is unavailable
        """
        # Get or generate article embedding
        article_embedding = self._get_or_create_article_embedding(article)

        # Get active stories
        active_stories = self.storage.get_active_stories(limit=100)

        if not active_stories:
            return None

        # Compare article embedding with each story embedding
        best_match = None
        best_score = 0.0

        for story in active_stories:
            score = self._calculate_similarity(article_embedding, story)
            if score > best_score:
                best_score = score
                best_match = story

        # Return match if above threshold
        if best_score >= self.similarity_threshold:
            return best_match

        return None

    def find_matching_story_with_embedding(
        self, article: Article, embedding: list[float]
    ) -> Optional[Story]:
        """Find matching story using a pre-computed embedding.

        This avoids loading the embedding model during LLM phase.
        """
        # Get active stories
        active_stories = self.storage.get_active_stories(limit=100)

        if not active_stories:
            return None

        # Compare with each story
        best_match = None
        best_score = 0.0

        for story in active_stories:
            score = self._calculate_similarity(embedding, story)
            if score > best_score:
                best_score = score
                best_match = story

        if best_score >= self.similarity_threshold:
            return best_match

        return None

    def _get_or_create_article_embedding(self, article: Article) -> list[float]:
        """Get existing embedding or create new one for article.

        Raises:
            ClusteringError: If embedding fails
        """
        # Check if embedding already exists
        existing = self.embedding_service.get_embedding(article.id, "article")
        if existing:
            return existing

        # Generate new embedding
        try:
            result = self.embedding_service.embed_article(article)
            self.embedding_service.save_embedding(article.id, "article", result)
            return result.vector
        except EmbeddingError as e:
            raise ClusteringError(
                f"Cannot cluster article '{article.title}': {e}"
            ) from e

    def _calculate_similarity(self, article_embedding: list[float], story: Story) -> float:
        """Calculate similarity between article and story using vector cosine similarity.

        No LLM calls, no embedding generation - just fast vector math.
        If story has no embedding, returns 0 (no match) to avoid model switching.
        """
        # Get story embedding - never generate on the fly to avoid model switching
        story_embedding = self.embedding_service.get_embedding(story.id, "story")

        if not story_embedding:
            # Story doesn't have embedding - skip it to avoid model switch
            # Story will get embedding during next embedding phase
            return 0.0

        return self.embedding_service.cosine_similarity(article_embedding, story_embedding)

    def _find_matching_story_keywords(self, article: Article) -> Optional[Story]:
        """Fallback: find matching story using keywords (no embeddings)."""
        active_stories = self.storage.get_active_stories(limit=50)

        if not active_stories:
            return None

        best_match = None
        best_score = 0.0

        for story in active_stories:
            score = self._keyword_similarity(article, story)
            if score > best_score:
                best_score = score
                best_match = story

        if best_score >= 0.5:  # Lower threshold for keyword matching
            return best_match

        return None

    def _generate_comparison_prompt(self, article: Article, story: Story) -> str:
        """Generate prompt for LLM to compare article with story."""
        return f"""Compare this article to an existing story.

ARTICLE:
Title: {article.title}
Content: {article.content}

EXISTING STORY:
Title: {story.title}
Description: {story.description}
Keywords: {', '.join(story.keywords[:10]) if story.keywords else 'None'}

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
        except (json.JSONDecodeError, ValueError) as e:
            import sys
            print(f"JSON parsing failed for similarity response: {e}", file=sys.stderr)

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
        """Create a new story from an article.

        Also generates and stores embedding for the story for future similarity matching.
        """
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
            except (ValueError, TypeError) as e:
                import sys
                print(f"Warning: Invalid date format for article '{article.title[:30]}': {e}", file=sys.stderr)
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

        # NOTE: Story embedding is deferred to avoid model switching during LLM phase.
        # New stories will get embeddings during the next embedding phase.

        return story

    def update_story_with_article(self, story: Story, article: Article) -> Story:
        """Add an article to an existing story.

        Updates keywords and refreshes story embedding if keywords changed significantly.
        """
        # Add article ID if not already present
        if article.id not in story.article_ids:
            story.article_ids.append(article.id)

        # Update last_updated timestamp
        story.last_updated = datetime.now()

        # Update story metadata (keywords may evolve)
        old_keyword_count = len(story.keywords)
        new_keywords = self._extract_keywords(article)
        keywords_added = 0
        for kw in new_keywords:
            if kw not in story.keywords:
                story.keywords.append(kw)
                keywords_added += 1

        # Keep only top keywords
        story.keywords = story.keywords[:20]

        # Save updates
        self.storage.update_story(story)
        self.storage.update_article_story(article.id, story.id)

        # NOTE: Story re-embedding is deferred to avoid model switching during LLM phase.
        # Story embeddings are refreshed during the next embedding phase when needed.
        # The keywords are stored, so semantic matching will still work reasonably well.

        return story

    def _generate_story_title(self, article: Article) -> str:
        """Generate a story title from the article."""
        prompt = f"""You are a headline writer. Write ONE short headline (3-8 words) that captures the main topic.

Article: {article.title}

Headline:"""

        try:
            title = self.llm.generate(prompt, max_tokens=30).strip()
            # Clean up the title - remove quotes, newlines, markdown, common prefixes
            title = title.replace('"', '').replace('\n', ' ')
            title = title.replace('**', '').replace('*', '').replace('`', '')  # Strip markdown
            title = title.strip()
            # Remove common LLM response patterns
            for prefix in ["Here is", "Here's", "The headline is", "Headline:"]:
                if title.lower().startswith(prefix.lower()):
                    title = title[len(prefix):].strip()
            # If still garbage, use fallback
            if len(title) < 3 or len(title) > 100 or "few" in title.lower():
                return article.title
            return title
        except Exception:
            # Fallback: use article title
            return article.title

    def _generate_story_description(self, article: Article) -> str:
        """Generate a brief story description."""
        prompt = f"""Describe what this story is about in 1-2 sentences.

Article: {article.title}
Content: {article.content}

Description:"""

        try:
            desc = self.llm.generate(prompt, max_tokens=150).strip()
            return desc
        except Exception:
            # Fallback: use article summary or full content
            return article.summary or article.content or ""

    def _extract_keywords(self, article: Article) -> list[str]:
        """Extract keywords from article."""
        prompt = f"""Extract ALL key terms from this article.
Include: people, organizations, places, main topics. The number of terms depends on content density.

Article: {article.title}
Content: {article.content}

Return as comma-separated list:"""

        try:
            response = self.llm.generate(prompt, max_tokens=200).strip()
            # Split and clean keywords
            keywords = [kw.strip() for kw in response.split(',')]
            return [kw for kw in keywords if kw and len(kw) > 2]
        except Exception:
            # Fallback: extract from title
            return [word for word in article.title.split() if len(word) > 4]


class NewsItemExtractor:
    """Handles Level 2: extracting news items within stories."""

    # Similarity threshold for duplicate detection
    SIMILARITY_THRESHOLD = 0.75

    def __init__(
        self,
        llm_provider: LLMProvider,
        storage: Storage,
        embedding_service: Optional[EmbeddingService] = None,
        kb: Optional[KnowledgeBase] = None,
    ):
        self.llm = llm_provider
        self.storage = storage
        self.min_confidence = 0.7
        # Use provided embedding service or create one
        if embedding_service:
            self._embedding_service = embedding_service
        else:
            self._kb = kb or KnowledgeBase()
            self._embedding_service = EmbeddingService(self._kb)
        self._embedding_cache: dict[str, list[float]] = {}

    def extract_news_items(self, article: Article, story: Story) -> list[NewsItem]:
        """Extract new information from article within the context of a story."""
        # Get existing news items for this story
        existing_items = self.storage.get_news_items(story.id)

        # Generate extraction prompt
        prompt = self._generate_extraction_prompt(article, existing_items)

        try:
            # Get LLM response - use generate() for extraction prompt
            response = self.llm.generate(prompt, max_tokens=500)

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

        except Exception as e:
            # Log error for visibility, return empty list to continue processing
            import sys
            print(f"Error extracting news items from article '{article.title[:40]}': {e}", file=sys.stderr)
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
Content: {article.content}

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
                    except (ValueError, TypeError) as e:
                        import sys
                        print(f"Warning: Invalid date format for article: {e}", file=sys.stderr)
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

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # Expected for non-JSON or malformed responses
            import sys
            print(f"Could not parse news items from LLM response: {e}", file=sys.stderr)

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
        """Check if two news items are similar (duplicates) using embedding similarity.

        Requires EmbeddingService. Returns False if unavailable (assumes not duplicate).
        """
        if not self._embedding_service or not self._embedding_service.is_available():
            import sys
            print("EmbeddingService required but not available for item similarity", file=sys.stderr)
            return False  # Can't determine similarity, assume not duplicate

        # Combine title and description for better semantic matching
        text1 = f"{item1.title} {item1.description or ''}"
        text2 = f"{item2.title} {item2.description or ''}"

        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)

        if emb1 is None or emb2 is None:
            return False  # Can't embed, assume not duplicate

        similarity = self._embedding_service.cosine_similarity(emb1, emb2)
        return similarity >= self.SIMILARITY_THRESHOLD

    def _get_embedding(self, text: str) -> Optional[list[float]]:
        """Get embedding for text, using cache."""
        # Normalize text for cache key
        cache_key = text[:500]  # Limit key length
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        try:
            result = self._embedding_service.embed_text(text)
            self._embedding_cache[cache_key] = result.vector
            return result.vector
        except EmbeddingError:
            return None


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
                except (ValueError, TypeError) as e:
                    # Date parsing failed - skip this article for velocity calc
                    import sys
                    print(f"Warning: Invalid date format for article {article_id}: {e}", file=sys.stderr)

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
    kb: Optional[KnowledgeBase] = None,
) -> dict:
    """
    Process clustering for a single article.

    Uses vector embeddings for O(n) similarity comparisons instead of O(n²) LLM calls.

    Args:
        article: Article to process
        llm_provider: LLM provider for metadata generation
        storage: Storage instance
        enable_news_extraction: Whether to extract news items
        kb: Optional KnowledgeBase for embedding storage

    Returns:
        Dictionary with processing stats
    """
    stats = {
        "story_created": False,
        "story_id": None,
        "news_items_extracted": 0,
    }

    try:
        # Level 1: Cluster article into story (uses embeddings, not LLM calls)
        clusterer = StoryClusterer(llm_provider, storage, kb)
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


def update_story_clusters(
    storage: Storage,
    lookback_hours: int = 72,
) -> dict:
    """
    Update story clusters by processing unclustered articles.

    This is a convenience function that gets an LLM provider and processes
    unclustered articles in batch.

    Args:
        storage: Storage instance
        lookback_hours: How far back to look for articles to cluster

    Returns:
        Dictionary with stats: {'processed': int, 'new_clusters': int,
                               'added_to_existing': int, 'skipped': int}
    """
    from .llm_providers import get_best_provider
    from datetime import datetime, timedelta

    # Get LLM provider
    provider, is_llm = get_best_provider()

    if not is_llm:
        # No LLM available, can't cluster
        return {
            'processed': 0,
            'new_clusters': 0,
            'added_to_existing': 0,
            'skipped': 0,
        }

    # Get unclustered articles from the lookback window
    all_articles = storage.get_articles(limit=500)
    cutoff = datetime.now() - timedelta(hours=lookback_hours)

    unclustered = []
    for article in all_articles:
        # Skip if already has a story
        if article.story_id:
            continue

        # Check if within lookback window
        if article.published:
            try:
                if isinstance(article.published, str):
                    pub_str = article.published.replace("Z", "+00:00")
                    pub_time = datetime.fromisoformat(pub_str).replace(tzinfo=None)
                else:
                    pub_time = article.published

                if pub_time < cutoff:
                    continue
            except (ValueError, TypeError) as e:
                # Date parsing failed - include article anyway (conservative)
                import sys
                print(f"Warning: Invalid date format for article {article.id}: {e}", file=sys.stderr)

        unclustered.append(article)

    if not unclustered:
        return {
            'processed': 0,
            'new_clusters': 0,
            'added_to_existing': 0,
            'skipped': len(all_articles),
        }

    # Process with batch function
    result = batch_process_articles(
        unclustered,
        provider,
        storage,
        enable_news_extraction=False  # Faster for cluster updates
    )

    return {
        'processed': result['processed'],
        'new_clusters': result['stories_created'],
        'added_to_existing': result['articles_added_to_existing'],
        'skipped': len(all_articles) - len(unclustered),
    }


def backfill_story_embeddings(
    storage: Storage,
    kb: Optional[KnowledgeBase] = None,
    progress_callback: Optional[callable] = None,
) -> dict:
    """
    Backfill embeddings for stories that don't have them.

    This fixes duplicate detection for stories created before the embedding
    phase was added. Stories without embeddings return similarity=0.

    Args:
        storage: Storage instance
        kb: Optional KnowledgeBase (creates one if not provided)
        progress_callback: Optional callback(current, total, story_title)

    Returns:
        Dictionary with stats: {'processed': int, 'embedded': int, 'errors': list}
    """
    if kb is None:
        kb = KnowledgeBase()

    embedding_service = EmbeddingService(kb)

    # Check if embedding provider is available
    if not embedding_service.is_available():
        return {
            'processed': 0,
            'embedded': 0,
            'errors': ['No embedding provider available'],
        }

    # Get all stories
    all_stories = storage.get_all_stories(limit=1000)

    # Get story IDs that already have embeddings
    embedded_ids = kb.get_target_ids_with_embeddings("story")

    # Filter to stories needing embeddings
    stories_needing_embeddings = [
        s for s in all_stories if s.id not in embedded_ids
    ]

    stats = {
        'processed': 0,
        'embedded': 0,
        'already_embedded': len(embedded_ids),
        'errors': [],
    }

    total = len(stories_needing_embeddings)
    for i, story in enumerate(stories_needing_embeddings):
        if progress_callback:
            progress_callback(i + 1, total, story.title)

        try:
            result = embedding_service.embed_story(story)
            embedding_service.save_embedding(story.id, "story", result)
            stats['embedded'] += 1
        except Exception as e:
            stats['errors'].append(f"{story.id}: {str(e)}")

        stats['processed'] += 1

    return stats


def batch_process_articles(
    articles: list[Article],
    llm_provider: LLMProvider,
    storage: Storage,
    enable_news_extraction: bool = True,
    kb: Optional[KnowledgeBase] = None,
) -> dict:
    """
    Process clustering for multiple articles in batch.

    Uses vector embeddings for O(n) similarity comparisons per article,
    avoiding O(n²) LLM calls that would make batch processing slow.

    Args:
        articles: List of articles to process
        llm_provider: LLM provider for metadata generation
        storage: Storage instance
        enable_news_extraction: Whether to extract news items
        kb: Optional KnowledgeBase for embedding storage

    Returns:
        Dictionary with batch processing stats
    """
    # Create shared KB instance if not provided
    if kb is None:
        kb = KnowledgeBase()

    stats = {
        "processed": 0,
        "stories_created": 0,
        "articles_added_to_existing": 0,
        "total_news_items": 0,
        "errors": [],
    }

    for article in articles:
        result = process_article_clustering(
            article, llm_provider, storage, enable_news_extraction, kb
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
