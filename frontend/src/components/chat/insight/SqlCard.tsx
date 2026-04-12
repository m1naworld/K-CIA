"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Database, ChevronDown, ChevronUp, Copy, Check } from "lucide-react";
import type { SqlEvent } from "@/types/chat";

interface SqlCardProps {
  sql: SqlEvent;
}

export function SqlCard({ sql }: SqlCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql.sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="intel-panel-soft w-full min-w-0 text-foreground">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="intel-text-primary flex items-center gap-2 text-sm font-medium">
            <Database className="h-4 w-4" />
            SQL 쿼리
            <span className="text-xs text-slate-500 dark:text-white/50">
              ({sql.row_count}행 반환)
            </span>
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-slate-500 hover:text-slate-900 dark:text-white/50 dark:hover:text-white"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="intel-text-success h-3.5 w-3.5" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-slate-500 hover:text-slate-900 dark:text-white/50 dark:hover:text-white"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      {isExpanded && (
        <CardContent className="pt-0">
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded bg-[hsl(var(--foreground))] p-2 text-[10px] text-[hsl(var(--intel-cream))]">
            <code>{sql.sql}</code>
          </pre>
        </CardContent>
      )}
    </Card>
  );
}
