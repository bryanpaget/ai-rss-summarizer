"""Tests for pipeline architecture invariants.

These tests enforce architectural rules that MUST hold:
1. LLM phase must have ZERO embedding calls
2. LLM phase must have exactly 1 LLM call per article
3. Embedding phase must have ZERO LLM calls
4. No model switching within a phase

These tests are designed to FAIL when the architecture is broken,
providing immediate visibility into regressions.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass


# =============================================================================
# Test Infrastructure - Call Trackers
# =============================================================================


class CallTracker:
    """Tracks calls to LLM and embedding services with full visibility."""

    def __init__(self):
        self.llm_calls = []  # List of (method_name, args) tuples
        self.embedding_calls = []  # List of (method_name, args) tuples
        self.call_sequence = []  # Ordered list of ("llm", method) or ("embed", method)

    def record_llm_call(self, method_name: str, *args):
        """Record an LLM call."""
        self.llm_calls.append((method_name, args))
        self.call_sequence.append(("llm", method_name))

    def record_embedding_call(self, method_name: str, *args):
        """Record an embedding call."""
        self.embedding_calls.append((method_name, args))
        self.call_sequence.append(("embed", method_name))

    def get_llm_count(self) -> int:
        """Get total LLM calls."""
        return len(self.llm_calls)

    def get_embedding_count(self) -> int:
        """Get total embedding calls."""
        return len(self.embedding_calls)

    def has_model_switching(self) -> bool:
        """Check if there's llm->embed->llm or embed->llm->embed pattern."""
        if len(self.call_sequence) < 3:
            return False

        for i in range(len(self.call_sequence) - 2):
            types = [self.call_sequence[i][0],
                    self.call_sequence[i+1][0],
                    self.call_sequence[i+2][0]]
            # llm -> embed -> llm
            if types == ["llm", "embed", "llm"]:
                return True
            # embed -> llm -> embed
            if types == ["embed", "llm", "embed"]:
                return True
        return False

    def get_report(self) -> str:
        """Get a human-readable report of all calls."""
        lines = ["Call Sequence Report:"]
        lines.append(f"  Total LLM calls: {len(self.llm_calls)}")
        lines.append(f"  Total Embedding calls: {len(self.embedding_calls)}")
        lines.append("")
        lines.append("  Sequence:")
        for i, (call_type, method) in enumerate(self.call_sequence):
            lines.append(f"    {i+1}. [{call_type.upper()}] {method}")
        return "\n".join(lines)


def create_tracking_provider(tracker: CallTracker):
    """Create a mock LLM provider that tracks all calls."""
    provider = MagicMock()
    provider.name = "TrackingProvider"

    def track_summarize(prompt, max_length=None):
        tracker.record_llm_call("summarize", prompt[:100] + "...")
        # Return valid JSON for insight extraction
        return '[{"content": "Test insight", "type": "technical", "confidence": "high", "reason": "test", "entities": []}]'

    def track_generate(prompt, max_tokens=None):
        tracker.record_llm_call("generate", prompt[:100] + "...")
        # Return valid JSON for various extraction types
        if "chunk" in prompt.lower() or "divide" in prompt.lower():
            return '["chunk 1 text here"]'
        elif "triple" in prompt.lower() or "relationship" in prompt.lower():
            return '[]'
        return '{}'

    provider.summarize.side_effect = track_summarize
    provider.generate.side_effect = track_generate

    return provider


def create_tracking_embedding_service(tracker: CallTracker):
    """Create a mock embedding service that tracks all calls."""
    service = MagicMock()

    def track_embed_text(text):
        tracker.record_embedding_call("embed_text", text[:50] + "...")
        result = MagicMock()
        result.vector = [0.1] * 384  # Return valid embedding
        return result

    def track_embed_story(story):
        tracker.record_embedding_call("embed_story", story.id if hasattr(story, 'id') else str(story))
        result = MagicMock()
        result.vector = [0.1] * 384
        return result

    service.embed_text.side_effect = track_embed_text
    service.embed_story.side_effect = track_embed_story
    service.is_available.return_value = True
    service.get_provider_info.return_value = {"provider": "tracking", "model": "test"}
    service.get_embedding.return_value = None  # No cached embeddings
    service.cosine_similarity.return_value = 0.5

    return service


def create_test_article(article_id: str = "test-1"):
    """Create a test article with sufficient content."""
    article = MagicMock()
    article.id = article_id
    article.title = f"Test Article {article_id}"
    article.content = (
        "This is test content that is long enough to be processed. " * 10
    )  # ~500 chars
    article.summary = None
    article.trend_tags = None
    article.signal_tags = None
    article.link = f"https://example.com/{article_id}"
    article.published = None
    article.story_id = None
    return article


# =============================================================================
# TEST 1: LLM Phase Must Have ZERO Embedding Calls
# =============================================================================


