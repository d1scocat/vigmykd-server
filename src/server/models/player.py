from server.data.factory import Packets

from dataclasses import dataclass
from enum import IntEnum
from uuid import UUID
from typing import Tuple

from server.log import logger


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
    vel_dy: float = 0


@dataclass
class Player:
    player_id: UUID
    name: str
    join_token: str | None
    status: PlayerStatus
    addr: Tuple[str, int] | None
    position: Position

    def claim_address(self, address: Tuple[str, int]):
        self.addr = address

    async def inform_game_start(
        self,
        match: 'server.models.match.Match',
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
