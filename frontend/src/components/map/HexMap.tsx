"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Map, { Source, Layer, MapMouseEvent } from "react-map-gl/mapbox";
import DeckGL from "@deck.gl/react";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { Button } from "@/components/ui/button";
import { useMapStore } from "@/store/mapStore";
import type { HexagonSummary, MapViewState } from "@/types/map";
import { trackEvent } from "@/lib/analytics";

const INITIAL_VIEW_STATE: MapViewState = {
  longitude: 127.055,
  latitude: 37.5435,
  zoom: 15.2,
  pitch: 50,
  bearing: -20,
};

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
const MAPBOX_STYLE_DARK = "mapbox://styles/mapbox/dark-v11";
const MAPBOX_STYLE_LIGHT = "mapbox://styles/mapbox/light-v11";
const CARTO_STYLE_DARK =
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const CARTO_STYLE_LIGHT =
  "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

/**
 * Color scale for QoQ sales growth rate.
 * Negative (decline) → red, zero → gray/yellow, positive (growth) → green.
 * @param qoq - QoQ growth ratio (e.g., -0.1 = -10%, 0.05 = +5%)
 */
function getQoQColorScale(
  qoq: number | null,
  isDark: boolean
): [number, number, number] {
  if (qoq === null || qoq === undefined || !Number.isFinite(qoq)) return [180, 180, 80]; // neutral yellow-gray for no data

  // Clamp to [-0.3, 0.3] range for normalization
  const clamped = Math.max(-0.3, Math.min(0.3, qoq));
  // Map to 0~1: -0.3 → 0, 0 → 0.5, +0.3 → 1
  const t = (clamped + 0.3) / 0.6;

  if (t < 0.35) {
    // Red zone (strong decline)
    const s = t / 0.35;
    return isDark
      ? [
        Math.round(200 + s * 55),
        Math.round(50 + s * 50),
        Math.round(30 + s * 10),
      ]
      : [
        Math.round(180 + s * 60),
        Math.round(45 + s * 45),
        Math.round(25 + s * 15),
      ];
  } else if (t < 0.5) {
    // Orange zone (mild decline)
    const s = (t - 0.35) / 0.15;
    return isDark
      ? [
        255,
        Math.round(100 + s * 80),
        Math.round(40 + s * 20),
      ]
      : [
        235,
        Math.round(110 + s * 70),
        Math.round(45 + s * 20),
      ];
  } else if (t < 0.65) {
    // Yellow zone (neutral / slight growth)
    const s = (t - 0.5) / 0.15;
    return isDark
      ? [
        Math.round(255 - s * 80),
        Math.round(180 + s * 30),
        Math.round(60 - s * 20),
      ]
      : [
        Math.round(235 - s * 60),
        Math.round(175 + s * 35),
        Math.round(65 - s * 20),
      ];
  } else {
    // Green zone (growth)
    const s = (t - 0.65) / 0.35;
    return isDark
      ? [
        Math.round(175 - s * 135),
        Math.round(210 - s * 40),
        Math.round(40 + s * 40),
      ]
      : [
        Math.round(140 - s * 110),
        Math.round(200 - s * 50),
        Math.round(50 + s * 50),
      ];
  }
}

/**
 * Color scale for foot-traffic volume.
 * Low → deep blue, High → bright aqua.
 */
function getFlowColorScale(
  value: number,
  min: number,
  max: number,
  isDark: boolean
): [number, number, number] {
  if (!Number.isFinite(value) || max === min) {
    return isDark ? [40, 50, 80] : [60, 90, 140];
  }
  const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
  // More vibrant gradient: dark indigo -> electric blue -> bright cyan -> mint green
  if (t < 0.33) {
    const s = t / 0.33;
    return isDark
      ? [
        Math.round(20 + s * 20),    // 20 -> 40
        Math.round(30 + s * 80),    // 30 -> 110
        Math.round(80 + s * 100),   // 80 -> 180
      ]
      : [
        Math.round(20 + s * 20),
        Math.round(60 + s * 80),
        Math.round(140 + s * 60),
      ];
  } else if (t < 0.66) {
    const s = (t - 0.33) / 0.33;
    return isDark
      ? [
        Math.round(40 + s * 30),    // 40 -> 70
        Math.round(110 + s * 90),   // 110 -> 200
        Math.round(180 + s * 40),   // 180 -> 220
      ]
      : [
        Math.round(40 + s * 20),
        Math.round(140 + s * 60),
        Math.round(200 - s * 20),
      ];
  } else {
    const s = (t - 0.66) / 0.34;
    return isDark
      ? [
        Math.round(70 + s * 60),    // 70 -> 130
        Math.round(200 + s * 55),   // 200 -> 255
        Math.round(220 - s * 50),   // 220 -> 170
      ]
      : [
        Math.round(60 + s * 40),
        Math.round(200 + s * 55),
        Math.round(180 - s * 40),
      ];
  }
}

