"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { ComparisonResponse } from "@/types/map";
import { MetricCard, WarningList } from "./MetricCard";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface ComparisonCardProps {
  data: ComparisonResponse;
}

const CompareIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
    />
  </svg>
);

function fmtQtr(qtr: string): string {
  if (qtr.length < 5) return qtr;
  return `${qtr.slice(0, 4)} Q${qtr.slice(4)}`;
}

function fmtRate(rate: number | null): string {
  if (rate === null) return "-";
  const pct = rate * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function rateColor(rate: number | null): string {
  if (rate === null) return "text-slate-500 dark:text-white/50";
  return rate >= 0
    ? "text-emerald-600 dark:text-emerald-400"
    : "text-red-600 dark:text-red-400";
}

function fmtAmt(v: number | null): string {
  if (v === null) return "-";
  return `${Math.round(v / 10000).toLocaleString()}만`;
}

function fmtNum(v: number | null): string {
  if (v === null) return "-";
  return v.toLocaleString();
}

export default function ComparisonCard({ data }: ComparisonCardProps) {
  const { before, after, change, warnings } = data;
  const [isDark, setIsDark] = useState(true);
  const axisText = isDark ? "rgba(255,255,255,0.75)" : "#334155";
  const legendText = isDark ? "rgba(255,255,255,0.7)" : "#475569";
  const tooltipText = isDark ? "rgba(255,255,255,0.85)" : "rgba(15,23,42,0.85)";

  useEffect(() => {
    const getTheme = () => document.documentElement.classList.contains("dark");
    const handleThemeChange = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      if (detail === "dark" || detail === "light") {
        setIsDark(detail === "dark");
      } else {
        setIsDark(getTheme());
      }
    };
    setIsDark(getTheme());
    window.addEventListener("theme-change", handleThemeChange);
    return () => window.removeEventListener("theme-change", handleThemeChange);
  }, []);

  const chartDataRaw = [
    {
      name: "매출(만)",
      beforeRaw: before.sales_amt ? Math.round(before.sales_amt / 10000) : 0,
      afterRaw: after.sales_amt ? Math.round(after.sales_amt / 10000) : 0,
      unit: "만",
    },
    {
      name: "유동인구",
      beforeRaw: before.flow_total ?? 0,
      afterRaw: after.flow_total ?? 0,
      unit: "명",
    },
    {
      name: "점포수",
      beforeRaw: before.store_cnt ?? 0,
      afterRaw: after.store_cnt ?? 0,
      unit: "개",
    },
  ];
  const chartData = chartDataRaw.map((item) => {
    const max = Math.max(item.beforeRaw, item.afterRaw, 1);
    return {
      ...item,
      before: Math.round((item.beforeRaw / max) * 100),
      after: Math.round((item.afterRaw / max) * 100),
    };
  });

  return (
    <div className="space-y-3">
      {/* Quarter badges */}
      <div className="flex items-center gap-2">
        <Badge className="border-blue-500/50 bg-blue-500/10 text-xs text-blue-700 dark:text-blue-300">
          Before: {fmtQtr(data.qtr_before)}
        </Badge>
        <span className="text-slate-400 dark:text-white/30">→</span>
        <Badge className="border-violet-500/50 bg-violet-500/10 text-xs text-violet-700 dark:text-violet-300">
          After: {fmtQtr(data.qtr_after)}
        </Badge>
      </div>

      {/* Areas */}
      {data.areas.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {data.areas.map((area) => (
            <Badge
              key={area}
              variant="secondary"
              className="bg-slate-100 text-xs text-slate-600 dark:bg-white/5 dark:text-white/70"
            >
              {area}
            </Badge>
          ))}
        </div>
      )}

      <Separator className="bg-slate-200 dark:bg-white/10" />

      {/* Change rates grid */}
      <MetricCard title="변화율" icon={<CompareIcon />}>
        <div className="grid grid-cols-3 gap-3 py-1">
          <div className="text-center">
            <p className="text-[10px] text-slate-500 dark:text-white/40">매출</p>
            <p className={`text-sm font-semibold ${rateColor(change.sales_change_rate)}`}>
              {fmtRate(change.sales_change_rate)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-[10px] text-slate-500 dark:text-white/40">유동인구</p>
            <p className={`text-sm font-semibold ${rateColor(change.flow_change_rate)}`}>
              {fmtRate(change.flow_change_rate)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-[10px] text-slate-500 dark:text-white/40">점포</p>
            <p className={`text-sm font-semibold ${rateColor(change.store_change_rate)}`}>
              {fmtRate(change.store_change_rate)}
            </p>
          </div>
        </div>

        <Separator className="my-2 bg-slate-200 dark:bg-white/10" />

        {/* Before / After detail rows */}
        <div className="space-y-1">
          <p className="text-[10px] font-medium text-slate-500 dark:text-white/40">상세 비교</p>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-xs text-slate-500 dark:text-white/50">매출</span>
              <span className="text-xs text-slate-700 dark:text-white/70">
               <span className="text-blue-700 dark:text-blue-300">{fmtAmt(before.sales_amt)}</span>
                <span className="mx-1 text-slate-400 dark:text-white/30">→</span>
                <span className="text-violet-700 dark:text-violet-300">{fmtAmt(after.sales_amt)}</span>
              </span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-xs text-slate-500 dark:text-white/50">유동인구</span>
            <span className="text-xs text-slate-700 dark:text-white/70">
              <span className="text-blue-700 dark:text-blue-300">{fmtNum(before.flow_total)}</span>
              <span className="mx-1 text-slate-400 dark:text-white/30">→</span>
              <span className="text-violet-700 dark:text-violet-300">{fmtNum(after.flow_total)}</span>
            </span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-xs text-slate-500 dark:text-white/50">점포수</span>
            <span className="text-xs text-slate-700 dark:text-white/70">
              <span className="text-blue-700 dark:text-blue-300">{fmtNum(before.store_cnt)}</span>
              <span className="mx-1 text-slate-400 dark:text-white/30">→</span>
              <span className="text-violet-700 dark:text-violet-300">{fmtNum(after.store_cnt)}</span>
            </span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-xs text-slate-500 dark:text-white/50">개업</span>
            <span className="text-xs text-slate-700 dark:text-white/70">
              <span className="text-blue-700 dark:text-blue-300">{fmtNum(before.open_cnt)}</span>
              <span className="mx-1 text-slate-400 dark:text-white/30">→</span>
              <span className="text-violet-700 dark:text-violet-300">{fmtNum(after.open_cnt)}</span>
            </span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-xs text-slate-500 dark:text-white/50">폐업</span>
            <span className="text-xs text-slate-700 dark:text-white/70">
              <span className="text-blue-700 dark:text-blue-300">{fmtNum(before.close_cnt)}</span>
              <span className="mx-1 text-slate-400 dark:text-white/30">→</span>
              <span className="text-violet-700 dark:text-violet-300">{fmtNum(after.close_cnt)}</span>
            </span>
          </div>
        </div>

        {/* Dual bar chart */}
        <div className="mt-3 h-36">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 6, right: 18, left: 0, bottom: 0 }}>
              <XAxis
                dataKey="name"
                tick={{ fill: axisText, fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis hide />
              <Tooltip
                contentStyle={{
                  backgroundColor: isDark
                    ? "rgba(17, 24, 39, 0.95)"
                    : "rgba(255,255,255,0.98)",
                  border: isDark
                    ? "1px solid rgba(255,255,255,0.12)"
                    : "1px solid rgba(15,23,42,0.12)",
                  borderRadius: "6px",
                  fontSize: "11px",
                  color: tooltipText,
                }}
                labelStyle={{ color: tooltipText }}
                itemStyle={{ color: tooltipText }}
                formatter={(_, name, props) => {
                  const rawKey = name === "before" ? "beforeRaw" : "afterRaw";
                  const raw = props?.payload?.[rawKey] ?? 0;
                  const unit = props?.payload?.unit ?? "";
                  return [`${raw.toLocaleString()}${unit}`, ""];
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "10px" }}
                formatter={(value) => (
                  <span style={{ color: legendText }}>
                    {value === "before" ? fmtQtr(data.qtr_before) : fmtQtr(data.qtr_after)}
                  </span>
                )}
              />
              <Bar
                dataKey="before"
                fill={isDark ? "#60a5fa" : "#1d4ed8"}
                radius={[2, 2, 0, 0]}
                barSize={18}
              />
              <Bar
                dataKey="after"
                fill={isDark ? "#a78bfa" : "#6d28d9"}
                radius={[2, 2, 0, 0]}
                barSize={18}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Warnings */}
        <WarningList warnings={warnings} />
        {warnings.length === 0 && (
            <p className="mt-2 text-xs text-emerald-600/80 dark:text-emerald-400/80">
              특별한 위험 신호 없음
            </p>
        )}
      </MetricCard>
    </div>
  );
}
