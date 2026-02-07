"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PeaktimeAnalysis } from "@/types/map";

interface PeaktimeCardProps {
  data: PeaktimeAnalysis;
}

export default function PeaktimeCard({ data }: PeaktimeCardProps) {
  const formatHour = (h: number) => `${h}시`;

  // Build hourly bar chart data
  const hourlyEntries = Object.entries(data.hourly_pattern || {})
    .map(([k, v]) => ({ hour: parseInt(k, 10), value: v }))
    .sort((a, b) => a.hour - b.hour);

  const maxValue = Math.max(...hourlyEntries.map((e) => e.value), 1);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          피크타임 분석
          <Badge variant="outline" className="text-xs">{data.qtr}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {/* Peak / Off-peak */}
        <div className="flex gap-4">
          <div>
            <span className="text-muted-foreground">피크</span>
            <div className="flex gap-1 mt-1">
              {data.peak_hours.map((h) => (
                <Badge key={h} className="bg-red-500/20 text-red-400 text-xs">
                  {formatHour(h)}
                </Badge>
              ))}
            </div>
          </div>
          <div>
            <span className="text-muted-foreground">오프피크</span>
            <div className="flex gap-1 mt-1">
              {data.off_peak_hours.map((h) => (
                <Badge key={h} variant="outline" className="text-xs">
                  {formatHour(h)}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {/* Hourly mini chart */}
        {hourlyEntries.length > 0 && (
          <div>
            <span className="text-muted-foreground">시간대별 유동인구</span>
            <div className="flex items-end gap-[1px] mt-1 h-12">
              {hourlyEntries.map((e) => (
                <div
                  key={e.hour}
                  className="flex-1 rounded-t-sm"
                  style={{
                    height: `${(e.value / maxValue) * 100}%`,
                    backgroundColor: data.peak_hours.includes(e.hour)
                      ? "rgb(239 68 68 / 0.7)"
                      : "rgb(148 163 184 / 0.4)",
                  }}
                  title={`${e.hour}시: ${e.value.toLocaleString()}명`}
                />
              ))}
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
              <span>0시</span>
              <span>6시</span>
              <span>12시</span>
              <span>18시</span>
              <span>23시</span>
            </div>
          </div>
        )}

        {/* Weekday pattern */}
        {Object.keys(data.weekday_pattern || {}).length > 0 && (
          <div>
            <span className="text-muted-foreground">요일별 유동인구</span>
            <div className="grid grid-cols-7 gap-1 mt-1">
              {Object.entries(data.weekday_pattern).map(([day, val]) => (
                <div key={day} className="text-center">
                  <div className="text-[10px] text-muted-foreground">{day}</div>
                  <div className="text-xs font-medium">
                    {(val / 10000).toFixed(0)}만
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total */}
        {data.flow_total && (
          <div className="text-muted-foreground">
            분기 총 유동인구: {(data.flow_total / 10000).toFixed(1)}만명
          </div>
        )}
      </CardContent>
    </Card>
  );
}
