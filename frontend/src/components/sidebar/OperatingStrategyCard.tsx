"use client";

import { useState, useMemo } from "react";
import { MetricCard, StatRow } from "./MetricCard";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { OperatingStrategyCard as OperatingStrategyData } from "@/types/map";

const StrategyIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
  </svg>
);

/** Parse "HH:MM" → hour number, or start hour from "HH~HH" range */
function parseHour(s: string): number {
  if (s.includes(":")) return parseInt(s.split(":")[0], 10);
  if (s.includes("~")) return parseInt(s.split("~")[0], 10);
  return parseInt(s, 10) || 0;
}

/** Get slot duration in hours from "HH~HH" range */
function slotHours(hourRange: string): number {
  const parts = hourRange.split("~").map(Number);
  if (parts.length !== 2) return 3;
  const [start, end] = parts;
  return end > start ? end - start : 24 - start + end;
}

interface Props {
  data: OperatingStrategyData;
}

export default function OperatingStrategyCard({ data }: Props) {
  // -- 가정값 입력 state --
  const [avgCheckInput, setAvgCheckInput] = useState<string>("15000");
  const [turnover, setTurnover] = useState<number>(1.5); // 회전율/시간
  const [seats, setSeats] = useState<number>(30); // 좌석수
  const avgCheck = Number(avgCheckInput) || 0;

  const openHour = parseHour(data.recommended_open);
  const closeHour = parseHour(data.recommended_close);

  // -- 매출 시뮬레이션 --
  const simulation = useMemo(() => {
    const dailyCapacity = seats * turnover * data.recommended_hours;
    const dailyRevenue = dailyCapacity * avgCheck;
    const monthlyRevenue = dailyRevenue * 30;

    // Per-slot breakdown using estimated_revenue_share
    const perSlot = data.all_slots.map((slot) => ({
      label: slot.label,
      hourRange: slot.hour_range,
      revenue: dailyRevenue * slot.estimated_revenue_share,
      customers: dailyCapacity * slot.flow_ratio,
      isPeak: slot.is_peak,
    }));

    return { dailyCapacity, dailyRevenue, monthlyRevenue, perSlot };
  }, [avgCheck, turnover, seats, data]);

  return (
    <MetricCard title="운영 전략" icon={<StrategyIcon />}>
      {/* === Section 1: 권장 영업시간 타임라인 === */}
      <div className="mb-3">
        <p className="mb-1.5 text-[10px] font-medium text-slate-500 dark:text-white/40">
          권장 영업시간
        </p>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="border-emerald-500/40 bg-emerald-500/10 text-xs text-emerald-500 dark:text-emerald-400"
          >
            {data.recommended_open}
          </Badge>
          <span className="text-[10px] text-slate-400 dark:text-white/30">~</span>
          <Badge
            variant="outline"
            className="border-red-500/40 bg-red-500/10 text-xs text-red-500 dark:text-red-400"
          >
            {data.recommended_close}
          </Badge>
          <span className="text-[10px] text-slate-500 dark:text-white/40">
            ({data.recommended_hours}시간)
          </span>
        </div>

        {/* 24h Timeline Bar */}
        <div className="mt-2">
          <div className="relative h-6 w-full overflow-hidden rounded bg-slate-100 dark:bg-white/5">
            {/* Operating hours background */}
            <div
              className="absolute top-0 h-full bg-emerald-500/20 dark:bg-emerald-500/15"
              style={{
                left: `${(openHour / 24) * 100}%`,
                width: `${(((closeHour > openHour ? closeHour - openHour : 24 - openHour + closeHour)) / 24) * 100}%`,
              }}
            />
            {/* Peak slot highlights */}
            {data.peak_slots.map((slot) => {
              const start = parseHour(slot.hour_range);
              const hours = slotHours(slot.hour_range);
              return (
                <div
                  key={slot.hour_range}
                  className="absolute top-0 h-full bg-amber-500/40 dark:bg-amber-500/30"
                  style={{
                    left: `${(start / 24) * 100}%`,
                    width: `${(hours / 24) * 100}%`,
                  }}
                />
              );
            })}
            {/* Hour ticks */}
            {[0, 6, 12, 18, 24].map((h) => (
              <div
                key={h}
                className="absolute top-0 h-full border-l border-slate-300/40 dark:border-white/10"
                style={{ left: `${(h / 24) * 100}%` }}
              >
                <span className="absolute -bottom-3.5 left-0 -translate-x-1/2 text-[8px] text-slate-400 dark:text-white/25">
                  {h}
                </span>
              </div>
            ))}
          </div>
          {/* Legend */}
          <div className="mt-4 flex items-center gap-3">
            <div className="flex items-center gap-1">
              <div className="h-2 w-3 rounded-sm bg-emerald-500/20 dark:bg-emerald-500/15" />
              <span className="text-[8px] text-slate-400 dark:text-white/30">영업</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-3 rounded-sm bg-amber-500/40 dark:bg-amber-500/30" />
              <span className="text-[8px] text-slate-400 dark:text-white/30">피크</span>
            </div>
          </div>
        </div>
      </div>

      <Separator className="my-3 bg-slate-200 dark:bg-white/10" />

      {/* === Section 2: 인력 스케줄 시각화 === */}
      <div className="mb-3">
        <p className="mb-1.5 text-[10px] font-medium text-slate-500 dark:text-white/40">
          시간대별 인력 배분
        </p>
        <div className="space-y-1">
          {data.all_slots.map((slot) => {
            const maxRatio = Math.max(...data.all_slots.map((s) => s.staff_ratio));
            const barWidth = maxRatio > 0 ? (slot.staff_ratio / maxRatio) * 100 : 0;
            return (
              <div key={slot.hour_range} className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={`w-11 shrink-0 justify-center px-1 text-[10px] ${
                    slot.is_peak
                      ? "border-amber-500/40 bg-amber-500/10 text-amber-500 dark:text-amber-400"
                      : "border-slate-300/40 bg-slate-100 text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-white/40"
                  }`}
                >
                  {slot.label}
                </Badge>
                <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/5">
                  <div
                    className={`h-full rounded-full transition-all ${
                      slot.is_peak ? "bg-amber-500/60" : "bg-slate-400/40 dark:bg-white/20"
                    }`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <span className="w-8 text-right text-[10px] font-medium text-slate-600 dark:text-white/50">
                  x{slot.staff_ratio.toFixed(1)}
                </span>
                <span className="w-8 text-right text-[10px] text-slate-400 dark:text-white/30">
                  {(slot.estimated_revenue_share * 100).toFixed(0)}%
                </span>
              </div>
            );
          })}
        </div>
        <div className="mt-1 flex justify-end gap-4">
          <span className="text-[8px] text-slate-400 dark:text-white/25">
            x 인력배분
          </span>
          <span className="text-[8px] text-slate-400 dark:text-white/25">
            매출기여
          </span>
        </div>
      </div>

      <Separator className="my-3 bg-slate-200 dark:bg-white/10" />

      {/* === Section 3: 가정값 입력 & 매출 시뮬레이션 === */}
      <div>
        <p className="mb-2 text-[10px] font-medium text-slate-500 dark:text-white/40">
          매출 시뮬레이션
        </p>

        {/* Assumption inputs */}
        <div className="mb-3 grid grid-cols-3 gap-2">
          <div>
            <Label className="text-[9px] text-slate-500 dark:text-white/40">
              객단가(원)
            </Label>
            <Input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={avgCheckInput}
              onChange={(e) => setAvgCheckInput(e.target.value.replace(/[^0-9]/g, ""))}
              onBlur={() => {
                if (!avgCheckInput) setAvgCheckInput("0");
              }}
              className="mt-0.5 h-7 bg-slate-50 text-xs text-slate-900 dark:bg-white/5 dark:text-white"
            />
          </div>
          <div>
            <Label className="text-[9px] text-slate-500 dark:text-white/40">
              회전율(/h)
            </Label>
            <Input
              type="number"
              value={turnover}
              onChange={(e) => setTurnover(Number(e.target.value) || 0)}
              className="mt-0.5 h-7 bg-slate-50 text-xs text-slate-900 dark:bg-white/5 dark:text-white"
              min={0}
              step={0.1}
            />
          </div>
          <div>
            <Label className="text-[9px] text-slate-500 dark:text-white/40">
              좌석수
            </Label>
            <Input
              type="number"
              value={seats}
              onChange={(e) => setSeats(Number(e.target.value) || 0)}
              className="mt-0.5 h-7 bg-slate-50 text-xs text-slate-900 dark:bg-white/5 dark:text-white"
              min={0}
              step={1}
            />
          </div>
        </div>

        {/* Simulation results */}
        <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-2.5 dark:border-white/10 dark:bg-white/5">
          <StatRow
            label="일 예상 고객"
            value={Math.round(simulation.dailyCapacity)}
            unit="명"
          />
          <StatRow
            label="일 예상 매출"
            value={Math.round(simulation.dailyRevenue / 10000).toLocaleString()}
            unit="만원"
            highlight
          />
          <StatRow
            label="월 예상 매출"
            value={Math.round(simulation.monthlyRevenue / 10000).toLocaleString()}
            unit="만원"
            highlight
          />
        </div>

        {/* Per-slot breakdown */}
        {simulation.perSlot.length > 0 && (
          <div className="mt-2">
            <p className="mb-1 text-[9px] text-slate-400 dark:text-white/30">
              시간대별 예상 매출
            </p>
            <div className="space-y-0.5">
              {simulation.perSlot.map((slot) => {
                const maxRevenue = Math.max(...simulation.perSlot.map((s) => s.revenue));
                const barW = maxRevenue > 0 ? (slot.revenue / maxRevenue) * 100 : 0;
                return (
                  <div key={slot.hourRange} className="flex items-center gap-1.5">
                    <span className={`w-8 text-right text-[9px] ${
                      slot.isPeak
                        ? "font-medium text-amber-600 dark:text-amber-400"
                        : "text-slate-500 dark:text-white/40"
                    }`}>
                      {slot.label}
                    </span>
                    <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/5">
                      <div
                        className={`h-full rounded-full transition-all ${
                          slot.isPeak ? "bg-amber-500/50" : "bg-slate-400/30 dark:bg-white/15"
                        }`}
                        style={{ width: `${barW}%` }}
                      />
                    </div>
                    <span className="w-12 text-right text-[9px] text-slate-500 dark:text-white/40">
                      {Math.round(slot.revenue / 10000).toLocaleString()}만
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Assumptions */}
      {data.assumptions.length > 0 && (
        <>
          <Separator className="my-3 bg-slate-200 dark:bg-white/10" />
          <div>
            <p className="mb-1 text-[9px] text-slate-400 dark:text-white/30">
              가정 및 참고사항
            </p>
            <ul className="space-y-0.5">
              {data.assumptions.map((a, i) => (
                <li key={i} className="flex items-start gap-1 text-[9px] text-slate-500 dark:text-white/35">
                  <span className="mt-px shrink-0">*</span>
                  <span>{a}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </MetricCard>
  );
}
