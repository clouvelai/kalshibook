"""KalshiBook API — FastAPI application entry point.

Run with:
    uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.api.errors import generate_request_id, register_exception_handlers
from src.api.routes import auth, billing, deltas, keys, markets, orderbook
from src.api.services.supabase_auth import create_supabase_auth_client
from src.shared.config import get_settings
from src.shared.db import close_pool, create_pool

logger = structlog.get_logger("api")

# Resolve static directory relative to project root
_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

def _rate_limit_key(request: Request) -> str:
    """Extract rate-limit key: API key for authenticated requests, IP otherwise."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer kb-"):
        return auth
    return get_remote_address(request)


# Rate limiter set to 120/minute (Project-tier max) as abuse backstop.
# The credit system (require_credits) is the real enforcement mechanism --
# free users with 1000 credits/month will exhaust credits before rate limits matter.
limiter = Limiter(key_func=_rate_limit_key, headers_enabled=True)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: DB pool, Supabase client creation and teardown."""
    settings = get_settings()
    pool = await create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    app.state.pool = pool

    # Initialize Supabase Auth client (uses httpx, not supabase-py)
    supabase = await create_supabase_auth_client(
        supabase_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
    )
    app.state.supabase = supabase

    # Initialize Stripe API key if configured
    import stripe as stripe_lib

    if settings.stripe_secret_key:
        stripe_lib.api_key = settings.stripe_secret_key
        logger.info("stripe_initialized")

    logger.info("api_started", host=settings.api_host, port=settings.api_port)
    yield
    await supabase.close()
    await close_pool()
    logger.info("api_stopped")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KalshiBook API",
    description=(
        "Historical L2 orderbook data for Kalshi prediction markets. "
        "Query reconstructed orderbook state at any timestamp, raw deltas, "
        "and market metadata for backtesting and automated trading."
    ),
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User signup and login via Supabase Auth.",
        },
        {
            "name": "API Keys",
            "description": (
                "Manage API keys for data endpoint access. "
                "Requires a Supabase access token (from POST /auth/login)."
            ),
        },
        {
            "name": "Orderbook",
            "description": "Reconstruct historical orderbook state at any timestamp.",
        },
        {
            "name": "Deltas",
            "description": "Query raw orderbook delta events with cursor-based pagination.",
        },
        {
            "name": "Markets",
            "description": "List and inspect available markets with data coverage info.",
        },
        {
            "name": "Billing",
            "description": (
                "Credit-based billing, Stripe subscription management, "
                "and usage tracking."
            ),
        },
        {
            "name": "Health",
            "description": "Service health checks.",
        },
    ],
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


@app.middleware("http")
async def inject_credit_headers(request: Request, call_next):
    """Add credit usage headers to every API response.

    These are populated by the require_credits dependency on data endpoints.
    Non-data endpoints (health, auth, keys) won't have credit info on request.state.
    """
    response = await call_next(request)
    if hasattr(request.state, "credits_remaining"):
        response.headers["X-Credits-Remaining"] = str(request.state.credits_remaining)
        response.headers["X-Credits-Used"] = str(request.state.credits_used)
        response.headers["X-Credits-Total"] = str(request.state.credits_total)
        response.headers["X-Credits-Cost"] = str(request.state.credits_cost)
    return response


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# llms.txt discovery files for AI agents
# ---------------------------------------------------------------------------

@app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
async def llms_txt():
    """Serve the AI agent discovery file (llms.txt spec)."""
    return (_STATIC_DIR / "llms.txt").read_text()


@app.get("/llms-full.txt", response_class=PlainTextResponse, include_in_schema=False)
async def llms_full_txt():
    """Serve the detailed AI agent API reference."""
    return (_STATIC_DIR / "llms-full.txt").read_text()


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(orderbook.router)
app.include_router(deltas.router)
app.include_router(markets.router)
app.include_router(keys.router)
app.include_router(billing.router)
