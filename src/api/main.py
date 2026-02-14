"""KalshiBook API — FastAPI application entry point.

Run with:
    uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.api.errors import generate_request_id, register_exception_handlers
from src.api.routes import deltas, keys, markets, orderbook
from src.shared.config import get_settings
from src.shared.db import close_pool, create_pool

logger = structlog.get_logger("api")


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def _rate_limit_key(request: Request) -> str:
    """Extract rate-limit key: API key for authenticated requests, IP otherwise."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer kb-"):
        return auth
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key, headers_enabled=True)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: DB pool creation and teardown."""
    settings = get_settings()
    pool = await create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    app.state.pool = pool
    logger.info("api_started", host=settings.api_host, port=settings.api_port)
    yield
    await close_pool()
    logger.info("api_stopped")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KalshiBook API",
    description="Historical L2 orderbook data for Kalshi prediction markets",
    lifespan=lifespan,
)

# Middleware — order matters (last added = first executed)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    """Inject a unique request_id into every request for tracing."""
    request.state.request_id = generate_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

app.include_router(orderbook.router)
app.include_router(deltas.router)
app.include_router(markets.router)
app.include_router(keys.router)
