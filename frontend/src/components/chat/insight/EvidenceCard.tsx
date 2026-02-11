"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle } from "lucide-react";

interface EvidenceCardProps {
  evidence: string[];
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <Card className="border-emerald-500/30 bg-white/90 text-slate-900 backdrop-blur-sm dark:bg-gray-900/60 dark:text-white">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-emerald-400">
          <CheckCircle className="h-4 w-4" />
          근거
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ul className="space-y-2">
          {evidence.map((item, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-xs text-slate-700 dark:text-white/80"
            >
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] text-emerald-400">
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
