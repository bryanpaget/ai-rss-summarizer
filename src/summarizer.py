"""Article summarization using LLMs."""

from typing import Optional, Protocol


class SummarizerBackend(Protocol):
    """Protocol for summarizer backends."""

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate a summary of the given text."""
        ...


class SimpleSummarizer:
    """
    Simple extractive summarizer that doesn't require ML models.
    Extracts the first few sentences as a summary.
    """

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Extract first sentences up to max_length characters."""
        if not text:
            return ""

        # Clean up whitespace
        text = " ".join(text.split())

        # If text is short enough, return as-is
        if len(text) <= max_length:
            return text

        # Try to break at sentence boundaries
        sentences = []
        current = ""

        for char in text:
            current += char
            if char in ".!?" and len(current) > 20:
                sentences.append(current.strip())
                current = ""

        # Build summary from sentences
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) + 1 <= max_length:
                summary = (summary + " " + sentence).strip()
            else:
                break

        # If no complete sentences fit, truncate
        if not summary:
            summary = text[: max_length - 3].rsplit(" ", 1)[0] + "..."

        return summary


class TransformerSummarizer:
    """
    Summarizer using HuggingFace transformers.
    Requires: pip install transformers torch
    """

    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        self.model_name = model_name
        self._pipeline = None

    def _load_pipeline(self):
        """Lazy load the pipeline to avoid slow imports."""
        if self._pipeline is None:
            try:
                from transformers import pipeline

                self._pipeline = pipeline("summarization", model=self.model_name)
            except ImportError:
                raise ImportError(
                    "transformers and torch are required for TransformerSummarizer. "
                    "Install with: pip install transformers torch"
                )
        return self._pipeline

    def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate a summary using the transformer model."""
        if not text:
            return ""

        pipeline = self._load_pipeline()

        # BART model has a 1024 token context limit
        # The model will handle truncation internally if needed
        result = pipeline(
            text,
            max_length=max_length,
            min_length=30,
            do_sample=False,
            truncation=True,
        )
        return result[0]["summary_text"]


def get_summarizer(use_llm: bool = False) -> SummarizerBackend:
    """
    Get the appropriate summarizer backend.

    Args:
        use_llm: If True, use transformer-based summarizer (requires ML deps)
    """
    if use_llm:
        return TransformerSummarizer()
    return SimpleSummarizer()


def summarize_articles(
    storage,
    limit: int = 10,
    use_llm: bool = False,
    tag_articles: bool = False,
) -> dict:
    """
    Summarize unsummarized articles in storage.

    Args:
        storage: Storage instance
        limit: Maximum number of articles to summarize
        use_llm: If True, use LLM-based summarizer
        tag_articles: If True, also assign signal tags to articles

    Returns:
        Statistics about the summarization including processed count and errors.
    """
    summarizer = get_summarizer(use_llm)
    articles = storage.get_articles(limit=limit, unsummarized_only=True)

    # Initialize tagger if requested
    tagger = None
    if tag_articles:
        try:
            from .signal_tagger import SignalTagger
            tagger = SignalTagger(use_llm=use_llm)
        except Exception as e:
            # If tagging fails to initialize, continue without it
            pass

    stats = {"processed": 0, "tagged": 0, "errors": []}

    for article in articles:
        try:
            # Generate summary
            summary = summarizer.summarize(article.content)
            storage.update_summary(article.id, summary)
            stats["processed"] += 1

            # Generate tags if enabled
            if tagger:
                try:
                    tags = tagger.tag_article(article)
                    storage.update_signal_tags(article.id, tags.to_json())
                    stats["tagged"] += 1
                except Exception as e:
                    stats["errors"].append(f"Error tagging {article.id}: {str(e)}")

        except Exception as e:
            stats["errors"].append(f"Error summarizing {article.id}: {str(e)}")

    return stats
