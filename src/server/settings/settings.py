from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class EnvSettings(BaseSettings):
    port: int = Field(...)
    queue_size: int = Field(...)
    signature: str = Field(...)
    match_task_interval: float = Field(...)

    max_ack_attempts: int = Field(...)
    reack_interval: float = Field(...)
    packet_size: int = Field(...)
    keep_processed: int = Field(...)

    tps: int = Field(...)

    model_config = SettingsConfigDict(env_prefix="vigmykd_")


class PhysicsSettings(BaseSettings):
    move_speed: float = Field(...)
    gravity_rise: float = Field(...)
    gravity_fall: float = Field(...)
    terminal_velocity: float = Field(...)
    jump_force: float = Field(...)
    dash_speed: float = Field(...)
    dash_duration_ticks: int = Field(...)
    accel_x: float = Field(...)
    decel_x: float = Field(...)
    dash_plunge_speed: float = Field(...)
    max_jump_force: float = Field(...)
    air_move_speed: float = Field(...)
    air_accel_x: float = Field(...)
    air_decel_x: float = Field(...)
    fast_fall_multiplier: float = Field(...)
    air_drag: float = Field(...)

    model_config = SettingsConfigDict(env_prefix="movement_")
