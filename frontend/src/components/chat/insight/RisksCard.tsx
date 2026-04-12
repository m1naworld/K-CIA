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
  high: "intel-text-danger",
  medium: "intel-text-accent",
  low: "intel-text-success",
};

export function RisksCard({ risks }: RisksCardProps) {
  if (!risks || risks.length === 0) return null;

  return (
    <Card className="intel-panel-soft text-foreground">
      <CardHeader className="pb-2">
        <CardTitle className="intel-text-accent flex items-center gap-2 text-sm font-medium">
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
                  <span className="text-foreground/85">{description}</span>
                </div>
                {mitigation && (
                  <span className="ml-4 text-muted-foreground">→ {mitigation}</span>
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
