from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Environmental Monitoring API"
    app_version: str = "0.1.0"
    stream_interval_seconds: float = 5.0
    wildfire_event_probability: float = 0.05


settings = Settings()
