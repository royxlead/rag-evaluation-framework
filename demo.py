"""RAG Evaluation Framework Demo Script

Runs a sample evaluation using the MockLLMAdapter (no API key needed)
and prints complete reports in all supported formats.

Usage:
    python demo.py
"""

import json
import os

# Set UTF-8 encoding for Windows console
if os.name == "nt":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    import sys

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

from pathlib import Path

from rag_evaluation_framework import Evaluator
from rag_evaluation_framework.report import ReportBuilder
from tests.conftest import MockLLMAdapter

print("=" * 65)
print("  RAG Evaluation Framework Demo -- Production-Grade RAG Evaluation")
print("=" * 65)
print()

# -- 1. Create Evaluator with Mock Adapter -------------------
print(">> Initializing Evaluator with MockLLMAdapter...")
evaluator = Evaluator(llm="ollama/llama3", cache=True)
evaluator._adapter = MockLLMAdapter()
print("   [OK] Evaluator ready (model=ollama/llama3, cache=enabled)")
print()

# -- 2. Define Sample RAG Data --------------------------------
sample_question = "What is the capital of France?"
sample_context = [
    "France is a country in Western Europe.",
    "Its capital is Paris, which is located on the Seine River.",
    "Paris is one of the world's major cultural and financial centers.",
]
sample_answer = "The capital of France is Paris, located on the Seine River."

print(">> Sample RAG data:")
print(f"   Question: {sample_question}")
print(f"   Context chunks: {len(sample_context)}")
print(f"   Answer: {sample_answer}")
print()

# -- 3. Run Evaluation ----------------------------------------
print(">> Running evaluation (all 6 metrics)...")
print()

result = evaluator.score(
    question=sample_question,
    context=sample_context,
    answer=sample_answer,
)

print(f"   [OK] Evaluation complete in {result.latency_ms}ms")
print(f"   [OK] Result ID: {result.id[:16]}...")
print()

# -- 4. Print Score Overview ----------------------------------
print("=" * 65)
print("  SCORE OVERVIEW")
print("=" * 65)

metrics_table = [
    ("Faithfulness", result.faithfulness.score, result.faithfulness.confidence),
    ("Hallucination Rate", result.hallucination_rate.score,
     result.hallucination_rate.confidence),
    ("Retrieval Precision", result.retrieval_precision.score,
     result.retrieval_precision.confidence),
    ("Answer Relevance", result.answer_relevance.score,
     result.answer_relevance.confidence),
    ("Context Coverage", result.context_coverage.score,
     result.context_coverage.confidence),
    ("UCM Confidence", result.ucm_confidence.score,
     result.ucm_confidence.confidence),
]

# Header
print(f"  {'Metric':<22} {'Score':>8} {'Conf':>6}  Bar")
print(f"  {'-'*22} {'-'*8} {'-'*6}  {'-'*25}")

# Rows
for name, score, confidence in metrics_table:
    bar = "#" * int(score * 20) + "." * (20 - int(score * 20))
    print(f"  {name:<22} {score:>7.3f} {confidence:>5.2f}  |{bar}|  {(score*100):.0f}%")

print()
print(f"  {'-'*22} {'-'*8} {'-'*6}  {'-'*25}")
print(f"  {'OVERALL':<22} {result.overall_score:>7.3f}")
print()

# -- 5. Detailed Metric Breakdown -----------------------------
print("=" * 65)
print("  METRIC DETAILS")
print("=" * 65)
print()

# 5a. Faithfulness
print(f"  [1] Faithfulness  --  Score: {result.faithfulness.score:.3f}")
print(f"       {result.faithfulness.explanation}")
claims = result.faithfulness.details.get("claims", [])
if claims:
    for c in claims[:5]:
        icon = "[OK]" if c.get("supported") else "[--]"
        print(f"       {icon}  {c.get('claim', '')[:80]}")
print()