// 행정동별 색상
const DONG_COLORS: Record<string, string> = {
  "성수1가1동": "#6366f1", // indigo
  "성수1가2동": "#8b5cf6", // violet
  "성수2가1동": "#06b6d4", // cyan
  "성수2가3동": "#14b8a6", // teal
};

interface CommercialTypeStyle {
  color: string;
  dashArray: [number, number] | [number, number, number, number];
  speed: number;
  label: string;
}

const COMMERCIAL_TYPE_STYLES: Record<string, CommercialTypeStyle> = {
  "발달상권": {
    color: "#BD2E4A", // Crimson - Grandeur/Luxury
    dashArray: [12, 6],
    speed: 15,
    label: "━ ━ ━ 발달상권",
  },
  "골목상권": {
    color: "#4CBB17", // Kelly Green - Vitality/Energy
    dashArray: [6, 6],
    speed: 30,
    label: "╴╴╴╴ 골목상권",
  },
  "전통시장": {
    color: "#F28500", // Tangerine - Warmth/Energy
    dashArray: [3, 3, 9, 3],
    speed: 45,
    label: "·-·-· 전통시장",
  },
};

const COMMERCIAL_TYPE_COLORS: Record<string, string> = {
  "발달상권": COMMERCIAL_TYPE_STYLES["발달상권"].color,
  "골목상권": COMMERCIAL_TYPE_STYLES["골목상권"].color,
  "전통시장": COMMERCIAL_TYPE_STYLES["전통시장"].color,
};

// 행정동 라벨 데이터 생성 (centroid)
function buildDongLabels(geojson: GeoJSON.FeatureCollection | null): GeoJSON.FeatureCollection {
  if (!geojson) return { type: "FeatureCollection", features: [] };
  return {
    type: "FeatureCollection",
    features: geojson.features.map((f) => {
      // 간이 centroid (bbox 중심)
      const coords = (f.geometry as GeoJSON.Polygon | GeoJSON.MultiPolygon).coordinates;
      const flat = coords.flat(3);
      const lngs: number[] = [];
      const lats: number[] = [];
      for (let i = 0; i < flat.length; i += 2) {
        lngs.push(flat[i] as number);
        lats.push(flat[i + 1] as number);
      }
      // For polygon coordinates, flatten differently
      let allCoords: [number, number][] = [];
      if (f.geometry.type === "Polygon") {
        allCoords = (f.geometry as GeoJSON.Polygon).coordinates[0] as [number, number][];
      } else if (f.geometry.type === "MultiPolygon") {
        for (const poly of (f.geometry as GeoJSON.MultiPolygon).coordinates) {
          allCoords = allCoords.concat(poly[0] as [number, number][]);
        }
      }
      const cLng = allCoords.reduce((s, c) => s + c[0], 0) / allCoords.length;
      const cLat = allCoords.reduce((s, c) => s + c[1], 0) / allCoords.length;
      return {
        type: "Feature" as const,
        properties: { name: f.properties?.name ?? "" },
        geometry: { type: "Point" as const, coordinates: [cLng, cLat] },
      };
    }),
  };
}

