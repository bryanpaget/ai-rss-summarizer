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

        # Transformers has input length limits, truncate if needed
        # BART has a 1024 token limit, roughly 4 chars per token
        max_input = 4000
        if len(text) > max_input:
            text = text[:max_input]

        try:
            result = pipeline(
                text,
                max_length=max_length,
                min_length=30,
                do_sample=False,
            )
            return result[0]["summary_text"]
        except Exception as e:
            # Fall back to simple summarizer on error
            return SimpleSummarizer().summarize(text, max_length)


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
) -> dict:
    """
    Summarize unsummarized articles in storage.

    Returns statistics about the summarization.
    """
    summarizer = get_summarizer(use_llm)
    articles = storage.get_articles(limit=limit, unsummarized_only=True)

    stats = {"processed": 0, "errors": []}

    for article in articles:
        try:
            summary = summarizer.summarize(article.content)
            storage.update_summary(article.id, summary)
            stats["processed"] += 1
        except Exception as e:
            stats["errors"].append(f"Error summarizing {article.id}: {str(e)}")

    return stats
