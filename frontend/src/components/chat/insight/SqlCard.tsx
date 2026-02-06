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
    <Card className="border-cyan-500/30 bg-gray-900/60 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-cyan-400">
            <Database className="h-4 w-4" />
            SQL 쿼리
            <span className="text-xs text-white/50">
              ({sql.row_count}행 반환)
            </span>
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-white/50 hover:text-white"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-white/50 hover:text-white"
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
          <pre className="overflow-x-auto rounded bg-gray-950 p-2 text-[10px] text-cyan-300/80">
            <code>{sql.sql}</code>
          </pre>
        </CardContent>
      )}
    </Card>
  );
}