# 5b. Hallucination
print(f"  [2] Hallucination Rate  --  Score: {result.hallucination_rate.score:.3f}")
print(f"       {result.hallucination_rate.explanation}")
hallu_claims = result.hallucination_rate.details.get("claims", [])
if hallu_claims:
    for c in hallu_claims[:5]:
        icon = "[OK]" if c.get("grounded") else "[--]"
        htype = c.get("hallucination_type", "unknown")
        print(f"       {icon}  [{htype:>7}]  {c.get('claim', '')[:60]}")
print()

# 5c. Retrieval Precision
print(f"  [3] Retrieval Precision  --  Score: {result.retrieval_precision.score:.3f}")
print(f"       {result.retrieval_precision.explanation}")
chunks = result.retrieval_precision.details.get("chunks", [])
for ch in chunks[:5]:
    rel = "[OK]" if ch.get("relevant") else "[--]"
    preview = ch.get("preview", "")[:50]
    print(
        f"       {rel}  chunk {ch.get('chunk_index', 0)}"
        f" sim={ch.get('similarity', 0):.3f}: {preview}"
    )
print()

# 5d. Answer Relevance
print(f"  [4] Answer Relevance  --  Score: {result.answer_relevance.score:.3f}")
print(f"       {result.answer_relevance.explanation}")
print()

# 5e. Context Coverage
print(f"  [5] Context Coverage  --  Score: {result.context_coverage.score:.3f}")
print(f"       {result.context_coverage.explanation}")
print()

# 5f. UCM Confidence
print(f"  [6] UCM Confidence  --  Score: {result.ucm_confidence.score:.3f}")
print(f"       {result.ucm_confidence.explanation}")
samples = result.ucm_confidence.details.get("samples", [])
if samples:
    print(f"       Generated samples ({len(samples)}):")
    for i, s in enumerate(samples[:3]):
        print(f"         [{i+1}] {s[:80]}")
    print(
        "       Semantic consistency:"
        f" {result.ucm_confidence.details.get('semantic_consistency', 0):.3f}"
    )
    print(
        "       Lexical consistency: "
        f" {result.ucm_confidence.details.get('lexical_consistency', 0):.3f}"
    )
    print(
        "       Factual claim overlap:"
        f" {result.ucm_confidence.details.get('factual_overlap', 0):.3f}"
    )
print()

# -- 6. Report Generation -------------------------------------
print("=" * 65)
print("  REPORT GENERATION (all formats)")
print("=" * 65)
print()

builder = ReportBuilder(result)

# 6a. Dict Report
report_dict = result.report(format="dict")
print(f"  [DICT]  Dict report keys: {list(report_dict.keys())}")
print()

# 6b. JSON Report
json_report = result.report(format="json")
report_path_json = Path("demo_report.json")
report_path_json.write_text(json_report, encoding="utf-8")
json_size = len(json_report)
print(f"  [JSON]  Saved to demo_report.json  ({json_size} chars)")
# Print a snippet
json_parsed = json.loads(json_report)
print(f"          overall_score: {json_parsed['overall_score']}")
print(f"          faithfulness:  {json_parsed['faithfulness']['score']}")
print(f"          hallucination: {json_parsed['hallucination_rate']['score']}")
print()

# 6c. Markdown Report
md_report = result.report(format="markdown")
report_path_md = Path("demo_report.md")
report_path_md.write_text(md_report, encoding="utf-8")
print(f"  [MD]    Saved to demo_report.md  ({len(md_report)} chars)")
# Print first few lines
for line in md_report.splitlines()[:5]:
    print(f"          {line}")
print()

# 6d. HTML Report
html_report = result.report(format="html")
report_path_html = Path("demo_report.html")
report_path_html.write_text(html_report, encoding="utf-8")
html_size = len(html_report)
print(f"  [HTML]  Saved to demo_report.html  ({html_size} chars)")
# Extract title from HTML
title_start = html_report.find("<title>")
title_end = html_report.find("</title>")
if title_start >= 0 and title_end >= 0:
    print(f"          Title: {html_report[title_start+7:title_end]}")
