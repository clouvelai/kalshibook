"""API key management endpoints — POST /keys, GET /keys, DELETE /keys/{id}."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["API Keys"])

# Endpoint implementation in Plan 02-03
