# Requirements: KalshiBook

**Defined:** 2026-02-18
**Core Value:** Reliable, complete orderbook history for every Kalshi market -- reconstructable to any point in time

## v1.2 Requirements

Requirements for Discovery & Replay milestone. Each maps to roadmap phases.

### Market Coverage

- [ ] **COVR-01**: User can browse a list of all markets with data coverage segments (contiguous date/time ranges)
- [ ] **COVR-02**: User can see per-market coverage summary: total data points, number of segments, completeness
- [ ] **COVR-03**: User can search and filter markets by ticker, event, or status
- [ ] **COVR-04**: Coverage data loads fast via pre-computed stats (not live partition scans)
- [ ] **COVR-05**: Coverage segments are computed from actual data gaps (not just first/last timestamps)

### Playground

- [ ] **PLAY-01**: Playground pre-populates with real captured market tickers (not hardcoded)
- [ ] **PLAY-02**: User can autocomplete ticker input from available markets
- [ ] **PLAY-03**: Playground shows example cards with pre-populated queries for common use cases
- [ ] **PLAY-04**: Playground demos cost zero credits (dedicated demo endpoint or pre-baked responses)
- [ ] **PLAY-05**: Playground includes a depth chart tab showing visual orderbook at selected timestamp

### Depth Chart

- [ ] **DPTH-01**: User can view a visual depth chart (Yes/No sides, 0-100 cent range) for any market at any covered timestamp
- [ ] **DPTH-02**: Depth chart renders using Canvas for performance (not SVG)
- [ ] **DPTH-03**: Depth chart is embedded in the playground as a tab alongside API response view

## Future Requirements

Deferred to v1.3+ milestone. Tracked but not in current roadmap.

### Replay Animation

- **RPLY-01**: Animated orderbook replay with play/pause/scrub controls
- **RPLY-02**: Adjustable replay speed (1x, 2x, 5x, 10x)
- **RPLY-03**: Price line overlay on depth chart during replay

### Coverage Analytics

- **COVR-06**: Calendar heatmap showing data density per day per market
- **COVR-07**: Coverage page accessible publicly (marketing value)

### Backtesting Abstractions

- **BKTS-01**: `replay_orderbook()` streaming async generator in SDK
- **BKTS-02**: `stream_trades()` iterator over historical trades in SDK
- **BKTS-03**: `credit_budget` parameter to limit credit consumption on large queries

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Animated replay with scrubbing | Deferred to v1.3 — ship static depth chart first, validate before animating |
| Calendar heatmap | Deferred to v1.3+ — nice-to-have, not core to discovery |
| Pricing restructure | Current tiers validated as-is; adjust after real usage data |
| Public landing page demo | Future milestone — playground-first, public page later |
| Expanding market collection | Future — validate coverage UX before scaling collection |
| SVG-based depth chart | Canvas required for future animation performance; build right from day one |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| COVR-01 | TBD | Pending |
| COVR-02 | TBD | Pending |
| COVR-03 | TBD | Pending |
| COVR-04 | TBD | Pending |
| COVR-05 | TBD | Pending |
| PLAY-01 | TBD | Pending |
| PLAY-02 | TBD | Pending |
| PLAY-03 | TBD | Pending |
| PLAY-04 | TBD | Pending |
| PLAY-05 | TBD | Pending |
| DPTH-01 | TBD | Pending |
| DPTH-02 | TBD | Pending |
| DPTH-03 | TBD | Pending |

**Coverage:**
- v1.2 requirements: 13 total
- Mapped to phases: 0
- Unmapped: 13 (populated during roadmap creation)

---
*Requirements defined: 2026-02-18*
*Last updated: 2026-02-18 after initial definition*
