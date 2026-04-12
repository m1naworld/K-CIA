"use client";

import { useRef, useEffect } from "react";
import { useMapStore } from "@/store/mapStore";
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
import FacilityCard from "./FacilityCard";
import DemoCard from "./DemoCard";
import TimeSlotCard from "./TimeSlotCard";
import ComparisonCard from "./ComparisonCard";
import SocialBuzzCard from "./SocialBuzzCard";
import OperatingStrategyCard from "./OperatingStrategyCard";
import AlternativeAreasCard from "./AlternativeAreasCard";

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
  mon: "월",
  tue: "화",
  wed: "수",
  thu: "목",
  fri: "금",
  sat: "토",
  sun: "일",
};

export default function Sidebar() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const {
    sidebarOpen,
    hexDetail,
    hexDetailLoading,
    selectedAreaName,
    selectedRealName,
    selectedHex,
    closeSidebar,
    comparisonMode,
    comparisonData,
    comparisonLoading,
    socialEnabled,
    socialData,
    socialLoading,
  } = useMapStore();

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = 0;
    }
  }, [selectedHex]);

  if (!sidebarOpen) return null;

  return (
    <div className="intel-panel intel-scroll flex h-full w-[22rem] flex-col rounded-none border-y-0 border-r-0 border-l border-border/70 text-foreground shadow-[-28px_0_80px_-48px_rgba(2,6,23,0.35)] xl:w-[24rem]">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-border/70 bg-background/70 px-5 py-4 backdrop-blur-xl">
        <div className="intel-kicker">Area Briefing</div>
        <div>
          <h2 className="intel-title mt-2 text-sm font-semibold text-foreground">
            {selectedRealName ?? selectedAreaName ?? "구역 상세"}
          </h2>
          {selectedRealName && selectedAreaName && (
            <p className="mt-1 text-xs text-muted-foreground">{selectedAreaName}</p>
          )}
        </div>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs leading-5 text-muted-foreground">
            선택한 구역의 흐름, 경쟁, 리스크와 추천을 한 화면에서 요약합니다.
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={closeSidebar}
            className="h-9 w-9 rounded-full p-0 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        </div>
      </div>

      {/* Content */}
      <div
        ref={scrollContainerRef}
        className="intel-scroll flex-1 overflow-y-auto"
      >
        <div className="space-y-4 p-4">
          {comparisonMode ? (
            /* === Comparison Mode === */
            comparisonLoading ? (
              <LoadingSkeleton />
            ) : comparisonData ? (
              <ComparisonCard data={comparisonData} />
            ) : (
              <div className="intel-panel-soft flex h-40 items-center justify-center rounded-[1.35rem] text-center text-sm text-muted-foreground">
                비교할 분기를 선택하고
                <br />
                헥사곤을 클릭하세요
              </div>
            )
          ) : hexDetailLoading ? (
            <LoadingSkeleton />
          ) : hexDetail ? (
            <>
              {/* As-of Badge */}
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className="intel-badge-accent rounded-full text-xs"
                >
                  기준: {hexDetail.qtr}
                </Badge>
                <span className="text-[10px] text-muted-foreground">
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
                      className="rounded-full bg-secondary/70 text-xs text-secondary-foreground"
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
                    color="#7F1734"
                  />
                )}
                {hexDetail.flow.flow_by_weekday && (
                  <div className="mt-3">
                    <p className="mb-1 text-[10px] text-muted-foreground">요일별 분포</p>
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
                    color="#CC7722"
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
                    <p className="text-[10px] text-muted-foreground">개업</p>
                    <p className="intel-text-success text-sm font-medium">
                      +{hexDetail.competition.open_cnt ?? 0}
                    </p>
                  </div>
                  <div className="flex-1">
                    <p className="text-[10px] text-muted-foreground">폐업</p>
                    <p className="intel-text-danger text-sm font-medium">
                      -{hexDetail.competition.close_cnt ?? 0}
                    </p>
                  </div>
                  <div className="flex-1">
                    <p className="text-[10px] text-muted-foreground">폐업률</p>
                    <p className="text-sm font-medium text-foreground">
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

              {/* Risk Card (M11-6 확장) */}
              <MetricCard
                title="리스크 진단"
                icon={<RiskIcon />}
                variant={
                  hexDetail.risk.risk_level === "High" ? "danger"
                    : hexDetail.risk.risk_level === "Medium" ? "warning"
                    : "default"
                }
              >
                {/* Risk Score Gauge */}
                {hexDetail.risk.risk_score !== null && (
                  <div className="mb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-bold text-foreground">
                          {hexDetail.risk.risk_score.toFixed(1)}
                        </span>
                        <span className="text-xs text-muted-foreground">/100</span>
                      </div>
                      <Badge
                        variant="outline"
                        className={`text-xs font-semibold ${
                          hexDetail.risk.risk_level === "High"
                            ? "intel-badge-danger"
                            : hexDetail.risk.risk_level === "Medium"
                              ? "intel-badge-accent"
                              : "intel-badge-success"
                        }`}
                      >
                        {hexDetail.risk.risk_level === "High" ? "고위험"
                          : hexDetail.risk.risk_level === "Medium" ? "주의"
                          : "양호"}
                      </Badge>
                    </div>
                    {/* Gauge bar */}
                    <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${hexDetail.risk.risk_score}%`,
                          background: hexDetail.risk.risk_score >= 67
                            ? "linear-gradient(to right, #ef4444, #dc2626)"
                            : hexDetail.risk.risk_score >= 34
                              ? "linear-gradient(to right, #f59e0b, #d97706)"
                              : "linear-gradient(to right, #22c55e, #16a34a)",
                        }}
                      />
                    </div>
                    <div className="mt-1 flex justify-between text-[9px] text-muted-foreground">
                      <span>Low</span>
                      <span>Medium</span>
                      <span>High</span>
                    </div>
                  </div>
                )}

                {/* Decomposition bar chart */}
                {hexDetail.risk.decomposition.length > 0 && (
                  <div className="mt-1">
                    <p className="mb-2 text-[10px] font-medium text-muted-foreground">원인 분해</p>
                    <div className="space-y-2">
                      {hexDetail.risk.decomposition
                        .sort((a, b) => b.contribution - a.contribution)
                        .map((d) => {
                          const pct = hexDetail.risk.risk_score && hexDetail.risk.risk_score > 0
                            ? (d.contribution / hexDetail.risk.risk_score) * 100
                            : 0;
                          return (
                            <div key={d.factor}>
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">{d.label}</span>
                                <span className="font-medium text-foreground">
                                  {pct.toFixed(1)}%
                                </span>
                              </div>
                              <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                                <div
                                  className="h-full rounded-full transition-all duration-300"
                                  style={{
                                    width: `${Math.min(100, pct)}%`,
                                    backgroundColor: d.score >= 67 ? "#ef4444"
                                      : d.score >= 34 ? "#f59e0b"
                                      : "#22c55e",
                                  }}
                                />
                              </div>
                              <div className="mt-0.5 flex justify-between text-[9px] text-muted-foreground">
                                <span>
                                  {d.value !== null
                                    ? d.factor === "close_rate" || d.factor === "store_growth" || d.factor === "sales_decline"
                                      ? `${(d.value * 100).toFixed(1)}%`
                                      : d.value.toFixed(1)
                                    : "—"}
                                </span>
                                <span>점수 {d.score.toFixed(0)}</span>
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}

                {/* Warnings */}
                <WarningList warnings={hexDetail.risk.warnings} />
                {hexDetail.risk.warnings.length === 0 && hexDetail.risk.risk_level !== "High" && (
                  <p className="intel-text-success mt-2 text-xs">
                    특별한 위험 신호 없음
                  </p>
                )}
              </MetricCard>

              {/* Alternative Areas Card (M11-7) */}
              {hexDetail.alternatives && hexDetail.alternatives.length > 0 && (
                <AlternativeAreasCard
                  alternatives={hexDetail.alternatives}
                  currentRiskScore={hexDetail.risk.risk_score}
                />
              )}

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
                          ? "intel-surface-success"
                          : hexDetail.recommendation.grade === "A"
                            ? "intel-surface-primary"
                            : hexDetail.recommendation.grade === "B"
                              ? "intel-surface-accent"
                              : hexDetail.recommendation.grade === "C"
                                ? "intel-surface-accent"
                                : "intel-surface-danger"
                      }`}
                    >
                      {hexDetail.recommendation.grade}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {hexDetail.recommendation.summary}
                    </span>
                  </div>
                </div>
                {hexDetail.recommendation.pros.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] text-muted-foreground">긍정 요인</p>
                    <ul className="mt-1 space-y-0.5">
                      {hexDetail.recommendation.pros.map((p, i) => (
                        <li
                          key={i}
                          className="intel-text-success flex items-start gap-1.5 text-xs"
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
                    <p className="text-[10px] text-muted-foreground">부정 요인</p>
                    <ul className="mt-1 space-y-0.5">
                      {hexDetail.recommendation.cons.map((c, i) => (
                        <li
                          key={i}
                          className="intel-text-danger flex items-start gap-1.5 text-xs"
                        >
                          <span className="mt-0.5 shrink-0">-</span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </MetricCard>

              {/* Facility Card (M7-4) */}
              {hexDetail.facility && (
                <FacilityCard data={hexDetail.facility} />
              )}

              {/* Demo Card (M7-4) */}
              {hexDetail.demo && (
                <DemoCard data={hexDetail.demo} />
              )}

              {/* TimeSlot Card (M7-4, M10-5 확장) */}
              {hexDetail.time_slot && (
                <TimeSlotCard
                  data={hexDetail.time_slot}
                  flow={hexDetail.flow}
                  operatingStrategy={hexDetail.operating_strategy}
                />
              )}

              {/* Operating Strategy Card (M10-6) */}
              {hexDetail.operating_strategy && (
                <OperatingStrategyCard data={hexDetail.operating_strategy} />
              )}

              {/* Social Buzz Card (M9) */}
              {socialEnabled && (
                socialLoading
                  ? <Skeleton className="h-48 w-full bg-slate-200/80 dark:bg-white/5" />
                  : socialData
                    ? <SocialBuzzCard data={socialData} />
                    : null
              )}
            </>
          ) : (
            <div className="intel-panel-soft flex h-40 items-center justify-center rounded-[1.35rem] text-sm text-muted-foreground">
              데이터를 불러올 수 없습니다
            </div>
          )}
        </div>
      </div>
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
        <p className="text-[10px] text-muted-foreground">{label}</p>
        <p className="text-sm text-muted-foreground">-</p>
      </div>
    );
  }

  const isPositive = rate >= 0;
  const pct = rate * 100; // API returns ratio (0.0219 = 2.19%)
  return (
    <div className="text-center">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p
        className={`text-sm font-medium ${
          isPositive ? "intel-text-success" : "intel-text-danger"
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
      <Skeleton className="h-6 w-24 bg-muted/70" />
      <Skeleton className="h-32 w-full bg-muted/70" />
      <Skeleton className="h-24 w-full bg-muted/70" />
      <Skeleton className="h-24 w-full bg-muted/70" />
      <Skeleton className="h-20 w-full bg-muted/70" />
      <Skeleton className="h-20 w-full bg-muted/70" />
    </div>
  );
}
