"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { QuarterComparison } from "@/types/map";

interface CompareChartProps {
  comparisons: QuarterComparison[];
  qtr1: string;
  qtr2: string;
}

const METRIC_LABELS: Record<string, string> = {
  sales_amt: "매출",
  sales_cnt: "결제건수",
  flow_total: "유동인구",
  store_cnt: "점포수",
  open_cnt: "개업",
  close_cnt: "폐업",
};

export default function CompareChart({ comparisons, qtr1, qtr2 }: CompareChartProps) {
  const chartData = comparisons.map((c) => ({
    name: METRIC_LABELS[c.metric] ?? c.metric,
    metric: c.metric,
    change: c.change_rate !== null ? c.change_rate * 100 : 0,
    avg: c.avg_change_rate !== null ? c.avg_change_rate * 100 : 0,
    aboveAvg: c.above_avg,
    qtr1Val: c.qtr1_value,
    qtr2Val: c.qtr2_value,
  }));

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-[10px] text-white/40">증감률 비교</p>
        <p className="text-[10px] text-white/40">
          {qtr1} → {qtr2}
        </p>
      </div>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 50, right: 10, top: 5, bottom: 5 }}>
            <XAxis
              type="number"
              tickFormatter={(v) => `${v.toFixed(0)}%`}
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={45}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(17, 24, 39, 0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: "11px",
                color: "white",
              }}
              formatter={(value, name) => {
                const v = Number(value);
                if (name === "change") return [`${v.toFixed(1)}%`, "증감률"];
                if (name === "avg") return [`${v.toFixed(1)}%`, "성수동 평균"];
                return [v, name ?? ""];
              }}
            />
            <Bar dataKey="change" radius={[0, 4, 4, 0]} barSize={14}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.change >= 0 ? "rgb(16 185 129 / 0.7)" : "rgb(239 68 68 / 0.7)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
