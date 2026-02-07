"use client";

import { useMapStore } from "@/store/mapStore";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import {
  MetricCard,
  MiniChart,
  StatRow,
  BarDistribution,
  WarningList,
} from "./MetricCard";

// Icons as simple SVGs
const FlowIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
  </svg>
);

const SalesIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const StoreIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

const GrowthIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
);

const RiskIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const RecommendIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const WEEKDAY_LABELS: Record<string, string> = {
  "1": "월",
  "2": "화",
  "3": "수",
  "4": "목",
  "5": "금",
  "6": "토",
  "7": "일",
};

export default function Sidebar() {
  const {
    sidebarOpen,
    hexDetail,
    hexDetailLoading,
    selectedAreaName,
    selectedRealName,
    closeSidebar,
  } = useMapStore();

  if (!sidebarOpen) return null;

  return (
    <div className="flex h-full w-80 flex-col border-l border-white/10 bg-gray-950">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-white">
            {selectedRealName ?? selectedAreaName ?? "구역 상세"}
          </h2>
          {selectedRealName && selectedAreaName && (
            <p className="text-xs text-white/50">{selectedAreaName}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={closeSidebar}
          className="h-8 w-8 p-0 text-white/50 hover:bg-white/10 hover:text-white"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </Button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="space-y-3 p-4">
          {hexDetailLoading ? (
            <LoadingSkeleton />
          ) : hexDetail ? (
            <>
              {/* As-of Badge */}
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="border-blue-500/50 bg-blue-500/10 text-xs text-blue-300"
                >
                  기준: {hexDetail.qtr}
                </Badge>
                <span className="text-[10px] text-white/40">
                  {hexDetail.data_asof}
                </span>
              </div>

              {/* Areas */}
              {hexDetail.areas.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {hexDetail.areas.map((area) => (
                    <Badge
                      key={area}
                      variant="secondary"
                      className="bg-white/5 text-xs text-white/70"
                    >
                      {area}
                    </Badge>
                  ))}
                </div>
              )}

              <Separator className="bg-white/10" />

              {/* Flow Card */}
              <MetricCard
                title="유동인구"
                icon={<FlowIcon />}
                growthRate={hexDetail.growth.flow_growth_rate}
              >
                <StatRow
                  label="분기 총 유동인구"
                  value={hexDetail.flow.flow_total}
                  unit="명"
                  highlight
                />
                {hexDetail.trend.flow.length > 0 && (
                  <MiniChart
                    data={hexDetail.trend.flow
                      .filter((p) => p.value !== null)
                      .map((p) => ({ label: p.qtr, value: p.value! }))}
                    color="#60a5fa"
                  />
                )}
                {hexDetail.flow.flow_by_weekday && (
                  <div className="mt-3">
                    <p className="mb-1 text-[10px] text-white/40">요일별 분포</p>
                    <BarDistribution
                      data={hexDetail.flow.flow_by_weekday}
                      labelMap={WEEKDAY_LABELS}
                    />
                  </div>
                )}
              </MetricCard>

              {/* Sales Card */}
              <MetricCard
                title="매출"
                icon={<SalesIcon />}
                growthRate={hexDetail.growth.sales_growth_rate}
              >
                <StatRow
                  label="분기 총 매출"
                  value={
                    hexDetail.sales.sales_amt
                      ? Math.round(hexDetail.sales.sales_amt / 10000).toLocaleString()
                      : null
                  }
                  unit="만원"
                  highlight
                />
                <StatRow
                  label="결제 건수"
                  value={hexDetail.sales.sales_cnt}
                  unit="건"
                />
                {hexDetail.trend.sales.length > 0 && (
                  <MiniChart
                    data={hexDetail.trend.sales
                      .filter((p) => p.value !== null)
                      .map((p) => ({
                        label: p.qtr,
                        value: Math.round(p.value! / 10000),
                      }))}
                    color="#fbbf24"
                  />
                )}
              </MetricCard>

              {/* Competition Card */}
              <MetricCard
                title="경쟁 현황"
                icon={<StoreIcon />}
                growthRate={hexDetail.growth.store_growth_rate}
              >
                <StatRow
                  label="점포 수"
                  value={hexDetail.competition.store_cnt}
                  unit="개"
                  highlight
                />
                <div className="mt-2 flex gap-4">
                  <div className="flex-1">
                    <p className="text-[10px] text-white/40">개업</p>
                    <p className="text-sm font-medium text-emerald-400">
                      +{hexDetail.competition.open_cnt ?? 0}
                    </p>
                  </div>
                  <div className="flex-1">
                    <p className="text-[10px] text-white/40">폐업</p>
                    <p className="text-sm font-medium text-red-400">
                      -{hexDetail.competition.close_cnt ?? 0}
                    </p>
                  </div>
                  <div className="flex-1">
                    <p className="text-[10px] text-white/40">폐업률</p>
                    <p className="text-sm font-medium text-white">
                      {hexDetail.competition.close_rate !== null
                        ? `${(hexDetail.competition.close_rate * 100).toFixed(1)}%`
                        : "-"}
                    </p>
                  </div>
                </div>
              </MetricCard>

              {/* Growth Card */}
              <MetricCard title="성장성" icon={<GrowthIcon />}>
                <div className="grid grid-cols-3 gap-2">
                  <GrowthStat
                    label="매출"
                    rate={hexDetail.growth.sales_growth_rate}
                  />
                  <GrowthStat
                    label="유동인구"
                    rate={hexDetail.growth.flow_growth_rate}
                  />
                  <GrowthStat
                    label="점포"
                    rate={hexDetail.growth.store_growth_rate}
                  />
                </div>
              </MetricCard>

              {/* Risk Card */}
              <MetricCard
                title="리스크"
                icon={<RiskIcon />}
                variant={
                  hexDetail.risk.warnings.length > 0 ? "warning" : "default"
                }
              >
                <StatRow
                  label="폐업률"
                  value={
                    hexDetail.risk.close_rate !== null
                      ? `${(hexDetail.risk.close_rate * 100).toFixed(1)}%`
                      : null
                  }
                />
                <StatRow
                  label="경쟁 밀도"
                  value={
                    hexDetail.risk.competition_density !== null
                      ? hexDetail.risk.competition_density.toFixed(2)
                      : null
                  }
                  unit="점포/hex"
                />
                <WarningList warnings={hexDetail.risk.warnings} />
                {hexDetail.risk.warnings.length === 0 && (
                  <p className="mt-2 text-xs text-emerald-400/80">
                    특별한 위험 신호 없음
                  </p>
                )}
              </MetricCard>

              {/* Recommendation Card (6th) */}
              <MetricCard
                title="추천"
                icon={<RecommendIcon />}
                variant={
                  hexDetail.recommendation.grade === "D"
                    ? "danger"
                    : hexDetail.recommendation.grade === "C"
                      ? "warning"
                      : "default"
                }
              >
                <div className="flex items-center justify-between py-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${
                        hexDetail.recommendation.grade === "S"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : hexDetail.recommendation.grade === "A"
                            ? "bg-blue-500/20 text-blue-400"
                            : hexDetail.recommendation.grade === "B"
                              ? "bg-amber-500/20 text-amber-400"
                              : hexDetail.recommendation.grade === "C"
                                ? "bg-orange-500/20 text-orange-400"
                                : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {hexDetail.recommendation.grade}
                    </span>
                    <span className="text-xs text-white/60">
                      {hexDetail.recommendation.summary}
                    </span>
                  </div>
                </div>
                {hexDetail.recommendation.pros.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] text-white/40">긍정 요인</p>
                    <ul className="mt-1 space-y-0.5">
                      {hexDetail.recommendation.pros.map((p, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-1.5 text-xs text-emerald-400/90"
                        >
                          <span className="mt-0.5 shrink-0">+</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {hexDetail.recommendation.cons.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] text-white/40">부정 요인</p>
                    <ul className="mt-1 space-y-0.5">
                      {hexDetail.recommendation.cons.map((c, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-1.5 text-xs text-red-400/90"
                        >
                          <span className="mt-0.5 shrink-0">-</span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </MetricCard>
            </>
          ) : (
            <div className="flex h-40 items-center justify-center text-sm text-white/40">
              데이터를 불러올 수 없습니다
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function GrowthStat({
  label,
  rate,
}: {
  label: string;
  rate: number | null;
}) {
  if (rate === null) {
    return (
      <div className="text-center">
        <p className="text-[10px] text-white/40">{label}</p>
        <p className="text-sm text-white/30">-</p>
      </div>
    );
  }

  const isPositive = rate >= 0;
  const pct = rate * 100; // API returns ratio (0.0219 = 2.19%)
  return (
    <div className="text-center">
      <p className="text-[10px] text-white/40">{label}</p>
      <p
        className={`text-sm font-medium ${
          isPositive ? "text-emerald-400" : "text-red-400"
        }`}
      >
        {isPositive ? "+" : ""}
        {pct.toFixed(1)}%
      </p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-6 w-24 bg-white/5" />
      <Skeleton className="h-32 w-full bg-white/5" />
      <Skeleton className="h-24 w-full bg-white/5" />
      <Skeleton className="h-24 w-full bg-white/5" />
      <Skeleton className="h-20 w-full bg-white/5" />
      <Skeleton className="h-20 w-full bg-white/5" />
    </div>
  );
}
