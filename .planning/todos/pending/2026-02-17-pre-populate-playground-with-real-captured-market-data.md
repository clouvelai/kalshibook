---
created: 2026-02-17T13:04:30.997Z
title: Pre-populate playground with real captured market data
area: dashboard
files:
  - dashboard/src/app/(dashboard)/playground/page.tsx
  - dashboard/src/app/(dashboard)/playground/use-playground.ts
---

## Problem

The API Playground's "Try an example" feature uses a hardcoded example ticker (`KXBTC-25FEB14-T96074.99`) that returns a 404 because it's an expired/non-existent market. This means the playground doesn't work out of the box for new users -- their first experience is an error response instead of seeing real orderbook data.

Before shipping, the example ticker should reference a real market that the collector has actually captured orderbook data for, so "Try an example" → "Send Request" produces a successful 200 response with real orderbook data and the Preview tab renders an actual orderbook table.

## Solution

1. Query the database for a market with recent orderbook data (snapshots + deltas)
2. Update the example ticker and timestamp in the playground to reference that market at a known-good timestamp
3. Consider making the example dynamic (API endpoint that returns a known-good market/timestamp pair) or just hardcode a reliable one from captured data
