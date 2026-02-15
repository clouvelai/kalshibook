---
created: 2026-02-15T22:18:02.681Z
title: Subscribe to ticker WS channel for open interest data
area: collector
files:
  - src/collector/main.py
  - src/api/services/candles.py
---

## Problem

Our candlestick endpoint (GET /candles/{ticker}) computes OHLC + volume from the `trades` table, but the CONTEXT.md spec also calls for "open interest" in candle data. Open interest (total outstanding contracts) is NOT derivable from our stored trade or orderbook data — it requires the Kalshi `ticker` WS channel which provides real-time price, volume, and open interest updates.

The `ticker` channel (https://docs.kalshi.com/websockets/market-ticker) fires whenever any ticker field changes. It can be subscribed without market_tickers filter to receive all markets (same pattern as our existing `trade` channel subscription). This is the same low-effort pattern we used for trade capture in Phase 4.

## Solution

1. Subscribe to `ticker` WS channel in collector (same fire-and-forget pattern as trades)
2. Store periodic ticker snapshots or just open interest values in a new table (e.g., `market_stats` or extend `markets`)
3. Enrich candle response with open interest at each interval boundary
4. Low priority — trade-price candles + volume already serve the primary backtesting use case. Open interest is a "nice to have" enrichment for signal-strength analysis.

Fits naturally as a small collector extension + candle service enrichment. Could be a standalone mini-phase or folded into the backtesting framework milestone.
