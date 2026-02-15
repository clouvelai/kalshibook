---
created: 2026-02-15T22:25:00.000Z
title: Fetch Kalshi event candlesticks for untracked markets
area: api
files:
  - src/api/routes/candles.py
  - src/api/services/candles.py
  - src/collector/enrichment.py
---

## Problem

Our current candle endpoint (GET /candles/{ticker}) only works for markets where we have stored trade data — i.e., markets we've been collecting since the collector started. For historical markets or events we never tracked, we return empty data. This limits the directional backtesting use case for customers who want candle data across all Kalshi events.

Kalshi provides `GET /trade-api/v2/series/{series_ticker}/events/{event_ticker}/candlesticks` which:
- Returns aggregated candlestick data across ALL markets in an event (bulk by event)
- Supports intervals: 1 min, 60 min (1h), 1440 min (1d)
- Returns rich data: OHLC for yes bid/ask, OHLC trade prices (mean/min/max), volume, AND open interest
- **No authentication required** (public endpoint)
- Requires `series_ticker` + event `ticker` as path params

This is richer than what we compute from our own trades (we don't have bid/ask OHLC or open interest in our computed candles).

## Solution

Two approaches (not mutually exclusive):

**Option A: Fallback proxy** — When our candle endpoint has no trade data for a market, fall back to fetching from Kalshi's event candlestick API. Transparent to the consumer. Downside: adds external dependency and rate limit exposure on the hot path.

**Option B: Periodic bulk import** — Background job fetches Kalshi event candlesticks for events in our `events` table and caches them in a `candles_cache` table. Our endpoint queries cached data first, then our computed data. Decouples serving from Kalshi API availability.

**Option C: Separate endpoint** — New endpoint like `GET /candles/event/{event_ticker}` that explicitly proxies Kalshi's event candlestick data. Clear to consumers that this is Kalshi-sourced vs our own computed data.

Key consideration: requires `series_ticker` which we now store in the `events` table (added in Phase 4). The data pipeline is already in place.

Related: ticker WS channel todo (open interest for our own computed candles).
