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
  sales_qoq: number | null;
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

export interface RecommendationCard {
  score: number;
  grade: string;
  pros: string[];
  cons: string[];
  summary: string;
}

export interface TrendPoint {
  qtr: string;
  value: number | null;
}

export interface TrendData {
  sales: TrendPoint[];
  flow: TrendPoint[];
  store: TrendPoint[];
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
  recommendation: RecommendationCard;
  trend: TrendData;
}
