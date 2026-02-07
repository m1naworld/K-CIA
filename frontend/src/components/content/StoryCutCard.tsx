"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { StoryCut } from "@/types/map";

interface StoryCutCardProps {
  cut: StoryCut;
}

const CUT_STYLES: Record<number, { border: string; label: string; emoji: string }> = {
  1: { border: "border-blue-500/30", label: "HOOK", emoji: "!" },
  2: { border: "border-emerald-500/30", label: "FACT", emoji: "#" },
  3: { border: "border-amber-500/30", label: "RISK", emoji: "?" },
  4: { border: "border-purple-500/30", label: "ACTION", emoji: ">" },
};

export default function StoryCutCard({ cut }: StoryCutCardProps) {
  const style = CUT_STYLES[cut.cut_number] ?? CUT_STYLES[1];

  return (
    <Card className={`${style.border} bg-gray-900/60 backdrop-blur-sm`}>
      <CardContent className="p-3">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/10 text-[10px] font-bold text-white/60">
              {style.emoji}
            </span>
            <Badge variant="outline" className="text-[10px] text-white/50">
              {style.label}
            </Badge>
          </div>
          {cut.kpi_ref && (
            <Badge variant="outline" className="text-[10px] text-blue-400">
              {cut.kpi_ref}
            </Badge>
          )}
        </div>
        <h4 className="mb-1 text-sm font-semibold text-white/90">{cut.title}</h4>
        <p className="text-xs leading-relaxed text-white/60">{cut.body}</p>
        {cut.visual_hint && (
          <p className="mt-2 text-[10px] text-white/30">
            Visual: {cut.visual_hint}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
