"""Test which embedding format produces better semantic similarity.

Compares:
1. Raw article text (current approach)
2. Structured key-value form
3. Natural paragraph summary

We embed each format and measure which produces tighter clusters
for semantically similar content.
"""

import sys
sys.path.insert(0, '.')

from src.embedding_providers import EmbeddingProviderManager
import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Test data: Two related articles about the same topic
ARTICLE_1_RAW = "Russia is recruiting prisoners to fight in Ukraine, offering them early release in exchange for six months of frontline service. The Wagner Group, a private military company with ties to the Kremlin, has been conducting recruitment drives in remote Siberian prisons. Inmates are promised freedom, a monthly salary, and amnesty for their crimes. Human rights groups have condemned the practice, calling it exploitation of vulnerable populations."

ARTICLE_2_RAW = "Private military contractors linked to Russia are offering convicted criminals a path to freedom through combat service in Ukraine. Investigative journalists have documented recruitment sessions at penal colonies across Russia, where prisoners are offered deals: fight for six months and receive a pardon. The Wagner Group, led by Yevgeny Prigozhin, has been the primary organization conducting these operations."

# Unrelated article for comparison
ARTICLE_3_RAW = "Apple announced its latest iPhone model today, featuring improved camera capabilities and a faster processor. The new device includes a titanium frame and USB-C charging port. Pre-orders begin next week with shipping expected in October. Analysts predict strong sales despite the higher price point."


def format_structured(title, summary, entities, signal):
    """Structured key-value format."""
    return f"Title: {title}. Summary: {summary}. Key Entities: {entities}. Signal Type: {signal}."


def format_natural(title, summary, entities, signal):
    """Natural paragraph format."""
    return f"{summary} Key entities involved: {entities}. This is a {signal} report."


def run_test():
    print("Loading embedding provider...")
    manager = EmbeddingProviderManager()
    provider = manager.get_provider()
    print(f"Using: {provider.name}")
    print()

    # Create different formats for Article 1
    formats_1 = {
        "raw": ARTICLE_1_RAW.strip(),
        "structured": format_structured(
            "Russia recruiting prisoners for Ukraine war",
            "Russia offers prisoners early release for 6 months frontline service. Wagner Group recruiting in Siberian prisons.",
            "Russia, Wagner Group, Ukraine, Siberia",
            "investigative, multi-source"
        ),
        "natural": format_natural(
            "Russia recruiting prisoners for Ukraine war",
            "Russia offers prisoners early release for 6 months frontline service. Wagner Group recruiting in Siberian prisons.",
            "Russia, Wagner Group, Ukraine, Siberia",
            "investigative, multi-source"
        ),
    }

    # Create different formats for Article 2 (related to Article 1)
    formats_2 = {
        "raw": ARTICLE_2_RAW.strip(),
        "structured": format_structured(
            "Wagner Group recruits prisoners for Ukraine",
            "Private military contractors offer criminals freedom through combat. Documented recruitment at Russian penal colonies.",
            "Wagner Group, Yevgeny Prigozhin, Russia, Ukraine",
            "investigative, documented"
        ),
        "natural": format_natural(
            "Wagner Group recruits prisoners for Ukraine",
            "Private military contractors offer criminals freedom through combat. Documented recruitment at Russian penal colonies.",
            "Wagner Group, Yevgeny Prigozhin, Russia, Ukraine",
            "investigative, documented"
        ),
    }

    # Article 3 (unrelated) - only need one format for baseline
    article_3_raw = ARTICLE_3_RAW.strip()

    print("Generating embeddings...")

    # Embed all formats
    embeddings_1 = {}
    embeddings_2 = {}

    for name, text in formats_1.items():
        print(f"  Embedding Article 1 ({name})... ", end="")
        embeddings_1[name] = provider.embed(text)
        print(f"{len(embeddings_1[name])} dims")

    for name, text in formats_2.items():
        print(f"  Embedding Article 2 ({name})... ", end="")
        embeddings_2[name] = provider.embed(text)
        print(f"{len(embeddings_2[name])} dims")

    print(f"  Embedding Article 3 (unrelated)... ", end="")
    embedding_3 = provider.embed(article_3_raw)
    print(f"{len(embedding_3)} dims")

    print()
    print("=" * 60)
    print("RESULTS: Similarity between Article 1 and Article 2")
    print("(Higher = better for related articles)")
    print("=" * 60)

    results = {}
    for fmt in ["raw", "structured", "natural"]:
        sim = cosine_similarity(embeddings_1[fmt], embeddings_2[fmt])
        results[fmt] = sim
        print(f"  {fmt:12}: {sim:.4f}")

    print()
    print("=" * 60)
    print("BASELINE: Similarity to unrelated Article 3")
    print("(Lower = better discrimination)")
    print("=" * 60)

    baselines = {}
    for fmt in ["raw", "structured", "natural"]:
        sim = cosine_similarity(embeddings_1[fmt], embedding_3)
        baselines[fmt] = sim
        print(f"  {fmt:12}: {sim:.4f}")

    print()
    print("=" * 60)
    print("SCORE: Related similarity minus unrelated similarity")
    print("(Higher = better overall)")
    print("=" * 60)

    scores = {}
    for fmt in ["raw", "structured", "natural"]:
        score = results[fmt] - baselines[fmt]
        scores[fmt] = score
        print(f"  {fmt:12}: {score:.4f}")

    winner = max(scores, key=scores.get)
    print()
    print(f"WINNER: {winner.upper()}")
    print()

    return scores


if __name__ == "__main__":
    run_test()
