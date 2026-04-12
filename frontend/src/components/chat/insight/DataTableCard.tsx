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
    <div className="intel-surface-primary rounded-lg border p-3 text-foreground">
      <div className="intel-text-primary mb-2 flex items-center gap-2 text-xs font-medium">
        <Table className="h-3.5 w-3.5" />
        <span>데이터</span>
      </div>
      <div className="space-y-2">
        {data.map((item, idx) => (
          <div
            key={idx}
            className="flex flex-col gap-1 rounded bg-background/80 px-2 py-1.5"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="min-w-0 break-words text-sm font-medium text-foreground">
                {item.rank ? `${item.rank}. ` : ""}{item.area_name}
              </span>
              <span className="intel-text-primary shrink-0 text-sm font-semibold">
                {item.value}{item.unit ? ` ${item.unit}` : ""}
              </span>
            </div>
            {item.description && (
              <span className="break-words text-xs text-muted-foreground">{item.description}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