// 상권 라벨 데이터 생성
function buildCommercialLabels(geojson: GeoJSON.FeatureCollection | null): GeoJSON.FeatureCollection {
  if (!geojson) return { type: "FeatureCollection", features: [] };
  return {
    type: "FeatureCollection",
    features: geojson.features.map((f) => {
      let allCoords: [number, number][] = [];
      if (f.geometry.type === "Polygon") {
        allCoords = (f.geometry as GeoJSON.Polygon).coordinates[0] as [number, number][];
      } else if (f.geometry.type === "MultiPolygon") {
        for (const poly of (f.geometry as GeoJSON.MultiPolygon).coordinates) {
          allCoords = allCoords.concat(poly[0] as [number, number][]);
        }
      }
      const cLng = allCoords.reduce((s, c) => s + c[0], 0) / allCoords.length;
      const cLat = allCoords.reduce((s, c) => s + c[1], 0) / allCoords.length;
      const typeName = f.properties?.type ?? "";
      const realName = f.properties?.real_name ?? "";
      const labelText = realName
        ? `${f.properties?.name} (${realName})`
        : f.properties?.name ?? "";
      return {
        type: "Feature" as const,
        properties: {
          name: f.properties?.name ?? "",
          label: labelText,
          type: typeName,
        },
        geometry: { type: "Point" as const, coordinates: [cLng, cLat] },
      };
    }),
  };
}

