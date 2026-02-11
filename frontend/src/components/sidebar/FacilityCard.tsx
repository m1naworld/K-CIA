"use client";

import { MetricCard, StatRow } from "./MetricCard";
import type { FacilityCard as FacilityCardType } from "@/types/map";

const FacilityIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
  </svg>
);

interface Props {
  data: FacilityCardType;
}

export default function FacilityCard({ data }: Props) {
  return (
    <MetricCard title="집객시설" icon={<FacilityIcon />}>
      <StatRow label="총 시설 수" value={data.total_count} unit="개" highlight />
      {data.facilities.length > 0 && (
        <div className="mt-2 space-y-1">
          {data.facilities.slice(0, 6).map((f) => (
            <div key={f.facility_type} className="flex items-center justify-between">
              <span className="text-xs text-slate-500 dark:text-white/50">{f.label}</span>
              <span className="text-xs font-medium text-slate-900 dark:text-white">{f.count}</span>
            </div>
          ))}
          {data.facilities.length > 6 && (
            <p className="text-[10px] text-slate-400 dark:text-white/30">
              외 {data.facilities.length - 6}개 유형
            </p>
          )}
        </div>
      )}
    </MetricCard>
  );
}
