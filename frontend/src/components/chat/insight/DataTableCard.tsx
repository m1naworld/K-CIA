"use client";

import { Table } from "lucide-react";

interface DataTableItem {
  rank?: number;
  area_name: string;
  value: string;
  description?: string;
  unit?: string;
}

interface DataTableCardProps {
  data: DataTableItem[];
}

export function DataTableCard({ data }: DataTableCardProps) {
  if (!data || data.length === 0) return null;

  return (
    <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-3 text-slate-900 dark:text-white">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-blue-400">
        <Table className="h-3.5 w-3.5" />
        <span>데이터</span>
      </div>
      <div className="space-y-2">
        {data.map((item, idx) => (
          <div
            key={idx}
            className="flex flex-col gap-1 rounded bg-white/80 px-2 py-1.5 dark:bg-gray-800/50"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="min-w-0 break-words text-sm font-medium text-slate-900 dark:text-white/90">
                {item.rank ? `${item.rank}. ` : ""}{item.area_name}
              </span>
              <span className="shrink-0 text-sm font-semibold text-blue-400">
                {item.value}{item.unit ? ` ${item.unit}` : ""}
              </span>
            </div>
            {item.description && (
              <span className="break-words text-xs text-slate-500 dark:text-white/60">{item.description}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
