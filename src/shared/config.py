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

    # Collector settings
    batch_size: int = 500
    flush_interval_seconds: float = 2.0
    periodic_snapshot_interval: int = 300
    max_subscriptions: int = 1000
    watchdog_timeout_seconds: float = 30.0

    # Archival settings
    hot_storage_days: int = 7
    archive_bucket: str = "orderbook-archive"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_rate_limit_default: int = 100  # requests per minute

    # DB pool
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Module-level singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
