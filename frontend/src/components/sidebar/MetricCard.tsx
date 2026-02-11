"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";

interface MetricCardProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  growthRate?: number | null;
  variant?: "default" | "warning" | "danger";
}

export function MetricCard({
  title,
  icon,
  children,
  growthRate,
  variant = "default",
}: MetricCardProps) {
  const borderColor = {
    default: "border-slate-200 dark:border-white/10",
    warning: "border-amber-500/30",
    danger: "border-red-500/30",
  }[variant];

  return (
    <Card className={`bg-white/90 text-slate-900 dark:bg-gray-900/60 dark:text-white ${borderColor} backdrop-blur-sm`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-white/80">
            {icon}
            {title}
          </CardTitle>
          {growthRate !== undefined && growthRate !== null && (
            <GrowthBadge rate={growthRate} />
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">{children}</CardContent>
    </Card>
  );
}

function GrowthBadge({ rate }: { rate: number }) {
  const isPositive = rate >= 0;
  const pct = rate * 100; // API returns ratio (0.0219 = 2.19%)
  return (
    <Badge
      variant="outline"
      className={`text-xs ${
        isPositive
          ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400"
          : "border-red-500/50 bg-red-500/10 text-red-400"
      }`}
    >
      {isPositive ? "+" : ""}
      {pct.toFixed(1)}%
    </Badge>
  );
}

// Mini chart for QoQ trend
interface MiniChartProps {
  data: { label: string; value: number }[];
  color?: string;
}

export function MiniChart({ data, color = "#60a5fa" }: MiniChartProps) {
  if (!data || data.length === 0) return null;

  return (
    <div className="mt-2 h-12">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`gradient-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="label" hide />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(17, 24, 39, 0.9)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "6px",
              fontSize: "11px",
            }}
            formatter={(value) => [(value as number).toLocaleString(), ""]}
            labelFormatter={(label) => String(label)}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#gradient-${color})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Bar chart for hourly/weekday distribution
interface BarDistributionProps {
  data: Record<string, number> | null;
  labelMap?: Record<string, string>;
}

export function BarDistribution({ data, labelMap }: BarDistributionProps) {
  if (!data) return null;

  const entries = Object.entries(data);
  const maxValue = Math.max(...entries.map(([, v]) => v));

  return (
    <div className="mt-2 flex gap-0.5">
      {entries.map(([key, value]) => {
        const height = maxValue > 0 ? (value / maxValue) * 100 : 0;
        const label = labelMap?.[key] ?? key;
        return (
          <div
            key={key}
            className="group relative flex flex-1 flex-col items-center"
          >
            <div className="relative h-8 w-full">
              <div
                className="absolute bottom-0 w-full rounded-t bg-blue-500/60 transition-all group-hover:bg-blue-400"
                style={{ height: `${height}%` }}
              />
            </div>
            <span className="mt-1 text-[9px] text-slate-500 dark:text-white/40">{label}</span>
            <div className="pointer-events-none absolute -top-6 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded bg-white px-1.5 py-0.5 text-[10px] text-slate-700 opacity-0 shadow-sm transition-opacity group-hover:opacity-100 dark:bg-gray-800 dark:text-white">
              {value.toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Stat row for simple key-value display
interface StatRowProps {
  label: string;
  value: string | number | null;
  unit?: string;
  highlight?: boolean;
}

export function StatRow({ label, value, unit, highlight }: StatRowProps) {
  if (value === null || value === undefined) return null;

  const displayValue =
    typeof value === "number" ? value.toLocaleString() : value;

  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-slate-500 dark:text-white/50">{label}</span>
      <span
        className={`text-sm font-medium ${
          highlight ? "text-amber-500 dark:text-amber-300" : "text-slate-900 dark:text-white"
        }`}
      >
        {displayValue}
        {unit && <span className="ml-0.5 text-xs text-slate-500 dark:text-white/50">{unit}</span>}
      </span>
    </div>
  );
}

// Warning list for risk card
interface WarningListProps {
  warnings: string[];
}

export function WarningList({ warnings }: WarningListProps) {
  if (!warnings || warnings.length === 0) return null;

  return (
    <ul className="mt-2 space-y-1">
      {warnings.map((warning, i) => (
        <li
          key={i}
          className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300/90"
        >
          <span className="mt-0.5">⚠</span>
          <span>{warning}</span>
        </li>
      ))}
    </ul>
  );
}
