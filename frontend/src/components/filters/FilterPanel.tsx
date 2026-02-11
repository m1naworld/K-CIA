"use client";

import { useEffect } from "react";
import { useMapStore } from "@/store/mapStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { trackEvent } from "@/lib/analytics";
import ThemeToggle from "@/components/common/ThemeToggle";

// 최근 8분기 생성 (현재 2024Q4 기준 → 2023Q1~2024Q4)
function generateQuarters(): { value: string; label: string }[] {
  const quarters: { value: string; label: string }[] = [];
  const now = new Date();
  let year = now.getFullYear();
  let q = Math.ceil((now.getMonth() + 1) / 3);
  for (let i = 0; i < 8; i++) {
    quarters.push({
      value: `${year}${q}`,
      label: `${year}년 ${q}분기`,
    });
    q--;
    if (q === 0) {
      q = 4;
      year--;
    }
  }
  return quarters;
}

const QUARTERS = generateQuarters();

export default function FilterPanel() {
  const {
    category,
    quarter,
    categories,
    setCategory,
    setQuarter,
    fetchCategories,
    comparisonMode,
    compareQtrBefore,
    compareQtrAfter,
    compareCategoryMode,
    setComparisonMode,
    setCompareQtrBefore,
    setCompareQtrAfter,
    setCompareCategoryMode,
    socialEnabled,
    toggleSocial,
    fetchSocialConfig,
  } = useMapStore();

  useEffect(() => {
    fetchCategories();
    fetchSocialConfig();
  }, [fetchCategories, fetchSocialConfig]);

  const handleCategoryChange = (nextCategory: string) => {
    setCategory(nextCategory);
    trackEvent("FILTER_APPLY", {
      filter_type: "category",
      value: nextCategory,
      category: nextCategory,
      qtr: quarter,
    });
  };

  const handleQuarterChange = (nextQuarter: string) => {
    setQuarter(nextQuarter);
    trackEvent("FILTER_APPLY", {
      filter_type: "qtr",
      value: nextQuarter,
      category,
      qtr: nextQuarter,
    });
  };

  return (
    <Card className="h-full w-72 shrink-0 overflow-y-auto rounded-none border-0 border-r border-slate-200 bg-slate-50 text-slate-900 dark:border-white/10 dark:bg-gray-900 dark:text-white">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">필터</CardTitle>
          <ThemeToggle />
        </div>
        <Badge variant="outline" className="w-fit border-slate-200 text-[10px] text-slate-500 dark:border-white/10 dark:text-white/50">
          성수동 상권 분석
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {/* 업종 선택 */}
        <div className="flex flex-col gap-2">
          <Label className="text-xs text-slate-500 dark:text-white/60">업종</Label>
          <Select value={category} onValueChange={handleCategoryChange}>
            <SelectTrigger className="border-slate-200 bg-white text-sm text-slate-900 dark:border-white/20 dark:bg-gray-800 dark:text-white">
              <SelectValue placeholder="전체 업종" />
            </SelectTrigger>
            <SelectContent className="max-h-60 bg-white text-slate-900 dark:bg-gray-800 dark:text-white">
              <SelectItem value="all">전체 업종</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.service_code} value={cat.service_code}>
                  {cat.service_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 분기 선택 (기본 모드) */}
        {!comparisonMode && (
          <div className="flex flex-col gap-2">
            <Label className="text-xs text-slate-500 dark:text-white/60">기준 분기</Label>
            <Select value={quarter} onValueChange={handleQuarterChange}>
              <SelectTrigger className="border-slate-200 bg-white text-sm text-slate-900 dark:border-white/20 dark:bg-gray-800 dark:text-white">
                <SelectValue placeholder="최신 분기" />
              </SelectTrigger>
              <SelectContent className="bg-white text-slate-900 dark:bg-gray-800 dark:text-white">
                <SelectItem value="latest">최신 분기</SelectItem>
                {QUARTERS.map((q) => (
                  <SelectItem key={q.value} value={q.value}>
                    {q.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* 비교 모드 토글 */}
        <div className="flex flex-col gap-2">
          <button
            onClick={() => setComparisonMode(!comparisonMode)}
            className={`flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
              comparisonMode
                ? "bg-indigo-600 text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:border-white/20 dark:bg-gray-800 dark:text-white/60 dark:hover:bg-gray-700 dark:hover:text-white"
            }`}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            분기 비교 {comparisonMode ? "ON" : "OFF"}
          </button>
        </div>

        {/* 소셜 트렌드 토글 (M9) */}
        <div className="flex flex-col gap-2">
          <button
            onClick={toggleSocial}
            className={`flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
              socialEnabled
                ? "bg-purple-600 text-white"
                : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:border-white/20 dark:bg-gray-800 dark:text-white/60 dark:hover:bg-gray-700 dark:hover:text-white"
            }`}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
            </svg>
            소셜 트렌드 {socialEnabled ? "ON" : "OFF"}
          </button>
        </div>

        {/* 비교 모드: Before / After 분기 선택 */}
        {comparisonMode && (
          <>
            <div className="flex flex-col gap-2">
              <Label className="text-xs text-slate-500 dark:text-white/60">비교 업종 기준</Label>
              <div className="flex gap-2">
                <button
                  onClick={() => setCompareCategoryMode("all")}
                  className={`flex-1 rounded-md px-3 py-2 text-xs font-medium transition ${
                    compareCategoryMode === "all"
                      ? "bg-blue-600 text-white"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:border-white/20 dark:bg-gray-800 dark:text-white/60 dark:hover:bg-gray-700 dark:hover:text-white"
                  }`}
                >
                  전체 업종
                </button>
                <button
                  onClick={() => setCompareCategoryMode("selected")}
                  className={`flex-1 rounded-md px-3 py-2 text-xs font-medium transition ${
                    compareCategoryMode === "selected"
                      ? "bg-indigo-600 text-white"
                      : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:border-white/20 dark:bg-gray-800 dark:text-white/60 dark:hover:bg-gray-700 dark:hover:text-white"
                  }`}
                >
                  선택 업종
                </button>
              </div>
              <p className="text-[10px] text-slate-400 dark:text-white/40">
                선택 업종은 위의 업종 필터를 기준으로 비교합니다.
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <Label className="text-xs text-indigo-600 dark:text-violet-300">Before 분기</Label>
              <Select value={compareQtrBefore} onValueChange={setCompareQtrBefore}>
                <SelectTrigger className="border-indigo-200 bg-white text-sm text-slate-900 dark:border-violet-500/30 dark:bg-gray-800 dark:text-white">
                  <SelectValue placeholder="이전 분기 선택" />
                </SelectTrigger>
                <SelectContent className="bg-white text-slate-900 dark:bg-gray-800 dark:text-white">
                  {QUARTERS.map((q) => (
                    <SelectItem key={q.value} value={q.value}>
                      {q.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label className="text-xs text-indigo-600 dark:text-violet-300">After 분기</Label>
              <Select value={compareQtrAfter} onValueChange={setCompareQtrAfter}>
                <SelectTrigger className="border-indigo-200 bg-white text-sm text-slate-900 dark:border-violet-500/30 dark:bg-gray-800 dark:text-white">
                  <SelectValue placeholder="이후 분기 선택" />
                </SelectTrigger>
                <SelectContent className="bg-white text-slate-900 dark:bg-gray-800 dark:text-white">
                  {QUARTERS.map((q) => (
                    <SelectItem key={q.value} value={q.value}>
                      {q.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
