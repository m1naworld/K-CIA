"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Map, { Source, Layer, MapMouseEvent } from "react-map-gl/mapbox";
import DeckGL from "@deck.gl/react";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
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
const MAP_STYLE = "mapbox://styles/mapbox/dark-v11";

function getColorScale(
  value: number,
  min: number,
  max: number
): [number, number, number] {
  const t = max === min ? 0.5 : (value - min) / (max - min);
  let r: number, g: number, b: number;
  if (t < 0.25) {
    const s = t / 0.25;
    r = Math.round(40 + s * 120);
    g = Math.round(160 + s * 60);
    b = Math.round(40 - s * 20);
  } else if (t < 0.5) {
    const s = (t - 0.25) / 0.25;
    r = Math.round(160 + s * 95);
    g = Math.round(220 - s * 10);
    b = Math.round(20);
  } else if (t < 0.75) {
    const s = (t - 0.5) / 0.25;
    r = 255;
    g = Math.round(210 - s * 100);
    b = 20;
  } else {
    const s = (t - 0.75) / 0.25;
    r = Math.round(255 - s * 25);
    g = Math.round(110 - s * 80);
    b = Math.round(20 + s * 20);
  }
  return [r, g, b];
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
    color: "#60a5fa",
    dashArray: [12, 6],
    speed: 15,
    label: "━ ━ ━ 발달상권",
  },
  "골목상권": {
    color: "#4ade80",
    dashArray: [6, 6],
    speed: 30,
    label: "╴╴╴╴ 골목상권",
  },
  "전통시장": {
    color: "#fb923c",
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
    selectedAreaId, selectedAreaName, selectedRealName, elevationMetric, areaType, category, quarter,
    setSelectedHex, setSelectedArea, fetchHexDetail, closeSidebar,
    showAdminDong, showCommercialAreas, toggleAdminDong, toggleCommercialAreas,
  } = useMapStore();
  const [data, setData] = useState<HexagonSummary[]>([]);
  const [loading, setLoading] = useState(true);
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
      .catch(() => {});
    fetch("/data/commercial_areas.geojson")
      .then((r) => r.json())
      .then(setCommercialGeo)
      .catch(() => {});
  }, []);

  const dongLabels = useMemo(() => buildDongLabels(adminDongGeo), [adminDongGeo]);
  const commercialLabels = useMemo(() => buildCommercialLabels(commercialGeo), [commercialGeo]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const params = new URLSearchParams({ area_type: areaType });
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
  }, [areaType, category, quarter]);

  const salesRange = useMemo(() => {
    if (data.length === 0) return { min: 0, max: 1 };
    const commercial = data.filter((d) => d.area_name !== null);
    if (commercial.length === 0) return { min: 0, max: 1 };
    const values = commercial.map((d) => d.sales_amt);
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [data]);

  const elevationRange = useMemo(() => {
    if (data.length === 0) return { min: 0, max: 1 };
    const commercial = data.filter((d) => d.area_name !== null);
    if (commercial.length === 0) return { min: 0, max: 1 };
    const values = commercial.map((d) =>
      elevationMetric === "flow" ? d.flow_total : d.sales_amt
    );
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
          // residential (no area) = gray
          if (d.area_name === null) {
            const isHighlighted = selectedAreaId === null && selectedAreaName === null;
            return isHighlighted
              ? [100, 100, 100, 200] as [number, number, number, number]
              : [85, 85, 85, 160] as [number, number, number, number];
          }
          const [r, g, b] = getColorScale(
            d.sales_amt,
            salesRange.min,
            salesRange.max
          );
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
            return [255, 255, 255, 200] as [number, number, number, number];
          }
          return [0, 0, 0, 60] as [number, number, number, number];
        },
        getElevation: (d: HexagonSummary) => {
          if (d.area_name === null) {
            return 2;
          }
          const value =
            elevationMetric === "flow" ? d.flow_total : d.sales_amt;
          const { min, max } = elevationRange;
          const normalized =
            max === min ? 0.5 : (value - min) / (max - min);
          return 10 + normalized * 150;
        },
        updateTriggers: {
          getFillColor: [salesRange, selectedAreaId],
          getLineColor: [selectedAreaId],
          getElevation: [elevationMetric, elevationRange],
        },
        transitions: {
          getElevation: 400,
          getFillColor: 400,
        },
      }),
    ],
    [data, salesRange, elevationRange, elevationMetric, selectedAreaId, selectedAreaName]
  );

  const handleClick = useCallback(
    (info: { object?: HexagonSummary }) => {
      if (info.object) {
        setSelectedHex(info.object.h3_index);
        setSelectedArea(info.object.area_id, info.object.area_name, info.object.real_name ?? null);
        // Fetch hex detail and open sidebar
        fetchHexDetail(info.object.h3_index);
        trackEvent("HEX_CLICK", {
          h3_index: info.object.h3_index,
          area_id: info.object.area_id,
          area_name: info.object.area_name,
          real_name: info.object.real_name ?? null,
          area_type: areaType,
          category,
          qtr: quarter,
        });
      } else {
        setSelectedHex(null);
        setSelectedArea(null, null, null);
        closeSidebar();
      }
    },
    [setSelectedHex, setSelectedArea, fetchHexDetail, closeSidebar, areaType, category, quarter]
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
      <div className="flex h-full w-full items-center justify-center bg-gray-900 text-white">
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
          mapStyle={MAP_STYLE}
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
                    "line-width": 2.5,
                    "line-opacity": 0.8,
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
                    "text-color": "#e0e0ff",
                    "text-halo-color": "rgba(0,0,0,0.9)",
                    "text-halo-width": 2,
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
                    "line-width": 6,
                    "line-opacity": 0.15,
                    "line-blur": 4,
                  }}
                />
                <Layer
                  id="commercial-line-developed"
                  type="line"
                  filter={["==", ["get", "type"], "발달상권"]}
                  paint={{
                    "line-color": COMMERCIAL_TYPE_STYLES["발달상권"].color,
                    "line-width": 2.5,
                    "line-opacity": 0.95,
                    "line-dasharray": [12, 6],
                  }}
                />
                <Layer
                  id="commercial-line-alley"
                  type="line"
                  filter={["==", ["get", "type"], "골목상권"]}
                  paint={{
                    "line-color": COMMERCIAL_TYPE_STYLES["골목상권"].color,
                    "line-width": 2.5,
                    "line-opacity": 0.95,
                    "line-dasharray": [6, 6],
                  }}
                />
                <Layer
                  id="commercial-line-market"
                  type="line"
                  filter={["==", ["get", "type"], "전통시장"]}
                  paint={{
                    "line-color": COMMERCIAL_TYPE_STYLES["전통시장"].color,
                    "line-width": 2.5,
                    "line-opacity": 0.95,
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
                    "text-color": "#ffffff",
                    "text-halo-color": "rgba(0,0,0,0.85)",
                    "text-halo-width": 1.5,
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
          className="pointer-events-none absolute z-10 rounded-lg border border-white/10 bg-gray-900/90 px-4 py-3 text-xs text-white shadow-xl backdrop-blur-sm"
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
            <p className="mb-1 text-[10px] text-white/50">
              ({hoverInfo.object.area_name})
            </p>
          )}
          {hoverInfo.object.area_name !== null && (
            <>
              <p className="text-sm font-semibold text-amber-300">
                매출 {(hoverInfo.object.sales_amt / 10000).toLocaleString()}만원
              </p>
              <div className="mt-1.5 flex gap-3 text-white/70">
                <span>유동 {hoverInfo.object.flow_total.toLocaleString()}명</span>
                <span>점포 {hoverInfo.object.store_cnt}개</span>
              </div>
              <div className="mt-1 flex gap-3 text-[10px] text-white/50">
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
          className="pointer-events-none absolute z-10 rounded-lg border border-white/10 bg-gray-900/90 px-4 py-3 text-xs text-white shadow-xl backdrop-blur-sm"
          style={{ left: polygonHover.x + 12, top: polygonHover.y + 12 }}
        >
          <p className="text-sm font-semibold">
            {polygonHover.name}
            {polygonHover.realName && (
              <span className="ml-1 text-emerald-400">({polygonHover.realName})</span>
            )}
          </p>
          <p className="mt-1 text-white/60">{polygonHover.type}</p>
        </div>
      )}

      {/* Metric toggle + Layer toggle */}
      <div className="absolute right-4 top-4 z-10 flex flex-col gap-2">
        <div className="flex gap-1 rounded-lg border border-white/10 bg-gray-900/80 p-1 text-xs text-white backdrop-blur-sm">
          <button
            onClick={() => useMapStore.getState().setElevationMetric("flow")}
            className={`rounded-md px-3 py-1.5 transition ${
              elevationMetric === "flow"
                ? "bg-blue-600 text-white"
                : "text-white/60 hover:bg-white/10 hover:text-white"
            }`}
          >
            유동인구
          </button>
          <button
            onClick={() => useMapStore.getState().setElevationMetric("sales")}
            className={`rounded-md px-3 py-1.5 transition ${
              elevationMetric === "sales"
                ? "bg-blue-600 text-white"
                : "text-white/60 hover:bg-white/10 hover:text-white"
            }`}
          >
            매출
          </button>
        </div>
        <div className="flex gap-1 rounded-lg border border-white/10 bg-gray-900/80 p-1 text-xs text-white backdrop-blur-sm">
          <button
            onClick={toggleAdminDong}
            className={`rounded-md px-3 py-1.5 transition ${
              showAdminDong
                ? "bg-indigo-600 text-white"
                : "text-white/60 hover:bg-white/10 hover:text-white"
            }`}
          >
            행정동
          </button>
          <button
            onClick={toggleCommercialAreas}
            className={`rounded-md px-3 py-1.5 transition ${
              showCommercialAreas
                ? "bg-emerald-600 text-white"
                : "text-white/60 hover:bg-white/10 hover:text-white"
            }`}
          >
            상권
          </button>
        </div>
      </div>

      {/* Selected area indicator */}
      {selectedAreaName && (
        <div className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-lg border border-white/10 bg-gray-900/80 px-4 py-2 text-sm text-white backdrop-blur-sm">
          <div>
            <span className="font-semibold">
              {selectedRealName ?? selectedAreaName}
            </span>
            {selectedRealName && (
              <span className="ml-2 text-xs text-white/50">
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
            className="ml-1 text-white/50 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-6 left-4 z-10 rounded-lg border border-white/10 bg-gray-900/80 px-4 py-3 backdrop-blur-sm">
        <p className="mb-2 text-[10px] font-medium tracking-wide text-white/50">
          매출 규모
        </p>
        <div
          className="h-2.5 w-24 rounded-sm"
          style={{
            background:
              "linear-gradient(to right, #32a050, #96dc28, #ffd600, #ff8c00, #e03020)",
          }}
        />
        <div className="mt-1 flex justify-between text-[10px] text-white/40">
          <span>낮음</span>
          <span>높음</span>
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-[10px] text-white/40">
          <div className="h-2.5 w-4 rounded-sm bg-[#555]" />
          <span>주거/기타</span>
        </div>
        {showCommercialAreas && (
          <div className="mt-3 border-t border-white/10 pt-2">
            <p className="mb-1.5 text-[10px] font-medium tracking-wide text-white/50">상권 유형</p>
            <div className="flex flex-col gap-1.5">
              {Object.entries(COMMERCIAL_TYPE_STYLES).map(([type, style]) => (
                <div key={type} className="flex items-center gap-2 text-[10px] text-white/60">
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
