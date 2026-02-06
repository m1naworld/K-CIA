"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ListChecks } from "lucide-react";

interface ChecklistCardProps {
  checklist: string[];
}

export function ChecklistCard({ checklist }: ChecklistCardProps) {
  if (!checklist || checklist.length === 0) return null;

  return (
    <Card className="border-violet-500/30 bg-gray-900/60 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-violet-400">
          <ListChecks className="h-4 w-4" />
          추가 확인 체크리스트
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ul className="space-y-2">
          {checklist.map((item, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-xs text-white/80"
            >
              <span className="mt-0.5 text-violet-400">-</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
