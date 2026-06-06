from datetime import timezone
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    WARNING_DAYS_NEAR_EXPIRY: int = 30


settings = Settings()


def utc_now():
    from datetime import datetime
    return datetime.now(timezone.utc).replace(tzinfo=None)
