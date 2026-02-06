import { create } from "zustand";
import type { Category, AreaScopeItem, HexagonDetailResponse } from "@/types/map";

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
  // Sidebar state
  sidebarOpen: boolean;
  hexDetail: HexagonDetailResponse | null;
  hexDetailLoading: boolean;
  setSelectedHex: (hex: string | null) => void;
  setSelectedArea: (areaId: number | null, areaName: string | null, realName: string | null) => void;
  setAreaType: (areaType: string) => void;
  setCategory: (category: string) => void;
  setQuarter: (quarter: string) => void;
  setElevationMetric: (metric: ElevationMetric) => void;
  toggleAdminDong: () => void;
  toggleCommercialAreas: () => void;
  fetchCategories: () => Promise<void>;
  fetchAreas: () => Promise<void>;
  // Sidebar actions
  openSidebar: () => void;
  closeSidebar: () => void;
  fetchHexDetail: (h3Index: string) => Promise<void>;
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
  // Sidebar state
  sidebarOpen: false,
  hexDetail: null,
  hexDetailLoading: false,
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
}));
