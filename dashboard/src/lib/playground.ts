/**
 * Playground-specific fetch utility using API key auth (not Supabase JWT).
 * Does NOT throw on non-2xx -- returns status code and error body for display.
 */

export interface PlaygroundResult {
  data: unknown;
  status: number;
  responseTime: number;
  creditsDeducted: number | null;
  creditsRemaining: number | null;
}

export async function executePlaygroundRequest(
  path: string,
  body: Record<string, unknown>,
  apiKey: string
): Promise<PlaygroundResult> {
  const start = performance.now();

  const response = await fetch("/api" + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + apiKey,
    },
    body: JSON.stringify(body),
  });

  const responseTime = Math.round(performance.now() - start);

  // Read credit headers (may be null if CORS doesn't expose them)
  const creditsCostHeader = response.headers.get("X-Credits-Cost");
  const creditsRemainingHeader = response.headers.get("X-Credits-Remaining");

  const creditsDeducted = creditsCostHeader
    ? parseInt(creditsCostHeader, 10)
    : null;
  const creditsRemaining = creditsRemainingHeader
    ? parseInt(creditsRemainingHeader, 10)
    : null;

  // Parse response body as JSON, fall back to raw text
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    data = await response.text();
  }

  return {
    data,
    status: response.status,
    responseTime,
    creditsDeducted,
    creditsRemaining,
  };
}
