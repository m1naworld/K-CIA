import { create } from "zustand";
import type { Category, AreaScopeItem, HexagonDetailResponse, ViewMode, PeaktimeAnalysis, RiskAnalysis, CompareResponse } from "@/types/map";

type ElevationMetric = "flow" | "sales";

interface MapState {
  selectedHex: string | null;
  selectedAreaId: number | null;
  selectedAreaName: string | null;
  selectedRealName: string | null;
  areaType: string;
  category: string;
  quarter: string;
  elevationMetric: ElevationMetric;
  categories: Category[];
  areas: AreaScopeItem[];
  showAdminDong: boolean;
  showCommercialAreas: boolean;
  // View mode (Phase 2+)
  viewMode: ViewMode;
  selectedHour: number | null;
  // Sidebar state
  sidebarOpen: boolean;
  hexDetail: HexagonDetailResponse | null;
  hexDetailLoading: boolean;
  // Phase 2 state
  peaktime: PeaktimeAnalysis | null;
  riskAnalysis: RiskAnalysis | null;
  // Phase 3 state
  compareData: CompareResponse | null;
  compareQtr1: string;
  compareQtr2: string;
  setSelectedHex: (hex: string | null) => void;
  setSelectedArea: (areaId: number | null, areaName: string | null, realName: string | null) => void;
  setAreaType: (areaType: string) => void;
  setCategory: (category: string) => void;
  setQuarter: (quarter: string) => void;
  setElevationMetric: (metric: ElevationMetric) => void;
  setViewMode: (mode: ViewMode) => void;
  setSelectedHour: (hour: number | null) => void;
  setCompareQtrs: (qtr1: string, qtr2: string) => void;
  toggleAdminDong: () => void;
  toggleCommercialAreas: () => void;
  fetchCategories: () => Promise<void>;
  fetchAreas: () => Promise<void>;
  // Sidebar actions
  openSidebar: () => void;
  closeSidebar: () => void;
  fetchHexDetail: (h3Index: string) => Promise<void>;
  fetchPeaktime: (h3Index: string) => Promise<void>;
  fetchRiskAnalysis: (h3Index: string) => Promise<void>;
  fetchCompare: (h3Index: string) => Promise<void>;
}

export const useMapStore = create<MapState>((set) => ({
  selectedHex: null,
  selectedAreaId: null,
  selectedAreaName: null,
  selectedRealName: null,
  areaType: "COMMERCIAL_AREA",
  category: "",
  quarter: "",
  elevationMetric: "flow",
  categories: [],
  areas: [],
  showAdminDong: true,
  showCommercialAreas: true,
  // View mode
  viewMode: "default",
  selectedHour: null,
  // Sidebar state
  sidebarOpen: false,
  hexDetail: null,
  hexDetailLoading: false,
  // Phase 2 state
  peaktime: null,
  riskAnalysis: null,
  // Phase 3 state
  compareData: null,
  compareQtr1: "",
  compareQtr2: "",
  setSelectedHex: (hex) => set({ selectedHex: hex }),
  setSelectedArea: (areaId, areaName, realName) => set({ selectedAreaId: areaId, selectedAreaName: areaName, selectedRealName: realName }),
  setAreaType: (areaType) => {
    set({ areaType });
    // Refetch hex detail if sidebar is open
    const state = useMapStore.getState();
    if (state.sidebarOpen && state.selectedHex) {
      state.fetchHexDetail(state.selectedHex);
    }
  },
  setCategory: (category) => {
    set({ category });
    const state = useMapStore.getState();
    if (state.sidebarOpen && state.selectedHex) {
      state.fetchHexDetail(state.selectedHex);
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
  setViewMode: (mode) => set({ viewMode: mode }),
  setSelectedHour: (hour) => set({ selectedHour: hour }),
  setCompareQtrs: (qtr1, qtr2) => set({ compareQtr1: qtr1, compareQtr2: qtr2 }),
  toggleAdminDong: () => set((s) => ({ showAdminDong: !s.showAdminDong })),
  toggleCommercialAreas: () => set((s) => ({ showCommercialAreas: !s.showCommercialAreas })),
  fetchCategories: async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    try {
      const res = await fetch(`${apiUrl}/api/data/categories`);
      const json = await res.json();
      set({ categories: json.data ?? [] });
    } catch {
      // API unavailable — keep empty
    }
  },
  fetchAreas: async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;
    try {
      const res = await fetch(`${apiUrl}/api/data/area-scope`);
      const json = await res.json();
      set({ areas: json.data ?? [] });
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
    // Always pass area_type to filter data by selected view
    params.set("area_type", state.areaType);
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
    } catch {
      set({ hexDetail: null, hexDetailLoading: false });
    }
  },
  fetchPeaktime: async (h3Index: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const state = useMapStore.getState();
    const params = new URLSearchParams({ area_type: state.areaType });
    if (state.quarter && state.quarter !== "latest") params.set("qtr", state.quarter);
    try {
      const res = await fetch(`${apiUrl}/api/map/hexagon/${h3Index}/peaktime?${params}`);
      if (!res.ok) throw new Error("Failed");
      const json = await res.json();
      set({ peaktime: json });
    } catch {
      set({ peaktime: null });
    }
  },
  fetchRiskAnalysis: async (h3Index: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const state = useMapStore.getState();
    const params = new URLSearchParams({ area_type: state.areaType });
    if (state.category && state.category !== "all") params.set("category", state.category);
    if (state.quarter && state.quarter !== "latest") params.set("qtr", state.quarter);
    try {
      const res = await fetch(`${apiUrl}/api/map/hexagon/${h3Index}/risk?${params}`);
      if (!res.ok) throw new Error("Failed");
      const json = await res.json();
      set({ riskAnalysis: json });
    } catch {
      set({ riskAnalysis: null });
    }
  },
  fetchCompare: async (h3Index: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const state = useMapStore.getState();
    if (!state.compareQtr1 || !state.compareQtr2) return;
    const params = new URLSearchParams({
      qtr1: state.compareQtr1,
      qtr2: state.compareQtr2,
      area_type: state.areaType,
    });
    if (state.category && state.category !== "all") params.set("category", state.category);
    try {
      const res = await fetch(`${apiUrl}/api/map/hexagon/${h3Index}/compare?${params}`);
      if (!res.ok) throw new Error("Failed");
      const json = await res.json();
      set({ compareData: json });
    } catch {
      set({ compareData: null });
    }
  },
}));
