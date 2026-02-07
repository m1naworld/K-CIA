import { create } from "zustand";
import type { AssetHealth } from "@/types/map";

interface AssetInput {
  address: string;
  category: string;
}

interface ABComparison {
  asset_a: AssetHealth;
  asset_b: AssetHealth;
  verdict: string;
  factors: Array<{ metric: string; a_value: number | null; b_value: number | null; winner: string }>;
}

interface PortfolioState {
  assets: AssetHealth[];
  assetsLoading: boolean;
  compareResult: ABComparison | null;
  selectedAssetA: number | null;
  selectedAssetB: number | null;
  setSelectedAssets: (a: number | null, b: number | null) => void;
  registerAsset: (input: AssetInput) => Promise<void>;
  fetchHealth: () => Promise<void>;
  fetchCompare: (assetIdA: number, assetIdB: number) => Promise<void>;
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  assets: [],
  assetsLoading: false,
  compareResult: null,
  selectedAssetA: null,
  selectedAssetB: null,
  setSelectedAssets: (a, b) => set({ selectedAssetA: a, selectedAssetB: b }),
  registerAsset: async (input) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    try {
      await fetch(`${apiUrl}/api/portfolio/assets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      // Refresh health after registering
      get().fetchHealth();
    } catch {
      // Ignore
    }
  },
  fetchHealth: async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    set({ assetsLoading: true });
    try {
      const res = await fetch(`${apiUrl}/api/portfolio/health`);
      if (!res.ok) throw new Error("Failed");
      const json = await res.json();
      set({ assets: json.assets ?? [], assetsLoading: false });
    } catch {
      set({ assets: [], assetsLoading: false });
    }
  },
  fetchCompare: async (assetIdA, assetIdB) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    try {
      const res = await fetch(`${apiUrl}/api/portfolio/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_id_a: assetIdA, asset_id_b: assetIdB }),
      });
      if (!res.ok) throw new Error("Failed");
      const json = await res.json();
      set({ compareResult: json });
    } catch {
      set({ compareResult: null });
    }
  },
}));
