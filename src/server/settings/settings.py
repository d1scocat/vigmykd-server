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
    expire_processed_ticks: int = Field(...)

    tps: int = Field(...)
    reconcile_interval: int = Field(...)
    max_worker_steps: int = Field(...)

    max_elo_diff: int = Field(...)
    server_url: str = Field(...)

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
    ground_tolerance: int = Field(...)
    coyote: int = Field(...)
    jump_buffer_ticks: int = Field(...)
    step_height: float = Field(...)

    model_config = SettingsConfigDict(env_prefix="movement_")


class PlayerSettings(BaseSettings):
    hitbox_width: float = Field(...)
    hitbox_height: float = Field(...)
    hitbox_height_ducking: float = Field(...)
    keepalive_ticks: int = Field(...)

    max_mana: int = Field(...)
    max_health: float = Field(...)

    dash_mana_cost: int = Field(...)

    brake_dash_cooldown_ticks: int = Field(...)

    reverse_dash_mana_cost: int = Field(...)
    reverse_dash_cooldown_ticks: int = Field(...)

    hang_mana_cost: int = Field(...)
    hang_ticks: int = Field(...)
    hang_cooldown_ticks: int = Field(...)

    parry_ticks: int = Field(...)
    parry_mana_cost: int = Field(...)
    parry_cooldown_ticks: int = Field(...)

    heavy_ticks: int = Field(...)
    heavy_scalar: float = Field(...)
    heavy_mana_cost: int = Field(...)
    heavy_cooldown_ticks: int = Field(...)

    light_ticks: int = Field(...)
    light_scalar: float = Field(...)
    light_mana_cost: int = Field(...)
    light_cooldown_ticks: int = Field(...)

    normal_mana_cost: int = Field(...)
    normal_cooldown_ticks: int = Field(...)

    push_cooldown_ticks: int = Field(...)
    push_range: float = Field(...)
    push_vertical_tolerance: float = Field(...)
    push_force_x: float = Field(...)
    push_force_y: float = Field(...)
    push_iframes: int = Field(...)

    stomp_range: float = Field(...)
    stomp_iframes: int = Field(...)
    stomp_cooldown_ticks: int = Field(...)
    stomp_knockback_x: float = Field(...)
    stomp_knockback_y: float = Field(...)
    stomp_damage: float = Field(...)

    punch_damage: float = Field(...)
    punch_iframes: int = Field(...)
    punches_to_knockdown: int = Field(...)
    punch_combo_window_ticks: int = Field(...)
    punch_cooldown_ticks: int = Field(...)
    punch_stun_ticks: int = Field(...)
    punch_knockdown_kb_x: float = Field(...)
    punch_knockdown_kb_y: float = Field(...)
    punch_range: float = Field(...)
    punch_recoil_x: float = Field(...)
    punch_recoil_y: float = Field(...)

    model_config = SettingsConfigDict(env_prefix="player_")
