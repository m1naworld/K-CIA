"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

interface RiskItem {
  level: "high" | "medium" | "low";
  description: string;
  mitigation?: string;
  data?: string;
}

interface RisksCardProps {
  risks: (string | RiskItem)[];
}

const levelColors = {
  high: "text-red-400",
  medium: "text-amber-400",
  low: "text-yellow-400",
};

export function RisksCard({ risks }: RisksCardProps) {
  if (!risks || risks.length === 0) return null;

  return (
    <Card className="border-amber-500/30 bg-white/90 text-slate-900 backdrop-blur-sm dark:bg-gray-900/60 dark:text-white">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-amber-400">
          <AlertTriangle className="h-4 w-4" />
          리스크
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ul className="space-y-2">
          {risks.map((item, index) => {
            const isObject = typeof item === "object";
            const description = isObject ? item.description : item;
            const level = isObject ? item.level : "medium";
            const mitigation = isObject ? item.mitigation : undefined;

            return (
              <li
                key={index}
                className="flex flex-col gap-1 text-xs"
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-0.5 ${levelColors[level]}`}>!</span>
                  <span className="text-slate-700 dark:text-white/80">{description}</span>
                </div>
                {mitigation && (
                  <span className="ml-4 text-slate-500 dark:text-white/50">→ {mitigation}</span>
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
