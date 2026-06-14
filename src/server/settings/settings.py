from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    port: int = Field(...)
    queue_size: int = Field(...)
    signature: str = Field(...q)

    model_config = SettingsConfigDict(env_prefix="vigmykd_")