class TestLLMPhaseNoEmbeddings:
    """LLM phase (Step 3) must NEVER call embedding service."""

    @patch('src.report.SignalTagger')
    @patch('src.knowledge.KnowledgeBase')
    def test_llm_phase_zero_embedding_calls(self, mock_kb_class, mock_tagger_class):
        """
        ARCHITECTURAL INVARIANT: _run_llm_phase must not call embedding service.

        This test MUST FAIL if embedding calls happen during LLM phase.
        Current code violates this by calling analyze_article() which embeds.
        """
        from src.report import _run_llm_phase
        from src.knowledge import TripleExtractionResult

        # Setup tracking
        tracker = CallTracker()
        provider = create_tracking_provider(tracker)
        embedding_service = create_tracking_embedding_service(tracker)

        # Setup mocks
        mock_kb = MagicMock()
        mock_kb.get_insights.return_value = []
        mock_kb.get_triples.return_value = []
        mock_kb.query_triples_pattern.return_value = []
        mock_kb_class.return_value = mock_kb

        mock_tagger = MagicMock()
        mock_tagger.tag_article.return_value = MagicMock(
            to_json=lambda: '{}',
            to_compact_string=lambda: ""
        )
        mock_tagger_class.return_value = mock_tagger

        mock_storage = MagicMock()
        mock_storage.get_embedding.return_value = None

        # Create test article
        articles = [create_test_article("article-1")]

        stats = {
            "processed": 0,
            "insights": 0,
            "triples": 0,
            "triples_new": 0,
            "triples_existing": 0,
            "connections": 0,
            "errors": 0,
        }

        # Patch the functions that would be called
        with patch('src.report.extract_insights_from_article') as mock_insights, \
             patch('src.report.extract_triples_with_comparison') as mock_triples, \
             patch('src.report.analyze_article') as mock_analyze:

            # Setup return values
            mock_insights.return_value = []
            mock_triples.return_value = TripleExtractionResult(
                new_triples=[], existing_triples=[], updated_triples=[]
            )
            mock_analyze.return_value = "AI, Technology"

            # Run LLM phase
            _run_llm_phase(
                articles=articles,
                storage=mock_storage,
                kb=mock_kb,
                provider=provider,
                stats=stats,
                embedding_service=embedding_service,
                limit=0,
            )

        # ASSERTION: Zero embedding calls during LLM phase
        embedding_count = tracker.get_embedding_count()

        if embedding_count > 0:
            report = tracker.get_report()
            pytest.fail(
                f"ARCHITECTURAL VIOLATION: LLM phase made {embedding_count} embedding calls!\n"
                f"LLM phase must have ZERO embedding calls.\n\n"
                f"{report}"
            )


class TestLLMPhaseCallCount:
    """LLM phase must make exactly 1 LLM call per article."""

    def test_one_llm_call_per_article(self):
        """
        ARCHITECTURAL INVARIANT: Each article should trigger exactly 1 LLM call.

        This test MUST FAIL if multiple LLM calls happen per article.
        Current code violates this with: insights + chunking + triples + tagging.
        """
        from src.report import _run_llm_phase
        from src.knowledge import TripleExtractionResult

        # Setup tracking
        tracker = CallTracker()
        provider = create_tracking_provider(tracker)
        embedding_service = create_tracking_embedding_service(tracker)

        # Setup mocks
        mock_kb = MagicMock()
        mock_kb.get_insights.return_value = []
        mock_kb.get_triples.return_value = []
        mock_kb.query_triples_pattern.return_value = []

        mock_tagger = MagicMock()
        mock_tagger.tag_article.return_value = MagicMock(
            to_json=lambda: '{}',
            to_compact_string=lambda: ""
        )

        mock_storage = MagicMock()
        mock_storage.get_embedding.return_value = None

        # Create test articles
        num_articles = 3
        articles = [create_test_article(f"article-{i}") for i in range(num_articles)]

        stats = {
            "processed": 0,
            "insights": 0,
            "triples": 0,
            "triples_new": 0,
            "triples_existing": 0,
            "connections": 0,
            "errors": 0,
        }

        # Run WITHOUT mocking the extraction functions - let them call provider
        with patch('src.report.SignalTagger') as mock_tagger_class, \
             patch('src.knowledge._semantic_chunk') as mock_chunk:

            mock_tagger_class.return_value = mock_tagger
            # Return single chunk to minimize calls (but still wrong if >1 per article)
            mock_chunk.return_value = ["single chunk"]

            # Run LLM phase
            _run_llm_phase(
                articles=articles,
                storage=mock_storage,
                kb=mock_kb,
                provider=provider,
                stats=stats,
                embedding_service=embedding_service,
                limit=0,
            )

        # ASSERTION: Exactly 1 LLM call per article
        llm_count = tracker.get_llm_count()
        expected = num_articles  # 1 call per article

        if llm_count != expected:
            report = tracker.get_report()
            calls_per_article = llm_count / num_articles if num_articles > 0 else 0
            pytest.fail(
                f"ARCHITECTURAL VIOLATION: Expected {expected} LLM calls ({num_articles} articles x 1 call), "
                f"got {llm_count} ({calls_per_article:.1f} calls per article)!\n\n"
                f"{report}"
            )


# =============================================================================
# TEST 2: Embedding Phase Must Have ZERO LLM Calls
# =============================================================================


