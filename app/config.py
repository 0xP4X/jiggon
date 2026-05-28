from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"

    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""

    broker_app_id: int = 1089
    broker_api_token: str = ""
    broker_endpoint: str = ""
    broker_symbol: str = "R_75"
    broker_currency: str = "USD"

    database_url: str = "postgresql+asyncpg://jiggon:jiggon@localhost:5432/jiggon"

    trading_enabled: bool = False
    safe_mode_enabled: bool = True
    confidence_threshold: int = Field(default=80, ge=0, le=100)
    max_risk_per_trade: float = Field(default=0.01, gt=0, le=1)
    max_daily_drawdown: float = Field(default=0.05, gt=0, le=1)
    safe_mode_cooldown_minutes: int = Field(default=45, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig")


@lru_cache
def get_settings() -> Settings:
    return Settings()
