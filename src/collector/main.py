"""Collector main entry point - orchestrates all components."""

from __future__ import annotations

import asyncio
import signal

from src.collector.connection import KalshiWSConnection, load_private_key
from src.collector.discovery import MarketDiscovery
from src.collector.enrichment import KalshiRestClient
from src.collector.metrics import (
    configure_logging,
    get_logger,
    get_metrics,
    log_metrics_periodically,
)
from src.collector.models import SettlementData, TradeExecution
from src.collector.processor import OrderbookProcessor, _parse_ts
from src.collector.writer import DatabaseWriter
from src.shared.config import Settings, get_settings
from src.shared.db import close_pool, create_pool, ensure_partitions

logger = get_logger("collector")

# Batch size for resubscriptions after reconnect
RESUBSCRIBE_BATCH_SIZE = 100


class CollectorService:
    """Orchestrates the data collection pipeline."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._metrics = get_metrics()
        self._shutdown_event = asyncio.Event()

        # Components (initialized in start())
        self._pool = None
        self._writer: DatabaseWriter | None = None
        self._processor: OrderbookProcessor | None = None
        self._discovery: MarketDiscovery | None = None
        self._connection: KalshiWSConnection | None = None
        self._enrichment: KalshiRestClient | None = None
        self._tasks: list[asyncio.Task] = []
        # GC protection for fire-and-forget background tasks
        self._fire_and_forget: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Initialize all components and run the collector."""
        logger.info("collector_starting", env=self._settings.app_env)

        # Database
        self._pool = await create_pool(
            self._settings.database_url,
            min_size=self._settings.db_pool_min_size,
            max_size=self._settings.db_pool_max_size,
        )

        # Ensure partitions exist
        try:
            await ensure_partitions(self._pool)
        except Exception:
            logger.warning("partition_creation_skipped", exc_info=True)

        # Writer
        self._writer = DatabaseWriter(
            pool=self._pool,
            max_batch_size=self._settings.batch_size,
            flush_interval=self._settings.flush_interval_seconds,
        )

        # Processor
        self._processor = OrderbookProcessor(
            on_resubscribe=self._handle_resubscribe,
        )
        self._processor.on_snapshot_ready = self._writer.add_snapshot
        self._processor.on_delta_ready = self._writer.add_delta
        self._processor.on_gap_record = self._writer.add_gap

        # Discovery
        self._discovery = MarketDiscovery(
            max_subscriptions=self._settings.max_subscriptions,
            subscribe_fn=self._subscribe_orderbook,
            unsubscribe_fn=self._unsubscribe_orderbook,
        )
        self._discovery.on_market_update = self._writer.add_market_update
        self._discovery.on_overflow_record = self._writer.add_overflow
        self._discovery.on_enrichment_needed = self._handle_enrichment_needed

        # Enrichment (REST API client for market/event/series data)
        try:
            private_key = load_private_key(self._settings)
            self._enrichment = KalshiRestClient(
                api_key_id=self._settings.kalshi_api_key_id,
                private_key=private_key,
                base_url=self._settings.kalshi_rest_base_url,
            )
            logger.info("enrichment_client_initialized")
        except Exception:
            logger.warning("enrichment_client_init_failed", exc_info=True)
            self._enrichment = None

        # Connection
        self._connection = KalshiWSConnection(
            settings=self._settings,
            on_message=self._handle_message,
            on_reconnect=self._handle_reconnect,
        )

        # Load known active markets from DB
        await self._load_existing_markets()

        # Register signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Run all tasks
        logger.info("collector_started")
        self._tasks = [
            asyncio.create_task(self._connection.start(), name="ws_connection"),
            asyncio.create_task(self._writer.start_flush_loop(), name="flush_loop"),
            asyncio.create_task(log_metrics_periodically(60.0), name="metrics"),
            asyncio.create_task(self._periodic_partition_check(), name="partitions"),
        ]
        try:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass
        finally:
            await self._cleanup()

    async def stop(self) -> None:
        """Signal the collector to shut down."""
        logger.info("collector_stopping")
        self._shutdown_event.set()
        if self._connection:
            await self._connection.stop()
        # Cancel all background tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        self._tasks.clear()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._enrichment:
            await self._enrichment.close()
        if self._writer:
            await self._writer.stop()
        await close_pool()
        logger.info("collector_stopped")

    async def _handle_message(self, msg: dict) -> None:
        """Route incoming WS messages to appropriate handlers."""
        msg_type = msg.get("type", "")

        if msg_type == "orderbook_snapshot":
            await self._processor.handle_snapshot(msg)

        elif msg_type == "orderbook_delta":
            await self._processor.handle_delta(msg)

        elif msg_type == "trade":
            await self._handle_trade(msg)

        elif msg_type in ("market_lifecycle_v2", "market_lifecycle"):
            await self._discovery.handle_lifecycle_event(msg)

        elif msg_type == "subscribed":
            # Subscription confirmed - extract tickers from the message
            params = msg.get("msg", {})
            tickers = params.get("market_tickers", [])
            sid = msg.get("sid", 0)
            for ticker in tickers:
                self._discovery.confirm_subscription(ticker, sid)
                self._processor.track_market(ticker, sid)

        elif msg_type == "unsubscribed":
            params = msg.get("msg", {})
            tickers = params.get("market_tickers", [])
            for ticker in tickers:
                self._discovery.confirm_unsubscription(ticker)
                self._processor.untrack_market(ticker)

        elif msg_type == "error":
            code = msg.get("code", 0)
            error_msg = msg.get("msg", "")
            logger.error("ws_error", code=code, error=error_msg)

        else:
            logger.debug("ws_unknown_type", type=msg_type)

    async def _handle_reconnect(self) -> None:
        """Handle reconnection: resubscribe to all channels."""
        logger.info("resubscribing_after_reconnect")

        # Subscribe to lifecycle channel (receives ALL events, no ticker filter)
        await self._connection.send_subscribe(["market_lifecycle_v2"])

        # Subscribe to trade channel (ALL public trades, no market_tickers filter)
        await self._connection.send_subscribe(["trade"])

        # Resubscribe to orderbook channels in batches
        tickers = self._discovery.get_resubscribe_list()
        if tickers:
            for i in range(0, len(tickers), RESUBSCRIBE_BATCH_SIZE):
                batch = tickers[i : i + RESUBSCRIBE_BATCH_SIZE]
                await self._connection.send_subscribe(["orderbook_delta"], batch)
                # Small delay between batches to avoid flooding
                if i + RESUBSCRIBE_BATCH_SIZE < len(tickers):
                    await asyncio.sleep(0.1)

            logger.info("resubscription_complete", total_tickers=len(tickers))

    async def _handle_resubscribe(self, ticker: str) -> None:
        """Handle resubscribe request from processor (gap recovery)."""
        logger.info("gap_recovery_resubscribe", ticker=ticker)
        # Unsubscribe then resubscribe to trigger fresh snapshot
        await self._connection.send_unsubscribe(["orderbook_delta"], [ticker])
        await asyncio.sleep(0.1)
        await self._connection.send_subscribe(["orderbook_delta"], [ticker])

    async def _subscribe_orderbook(self, tickers: list[str]) -> None:
        """Subscribe to orderbook updates for given tickers."""
        if self._connection and self._connection.is_connected:
            await self._connection.send_subscribe(["orderbook_delta"], tickers)

    async def _unsubscribe_orderbook(self, tickers: list[str]) -> None:
        """Unsubscribe from orderbook updates for given tickers."""
        if self._connection and self._connection.is_connected:
            await self._connection.send_unsubscribe(["orderbook_delta"], tickers)

    async def _handle_trade(self, msg: dict) -> None:
        """Parse and buffer a trade execution message."""
        data = msg.get("msg", {})
        try:
            trade = TradeExecution(
                trade_id=str(data.get("trade_id", "")),
                market_ticker=data.get("market_ticker", ""),
                yes_price=data.get("yes_price", 0),
                no_price=data.get("no_price", 0),
                count=data.get("count", 0),
                taker_side=data.get("taker_side", ""),
                ts=_parse_ts(data.get("ts")),
            )
            await self._writer.add_trade(trade)
        except Exception:
            logger.exception("trade_parse_failed", msg=data)

    async def _handle_enrichment_needed(self, data: dict) -> None:
        """Fire-and-forget enrichment task (does not block WS message loop)."""
        if not self._enrichment:
            return
        task = asyncio.create_task(self._enrich_market(data))
        self._fire_and_forget.add(task)
        task.add_done_callback(self._fire_and_forget.discard)

    async def _enrich_market(self, data: dict) -> None:
        """Fetch settlement, event, and series data from Kalshi REST API."""
        ticker = data.get("market_ticker", "")
        event_ticker = data.get("event_ticker", "")
        event_type = data.get("event_type", "")

        try:
            # Settlement enrichment for terminal events
            if event_type in ("determined", "settled"):
                market_data = await self._enrichment.get_market(ticker)
                if market_data:
                    result = market_data.get("result")
                    # Retry once if result is None (Kalshi API propagation delay)
                    if result is None:
                        logger.debug("settlement_result_pending", ticker=ticker)
                        await asyncio.sleep(5)
                        market_data = await self._enrichment.get_market(ticker)
                        result = market_data.get("result") if market_data else None

                    if market_data:
                        settlement = SettlementData(
                            market_ticker=ticker,
                            event_ticker=event_ticker or market_data.get("event_ticker", ""),
                            result=result,
                            settlement_value=market_data.get("settlement_value"),
                            determined_at=_parse_ts(market_data.get("determined_at"))
                            if market_data.get("determined_at")
                            else None,
                            settled_at=_parse_ts(market_data.get("settled_at"))
                            if market_data.get("settled_at")
                            else None,
                            source="rest_api",
                            metadata=market_data,
                        )
                        await self._writer.add_settlement(settlement)
                        logger.info("settlement_enriched", ticker=ticker, result=result)

                    # Update event_ticker from enriched market data if missing
                    if not event_ticker and market_data:
                        event_ticker = market_data.get("event_ticker", "")

            # Event enrichment
            if event_ticker:
                event_data = await self._enrichment.get_event(event_ticker)
                if event_data:
                    await self._writer.add_event_update(event_data)
                    logger.debug("event_enriched", event_ticker=event_ticker)

                    # Series enrichment (if event has a series)
                    series_ticker = event_data.get("series_ticker")
                    if series_ticker:
                        series_data = await self._enrichment.get_series(series_ticker)
                        if series_data:
                            await self._writer.add_series_update(series_data)
                            logger.debug("series_enriched", series_ticker=series_ticker)

        except Exception:
            logger.exception(
                "enrichment_failed",
                ticker=ticker,
                event_ticker=event_ticker,
                event_type=event_type,
            )

    async def _load_existing_markets(self) -> None:
        """Load known active markets from database on startup."""
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT ticker FROM markets WHERE status = 'active'"
                )
            tickers = [row["ticker"] for row in rows]
            if tickers:
                self._discovery.load_existing_subscriptions(tickers)
                logger.info("loaded_markets_from_db", count=len(tickers))
        except Exception:
            logger.warning("failed_to_load_markets", exc_info=True)

    async def _periodic_partition_check(self) -> None:
        """Periodically ensure future partitions exist."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(3600)  # Check every hour
                if self._pool:
                    await ensure_partitions(self._pool)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.warning("partition_check_failed", exc_info=True)


async def main() -> None:
    """Entry point for the collector service."""
    configure_logging()
    settings = get_settings()
    service = CollectorService(settings)
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
