import { createClient } from "@/lib/supabase/client";
import type {
  ApiKeyCreated,
  ApiKeyInfo,
  ApiResponse,
  AuthResponse,
  BillingStatus,
  CheckoutResponse,
  KeyUsageItem,
  PaygToggleResponse,
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
};
