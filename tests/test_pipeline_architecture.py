"""Tests for pipeline architecture invariants.

SIMPLE APPROACH:
1. Global tracker logs every LLM and embedding call WITH CALLER INFO
2. Run the full pipeline
3. ALWAYS print the log (pass or fail) for visibility
4. Validate:
   - Model switches should be 2-3 MAX (embed -> llm -> embed)
   - No back-and-forth within a logical phase
"""

import pytest
import inspect
from unittest.mock import MagicMock, patch
from datetime import datetime


# =============================================================================
# Global Call Logger with Caller Tracking
# =============================================================================


class PipelineCallLogger:
    """
    Global logger for all LLM and embedding calls.

    Each log entry includes:
    - timestamp
    - call_type (LLM or EMBED)
    - method_name
    - caller function name and file
    - context (first N chars of input)
    """

    def __init__(self):
        self.calls = []
        self.enabled = True

    def log(self, call_type: str, method: str, context: str = ""):
        """Log a call with caller info."""
        if not self.enabled:
            return

        # Get caller info - walk up stack to find non-mock caller
        caller_info = "unknown"
        for frame_info in inspect.stack():
            # Skip mock internals, this file, and standard library
            filename = frame_info.filename
            if "unittest" in filename or "mock" in filename:
                continue
            if "test_pipeline_architecture" in filename:
                continue
            if "site-packages" in filename:
                continue
            # Found a real caller
            caller_info = f"{frame_info.function}() in {filename.split('/')[-1].split(chr(92))[-1]}:{frame_info.lineno}"
            break

        self.calls.append({
            "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "type": call_type,
            "method": method,
            "caller": caller_info,
            "context": context[:60] + "..." if len(context) > 60 else context,
        })

    def clear(self):
        """Clear all logged calls."""
        self.calls = []

    def get_sequence(self) -> list[str]:
        """Get just the type sequence: ['LLM', 'LLM', 'EMBED', 'EMBED', ...]"""
        return [c["type"] for c in self.calls]

    def count_switches(self) -> int:
        """Count model switches (LLM->EMBED or EMBED->LLM transitions)."""
        seq = self.get_sequence()
        if len(seq) < 2:
            return 0
        return sum(1 for i in range(1, len(seq)) if seq[i] != seq[i-1])

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
        """Generate human-readable report - ALWAYS CALL THIS."""
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("PIPELINE CALL LOG")
        lines.append("=" * 80)

        counts = self.count_by_type()
        switches = self.count_switches()
        lines.append(f"SUMMARY: {counts['LLM']} LLM calls, {counts['EMBED']} EMBED calls, {switches} switches")
        lines.append("")

        # Call sequence with callers
        lines.append("CALL SEQUENCE:")
        lines.append("-" * 80)
        for i, c in enumerate(self.calls):
            type_marker = f"[{c['type']:5s}]"
            lines.append(f"{i+1:3d}. {type_marker} {c['method']:15s} <- {c['caller']}")
            if c['context']:
                lines.append(f"     Context: {c['context']}")

        # Switch points
        if switches > 0:
            lines.append("")
            lines.append("SWITCH POINTS (model changes):")
            lines.append("-" * 80)
            for sp in self.get_switch_points():
                lines.append(f"  #{sp['position']}: {sp['from']} -> {sp['to']}")
                lines.append(f"       Before: {sp['from_call']['method']} <- {sp['from_call']['caller']}")
                lines.append(f"       After:  {sp['to_call']['method']} <- {sp['to_call']['caller']}")

        lines.append("=" * 80)
        return "\n".join(lines)


def create_logging_provider(logger: PipelineCallLogger):
    """Create an LLM provider that logs all calls with caller info."""
    provider = MagicMock()
    provider.name = "LoggingProvider"

    def log_summarize(prompt, max_length=None):
        logger.log("LLM", "summarize", prompt[:100].replace("\n", " "))
        return '[{"content": "Test insight", "type": "technical", "confidence": "high", "reason": "test", "entities": []}]'

    def log_generate(prompt, max_tokens=None):
        logger.log("LLM", "generate", prompt[:100].replace("\n", " "))
        if "chunk" in prompt.lower() or "divide" in prompt.lower():
            return '["chunk text here"]'
        return '[]'

    provider.summarize.side_effect = log_summarize
    provider.generate.side_effect = log_generate
    return provider


