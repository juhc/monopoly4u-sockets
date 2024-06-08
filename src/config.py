from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent.parent


class APISettings(BaseSettings):
    GAME_API_HOST: str
    GAME_API_PORT: int

    AUTH_API_HOST: str
    AUTH_API_PORT: int

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="allow")

    @property
    def game_api_url(self):
        return f"http://{self.GAME_API_HOST}:{self.GAME_API_PORT}"
    
    @property
    def auth_api_url(self):
        return f"http://{self.AUTH_API_HOST}:{self.AUTH_API_PORT}"


class RedisSettings(BaseSettings):
    REDIS_HOST: str

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="allow")


class Settings(BaseSettings):
    api: APISettings = APISettings()
    redis: RedisSettings = RedisSettings()


settings = Settings()
