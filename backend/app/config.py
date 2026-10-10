from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./sehat_grid.db"
    cors_origins: str = "http://localhost:3000"
    app_timezone: str = "Asia/Karachi"
    seed_on_start: bool = True
    enable_demo_reset: bool = False
    demo_mode: bool = True
    jwt_secret: str = ""
    demo_password: str = ""
    capacity_freshness_minutes: int = 1440
    referral_hold_minutes: int = 30
    cancellation_cutoff_local: str = "09:00"
    embedding_model_path: str = "models/all-MiniLM-L6-v2"
    match_review_threshold: float = 0.69
    optimizer_time_limit_seconds: int = 10
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
