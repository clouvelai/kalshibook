---
created: 2026-02-14T12:56:56.389Z
title: Hydrate market metadata via REST API on discovery
area: collector
files:
  - src/collector/discovery.py
  - src/collector/writer.py
  - supabase/migrations/20260213000001_create_markets.sql
---

## Problem

When the collector subscribes to a market mid-stream (e.g., via a `close_date_updated` lifecycle event), we only store `discovered_at` (when our collector first saw it) and `captured_at` on snapshots. We have no record of when the market originally opened or how long it's been active.

This means we can't tell whether we caught 95% of a market's history or 5%. The Kalshi REST API's market details endpoint provides `open_time`, `close_time`, `created_time`, and other metadata (title, event_ticker, category, rules, strike_price) that would fill the empty columns in the `markets` table.

## Solution

When a new market is discovered via lifecycle event, make a REST API call to `GET /trade-api/v2/markets/{ticker}` to hydrate the full market metadata. This gives us `open_time` to compare against `discovered_at` so we know how late we joined. Fits naturally into Phase 2 (REST API layer) — the auth and HTTP client will already exist.
