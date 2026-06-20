"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface MetricRadarProps {
  data: Array<{ metric: string; score: number }>;
  height?: number;
}

export default function MetricRadar({ data, height = 300 }: MetricRadarProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data}>
        <PolarGrid stroke="#334155" strokeDasharray="3 3" />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fontSize: 11, fill: "#94a3b8" }}
        />
        <PolarRadiusAxis
          angle={30}
          domain={[0, 100]}
          tick={{ fontSize: 10, fill: "#94a3b8" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1e293b",
            border: "none",
            borderRadius: "8px",
            color: "#f1f5f9",
          }}
          formatter={(value: number) => `${(value).toFixed(0)}%`}
        />
        <Radar
          name="Score"
          dataKey="score"
          stroke="#6366f1"
          fill="#6366f1"
          fillOpacity={0.3}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
