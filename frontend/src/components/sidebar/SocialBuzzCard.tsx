"use client";

import { Badge } from "@/components/ui/badge";
import type { SocialTrendsResponse } from "@/types/social";

const SOURCE_LABELS: Record<string, string> = {
  youtube: "YouTube",
  naver_blog: "네이버 블로그",
  naver_cafe: "네이버 카페",
};

const SOURCE_COLORS: Record<string, string> = {
  youtube: "bg-red-500/20 text-red-400",
  naver_blog: "bg-green-500/20 text-green-400",
  naver_cafe: "bg-emerald-500/20 text-emerald-400",
};

function SentimentBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-white/40">N/A</span>;
  // -1 ~ 1 → 0% ~ 100%
  const pct = Math.round((score + 1) * 50);
  const color =
    score > 0.3
      ? "bg-emerald-400"
      : score < -0.3
        ? "bg-red-400"
        : "bg-amber-400";
  const label = score > 0.3 ? "긍정" : score < -0.3 ? "부정" : "중립";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-white/10">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-white/60">
        {label} ({(score * 100).toFixed(0)}%)
      </span>
    </div>
  );
}

export default function SocialBuzzCard({
  data,
}: {
  data: SocialTrendsResponse;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-white/[0.03]">
      {/* Header */}
      <div className="mb-2 flex items-center gap-2">
        <svg
          className="h-4 w-4 text-purple-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
          />
        </svg>
        <span className="text-xs font-semibold text-slate-900 dark:text-white">
          소셜 트렌드
        </span>
        <span className="text-[10px] text-slate-500 dark:text-white/40">
          최근 30일
        </span>
      </div>

      {/* Filter context badges */}
      <div className="mb-2 flex flex-wrap gap-1">
        <Badge
          variant="outline"
          className="border-purple-500/30 text-[10px] text-purple-300"
        >
          {data.filtered_area ?? "성수동 전체"}
        </Badge>
        {data.filtered_category && (
          <Badge
            variant="outline"
            className="border-blue-500/30 text-[10px] text-blue-300"
          >
            {data.filtered_category}
          </Badge>
        )}
        {data.is_fallback && (
          <Badge
            variant="outline"
            className="border-amber-500/30 text-[10px] text-amber-300"
          >
            해당 상권 데이터 부족 · 전체 표시
          </Badge>
        )}
      </div>

      {/* Buzz Volume */}
      <div className="mb-2 flex items-baseline gap-2">
        <span className="text-lg font-bold text-purple-400">
          {data.total_buzz.toLocaleString()}
        </span>
        <span className="text-[10px] text-slate-500 dark:text-white/40">
          건 언급
        </span>
      </div>

      {/* Sentiment */}
      <div className="mb-3">
        <p className="mb-1 text-[10px] text-slate-500 dark:text-white/40">
          감성 분석
        </p>
        <SentimentBar score={data.avg_sentiment} />
        <div className="mt-1 flex gap-3 text-[10px]">
          <span className="text-emerald-400">
            긍정 {data.total_pos}
          </span>
          <span className="text-red-400">
            부정 {data.total_neg}
          </span>
        </div>
      </div>

      {/* Source breakdown */}
      <div className="mb-3">
        <p className="mb-1 text-[10px] text-slate-500 dark:text-white/40">
          소스별
        </p>
        <div className="flex flex-wrap gap-1">
          {data.by_source.map((s) => (
            <Badge
              key={s.source}
              variant="secondary"
              className={`text-[10px] ${SOURCE_COLORS[s.source] ?? "bg-white/10 text-white/70"}`}
            >
              {SOURCE_LABELS[s.source] ?? s.source} {s.buzz}
            </Badge>
          ))}
        </div>
      </div>

      {/* Top Keywords */}
      {data.top_keywords.length > 0 && (
        <div className="mb-3">
          <p className="mb-1 text-[10px] text-slate-500 dark:text-white/40">
            TOP 키워드
          </p>
          <div className="flex flex-wrap gap-1">
            {data.top_keywords.slice(0, 8).map((kw) => (
              <Badge
                key={kw}
                variant="outline"
                className="border-purple-500/30 text-[10px] text-purple-300"
              >
                {kw}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Snippets */}
      {data.evidence_snippets.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] text-slate-500 dark:text-white/40">
            최근 언급
          </p>
          <div className="space-y-1.5">
            {data.evidence_snippets.slice(0, 3).map((ev, i) => (
              <a
                key={i}
                href={ev.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded border border-slate-200 p-1.5 transition-colors hover:border-purple-500/30 dark:border-white/5 dark:hover:border-purple-500/30"
              >
                <div className="flex items-center gap-1">
                  <Badge
                    variant="secondary"
                    className={`text-[8px] ${SOURCE_COLORS[ev.source] ?? "bg-white/10 text-white/70"}`}
                  >
                    {SOURCE_LABELS[ev.source] ?? ev.source}
                  </Badge>
                  <span className="text-[9px] text-slate-500 dark:text-white/30">
                    {ev.published_at}
                  </span>
                </div>
                <p className="mt-0.5 line-clamp-2 text-[11px] text-slate-700 dark:text-white/70">
                  {ev.title.replace(/<[^>]+>/g, "")}
                </p>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Mini trend chart placeholder */}
      {data.daily_trend.length > 1 && (
        <div className="mt-2">
          <p className="mb-1 text-[10px] text-slate-500 dark:text-white/40">
            일별 버즈 추이
          </p>
          <div className="flex h-8 items-end gap-px">
            {data.daily_trend.slice(-14).map((d, i) => {
              const max = Math.max(...data.daily_trend.slice(-14).map((x) => x.buzz), 1);
              const h = Math.max((d.buzz / max) * 100, 4);
              return (
                <div
                  key={i}
                  className="flex-1 rounded-t bg-purple-400/60"
                  style={{ height: `${h}%` }}
                  title={`${d.date}: ${d.buzz}건`}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
