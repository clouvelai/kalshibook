# Pitfalls Research

**Domain:** Monetized L2 orderbook data API (Kalshi prediction markets)
**Researched:** 2026-02-13
**Confidence:** MEDIUM-HIGH (verified against Kalshi API docs, Supabase official docs, Stripe docs, and community implementations)

## Critical Pitfalls

### Pitfall 1: Silent Orderbook Corruption from Missed Deltas

**What goes wrong:**
The Kalshi websocket sends an `orderbook_snapshot` on subscription, then incremental `orderbook_delta` messages with a `seq` (sequence number) field. If any delta is missed -- due to a network blip, slow consumer, or process hiccup -- every subsequent delta is applied to a stale base. The reconstructed orderbook silently diverges from reality. Clients consuming your API get wrong prices, wrong depths, wrong spread data. For algo traders, this is catastrophic -- they make decisions on phantom liquidity.

**Why it happens:**
Developers build the happy path (snapshot + apply deltas) and never implement sequence validation. The Kalshi Go client reference implementation (`github.com/ammario/kalshi/blob/main/feed.go`) validates sequences strictly -- `if header.Seq != wantSeq { return error }` -- but simply errors out with no recovery. Many implementations copy this pattern but then swallow the error or log-and-continue, leaving a corrupted book in memory.

**How to avoid:**
- Validate `seq` on every delta message. If `seq != expected`, immediately mark that market's book as STALE.
- On any gap detection, unsubscribe and resubscribe to trigger a fresh `orderbook_snapshot` from Kalshi.
- Never serve stale book data to API consumers -- return a `503 Stale Data` or flag the response with a staleness indicator.
- Persist the last known good `seq` per market so you can detect gaps across process restarts.
- Implement a periodic full-book reconciliation (e.g., REST API snapshot every 60 seconds) to detect silent drift that sequence checking alone might not catch.

**Warning signs:**
- Orderbook spreads that go negative or show impossible price levels.
- Your stored book diverges from Kalshi's REST API `/orderbook` endpoint when spot-checked.
- Sequence gap counter is non-zero in monitoring.
- Consumers report stale or incorrect price data.

**Phase to address:**
Phase 1 (Data Collection) -- this is the foundational integrity guarantee. Everything downstream (storage, API, consumer trust) depends on this being correct from day one.

---

### Pitfall 2: Websocket Disconnection and Process Crash Losing Data Windows

**What goes wrong:**
The Kalshi websocket drops (network partition, Kalshi maintenance, your process crashes, machine reboots). During the disconnection window, orderbook deltas are lost permanently. If your system doesn't detect the gap and re-snapshot, you have a hole in your historical data. Worse: if the collector process crashes and restarts, it may reconnect and start storing deltas without realizing it missed a window, creating an undetectable data gap.

**Why it happens:**
The Kalshi websocket sends ping frames every 10 seconds with body `heartbeat` -- clients must respond with pong. Many websocket libraries handle this automatically (Python `websockets` does), but not all do. If pong is missed, Kalshi drops the connection silently. Developers assume the connection is alive because no error fires until the next read attempt. Process-level crashes are even worse because there is no graceful shutdown to mark the gap.

**How to avoid:**
- Implement a heartbeat watchdog: if no message (data or ping) received in 15 seconds, assume connection is dead and force reconnect.
- On every reconnect: (1) log the disconnection timestamp, (2) resubscribe to all channels, (3) receive fresh snapshots, (4) record the gap window in a `data_gaps` table for downstream consumers to query.
- Use a process supervisor (systemd, pm2, Docker restart policy) that auto-restarts the collector.
- On startup, always assume the book is empty -- never resume from in-memory state. Force a full snapshot.
- Consider running two collector instances for redundancy -- if one drops, the other covers the gap.

**Warning signs:**
- Heartbeat timeout counter incrementing in metrics.
- Gaps in your `orderbook_snapshots` table timestamps (e.g., no data for 30+ seconds).
- Process uptime significantly shorter than wall-clock time (frequent restarts).
- Consumers reporting "no data available" for specific time windows.