print()

# 6e. PDF Report
print("  [PDF]   Generating...")
try:
    pdf_path = str(Path("demo_report.pdf").resolve())
    result_path = builder.to_pdf(pdf_path)
    print(f"  [PDF]   Saved to {result_path}")
except Exception as e:
    print(f"  [PDF]   Skipped: {e}")
print()

# -- 7. CI Badge ----------------------------------------------
print("=" * 65)
print("  CI BADGE GENERATION")
print("=" * 65)
print()
badge_url = builder.to_ci_badge("overall_score")
print(f"  Overall score badge: {badge_url}")
badge_faith = builder.to_ci_badge("faithfulness")
print(f"  Faithfulness badge:  {badge_faith}")
print()

# -- 8. Batch Evaluation Demo ---------------------------------
print("=" * 65)
print("  BATCH EVALUATION DEMO")
print("=" * 65)
print()

batch_items = [
    {
        "question": "What is the capital of Germany?",
        "context": ["Germany's capital is Berlin."],
        "answer": "Berlin",
    },
    {
        "question": "What is the currency of Japan?",
        "context": ["The Japanese Yen (JPY) is Japan's currency."],
        "answer": "The Japanese Yen",
    },
    {
        "question": "Who wrote Romeo and Juliet?",
        "context": ["William Shakespeare wrote Romeo and Juliet."],
        "answer": "William Shakespeare",
    },
    {
        "question": "What is the speed of light?",
        "context": ["Light travels at 299,792,458 m/s in a vacuum."],
        "answer": "299,792,458 m/s",
    },
]

print(f">> Evaluating {len(batch_items)} items in batch...")
batch_results = evaluator.batch_score(batch_items)

print(f"   {'Question':<35} {'Overall':>8} {'Faith':>7} {'Hallu':>7}")
print(f"   {'-'*35} {'-'*8} {'-'*7} {'-'*7}")
for r in batch_results:
    q_short = r.question[:33] + ".." if len(r.question) > 33 else r.question
    print(
        f"   {q_short:<35}"
        f" {r.overall_score:>7.3f}"
        f" {r.faithfulness.score:>6.3f}"
        f" {r.hallucination_rate.score:>6.3f}"
    )

avg_overall = sum(r.overall_score for r in batch_results) / len(batch_results)
print(f"   {'-'*35} {'-'*8} {'-'*7} {'-'*7}")
print(f"   {'AVERAGE':<35} {avg_overall:>7.3f}")
print()

# -- 9. Comparison Demo ---------------------------------------
print("=" * 65)
print("  COMPARISON DEMO")
print("=" * 65)
print()

print(">> Comparing first two batch results...")
comparison = evaluator.compare(batch_results[0], batch_results[1])
print(f"   Verdict: {comparison.verdict}")
print("   Score deltas:")
for metric, delta in comparison.score_deltas.items():
    arrow = "+" if delta > 0 else "-" if delta < 0 else " "
    print(f"     {arrow}  {metric:<22} {delta:+.4f}")
print()

# -- 10. Summary ----------------------------------------------
print("=" * 65)
print("  DEMO COMPLETE")
print("=" * 65)
print()
print("  Generated files:")
print("    demo_report.json   -- Full JSON report")
print("    demo_report.md     -- Markdown report")
print("    demo_report.html   -- HTML report (open in browser)")
print("    demo_report.pdf    -- PDF report (if generated)")
print()
print("  Results summary:")
print(f"    Overall score:     {result.overall_score:.3f}")
print("    Metrics computed:  6/6")
print(f"    Latency:           {result.latency_ms}ms")
print(f"    Samples generated: {len(result.ucm_confidence.details.get('samples', []))}")
print()
print("  Try it for real with:")
print("    evaluator = Evaluator(llm='openai/gpt-4o')")
print("    result = evaluator.score(question, context, answer)")
print()
print("  (This demo used MockLLMAdapter -- no API key was needed)")
