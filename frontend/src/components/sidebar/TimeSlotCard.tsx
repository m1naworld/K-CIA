"use client";

import { MetricCard } from "./MetricCard";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type {
  TimeSlotRecommendation,
  FlowCard,
  OperatingStrategyCard,
} from "@/types/map";

const ClockIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const WEEKDAY_LABELS: Record<string, string> = {
  "1": "월", "2": "화", "3": "수", "4": "목", "5": "금", "6": "토", "7": "일",
  mon: "월", tue: "화", wed: "수", thu: "목", fri: "금", sat: "토", sun: "일",
};

const WEEKDAY_KEYS_API = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const WEEKDAY_KEYS_NUM = ["1", "2", "3", "4", "5", "6", "7"];
const WEEKEND_KEYS = new Set(["sat", "sun", "6", "7"]);

const SLOT_SHORT_LABELS: Record<string, string> = {
  "00~06": "새벽", "06~11": "오전", "11~14": "점심",
  "14~17": "오후", "17~21": "저녁", "21~24": "밤",
};

/** Map flow_by_hour keys (e.g. "00_06") to slot labels */
const HOUR_KEY_TO_SLOT: Record<string, string> = {
  "00_06": "00~06", "06_11": "06~11", "11_14": "11~14",
  "14_17": "14~17", "17_21": "17~21", "21_24": "21~24",
};

/** Color scale for heatmap cells: 0 (low) ~ 1 (high) */
function heatmapColor(t: number): string {
  // navy tint → apricot → ochre
  if (t < 0.5) {
    const s = t / 0.5;
    const r = Math.round(229 + (255 - 229) * s);
    const g = Math.round(234 + (178 - 234) * s);
    const b = Math.round(247 + (127 - 247) * s);
    return `rgb(${r},${g},${b})`;
  }
  const s = (t - 0.5) / 0.5;
  const r = Math.round(255 + (204 - 255) * s);
  const g = Math.round(178 + (119 - 178) * s);
  const b = Math.round(127 + (34 - 127) * s);
  return `rgb(${r},${g},${b})`;
}

interface Props {
  data: TimeSlotRecommendation;
  flow?: FlowCard | null;
  operatingStrategy?: OperatingStrategyCard | null;
}

