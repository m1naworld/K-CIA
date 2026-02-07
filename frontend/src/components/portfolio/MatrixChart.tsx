"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import type { AssetHealth } from "@/types/map";

interface MatrixChartProps {
  assets: AssetHealth[];
}

export default function MatrixChart({ assets }: MatrixChartProps) {
  if (assets.length === 0) return null;

  const chartData = assets.map((a) => ({
    x: a.demand_z ?? 0,
    y: a.risk_z ?? 0,
    name: a.area_name ?? a.address,
    status: a.health_status,
    score: a.health_score,
  }));

  const statusColor = (status: string) => {
    if (status === "green") return "rgb(16 185 129 / 0.8)";
    if (status === "yellow") return "rgb(245 158 11 / 0.8)";
    return "rgb(239 68 68 / 0.8)";
  };

  return (
    <div>
      <p className="mb-2 text-[10px] text-white/40">성과(수요) vs 리스크 매트릭스</p>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
            <XAxis
              type="number"
              dataKey="x"
              name="수요"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }}
              axisLine={false}
              label={{ value: "수요 Z", position: "insideBottom", offset: -10, fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="리스크"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }}
              axisLine={false}
              label={{ value: "리스크 Z", angle: -90, position: "insideLeft", fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
            />
            <ReferenceLine x={0} stroke="rgba(255,255,255,0.1)" />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17, 24, 39, 0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: "11px",
                color: "white",
              }}
              formatter={(value, name) => {
                return [Number(value).toFixed(1), name ?? ""];
              }}
            />
            <Scatter data={chartData}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={statusColor(entry.status)} r={8} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      {/* Quadrant Labels */}
      <div className="mt-1 grid grid-cols-2 gap-1 text-[9px] text-white/20">
        <span className="text-center">저수요/저리스크</span>
        <span className="text-center">고수요/저리스크</span>
        <span className="text-center">저수요/고리스크</span>
        <span className="text-center">고수요/고리스크</span>
      </div>
    </div>
  );
}
