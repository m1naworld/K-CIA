"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Target } from "lucide-react";

interface ActionItemsCardProps {
  actionItems: string[];
}

export function ActionItemsCard({ actionItems }: ActionItemsCardProps) {
  if (!actionItems || actionItems.length === 0) return null;

  return (
    <Card className="intel-panel-soft text-foreground">
      <CardHeader className="pb-2">
        <CardTitle className="intel-text-success flex items-center gap-2 text-sm font-medium">
          <Target className="h-4 w-4" />
          추천 액션
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ul className="space-y-2">
          {actionItems.map((item, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-xs text-foreground/85"
            >
              <span className="intel-surface-success mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px]">
                {index + 1}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
