"use client";

import { useState, useEffect } from "react";
import { BookOpen, BarChart3, TrendingUp, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { DemoRequest, DemoResponse, PlaygroundMarket } from "@/types/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ExampleCardsProps {
  onExecute: (result: DemoResponse) => void;
  onError: (error: string) => void;
}

// ---------------------------------------------------------------------------
// Example card config
// ---------------------------------------------------------------------------

interface ExampleConfig {
  title: string;
  description: string;
  endpoint: DemoRequest["endpoint"];
  icon: typeof BookOpen;
  buildRequest: (market: PlaygroundMarket) => DemoRequest;
}

function buildExamples(market: PlaygroundMarket): ExampleConfig[] {
  const firstDate = market.first_date || "2025-01-01";
  const lastDate = market.last_date || "2025-01-02";

  // Compute midpoint for orderbook timestamp
  const startMs = new Date(firstDate + "T00:00:00Z").getTime();
  const endMs = new Date(lastDate + "T23:59:59Z").getTime();
  const midpoint = new Date((startMs + endMs) / 2).toISOString();

  return [
    {
      title: "Orderbook Reconstruction",
      description: "Reconstruct L2 orderbook at a point in time",
      endpoint: "orderbook",
      icon: BookOpen,
      buildRequest: () => ({
        endpoint: "orderbook",
        market_ticker: market.ticker,
        timestamp: midpoint,
        depth: 10,
      }),
    },
    {
      title: "Trade History",
      description: "Fetch recent trades for a market",
      endpoint: "trades",
      icon: BarChart3,
      buildRequest: () => ({
        endpoint: "trades",
        market_ticker: market.ticker,
        start_time: firstDate + "T00:00:00Z",
        end_time: firstDate + "T23:59:59Z",
        limit: 20,
      }),
    },
    {
      title: "Price Candles",
      description: "OHLCV candles at hourly intervals",
      endpoint: "candles",
      icon: TrendingUp,
      buildRequest: () => ({
        endpoint: "candles",
        market_ticker: market.ticker,
        start_time: firstDate + "T00:00:00Z",
        end_time: lastDate + "T23:59:59Z",
        interval: "1h",
      }),
    },
  ];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ExampleCards({ onExecute, onError }: ExampleCardsProps) {
  const [featuredMarket, setFeaturedMarket] = useState<PlaygroundMarket | null>(null);
  const [loading, setLoading] = useState(true);
  const [executingIdx, setExecutingIdx] = useState<number | null>(null);

  // Fetch a featured market on mount
  useEffect(() => {
    let cancelled = false;

    async function fetchFeatured() {
      try {
        const res = await api.playground.markets("", 1);
        if (!cancelled && res.data.length > 0) {
          setFeaturedMarket(res.data[0]);
        }
      } catch {
        // Silently fail -- example cards just won't show
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchFeatured();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-3 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!featuredMarket) {
    return null; // No markets with coverage data
  }

  const examples = buildExamples(featuredMarket);

  async function handleClick(idx: number) {
    if (executingIdx !== null) return; // Already executing
    if (!featuredMarket) return;

    setExecutingIdx(idx);
    try {
      const request = examples[idx].buildRequest(featuredMarket);
      const result = await api.playground.demo(request);
      onExecute(result);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Demo request failed");
    } finally {
      setExecutingIdx(null);
    }
  }

  return (
    <div>
      <p className="text-xs text-muted-foreground mb-2">
        Try a free example with <span className="font-mono">{featuredMarket.ticker}</span>
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {examples.map((ex, idx) => {
          const Icon = ex.icon;
          const isExecuting = executingIdx === idx;
          return (
            <Card
              key={ex.endpoint}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => handleClick(idx)}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-1.5">
                  {isExecuting ? (
                    <Loader2 className="size-4 animate-spin text-primary" />
                  ) : (
                    <Icon className="size-4 text-muted-foreground" />
                  )}
                  <span className="text-sm font-medium">{ex.title}</span>
                </div>
                <p className="text-xs text-muted-foreground">{ex.description}</p>
                <Badge variant="outline" className="mt-2 text-[10px]">
                  {ex.endpoint}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
