"""Authentication proxy endpoints — POST /auth/signup, POST /auth/login.

Proxies user signup/login to Supabase Auth REST API.
These are public endpoints (no API key required).
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request

from src.api.errors import KalshiBookError
from src.api.models import AuthResponse, LoginRequest, SignupRequest

logger = structlog.get_logger("api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest, request: Request):
    """Create a new user account via Supabase Auth.

    Returns access and refresh tokens on success.
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

    logger.info("user_signup", email=body.email, user_id=result["user_id"])

    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user_id=result["user_id"],
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
