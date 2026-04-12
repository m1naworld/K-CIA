"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ListChecks } from "lucide-react";

interface ChecklistCardProps {
  checklist: string[];
}

export function ChecklistCard({ checklist }: ChecklistCardProps) {
  if (!checklist || checklist.length === 0) return null;

  return (
    <Card className="border-[hsl(var(--intel-primary)/0.24)] bg-white/90 text-slate-900 backdrop-blur-sm dark:border-[hsl(var(--intel-primary)/0.3)] dark:bg-gray-900/60 dark:text-white">
      <CardHeader className="pb-2">
        <CardTitle className="intel-text-primary flex items-center gap-2 text-sm font-medium">
          <ListChecks className="h-4 w-4" />
          추가 확인 체크리스트
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ul className="space-y-2">
          {checklist.map((item, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-xs text-slate-700 dark:text-white/80"
            >
              <span className="intel-text-primary mt-0.5">-</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
