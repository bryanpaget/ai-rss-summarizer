#!/usr/bin/env python3
"""Add cluster chunking to report.py"""

with open('src/report.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function definition
marker = 'def build_cluster_analysis_prompt(cluster: list) -> str:'

if marker not in content:
    print("ERROR: Function not found")
    exit(1)

# Insert chunking code before the function
chunk_code = '''# Maximum insights per cluster to avoid timeout (based on empirical testing)
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

    return chunks if chunks else [cluster[:max_size]]


'''

content = content.replace(marker, chunk_code + marker)

with open('src/report.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Added chunk_large_cluster function")
