"use client";

import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types/chat";
import { EvidenceCard } from "./insight/EvidenceCard";
import { RisksCard } from "./insight/RisksCard";
import { RecommendationsCard } from "./insight/RecommendationsCard";
import { ActionItemsCard } from "./insight/ActionItemsCard";
import { ChecklistCard } from "./insight/ChecklistCard";
import { SqlCard } from "./insight/SqlCard";
import { InsightsCard } from "./insight/InsightsCard";
import { DataTableCard } from "./insight/DataTableCard";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg bg-blue-600 px-3 py-2 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex flex-col gap-2">
      {/* Streaming indicator */}
      {message.isStreaming && !message.insight && !message.sql && (
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-white/60">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>
            {message.route === "sql"
              ? "SQL 쿼리 실행 중..."
              : message.route === "insight"
                ? "인사이트 분석 중..."
                : message.route === "both"
                  ? "분석 중..."
                  : "응답 준비 중..."}
          </span>
        </div>
      )}

      {/* Error message */}
      {message.error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {message.error}
        </div>
      )}

      {message.categoryInfo?.source === "inferred" && (
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="border-slate-200 bg-slate-100 text-[10px] text-slate-500 dark:border-white/20 dark:bg-gray-800/50 dark:text-white/50"
          >
            업종 자동 적용: {message.categoryInfo.service_name}
          </Badge>
        </div>
      )}

      {/* SQL Card */}
      {message.sql && <SqlCard sql={message.sql} />}

      {/* Summary */}
      {message.content && !message.error && (
        <div className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-900 dark:bg-gray-800/60 dark:text-white/90">
          {message.content}
        </div>
      )}

      {/* Insight Cards - only show if data exists */}
      {message.insight && (
        <div className="flex flex-col gap-2">
          {/* Data Table (for data_lookup responses) */}
          {message.insight.data_table && message.insight.data_table.length > 0 && (
            <DataTableCard data={message.insight.data_table} />
          )}
          {/* Insights (analysis/interpretation) */}
          {message.insight.insights && message.insight.insights.length > 0 && (
            <InsightsCard insights={message.insight.insights} />
          )}
          {message.insight.evidence && message.insight.evidence.length > 0 && (
            <EvidenceCard evidence={message.insight.evidence} />
          )}
          {message.insight.risks && message.insight.risks.length > 0 && (
            <RisksCard risks={message.insight.risks} />
          )}
          {message.insight.recommendations && message.insight.recommendations.length > 0 && (
            <RecommendationsCard recommendations={message.insight.recommendations} />
          )}
          {message.insight.action_items && message.insight.action_items.length > 0 && (
            <ActionItemsCard actionItems={message.insight.action_items} />
          )}
          {message.insight.checklist && message.insight.checklist.length > 0 && (
            <ChecklistCard checklist={message.insight.checklist} />
          )}
        </div>
      )}

      {/* Data as-of badge */}
      {message.dataAsof && !message.isStreaming && (
        <div className="flex justify-end">
          <Badge
            variant="outline"
            className="border-slate-200 bg-slate-100 text-[10px] text-slate-500 dark:border-white/20 dark:bg-gray-800/50 dark:text-white/50"
          >
            기준: {message.dataAsof}
          </Badge>
        </div>
      )}
    </div>
  );
}
