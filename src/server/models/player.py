from server.data.factory import Packets

from dataclasses import dataclass, field
from enum import IntEnum
from uuid import UUID
from typing import Tuple

from server.geometry import Rect
from server.log import logger
from server.settings import player


class PlayerStatus(IntEnum):
    NOT_IN_GAME_OR_QUEUE = -1
    WAITING_FOR_MATCHMAKING_START = 0
    IN_MATCHMAKING_QUEUE = 1
    ENTERING_GAME = 2
    IN_GAME = 3


class Facing(IntEnum):
    NEG_X = 0
    POS_X = 1


@dataclass
class Position:
    facing: Facing
    x: float = 0
    y: float = 0
    vel_x: float = 0
    vel_y: float = 0
    is_grounded: bool = False
    ducking: bool = False
    dashing: bool = False


@dataclass
class PlayerInput:
    move_dir: int = 0
    duck: bool = False
    jump: bool = False
    dash: bool = False
    brake_dash: bool = False
    reverse_dash: bool = False
    hang: bool = False
    parry: bool = False
    gravity_heavy: bool = False
    gravity_light: bool = False
    gravity_normal: bool = False

    punch: bool = False
    push: bool = False
    stomp: bool = False


@dataclass
class PlayerPhysics:
    dash_timer: int = 0
    coyote_timer: int = 0
    jump_buffer_timer: int = 0
    last_jump_pressed: bool = False
    last_dash_pressed: bool = False
    hang_timer: int = 0
    invulnerable_timer: int = 0
    heavy_gravity_timer: int = 0
    light_gravity_timer: int = 0
    stun_timer: int = 0


@dataclass
class PlayerCooldowns:
    brake_dash: int = 0
    reverse_dash: int = 0
    hang: int = 0
    parry: int = 0

    heavy: int = 0
    light: int = 0
    normal: int = 0

    push: int = 0
    stomp: int = 0
    punch: int = 0

    def reduce(self):
        self.brake_dash = max(0, self.brake_dash - 1)
        self.reverse_dash = max(0, self.reverse_dash - 1)
        self.hang = max(0, self.hang - 1)
        self.parry = max(0, self.parry - 1)
        self.heavy = max(0, self.heavy - 1)
        self.light = max(0, self.light - 1)
        self.normal = max(0, self.normal - 1)

        self.push = max(0, self.push - 1)
        self.stomp = max(0, self.stomp - 1)
        self.punch = max(0, self.punch - 1)

    @property
    def can_brake_dash(self):
        return self.brake_dash == 0

    def cooldown_brake_dash(self):
        self.brake_dash = player.brake_dash_cooldown_ticks

    @property
    def can_reverse_dash(self):
        return self.reverse_dash == 0

    def cooldown_reverse_dash(self):
        self.reverse_dash = player.reverse_dash_cooldown_ticks

    @property
    def can_hang(self):
        return self.hang == 0

    def cooldown_hang(self):
        self.hang = player.hang_cooldown_ticks

    @property
    def can_parry(self):
        return self.parry == 0

    def cooldown_parry(self):
        self.parry = player.parry_cooldown_ticks

    @property
    def can_heavy(self):
        return self.heavy == 0

    def cooldown_heavy(self):
        self.heavy = player.heavy_cooldown_ticks

    @property
    def can_light(self):
        return self.light == 0

    def cooldown_light(self):
        self.light = player.light_cooldown_ticks

    @property
    def can_normal(self):
        return self.normal == 0

    def cooldown_normal(self):
        self.normal = player.normal_cooldown_ticks

    @property
    def can_push(self):
        return self.push == 0

    def cooldown_push(self):
        self.push = player.push_cooldown_ticks

    @property
    def can_stomp(self):
        return self.stomp == 0

    def cooldown_stomp(self):
        self.stomp = player.stomp_cooldown_ticks

    @property
    def can_punch(self):
        return self.punch == 0

    def cooldown_punch(self):
        self.punch = player.punch_cooldown_ticks


@dataclass
class Combo:
    hits: int = 0
    timer: int = 0
    broken: bool = True


@dataclass
class Player:
    player_id: UUID
    name: str
    join_token: str | None
    status: PlayerStatus
    addr: Tuple[str, int] | None
    position: Position
    last_input: PlayerInput = field(default_factory=PlayerInput)

    physics: PlayerPhysics = field(default_factory=PlayerPhysics)
    cooldowns: PlayerCooldowns = field(default_factory=PlayerCooldowns)
    combo: Combo = field(default_factory=Combo)

    last_client_tick: int = 0
    keepalive_tick: int = 2**31
    missing_input_ticks: int = 0

    mana: int = player.max_mana
    health: float = player.max_health

    def break_combo(self):
        self.combo.hits = 0
        self.combo.timer = 0
        self.combo.broken = True

    @property
    def rect(self) -> Rect:
        height = player.hitbox_height_ducking if self.position.ducking else player.hitbox_height

        return Rect(
            self.position.x,
            self.position.y,
            player.hitbox_width,
            height
        )

    def claim_address(self, address: Tuple[str, int]):
        self.addr = address

    async def inform_game_start(
        self,
        io_handler: 'server.data.all_handler.SocketIOHandler'
    ):
        if not self.addr:
            logger.warning("Cannot inform player %r of start because they have no address",
                           self.player_id)
            return

        packet = Packets.inform_match_start()
        msg_id = packet.msg_id
        data = Packets.envelope(packet)

        await io_handler.enqueue_single_out(data, self.addr, True, msg_id)

    def keepalive(self, server_tick: int):
        self.keepalive_tick = server_tick

    def is_keepalive(self, current_server_tick: int):
        return current_server_tick - self.keepalive_tick <= player.keepalive_ticks