**Phase to address:**
Phase 1 (Data Collection) -- reconnection logic and gap tracking are core collector requirements, not add-ons.

---

### Pitfall 3: Supabase TimescaleDB Deprecation Trap

**What goes wrong:**
You build your time-series storage on TimescaleDB hypertables (the obvious choice for orderbook data), then discover that TimescaleDB is deprecated on Supabase Postgres 17. Per Supabase's official announcement, existing Postgres 15 projects have until approximately May 2026 before end-of-life, at which point you must drop the extension before upgrading. Additionally, Supabase only provides the Apache 2 Edition, so continuous aggregates, compression, data retention policies, and distributed hypertables are all unavailable.

**Why it happens:**
TimescaleDB is the standard answer for "time-series in Postgres" and every tutorial recommends it. The deprecation happened because TimescaleDB's complexity didn't match its usage patterns on the Supabase platform. Developers who don't check Supabase-specific docs will build on a foundation with a known expiration date.

**How to avoid:**
- Do NOT use TimescaleDB on Supabase. Use native Postgres range partitioning with `pg_partman` (which Supabase is adding to Postgres 17).
- Design your schema with `PARTITION BY RANGE (timestamp)` from the start -- daily or hourly partitions depending on data volume.
- Use `date_bin()` (native Postgres) instead of TimescaleDB's `time_bucket()` for time-series aggregations.
- Use BRIN indexes on timestamp columns instead of B-tree -- they are dramatically smaller and faster for append-only time-series data.
- Plan for partition management (creating future partitions, detaching old ones) from day one.

**Warning signs:**
- Using `CREATE TABLE ... USING timescaledb` or `create_hypertable()` in migrations.
- Supabase dashboard warnings about deprecated extensions.
- Inability to upgrade to Postgres 17 when the time comes.

**Phase to address:**
Phase 1 (Database Schema Design) -- schema decisions are the hardest to change later. Getting partitioning right from the start avoids a painful migration.

---

### Pitfall 4: Supabase Write Throughput Ceiling for High-Frequency Orderbook Data

**What goes wrong:**
Kalshi orderbook deltas can arrive at high frequency across many markets simultaneously. Each delta triggers an INSERT into Postgres through Supabase's connection pooler. At scale, you hit multiple bottlenecks: connection pool exhaustion, RLS policy overhead on every write, Supabase Realtime fan-out (every insert triggers N authorization checks for N subscribers), and index maintenance on hot tables. Writes start queuing, latency spikes, and you lose data because the websocket consumer falls behind.

**Why it happens:**
Supabase is optimized for typical web app workloads (moderate reads/writes with auth). High-frequency append-only writes from a data collector are an atypical pattern. Specific gotchas:
- PgBouncer in transaction mode does not support prepared statements, so your ORM/driver might silently fall back to less efficient query patterns.
- RLS policies execute per-row on writes. Even simple `auth.uid() = user_id` checks cause measurable overhead at thousands of writes per second.
- Supabase Realtime checks authorization for every subscriber on every change -- 100 subscribers x 1 insert = 100 authorization queries.
- Default connection pool sizes are conservative (tied to your Supabase plan tier).

**How to avoid:**
- Use a direct Postgres connection (not through the REST API or Realtime) for the collector process. Use the pooler only for API-serving reads.
- Batch inserts: accumulate deltas in memory for 100-500ms, then INSERT in a single multi-row statement. This dramatically reduces connection overhead and index churn.
- Disable RLS on collector-only tables (the collector uses a service role, not end-user auth). Add RLS only on API-facing views.
- Do NOT enable Supabase Realtime subscriptions on high-write tables. Serve real-time data through your own API layer instead.
- Index columns referenced in RLS policies. A missing index on the RLS-filtered column can cause 100x slowdowns on large tables.
- Wrap RLS function calls in `(SELECT ...)` subqueries to enable query planner caching.
- Monitor connection pool utilization and queue depth via Supabase's Observability dashboard.

