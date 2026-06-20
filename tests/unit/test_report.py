"""Unit tests for the ReportBuilder class."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from rag_evaluation_framework.models import EvalResult, MetricScore
from rag_evaluation_framework.report import ReportBuilder, build_report


@pytest.fixture
def sample_result():
    """Create a sample EvalResult for testing."""
    return EvalResult(
        question="What is the capital of France?",
        context=["France is in Europe. Its capital is Paris."],
        answer="The capital of France is Paris.",
        overall_score=0.85,
        faithfulness=MetricScore(
            score=0.90,
            explanation="9/10 claims supported.",
            confidence=0.80,
            details={"claims": [{"claim": "Paris is capital.", "supported": True}]},
        ),
        hallucination_rate=MetricScore(
            score=0.10,
            explanation="Low hallucination rate.",
            confidence=0.90,
            details={
                "claims": [
                    {
                        "claim": "Paris is capital.",
                        "grounded": True,
                        "factual": True,
                        "hallucination_type": "none",
                    }
                ]
            },
        ),
        retrieval_precision=MetricScore(
            score=0.75,
            explanation="3/4 chunks relevant.",
            confidence=0.70,
            details={
                "chunks": [
                    {
                        "chunk_index": 0,
                        "relevant": True,
                        "similarity": 0.85,
                        "preview": "France is...",
                    }
                ]
            },
        ),
        answer_relevance=MetricScore(
            score=0.95,
            explanation="Directly answers the question.",
            confidence=0.90,
        ),
        context_coverage=MetricScore(
            score=0.80,
            explanation="Most context is covered.",
            confidence=0.85,
        ),
        ucm_confidence=MetricScore(
            score=0.70,
            explanation="Moderate consistency.",
            confidence=0.60,
            details={
                "samples": ["Paris", "The capital is Paris."],
                "semantic_consistency": 0.70,
                "lexical_consistency": 0.65,
                "factual_overlap": 0.75,
            },
        ),
        metadata={"llm": "openai/gpt-4o", "metrics_computed": ["all"]},
        latency_ms=150,
    )


class TestReportBuilder:
    """Test suite for ReportBuilder."""

    def test_init(self, sample_result):
        """ReportBuilder initializes with EvalResult."""
        builder = ReportBuilder(sample_result)
        assert builder.result is sample_result

    def test_to_dict(self, sample_result):
        """to_dict returns a dict with expected keys."""
        builder = ReportBuilder(sample_result)
        result = builder.to_dict()
        assert isinstance(result, dict)
        assert result["overall_score"] == 0.85
        assert result["question"] == "What is the capital of France?"
        assert "faithfulness" in result

    def test_to_json(self, sample_result):
        """to_json returns a valid JSON string."""
        builder = ReportBuilder(sample_result)
        result = builder.to_json()
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["overall_score"] == 0.85

    def test_to_json_with_indent(self, sample_result):
        """to_json respects indent parameter."""
        builder = ReportBuilder(sample_result)
        result = builder.to_json(indent=4)
        assert "    " in result

    def test_to_markdown(self, sample_result):
        """to_markdown returns a markdown string."""
        builder = ReportBuilder(sample_result)
        result = builder.to_markdown()
        assert isinstance(result, str)
        assert "RAG Evaluation Framework Report" in result
        assert "Faithfulness" in result
        assert "0.900" in result

    def test_to_html(self, sample_result):
        """to_html returns an HTML string."""
        builder = ReportBuilder(sample_result)
        result = builder.to_html()
        assert isinstance(result, str)
        assert "<html" in result or "<!DOCTYPE html>" in result
        assert "RAG Evaluation Framework Report" in result
        assert "Faithfulness" in result

    def test_to_pdf_fallback_to_html(self, sample_result):
        """to_pdf falls back to HTML when WeasyPrint is unavailable."""
        builder = ReportBuilder(sample_result)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name

        try:
            output = builder.to_pdf(path)
            # Should save as HTML if PDF fails
            if output.endswith(".html"):
                assert Path(output).exists()
                content = Path(output).read_text(encoding="utf-8")
                assert "RAG Evaluation Framework Report" in content
            else:
                assert Path(output).exists()
        finally:
            # Cleanup
            for ext in [".pdf", ".html"]:
                p = path.replace(".pdf", ext)
                if os.path.exists(p):
                    os.unlink(p)

    def test_to_ci_badge_overall(self, sample_result):
        """to_ci_badge generates correct URL for overall_score."""
        builder = ReportBuilder(sample_result)
        url = builder.to_ci_badge("overall_score")
        assert url.startswith("https://img.shields.io/badge/")
        assert "overall" in url
        assert "85" in url
        assert "green" in url

    def test_to_ci_badge_faithfulness(self, sample_result):
        """to_ci_badge generates correct URL for faithfulness."""
        builder = ReportBuilder(sample_result)
        url = builder.to_ci_badge("faithfulness")
        assert "faithfulness" in url

    def test_to_ci_badge_unknown_metric(self, sample_result):
        """to_ci_badge returns empty string for unknown metric."""
        builder = ReportBuilder(sample_result)
        url = builder.to_ci_badge("nonexistent_metric")
        assert url == ""

    def test_to_ci_badge_low_score(self, sample_result):
        """to_ci_badge shows red for low scores."""
        result = EvalResult(
            question="Q",
            context=["C"],
            answer="A",
            overall_score=0.30,
        )
        builder = ReportBuilder(result)
        url = builder.to_ci_badge("overall_score")
        assert "red" in url

    def test_to_ci_badge_medium_score(self, sample_result):
        """to_ci_badge shows orange for medium scores."""
        result = EvalResult(
            question="Q",
            context=["C"],
            answer="A",
            overall_score=0.70,
        )
        builder = ReportBuilder(result)
        url = builder.to_ci_badge("overall_score")
        assert "orange" in url

    def test_summary_stats(self, sample_result):
        """summary_stats returns correct structure."""
        builder = ReportBuilder(sample_result)
        stats = builder.summary_stats()
        assert stats["overall_score"] == 0.85
        assert stats["latency_ms"] == 150
        assert "metrics" in stats
        assert stats["metrics"]["faithfulness"] == 0.90
        assert stats["metrics"]["hallucination_rate"] == 0.10
        assert "llm" in stats


class TestBuildReportFunction:
    """Test suite for the build_report convenience function."""

    def test_build_report_dict(self, sample_result):
        """build_report with format='dict' returns dict."""
        result = build_report(sample_result, format="dict")
        assert isinstance(result, dict)
        assert result["overall_score"] == 0.85

    def test_build_report_json(self, sample_result):
        """build_report with format='json' returns JSON string."""
        result = build_report(sample_result, format="json")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["overall_score"] == 0.85

    def test_build_report_html(self, sample_result):
        """build_report with format='html' returns HTML string."""
        result = build_report(sample_result, format="html")
        assert "RAG Evaluation Framework Report" in result

    def test_build_report_markdown(self, sample_result):
        """build_report with format='markdown' returns markdown string."""
        result = build_report(sample_result, format="markdown")
        assert "RAG Evaluation Framework Report" in result

    def test_build_report_pdf(self, sample_result):
        """build_report with format='pdf' returns path."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            path = tmp.name

        try:
            result = build_report(sample_result, format="pdf", output_path=path)
            assert isinstance(result, str)
        finally:
            for ext in [".pdf", ".html"]:
                p = path.replace(".pdf", ext)
                if os.path.exists(p):
                    os.unlink(p)

    def test_build_report_invalid_format(self, sample_result):
        """build_report with unknown format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format"):
            build_report(sample_result, format="unknown")
