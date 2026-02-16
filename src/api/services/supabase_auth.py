"""Supabase Auth client using httpx directly.

Avoids the supabase-py package dependency which requires websockets<16,
conflicting with the Kalshi WebSocket collector (websockets>=16).

This module provides a thin async wrapper around the Supabase GoTrue REST API
for the operations we need: signup, login, and JWT validation.
"""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger("api.supabase_auth")


class SupabaseAuthClient:
    """Async Supabase Auth client using httpx.

    Uses the Supabase service_role key for admin operations
    and the GoTrue REST API endpoints.
    """

    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self.base_url = supabase_url.rstrip("/")
        self.auth_url = f"{self.base_url}/auth/v1"
        self.service_role_key = service_role_key
        self._client = httpx.AsyncClient(
            base_url=self.auth_url,
            headers={
                "apikey": service_role_key,
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def auth_sign_up(self, email: str, password: str) -> dict:
        """Create a new user via Supabase Auth.

        Returns dict with access_token, refresh_token, user_id.

        Raises:
            Exception with descriptive message on failure.
        """
        resp = await self._client.post(
            "/signup",
            json={"email": email, "password": password},
        )

        if resp.status_code >= 400:
            body = resp.json()
            error_msg = (
                body.get("msg")
                or body.get("error_description")
                or body.get("message", "Signup failed")
            )
            raise Exception(error_msg)

        data = resp.json()

        # GoTrue returns access_token at root level (not nested under "session")
        access_token = data.get("access_token")
        user = data.get("user") or {}

        if not access_token:
            # User created but no session (email confirmation required)
            raise Exception(
                "Signup successful but email confirmation is required. "
                "Please check your email to confirm your account before logging in."
            )

        return {
            "access_token": access_token,
            "refresh_token": data.get("refresh_token", ""),
            "user_id": str(user.get("id", "")),
        }

    async def auth_sign_in(self, email: str, password: str) -> dict:
        """Authenticate a user with email and password.

        Returns dict with access_token, refresh_token, user_id.

        Raises:
            Exception with descriptive message on failure.
        """
        resp = await self._client.post(
            "/token?grant_type=password",
            json={"email": email, "password": password},
        )

        if resp.status_code >= 400:
            body = resp.json()
            error_msg = (
                body.get("msg")
                or body.get("error_description")
                or body.get("message", "Login failed")
            )
            raise Exception(error_msg)

        data = resp.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "user_id": str(data.get("user", {}).get("id", "")),
        }

    async def get_user(self, access_token: str) -> dict | None:
        """Validate a Supabase JWT and return user info.

        Returns dict with user_id and email, or None if token is invalid.
        """
        resp = await self._client.get(
            "/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        return {
            "user_id": str(data.get("id", "")),
            "email": data.get("email", ""),
        }


async def create_supabase_auth_client(
    supabase_url: str, service_role_key: str
) -> SupabaseAuthClient:
    """Create and return a SupabaseAuthClient instance."""
    client = SupabaseAuthClient(supabase_url, service_role_key)
    logger.info("supabase_auth_client_created", url=supabase_url)
    return client
