from app.config import Settings


def health_snapshot(settings: Settings) -> dict:
    return {
        "status": "ok",
        "environment": settings.app_env,
        "trading_enabled": settings.trading_enabled,
        "safe_mode_enabled": settings.safe_mode_enabled,
        "broker_symbol": settings.broker_symbol,
    }
