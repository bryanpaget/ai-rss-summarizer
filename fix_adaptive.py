#!/usr/bin/env python3
"""Replace static chunking with adaptive retry"""

with open('src/report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace static chunking with adaptive approach
old_chunk = '''# Maximum insights per cluster to avoid timeout (based on empirical testing)
# Large clusters get chunked into smaller pieces
MAX_INSIGHTS_PER_CLUSTER = 15


def chunk_large_cluster(cluster: list, max_size: int = MAX_INSIGHTS_PER_CLUSTER) -> list[list]:
    """Split large clusters into smaller chunks to prevent LLM timeouts.

    Args:
        cluster: List of (insight, embedding) tuples
        max_size: Maximum insights per chunk

    Returns:
        List of cluster chunks (each chunk is a list of (insight, embedding) tuples)
    """
    if len(cluster) <= max_size:
        return [cluster]

    # Split into chunks, preserving pairs
    chunks = []
    for i in range(0, len(cluster), max_size):
        chunk = cluster[i:i + max_size]
        if len(chunk) >= 2:  # Need at least 2 insights for analysis
            chunks.append(chunk)

    return chunks if chunks else [cluster[:max_size]]'''

new_chunk = '''# Adaptive cluster sizing - learns system capacity through retry
# Start optimistic, shrink on timeout, track what works
_learned_max_cluster_size = 50  # Start optimistic, will shrink on failures
_min_cluster_size = 5  # Don't go below this


def split_cluster_in_half(cluster: list) -> list[list]:
    """Split a cluster into two halves for retry after timeout.

    Args:
        cluster: List of (insight, embedding) tuples

    Returns:
        List of two cluster halves (or single cluster if too small to split)
    """
    if len(cluster) <= _min_cluster_size:
        return [cluster]  # Can't split further

    mid = len(cluster) // 2
    first_half = cluster[:mid]
    second_half = cluster[mid:]

    result = []
    if len(first_half) >= 2:
        result.append(first_half)
    if len(second_half) >= 2:
        result.append(second_half)

    return result if result else [cluster]


def update_learned_max_size(failed_size: int):
    """Update learned max size after a timeout failure."""
    global _learned_max_cluster_size
    # Shrink to 75% of failed size (not half, to find sweet spot faster)
    new_max = max(_min_cluster_size, int(failed_size * 0.75))
    if new_max < _learned_max_cluster_size:
        _learned_max_cluster_size = new_max
        console.print(f"      [yellow]Learned: max cluster size now {_learned_max_cluster_size}[/yellow]")


def chunk_large_cluster(cluster: list, max_size: int = None) -> list[list]:
    """Split large clusters based on learned system capacity.

    Args:
        cluster: List of (insight, embedding) tuples
        max_size: Override max size (uses learned size if None)

    Returns:
        List of cluster chunks
    """
    if max_size is None:
        max_size = _learned_max_cluster_size

    if len(cluster) <= max_size:
        return [cluster]

    # Split into chunks based on learned capacity
    chunks = []
    for i in range(0, len(cluster), max_size):
        chunk = cluster[i:i + max_size]
        if len(chunk) >= 2:
            chunks.append(chunk)

    return chunks if chunks else [cluster[:max_size]]'''

if old_chunk in content:
    content = content.replace(old_chunk, new_chunk)
    print("Replaced chunking with adaptive approach")
else:
    print("ERROR: Old chunk pattern not found")
    exit(1)

with open('src/report.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS")
