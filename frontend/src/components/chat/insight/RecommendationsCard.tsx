"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Lightbulb, TrendingUp, Store, Users } from "lucide-react";

interface RecommendationItem {
  rank: number;
  area_name: string;
  reason: string;
  metrics?: {
    매출?: string;
    점포수?: string;
    유동인구?: string;
  };
}

interface RecommendationsCardProps {
  recommendations: (string | RecommendationItem)[];
}

export function RecommendationsCard({
  recommendations,
}: RecommendationsCardProps) {
  if (!recommendations || recommendations.length === 0) return null;

  const isStructured = typeof recommendations[0] === "object";

  return (
    <Card className="border-blue-500/30 bg-white/90 text-slate-900 backdrop-blur-sm dark:bg-gray-900/60 dark:text-white">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-blue-400">
          <Lightbulb className="h-4 w-4" />
          추천 상권
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {isStructured ? (
          <div className="space-y-3">
            {(recommendations as RecommendationItem[]).map((item) => (
              <div
                key={item.rank}
                className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white">
                    {item.rank}
                  </span>
                  <span className="text-sm font-medium text-slate-900 dark:text-white">
                    {item.area_name}
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-white/70 mb-2">{item.reason}</p>
                {item.metrics && (
                  <div className="flex flex-wrap gap-3 text-xs">
                    {item.metrics.매출 && (
                      <div className="flex items-center gap-1 text-green-400">
                        <TrendingUp className="h-3 w-3" />
                        <span>매출 {item.metrics.매출}</span>
                      </div>
                    )}
                    {item.metrics.점포수 && (
                      <div className="flex items-center gap-1 text-yellow-400">
                        <Store className="h-3 w-3" />
                        <span>{item.metrics.점포수}</span>
                      </div>
                    )}
                    {item.metrics.유동인구 && (
                      <div className="flex items-center gap-1 text-cyan-400">
                        <Users className="h-3 w-3" />
                        <span>{item.metrics.유동인구}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <ul className="space-y-2">
            {(recommendations as string[]).map((item, index) => (
              <li
                key={index}
                className="flex items-start gap-2 text-xs text-slate-700 dark:text-white/80"
              >
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-[10px] text-blue-400">
                  {index + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
