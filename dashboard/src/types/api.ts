/** TypeScript interfaces matching FastAPI response models. */

export interface ApiKeyInfo {
  id: string;
  name: string;
  key_prefix: string;
  key_type: string;
  created_at: string;
  last_used_at: string | null;
}

export interface ApiKeyCreated {
  id: string;
  key: string;
  name: string;
  key_prefix: string;
  key_type: string;
  created_at: string;
}

export interface KeyUsageItem {
  id: string;
  name: string;
  key_prefix: string;
  key_type: string;
  created_at: string;
  last_used_at: string | null;
  credits_used: number;
}

export interface BillingStatus {
  tier: string;
  credits_total: number;
  credits_used: number;
  credits_remaining: number;
  payg_enabled: boolean;
  billing_cycle_start: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user_id: string;
  request_id: string;
}

/** Envelope types matching FastAPI response wrappers. */

export interface ApiResponse<T> {
  data: T;
  request_id: string;
}

export interface CheckoutResponse {
  checkout_url: string;
  request_id: string;
}

export interface PortalResponse {
  portal_url: string;
  request_id: string;
}

export interface PaygToggleResponse {
  payg_enabled: boolean;
  message: string;
  request_id: string;
}

/** Playground / Orderbook types */

export interface OrderbookRequest {
  market_ticker: string;
  timestamp: string;
  depth?: number;
}

export interface OrderbookLevel {
  price: number;
  quantity: number;
}

export interface OrderbookResponse {
  market_ticker: string;
  timestamp: string;
  yes: OrderbookLevel[];
  no: OrderbookLevel[];
  snapshot_basis: string;
  deltas_applied: number;
  response_time: number;
  request_id: string;
}

/** Coverage types */

export interface CoverageSegment {
  segment_id: number;
  segment_start: string;
  segment_end: string;
  days_covered: number;
  snapshot_count: number;
  delta_count: number;
  trade_count: number;
}

export interface MarketCoverage {
  ticker: string;
  title: string | null;
  status: string | null;
  segment_count: number;
  total_snapshots: number;
  total_deltas: number;
  total_trades: number;
  first_date: string | null;
  last_date: string | null;
  segments: CoverageSegment[];
}

export interface EventCoverageGroup {
  event_ticker: string;
  event_title: string | null;
  market_count: number;
  markets: MarketCoverage[];
}

export interface CoverageSummary {
  total_markets: number;
  total_snapshots: number;
  total_deltas: number;
  date_range_start: string | null;
  date_range_end: string | null;
}

export interface CoverageStatsResponse {
  summary: CoverageSummary;
  events: EventCoverageGroup[];
  total_events: number;
  request_id: string;
  response_time: number;
}
