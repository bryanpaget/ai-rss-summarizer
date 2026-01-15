#!/usr/bin/env python3
"""Quality testing harness for multi-task extraction.

Tests whether asking an LLM to do multiple extraction tasks at once
degrades quality compared to doing tasks separately.

Test Design:
- Same article, same tasks
- Variable: tasks per call (1, 2, 3, 6)
- Measures: quality metrics, extraction counts, time taken
- Run multiple times for consistency

Usage:
    python scripts/quality_test_harness.py --article-file sample.txt
    python scripts/quality_test_harness.py --runs 3
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage import Article


@dataclass
class ExtractionResult:
    """Result from a single extraction run."""
    mode: str  # "single", "combined_2", "combined_3", "combined_6"
    insights_count: int
    triples_count: int
    tags_count: int
    has_summary: bool
    time_seconds: float
    raw_output: str = ""


@dataclass
class QualityMetrics:
    """Quality metrics for comparison."""
    insight_specificity: float = 0.0  # How specific/actionable are insights
    triple_accuracy: float = 0.0  # How accurate are relationships
    tag_relevance: float = 0.0  # How relevant are tags
    summary_quality: float = 0.0  # Summary completeness
    overall_score: float = 0.0


@dataclass
class TestRun:
    """Results from a complete test run."""
    article_title: str
    timestamp: str
    results: dict[str, ExtractionResult] = field(default_factory=dict)
    metrics: dict[str, QualityMetrics] = field(default_factory=dict)


def get_sample_article() -> Article:
    """Get a sample article for testing."""
    return Article(
        id="test-article-001",
        feed_id="test-feed",
        title="OpenAI Announces GPT-5 with Revolutionary Capabilities",
        link="https://example.com/gpt5",
        published=datetime.now(),
        summary="OpenAI has announced GPT-5, featuring improved reasoning and multimodal abilities.",
        content="""OpenAI has officially announced GPT-5, the next generation of their large language model series.
The announcement came during a press event in San Francisco, where CEO Sam Altman demonstrated several new capabilities.

Key features of GPT-5 include:
- 10x improvement in reasoning benchmarks compared to GPT-4
- Native multimodal understanding (text, images, audio, video)
- Reduced hallucination rate by 75%
- Context window extended to 1 million tokens
- New "chain of thought" mode for complex problem solving

The model will be available through the API starting next month, with pricing similar to GPT-4 Turbo.
Microsoft, OpenAI's primary investor, announced immediate integration plans for Copilot products.

Industry analysts predict this will accelerate AI adoption across enterprise applications.
Google and Anthropic are expected to respond with their own announcements in coming weeks.

The release has sparked renewed debate about AI safety, with several researchers expressing
concern about the rapid pace of capability improvements. OpenAI stated they have implemented
additional safety measures including improved content filtering and output monitoring.

Enterprise customers report early access testing showed significant improvements in code generation,
data analysis, and document summarization tasks compared to previous models.""",
    )


def extract_single_task(article: Article, task: str, llm_provider) -> dict:
    """Run a single extraction task."""
    prompts = {
        "insights": f"""Extract key insights from this article.

Article: "{article.title}"
Content: {article.content}

Return as JSON array:
[{{"content": "insight text", "type": "technical|tool|statistic|opinion", "confidence": "high|medium|low"}}]

Return ONLY valid JSON.""",

        "triples": f"""Extract factual relationships as subject-predicate-object triples.

Article: "{article.title}"
Content: {article.content}

Return as JSON array:
[{{"subject": "Entity", "predicate": "relationship", "object": "Entity/Value"}}]

Return ONLY valid JSON.""",

        "tags": f"""Generate topic tags for this article.

Article: "{article.title}"
Content: {article.content}

Return as JSON array:
[{{"tag": "topic", "confidence": 0.9}}]

Return ONLY valid JSON.""",

        "summary": f"""Write a 2-3 sentence summary of this article.

Article: "{article.title}"
Content: {article.content}

Return as JSON:
{{"summary": "The summary text..."}}

Return ONLY valid JSON.""",
    }

    prompt = prompts.get(task)
    if not prompt:
        return {}

    try:
        response = llm_provider.generate(prompt, max_tokens=1000)
        from src.schema import parse_json_response
        return parse_json_response(response)
    except Exception as e:
        print(f"  Warning: {task} extraction failed: {e}", file=sys.stderr)
        return {}


def extract_combined(article: Article, tasks: list[str], llm_provider) -> dict:
    """Run multiple extraction tasks in one call."""
    task_instructions = []
    if "insights" in tasks:
        task_instructions.append('- "insights": array of {content, type, confidence}')
    if "triples" in tasks:
        task_instructions.append('- "triples": array of {subject, predicate, object}')
    if "tags" in tasks:
        task_instructions.append('- "tags": array of {tag, confidence}')
    if "summary" in tasks:
        task_instructions.append('- "summary": 2-3 sentence summary string')

    instructions = "\n".join(task_instructions)

    prompt = f"""Analyze this article and extract the following:

Article: "{article.title}"
Content: {article.content}

Return a JSON object with these fields:
{instructions}

