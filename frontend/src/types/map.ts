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

// ---------- Facility / Demo / TimeSlot (M6-4 확장) ----------

export interface FacilityItem {
  facility_type: string;
  label: string;
  count: number;
}

export interface FacilityCard {
  total_count: number;
  facilities: FacilityItem[];
  top_types: string[];
}

export interface DemoGenderRatio {
  male: number | null;
  female: number | null;
}

export interface DemoAgeItem {
  age_group: string; // "10" | "20" | "30" | "40" | "50" | "60+"
  ratio: number;
  count: number;
}

export interface DemoCard {
  gender: DemoGenderRatio;
  age_distribution: DemoAgeItem[];
  peak_age_group: string | null;
  peak_gender: string | null;
}

export interface TimeSlotItem {
  hour_range: string;
  label: string;
  flow_ratio: number;
}

export interface TimeSlotRecommendation {
  peak_hours: number[];
  peak_weekday: string | null;
  off_peak_hours: number[];
  recommendations: TimeSlotItem[];
}

// ---------- Comparison (M8) ----------

export interface ComparisonMetricSnapshot {
  sales_amt: number | null;
  sales_cnt: number | null;
  flow_total: number | null;
  store_cnt: number | null;
  open_cnt: number | null;
  close_cnt: number | null;
  close_rate: number | null;
}

export interface ComparisonChange {
  sales_change_rate: number | null;
  sales_diff: number | null;
  flow_change_rate: number | null;
  flow_diff: number | null;
  store_change_rate: number | null;
  store_diff: number | null;
}

export interface ComparisonBreakdown {
  flow_by_weekday_before: Record<string, number> | null;
  flow_by_weekday_after: Record<string, number> | null;
  flow_by_hour_before: Record<string, number> | null;
  flow_by_hour_after: Record<string, number> | null;
  flow_by_demo_before: Record<string, number> | null;
  flow_by_demo_after: Record<string, number> | null;
}

export interface ComparisonResponse {
  h3_index: string;
  qtr_before: string;
  qtr_after: string;
  areas: string[];
  before: ComparisonMetricSnapshot;
  after: ComparisonMetricSnapshot;
  change: ComparisonChange;
  breakdown: ComparisonBreakdown | null;
  warnings: string[];
  data_asof: string;
}

// ---------- Hexagon Detail Response ----------

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
  facility: FacilityCard | null;
  demo: DemoCard | null;
  time_slot: TimeSlotRecommendation | null;
}
