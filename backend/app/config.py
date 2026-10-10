from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./sehat_grid.db"
    cors_origins: str = "http://localhost:3000"
    app_timezone: str = "Asia/Karachi"
    seed_on_start: bool = True
    enable_demo_reset: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
