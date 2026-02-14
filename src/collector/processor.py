"""Orderbook message processor with sequence validation and gap detection."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from src.collector.metrics import get_logger, get_metrics
from src.collector.models import (
    GapRecord,
    MarketSubscription,
    OrderbookDelta,
    OrderbookSnapshot,
)

logger = get_logger("processor")


class OrderbookProcessor:
    """Processes orderbook snapshots and deltas with sequence gap detection."""

    def __init__(
        self,
        on_resubscribe: Callable[[str], Awaitable[None]],
    ):
        self._subscriptions: dict[str, MarketSubscription] = {}
        self._on_resubscribe = on_resubscribe
        self._metrics = get_metrics()
        # Callbacks set by the orchestrator
        self.on_snapshot_ready: Callable[[OrderbookSnapshot], Awaitable[None]] | None = None
        self.on_delta_ready: Callable[[OrderbookDelta], Awaitable[None]] | None = None
        self.on_gap_record: Callable[[GapRecord], Awaitable[None]] | None = None

    def track_market(self, ticker: str, sid: int = 0) -> None:
        """Start tracking a market subscription."""
        self._subscriptions[ticker] = MarketSubscription(
            ticker=ticker,
            sid=sid,
            last_seq=-1,
            subscribed_at=datetime.now(timezone.utc),
        )
        logger.info("market_tracked", ticker=ticker, sid=sid)

    def untrack_market(self, ticker: str) -> None:
        """Stop tracking a market subscription."""
        self._subscriptions.pop(ticker, None)
        logger.info("market_untracked", ticker=ticker)

    async def handle_snapshot(self, msg: dict) -> None:
        """Process an orderbook_snapshot message.

        Expected format from Kalshi:
        {
            "type": "orderbook_snapshot",
            "sid": 123,
            "seq": 1,
            "msg": {
                "market_ticker": "TICKER",
                "yes": [[price, qty], ...],
                "no": [[price, qty], ...],
                "ts": 1234567890
            }
        }
        """
        sid = msg.get("sid", 0)
        seq = msg.get("seq", 0)
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", "")

        if not ticker:
            logger.warning("snapshot_missing_ticker", msg=msg)
            return

        snapshot = OrderbookSnapshot(
            market_ticker=ticker,
            seq=seq,
            sid=sid,
            yes=data.get("yes", []),
            no=data.get("no", []),
            ts=_parse_ts(data.get("ts")),
        )

        # Update tracking state - snapshot resets sequence tracking
        sub = self._subscriptions.get(ticker)
        if sub is None:
            sub = MarketSubscription(ticker=ticker)
            self._subscriptions[ticker] = sub

        sub.sid = sid
        sub.last_seq = seq
        sub.is_stale = False
        sub.subscribed_at = datetime.now(timezone.utc)

        logger.info(
            "snapshot_received",
            ticker=ticker,
            seq=seq,
            sid=sid,
            yes_levels=len(snapshot.yes),
            no_levels=len(snapshot.no),
        )

        # Forward to writer
        if self.on_snapshot_ready:
            await self.on_snapshot_ready(snapshot)

    async def handle_delta(self, msg: dict) -> None:
        """Process an orderbook_delta message.

        Expected format from Kalshi:
        {
            "type": "orderbook_delta",
            "sid": 123,
            "seq": 2,
            "msg": {
                "market_ticker": "TICKER",
                "price": 42,
                "delta": 5,
                "side": "yes",
                "ts": 1234567890
            }
        }
        """
        sid = msg.get("sid", 0)
        seq = msg.get("seq", 0)
        data = msg.get("msg", {})
        ticker = data.get("market_ticker", "")

        if not ticker:
            logger.warning("delta_missing_ticker", msg=msg)
            return

        sub = self._subscriptions.get(ticker)

        # If we're not tracking this market, start tracking
        if sub is None:
            logger.warning("delta_for_untracked_market", ticker=ticker, seq=seq)
            sub = MarketSubscription(ticker=ticker, sid=sid, last_seq=seq)
            self._subscriptions[ticker] = sub
            # Can't validate sequence for untracked market - accept it
        else:
            # Sequence validation
            expected_seq = sub.last_seq + 1

            if seq < expected_seq:
                # Duplicate or old message - discard
                logger.debug(
                    "delta_duplicate",
                    ticker=ticker,
                    seq=seq,
                    expected=expected_seq,
                )
                return

            if seq > expected_seq:
                # GAP DETECTED
                await self._handle_gap(ticker, expected_seq, seq, sid)
                return

        # Sequence is valid - update tracking
        sub.last_seq = seq
        sub.sid = sid

        delta = OrderbookDelta(
            market_ticker=ticker,
            seq=seq,
            sid=sid,
            price=data.get("price", 0),
            delta=data.get("delta", 0),
            side=data.get("side", ""),
            ts=_parse_ts(data.get("ts")),
        )

        # Forward to writer
        if self.on_delta_ready:
            await self.on_delta_ready(delta)

    async def _handle_gap(
        self, ticker: str, expected_seq: int, received_seq: int, sid: int
    ) -> None:
        """Handle a detected sequence gap."""
        self._metrics.record_gap_detected()

        sub = self._subscriptions.get(ticker)
        if sub:
            sub.is_stale = True
            self._metrics.stale_markets = sum(
                1 for s in self._subscriptions.values() if s.is_stale
            )

        gap = GapRecord(
            market_ticker=ticker,
            detected_at=datetime.now(timezone.utc),
            expected_seq=expected_seq,
            received_seq=received_seq,
            sid=sid,
        )

        logger.warning(
            "sequence_gap_detected",
            ticker=ticker,
            expected_seq=expected_seq,
            received_seq=received_seq,
            sid=sid,
            gap_size=received_seq - expected_seq,
        )

        # Record the gap
        if self.on_gap_record:
            await self.on_gap_record(gap)

        # Trigger re-subscription (unsubscribe + subscribe gets fresh snapshot)
        await self._on_resubscribe(ticker)

    def get_tracked_tickers(self) -> list[str]:
        """Return list of all currently tracked market tickers."""
        return list(self._subscriptions.keys())

    def get_subscription(self, ticker: str) -> MarketSubscription | None:
        """Get subscription state for a specific market."""
        return self._subscriptions.get(ticker)

    def clear_all(self) -> None:
        """Clear all subscription tracking (e.g., on full reconnect)."""
        self._subscriptions.clear()
        self._metrics.stale_markets = 0


def _parse_ts(ts_value) -> datetime:
    """Parse a timestamp from Kalshi (could be epoch seconds or milliseconds)."""
    if ts_value is None:
        return datetime.now(timezone.utc)
    if isinstance(ts_value, (int, float)):
        # Kalshi sends epoch seconds (or milliseconds)
        if ts_value > 1e12:
            # Milliseconds
            return datetime.fromtimestamp(ts_value / 1000, tz=timezone.utc)
        return datetime.fromtimestamp(ts_value, tz=timezone.utc)
    return datetime.now(timezone.utc)