**Warning signs:**
- Connection pool utilization consistently above 70%.
- Write latency (p99) exceeding 100ms for simple inserts.
- "Too many connections" errors in application logs.
- Supabase Realtime lagging behind or dropping messages.
- `pg_stat_activity` showing many `idle in transaction` connections.

**Phase to address:**
Phase 1 (Data Collection) for write path optimization. Phase 2 (API Layer) for read path and RLS configuration.

---

### Pitfall 5: Stripe Webhook Unreliability Breaking Subscription Access Control

**What goes wrong:**
Your API access control depends on Stripe webhook events to know who has an active subscription. Stripe can deliver events late (hours), deliver duplicates, deliver out-of-order, or fail to deliver entirely if your endpoint returns non-2xx. The result: customers lose API access despite paying, or get free access after cancellation. Both destroy trust.

**Why it happens:**
Developers treat webhooks as synchronous notifications ("Stripe tells me, I update"). In reality, webhooks are unreliable async messages. Specific failure modes:
- `invoice.paid` arrives before `customer.subscription.created` -- your system doesn't know the subscription exists yet.
- `invoice.payment_failed` retries happen over days (Smart Retries) -- access toggling during dunning confuses users.
- Duplicate `invoice.paid` events credit the account twice.
- Your webhook endpoint times out under load (Stripe expects response within seconds), Stripe retries, creating duplicate processing.
- `invoice.created` webhook failure delays invoice finalization for up to 72 hours (per Stripe docs).
- Trial-to-paid transition: if the `customer.subscription.trial_will_end` event is missed and payment method is missing, the subscription silently moves to `incomplete`.

**How to avoid:**
- Make every webhook handler idempotent. Store processed `event.id`s in a database table with a unique constraint. Return 200 for duplicates without processing.
- Never trust event ordering. Use the `data.object` state from the event payload, not the event type alone, to determine current subscription status.
- Implement a "reconciliation cron" that polls Stripe's API every 5-10 minutes to verify subscription statuses match your database. This is your safety net for missed webhooks.
- During dunning (failed payment retries), keep access active for a grace period (e.g., 3-7 days) rather than immediately revoking. Smart Retries can recover many failed payments.
- Verify webhook signatures (`stripe.webhooks.constructEvent`) on every request. Never skip this.
- Set up Stripe webhook endpoint to only receive events you handle (not all events) to prevent overwhelm.
- Store access as an expiration timestamp (updated from `invoice.paid`) rather than a boolean flag. This way, if webhooks fail, access naturally expires rather than persisting forever.

**Warning signs:**
- Customers reporting "access denied" within hours of payment.
- Webhook processing time exceeding 5 seconds (Stripe may retry).
- Duplicate entries in your subscription or payment tables.
- Reconciliation cron finding mismatches between Stripe and your database.
- Webhook failure rate visible in Stripe Dashboard > Developers > Webhooks.

**Phase to address:**
Phase 3 (Billing/Monetization) -- but the access control data model (expiration-based, not boolean) should be designed in Phase 2 (API Layer).

---

### Pitfall 6: API Rate Limiting That Blocks Agents and Frustrates Power Users

**What goes wrong:**
You implement rate limiting at a single level (e.g., 100 requests/minute per API key) using a naive counter. Power users and AI agents hit it constantly. Agents are especially problematic -- they make rapid sequential calls without backoff, burn through limits in seconds, then fail without understanding why. Meanwhile, a single misbehaving client can degrade performance for everyone because you have no per-tier or per-endpoint differentiation.

**Why it happens:**
Rate limiting seems simple (count requests, reject over limit) but production implementations need multiple dimensions: per-key, per-endpoint, per-tier, burst allowance, and agent-aware responses. Most first implementations get only one of these right.

