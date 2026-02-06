import type { HexagonDetailResponse } from "@/types/map";

// Chat route types
export type ChatRoute = "sql" | "insight" | "both";

// SSE Event types
export interface RoutingEvent {
  route: ChatRoute;
}

export interface SqlEvent {
  sql: string;
  row_count: number;
}

export interface RecommendationItem {
  rank: number;
  area_name: string;
  reason: string;
  metrics?: {
    매출?: string;
    점포수?: string;
    유동인구?: string;
  };
}

export interface InsightEvent {
  evidence: string[];
  risks: string[];
  recommendations: (string | RecommendationItem)[];
  action_items?: string[];
  checklist: string[];
  summary: string;
}

export interface DoneEvent {
  data_asof: string;
}

export interface ErrorEvent {
  message: string;
}

// Chat message role
export type MessageRole = "user" | "assistant";

// Chat message interface
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  route?: ChatRoute;
  sql?: SqlEvent;
  insight?: InsightEvent;
  dataAsof?: string;
  isStreaming?: boolean;
  error?: string;
}

// Chat message for API request (simplified)
export interface ChatMessagePayload {
  role: "user" | "assistant";
  content: string;
}

// Chat request payload
export interface ChatRequest {
  question: string;
  messages?: ChatMessagePayload[];
  area_type?: string;
  category?: string;
  qtr?: string;
  selected_hex_detail?: HexagonDetailResponse | null;
}
