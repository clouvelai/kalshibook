"""Authentication proxy endpoints — POST /auth/signup, POST /auth/login.

Proxies user signup/login to Supabase Auth REST API.
These are public endpoints (no API key required).
"""

from __future__ import annotations

import asyncpg
import structlog
from fastapi import APIRouter, Depends, Request

from src.api.deps import get_db_pool
from src.api.errors import KalshiBookError
from src.api.models import AuthResponse, LoginRequest, SignupRequest
from src.api.services.auth import create_api_key
from src.api.services.billing import ensure_billing_account

logger = structlog.get_logger("api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse)
async def signup(
    body: SignupRequest,
    request: Request,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Create a new user account via Supabase Auth.

    Returns access and refresh tokens on success.
    Auto-provisions a billing account and default API key for the new user.

    Note: Google OAuth users do NOT go through this endpoint — the dashboard
    uses a lazy init pattern (check keys on first load, create default if
    none exist) to handle OAuth signup.
    """
    supabase = request.app.state.supabase
    request_id = getattr(request.state, "request_id", "")

    try:
        result = await supabase.auth_sign_up(body.email, body.password)
    except Exception as exc:
        error_msg = str(exc)
        logger.warning("signup_failed", email=body.email, error=error_msg)

        if "already registered" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise KalshiBookError(
                code="user_already_exists",
                message="A user with this email already exists.",
                status=409,
            ) from exc

        if "weak" in error_msg.lower() or "password" in error_msg.lower():
            raise KalshiBookError(
                code="weak_password",
                message="Password does not meet strength requirements.",
                status=422,
            ) from exc

        raise KalshiBookError(
            code="signup_failed",
            message=f"Signup failed: {error_msg}",
            status=400,
        ) from exc

    user_id = result["user_id"]
    logger.info("user_signup", email=body.email, user_id=user_id)

    # Auto-provision billing account and default API key.
    # Wrapped in try/except so signup still succeeds if provisioning fails.
    try:
        await ensure_billing_account(pool, user_id)
        await create_api_key(pool, user_id, name="default", key_type="dev")
        logger.info("user_provisioned", user_id=user_id)
    except Exception:
        logger.warning(
            "user_provisioning_failed",
            user_id=user_id,
            exc_info=True,
        )

    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user_id=user_id,
        request_id=request_id,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request):
    """Authenticate with email and password via Supabase Auth.

    Returns access and refresh tokens on success.
    """
    supabase = request.app.state.supabase
    request_id = getattr(request.state, "request_id", "")

    try:
        result = await supabase.auth_sign_in(body.email, body.password)
    except Exception as exc:
        error_msg = str(exc)
        logger.warning("login_failed", email=body.email, error=error_msg)

        raise KalshiBookError(
            code="invalid_credentials",
            message="Invalid email or password.",
            status=401,
        ) from exc

    logger.info("user_login", email=body.email, user_id=result["user_id"])

    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user_id=result["user_id"],
        request_id=request_id,
    )