class TestEmbeddingPhaseNoLLM:
    """Embedding phase (Step 4) must NEVER call LLM."""

    def test_embedding_phase_zero_llm_calls(self):
        """
        ARCHITECTURAL INVARIANT: _run_embedding_phase must not call LLM.

        This test verifies embedding phase isolation.
        """
        from src.report import _run_embedding_phase

        # Setup tracking
        tracker = CallTracker()
        provider = create_tracking_provider(tracker)
        embedding_service = create_tracking_embedding_service(tracker)

        # Setup mocks
        mock_kb = MagicMock()
        mock_storage = MagicMock()
        mock_storage.get_embedding.return_value = None  # No cached embeddings
        mock_storage.get_active_stories.return_value = []

        # Create test articles with summaries (so semantic card can be built)
        articles = [create_test_article(f"article-{i}") for i in range(3)]
        for a in articles:
            a.summary = "Test summary"
            a.trend_tags = "AI"

        stats = {
            "embeddings_generated": 0,
            "story_embeddings_generated": 0,
            "errors": 0,
        }

        # Run embedding phase
        _run_embedding_phase(
            articles=articles,
            storage=mock_storage,
            kb=mock_kb,
            stats=stats,
            embedding_service=embedding_service,
            limit=0,
        )

        # ASSERTION: Zero LLM calls during embedding phase
        llm_count = tracker.get_llm_count()

        if llm_count > 0:
            report = tracker.get_report()
            pytest.fail(
                f"ARCHITECTURAL VIOLATION: Embedding phase made {llm_count} LLM calls!\n"
                f"Embedding phase must have ZERO LLM calls.\n\n"
                f"{report}"
            )


# =============================================================================
# TEST 3: No Model Switching Within Phase
# =============================================================================


class TestNoModelSwitching:
    """No phase should switch between LLM and embedding models."""

    def test_no_interleaved_calls(self):
        """
        ARCHITECTURAL INVARIANT: No llm->embed->llm or embed->llm->embed patterns.

        Model switching is expensive and indicates architectural violation.
        """
        from src.report import _run_llm_phase
        from src.knowledge import TripleExtractionResult

        # Setup tracking
        tracker = CallTracker()
        provider = create_tracking_provider(tracker)
        embedding_service = create_tracking_embedding_service(tracker)

        # Setup mocks
        mock_kb = MagicMock()
        mock_kb.get_insights.return_value = []

        mock_tagger = MagicMock()
        mock_tagger.tag_article.return_value = MagicMock(
            to_json=lambda: '{}',
            to_compact_string=lambda: ""
        )

        mock_storage = MagicMock()
        mock_storage.get_embedding.return_value = None

        articles = [create_test_article("article-1")]

        stats = {
            "processed": 0,
            "insights": 0,
            "triples": 0,
            "triples_new": 0,
            "triples_existing": 0,
            "connections": 0,
            "errors": 0,
        }

        with patch('src.report.SignalTagger') as mock_tagger_class, \
             patch('src.report.extract_insights_from_article') as mock_insights, \
             patch('src.report.extract_triples_with_comparison') as mock_triples, \
             patch('src.report.analyze_article') as mock_analyze:

            mock_tagger_class.return_value = mock_tagger
            mock_insights.return_value = []
            mock_triples.return_value = TripleExtractionResult(
                new_triples=[], existing_triples=[], updated_triples=[]
            )
            mock_analyze.return_value = "AI"

            _run_llm_phase(
                articles=articles,
                storage=mock_storage,
                kb=mock_kb,
                provider=provider,
                stats=stats,
                embedding_service=embedding_service,
                limit=0,
            )

        # ASSERTION: No model switching
        if tracker.has_model_switching():
            report = tracker.get_report()
            pytest.fail(
                f"ARCHITECTURAL VIOLATION: Model switching detected!\n"
                f"Phases must not interleave LLM and embedding calls.\n\n"
                f"{report}"
            )


# =============================================================================
# TEST 4: analyze_article Must Not Use Embeddings
# =============================================================================


class TestAnalyzeArticleNoEmbeddings:
    """analyze_article in trends.py must not make embedding calls during LLM phase."""

    def test_analyze_article_embedding_violation(self):
        """
        ARCHITECTURAL VIOLATION CHECK: analyze_article currently uses embeddings.

        This test documents the violation and will FAIL until fixed.
        The fix is to move trend categorization to embedding phase or use LLM.
        """
        from src.trends import analyze_article

        # Setup tracking
        tracker = CallTracker()
        embedding_service = create_tracking_embedding_service(tracker)

        # Create test article
        article = create_test_article("test-1")

        # Call analyze_article with embedding service
        result = analyze_article(article, embedding_service=embedding_service)

        # ASSERTION: This SHOULD fail because analyze_article uses embeddings
        embedding_count = tracker.get_embedding_count()

        if embedding_count > 0:
            report = tracker.get_report()
            pytest.fail(
                f"KNOWN VIOLATION: analyze_article made {embedding_count} embedding calls!\n"
                f"This function is called during LLM phase but uses embeddings.\n"
                f"FIX: Move to embedding phase or use LLM-based categorization.\n\n"
                f"{report}"
            )
