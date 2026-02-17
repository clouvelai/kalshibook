"""Internal parsing utilities for KalshiBook SDK."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string to a timezone-aware datetime.

    Handles the 'Z' suffix that datetime.fromisoformat() rejects on Python 3.10.
    Returns None if the input is None or empty string.
    """
    if not value:
        return None
    # Python 3.10 fromisoformat doesn't accept 'Z', 3.11+ does.
    # Normalize to +00:00 for cross-version safety.
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    dt = datetime.fromisoformat(normalized)
    # Ensure timezone-aware (server should always send tz-aware, but be defensive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
