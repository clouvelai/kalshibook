"""Tests for application configuration."""

from src.shared.config import Settings


def test_default_values():
    settings = Settings(kalshi_api_key_id="test-key")
    assert settings.batch_size == 500
    assert settings.flush_interval_seconds == 2.0
    assert settings.max_subscriptions == 1000
    assert settings.watchdog_timeout_seconds == 30.0
    assert settings.hot_storage_days == 7
    assert settings.db_pool_min_size == 5
    assert settings.db_pool_max_size == 20


def test_ws_url_defaults_to_prod():
    settings = Settings(kalshi_api_key_id="test-key")
    assert "api.elections.kalshi.com" in settings.kalshi_ws_url
    assert settings.kalshi_ws_path == "/trade-api/ws/v2"


def test_ws_url_override():
    settings = Settings(
        kalshi_api_key_id="test-key",
        kalshi_ws_url="wss://custom.example.com/ws",
    )
    assert settings.kalshi_ws_url == "wss://custom.example.com/ws"
