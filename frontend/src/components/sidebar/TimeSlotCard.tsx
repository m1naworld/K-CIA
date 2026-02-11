"use client";

import { MetricCard } from "./MetricCard";
import { Badge } from "@/components/ui/badge";
import type { TimeSlotRecommendation } from "@/types/map";

const ClockIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

interface Props {
  data: TimeSlotRecommendation;
}

export default function TimeSlotCard({ data }: Props) {
  const hasHourly = data.recommendations.length > 0;

  return (
    <MetricCard title="시간대 추천" icon={<ClockIcon />}>
      {/* Peak weekday */}
      {data.peak_weekday && (
        <div className="mb-3 flex items-center gap-2">
          <span className="text-xs text-slate-500 dark:text-white/50">피크 요일</span>
          <Badge
            variant="outline"
            className="border-violet-500/50 bg-violet-500/10 text-xs text-violet-300"
          >
            {data.peak_weekday}요일
          </Badge>
        </div>
      )}

      {/* Hourly distribution */}
      {hasHourly && (
        <div>
          <p className="mb-1 text-[10px] text-slate-500 dark:text-white/40">시간대별 유동인구 비율</p>
          <div className="space-y-1">
            {data.recommendations.map((slot) => {
              const maxRatio = Math.max(...data.recommendations.map((s) => s.flow_ratio));
              const width = maxRatio > 0 ? (slot.flow_ratio / maxRatio) * 100 : 0;
              const isPeak = data.peak_hours.some((h) => {
                const [start, end] = slot.hour_range.split("~").map(Number);
                return h >= start && h < end;
              });
              return (
                <div key={slot.hour_range} className="flex items-center gap-2">
                  <span className="w-10 shrink-0 text-right text-[10px] text-slate-500 dark:text-white/40">
                    {slot.label}
                  </span>
                  <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/5">
                    <div
                      className={`h-full rounded-full transition-all ${
                        isPeak ? "bg-amber-500/70" : "bg-violet-500/40"
                      }`}
                      style={{ width: `${width}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-[10px] text-slate-500 dark:text-white/50">
                    {(slot.flow_ratio * 100).toFixed(0)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* No hourly data fallback */}
      {!hasHourly && data.peak_weekday && (
        <p className="text-xs text-slate-500 dark:text-white/40">
          시간대별 상세 데이터는 추후 업데이트 예정
        </p>
      )}
    </MetricCard>
  );
}
