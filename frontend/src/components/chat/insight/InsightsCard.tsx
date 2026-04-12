"use client";

import { Lightbulb } from "lucide-react";

interface InsightsCardProps {
  insights: string[];
}

export function InsightsCard({ insights }: InsightsCardProps) {
  if (!insights || insights.length === 0) return null;

  return (
    <div className="intel-surface-accent rounded-lg border p-3 text-foreground">
      <div className="intel-text-accent mb-2 flex items-center gap-2 text-xs font-medium">
        <Lightbulb className="h-3.5 w-3.5" />
        <span>인사이트</span>
      </div>
      <ul className="space-y-2">
        {insights.map((insight, idx) => (
          <li
            key={idx}
            className="flex gap-2 text-sm text-foreground/85"
          >
            <span className="intel-text-accent">•</span>
            <span>{insight}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
