// ---------- Social Module Types (M9) ----------

export interface SourceBreakdown {
  source: string;
  count: number;
  buzz: number;
}

export interface TrendDayPoint {
  date: string;
  buzz: number;
}

export interface EvidenceSnippet {
  title: string;
  url: string;
  published_at: string;
  snippet: string;
  source: string;
  keyword: string;
}

export interface SocialTrendsResponse {
  total_buzz: number;
  avg_sentiment: number | null;
  total_pos: number;
  total_neg: number;
  by_source: SourceBreakdown[];
  top_keywords: string[];
  evidence_snippets: EvidenceSnippet[];
  daily_trend: TrendDayPoint[];
  data_asof: string;
  filtered_area: string | null;
  filtered_category: string | null;
  is_fallback: boolean;
}

export interface SocialConfigResponse {
  enabled: boolean;
  youtube_enabled: boolean;
  naver_enabled: boolean;
  default_keywords: string[];
  collection_days: number;
}
