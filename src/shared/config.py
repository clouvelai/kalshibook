"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Kalshi API
    kalshi_api_key_id: str = ""
    kalshi_private_key_path: str = ""
    kalshi_private_key_content: str = ""

    # Supabase / Postgres
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_service_role_key: str = ""

    # App
    app_env: str = "development"

    # Kalshi WS
    kalshi_ws_url: str = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    kalshi_ws_path: str = "/trade-api/ws/v2"

    # Kalshi REST API
    kalshi_rest_base_url: str = "https://api.elections.kalshi.com/trade-api/v2"

    # Collector settings
    batch_size: int = 500
    flush_interval_seconds: float = 2.0
    periodic_snapshot_interval: int = 300
    max_subscriptions: int = 1000
    watchdog_timeout_seconds: float = 30.0

    # Archival settings
    hot_storage_days: int = 7
    archive_bucket: str = "orderbook-archive"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_project_price_id: str = ""
    stripe_meter_event_name: str = "kalshibook_api_credits"
    stripe_meter_event_id: str = ""

    # Frontend
    app_url: str = "http://localhost:3000"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_rate_limit_default: int = 120  # requests per minute (backstop; credits enforce real limits)

    # DB pool
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20

    # Dev login (used by scripts/dev-login.sh, ignored by app)
    dev_user_email: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Module-level singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
