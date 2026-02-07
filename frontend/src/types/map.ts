export interface HexagonSummary {
  h3_index: string;
  lat: number;
  lng: number;
  area_id: number | null;
  area_name: string | null;
  real_name: string | null;
  sales_amt: number;
  sales_cnt: number;
  flow_total: number;
  store_cnt: number;
  open_cnt: number;
  close_cnt: number;
}

export interface HexagonsResponse {
  data: HexagonSummary[];
  data_asof: string;
  area_type: string;
  filters: {
    category?: string;
    quarter?: string;
  };
}

export interface Category {
  cat_id: number;
  service_code: string;
  service_name: string;
}

export interface AreaScopeItem {
  area_id: number;
  area_type: string;
  area_code: string;
  area_name: string;
}

export interface MapViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
}

// ---------- Hexagon Detail Response ----------

export interface FlowCard {
  flow_total: number | null;
  flow_by_hour: Record<string, number> | null;
  flow_by_weekday: Record<string, number> | null;
  flow_by_demo: Record<string, number> | null;
}

export interface SalesCard {
  sales_amt: number | null;
  sales_cnt: number | null;
}

export interface CompetitionCard {
  store_cnt: number | null;
  open_cnt: number | null;
  close_cnt: number | null;
  close_rate: number | null;
  competition_density: number | null;
}

export interface GrowthCard {
  sales_growth_rate: number | null;
  flow_growth_rate: number | null;
  store_growth_rate: number | null;
}

export interface RiskCard {
  close_rate: number | null;
  competition_density: number | null;
  warnings: string[];
}

export interface HexagonDetailResponse {
  h3_index: string;
  lat: number;
  lng: number;
  qtr: string;
  data_asof: string;
  areas: string[];
  flow: FlowCard;
  sales: SalesCard;
  competition: CompetitionCard;
  growth: GrowthCard;
  risk: RiskCard;
}

// ---------- Heatmap (Phase 2 S2) ----------

export interface HeatmapHexagon {
  h3_index: string;
  lat: number;
  lng: number;
  area_name: string | null;
  real_name: string | null;
  flow_total: number | null;
  values: Record<string, number>;
}

export interface HeatmapResponse {
  data: HeatmapHexagon[];
  data_asof: string;
  mode: string;
}

// ---------- Peaktime (Phase 2 S2) ----------

export interface PeaktimeAnalysis {
  h3_index: string;
  qtr: string;
  flow_total: number | null;
  peak_hours: number[];
  off_peak_hours: number[];
  hourly_pattern: Record<string, number>;
  weekday_pattern: Record<string, number>;
  demo_breakdown: Record<string, number>;
}

// ---------- Risk Layer (Phase 2 S5) ----------

export interface RiskHexagon {
  h3_index: string;
  lat: number;
  lng: number;
  area_name: string | null;
  real_name: string | null;
  risk_score: number;
  risk_factors: string[];
  close_rate: number | null;
  sales_qoq: number | null;
  store_growth: number | null;
  flow_qoq: number | null;
  sales_amt: number | null;
}

export interface RiskLayerResponse {
  data: RiskHexagon[];
  data_asof: string;
}

export interface RiskAnalysis {
  h3_index: string;
  area_name: string | null;
  real_name: string | null;
  risk_score: number;
  risk_factors: string[];
  close_rate: number | null;
  sales_qoq: number | null;
  store_growth: number | null;
  flow_qoq: number | null;
  alternative_areas: Array<{
    h3_index: string;
    area_name: string | null;
    real_name: string | null;
    risk_score: number;
    sales_amt: number | null;
  }>;
  data_asof: string;
}

// ---------- Quarter Comparison (Phase 3 S4) ----------

export interface QuarterComparison {
  metric: string;
  qtr1_value: number | null;
  qtr2_value: number | null;
  change_rate: number | null;
  avg_change_rate: number | null;
  above_avg: boolean | null;
}

export interface CompareResponse {
  h3_index: string;
  qtr1: string;
  qtr2: string;
  comparisons: QuarterComparison[];
  hourly_q1: Record<string, number> | null;
  hourly_q2: Record<string, number> | null;
  data_asof: string;
}

// ---------- Story Content (Phase 4 S6) ----------

export interface StoryCut {
  cut_number: number;
  title: string;
  body: string;
  kpi_ref: string | null;
  visual_hint: string | null;
}

export interface StoryResponse {
  cuts: StoryCut[];
  citations: string[];
  data_asof: string;
  warning: string;
}

// ---------- Portfolio (Phase 5 S7/S8) ----------

export interface AssetHealth {
  asset_id: number;
  address: string;
  area_name: string | null;
  health_status: "green" | "yellow" | "red";
  health_score: number;
  demand_z: number | null;
  competition_z: number | null;
  growth_z: number | null;
  risk_z: number | null;
  top_factors: string[];
  alternatives: Array<Record<string, unknown>>;
}

export type ViewMode = "default" | "heatmap_hourly" | "heatmap_weekday" | "risk";
