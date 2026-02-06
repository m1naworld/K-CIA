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
import { trackEvent } from "@/lib/analytics";

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
    areaType,
    category,
    quarter,
    categories,
    setAreaType,
    setCategory,
    setQuarter,
    fetchCategories,
    fetchAreas,
  } = useMapStore();

  useEffect(() => {
    fetchCategories();
    fetchAreas();
  }, [fetchCategories, fetchAreas]);

  const handleAreaTypeChange = (nextType: "COMMERCIAL_AREA" | "ADMIN_DONG") => {
    setAreaType(nextType);
    trackEvent("FILTER_APPLY", {
      filter_type: "area_type",
      value: nextType,
      area_type: nextType,
      category,
      qtr: quarter,
    });
  };

  const handleCategoryChange = (nextCategory: string) => {
    setCategory(nextCategory);
    trackEvent("FILTER_APPLY", {
      filter_type: "category",
      value: nextCategory,
      area_type: areaType,
      category: nextCategory,
      qtr: quarter,
    });
  };

  const handleQuarterChange = (nextQuarter: string) => {
    setQuarter(nextQuarter);
    trackEvent("FILTER_APPLY", {
      filter_type: "qtr",
      value: nextQuarter,
      area_type: areaType,
      category,
      qtr: nextQuarter,
    });
  };

  return (
    <Card className="h-full w-72 shrink-0 overflow-y-auto rounded-none border-0 border-r border-white/10 bg-gray-900 text-white">
      <CardHeader className="pb-4">
        <CardTitle className="text-base font-semibold">필터</CardTitle>
        <Badge variant="outline" className="w-fit text-[10px] text-white/50">
          성수동 상권 분석
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {/* 영역 타입 토글 */}
        <div className="flex flex-col gap-2">
          <Label className="text-xs text-white/60">영역 기준</Label>
          <div className="flex gap-1">
            <Button
              variant={areaType === "COMMERCIAL_AREA" ? "default" : "outline"}
              size="sm"
              className="flex-1 text-xs"
              onClick={() => handleAreaTypeChange("COMMERCIAL_AREA")}
            >
              상권
            </Button>
            <Button
              variant={areaType === "ADMIN_DONG" ? "default" : "outline"}
              size="sm"
              className="flex-1 text-xs"
              onClick={() => handleAreaTypeChange("ADMIN_DONG")}
            >
              행정동
            </Button>
          </div>
        </div>

        {/* 업종 선택 */}
        <div className="flex flex-col gap-2">
          <Label className="text-xs text-white/60">업종</Label>
          <Select value={category} onValueChange={handleCategoryChange}>
            <SelectTrigger className="border-white/20 bg-gray-800 text-sm text-white">
              <SelectValue placeholder="전체 업종" />
            </SelectTrigger>
            <SelectContent className="max-h-60 bg-gray-800 text-white">
              <SelectItem value="all">전체 업종</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.service_code} value={cat.service_code}>
                  {cat.service_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 분기 선택 */}
        <div className="flex flex-col gap-2">
          <Label className="text-xs text-white/60">기준 분기</Label>
          <Select value={quarter} onValueChange={handleQuarterChange}>
            <SelectTrigger className="border-white/20 bg-gray-800 text-sm text-white">
              <SelectValue placeholder="최신 분기" />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 text-white">
              <SelectItem value="latest">최신 분기</SelectItem>
              {QUARTERS.map((q) => (
                <SelectItem key={q.value} value={q.value}>
                  {q.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
