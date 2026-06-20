"use client";

import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import { getReports, ReportSummary } from "@/lib/api";

interface TrendDataPoint {
  date: string;
  faithfulness: number;
  hallucination: number;
  retrieval: number;
  relevance: number;
  coverage: number;
  ucm: number;
  count: number;
}

const METRICS_CONFIG = [
  { key: "faithfulness", label: "Faithfulness", color: "#6366f1", sourceKey: "faithfulness_score" as const },
  { key: "hallucination", label: "Hallucination (inverted)", color: "#ef4444", sourceKey: "hallucination_rate" as const },
  { key: "retrieval", label: "Retrieval Precision", color: "#10b981", sourceKey: "retrieval_precision" as const },
  { key: "relevance", label: "Answer Relevance", color: "#f59e0b", sourceKey: "answer_relevance" as const },
  { key: "coverage", label: "Context Coverage", color: "#8b5cf6", sourceKey: "context_coverage" as const },
  { key: "ucm", label: "UCM Confidence", color: "#06b6d4", sourceKey: "ucm_score" as const },
];

function aggregateTrends(reports: ReportSummary[]): TrendDataPoint[] {
  // Group by date (YYYY-MM-DD)
  const byDate = new Map<string, {
    faithfulness: number[]; hallucination: number[]; retrieval: number[];
    relevance: number[]; coverage: number[]; ucm: number[];
  }>();

  for (const r of reports) {
    if (!r.created_at) continue;
    const dateKey = r.created_at.slice(0, 10); // "2026-06-05"

    if (!byDate.has(dateKey)) {
      byDate.set(dateKey, {
        faithfulness: [], hallucination: [], retrieval: [],
        relevance: [], coverage: [], ucm: [],
      });
    }

    const bucket = byDate.get(dateKey)!;
    if (r.faithfulness_score !== null) bucket.faithfulness.push(r.faithfulness_score);
    if (r.hallucination_rate !== null) bucket.hallucination.push(r.hallucination_rate);
    if (r.retrieval_precision !== null) bucket.retrieval.push(r.retrieval_precision);
    if (r.answer_relevance !== null) bucket.relevance.push(r.answer_relevance);
    if (r.context_coverage !== null) bucket.coverage.push(r.context_coverage);
    if (r.ucm_score !== null) bucket.ucm.push(r.ucm_score);
  }

  // Compute averages
  const avg = (arr: number[]) =>
    arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

  const points: TrendDataPoint[] = [];
  for (const [date, vals] of byDate) {
    points.push({
      date: date.slice(5), // "06-05"
      faithfulness: avg(vals.faithfulness),
      hallucination: avg(vals.hallucination),
      retrieval: avg(vals.retrieval),
      relevance: avg(vals.relevance),
      coverage: avg(vals.coverage),
      ucm: avg(vals.ucm),
      count: Math.max(
        vals.faithfulness.length, vals.hallucination.length,
        vals.retrieval.length, vals.relevance.length,
        vals.coverage.length, vals.ucm.length
      ),
    });
  }

  // Sort by date
  points.sort((a, b) => a.date.localeCompare(b.date));
  return points;
}

function computeSummaryStats(data: TrendDataPoint[]) {
  if (data.length === 0) {
    return {
      bestMetric: "",
      bestAvg: 0,
      worstMetric: "",
      worstAvg: 0,
      trend: "",
      trendPct: 0,
    };
  }

  const avgs: Record<string, number> = {};
  for (const m of METRICS_CONFIG) {
    const values = data.map((d) => (d as any)[m.key]).filter((v: number) => v > 0);
    avgs[m.label] = values.length > 0
      ? values.reduce((a: number, b: number) => a + b, 0) / values.length
      : 0;
  }

  const bestEntry = Object.entries(avgs).sort(([, a], [, b]) => b - a)[0];
  const worstEntry = Object.entries(avgs).sort(([, a], [, b]) => a - b)[0];

  // Trend: compare first half vs second half of the overall scores
  const scores = data.map((d) => {
    const vals = METRICS_CONFIG.map((m) => (d as any)[m.key] as number).filter((v) => v > 0);
    return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  }).filter((v) => v > 0);

  let trend = "";
  let trendPct = 0;
  if (scores.length >= 4) {
    const mid = Math.floor(scores.length / 2);
    const firstHalf = scores.slice(0, mid).reduce((a, b) => a + b, 0) / mid;
    const secondHalf = scores.slice(mid).reduce((a, b) => a + b, 0) / (scores.length - mid);
    trendPct = ((secondHalf - firstHalf) / firstHalf) * 100;
    trend = trendPct > 0 ? "↗ Improving" : trendPct < 0 ? "↘ Declining" : "→ Stable";
  }

  return {
    bestMetric: bestEntry ? bestEntry[0] : "",
    bestAvg: bestEntry ? bestEntry[1] : 0,
    worstMetric: worstEntry ? worstEntry[0] : "",
    worstAvg: worstEntry ? worstEntry[1] : 0,
    trend,
    trendPct,
  };
}

