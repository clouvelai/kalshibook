"""Collector metrics and structured logging configuration."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

import structlog


def configure_logging() -> None:
    """Configure structlog for JSON output to stdout."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None, **kwargs) -> structlog.stdlib.BoundLogger:
    """Get a structured logger with optional context."""
    logger = structlog.get_logger(name)
    if kwargs:
        logger = logger.bind(**kwargs)
    return logger


@dataclass
class CollectorMetrics:
    """Track collector health and throughput metrics."""

    # Connection metrics
    connection_start_time: float = 0.0
    reconnect_count: int = 0
    last_message_time: float = 0.0
    last_disconnect_time: float = 0.0
    connection_state: str = "disconnected"  # connected, reconnecting, disconnected

    # Throughput counters
    messages_received: int = 0
    snapshots_stored: int = 0
    deltas_stored: int = 0
    active_subscriptions: int = 0

    # Data quality
    sequence_gaps_detected: int = 0
    stale_markets: int = 0
    overflow_markets: int = 0

    # Rate tracking (rolling window)
    _message_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    _rate_window_seconds: float = 60.0

    def record_connected(self) -> None:
        """Record a successful connection."""
        self.connection_start_time = time.monotonic()
        self.connection_state = "connected"

    def record_disconnected(self) -> None:
        """Record a disconnection."""
        self.last_disconnect_time = time.monotonic()
        self.connection_state = "disconnected"

    def record_reconnecting(self) -> None:
        """Record a reconnection attempt."""
        self.reconnect_count += 1
        self.connection_state = "reconnecting"

    def record_message(self) -> None:
        """Record an incoming message."""
        now = time.monotonic()
        self.messages_received += 1
        self.last_message_time = now
        self._message_times.append(now)

    def record_deltas_stored(self, count: int = 1) -> None:
        """Record deltas written to DB."""
        self.deltas_stored += count

    def record_gap_detected(self) -> None:
        """Record a sequence gap detection."""
        self.sequence_gaps_detected += 1

    @property
    def connection_uptime_seconds(self) -> float:
        """Seconds since last successful connection."""
        if self.connection_state != "connected" or self.connection_start_time == 0:
            return 0.0
        return time.monotonic() - self.connection_start_time

    @property
    def messages_per_second(self) -> float:
        """Compute messages/second over the rolling window."""
        if not self._message_times:
            return 0.0
        now = time.monotonic()
        cutoff = now - self._rate_window_seconds
        # Count messages within the window
        count = sum(1 for t in self._message_times if t >= cutoff)
        elapsed = min(now - self._message_times[0], self._rate_window_seconds)
        if elapsed <= 0:
            return 0.0
        return count / elapsed

    def as_dict(self) -> dict:
        """Return metrics as a dictionary for logging."""
        return {
            "connection_state": self.connection_state,
            "connection_uptime_s": round(self.connection_uptime_seconds, 1),
            "reconnect_count": self.reconnect_count,
            "messages_received": self.messages_received,
            "messages_per_second": round(self.messages_per_second, 2),
            "snapshots_stored": self.snapshots_stored,
            "deltas_stored": self.deltas_stored,
            "active_subscriptions": self.active_subscriptions,
            "sequence_gaps": self.sequence_gaps_detected,
            "stale_markets": self.stale_markets,
            "overflow_markets": self.overflow_markets,
        }


# Module-level singleton
_metrics: CollectorMetrics | None = None


def get_metrics() -> CollectorMetrics:
    """Get or create the singleton metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = CollectorMetrics()
    return _metrics


async def log_metrics_periodically(interval: float = 60.0) -> None:
    """Log metrics summary at regular intervals. Run as a background task."""
    logger = get_logger("metrics")
    metrics = get_metrics()

    try:
        while True:
            await asyncio.sleep(interval)
            logger.info("collector_metrics", **metrics.as_dict())
    except asyncio.CancelledError:
        return
