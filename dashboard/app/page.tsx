"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { getReports, ReportSummary } from "@/lib/api";

    interface RecentEval {
    id: string;
    question: string;
    overall_score: number;
    created_at: string;
}

    interface HomeStats {
    totalEvals: number;
    avgFaithfulness: number | null;
    avgHallucination: number | null;
}

    function computeStats(reports: ReportSummary[]): HomeStats {
    const totalEvals = reports.length;

// Last 7 days for averages
const sevenDaysAgo = new Date();
sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const recent = reports.filter((r) => {
    if (!r.created_at) return false;
    return new Date(r.created_at) >= sevenDaysAgo;
});

const faithScores = recent
.map((r) => r.faithfulness_score)
.filter((s): s is number => s !== null);
const halluScores = recent
.map((r) => r.hallucination_rate)
.filter((s): s is number => s !== null);

const avgFaithfulness =
faithScores.length > 0
? faithScores.reduce((a, b) => a + b, 0) / faithScores.length
: null;

const avgHallucination =
halluScores.length > 0
? halluScores.reduce((a, b) => a + b, 0) / halluScores.length
: null;

return { totalEvals, avgFaithfulness, avgHallucination };
}

    function computeScoreDistribution(reports: ReportSummary[]) {
    const buckets = [
    { range: "0.0-0.2", min: 0.0, max: 0.2, count: 0 },
    { range: "0.2-0.4", min: 0.2, max: 0.4, count: 0 },
    { range: "0.4-0.6", min: 0.4, max: 0.6, count: 0 },
    { range: "0.6-0.8", min: 0.6, max: 0.8, count: 0 },
    { range: "0.8-1.0", min: 0.8, max: 1.0, count: 0 },
    ];

    for (const r of reports) {
    const score = r.overall_score;
    for (const bucket of buckets) {
    if (score >= bucket.min && (score < bucket.max || score === 1.0)) {
    bucket.count++;
    break;
    }
    }
}

return buckets.map(({ range, count }) => ({ range, count }));
}

    export default function HomePage() {
    const [reports, setReports] = useState<ReportSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
    async function load() {
    try {
    const data = await getReports(50, 0);
    setReports(data);
    } catch (e) {
    setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
    setLoading(false);
    }
    }
    load();
}, []);

const stats = computeStats(reports);
const scoreDistribution = computeScoreDistribution(reports);