export default function TrendsPage() {
  const [trendData, setTrendData] = useState<TrendDataPoint[]>([]);
  const [selectedMetrics, setSelectedMetrics] = useState(METRICS_CONFIG.map((m) => m.key));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const reports = await getReports(500, 0);
        const aggregated = aggregateTrends(reports);
        setTrendData(aggregated);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load trends");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const toggleMetric = (key: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const stats = computeSummaryStats(trendData);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-3" />
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading trends...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Score Trends</h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Monitor how your RAG system metrics evolve over time.
          {trendData.length > 0 && (
            <span className="text-xs ml-2 text-slate-400">
              ({trendData.reduce((s, d) => s + d.count, 0)} evaluations across {trendData.length} days)
            </span>
          )}
        </p>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Metric Toggle */}
      <div className="flex flex-wrap gap-2">
        {METRICS_CONFIG.map((m) => (
          <button
            key={m.key}
            onClick={() => toggleMetric(m.key)}
            className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors border"
            style={{
              backgroundColor: selectedMetrics.includes(m.key) ? `${m.color}15` : undefined,
              color: selectedMetrics.includes(m.key) ? m.color : undefined,
              borderColor: selectedMetrics.includes(m.key) ? m.color : "rgb(226 232 240)",
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Line Chart */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4">
          Scores Over Time
          {trendData.length === 0 && !loading && (
            <span className="text-sm font-normal text-slate-400 ml-2">
              (no evaluation data yet)
            </span>
          )}
        </h2>
        <div className="h-80">
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.3} />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis domain={[0, 1]} stroke="#94a3b8" fontSize={12} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "none",
                    borderRadius: "8px",
                    color: "#f1f5f9",
                  }}
                  formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
                />
                <Legend />
                {METRICS_CONFIG.filter((m) => selectedMetrics.includes(m.key)).map((m) => (
                  <Line
                    key={m.key}
                    type="monotone"
                    dataKey={m.key}
                    name={m.label}
                    stroke={m.color}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-400 text-sm">
              {!loading && "Run some evaluations to see trends here."}
            </div>
          )}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card p-5">
          <p className="text-sm text-slate-500 dark:text-slate-400">Best Performing</p>
          <p className="text-lg font-bold mt-1 text-emerald-600 dark:text-emerald-400">
            {stats.bestMetric}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Avg: {(stats.bestAvg * 100).toFixed(1)}%
          </p>
        </div>
        <div className="card p-5">
          <p className="text-sm text-slate-500 dark:text-slate-400">Needs Improvement</p>
          <p className="text-lg font-bold mt-1 text-amber-600 dark:text-amber-400">
            {stats.worstMetric}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Avg: {(stats.worstAvg * 100).toFixed(1)}%
          </p>
        </div>
        <div className="card p-5">
          <p className="text-sm text-slate-500 dark:text-slate-400">Overall Trend</p>
          <p className={`text-lg font-bold mt-1 ${
            stats.trendPct > 0
              ? "text-emerald-600 dark:text-emerald-400"
              : stats.trendPct < 0
              ? "text-red-600 dark:text-red-400"
              : "text-slate-600 dark:text-slate-400"
          }`}>
            {stats.trend}
          </p>
          {stats.trendPct !== 0 && (
            <p className="text-xs text-slate-400 mt-1">
              {stats.trendPct > 0 ? "+" : ""}{stats.trendPct.toFixed(1)}% this period
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