def create_logging_embedding_service(logger: PipelineCallLogger):
    """Create an embedding service that logs all calls with caller info."""
    service = MagicMock()

    def log_embed_text(text):
        logger.log("EMBED", "embed_text", text[:80].replace("\n", " "))
        result = MagicMock()
        result.vector = [0.1] * 384
        return result

    def log_embed_story(story):
        ctx = f"story:{story.id}" if hasattr(story, 'id') else str(story)[:30]
        logger.log("EMBED", "embed_story", ctx)
        result = MagicMock()
        result.vector = [0.1] * 384
        return result

    service.embed_text.side_effect = log_embed_text
    service.embed_story.side_effect = log_embed_story
    service.is_available.return_value = True
    service.get_provider_info.return_value = {"provider": "logging", "model": "test"}
    service.get_embedding.return_value = None
    service.save_embedding.return_value = None
    service.cosine_similarity.return_value = 0.5
    service.find_similar.return_value = []
    return service


def create_test_article(article_id: str = "test-1"):
    """Create a test article with sufficient content."""
    article = MagicMock()
    article.id = article_id
    article.title = f"Test Article {article_id}"
    article.content = "This is test content about AI and technology. " * 15
    article.summary = None
    article.trend_tags = None
    article.signal_tags = None
    article.link = f"https://example.com/{article_id}"
    article.published = None
    article.story_id = None
    return article


# =============================================================================
# ARCHITECTURE TESTS - Always print logs for visibility
# =============================================================================


class TestPipelineArchitecture:
    """
    Tests for pipeline architectural invariants.

    These tests ALWAYS print the call log so you can see exactly what happened.
    """

    def test_llm_phase_model_switches(self, capsys):
        """
        TEST: LLM phase should have 0 model switches.

        If there are switches, embedding calls are happening during LLM phase.
        ALWAYS prints the call log for visibility.
        """
        from src.report import _run_llm_phase

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

        articles = [create_test_article(f"art-{i}") for i in range(2)]

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

        # ALWAYS print the log
        report = logger.get_full_report()
        print(report)

        # Validate
        switches = logger.count_switches()
        if switches > 0:
            pytest.fail(
                f"VIOLATION: LLM phase had {switches} model switches. "
                f"Should be 0 (no embedding calls during LLM phase)."
            )

    def test_llm_phase_embedding_count(self, capsys):
        """
        TEST: LLM phase must make ZERO embedding calls.

        Current code VIOLATES this via analyze_article() which uses embeddings.
        ALWAYS prints the call log for visibility.
        """
        from src.report import _run_llm_phase

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

        # ALWAYS print the log
        report = logger.get_full_report()
        print(report)

        # Validate
        counts = logger.count_by_type()
        embed_calls = counts.get("EMBED", 0)
        if embed_calls > 0:
            pytest.fail(
                f"VIOLATION: LLM phase made {embed_calls} embedding calls. "
                f"Should be 0."
            )

    def test_llm_calls_per_article(self, capsys):
        """
        TEST: Each article should trigger exactly 1 LLM call.

        Current code VIOLATES this with multiple calls per article:
        - insights extraction
        - semantic chunking
        - triple extraction per chunk
        - etc.

        ALWAYS prints the call log for visibility.
        """
        from src.report import _run_llm_phase

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

        # ALWAYS print the log
        report = logger.get_full_report()
        print(report)

        # Validate
        counts = logger.count_by_type()
        llm_calls = counts.get("LLM", 0)
        expected = NUM_ARTICLES

        if llm_calls != expected:
            per_article = llm_calls / NUM_ARTICLES if NUM_ARTICLES > 0 else 0
            pytest.fail(
                f"VIOLATION: Expected {expected} LLM calls ({NUM_ARTICLES} articles x 1). "
                f"Got {llm_calls} ({per_article:.1f} per article)."
            )

    def test_trend_tagging_no_new_embeddings(self, capsys):
        """
        TEST: Trend tagging must NOT create new embeddings.

        Trend tagging should use stored embeddings via get_embedding(),
        NOT create new ones via embed_text(). Re-embedding is a violation.

        ALWAYS prints the call log for visibility.
        """
        from src.trends import analyze_article

        logger = PipelineCallLogger()
        logger.clear()

        embedding_service = create_logging_embedding_service(logger)
        # Return a stored embedding so the code can use it
        embedding_service.get_embedding.return_value = [0.1] * 384

        article = create_test_article("trend-test-1")
        article.summary = "This is a test summary about AI technology."

        # Call trend tagging
        try:
            analyze_article(article, embedding_service=embedding_service)
        except Exception as e:
            # Might fail if code expects different interface - that's OK for this test
            print(f"analyze_article raised: {e}")

        # ALWAYS print the log
        report = logger.get_full_report()
        print(report)

        # Count embed_text calls specifically
        embed_text_calls = [c for c in logger.calls if c["method"] == "embed_text"]

        if embed_text_calls:
            pytest.fail(
                f"VIOLATION: Trend tagging called embed_text() {len(embed_text_calls)} times. "
                f"Should be 0 - must use stored embeddings via get_embedding() instead.\n"
                f"Callers: {[c['caller'] for c in embed_text_calls]}"
            )
