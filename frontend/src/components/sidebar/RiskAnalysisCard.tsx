"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { RiskAnalysis } from "@/types/map";

interface RiskAnalysisCardProps {
  data: RiskAnalysis;
}

function riskColor(score: number): string {
  if (score >= 70) return "text-red-400";
  if (score >= 40) return "text-amber-400";
  return "text-emerald-400";
}

function riskBg(score: number): string {
  if (score >= 70) return "bg-red-500/20 border-red-500/30";
  if (score >= 40) return "bg-amber-500/20 border-amber-500/30";
  return "bg-emerald-500/20 border-emerald-500/30";
}

function riskLabel(score: number): string {
  if (score >= 70) return "위험";
  if (score >= 40) return "주의";
  return "양호";
}

export default function RiskAnalysisCard({ data }: RiskAnalysisCardProps) {
  const factors = [
    { label: "폐업률", value: data.close_rate, format: (v: number) => `${(v * 100).toFixed(1)}%` },
    { label: "매출 QoQ", value: data.sales_qoq, format: (v: number) => `${(v * 100).toFixed(1)}%` },
    { label: "점포 증가율", value: data.store_growth, format: (v: number) => `${(v * 100).toFixed(1)}%` },
    { label: "유동인구 QoQ", value: data.flow_qoq, format: (v: number) => `${(v * 100).toFixed(1)}%` },
  ];

  return (
    <Card className={`${riskBg(data.risk_score)} backdrop-blur-sm`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-white/80">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            리스크 진단
          </CardTitle>
          <Badge variant="outline" className={`text-xs ${riskColor(data.risk_score)}`}>
            {riskLabel(data.risk_score)} ({data.risk_score.toFixed(0)}점)
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {/* Risk Score Gauge */}
        <div className="relative h-2 w-full rounded-full bg-white/10">
          <div
            className="absolute left-0 top-0 h-full rounded-full transition-all"
            style={{
              width: `${Math.min(data.risk_score, 100)}%`,
              backgroundColor:
                data.risk_score >= 70
                  ? "rgb(239 68 68 / 0.8)"
                  : data.risk_score >= 40
                    ? "rgb(245 158 11 / 0.8)"
                    : "rgb(16 185 129 / 0.8)",
            }}
          />
        </div>

        {/* Risk Factors */}
        {data.risk_factors.length > 0 && (
          <div>
            <p className="mb-1.5 text-[10px] text-white/40">위험 요인</p>
            <ul className="space-y-1">
              {data.risk_factors.map((factor, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-amber-300/90">
                  <span className="mt-0.5 shrink-0">!</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Factor Breakdown */}
        <div>
          <p className="mb-1.5 text-[10px] text-white/40">지표 분해</p>
          <div className="space-y-1.5">
            {factors.map(({ label, value, format }) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-white/50">{label}</span>
                <span className={`font-medium ${value !== null && value !== undefined ? (value < 0 ? "text-red-400" : "text-white") : "text-white/30"}`}>
                  {value !== null && value !== undefined ? format(value) : "-"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Alternative Areas */}
        {data.alternative_areas && data.alternative_areas.length > 0 && (
          <div>
            <p className="mb-1.5 text-[10px] text-white/40">대안 구역 제안</p>
            <div className="space-y-1.5">
              {data.alternative_areas.map((alt) => (
                <div
                  key={alt.h3_index}
                  className="flex items-center justify-between rounded-md border border-white/5 bg-white/5 px-2 py-1.5"
                >
                  <div>
                    <p className="text-xs font-medium text-white/80">
                      {alt.real_name ?? alt.area_name ?? alt.h3_index.slice(-6)}
                    </p>
                    {alt.sales_amt && (
                      <p className="text-[10px] text-white/40">
                        매출 {(alt.sales_amt / 10000).toFixed(0)}만원
                      </p>
                    )}
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${riskColor(alt.risk_score)}`}
                  >
                    {alt.risk_score.toFixed(0)}점
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