export default function TimeSlotCard({ data, flow, operatingStrategy }: Props) {
  const hasHourly = data.recommendations.length > 0;
  const hasStrategy = !!operatingStrategy;

  // Determine peak/off-peak slots from operating strategy or fallback to recommendations
  const peakSlots = hasStrategy
    ? operatingStrategy!.peak_slots
    : null;
  const offPeakSlots = hasStrategy
    ? operatingStrategy!.off_peak_slots
    : null;

  // Build weekday×timeslot heatmap data (estimated proportional distribution)
  const heatmapData = buildHeatmap(flow);

  // Weekday vs weekend comparison
  const weekdayWeekend = buildWeekdayWeekend(flow, operatingStrategy);

  return (
    <MetricCard title="시간대 분석" icon={<ClockIcon />}>
      {/* === Section 1: Peak / Off-peak Classification === */}
      {hasStrategy && peakSlots && offPeakSlots && (
        <div className="mb-3">
          <p className="mb-1.5 text-[10px] font-medium text-slate-500 dark:text-white/40">
            피크 / 오프피크 분류
          </p>
          {/* Peak slots */}
          <div className="mb-2">
            <div className="mb-1 flex items-center gap-1.5">
              <span className="intel-surface-accent inline-block h-2 w-2 rounded-full border" />
              <span className="intel-text-accent text-[10px] font-medium">피크</span>
            </div>
            <div className="space-y-1">
              {peakSlots.map((slot) => (
                <div key={slot.hour_range} className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className="intel-badge-accent w-11 shrink-0 justify-center px-1 text-[10px]"
                  >
                    {slot.label}
                  </Badge>
                  <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/5">
                    <div
                      className="intel-meter-accent h-full rounded-full transition-all"
                      style={{ width: `${slot.flow_ratio * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-[10px] text-slate-600 dark:text-white/50">
                    {(slot.flow_ratio * 100).toFixed(0)}%
                  </span>
                  <span className="intel-text-accent w-8 text-right text-[10px]">
                    x{slot.staff_ratio.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Off-peak slots */}
          <div>
            <div className="mb-1 flex items-center gap-1.5">
              <span className="intel-surface-primary inline-block h-2 w-2 rounded-full border" />
              <span className="intel-text-primary text-[10px] font-medium">오프피크</span>
            </div>
            <div className="space-y-1">
              {offPeakSlots.map((slot) => (
                <div key={slot.hour_range} className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className="intel-badge-primary w-11 shrink-0 justify-center px-1 text-[10px]"
                  >
                    {slot.label}
                  </Badge>
                  <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/5">
                    <div
                      className="intel-meter-primary h-full rounded-full opacity-70 transition-all"
                      style={{ width: `${slot.flow_ratio * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-[10px] text-slate-600 dark:text-white/50">
                    {(slot.flow_ratio * 100).toFixed(0)}%
                  </span>
                  <span className="intel-text-primary w-8 text-right text-[10px] opacity-80">
                    x{slot.staff_ratio.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <p className="mt-1.5 text-right text-[9px] text-slate-400 dark:text-white/30">
            x 인력배분 기준 (평균=1.0)
          </p>
        </div>
      )}

      {/* Fallback: original bar chart when no operating strategy */}
      {!hasStrategy && hasHourly && (
        <div className="mb-3">
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
                        isPeak ? "intel-meter-accent" : "intel-meter-primary opacity-65"
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

      {/* Peak weekday badge */}
      {data.peak_weekday && (
        <div className="mb-3 flex items-center gap-2">
          <span className="text-xs text-slate-500 dark:text-white/50">피크 요일</span>
          <Badge
            variant="outline"
            className="intel-badge-primary text-xs"
          >
            {data.peak_weekday}요일
          </Badge>
        </div>
      )}

      {/* === Section 2: Weekday x Timeslot Heatmap === */}
      {heatmapData && (
        <>
          <Separator className="my-3 bg-slate-200 dark:bg-white/10" />
          <div>
            <p className="mb-2 text-[10px] font-medium text-slate-500 dark:text-white/40">
              요일 x 시간대 유동 분포 (추정)
            </p>
            {/* Column headers */}
            <div className="mb-0.5 flex">
              <div className="w-6 shrink-0" />
              {heatmapData.slotKeys.map((sk) => (
                <div
                  key={sk}
                  className="flex-1 text-center text-[8px] text-slate-400 dark:text-white/30"
                >
                  {SLOT_SHORT_LABELS[sk] ?? sk}
                </div>
              ))}
            </div>
            {/* Rows */}
            {heatmapData.weekdayKeys.map((dk) => (
              <div key={dk} className="flex items-center">
                <span className="w-6 shrink-0 text-[9px] text-slate-500 dark:text-white/40">
                  {WEEKDAY_LABELS[dk] ?? dk}
                </span>
                {heatmapData.slotKeys.map((sk) => {
                  const val = heatmapData.grid[dk]?.[sk] ?? 0;
                  return (
                    <div
                      key={sk}
                      className="group relative m-px flex-1"
                      title={`${WEEKDAY_LABELS[dk]}요일 ${SLOT_SHORT_LABELS[sk]}: ${Math.round(val).toLocaleString()}명`}
                    >
                      <div
                        className="h-4 rounded-sm transition-all"
                        style={{ backgroundColor: heatmapColor(heatmapData.norm[dk]?.[sk] ?? 0) }}
                      />
                    </div>
                  );
                })}
              </div>
            ))}
            {/* Legend */}
            <div className="mt-1.5 flex items-center justify-end gap-1">
              <span className="text-[8px] text-slate-400 dark:text-white/30">낮음</span>
              <div className="flex h-2 overflow-hidden rounded">
                {[0, 0.25, 0.5, 0.75, 1].map((t) => (
                  <div
                    key={t}
                    className="w-3"
                    style={{ backgroundColor: heatmapColor(t) }}
                  />
                ))}
              </div>
              <span className="text-[8px] text-slate-400 dark:text-white/30">높음</span>
            </div>
          </div>
        </>
      )}

      {/* === Section 3: Weekday vs Weekend Comparison === */}
      {weekdayWeekend && (
        <>
          <Separator className="my-3 bg-slate-200 dark:bg-white/10" />
          <div>
            <p className="mb-2 text-[10px] font-medium text-slate-500 dark:text-white/40">
              평일 vs 주말 유동인구
            </p>
            <div className="flex gap-3">
              {/* Weekday bar */}
              <div className="flex-1">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-[10px] text-slate-600 dark:text-white/50">평일</span>
                  <span className="intel-text-primary text-[10px] font-medium">
                    {(weekdayWeekend.weekdayRatio * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/5">
                  <div
                    className="intel-meter-primary h-full rounded-full transition-all"
                    style={{ width: `${weekdayWeekend.weekdayRatio * 100}%` }}
                  />
                </div>
                <p className="mt-0.5 text-right text-[9px] text-slate-400 dark:text-white/30">
                  {Math.round(weekdayWeekend.weekdayAvg).toLocaleString()}명/일
                </p>
              </div>
              {/* Weekend bar */}
              <div className="flex-1">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-[10px] text-slate-600 dark:text-white/50">주말</span>
                  <span className="intel-text-accent text-[10px] font-medium">
                    {(weekdayWeekend.weekendRatio * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/5">
                  <div
                    className="intel-meter-accent h-full rounded-full transition-all"
                    style={{ width: `${weekdayWeekend.weekendRatio * 100}%` }}
                  />
                </div>
                <p className="mt-0.5 text-right text-[9px] text-slate-400 dark:text-white/30">
                  {Math.round(weekdayWeekend.weekendAvg).toLocaleString()}명/일
                </p>
              </div>
            </div>
            {/* Weekday per-day bars */}
            {weekdayWeekend.perDay.length > 0 && (
              <div className="mt-2 flex gap-0.5">
                {weekdayWeekend.perDay.map(({ key, label, value, ratio }) => {
                  const isWeekend = key === "6" || key === "7";
                  return (
                    <div key={key} className="group relative flex flex-1 flex-col items-center">
                      <div className="relative h-8 w-full">
                        <div
                          className={`absolute bottom-0 w-full rounded-t transition-all group-hover:opacity-80 ${
                            isWeekend ? "intel-meter-accent" : "intel-meter-primary opacity-75"
                          }`}
                          style={{ height: `${ratio * 100}%` }}
                        />
                      </div>
                      <span className={`mt-0.5 text-[9px] ${
                        isWeekend ? "intel-text-accent font-medium" : "text-slate-500 dark:text-white/40"
                      }`}>
                        {label}
                      </span>
                      <div className="pointer-events-none absolute -top-5 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded bg-white px-1.5 py-0.5 text-[10px] text-slate-700 opacity-0 shadow-sm transition-opacity group-hover:opacity-100 dark:bg-gray-800 dark:text-white">
                        {Math.round(value).toLocaleString()}명
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* No hourly data fallback */}
      {!hasHourly && !hasStrategy && data.peak_weekday && (
        <p className="text-xs text-slate-500 dark:text-white/40">
          시간대별 상세 데이터는 추후 업데이트 예정
        </p>
      )}
    </MetricCard>
  );
}

// ── Heatmap builder ──────────────────────────────

interface HeatmapResult {
  weekdayKeys: string[];   // ["1","2",...,"7"]
  slotKeys: string[];      // ["00~06","06~11",...,"21~24"]
  grid: Record<string, Record<string, number>>;   // absolute estimated values
  norm: Record<string, Record<string, number>>;   // 0~1 normalized for coloring
}

function resolveWeekdayKeys(data: Record<string, number>): string[] {
  if ("mon" in data) return WEEKDAY_KEYS_API;
  return WEEKDAY_KEYS_NUM;
}

function buildHeatmap(flow?: FlowCard | null): HeatmapResult | null {
  if (!flow?.flow_by_hour || !flow?.flow_by_weekday) return null;

  const weekdayKeys = resolveWeekdayKeys(flow.flow_by_weekday);
  const slotKeys = ["00~06", "06~11", "11~14", "14~17", "17~21", "21~24"];

  const SLOT_HOURS: Record<string, number> = {
    "00~06": 6, "06~11": 5, "11~14": 3, "14~17": 3, "17~21": 4, "21~24": 3,
  };

  // Normalize flow_by_hour keys (API uses "00_06" style)
  const hourNorm: Record<string, number> = {};
  for (const [k, v] of Object.entries(flow.flow_by_hour)) {
    const mapped = HOUR_KEY_TO_SLOT[k] ?? k.replace("_", "~");
    hourNorm[mapped] = v / (SLOT_HOURS[mapped] ?? 1);
  }

  const totalHour = Object.values(hourNorm).reduce((s, v) => s + v, 0) || 1;
  const totalWeekday = Object.values(flow.flow_by_weekday).reduce((s, v) => s + v, 0) || 1;

  // Estimated joint distribution: cell = weekday_prop * slot_prop * total
  // Using geometric mean total for scaling
  const total = Math.sqrt(totalHour * totalWeekday);

  const grid: Record<string, Record<string, number>> = {};
  let maxVal = 0;
  let minVal = Number.POSITIVE_INFINITY;

  for (const dk of weekdayKeys) {
    grid[dk] = {};
    const wdVal = flow.flow_by_weekday[dk] ?? 0;
    const wdProp = wdVal / totalWeekday;
    for (const sk of slotKeys) {
      const hVal = hourNorm[sk] ?? 0;
      const hProp = hVal / totalHour;
      const estimated = wdProp * hProp * total;
      grid[dk][sk] = estimated;
      if (estimated > maxVal) maxVal = estimated;
      if (estimated < minVal) minVal = estimated;
    }
  }

  // Normalize to 0~1
  const norm: Record<string, Record<string, number>> = {};
  const range = maxVal - minVal;
  for (const dk of weekdayKeys) {
    norm[dk] = {};
    for (const sk of slotKeys) {
      const val = grid[dk][sk];
      norm[dk][sk] = range > 0 ? (val - minVal) / range : 0;
    }
  }

  return { weekdayKeys, slotKeys, grid, norm };
}

// ── Weekday vs weekend builder ────────────────────

interface WeekdayWeekendResult {
  weekdayRatio: number;
  weekendRatio: number;
  weekdayAvg: number;
  weekendAvg: number;
  perDay: { key: string; label: string; value: number; ratio: number }[];
}

function buildWeekdayWeekend(
  flow?: FlowCard | null,
  strategy?: OperatingStrategyCard | null,
): WeekdayWeekendResult | null {
  // Try operating strategy first
  if (strategy?.weekday_pattern) {
    const wp = strategy.weekday_pattern;
    if (wp.weekday_flow_ratio != null && wp.weekend_flow_ratio != null) {
      const wdRatio = wp.weekday_flow_ratio;
      const weRatio = wp.weekend_flow_ratio;
      const total = strategy.total_flow ?? 0;
      const weekdayTotal = total * wdRatio;
      const weekendTotal = total * weRatio;

      // Build per-day if flow_by_weekday available
      const perDay = buildPerDay(flow?.flow_by_weekday);

      return {
        weekdayRatio: wdRatio,
        weekendRatio: weRatio,
        weekdayAvg: weekdayTotal / 5,
        weekendAvg: weekendTotal / 2,
        perDay,
      };
    }
  }

  // Fallback to flow_by_weekday
  if (!flow?.flow_by_weekday) return null;

  const entries = Object.entries(flow.flow_by_weekday);
  const weekdaySum = entries
    .filter(([k]) => !WEEKEND_KEYS.has(k))
    .reduce((s, [, v]) => s + v, 0);
  const weekendSum = entries
    .filter(([k]) => WEEKEND_KEYS.has(k))
    .reduce((s, [, v]) => s + v, 0);
  const total = weekdaySum + weekendSum || 1;

  return {
    weekdayRatio: weekdaySum / total,
    weekendRatio: weekendSum / total,
    weekdayAvg: weekdaySum / 5,
    weekendAvg: weekendSum / 2,
    perDay: buildPerDay(flow.flow_by_weekday),
  };
}

function buildPerDay(weekdayData?: Record<string, number> | null) {
  if (!weekdayData) return [];
  const entries = Object.entries(weekdayData);
  const maxVal = Math.max(...entries.map(([, v]) => v)) || 1;
  return entries.map(([k, v]) => ({
    key: k,
    label: WEEKDAY_LABELS[k] ?? k,
    value: v,
    ratio: v / maxVal,
  }));
}