**How to avoid:**
- Use token bucket algorithm (not fixed window) -- it allows legitimate bursts while enforcing sustained rate limits. Redis with a Lua script for atomicity is the standard implementation.
- Implement tiered limits: free tier (low), paid tier (higher), enterprise (custom). Tie limits to Stripe subscription tier.
- Always return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers. Agents parse these programmatically to self-throttle.
- Return `429 Too Many Requests` with a `Retry-After` header (in seconds). Agents and HTTP client libraries respect this automatically.
- Implement per-endpoint limits in addition to global limits. A snapshot endpoint (expensive) should have a lower limit than a status endpoint (cheap).
- For agent consumers specifically: support long-polling or websocket endpoints so they don't need to poll repeatedly.

**Warning signs:**
- High rate of 429 responses (more than 5% of requests).
- Customer complaints about rate limits despite being on paid plans.
- Uneven request distribution (one client consuming disproportionate resources).
- Agent clients retrying without backoff, amplifying the load.

**Phase to address:**
Phase 2 (API Layer) -- rate limiting is part of the API middleware, but tier integration depends on Phase 3 (Billing).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Storing orderbook state only in memory (no snapshots to DB) | Simpler collector, less write load | Complete data loss on crash, no historical replay, no gap detection | Never for a data product -- historical data IS the product |
| Using Supabase REST API for collector writes | No direct Postgres connection to manage | 2-5x higher latency per write, connection pool contention with API reads, RLS overhead on every write | Only during prototyping with <5 markets |
| Single-process collector (no redundancy) | Simpler deployment | Any crash = data gap visible to paying customers | Acceptable for MVP/beta with explicit SLA caveat to users |
| Hardcoded rate limits (no tier integration) | Ship rate limiting faster | Manual updates when plans change, inconsistency between billing and access | MVP only; integrate with Stripe metadata before public launch |
| Polling Stripe API instead of webhooks | Simpler to implement, more predictable | Higher API usage, 5-10 minute latency on subscription changes, Stripe rate limit risk | Acceptable as reconciliation backup, never as primary |
| Skipping RLS and using service role key for API reads | Faster queries, simpler setup | One leaked key = full database access; no per-user audit trail | Never for a multi-tenant API product |
| TimescaleDB hypertables on Supabase | Familiar time-series API, faster initial development | Forced migration before May 2026, no compression/continuous aggregates on Apache 2 edition | Never -- use native partitioning from the start |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Kalshi Websocket Auth | Generating HMAC signature once and reusing -- signatures are timestamped and expire | Generate fresh `KALSHI-ACCESS-SIGNATURE` with current `KALSHI-ACCESS-TIMESTAMP` on each connection/reconnection |
| Kalshi Websocket Channels | Using `market_id` to subscribe to orderbook updates | Use `market_ticker` (string) or `market_tickers` (array) -- `market_id`/`market_ids` are not supported for orderbook channels |
| Supabase Connection Pooler | Using both Supavisor and PgBouncer simultaneously | Choose one. Running both increases risk of hitting max connection limits. Use PgBouncer (dedicated) for performance-critical writes, Supavisor (shared) for general API traffic |
| Supabase Prepared Statements | Using ORMs that generate prepared statements through the transaction-mode pooler | PgBouncer in transaction mode does NOT support prepared statements. Disable them in your driver/ORM configuration or use session mode for the collector |
| Stripe Webhook Signatures | Parsing the request body as JSON before signature verification | Signature verification requires the RAW request body. Middleware that parses JSON first will cause verification to fail. Ensure raw body is available |
| Stripe Test vs Live | Mixing test and live webhook endpoints or API keys during development | Use separate webhook endpoints for test and live modes. Verify `livemode` field in event payloads as a safety check |
| Supabase API Keys | Exposing the `service_role` key in client-side code or API responses | Supabase is migrating to `sb_publishable_` and `sb_secret_` keys (from Nov 2025). Only use secret keys server-side. Anon/publishable keys are safe to expose ONLY with proper RLS |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| B-tree indexes on timestamp columns in append-only tables | Index bloat, write amplification, slow inserts as table grows | Use BRIN indexes for time-ordered append-only data. 100-1000x smaller than B-tree for the same data | >10M rows per partition |
| No table partitioning on orderbook data | Full table scans on time-range queries, vacuum taking hours, index bloat | Partition by range on timestamp (daily or hourly partitions). Use `pg_partman` for automated partition management | >50M rows total |
| Too many partitions | Query planner memory exhaustion, slow planning phase | Start with daily partitions. Only go hourly if daily partitions exceed 10M rows. Keep active partition count under 100 | >200 partitions |
| RLS policies with function calls not wrapped in SELECT | Function evaluated per-row instead of once per query | Wrap `auth.uid()` and custom functions in `(SELECT ...)` to enable initPlan optimization | >100K rows in queried table |
| Supabase Realtime enabled on high-write tables | Database bottleneck from N authorization checks per insert per subscriber | Disable Realtime on collector tables. Serve real-time data through your own websocket/SSE endpoint | >10 subscribers AND >10 writes/second |
| No connection pooling for API reads | Each API request opens/closes a Postgres connection | Use Supavisor transaction mode (port 6543) for API traffic. Keep pool_size at or below 40% of max connections | >50 concurrent API requests |
| Unindexed columns in RLS policies | Full table scan on every read through the policy | Add B-tree index on every column referenced in RLS WHERE clauses. Can yield 100x improvement | >100K rows |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Service role key in environment variables accessible to client-side code | Full database bypass of RLS; attacker can read/write all data | Use Supabase's new `sb_secret_` keys. Store only in server-side env. Rotate immediately if exposed. Consider Supabase Vault for secret management |
| API keys without per-user scoping | One leaked key exposes another user's data; no ability to revoke individual access | Generate per-user API keys (not just per-plan). Store hashed keys. Implement key rotation endpoint |
| No webhook signature verification | Attacker can forge Stripe events to grant themselves free access or manipulate billing state | Always verify signatures using `stripe.webhooks.constructEvent()`. Reject unsigned or invalid events with 400 |
| Orderbook data available without authentication on free tier | Data scraping; competitor can mirror your entire dataset for free | Always require API key even on free tier. Implement progressive throttling. Consider watermarking responses (add a synthetic field that identifies the subscriber) |
| Rate limit bypass via multiple API keys | Single user creates multiple free accounts to multiply their rate limit | Rate limit by user identity (email/account), not just API key. Implement IP-based secondary limits |
| SQL injection through market ticker parameters | Database compromise | Always use parameterized queries. Never interpolate user input into SQL. Supabase PostgREST handles this for REST API, but custom endpoints need explicit parameterization |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No data freshness indicator in API responses | Consumers cannot tell if data is current or stale (from a disconnection window) | Include `data_timestamp`, `collected_at`, and `is_stale` fields in every response. Let consumers decide how to handle stale data |
| Rate limit errors without clear remediation | Agents fail silently or retry endlessly without understanding the issue | Return `429` with `Retry-After` header, `X-RateLimit-*` headers, and a JSON body explaining the limit and how to upgrade |
| Opaque pricing tiers with unclear usage metering | Customers cannot predict costs or understand what counts as a "request" | Show real-time usage dashboard. Define "request" clearly in docs. Provide usage estimation calculator |
| No OpenAPI spec or machine-readable docs | AI agents cannot auto-discover or reason about your API | Publish a complete OpenAPI 3.1 spec with rich descriptions on every field, multiple examples per endpoint, and semantic error codes. This is the difference between "agent-usable" and "agent-friendly" |
| API changes without versioning or deprecation notices | Consumer integrations break without warning | Version your API from v1. Never remove fields. Add deprecation headers 30+ days before breaking changes |
| No sandbox/test environment | Consumers must test against production data with real API keys | Provide a sandbox with sample data. Use separate API keys for test vs production |

