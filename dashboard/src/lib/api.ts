import { createClient } from "@/lib/supabase/client";
import type {
  ApiKeyCreated,
  ApiKeyInfo,
  ApiResponse,
  AuthResponse,
  BillingStatus,
  CheckoutResponse,
  CoverageStatsResponse,
  DemoRequest,
  DemoResponse,
  KeyUsageItem,
  PaygToggleResponse,
  PlaygroundMarket,
  PortalResponse,
} from "@/types/api";

/**
 * Typed fetch wrapper for the FastAPI backend.
 * Requests go to /api/* which Next.js rewrites proxy to http://localhost:8000/*.
 */
async function fetchAPI<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      error: { message: "Request failed", code: "unknown" },
    }));
    throw new Error(
      error.error?.message || `API error: ${response.status}`
    );
  }

  return response.json();
}

/** Namespaced API client matching FastAPI endpoints. */
export const api = {
  keys: {
    list: () => fetchAPI<ApiResponse<ApiKeyInfo[]>>("/keys"),
    create: (name: string, keyType: string = "dev") =>
      fetchAPI<ApiResponse<ApiKeyCreated>>("/keys", {
        method: "POST",
        body: JSON.stringify({ name, key_type: keyType }),
      }),
    update: (keyId: string, data: { name?: string; key_type?: string }) =>
      fetchAPI<ApiResponse<ApiKeyInfo>>(`/keys/${keyId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    reveal: (keyId: string) =>
      fetchAPI<{ data: { key: string }; request_id: string }>(`/keys/${keyId}/reveal`),
    revoke: (keyId: string) =>
      fetchAPI<{ message: string; request_id: string }>(`/keys/${keyId}`, {
        method: "DELETE",
      }),
    usage: () => fetchAPI<ApiResponse<KeyUsageItem[]>>("/keys/usage"),
  },

  billing: {
    status: () => fetchAPI<BillingStatus & { request_id: string }>("/billing/status"),
    togglePayg: (enable: boolean) =>
      fetchAPI<PaygToggleResponse>("/billing/payg", {
        method: "POST",
        body: JSON.stringify({ enable }),
      }),
    createCheckout: () =>
      fetchAPI<CheckoutResponse>("/billing/checkout", {
        method: "POST",
      }),
    createPortal: () =>
      fetchAPI<PortalResponse>("/billing/portal", {
        method: "POST",
      }),
  },

  auth: {
    signup: (email: string, password: string) =>
      fetchAPI<AuthResponse>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    login: (email: string, password: string) =>
      fetchAPI<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
  },

  coverage: {
    stats: (params?: {
      search?: string;
      status?: string;
      event_ticker?: string;
      page?: number;
      page_size?: number;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.search) searchParams.set("search", params.search);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.event_ticker)
        searchParams.set("event_ticker", params.event_ticker);
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size)
        searchParams.set("page_size", String(params.page_size));
      const qs = searchParams.toString();
      return fetchAPI<CoverageStatsResponse>(
        `/coverage/stats${qs ? `?${qs}` : ""}`
      );
    },
    refresh: () =>
      fetchAPI<{ message: string; request_id: string }>("/coverage/refresh", {
        method: "POST",
      }),
  },

  playground: {
    markets: (q: string, limit = 10) =>
      fetchAPI<{ data: PlaygroundMarket[]; request_id: string }>(
        `/playground/markets?q=${encodeURIComponent(q)}&limit=${limit}`
      ),
    demo: (body: DemoRequest) =>
      fetchAPI<DemoResponse>("/playground/demo", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
};
