"use client";

import { useMapStore } from "@/store/mapStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import CompareChart from "@/components/charts/CompareChart";
import type { CompareResponse } from "@/types/map";

interface ComparePanelProps {
  data: CompareResponse | null;
}

function generateQuarters(): { value: string; label: string }[] {
  const quarters: { value: string; label: string }[] = [];
  const now = new Date();
  let year = now.getFullYear();
  let q = Math.ceil((now.getMonth() + 1) / 3);
  for (let i = 0; i < 8; i++) {
    quarters.push({ value: `${year}${q}`, label: `${year}년 ${q}분기` });
    q--;
    if (q === 0) { q = 4; year--; }
  }
  return quarters;
}

const QUARTERS = generateQuarters();

export default function ComparePanel({ data }: ComparePanelProps) {
  const {
    compareQtr1,
    compareQtr2,
    selectedHex,
    setCompareQtrs,
    fetchCompare,
  } = useMapStore();

  const handleCompare = () => {
    if (selectedHex && compareQtr1 && compareQtr2) {
      fetchCompare(selectedHex);
    }
  };

  return (
    <Card className="bg-gray-900/60 border-white/10 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-white/80">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          분기 비교
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {/* Quarter Selectors */}
        <div className="flex items-center gap-2">
          <Select value={compareQtr1} onValueChange={(v) => setCompareQtrs(v, compareQtr2)}>
            <SelectTrigger className="h-8 border-white/20 bg-gray-800 text-xs text-white">
              <SelectValue placeholder="이전 분기" />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 text-white">
              {QUARTERS.map((q) => (
                <SelectItem key={q.value} value={q.value}>{q.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-xs text-white/40">vs</span>
          <Select value={compareQtr2} onValueChange={(v) => setCompareQtrs(compareQtr1, v)}>
            <SelectTrigger className="h-8 border-white/20 bg-gray-800 text-xs text-white">
              <SelectValue placeholder="이후 분기" />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 text-white">
              {QUARTERS.map((q) => (
                <SelectItem key={q.value} value={q.value}>{q.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="w-full text-xs"
          onClick={handleCompare}
          disabled={!compareQtr1 || !compareQtr2 || !selectedHex}
        >
          비교하기
        </Button>

        {/* Comparison Results */}
        {data && (
          <>
            <CompareChart
              comparisons={data.comparisons}
              qtr1={data.qtr1}
              qtr2={data.qtr2}
            />

            {/* Above/Below Average Badges */}
            <div className="flex flex-wrap gap-1">
              {data.comparisons.map((c) => (
                <Badge
                  key={c.metric}
                  variant="outline"
                  className={`text-[10px] ${
                    c.above_avg
                      ? "border-emerald-500/50 text-emerald-400"
                      : "border-red-500/50 text-red-400"
                  }`}
                >
                  {c.metric === "sales_amt" ? "매출" :
                   c.metric === "flow_total" ? "유동" :
                   c.metric === "store_cnt" ? "점포" : c.metric}
                  {c.above_avg ? " 평균 이상" : " 평균 이하"}
                </Badge>
              ))}
            </div>

            <p className="text-[10px] text-white/30">
              기준: {data.data_asof}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
