"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

interface RisksCardProps {
  risks: string[];
}

export function RisksCard({ risks }: RisksCardProps) {
  if (!risks || risks.length === 0) return null;

  return (
    <Card className="border-amber-500/30 bg-gray-900/60 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-amber-400">
          <AlertTriangle className="h-4 w-4" />
          리스크
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <ul className="space-y-2">
          {risks.map((item, index) => (
            <li
              key={index}
              className="flex items-start gap-2 text-xs text-white/80"
            >
              <span className="mt-0.5 text-amber-400">!</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
