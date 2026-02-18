"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import {
  executePlaygroundRequest,
  type PlaygroundResult,
} from "@/lib/playground";

// ---------------------------------------------------------------------------
// Curl generation (pure function, not exported)
// ---------------------------------------------------------------------------

function generateCurl(
  marketTicker: string,
  timestamp: string,
  depth: string,
  keyPrefix: string
): string {
  // Mask key: show first 10 chars of prefix + ****...****
  const masked =
    keyPrefix.length > 10
      ? keyPrefix.slice(0, 10) + "****...****"
      : keyPrefix + "****...****";

  // Build JSON body
  const bodyFields: string[] = [];
  bodyFields.push(`  "market_ticker": "${marketTicker}"`);
  if (timestamp) {
    bodyFields.push(`  "timestamp": "${timestamp}"`);
  }
  if (depth) {
    bodyFields.push(`  "depth": ${depth}`);
  }

  const bodyJson = `{\n${bodyFields.join(",\n")}\n}`;

  return [
    `curl -X POST https://api.kalshibook.com/orderbook \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -H "Authorization: Bearer ${masked}" \\`,
    `  -d '${bodyJson}'`,
  ].join("\n");
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export type ActiveTab = "code" | "response";

export interface PlaygroundState {
  // Form fields
  marketTicker: string;
  timestamp: string;
  depth: string;

  // Key selection
  selectedKeyId: string | null;
  selectedKeyPrefix: string | null;
  revealedKey: string | null;
  keys: Array<{ id: string; key_prefix: string; name: string }>;
  keysLoading: boolean;
  keysError: string | null;

  // Generated code
  curlCommand: string;

  // Request lifecycle
  isLoading: boolean;
  response: PlaygroundResult | null;
  activeTab: ActiveTab;
  requestError: string | null;
}

export interface PlaygroundActions {
  setField: (field: "marketTicker" | "timestamp" | "depth", value: string) => void;
  selectKey: (keyId: string, keyPrefix: string) => void;
  sendRequest: () => Promise<void>;
  setActiveTab: (tab: ActiveTab) => void;
  handleDemoResult: (result: import("@/types/api").DemoResponse) => void;
  setRequestError: (msg: string | null) => void;
}

export function usePlayground(): PlaygroundState & PlaygroundActions {
  // Form state
  const [marketTicker, setMarketTicker] = useState("");
  const [timestamp, setTimestamp] = useState("");
  const [depth, setDepth] = useState("");

  // Key state
  const [selectedKeyId, setSelectedKeyId] = useState<string | null>(null);
  const [selectedKeyPrefix, setSelectedKeyPrefix] = useState<string | null>(null);
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [keys, setKeys] = useState<
    Array<{ id: string; key_prefix: string; name: string }>
  >([]);
  const [keysLoading, setKeysLoading] = useState(true);
  const [keysError, setKeysError] = useState<string | null>(null);

  // Generated code
  const [curlCommand, setCurlCommand] = useState("");

  // Request lifecycle
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<PlaygroundResult | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("code");
  const [requestError, setRequestError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // On mount: fetch keys, auto-select first, auto-reveal
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    async function loadKeys() {
      try {
        setKeysLoading(true);
        setKeysError(null);

        const result = await api.keys.list();
        const keyList = result.data.map((k) => ({
          id: k.id,
          key_prefix: k.key_prefix,
          name: k.name,
        }));

        if (cancelled) return;
        setKeys(keyList);

        if (keyList.length === 0) {
          setKeysError("No API keys found. Create one in the API Keys page.");
          setKeysLoading(false);
          return;
        }

        // Auto-select first key
        const first = keyList[0];
        setSelectedKeyId(first.id);
        setSelectedKeyPrefix(first.key_prefix);

        // Auto-reveal
        try {
          const revealed = await api.keys.reveal(first.id);
          if (!cancelled) {
            setRevealedKey(revealed.data.key);
          }
        } catch {
          if (!cancelled) {
            setKeysError("Failed to reveal API key for playground requests.");
          }
        }
      } catch {
        if (!cancelled) {
          setKeysError("Failed to load API keys.");
        }
      } finally {
        if (!cancelled) {
          setKeysLoading(false);
        }
      }
    }

    loadKeys();
    return () => {
      cancelled = true;
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Curl auto-update
  // ---------------------------------------------------------------------------
  useEffect(() => {
    setCurlCommand(
      generateCurl(
        marketTicker || "TICKER",
        timestamp,
        depth,
        selectedKeyPrefix || "kb_live_"
      )
    );
  }, [marketTicker, timestamp, depth, selectedKeyPrefix]);

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  const setField = useCallback(
    (field: "marketTicker" | "timestamp" | "depth", value: string) => {
      setRequestError(null);
      switch (field) {
        case "marketTicker":
          setMarketTicker(value);
          break;
        case "timestamp":
          setTimestamp(value);
          break;
        case "depth":
          setDepth(value);
          break;
      }
    },
    []
  );

  const selectKey = useCallback(async (keyId: string, keyPrefix: string) => {
    setSelectedKeyId(keyId);
    setSelectedKeyPrefix(keyPrefix);
    setRevealedKey(null);

    try {
      const revealed = await api.keys.reveal(keyId);
      setRevealedKey(revealed.data.key);
    } catch {
      setRequestError("Failed to reveal selected API key.");
    }
  }, []);

  const sendRequest = useCallback(async () => {
    if (!revealedKey) {
      setRequestError("No API key available. Select or create a key first.");
      return;
    }

    if (!timestamp.trim()) {
      setRequestError("Timestamp is required. Enter an ISO 8601 timestamp (e.g., 2025-02-14T18:00:00Z).");
      return;
    }

    setIsLoading(true);
    setRequestError(null);

    try {
      const body: Record<string, unknown> = {
        market_ticker: marketTicker,
      };
      body.timestamp = timestamp;
      if (depth) body.depth = parseInt(depth, 10);

      const result = await executePlaygroundRequest(
        "/orderbook",
        body,
        revealedKey
      );

      setResponse(result);
      setActiveTab("response");
    } catch (err) {
      setRequestError(
        err instanceof Error ? err.message : "Request failed unexpectedly."
      );
    } finally {
      setIsLoading(false);
    }
  }, [revealedKey, marketTicker, timestamp, depth]);

  const handleDemoResult = useCallback(
    (result: import("@/types/api").DemoResponse) => {
      setResponse({
        data: result.data,
        status: 200,
        responseTime: Math.round(result.response_time * 1000),
        creditsDeducted: 0,
        creditsRemaining: null,
      });
      setActiveTab("response");
    },
    []
  );

  return {
    // State
    marketTicker,
    timestamp,
    depth,
    selectedKeyId,
    selectedKeyPrefix,
    revealedKey,
    keys,
    keysLoading,
    keysError,
    curlCommand,
    isLoading,
    response,
    activeTab,
    requestError,

    // Actions
    setField,
    selectKey,
    sendRequest,
    setActiveTab,
    handleDemoResult,
    setRequestError,
  };
}