## "Looks Done But Isn't" Checklist

- [ ] **Websocket Collector:** Often missing sequence gap detection -- verify by intentionally dropping a message in tests and confirming the system re-snapshots
- [ ] **Websocket Collector:** Often missing process crash recovery -- verify by killing the process mid-stream and confirming clean reconnection with gap logging
- [ ] **Websocket Collector:** Often missing multi-market scaling -- verify that subscribing to 50+ markets simultaneously doesn't cause consumer lag
- [ ] **Database Schema:** Often missing partition management automation -- verify that future partitions are created before they're needed (not just the current one)
- [ ] **Database Schema:** Often missing data retention policy -- verify old partitions are detached/archived after N days to keep active dataset manageable
- [ ] **API Layer:** Often missing stale data indicators -- verify API responses include freshness metadata when serving from a gap window
- [ ] **Stripe Integration:** Often missing dunning grace period -- verify that access is not immediately revoked on first payment failure
- [ ] **Stripe Integration:** Often missing webhook idempotency -- verify by sending the same event twice and confirming no duplicate side effects
- [ ] **Stripe Integration:** Often missing reconciliation job -- verify by disabling webhooks temporarily and confirming the cron job catches mismatches
- [ ] **Rate Limiting:** Often missing tier integration -- verify that upgrading a Stripe subscription immediately updates rate limits without requiring API key regeneration
- [ ] **API Docs:** Often missing agent-friendly metadata -- verify your OpenAPI spec validates and includes descriptions for all parameters, response fields, and error codes

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Corrupted orderbook from missed deltas | LOW | Force re-snapshot by unsubscribing/resubscribing to affected market. Mark gap window in database. Affected historical data cannot be recovered unless you have a redundant collector |
| Extended data gap from collector downtime | MEDIUM | Log gap window. Backfill from Kalshi REST API if available (limited to current state, not historical). Notify affected subscribers. Consider SLA credit |
| TimescaleDB migration (if already deployed) | HIGH | Must migrate all hypertables to native partitioned tables. Requires downtime. Use `pg_partman` to manage new partitions. Convert `time_bucket()` calls to `date_bin()`. Rebuild BRIN indexes |
| Supabase write throughput ceiling hit | MEDIUM | Implement batch inserts. Move collector to direct Postgres connection. Disable Realtime on affected tables. Consider Supabase plan upgrade for dedicated pooler. As last resort, move write-heavy tables to self-hosted Postgres |
| Stripe webhook data inconsistency | LOW | Run reconciliation against Stripe API. Update local subscription states. Email affected users about any access disruption. Implement reconciliation cron to prevent recurrence |
| Leaked service role key | HIGH | Rotate key immediately in Supabase dashboard. Audit database for unauthorized changes. Check if data was exfiltrated. Migrate to new Supabase API key format (`sb_secret_`). Add key rotation to incident runbook |
| Rate limiting not working (overloaded API) | MEDIUM | Implement emergency global rate limit at infrastructure level (e.g., Cloudflare). Identify abusive keys and revoke. Deploy proper per-key token bucket. Communicate incident to affected users |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent orderbook corruption (missed deltas) | Phase 1: Data Collection | Unit test that simulates a sequence gap and verifies re-snapshot trigger. Integration test against live Kalshi feed with intentional network interruption |
| Websocket disconnection data gaps | Phase 1: Data Collection | Verify `data_gaps` table is populated after simulated disconnect. Confirm collector auto-restarts and re-snapshots |
| TimescaleDB deprecation | Phase 1: Database Schema | Confirm no TimescaleDB references in migrations. Verify native partitioning and `pg_partman` are used |
| Supabase write throughput ceiling | Phase 1: Data Collection | Load test with expected market count. Measure p99 write latency. Verify batch insert implementation |
| Stripe webhook unreliability | Phase 3: Billing | Send duplicate webhook events and verify idempotent handling. Disable webhooks and verify reconciliation cron catches drift. Test full subscription lifecycle (create, upgrade, downgrade, cancel, payment failure, recovery) |
| Rate limiting blocking agents | Phase 2: API Layer | Verify `429` responses include `Retry-After` and `X-RateLimit-*` headers. Test that tier changes from Stripe update rate limits within 5 minutes |
| API not agent-friendly | Phase 2: API Layer | Validate OpenAPI spec with `swagger-cli validate`. Test that an LLM can discover and use the API from the spec alone (manual test) |
| RLS performance degradation | Phase 2: API Layer | EXPLAIN ANALYZE queries through the API with RLS enabled. Verify indexes exist on all RLS-referenced columns. Benchmark read latency at expected subscriber count |
| Service role key exposure | Phase 1: Infrastructure | Verify key is only in server-side environment variables. No references in client-side code or API responses. Rotate and test |
| Data staleness not communicated | Phase 2: API Layer | Verify every API response includes `collected_at` timestamp and freshness metadata. Test behavior during a simulated gap window |

