from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent.parent


class APISettings(BaseSettings):
    GAME_API_HOST: str
    AUTH_API_HOST: str

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="allow")


class RedisSettings(BaseSettings):
    REDIS_HOST: str

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="allow")


class Settings(BaseSettings):
    api: APISettings = APISettings()
    redis: RedisSettings = RedisSettings()


settings = Settings()
