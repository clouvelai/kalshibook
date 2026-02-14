"""Market discovery and subscription management via Kalshi lifecycle channel."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from src.collector.metrics import get_logger, get_metrics
from src.collector.models import OverflowRecord

logger = get_logger("discovery")

# Event types that indicate an active, subscribable market
ACTIVE_EVENT_TYPES = {"created", "activated", "close_date_updated"}

# Event types that mean a market is no longer active
TERMINAL_EVENT_TYPES = {"determined", "settled", "deactivated", "closed"}


class MarketDiscovery:
    """Discovers new markets and manages orderbook subscriptions."""

    def __init__(
        self,
        max_subscriptions: int = 1000,
        subscribe_fn: Callable[[list[str]], Awaitable[None]] | None = None,
        unsubscribe_fn: Callable[[list[str]], Awaitable[None]] | None = None,
    ):
        self._max_subscriptions = max_subscriptions
        self._subscribe_fn = subscribe_fn
        self._unsubscribe_fn = unsubscribe_fn
        self._metrics = get_metrics()

        # State
        self._active_subscriptions: set[str] = set()
        self._pending_subscriptions: set[str] = set()
        self._overflow_tickers: list[str] = []

        # Callbacks set by orchestrator
        self.on_market_update: Callable[[dict], Awaitable[None]] | None = None
        self.on_overflow_record: Callable[[OverflowRecord], Awaitable[None]] | None = None

    @property
    def active_count(self) -> int:
        return len(self._active_subscriptions)

    @property
    def at_capacity(self) -> bool:
        return len(self._active_subscriptions) >= self._max_subscriptions

    async def handle_lifecycle_event(self, msg: dict) -> None:
        """Process a market lifecycle event from the WS.

        Expected format:
        {
            "type": "market_lifecycle_v2",
            "sid": 0,
            "seq": 0,
            "msg": {
                "market_ticker": "TICKER",
                "event_ticker": "EVENT",
                "market_id": "...",
                "action": "created|activated|deactivated|closed|settled|determined",
                "status": "active|closed|settled",
                "title": "...",
                ...
            }
        }
        """
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", "")
        event_type = data.get("event_type", "")

        if not ticker:
            logger.warning("lifecycle_missing_ticker", msg=msg)
            return

        logger.info(
            "lifecycle_event",
            ticker=ticker,
            event_type=event_type,
        )

        # Update market metadata in DB
        if self.on_market_update:
            await self.on_market_update({
                "ticker": ticker,
                "event_type": event_type,
                "metadata": {
                    k: v
                    for k, v in data.items()
                    if k not in ("market_ticker", "event_type")
                },
            })

        # Route by event type
        if event_type in ACTIVE_EVENT_TYPES:
            await self._try_subscribe(ticker)
        elif event_type in TERMINAL_EVENT_TYPES:
            await self._handle_terminal(ticker)
        else:
            logger.debug("lifecycle_unhandled_event_type", event_type=event_type)

    async def _try_subscribe(self, ticker: str, event_ticker: str = "") -> None:
        """Attempt to subscribe to a market's orderbook."""
        if ticker in self._active_subscriptions or ticker in self._pending_subscriptions:
            return

        if self.at_capacity:
            logger.warning(
                "subscription_cap_reached",
                ticker=ticker,
                active=self.active_count,
                cap=self._max_subscriptions,
            )
            self._overflow_tickers.append(ticker)
            self._metrics.overflow_markets = len(self._overflow_tickers)

            if self.on_overflow_record:
                await self.on_overflow_record(
                    OverflowRecord(
                        market_ticker=ticker,
                        event_ticker=event_ticker,
                    )
                )
            return

        # Subscribe
        self._pending_subscriptions.add(ticker)
        if self._subscribe_fn:
            await self._subscribe_fn([ticker])
        logger.info("subscription_requested", ticker=ticker)

    async def _handle_terminal(self, ticker: str) -> None:
        """Handle a market reaching a terminal state (settled/closed)."""
        was_active = ticker in self._active_subscriptions

        if was_active:
            # Unsubscribe from orderbook channel
            if self._unsubscribe_fn:
                await self._unsubscribe_fn([ticker])
            self._active_subscriptions.discard(ticker)
            self._metrics.active_subscriptions = len(self._active_subscriptions)
            logger.info("market_unsubscribed", ticker=ticker, reason="terminal_state")

            # Check if any overflow markets can now be subscribed
            await self._backfill_from_overflow()

        self._pending_subscriptions.discard(ticker)

    async def _backfill_from_overflow(self) -> None:
        """Subscribe overflow markets when capacity becomes available."""
        while self._overflow_tickers and not self.at_capacity:
            ticker = self._overflow_tickers.pop(0)
            self._metrics.overflow_markets = len(self._overflow_tickers)
            logger.info("backfilling_overflow", ticker=ticker)
            await self._try_subscribe(ticker)

    def confirm_subscription(self, ticker: str, sid: int = 0) -> None:
        """Called when a subscription is confirmed by the WS server."""
        self._pending_subscriptions.discard(ticker)
        self._active_subscriptions.add(ticker)
        self._metrics.active_subscriptions = len(self._active_subscriptions)
        logger.info(
            "subscription_confirmed",
            ticker=ticker,
            sid=sid,
            active=self.active_count,
        )

    def confirm_unsubscription(self, ticker: str) -> None:
        """Called when an unsubscription is confirmed."""
        self._active_subscriptions.discard(ticker)
        self._pending_subscriptions.discard(ticker)
        self._metrics.active_subscriptions = len(self._active_subscriptions)

    def get_resubscribe_list(self) -> list[str]:
        """Return list of tickers to resubscribe after reconnection."""
        # Combine active and pending - all need resubscription after reconnect
        tickers = list(self._active_subscriptions | self._pending_subscriptions)
        logger.info("resubscribe_list", count=len(tickers))
        return tickers

    def load_existing_subscriptions(self, tickers: list[str]) -> None:
        """Load known active tickers from database on startup."""
        self._active_subscriptions = set(tickers)
        self._metrics.active_subscriptions = len(self._active_subscriptions)
        logger.info("loaded_existing_subscriptions", count=len(tickers))

    def clear_all(self) -> None:
        """Clear all subscription state (e.g., on full reconnect)."""
        self._active_subscriptions.clear()
        self._pending_subscriptions.clear()
        self._metrics.active_subscriptions = 0