export default function HexMap() {
  const {
    selectedAreaId, selectedAreaName, selectedRealName, elevationMetric, category, quarter,
    setSelectedHex, setSelectedArea, fetchHexDetail, closeSidebar,
    showAdminDong, showCommercialAreas, toggleAdminDong, toggleCommercialAreas,
    comparisonMode, fetchComparison,
  } = useMapStore();
  const [data, setData] = useState<HexagonSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDark, setIsDark] = useState(true);
  const mapStyle = useMemo(() => {
    if (MAPBOX_TOKEN) {
      return isDark ? MAPBOX_STYLE_DARK : MAPBOX_STYLE_LIGHT;
    }
    return isDark ? CARTO_STYLE_DARK : CARTO_STYLE_LIGHT;
  }, [isDark]);
  const [adminDongGeo, setAdminDongGeo] = useState<GeoJSON.FeatureCollection | null>(null);
  const [commercialGeo, setCommercialGeo] = useState<GeoJSON.FeatureCollection | null>(null);
  const [hoverInfo, setHoverInfo] = useState<{
    x: number;
    y: number;
    object?: HexagonSummary;
  } | null>(null);
  const [polygonHover, setPolygonHover] = useState<{
    x: number;
    y: number;
    name: string;
    realName: string;
    type: string;
  } | null>(null);

  // Load boundary GeoJSON
  useEffect(() => {
    fetch("/data/admin_dong.geojson")
      .then((r) => r.json())
      .then(setAdminDongGeo)
      .catch(() => { });
    fetch("/data/commercial_areas.geojson")
      .then((r) => r.json())
      .then(setCommercialGeo)
      .catch(() => { });
  }, []);

  useEffect(() => {
    const getTheme = () => document.documentElement.classList.contains("dark");
    const handleThemeChange = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      if (detail === "dark" || detail === "light") {
        setIsDark(detail === "dark");
      } else {
        setIsDark(getTheme());
      }
    };
    setIsDark(getTheme());
    window.addEventListener("theme-change", handleThemeChange);
    return () => window.removeEventListener("theme-change", handleThemeChange);
  }, []);

  const dongLabels = useMemo(() => buildDongLabels(adminDongGeo), [adminDongGeo]);
  const commercialLabels = useMemo(() => buildCommercialLabels(commercialGeo), [commercialGeo]);
  const labelTextColor = isDark ? "#e5e7eb" : "#111827";
  const labelHaloColor = isDark ? "rgba(0,0,0,0.9)" : "rgba(255,255,255,0.98)";
  const labelHaloWidth = isDark ? 2 : 1.2;

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const params = new URLSearchParams({ area_type: "COMMERCIAL_AREA" });
    if (category && category !== "all") params.set("category", category);
    if (quarter && quarter !== "latest") params.set("qtr", quarter);
    fetch(`${apiUrl}/api/map/hexagons?${params}`)
      .then((res) => res.json())
      .then((json) => {
        setData(json.data || []);
        setLoading(false);
      })
      .catch(() => {
        setData([]);
        setLoading(false);
      });
  }, [category, quarter]);

  const elevationRange = useMemo(() => {
    if (data.length === 0) return { min: 0, max: 1 };
    const commercial = data.filter((d) => d.area_name !== null);
    if (commercial.length === 0) return { min: 0, max: 1 };
    const values = commercial
      .map((d) => (elevationMetric === "flow" ? d.flow_total : d.sales_amt))
      .filter((v) => v !== null && v !== undefined && Number.isFinite(v));
    if (values.length === 0) return { min: 0, max: 1 };
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [data, elevationMetric]);

  const layers = useMemo(
    () => [
      new H3HexagonLayer({
        id: "h3-hexagons",
        data,
        extruded: true,
        pickable: true,
        filled: true,
        wireframe: true,
        elevationScale: 1,
        getHexagon: (d: HexagonSummary) => d.h3_index,
        getFillColor: (d: HexagonSummary) => {
          // residential (no area) = nearly invisible
          if (d.area_name === null) {
            return isDark
              ? [50, 50, 50, 30] as [number, number, number, number]
              : [100, 100, 100, 40] as [number, number, number, number];
          }
          const [r, g, b] =
            elevationMetric === "flow"
              ? getFlowColorScale(
                d.flow_total,
                elevationRange.min,
                elevationRange.max,
                isDark
              )
              : getQoQColorScale(d.sales_qoq, isDark);
          // Highlight selected area
          if (selectedAreaId !== null && d.area_id === selectedAreaId) {
            return [
              Math.min(255, r + 50),
              Math.min(255, g + 50),
              Math.min(255, b + 50),
              240,
            ] as [number, number, number, number];
          }
          // Dim non-selected areas when an area is selected
          if (selectedAreaId !== null && d.area_id !== selectedAreaId) {
            return [r, g, b, 120] as [number, number, number, number];
          }
          return [r, g, b, 220] as [number, number, number, number];
        },
        getLineColor: (d: HexagonSummary) => {
          if (selectedAreaId !== null && d.area_id === selectedAreaId) {
            return isDark
              ? ([255, 255, 255, 200] as [number, number, number, number])
              : ([25, 25, 25, 200] as [number, number, number, number]);
          }
          return isDark
            ? ([255, 255, 255, 40] as [number, number, number, number])
            : ([0, 0, 0, 70] as [number, number, number, number]);
        },
        getElevation: (d: HexagonSummary) => {
          if (d.area_name === null) {
            return 2;
          }
          const value = elevationMetric === "flow" ? d.flow_total : d.sales_amt;
          if (value === null || value === undefined || !Number.isFinite(value)) return 10;
          const { min, max } = elevationRange;
          const normalized =
            max === min ? 0.5 : (value - min) / (max - min);
          const result = 10 + normalized * 150;
          return Number.isFinite(result) ? result : 10;
        },
        updateTriggers: {
          getFillColor: [data, selectedAreaId, elevationMetric, elevationRange, isDark],
          getLineColor: [selectedAreaId, isDark],
          getElevation: [elevationMetric, elevationRange],
        },
        transitions: {
          getElevation: 400,
          getFillColor: 400,
        },
      }),
    ],
    [data, elevationRange, elevationMetric, selectedAreaId, selectedAreaName]
  );

  const handleClick = useCallback(
    (info: { object?: HexagonSummary }) => {
      if (info.object) {
        setSelectedHex(info.object.h3_index);
        setSelectedArea(info.object.area_id, info.object.area_name, info.object.real_name ?? null);
        // Branch: comparison mode vs normal mode
        if (comparisonMode) {
          fetchComparison(info.object.h3_index);
        } else {
          fetchHexDetail(info.object.h3_index);
        }
        trackEvent("HEX_CLICK", {
          h3_index: info.object.h3_index,
          area_id: info.object.area_id,
          area_name: info.object.area_name,
          real_name: info.object.real_name ?? null,
          category,
          qtr: quarter,
          comparison_mode: comparisonMode,
        });
      } else {
        setSelectedHex(null);
        setSelectedArea(null, null, null);
        closeSidebar();
      }
    },
    [setSelectedHex, setSelectedArea, fetchHexDetail, fetchComparison, closeSidebar, category, quarter, comparisonMode]
  );

  const handleHover = useCallback(
    (info: { x: number; y: number; object?: HexagonSummary }) => {
      setHoverInfo(info.object ? info : null);
    },
    []
  );

  const handleMapMouseMove = useCallback(
    (e: MapMouseEvent) => {
      const feature = e.features?.[0];
      if (feature && feature.properties) {
        setPolygonHover({
          x: e.point.x,
          y: e.point.y,
          name: feature.properties.name || "",
          realName: feature.properties.real_name || "",
          type: feature.properties.type || "",
        });
      } else {
        setPolygonHover(null);
      }
    },
    []
  );

  const handleMapMouseLeave = useCallback(() => {
    setPolygonHover(null);
  }, []);

  if (loading) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-slate-50 text-slate-700 dark:bg-gray-900 dark:text-white">
        <p>지도 데이터 로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
        onClick={handleClick}
        onHover={handleHover}
      >
        <Map
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle={mapStyle}
          interactiveLayerIds={["commercial-fill", "admin-dong-fill"]}
          onMouseMove={handleMapMouseMove}
          onMouseLeave={handleMapMouseLeave}
        >
          {/* 행정동 경계 레이어 */}
          {showAdminDong && adminDongGeo && (
            <>
              <Source id="admin-dong" type="geojson" data={adminDongGeo}>
                <Layer
                  id="admin-dong-fill"
                  type="fill"
                  paint={{
                    "fill-color": [
                      "match", ["get", "name"],
                      "성수1가1동", DONG_COLORS["성수1가1동"],
                      "성수1가2동", DONG_COLORS["성수1가2동"],
                      "성수2가1동", DONG_COLORS["성수2가1동"],
                      "성수2가3동", DONG_COLORS["성수2가3동"],
                      "#888",
                    ],
                    "fill-opacity": 0,
                  }}
                />
                <Layer
                  id="admin-dong-line"
                  type="line"
                  paint={{
                    "line-color": [
                      "match", ["get", "name"],
                      "성수1가1동", DONG_COLORS["성수1가1동"],
                      "성수1가2동", DONG_COLORS["성수1가2동"],
                      "성수2가1동", DONG_COLORS["성수2가1동"],
                      "성수2가3동", DONG_COLORS["성수2가3동"],
                      "#888",
                    ],
                    "line-width": isDark ? 2.5 : 3,
                    "line-opacity": isDark ? 0.8 : 0.95,
                  }}
                />
              </Source>
              <Source id="dong-labels" type="geojson" data={dongLabels}>
                <Layer
                  id="dong-label-text"
                  type="symbol"
                  layout={{
                    "text-field": ["get", "name"],
                    "text-size": 14,
                    "text-anchor": "center",
                    "text-allow-overlap": true,
                    "text-font": ["DIN Pro Bold", "Arial Unicode MS Bold"],
                  }}
                  paint={{
                    "text-color": labelTextColor,
                    "text-halo-color": labelHaloColor,
                    "text-halo-width": labelHaloWidth,
                  }}
                />
              </Source>
            </>
          )}

          {/* 상권 영역 레이어 - 마칭 앤츠 애니메이션 */}
          {showCommercialAreas && commercialGeo && (
            <>
              <Source id="commercial-areas" type="geojson" data={commercialGeo}>
                <Layer
                  id="commercial-fill"
                  type="fill"
                  paint={{
                    "fill-color": "transparent",
                    "fill-opacity": 0,
                  }}
                />
                <Layer
                  id="commercial-line-glow"
                  type="line"
                  paint={{
                    "line-color": [
                      "match", ["get", "type"],
                      "발달상권", COMMERCIAL_TYPE_COLORS["발달상권"],
                      "골목상권", COMMERCIAL_TYPE_COLORS["골목상권"],
                      "전통시장", COMMERCIAL_TYPE_COLORS["전통시장"],
                      "#888",
                    ],
                    "line-width": isDark ? 6 : 7,
                    "line-opacity": isDark ? 0.15 : 0.28,
                    "line-blur": 4,
                  }}
                />
                <Layer
                  id="commercial-line-developed"
                  type="line"
                  filter={["==", ["get", "type"], "발달상권"]}
                  paint={{
                    "line-color": COMMERCIAL_TYPE_STYLES["발달상권"].color,
                    "line-width": isDark ? 2.5 : 3,
                    "line-opacity": isDark ? 0.95 : 1,
                    "line-dasharray": [12, 6],
                  }}
                />
                <Layer
                  id="commercial-line-alley"
                  type="line"
                  filter={["==", ["get", "type"], "골목상권"]}
                  paint={{
                    "line-color": COMMERCIAL_TYPE_STYLES["골목상권"].color,
                    "line-width": isDark ? 2.5 : 3,
                    "line-opacity": isDark ? 0.95 : 1,
                    "line-dasharray": [6, 6],
                  }}
                />
                <Layer
                  id="commercial-line-market"
                  type="line"
                  filter={["==", ["get", "type"], "전통시장"]}
                  paint={{
                    "line-color": COMMERCIAL_TYPE_STYLES["전통시장"].color,
                    "line-width": isDark ? 2.5 : 3,
                    "line-opacity": isDark ? 0.95 : 1,
                    "line-dasharray": [3, 3, 9, 3],
                  }}
                />
              </Source>
              <Source id="commercial-labels" type="geojson" data={commercialLabels}>
                <Layer
                  id="commercial-label-text"
                  type="symbol"
                  layout={{
                    "text-field": ["get", "label"],
                    "text-size": 10,
                    "text-anchor": "center",
                    "text-allow-overlap": false,
                    "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"],
                  }}
                  paint={{
                    "text-color": labelTextColor,
                    "text-halo-color": labelHaloColor,
                    "text-halo-width": labelHaloWidth,
                  }}
                />
              </Source>
            </>
          )}
        </Map>
      </DeckGL>

      {/* Tooltip */}
      {hoverInfo?.object && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border border-slate-200 bg-white/90 px-4 py-3 text-xs text-slate-900 shadow-xl backdrop-blur-sm dark:border-white/10 dark:bg-gray-900/90 dark:text-white"
          style={{ left: hoverInfo.x + 12, top: hoverInfo.y + 12 }}
        >
          <p className="mb-1 text-sm font-semibold">
            {hoverInfo.object.area_name === null
              ? "주거/기타 지역"
              : hoverInfo.object.real_name
                ? `${hoverInfo.object.real_name}`
                : hoverInfo.object.area_name}
          </p>
          {hoverInfo.object.real_name && (
            <p className="mb-1 text-[10px] text-slate-500 dark:text-white/50">
              ({hoverInfo.object.area_name})
            </p>
          )}
          {hoverInfo.object.area_name !== null && (
            <>
              <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">
                매출 {(hoverInfo.object.sales_amt / 10000).toLocaleString()}만원
              </p>
              <div className="mt-1.5 flex gap-3 text-slate-600 dark:text-white/70">
                <span>유동 {hoverInfo.object.flow_total.toLocaleString()}명</span>
                <span>점포 {hoverInfo.object.store_cnt}개</span>
              </div>
              <div className="mt-1 flex gap-3 text-[10px] text-slate-500 dark:text-white/50">
                <span>개업 {hoverInfo.object.open_cnt}</span>
                <span>폐업 {hoverInfo.object.close_cnt}</span>
              </div>
            </>
          )}
        </div>
      )}

      {/* Polygon Tooltip */}
      {polygonHover && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border border-slate-200 bg-white/90 px-4 py-3 text-xs text-slate-900 shadow-xl backdrop-blur-sm dark:border-white/10 dark:bg-gray-900/90 dark:text-white"
          style={{ left: polygonHover.x + 12, top: polygonHover.y + 12 }}
        >
          <p className="text-sm font-semibold">
            {polygonHover.name}
            {polygonHover.realName && (
              <span className="ml-1 text-emerald-400">({polygonHover.realName})</span>
            )}
          </p>
          <p className="mt-1 text-slate-600 dark:text-white/60">{polygonHover.type}</p>
        </div>
      )}

      {/* Metric toggle + Layer toggle */}
      <div className="absolute right-4 top-4 z-10 flex flex-col gap-2">
        <div className="flex gap-1 rounded-lg border border-slate-200 bg-white/80 p-1 text-xs text-slate-700 backdrop-blur-sm dark:border-white/10 dark:bg-gray-900/80 dark:text-white">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => useMapStore.getState().setElevationMetric("flow")}
            className={`h-8 px-3 text-xs ${elevationMetric === "flow"
              ? "bg-blue-600 text-white hover:bg-blue-700 hover:text-white"
              : "text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-white/60 dark:hover:bg-white/10 dark:hover:text-white"
              }`}
          >
            유동인구
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => useMapStore.getState().setElevationMetric("sales")}
            className={`h-8 px-3 text-xs ${elevationMetric === "sales"
              ? "bg-blue-600 text-white hover:bg-blue-700 hover:text-white"
              : "text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-white/60 dark:hover:bg-white/10 dark:hover:text-white"
              }`}
          >
            매출
          </Button>
        </div>
        <div className="flex gap-1 rounded-lg border border-slate-200 bg-white/80 p-1 text-xs text-slate-700 backdrop-blur-sm dark:border-white/10 dark:bg-gray-900/80 dark:text-white">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleAdminDong}
            className={`h-8 px-3 text-xs ${showAdminDong
              ? "bg-indigo-600 text-white hover:bg-indigo-700 hover:text-white"
              : "text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-white/60 dark:hover:bg-white/10 dark:hover:text-white"
              }`}
          >
            행정동
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleCommercialAreas}
            className={`h-8 px-3 text-xs ${showCommercialAreas
              ? "bg-emerald-600 text-white hover:bg-emerald-700 hover:text-white"
              : "text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-white/60 dark:hover:bg-white/10 dark:hover:text-white"
              }`}
          >
            상권
          </Button>
        </div>
      </div>

      {/* Selected area indicator */}
      {selectedAreaName && (
        <div className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-lg border border-slate-200 bg-white/80 px-4 py-2 text-sm text-slate-700 backdrop-blur-sm dark:border-white/10 dark:bg-gray-900/80 dark:text-white">
          <div>
            <span className="font-semibold">
              {selectedRealName ?? selectedAreaName}
            </span>
            {selectedRealName && (
              <span className="ml-2 text-xs text-slate-500 dark:text-white/50">
                ({selectedAreaName})
              </span>
            )}
          </div>
          <button
            onClick={() => {
              setSelectedHex(null);
              setSelectedArea(null, null, null);
              closeSidebar();
            }}
            className="ml-1 text-slate-500 hover:text-slate-900 dark:text-white/50 dark:hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-6 left-4 z-10 rounded-lg border border-slate-200 bg-white/80 px-4 py-3 backdrop-blur-sm dark:border-white/10 dark:bg-gray-900/80">
        <p className="mb-2 text-[10px] font-medium tracking-wide text-slate-500 dark:text-white/50">
          {elevationMetric === "flow" ? "유동인구" : "매출증감 (QoQ)"}
        </p>
        <div
          className="h-2.5 w-24 rounded-sm"
          style={{
            background:
              elevationMetric === "flow"
                ? isDark
                  ? "linear-gradient(to right, #0f1f3d, #245aa5, #3ac3c9, #6ff5b5)"
                  : "linear-gradient(to right, #dbeafe, #93c5fd, #38bdf8, #34d399)"
                : isDark
                  ? "linear-gradient(to right, #FF2400, #F28500, #FFF44F, #4CBB17, #50C878)"
                  : "linear-gradient(to right, #FF2400, #F28500, #FFF44F, #4CBB17, #50C878)",
          }}
        />
        <div className="mt-1 flex justify-between text-[10px] text-slate-500 dark:text-white/40">
          <span>{elevationMetric === "flow" ? "낮음" : "감소"}</span>
          <span>{elevationMetric === "flow" ? "높음" : "증가"}</span>
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-500 dark:text-white/40">
          <div className="h-2.5 w-4 rounded-sm bg-slate-300 dark:bg-[#555]" />
          <span>주거/기타</span>
        </div>
        {showCommercialAreas && (
          <div className="mt-3 border-t border-slate-200 pt-2 dark:border-white/10">
            <p className="mb-1.5 text-[10px] font-medium tracking-wide text-slate-500 dark:text-white/50">상권 유형</p>
            <div className="flex flex-col gap-1.5">
              {Object.entries(COMMERCIAL_TYPE_STYLES).map(([type, style]) => (
                <div key={type} className="flex items-center gap-2 text-[10px] text-slate-600 dark:text-white/60">
                  <svg width="24" height="3" className="shrink-0">
                    <line
                      x1="0" y1="1.5" x2="24" y2="1.5"
                      stroke={style.color}
                      strokeWidth="2"
                      strokeDasharray={style.dashArray.join(",")}
                    />
                  </svg>
                  <span>{type}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
