"""
RAG Evaluation Framework REAL LLM Benchmark Suite (OpenAI GPT-4o)
=================================================================
This script runs RAG Evaluation Framework with a real OpenAI LLM to produce actual
evaluation scores not mock data. Results are saved to JSON and
summarized for inclusion in BENCHMARKS.md.

Prerequisites:
    pip install rag-evaluation-framework openai
    set OPENAI_API_KEY=sk-...

Usage:
    python benchmarks/run_real_benchmarks.py
"""

import json
import os
import sys
import time
from pathlib import Path

from rag_evaluation_framework import Evaluator

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

LLM = "openai/gpt-4o"
api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    print("ERROR: OPENAI_API_KEY environment variable not set!")
    sys.exit(1)

print(f"Using model: {LLM}")
print(f"API key: {api_key[:8]}...{api_key[-4:]}")
print()

# ═══════════════════════════════════════════════════════════════
# TEST 1: Basic Single Evaluation
# ═══════════════════════════════════════════════════════════════

print("=" * 70)
print(" TEST 1: Single Evaluation All 6 Metrics")
print("=" * 70)

evaluator = Evaluator(llm=LLM, cache=True)

test_cases = [
    {
        "name": "France Capital (Perfect)",
        "question": "What is the capital of France?",
        "context": [
            "France is a country in Western Europe.",
            "Its capital is Paris, located on the Seine River.",
            "Paris is a major cultural and financial center."
        ],
        "answer": "The capital of France is Paris, located on the Seine River."
    },
    {
        "name": "France Capital (Hallucinated)",
        "question": "What is the capital of France?",
        "context": [
            "France is a country in Western Europe.",
            "Its capital is Paris, located on the Seine River."
        ],
        "answer": "The capital of France is Lyon, which is famous for its cuisine."
    },
    {
        "name": "Empty Answer",
        "question": "What is the capital of France?",
        "context": ["France's capital is Paris."],
        "answer": ""
    },
    {
        "name": "Off-topic Answer",
        "question": "What is the capital of France?",
        "context": ["France's capital is Paris."],
        "answer": "I like pizza. It's a delicious food."
    },
    {
        "name": "No Context",
        "question": "What is 2+2?",
        "context": [],
        "answer": "2 + 2 equals 4."
    },
]

results = []
for case in test_cases:
    print(f"\n -- {case['name']}")
    print(f" Q: {case['question']}")
    print(f" A: {case['answer'][:60]}...")

    t0 = time.time()
    try:
        r = evaluator.score(
            question=case['question'],
            context=case['context'],
            answer=case['answer'],
        )
        elapsed = time.time() - t0

        row = {
            "test": case['name'],
            "overall": round(r.overall_score, 4),
            "faithfulness": round(r.faithfulness.score, 4),
            "hallucination": round(r.hallucination_rate.score, 4),
            "retrieval_precision": round(r.retrieval_precision.score, 4),
            "answer_relevance": round(r.answer_relevance.score, 4),
            "context_coverage": round(r.context_coverage.score, 4),
            "ucm_confidence": round(r.ucm_confidence.score, 4),
            "latency_seconds": round(elapsed, 2),
        }
        results.append(row)

        print(f" Overall: {r.overall_score:.3f}")
        print(f" Faithful: {r.faithfulness.score:.3f}")
        print(f" Halluc: {r.hallucination_rate.score:.3f}")
        print(f" Retrieval:{r.retrieval_precision.score:.3f}")
        print(f" Relevance:{r.answer_relevance.score:.3f}")
        print(f" Coverage: {r.context_coverage.score:.3f}")
        print(f" UCM: {r.ucm_confidence.score:.3f}")
        print(f" {elapsed:.2f}s")

    except Exception as e:
        print(f" Error: {e}")
        results.append({"test": case['name'], "error": str(e)})

# ═══════════════════════════════════════════════════════════════
# TEST 2: Batch Evaluation
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print(" TEST 2: Batch Evaluation (4 items)")
print(f"{'=' * 70}")

batch_items = [
    {"question": "What is the capital of Germany?",
     "context": ["Germany's capital is Berlin."], "answer": "Berlin"},
    {"question": "What is the currency of Japan?",
     "context": ["The Japanese Yen is Japan's currency."], "answer": "The Japanese Yen"},
    {"question": "Who wrote Romeo and Juliet?",
     "context": ["William Shakespeare wrote Romeo and Juliet."], "answer": "William Shakespeare"},
    {"question": "What is the speed of light?",
     "context": ["Light travels at 299,792,458 m/s in vacuum."], "answer": "299,792,458 m/s"},
]

t0 = time.time()
batch_results = evaluator.batch_score(batch_items)
batch_time = time.time() - t0

batch_data = []
for i, r in enumerate(batch_results):
    batch_data.append({
        "question": batch_items[i]["question"],
        "overall": round(r.overall_score, 4),
        "faithfulness": round(r.faithfulness.score, 4),
        "hallucination": round(r.hallucination_rate.score, 4),
        "latency_ms": r.latency_ms,
    })
    print(f" {batch_items[i]['question'][:40]:<40} Overall: {r.overall_score:.3f}")

print(f"\n Batch time: {batch_time:.2f}s total, {batch_time/4:.2f}s per item")

# ═══════════════════════════════════════════════════════════════
# TEST 3: Comparison
# ═══════════════════════════════════════════════════════════════

print(f"\n{'=' * 70}")
print(" TEST 3: Comparison Engine")
print(f"{'=' * 70}")

comp = evaluator.compare(batch_results[0], batch_results[1])
print(f" Verdict: {comp.verdict}")
for metric, delta in comp.score_deltas.items():
    print(f" {metric}: {delta:+.4f}")

# ═══════════════════════════════════════════════════════════════
# SAVE RESULTS
# ═══════════════════════════════════════════════════════════════

output = {
    "meta": {
        "model": LLM,
        "api_key_prefix": api_key[:8],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    },
    "single_evaluations": results,
    "batch": {
        "items": batch_data,
        "total_time_seconds": round(batch_time, 2),
        "avg_time_per_item_seconds": round(batch_time / len(batch_items), 2),
    },
    "comparison": {
        "verdict": comp.verdict,
        "score_deltas": comp.score_deltas,
    },
}

out_path = Path("benchmarks/real_benchmark_results.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
print(f"\nResults saved to {out_path}")
