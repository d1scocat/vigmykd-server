from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    port: int = Field(...)
    queue_size: int = Field(...)
    signature: str = Field(...)
    match_task_interval: float = Field(...)

    max_ack_attempts: int = Field(...)
    reack_interval: float = Field(...)
    packet_size: int = Field(...)
    keep_processed: int = Field(...)

    model_config = SettingsConfigDict(env_prefix="vigmykd_")