// Top 5 most recent
    const recentEvals: RecentEval[] = reports.slice(0, 5).map((r) => ({
    id: r.id,
    question: r.question,
    overall_score: r.overall_score,
    created_at: r.created_at,
}));

    if (loading) {
    return (
    <div className="flex items-center justify-center h-64">
    <div className="text-center">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-3" />
    <p className="text-sm text-slate-500 dark:text-slate-400">Loading dashboard...</p>
    </div>
    </div>
    );
}

    return (
    <div className="space-y-8">
    {/* Header */}
    <div>
    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
    RAG Evaluation Framework Dashboard
    </h1>
    <p className="mt-1 text-slate-500 dark:text-slate-400">
    Production-grade RAG evaluation monitor, analyze, and improve your RAG system.
    </p>
    </div>

    {error && (
    <div className="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 px-4 py-3 rounded-lg text-sm">
    {error}
    </div>
)}

{/* Summary Stats */}
<div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
<StatCard
title="Total Evaluations"
value={stats.totalEvals.toString()}
subtitle="All time"
icon="📊"
/>
<StatCard
title="Avg Faithfulness"
    value={
    stats.avgFaithfulness !== null
    ? `${(stats.avgFaithfulness * 100).toFixed(0)}%`
    : ""
}
subtitle={stats.avgFaithfulness !== null ? "Last 7 days" : "No recent data"}
icon="🎯"
score={stats.avgFaithfulness ?? undefined}
/>
<StatCard
title="Avg Hallucination Rate"
    value={
    stats.avgHallucination !== null
    ? `${(stats.avgHallucination * 100).toFixed(0)}%`
    : ""
}
subtitle={stats.avgHallucination !== null ? "Last 7 days" : "No recent data"}
icon="⚠️"
score={stats.avgHallucination !== null ? 1 - stats.avgHallucination : undefined}
invert
/>
</div>

{/* Recent Evaluations */}
<div className="card p-6">
<div className="flex items-center justify-between mb-4">
<h2 className="text-lg font-semibold">
Recent Evaluations
    {reports.length === 0 && (
    <span className="text-sm font-normal text-slate-400 ml-2">(no data yet)</span>
)}
</h2>
<Link href="/evaluate" className="btn-primary text-sm">
New Evaluation
</Link>
</div>
    {reports.length > 0 ? (
    <div className="overflow-x-auto">
    <table className="w-full text-sm">
    <thead>
    <tr className="border-b border-slate-200 dark:border-slate-700">
    <th className="text-left py-3 px-2 font-medium text-slate-500 dark:text-slate-400">Question</th>
    <th className="text-right py-3 px-2 font-medium text-slate-500 dark:text-slate-400">Score</th>
    <th className="text-right py-3 px-2 font-medium text-slate-500 dark:text-slate-400">Date</th>
    <th className="text-right py-3 px-2 font-medium text-slate-500 dark:text-slate-400"></th>
    </tr>
    </thead>
    <tbody>
    {reports.slice(0, 10).map((eval_) => (
    <tr
    key={eval_.id}
    className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
    >
    <td className="py-3 px-2 max-w-xs truncate">{eval_.question}</td>
    <td className="py-3 px-2 text-right">
    <ScoreBadge score={eval_.overall_score} />
    </td>
    <td className="py-3 px-2 text-right text-slate-500 dark:text-slate-400">
    {eval_.created_at
    ? new Date(eval_.created_at).toLocaleDateString()
    : ""}
    </td>
    <td className="py-3 px-2 text-right">
    <Link
    href={`/reports/${eval_.id}`}
    className="text-indigo-600 dark:text-indigo-400 hover:underline text-xs font-medium"
    >
    View Report →
    </Link>
    </td>
    </tr>
    ))}
    </tbody>
    </table>
    </div>
    ) : (
    <div className="text-center py-8 text-slate-400 text-sm">
    {!loading && "Run your first evaluation to see data here."}
    </div>
)}
</div>

{/* Score Distribution */}
<div className="card p-6">
<h2 className="text-lg font-semibold mb-4">
Score Distribution
    {reports.length === 0 && (
    <span className="text-sm font-normal text-slate-400 ml-2">(no data yet)</span>
)}
</h2>
<div className="h-64">
    {reports.length > 0 ? (
    <ResponsiveContainer width="100%" height="100%">
    <BarChart data={scoreDistribution}>
    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
    <XAxis dataKey="range" stroke="#94a3b8" fontSize={12} />
    <YAxis stroke="#94a3b8" fontSize={12} allowDecimals={false} />
    <Tooltip
    contentStyle={{
    backgroundColor: "#1e293b",
    border: "none",
    borderRadius: "8px",
    color: "#f1f5f9",
    }}
    />
    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
    </BarChart>
    </ResponsiveContainer>
    ) : (
    <div className="flex items-center justify-center h-full text-slate-400 text-sm">
    {!loading && "No data to display yet."}
    </div>
)}
</div>
</div>
</div>
);
}

    function StatCard({
    title,
    value,
    subtitle,
    icon,
    score,
    invert,
    }: {
    title: string;
    value: string;
    subtitle: string;
    icon: string;
    score?: number;
    invert?: boolean;
    }) {
    const effectiveScore = invert ? (score ? 1 - score : 0) : score;
    const colorClass =
    effectiveScore !== undefined
    ? effectiveScore >= 0.8
    ? "score-green"
    : effectiveScore >= 0.6
    ? "score-amber"
    : "score-red"
    : "";

    return (
    <div className="card p-6">
    <div className="flex items-start justify-between">
    <div>
    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
    <p className="text-3xl font-bold mt-1">{value}</p>
    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">{subtitle}</p>
    </div>
    <span className="text-2xl">{icon}</span>
    </div>
    {score !== undefined && (
    <div className="mt-3">
    <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
    <div
    className={`h-full rounded-full transition-all duration-500 ${
    effectiveScore! >= 0.8
    ? "bg-emerald-500"
    : effectiveScore! >= 0.6
    ? "bg-amber-500"
    : "bg-red-500"
    }`}
    style={{ width: `${(effectiveScore! * 100).toFixed(0)}%` }}
    />
    </div>
    </div>
    )}
    </div>
);
}

    function ScoreBadge({ score }: { score: number }) {
    const colorClass =
    score >= 0.8
    ? "score-green"
    : score >= 0.6
    ? "score-amber"
    : "score-red";
    return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
    {(score * 100).toFixed(0)}%
    </span>
    );
}
