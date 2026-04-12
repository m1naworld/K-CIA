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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { trackEvent } from "@/lib/analytics";
import ThemeToggle from "@/components/common/ThemeToggle";

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
const sectionClass =
  "intel-panel-soft rounded-[1.35rem] p-3.5";
const selectTriggerClass =
  "intel-control h-11 rounded-xl border-0 bg-transparent text-sm text-foreground shadow-none";
const selectContentClass =
  "intel-panel rounded-2xl border-0 bg-popover text-popover-foreground";

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
    <Card className="intel-panel intel-scroll h-full w-[18.5rem] shrink-0 overflow-y-auto rounded-none border-0 border-r border-border/70 bg-transparent text-foreground">
      <CardHeader className="border-b border-border/70 pb-5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-3">
            <div className="intel-kicker">Geo Intelligence Filters</div>
            <div>
              <CardTitle className="intel-title text-lg font-semibold text-foreground">
                성수동 브리핑 컨트롤
              </CardTitle>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                업종, 기준 분기, 비교 조건을 조정하면 지도와 브리핑 패널이 같은 컨텍스트로
                함께 갱신됩니다.
              </p>
            </div>
          </div>
          <ThemeToggle />
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge
            variant="outline"
            className="intel-badge-primary rounded-full text-[10px] font-medium uppercase tracking-[0.16em]"
          >
            AI Consultant
          </Badge>
          <Badge
            variant="outline"
            className="intel-badge-accent rounded-full text-[10px] font-medium uppercase tracking-[0.16em]"
          >
            Quarter Compare
          </Badge>
          {socialEnabled && (
            <Badge
              variant="outline"
              className="intel-badge-success rounded-full text-[10px] font-medium uppercase tracking-[0.16em]"
            >
              Social Signal
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 py-5">
        <div className={sectionClass}>
          <Label className="intel-kicker text-[11px]">업종</Label>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            업종을 좁히면 지도 높이, 카드 지표, AI 답변이 같은 기준으로 정렬됩니다.
          </p>
          <Select value={category} onValueChange={handleCategoryChange}>
            <SelectTrigger className={cn(selectTriggerClass, "mt-3")}>
              <SelectValue placeholder="전체 업종" />
            </SelectTrigger>
            <SelectContent className={selectContentClass}>
              <SelectItem value="all">전체 업종</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.service_code} value={cat.service_code}>
                  {cat.service_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {!comparisonMode && (
          <div className={sectionClass}>
            <Label className="intel-kicker text-[11px]">기준 분기</Label>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">
              기본 브리핑은 선택한 분기 단일 기준으로 해석됩니다.
            </p>
            <Select value={quarter} onValueChange={handleQuarterChange}>
              <SelectTrigger className={cn(selectTriggerClass, "mt-3")}>
                <SelectValue placeholder="최신 분기" />
              </SelectTrigger>
              <SelectContent className={selectContentClass}>
                <SelectItem value="latest">최신 분기</SelectItem>
                {QUARTERS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className={sectionClass}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <Label className="intel-kicker text-[11px]">분기 비교</Label>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                전후 분기를 직접 비교해서 입지 변화와 리스크를 더 선명하게 확인합니다.
              </p>
            </div>
            <Button
              type="button"
              variant={comparisonMode ? "default" : "outline"}
              onClick={() => setComparisonMode(!comparisonMode)}
              className={cn(
                "h-10 rounded-full px-4 shadow-none",
                comparisonMode
                  ? "intel-button-accent"
                  : "intel-control border-0 bg-transparent text-foreground/80 hover:text-foreground"
              )}
            >
              {comparisonMode ? "ON" : "OFF"}
            </Button>
          </div>
        </div>

        <div className={sectionClass}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <Label className="intel-kicker text-[11px]">소셜 트렌드</Label>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                화제성과 지역 반응을 함께 읽어 정량 지표와 정성 신호를 연결합니다.
              </p>
            </div>
            <Button
              type="button"
              variant={socialEnabled ? "default" : "outline"}
              onClick={toggleSocial}
              className={cn(
                "h-10 rounded-full px-4 shadow-none",
                socialEnabled
                  ? "intel-button-primary"
                  : "intel-control border-0 bg-transparent text-foreground/80 hover:text-foreground"
              )}
            >
              {socialEnabled ? "ON" : "OFF"}
            </Button>
          </div>
        </div>

        {comparisonMode && (
          <>
            <div className={sectionClass}>
              <Label className="intel-kicker text-[11px]">비교 기준</Label>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant={compareCategoryMode === "all" ? "default" : "outline"}
                  onClick={() => setCompareCategoryMode("all")}
                  className={cn(
                    "h-11 rounded-xl px-3 text-xs shadow-none",
                    compareCategoryMode === "all"
                      ? "intel-button-accent"
                      : "intel-control border-0 bg-transparent text-foreground/80 hover:text-foreground"
                  )}
                >
                  전체 업종
                </Button>
                <Button
                  type="button"
                  variant={compareCategoryMode === "selected" ? "default" : "outline"}
                  onClick={() => setCompareCategoryMode("selected")}
                  className={cn(
                    "h-11 rounded-xl px-3 text-xs shadow-none",
                    compareCategoryMode === "selected"
                      ? "intel-button-primary"
                      : "intel-control border-0 bg-transparent text-foreground/80 hover:text-foreground"
                  )}
                >
                  선택 업종
                </Button>
              </div>
              <p className="mt-3 text-[11px] leading-5 text-muted-foreground">
                선택 업종 모드는 상단 업종 필터를 그대로 비교 기준으로 사용합니다.
              </p>
            </div>

            <div className={sectionClass}>
              <Label className="intel-kicker text-[11px]">Before 분기</Label>
              <Select value={compareQtrBefore} onValueChange={setCompareQtrBefore}>
                <SelectTrigger className={cn(selectTriggerClass, "mt-3")}>
                  <SelectValue placeholder="이전 분기 선택" />
                </SelectTrigger>
                <SelectContent className={selectContentClass}>
                  {QUARTERS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className={sectionClass}>
              <Label className="intel-kicker text-[11px]">After 분기</Label>
              <Select value={compareQtrAfter} onValueChange={setCompareQtrAfter}>
                <SelectTrigger className={cn(selectTriggerClass, "mt-3")}>
                  <SelectValue placeholder="이후 분기 선택" />
                </SelectTrigger>
                <SelectContent className={selectContentClass}>
                  {QUARTERS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
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