## Sources

- [Kalshi API WebSocket Documentation](https://docs.kalshi.com/websockets/websocket-connection) - Official connection and channel docs (HIGH confidence)
- [Kalshi Orderbook Updates Documentation](https://docs.kalshi.com/websockets/orderbook-updates) - Snapshot/delta message format with `seq` field (HIGH confidence)
- [Kalshi Go Client - feed.go](https://github.com/ammario/kalshi/blob/main/feed.go) - Reference implementation showing strict sequence validation (HIGH confidence)
- [Supabase TimescaleDB Deprecation](https://supabase.com/docs/guides/database/extensions/timescaledb) - Official deprecation notice for Postgres 17 (HIGH confidence)
- [Supabase Postgres 17 Release Discussion](https://github.com/orgs/supabase/discussions/35851) - Timeline: ~May 2026 for PG15 EOL, pg_partman as replacement (HIGH confidence)
- [Supabase Connection Management](https://supabase.com/docs/guides/database/connecting-to-postgres) - Pooler options, transaction mode limitations (HIGH confidence)
- [Supabase RLS Performance Best Practices](https://supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv) - Index recommendations, SELECT wrapping trick (HIGH confidence)
- [Supabase Realtime Benchmarks](https://supabase.com/docs/guides/realtime/benchmarks) - Authorization fan-out bottleneck (HIGH confidence)
- [Stripe Subscription Webhooks](https://docs.stripe.com/billing/subscriptions/webhooks) - Event lifecycle, 72-hour finalization delay, retry behavior (HIGH confidence)
- [Stripe Idempotent Webhooks](https://blog.adamzolo.com/idempotent-stripe-webhooks/) - Duplicate detection patterns (MEDIUM confidence)
- [Stripe Webhook Best Practices (Stigg)](https://www.stigg.io/blog-posts/best-practices-i-wish-we-knew-when-integrating-stripe-webhooks) - Real-world integration lessons (MEDIUM confidence)
- [AI-Friendly API Design Principles](https://github.com/stefanbuck/ai-api-best-practices) - Agent-specific API design guidelines (MEDIUM confidence)
- [API Rate Limiting at Scale (Gravitee)](https://www.gravitee.io/blog/rate-limiting-apis-scale-patterns-strategies) - Token bucket, distributed state, tiered limits (MEDIUM confidence)
- [WebSocket Architecture Best Practices (Ably)](https://ably.com/topic/websocket-architecture-best-practices) - Connection management patterns (MEDIUM confidence)
- [Supabase API Key Changes](https://github.com/orgs/supabase/discussions/29260) - Migration to sb_publishable_ and sb_secret_ keys (HIGH confidence)
- [Postgres Partitioning for Write-Heavy Workloads](https://www.cloudraft.io/blog/tuning-postgresql-for-write-heavy-workloads) - BRIN indexes, partition sizing (MEDIUM confidence)

---
*Pitfalls research for: KalshiBook -- Monetized L2 Orderbook Data API*
*Researched: 2026-02-13*
