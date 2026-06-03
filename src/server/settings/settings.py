from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    port: int = Field(...)

    model_config = SettingsConfigDict(env_prefix="vigmykd_")
