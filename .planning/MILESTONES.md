# Milestones

## v1.0 MVP (Shipped: 2026-02-17)

**Phases completed:** 7 phases, 18 plans
**Timeline:** 5 days (2026-02-13 → 2026-02-17)
**Codebase:** 6,346 Python + 5,684 TypeScript (12,030 LOC)
**Commits:** 108

**Key accomplishments:**
- Persistent WebSocket collector capturing L2 orderbook snapshots/deltas with auto-discovery and sequence gap recovery
- 10 authenticated REST endpoints: orderbook reconstruction, deltas, markets, trades, settlements, candles, events
- Credit-based billing with Stripe integration (free 1,000/mo, PAYG, Project $30/mo tiers)
- Self-service Next.js dashboard with API key management, usage tracking, and billing portal
- Interactive API playground with curl generation, syntax highlighting, and orderbook preview
- Agent-friendly developer experience: llms.txt discovery, structured JSON errors, OpenAPI 3.1 docs

**Deferred to v2:**
- Real-time WebSocket streaming (STRM-01/02)
- Python/JS SDK generation
- MCP server for AI agent tools

**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md) | [v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)

---


## v1.1 Python SDK (Shipped: 2026-02-18)

**Phases completed:** 5 phases (8-12), 11 plans
**Timeline:** 5 days (2026-02-13 → 2026-02-17)
**Codebase:** 2,686 LOC Python (SDK)
**Files changed:** 64 (+11,291 / -41)

**Key accomplishments:**
- SDK package with uv workspace integration, src layout, and py.typed marker
- 21 typed dataclass response models, exception hierarchy, and dual-mode HTTP transport with retry/auth
- 20 endpoint methods covering all KalshiBook API surfaces (sync + async)
- PageIterator with auto-pagination and .to_df() DataFrame conversion (pandas optional)
- mkdocs-material docs site with Getting Started, Authentication, and endpoint example guides
- GitHub Actions CI/CD and PyPI publishing pipeline

**Deferred to v1.2:**
- Backtesting abstractions (replay_orderbook, stream_trades)
- Credit budget parameter for large queries

**Archive:** [v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md) | [v1.1-REQUIREMENTS.md](milestones/v1.1-REQUIREMENTS.md)

---


## v1.2 Discovery & Replay (Shipped: 2026-02-18)

**Delivered:** Market coverage discovery, upgraded playground with real tickers and zero-credit demos, and Canvas depth chart visualization

**Phases completed:** 3 phases (13-15), 5 plans
**Timeline:** 1 day (2026-02-18)
**Files changed:** 41 (+4,951 / -116)
**Codebase:** 6,313 Python API + 7,519 TypeScript dashboard + 1,630 Python SDK (15,462 LOC)

**Key accomplishments:**
- Materialized coverage view with gaps-and-islands SQL for accurate contiguous segment detection
- Coverage dashboard page with event-grouped table, search, status filters, and timeline bars
- Playground backend with market search autocomplete and zero-credit demo execution endpoints
- TickerCombobox and ExampleCards for real captured market data in the playground
- Canvas-based depth chart showing Yes/No orderbook depth at any covered timestamp

**Deferred to v1.3:**
- Animated orderbook replay with play/pause/scrub controls
- Calendar heatmap for data density visualization
- SDK backtesting abstractions (replay_orderbook, stream_trades)

**Archive:** [v1.2-ROADMAP.md](milestones/v1.2-ROADMAP.md) | [v1.2-REQUIREMENTS.md](milestones/v1.2-REQUIREMENTS.md)

---

