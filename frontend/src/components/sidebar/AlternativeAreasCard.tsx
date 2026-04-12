"use client";

import { Badge } from "@/components/ui/badge";
import { useMapStore } from "@/store/mapStore";
import type { AlternativeArea } from "@/types/map";

interface AlternativeAreasCardProps {
  alternatives: AlternativeArea[];
  currentRiskScore: number | null;
}

export default function AlternativeAreasCard({
  alternatives,
  currentRiskScore,
}: AlternativeAreasCardProps) {
  const { fetchHexDetail, setSelectedHex, setSelectedArea } = useMapStore();

  if (alternatives.length === 0) return null;

  const handleClick = (alt: AlternativeArea) => {
    setSelectedHex(alt.h3_index);
    setSelectedArea(null, alt.area_name, null);
    fetchHexDetail(alt.h3_index);
  };

  const riskBadgeClass = (riskLevel: AlternativeArea["risk_level"]) => {
    if (riskLevel === "Low") return "intel-badge-success";
    if (riskLevel === "Medium") return "intel-badge-accent";
    return "intel-badge-danger";
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-white/[0.02]">
      <div className="mb-3 flex items-center gap-2">
        <svg className="intel-text-primary h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        <h3 className="text-xs font-semibold text-slate-900 dark:text-white">
          대안 구역 추천
        </h3>
      </div>

      <div className="space-y-2">
        {alternatives.map((alt, idx) => (
          <button
            key={alt.h3_index}
            onClick={() => handleClick(alt)}
            className="w-full rounded-md border border-slate-200 p-2.5 text-left transition-colors hover:border-[hsl(var(--intel-primary)/0.4)] hover:bg-[hsl(var(--intel-primary)/0.05)] dark:border-white/10 dark:hover:border-[hsl(var(--intel-primary)/0.28)] dark:hover:bg-[hsl(var(--intel-primary)/0.08)]"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="intel-surface-primary flex h-5 w-5 items-center justify-center rounded-full border text-[10px] font-bold">
                  {idx + 1}
                </span>
                <span className="text-xs font-medium text-slate-900 dark:text-white">
                  {alt.area_name ?? alt.h3_index.slice(-6)}
                </span>
              </div>
              <Badge
                variant="outline"
                className={`${riskBadgeClass(alt.risk_level)} text-[10px]`}
              >
                {alt.risk_score.toFixed(1)}
              </Badge>
            </div>

            {/* Comparison metrics */}
            <div className="mt-2 grid grid-cols-4 gap-1 text-center">
              <div>
                <p className="text-[9px] text-slate-400 dark:text-white/30">유동</p>
                <p className="text-[10px] font-medium text-slate-700 dark:text-white/70">
                  {alt.flow_total ? `${(alt.flow_total / 10000).toFixed(0)}만` : "—"}
                </p>
              </div>
              <div>
                <p className="text-[9px] text-slate-400 dark:text-white/30">매출</p>
                <p className="text-[10px] font-medium text-slate-700 dark:text-white/70">
                  {alt.sales_amt ? `${(alt.sales_amt / 100000000).toFixed(1)}억` : "—"}
                </p>
              </div>
              <div>
                <p className="text-[9px] text-slate-400 dark:text-white/30">점포</p>
                <p className="text-[10px] font-medium text-slate-700 dark:text-white/70">
                  {alt.store_cnt ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-[9px] text-slate-400 dark:text-white/30">폐업률</p>
                <p className="text-[10px] font-medium text-slate-700 dark:text-white/70">
                  {alt.close_rate !== null ? `${(alt.close_rate * 100).toFixed(1)}%` : "—"}
                </p>
              </div>
            </div>

            {/* Risk improvement indicator */}
            {currentRiskScore !== null && (
              <div className="intel-text-success mt-1.5 flex items-center gap-1 text-[10px]">
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
                <span>
                  리스크 {(currentRiskScore - alt.risk_score).toFixed(1)}p 낮음
                </span>
              </div>
            )}
          </button>
        ))}
      </div>

      <p className="mt-2 text-[9px] text-slate-400 dark:text-white/25">
        클릭하면 해당 구역으로 이동합니다
      </p>
    </div>
  );
}
