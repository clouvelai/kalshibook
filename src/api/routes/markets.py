"""Market listing and detail endpoints — GET /markets, GET /markets/{ticker}."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Markets"])

# Endpoint implementation in Plan 02-02
