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

