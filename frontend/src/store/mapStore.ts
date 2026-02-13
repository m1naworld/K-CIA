import { create } from "zustand";
import type { Category, ComparisonResponse, HexagonDetailResponse } from "@/types/map";
import type { SocialConfigResponse, SocialTrendsResponse } from "@/types/social";

type ElevationMetric = "flow" | "sales" | "timeslot" | "risk";

interface MapState {
  selectedHex: string | null;
  selectedAreaId: number | null;
  selectedAreaName: string | null;
  selectedRealName: string | null;
  category: string;
  quarter: string;
  elevationMetric: ElevationMetric;
  categories: Category[];
  showAdminDong: boolean;
  showCommercialAreas: boolean;
  // Sidebar state
  sidebarOpen: boolean;
  hexDetail: HexagonDetailResponse | null;
  hexDetailLoading: boolean;
  // Comparison mode (M8)
  comparisonMode: boolean;
  compareQtrBefore: string;
  compareQtrAfter: string;
  compareCategoryMode: "all" | "selected";
  comparisonData: ComparisonResponse | null;
  comparisonLoading: boolean;
  // Social module (M9)
  socialEnabled: boolean;
  socialConfig: SocialConfigResponse | null;
  socialData: SocialTrendsResponse | null;
  socialLoading: boolean;
  setSelectedHex: (hex: string | null) => void;
  setSelectedArea: (areaId: number | null, areaName: string | null, realName: string | null) => void;
  setCategory: (category: string) => void;
  setQuarter: (quarter: string) => void;
  setElevationMetric: (metric: ElevationMetric) => void;
  toggleAdminDong: () => void;
  toggleCommercialAreas: () => void;
  fetchCategories: () => Promise<void>;
  // Sidebar actions
  openSidebar: () => void;
  closeSidebar: () => void;
  fetchHexDetail: (h3Index: string) => Promise<void>;
  // Comparison actions (M8)
  setComparisonMode: (on: boolean) => void;
  setCompareQtrBefore: (qtr: string) => void;
  setCompareQtrAfter: (qtr: string) => void;
  setCompareCategoryMode: (mode: "all" | "selected") => void;
  fetchComparison: (h3Index: string) => Promise<void>;
  // Social actions (M9)
  fetchSocialConfig: () => Promise<void>;
  fetchSocialTrends: (h3Index?: string | null, catCode?: string | null) => Promise<void>;
  toggleSocial: () => void;
}

