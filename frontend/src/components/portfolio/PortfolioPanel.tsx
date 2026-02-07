"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { usePortfolioStore } from "@/store/portfolioStore";
import type { AssetHealth } from "@/types/map";

const HEALTH_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  green: { bg: "bg-emerald-500/20", text: "text-emerald-400", label: "양호" },
  yellow: { bg: "bg-amber-500/20", text: "text-amber-400", label: "주의" },
  red: { bg: "bg-red-500/20", text: "text-red-400", label: "위험" },
};

function HealthCard({ asset }: { asset: AssetHealth }) {
  const style = HEALTH_STYLES[asset.health_status] ?? HEALTH_STYLES.green;

  return (
    <Card className={`${style.bg} border-white/10`}>
      <CardContent className="p-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-medium text-white/80">
            {asset.area_name ?? asset.address}
          </p>
          <Badge variant="outline" className={`text-[10px] ${style.text}`}>
            {style.label} ({asset.health_score.toFixed(0)})
          </Badge>
        </div>
        <p className="text-[10px] text-white/40">{asset.address}</p>

        {/* Z-scores */}
        <div className="mt-2 grid grid-cols-4 gap-2">
          {[
            { label: "수요", value: asset.demand_z },
            { label: "경쟁", value: asset.competition_z },
            { label: "성장", value: asset.growth_z },
            { label: "리스크", value: asset.risk_z },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <p className="text-[10px] text-white/40">{label}</p>
              <p className={`text-xs font-medium ${
                value !== null && value !== undefined
                  ? value >= 0 ? "text-emerald-400" : "text-red-400"
                  : "text-white/30"
              }`}>
                {value !== null && value !== undefined ? value.toFixed(1) : "-"}
              </p>
            </div>
          ))}
        </div>

        {/* Top Factors */}
        {asset.top_factors.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {asset.top_factors.map((f, i) => (
              <Badge key={i} variant="outline" className="text-[10px] text-white/50">
                {f}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function PortfolioPanel() {
  const { assets, assetsLoading, fetchHealth, registerAsset } = usePortfolioStore();
  const [address, setAddress] = useState("");
  const [category, setCategory] = useState("");
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const handleRegister = async () => {
    if (!address.trim()) return;
    await registerAsset({ address: address.trim(), category: category.trim() });
    setAddress("");
    setCategory("");
    setShowForm(false);
  };

  return (
    <div className="flex h-full w-80 flex-col border-l border-white/10 bg-gray-950">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <h2 className="text-sm font-semibold text-white">내 점포 포트폴리오</h2>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-xs text-white/60"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? "취소" : "+ 점포 추가"}
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-3 p-4">
          {/* Registration Form */}
          {showForm && (
            <Card className="border-blue-500/30 bg-gray-900/60">
              <CardContent className="space-y-2 p-3">
                <div>
                  <Label className="text-[10px] text-white/40">주소</Label>
                  <Input
                    value={address}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddress(e.target.value)}
                    placeholder="서울시 성동구 성수동..."
                    className="h-8 border-white/20 bg-gray-800 text-xs text-white"
                  />
                </div>
                <div>
                  <Label className="text-[10px] text-white/40">업종</Label>
                  <Input
                    value={category}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCategory(e.target.value)}
                    placeholder="카페, 음식점 등"
                    className="h-8 border-white/20 bg-gray-800 text-xs text-white"
                  />
                </div>
                <Button
                  variant="default"
                  size="sm"
                  className="w-full text-xs"
                  onClick={handleRegister}
                >
                  등록
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Health Cards */}
          {assetsLoading ? (
            <p className="text-center text-xs text-white/40">로딩 중...</p>
          ) : assets.length === 0 ? (
            <p className="text-center text-xs text-white/40">
              등록된 점포가 없습니다
            </p>
          ) : (
            assets.map((asset) => (
              <HealthCard key={asset.asset_id} asset={asset} />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
