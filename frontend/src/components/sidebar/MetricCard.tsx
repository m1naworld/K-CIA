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
    default: "border-white/10",
    warning: "border-[hsl(var(--intel-ochre)/0.3)]",
    danger: "border-[hsl(var(--intel-danger)/0.3)]",
  }[variant];

  return (
    <Card className={`intel-panel-soft text-foreground ${borderColor} rounded-[1.35rem]`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
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
          ? "intel-badge-primary"
          : "intel-badge-danger"
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

export function MiniChart({ data, color = "#7F1734" }: MiniChartProps) {
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
              backgroundColor: "rgba(8, 15, 29, 0.94)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "12px",
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
                className="intel-meter-primary absolute bottom-0 w-full rounded-t transition-all group-hover:brightness-110"
                style={{ height: `${height}%` }}
              />
            </div>
            <span className="mt-1 text-[9px] text-muted-foreground">{label}</span>
            <div className="pointer-events-none absolute -top-7 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full border border-border/60 bg-popover px-2 py-0.5 text-[10px] text-popover-foreground opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
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
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={`text-sm font-medium ${
          highlight ? "intel-text-accent" : "text-foreground"
        }`}
      >
        {displayValue}
        {unit && <span className="ml-0.5 text-xs text-muted-foreground">{unit}</span>}
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
          className="intel-text-accent flex items-start gap-2 text-xs"
        >
          <span className="mt-0.5">⚠</span>
          <span>{warning}</span>
        </li>
      ))}
    </ul>
  );
}
