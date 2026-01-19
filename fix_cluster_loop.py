#!/usr/bin/env python3
"""Modify cluster processing loop to use chunking"""

with open('src/report.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_loop = '''        for cluster in batch_clusters:
            prompt = build_cluster_analysis_prompt(cluster)
            if prompt:
                handle = gateway.submit_text(prompt, temperature=0.3)
                cluster_handles.append((cluster, handle))
                total_llm_calls += 1'''

new_loop = '''        for cluster in batch_clusters:
            # Chunk large clusters to prevent timeouts
            chunks = chunk_large_cluster(cluster)
            for chunk in chunks:
                prompt = build_cluster_analysis_prompt(chunk)
                if prompt:
                    handle = gateway.submit_text(prompt, temperature=0.3)
                    cluster_handles.append((chunk, handle))
                    total_llm_calls += 1'''

if old_loop in content:
    content = content.replace(old_loop, new_loop)
    with open('src/report.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Modified cluster loop to use chunking")
else:
    print("ERROR: Pattern not found")