Return ONLY valid JSON, no other text."""

    try:
        response = llm_provider.generate(prompt, max_tokens=2000)
        from src.schema import parse_json_response
        return parse_json_response(response)
    except Exception as e:
        print(f"  Warning: Combined extraction failed: {e}", file=sys.stderr)
        return {}


def run_extraction_test(
    article: Article,
    mode: str,
    llm_provider,
) -> ExtractionResult:
    """Run extraction in specified mode and collect results."""
    start_time = time.time()

    if mode == "single":
        # Run each task separately (4 LLM calls)
        insights = extract_single_task(article, "insights", llm_provider)
        triples = extract_single_task(article, "triples", llm_provider)
        tags = extract_single_task(article, "tags", llm_provider)
        summary = extract_single_task(article, "summary", llm_provider)

        result_data = {
            "insights": insights if isinstance(insights, list) else [],
            "triples": triples if isinstance(triples, list) else [],
            "tags": tags if isinstance(tags, list) else [],
            "summary": summary.get("summary", "") if isinstance(summary, dict) else "",
        }

    elif mode == "combined_2":
        # Two calls: (insights + triples), (tags + summary)
        batch1 = extract_combined(article, ["insights", "triples"], llm_provider)
        batch2 = extract_combined(article, ["tags", "summary"], llm_provider)

        result_data = {
            "insights": batch1.get("insights", []),
            "triples": batch1.get("triples", []),
            "tags": batch2.get("tags", []),
            "summary": batch2.get("summary", ""),
        }

    elif mode == "combined_3":
        # Three calls: insights, (triples + tags), summary
        insights = extract_single_task(article, "insights", llm_provider)
        batch = extract_combined(article, ["triples", "tags"], llm_provider)
        summary = extract_single_task(article, "summary", llm_provider)

        result_data = {
            "insights": insights if isinstance(insights, list) else [],
            "triples": batch.get("triples", []),
            "tags": batch.get("tags", []),
            "summary": summary.get("summary", "") if isinstance(summary, dict) else "",
        }

    elif mode == "combined_6":
        # One call: everything together
        result_data = extract_combined(
            article, ["insights", "triples", "tags", "summary"], llm_provider
        )
        if not isinstance(result_data, dict):
            result_data = {}

    else:
        raise ValueError(f"Unknown mode: {mode}")

    elapsed = time.time() - start_time

    return ExtractionResult(
        mode=mode,
        insights_count=len(result_data.get("insights", [])),
        triples_count=len(result_data.get("triples", [])),
        tags_count=len(result_data.get("tags", [])),
        has_summary=bool(result_data.get("summary")),
        time_seconds=elapsed,
        raw_output=json.dumps(result_data, indent=2),
    )


def run_quality_test(
    article: Optional[Article] = None,
    llm_provider=None,
    runs: int = 1,
    output_file: Optional[Path] = None,
) -> list[TestRun]:
    """Run the full quality test suite."""
    if article is None:
        article = get_sample_article()

    if llm_provider is None:
        # Use gateway for LLM access
        from src.gateway import get_gateway
        gateway = get_gateway()
        if not gateway.is_available():
            print("ERROR: LLM gateway not available", file=sys.stderr)
            return []

        class GatewayWrapper:
            def generate(self, prompt: str, max_tokens: int = 1000) -> str:
                return gateway.request_text(prompt)

        llm_provider = GatewayWrapper()

    all_runs = []
    modes = ["single", "combined_2", "combined_3", "combined_6"]

    for run_num in range(runs):
        print(f"\n{'='*60}")
        print(f"TEST RUN {run_num + 1}/{runs}")
        print(f"{'='*60}")

        test_run = TestRun(
            article_title=article.title,
            timestamp=datetime.now().isoformat(),
        )

        for mode in modes:
            print(f"\nRunning mode: {mode}...")
            result = run_extraction_test(article, mode, llm_provider)
            test_run.results[mode] = result

            print(f"  Insights: {result.insights_count}")
            print(f"  Triples: {result.triples_count}")
            print(f"  Tags: {result.tags_count}")
            print(f"  Summary: {'Yes' if result.has_summary else 'No'}")
            print(f"  Time: {result.time_seconds:.2f}s")

        all_runs.append(test_run)

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"\n{'Mode':<15} {'Insights':<10} {'Triples':<10} {'Tags':<8} {'Time':<10}")
    print("-" * 55)

    for mode in modes:
        avg_insights = sum(r.results[mode].insights_count for r in all_runs) / len(all_runs)
        avg_triples = sum(r.results[mode].triples_count for r in all_runs) / len(all_runs)
        avg_tags = sum(r.results[mode].tags_count for r in all_runs) / len(all_runs)
        avg_time = sum(r.results[mode].time_seconds for r in all_runs) / len(all_runs)

        print(f"{mode:<15} {avg_insights:<10.1f} {avg_triples:<10.1f} {avg_tags:<8.1f} {avg_time:<10.2f}s")

    # Save results if requested
    if output_file:
        output_data = []
        for run in all_runs:
            run_data = {
                "article_title": run.article_title,
                "timestamp": run.timestamp,
                "results": {
                    mode: {
                        "mode": r.mode,
                        "insights_count": r.insights_count,
                        "triples_count": r.triples_count,
                        "tags_count": r.tags_count,
                        "has_summary": r.has_summary,
                        "time_seconds": r.time_seconds,
                        "raw_output": r.raw_output,
                    }
                    for mode, r in run.results.items()
                },
            }
            output_data.append(run_data)

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {output_file}")

    return all_runs


def main():
    parser = argparse.ArgumentParser(description="Quality testing harness for multi-task extraction")
    parser.add_argument("--runs", type=int, default=1, help="Number of test runs")
    parser.add_argument("--output", type=Path, help="Output file for results (JSON)")
    parser.add_argument("--article-file", type=Path, help="File containing article text to test")

    args = parser.parse_args()

    article = None
    if args.article_file and args.article_file.exists():
        content = args.article_file.read_text()
        article = Article(
            id="custom-article",
            feed_id="custom",
            title=args.article_file.stem,
            link="",
            published=datetime.now(),
            content=content,
        )

    run_quality_test(
        article=article,
        runs=args.runs,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
