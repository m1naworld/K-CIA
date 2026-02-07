"use client";

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
import { usePortfolioStore } from "@/store/portfolioStore";

export default function ABCompare() {
  const {
    assets,
    selectedAssetA,
    selectedAssetB,
    compareResult,
    setSelectedAssets,
    fetchCompare,
  } = usePortfolioStore();

  const handleCompare = () => {
    if (selectedAssetA !== null && selectedAssetB !== null) {
      fetchCompare(selectedAssetA, selectedAssetB);
    }
  };

  return (
    <Card className="bg-gray-900/60 border-white/10 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-white/80">
          A/B 비교
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {/* Asset Selectors */}
        <div className="flex items-center gap-2">
          <Select
            value={selectedAssetA?.toString() ?? ""}
            onValueChange={(v) => setSelectedAssets(Number(v), selectedAssetB)}
          >
            <SelectTrigger className="h-8 border-white/20 bg-gray-800 text-xs text-white">
              <SelectValue placeholder="점포 A" />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 text-white">
              {assets.map((a) => (
                <SelectItem key={a.asset_id} value={a.asset_id.toString()}>
                  {a.area_name ?? a.address}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-xs text-white/40">vs</span>
          <Select
            value={selectedAssetB?.toString() ?? ""}
            onValueChange={(v) => setSelectedAssets(selectedAssetA, Number(v))}
          >
            <SelectTrigger className="h-8 border-white/20 bg-gray-800 text-xs text-white">
              <SelectValue placeholder="점포 B" />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 text-white">
              {assets.map((a) => (
                <SelectItem key={a.asset_id} value={a.asset_id.toString()}>
                  {a.area_name ?? a.address}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="w-full text-xs"
          onClick={handleCompare}
          disabled={selectedAssetA === null || selectedAssetB === null}
        >
          비교하기
        </Button>

        {/* Comparison Results */}
        {compareResult && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-white/80">{compareResult.verdict}</p>

            <div className="space-y-1.5">
              {compareResult.factors.map((f, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-white/50">{f.metric}</span>
                  <div className="flex items-center gap-2">
                    <span className={f.winner === "A" ? "font-medium text-blue-400" : "text-white/40"}>
                      {f.a_value !== null ? f.a_value.toFixed(1) : "-"}
                    </span>
                    <span className="text-[10px] text-white/20">vs</span>
                    <span className={f.winner === "B" ? "font-medium text-purple-400" : "text-white/40"}>
                      {f.b_value !== null ? f.b_value.toFixed(1) : "-"}
                    </span>
                    <Badge
                      variant="outline"
                      className={`text-[10px] ${
                        f.winner === "A" ? "text-blue-400" : "text-purple-400"
                      }`}
                    >
                      {f.winner}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
