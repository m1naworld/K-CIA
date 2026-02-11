"use client";

import { Lightbulb } from "lucide-react";

interface InsightsCardProps {
  insights: string[];
}

export function InsightsCard({ insights }: InsightsCardProps) {
  if (!insights || insights.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-slate-900 dark:text-white">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-amber-400">
        <Lightbulb className="h-3.5 w-3.5" />
        <span>인사이트</span>
      </div>
      <ul className="space-y-2">
        {insights.map((insight, idx) => (
          <li
            key={idx}
            className="flex gap-2 text-sm text-slate-700 dark:text-white/80"
          >
            <span className="text-amber-400">•</span>
            <span>{insight}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
