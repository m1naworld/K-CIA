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
    <Card className="intel-panel-soft text-foreground">
      <CardHeader className="pb-2">
        <CardTitle className="intel-text-primary flex items-center gap-2 text-sm font-medium">
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
                className="intel-surface-primary rounded-lg border p-3"
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="intel-button-primary flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold">
                    {item.rank}
                  </span>
                  <span className="text-sm font-medium text-foreground">
                    {item.area_name}
                  </span>
                </div>
                <p className="mb-2 text-xs text-muted-foreground">{item.reason}</p>
                {item.metrics && (
                  <div className="flex flex-wrap gap-3 text-xs">
                    {item.metrics.매출 && (
                      <div className="intel-text-success flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        <span>매출 {item.metrics.매출}</span>
                      </div>
                    )}
                    {item.metrics.점포수 && (
                      <div className="intel-text-accent flex items-center gap-1">
                        <Store className="h-3 w-3" />
                        <span>{item.metrics.점포수}</span>
                      </div>
                    )}
                    {item.metrics.유동인구 && (
                      <div className="intel-text-primary flex items-center gap-1">
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
                className="flex items-start gap-2 text-xs text-foreground/85"
              >
                <span className="intel-surface-primary mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px]">
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
