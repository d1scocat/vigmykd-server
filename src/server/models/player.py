from dataclasses import dataclass
from enum import IntEnum
from uuid import UUID
from typing import Tuple


class PlayerStatus(IntEnum):
    NOT_IN_GAME_OR_QUEUE = -1
    WAITING_FOR_MATCHMAKING_START = 0
    IN_MATCHMAKING_QUEUE = 1
    ENTERING_GAME = 2
    IN_GAME = 3


@dataclass
class Player:
    uuid: UUID
    join_token: str | None
    status: PlayerStatus
    addr: Tuple[str, int]
