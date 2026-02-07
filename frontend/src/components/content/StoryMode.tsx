"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useMapStore } from "@/store/mapStore";
import StoryCutCard from "./StoryCutCard";
import type { StoryResponse } from "@/types/map";

export default function StoryMode() {
  const { selectedHex, selectedAreaName, selectedRealName, quarter } = useMapStore();
  const [goal, setGoal] = useState("location");
  const [loading, setLoading] = useState(false);
  const [storyData, setStoryData] = useState<StoryResponse | null>(null);

  const handleGenerate = async () => {
    if (!selectedHex) return;
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/content/story`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          h3_index: selectedHex,
          message_goal: goal,
          qtr: quarter || undefined,
        }),
      });
      if (!res.ok) throw new Error("Failed");
      const json = await res.json();
      setStoryData(json);
    } catch {
      setStoryData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="bg-gray-900/60 border-white/10 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-white/80">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 4V2m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-4 6h6m2-6v10m0 0l3-3m-3 3l-3-3" />
          </svg>
          4컷 스토리 생성
          {selectedAreaName && (
            <Badge variant="outline" className="text-[10px] text-white/50">
              {selectedRealName ?? selectedAreaName}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {/* Goal Selection */}
        <div>
          <p className="mb-1 text-[10px] text-white/40">메시지 목표</p>
          <Select value={goal} onValueChange={setGoal}>
            <SelectTrigger className="h-8 border-white/20 bg-gray-800 text-xs text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 text-white">
              <SelectItem value="location">입지 추천</SelectItem>
              <SelectItem value="risk">리스크 경고</SelectItem>
              <SelectItem value="operation">운영 최적화</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="w-full text-xs"
          onClick={handleGenerate}
          disabled={!selectedHex || loading}
        >
          {loading ? "생성 중..." : "스토리 생성"}
        </Button>

        {/* Story Result */}
        {storyData && (
          <div className="space-y-2">
            {storyData.cuts.map((cut) => (
              <StoryCutCard key={cut.cut_number} cut={cut} />
            ))}

            {/* Citations */}
            {storyData.citations.length > 0 && (
              <div className="pt-1">
                <p className="mb-1 text-[10px] text-white/30">출처</p>
                <ul className="space-y-0.5">
                  {storyData.citations.map((c, i) => (
                    <li key={i} className="text-[10px] text-white/20">{c}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex items-center justify-between">
              <p className="text-[10px] text-white/20">
                기준: {storyData.data_asof}
              </p>
              <p className="text-[10px] text-amber-400/60">
                {storyData.warning}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
