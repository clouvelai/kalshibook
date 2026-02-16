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
