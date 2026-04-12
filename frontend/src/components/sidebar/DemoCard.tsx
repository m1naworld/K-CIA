"use client";

import { MetricCard } from "./MetricCard";
import type { DemoCard as DemoCardType } from "@/types/map";

const DemoIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const AGE_LABELS: Record<string, string> = {
  "10": "10대",
  "20": "20대",
  "30": "30대",
  "40": "40대",
  "50": "50대",
  "60+": "60+",
};

interface Props {
  data: DemoCardType;
}

export default function DemoCard({ data }: Props) {
  const maleRatio = data.gender.male ?? 0;
  const femaleRatio = data.gender.female ?? 0;

  return (
    <MetricCard title="인구통계" icon={<DemoIcon />}>
      {/* Gender ratio bar */}
      <div className="mb-3">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="intel-text-primary">
            남성 {(maleRatio * 100).toFixed(1)}%
          </span>
          <span className="intel-text-accent">
            여성 {(femaleRatio * 100).toFixed(1)}%
          </span>
        </div>
        <div className="flex h-2 w-full overflow-hidden rounded-full">
          <div
            className="intel-meter-primary transition-all"
            style={{ width: `${maleRatio * 100}%` }}
          />
          <div
            className="intel-meter-accent transition-all"
            style={{ width: `${femaleRatio * 100}%` }}
          />
        </div>
      </div>

      {/* Age distribution */}
      {data.age_distribution.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] text-slate-500 dark:text-white/40">연령대 분포</p>
          <div className="flex gap-1">
            {data.age_distribution.map((item) => {
              const maxRatio = Math.max(...data.age_distribution.map((d) => d.ratio));
              const height = maxRatio > 0 ? (item.ratio / maxRatio) * 100 : 0;
              const displayHeight = item.ratio > 0 ? Math.max(15, height) : 0;
              const isPeak = item.age_group === data.peak_age_group;
              return (
                <div
                  key={item.age_group}
                  className="group relative flex flex-1 flex-col items-center"
                >
                  <div className="relative h-12 w-full flex items-end">
                    <div
                      className={`w-full rounded-t transition-all ${isPeak
                        ? "intel-meter-accent shadow-md shadow-[hsl(var(--intel-ochre)/0.28)]"
                        : "bg-slate-400/60 dark:bg-slate-500/50"
                        }`}
                      style={{ height: `${displayHeight}%` }}
                    />
                  </div>
                  <span className={`mt-1 text-[9px] ${isPeak ? "intel-text-accent font-bold" : "text-slate-500 dark:text-white/40"}`}>
                    {AGE_LABELS[item.age_group] ?? item.age_group}
                  </span>
                  <div className="pointer-events-none absolute -top-6 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded bg-white px-1.5 py-0.5 text-[10px] text-slate-700 opacity-0 shadow-sm transition-opacity group-hover:opacity-100 dark:bg-gray-800 dark:text-white">
                    {(item.ratio * 100).toFixed(1)}%
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Peak summary */}
      {(data.peak_age_group || data.peak_gender) && (
        <div className="mt-2 flex items-center gap-2 text-[10px] text-slate-500 dark:text-white/50">
          {data.peak_gender && (
            <span>
              주 고객: <span className="text-slate-700 dark:text-white/80">{data.peak_gender}</span>
            </span>
          )}
          {data.peak_age_group && (
            <span>
              <span className="intel-text-accent">{AGE_LABELS[data.peak_age_group] ?? data.peak_age_group}</span>
            </span>
          )}
        </div>
      )}
    </MetricCard>
  );
}
