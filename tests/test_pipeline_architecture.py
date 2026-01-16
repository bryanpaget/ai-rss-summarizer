"""Tests for pipeline architecture invariants.

SIMPLE APPROACH:
1. Global tracker logs every LLM and embedding call
2. Run the full pipeline
3. Parse the log and validate:
   - Model switches should be 2-3 MAX (embed -> llm -> embed)
   - No back-and-forth within a logical phase
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# =============================================================================
# Global Call Logger
# =============================================================================


class PipelineCallLogger:
    """
    Global logger for all LLM and embedding calls.

    Logs format: [(timestamp, call_type, method_name, context), ...]

    At end of test, parse to validate architectural rules.
    """

    def __init__(self):
        self.calls = []
        self.enabled = True

    def log(self, call_type: str, method: str, context: str = ""):
        """Log a call. call_type is 'LLM' or 'EMBED'."""
        if self.enabled:
            self.calls.append({
                "time": datetime.now().isoformat(),
                "type": call_type,
                "method": method,
                "context": context,
            })

    def clear(self):
        """Clear all logged calls."""
        self.calls = []

    def get_sequence(self) -> list[str]:
        """Get just the type sequence: ['LLM', 'LLM', 'EMBED', 'EMBED', ...]"""
        return [c["type"] for c in self.calls]

    def count_switches(self) -> int:
        """
        Count number of model switches (LLM->EMBED or EMBED->LLM transitions).

        A healthy pipeline has exactly 2 switches:
        - EMBED (pre-embed phase)
        - -> LLM (llm phase)
        - -> EMBED (post-embed phase)
        """
        seq = self.get_sequence()
        if len(seq) < 2:
            return 0

        switches = 0
        for i in range(1, len(seq)):
            if seq[i] != seq[i-1]:
                switches += 1
        return switches

    def get_switch_points(self) -> list[dict]:
        """Get details about where switches happen."""
        seq = self.get_sequence()
        switch_points = []

        for i in range(1, len(seq)):
            if seq[i] != seq[i-1]:
                switch_points.append({
                    "position": i,
                    "from": seq[i-1],
                    "to": seq[i],
                    "from_call": self.calls[i-1],
                    "to_call": self.calls[i],
                })
        return switch_points

    def count_by_type(self) -> dict:
        """Count calls by type."""
        counts = {"LLM": 0, "EMBED": 0}
        for c in self.calls:
            counts[c["type"]] = counts.get(c["type"], 0) + 1
        return counts

    def get_full_report(self) -> str:
        """Generate human-readable report."""
        lines = ["=" * 60]
        lines.append("PIPELINE CALL LOG REPORT")
        lines.append("=" * 60)

        counts = self.count_by_type()
        lines.append(f"Total LLM calls: {counts['LLM']}")
        lines.append(f"Total EMBED calls: {counts['EMBED']}")
        lines.append(f"Total switches: {self.count_switches()}")
        lines.append("")

        lines.append("CALL SEQUENCE:")
        for i, c in enumerate(self.calls):
            lines.append(f"  {i+1:3d}. [{c['type']:5s}] {c['method']} - {c['context']}")

        lines.append("")
        lines.append("SWITCH POINTS:")
        for sp in self.get_switch_points():
            lines.append(f"  Position {sp['position']}: {sp['from']} -> {sp['to']}")
            lines.append(f"    Before: {sp['from_call']['method']}")
            lines.append(f"    After:  {sp['to_call']['method']}")

        lines.append("=" * 60)
        return "\n".join(lines)


# Global instance
_logger = PipelineCallLogger()


def get_logger() -> PipelineCallLogger:
    """Get the global pipeline call logger."""
    return _logger


# =============================================================================
# Instrumented Mocks
# =============================================================================


def create_logging_provider(logger: PipelineCallLogger):
    """Create an LLM provider that logs all calls."""
    provider = MagicMock()
    provider.name = "LoggingProvider"

    def log_summarize(prompt, max_length=None):
        # Extract context from prompt
        context = prompt[:80].replace("\n", " ") + "..."
        logger.log("LLM", "summarize", context)
        # Return valid JSON
        return '[{"content": "Test insight", "type": "technical", "confidence": "high", "reason": "test", "entities": []}]'

    def log_generate(prompt, max_tokens=None):
        context = prompt[:80].replace("\n", " ") + "..."
        logger.log("LLM", "generate", context)
        # Handle different prompt types
        if "chunk" in prompt.lower() or "divide" in prompt.lower():
            return '["chunk text here"]'
        return '[]'

    provider.summarize.side_effect = log_summarize
    provider.generate.side_effect = log_generate

    return provider


def create_logging_embedding_service(logger: PipelineCallLogger):
    """Create an embedding service that logs all calls."""
    service = MagicMock()

    def log_embed_text(text):
        context = (text[:50] + "...") if len(text) > 50 else text
        logger.log("EMBED", "embed_text", context)
        result = MagicMock()
        result.vector = [0.1] * 384
        return result

    def log_embed_story(story):
        context = f"story:{story.id}" if hasattr(story, 'id') else str(story)[:30]
        logger.log("EMBED", "embed_story", context)
        result = MagicMock()
        result.vector = [0.1] * 384
        return result

    service.embed_text.side_effect = log_embed_text
    service.embed_story.side_effect = log_embed_story
    service.is_available.return_value = True
    service.get_provider_info.return_value = {"provider": "logging", "model": "test"}
    service.get_embedding.return_value = None  # No cached embeddings
    service.save_embedding.return_value = None
    service.cosine_similarity.return_value = 0.5
    service.find_similar.return_value = []

    return service


def create_test_article(article_id: str = "test-1"):
    """Create a test article with sufficient content."""
    article = MagicMock()
    article.id = article_id
    article.title = f"Test Article {article_id}"
    article.content = "This is test content. " * 20  # ~400 chars
    article.summary = None
    article.trend_tags = None
    article.signal_tags = None
    article.link = f"https://example.com/{article_id}"
    article.published = None
    article.story_id = None
    return article


# =============================================================================
# ARCHITECTURE TESTS
# =============================================================================


class TestPipelineModelSwitching:
    """Test that pipeline doesn't switch models excessively."""

    def test_max_two_switches_in_full_pipeline(self):
        """
        RULE: Full pipeline should have at most 2-3 model switches.

        Expected pattern:
        - Phase 2 (pre-embed): EMBED calls
        - Phase 3 (LLM): LLM calls
        - Phase 4 (embed): EMBED calls

        That's 2 switches: EMBED->LLM and LLM->EMBED

        This test WILL FAIL if current code interleaves calls.
        """
        from src.report import _run_llm_phase
        from src.knowledge import TripleExtractionResult

        # Fresh logger
        logger = PipelineCallLogger()
        logger.clear()

        provider = create_logging_provider(logger)
        embedding_service = create_logging_embedding_service(logger)

        # Setup mocks
        mock_kb = MagicMock()
        mock_kb.get_insights.return_value = []
        mock_kb.get_triples.return_value = []
        mock_kb.query_triples_pattern.return_value = []

        mock_storage = MagicMock()
        mock_storage.get_embedding.return_value = None
        mock_storage.update_trends.return_value = None
        mock_storage.update_signal_tags.return_value = None
        mock_storage.mark_as_analyzed.return_value = None

        mock_tagger = MagicMock()
        mock_tagger.tag_article.return_value = MagicMock(
            to_json=lambda: '{}',
            to_compact_string=lambda: ""
        )

        articles = [create_test_article(f"art-{i}") for i in range(2)]

        stats = {
            "processed": 0, "insights": 0, "triples": 0,
            "triples_new": 0, "triples_existing": 0,
            "connections": 0, "errors": 0,
        }

        # Run LLM phase with real function calls (not mocked)
        with patch('src.report.SignalTagger') as mock_tagger_class:
            mock_tagger_class.return_value = mock_tagger

            _run_llm_phase(
                articles=articles,
                storage=mock_storage,
                kb=mock_kb,
                provider=provider,
                stats=stats,
                embedding_service=embedding_service,
                limit=0,
            )

        # VALIDATE
        switches = logger.count_switches()

        # LLM phase should have 0 switches (all LLM or all nothing)
        # If there are switches, embeddings are being called during LLM phase
        if switches > 0:
            report = logger.get_full_report()
            pytest.fail(
                f"ARCHITECTURE VIOLATION: LLM phase had {switches} model switches!\n"
                f"LLM phase should have ZERO switches (no embedding calls).\n\n"
                f"{report}"
            )

    def test_llm_phase_no_embedding_calls(self):
        """
        RULE: LLM phase must make ZERO embedding calls.

        This test WILL FAIL because analyze_article() uses embeddings.
        """
        from src.report import _run_llm_phase
        from src.knowledge import TripleExtractionResult

        logger = PipelineCallLogger()
        logger.clear()

        provider = create_logging_provider(logger)
        embedding_service = create_logging_embedding_service(logger)

        mock_kb = MagicMock()
        mock_kb.get_insights.return_value = []
        mock_kb.get_triples.return_value = []
        mock_kb.query_triples_pattern.return_value = []

        mock_storage = MagicMock()
        mock_storage.get_embedding.return_value = None
        mock_storage.update_trends.return_value = None
        mock_storage.update_signal_tags.return_value = None
        mock_storage.mark_as_analyzed.return_value = None

        mock_tagger = MagicMock()
        mock_tagger.tag_article.return_value = MagicMock(
            to_json=lambda: '{}',
            to_compact_string=lambda: ""
        )

        articles = [create_test_article("single-article")]

        stats = {
            "processed": 0, "insights": 0, "triples": 0,
            "triples_new": 0, "triples_existing": 0,
            "connections": 0, "errors": 0,
        }

        with patch('src.report.SignalTagger') as mock_tagger_class:
            mock_tagger_class.return_value = mock_tagger

            _run_llm_phase(
                articles=articles,
                storage=mock_storage,
                kb=mock_kb,
                provider=provider,
                stats=stats,
                embedding_service=embedding_service,
                limit=0,
            )

        # COUNT EMBEDDING CALLS
        counts = logger.count_by_type()
        embed_calls = counts.get("EMBED", 0)

        if embed_calls > 0:
            report = logger.get_full_report()
            pytest.fail(
                f"ARCHITECTURE VIOLATION: LLM phase made {embed_calls} embedding calls!\n"
                f"Expected: 0 embedding calls during LLM phase.\n\n"
                f"{report}"
            )

    def test_one_llm_call_per_article(self):
        """
        RULE: Each article should trigger exactly 1 consolidated LLM call.

        This test WILL FAIL because current code does:
        - insights extraction (1 call)
        - semantic chunking (1 call)
        - triple extraction per chunk (N calls)
        - signal tagging (1 call, mocked in this test)

        Should be: 1 call that returns summary + insights + triples + tags
        """
        from src.report import _run_llm_phase
        from src.knowledge import TripleExtractionResult

        logger = PipelineCallLogger()
        logger.clear()

        provider = create_logging_provider(logger)
        embedding_service = create_logging_embedding_service(logger)

        mock_kb = MagicMock()
        mock_kb.get_insights.return_value = []
        mock_kb.get_triples.return_value = []
        mock_kb.query_triples_pattern.return_value = []

        mock_storage = MagicMock()
        mock_storage.get_embedding.return_value = None
        mock_storage.update_trends.return_value = None
        mock_storage.update_signal_tags.return_value = None
        mock_storage.mark_as_analyzed.return_value = None

        mock_tagger = MagicMock()
        mock_tagger.tag_article.return_value = MagicMock(
            to_json=lambda: '{}',
            to_compact_string=lambda: ""
        )

        NUM_ARTICLES = 3
        articles = [create_test_article(f"art-{i}") for i in range(NUM_ARTICLES)]

        stats = {
            "processed": 0, "insights": 0, "triples": 0,
            "triples_new": 0, "triples_existing": 0,
            "connections": 0, "errors": 0,
        }

        with patch('src.report.SignalTagger') as mock_tagger_class:
            mock_tagger_class.return_value = mock_tagger

            _run_llm_phase(
                articles=articles,
                storage=mock_storage,
                kb=mock_kb,
                provider=provider,
                stats=stats,
                embedding_service=embedding_service,
                limit=0,
            )

        # COUNT LLM CALLS
        counts = logger.count_by_type()
        llm_calls = counts.get("LLM", 0)
        expected_calls = NUM_ARTICLES  # 1 per article

        if llm_calls != expected_calls:
            calls_per_article = llm_calls / NUM_ARTICLES
            report = logger.get_full_report()
            pytest.fail(
                f"ARCHITECTURE VIOLATION: Expected {expected_calls} LLM calls "
                f"({NUM_ARTICLES} articles x 1 call each).\n"
                f"Got {llm_calls} calls ({calls_per_article:.1f} per article).\n\n"
                f"{report}"
            )