export const useMapStore = create<MapState>((set) => ({
  selectedHex: null,
  selectedAreaId: null,
  selectedAreaName: null,
  selectedRealName: null,
  category: "all",
  quarter: "latest",
  elevationMetric: "sales",
  categories: [],
  showAdminDong: true,
  showCommercialAreas: true,
  // Sidebar state
  sidebarOpen: false,
  hexDetail: null,
  hexDetailLoading: false,
  // Comparison mode (M8)
  comparisonMode: false,
  compareQtrBefore: "",
  compareQtrAfter: "",
  compareCategoryMode: "selected",
  comparisonData: null,
  comparisonLoading: false,
  // Social module (M9)
  socialEnabled: false,
  socialConfig: null,
  socialData: null,
  socialLoading: false,
  setSelectedHex: (hex) => set({ selectedHex: hex }),
  setSelectedArea: (areaId, areaName, realName) => set({ selectedAreaId: areaId, selectedAreaName: areaName, selectedRealName: realName }),
  setCategory: (category) => {
    set({ category });
    const state = useMapStore.getState();
    if (state.sidebarOpen && state.selectedHex) {
      state.fetchHexDetail(state.selectedHex);
    }
    if (
      state.comparisonMode &&
      state.selectedHex &&
      state.compareQtrBefore &&
      state.compareQtrAfter
    ) {
      state.fetchComparison(state.selectedHex);
    }
    if (state.socialEnabled) {
      state.fetchSocialTrends(state.selectedHex, category);
    }
  },
  setQuarter: (quarter) => {
    set({ quarter });
    const state = useMapStore.getState();
    if (state.sidebarOpen && state.selectedHex) {
      state.fetchHexDetail(state.selectedHex);
    }
  },
  setElevationMetric: (metric) => set({ elevationMetric: metric }),
  toggleAdminDong: () => set((s) => ({ showAdminDong: !s.showAdminDong })),
  toggleCommercialAreas: () => set((s) => ({ showCommercialAreas: !s.showCommercialAreas })),
  fetchCategories: async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    try {
      const res = await fetch(`${apiUrl}/api/data/categories`);
      const json = await res.json();
      set({ categories: json.data ?? [] });
    } catch {
      // API unavailable — keep empty
    }
  },
  // Sidebar actions
  openSidebar: () => set({ sidebarOpen: true }),
  closeSidebar: () => set({ sidebarOpen: false, hexDetail: null }),
  fetchHexDetail: async (h3Index: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const state = useMapStore.getState();
    const params = new URLSearchParams();
    params.set("area_type", "COMMERCIAL_AREA");
    if (state.quarter && state.quarter !== "latest") {
      params.set("qtr", state.quarter);
    }
    if (state.category && state.category !== "all") {
      params.set("category", state.category);
    }
    const url = `${apiUrl}/api/map/hexagon/${h3Index}?${params.toString()}`;

    set({ hexDetailLoading: true, sidebarOpen: true });
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch");
      const json = await res.json();
      set({ hexDetail: json, hexDetailLoading: false });
      // 소셜 활성화 시 해당 상권으로 재조회
      const s = useMapStore.getState();
      if (s.socialEnabled) {
        s.fetchSocialTrends(h3Index, s.category);
      }
    } catch {
      set({ hexDetail: null, hexDetailLoading: false });
    }
  },
  // Comparison actions (M8)
  setComparisonMode: (on) => set({ comparisonMode: on, comparisonData: null }),
  setCompareQtrBefore: (qtr) => {
    set({ compareQtrBefore: qtr });
    const state = useMapStore.getState();
    if (state.sidebarOpen && state.selectedHex && state.compareQtrAfter) {
      state.fetchComparison(state.selectedHex);
    }
  },
  setCompareQtrAfter: (qtr) => {
    set({ compareQtrAfter: qtr });
    const state = useMapStore.getState();
    if (state.sidebarOpen && state.selectedHex && state.compareQtrBefore) {
      state.fetchComparison(state.selectedHex);
    }
  },
  setCompareCategoryMode: (mode) => {
    set({ compareCategoryMode: mode });
    const state = useMapStore.getState();
    if (
      state.sidebarOpen &&
      state.selectedHex &&
      state.compareQtrBefore &&
      state.compareQtrAfter
    ) {
      state.fetchComparison(state.selectedHex);
    }
  },
  fetchComparison: async (h3Index: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const state = useMapStore.getState();
    if (!state.compareQtrBefore || !state.compareQtrAfter) return;

    const body: Record<string, string> = {
      h3_index: h3Index,
      qtr_before: state.compareQtrBefore,
      qtr_after: state.compareQtrAfter,
      area_type: "COMMERCIAL_AREA",
    };
    if (
      state.compareCategoryMode === "selected" &&
      state.category &&
      state.category !== "all"
    ) {
      body.category = state.category;
    }

    set({ comparisonLoading: true, sidebarOpen: true });
    try {
      const res = await fetch(`${apiUrl}/api/map/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to fetch comparison");
      const json = await res.json();
      set({ comparisonData: json, comparisonLoading: false });
    } catch {
      set({ comparisonData: null, comparisonLoading: false });
    }
  },
  // Social actions (M9)
  fetchSocialConfig: async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    try {
      const res = await fetch(`${apiUrl}/api/social/config`);
      if (!res.ok) return;
      const config = await res.json();
      set({ socialConfig: config, socialEnabled: config.enabled });
    } catch {
      // API unavailable
    }
  },
  fetchSocialTrends: async (h3Index?: string | null, catCode?: string | null) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    set({ socialLoading: true });
    try {
      const params = new URLSearchParams({ days: "30" });
      if (h3Index) params.set("h3_index", h3Index);
      if (catCode && catCode !== "all") params.set("cat_code", catCode);
      const res = await fetch(`${apiUrl}/api/social/trends?${params}`);
      if (!res.ok) throw new Error("Failed to fetch");
      const data = await res.json();
      set({ socialData: data, socialLoading: false });
    } catch {
      set({ socialData: null, socialLoading: false });
    }
  },
  toggleSocial: () => {
    const state = useMapStore.getState();
    const next = !state.socialEnabled;
    set({ socialEnabled: next });
    if (next) {
      state.fetchSocialTrends(state.selectedHex, state.category);
    }
  },
}));
