from typing import Awaitable, Callable, Dict, TypeAlias

from server.generated.proto.v1 import packet_pb2 as packet_pb2

from server.context import ServerContext
from server.data.factory import Packets
from server.models.match import Match
from server.log import logger

from google.protobuf.message import Message


UDPAddress: TypeAlias = tuple[str, int]
EnqueueOut: TypeAlias = Callable[[bytes, UDPAddress], Awaitable[None]]
DataHandler: TypeAlias = Callable[
    [Message, UDPAddress, ServerContext, EnqueueOut, int],
    Awaitable[None]
]

class ActionFailed(Exception):
    pass


class Handlers:
    @staticmethod
    async def cts_player_action(
        payload: packet_pb2.PlayerMove,
        client: UDPAddress,
        ctx: ServerContext,
        enqueue_out: EnqueueOut,
        msg_id: int,
    ):
        ...

    @staticmethod
    async def cts_matchmaking_enter(
        payload: packet_pb2.MatchmakingEnter,
        client: UDPAddress,
        ctx: ServerContext,
        enqueue_out: EnqueueOut,
        msg_id: int,
    ):
        # - Received Packet.ClientToServerPacket.MatchmakingEnter
        #   Params: str match_id, str join_token
        #   All of this ^^^ is inside Packet::client_to_server::matchmaking_enter
        #   Find the match by match_id and find the player there
        #   Check that now <= expires
        #   Ensure that this player is not already connected to any match
        #   Set "status" to "in-queue" (maybe enum?)
        #   Drop the join_token (set to None) so that it is one-use
        #   Return Ack message
        #   After making sure that enqueuing one player works, make it so that RegisterMatch
        #    responses can return an existing match, if the two players are allowed to
        #    battle each other
        match_id = payload.match_id
        join_token = payload.join_token

        ok = True

        try:  # exception driven flow management
            match = ctx.match_manager.get_match(match_id)
            if not match:
                raise ActionFailed

            player = match.get_player_by_token(join_token)
            if not player:
                raise ActionFailed

            match.let_matchmake(player)
        except ActionFailed:
            ok = False
        finally:
            packet = Packets.envelope(Packets.ack(msg_id, ok=ok))
            await enqueue_out(packet, client)
            return

    @staticmethod
    async def cts_matchmaking_quit(
        payload: packet_pb2.MatchmakingQuit,
        client: UDPAddress,
        ctx: ServerContext,
        enqueue_out: EnqueueOut,
        msg_id: int,
    ):
        ...

    @staticmethod
    async def icp_register_match(
        payload: packet_pb2.InternalCommunicationPacket.RegisterMatch,
        client: UDPAddress,
        ctx: ServerContext,
        enqueue_out: EnqueueOut,
        msg_id: int,
    ):
        match_id: str = payload.match_id
        match_key: str = payload.match_key
        players: list[str] = list(payload.players)
        join_token: str = payload.join_token  # for players[0]
        expires: int = payload.expires

        ok = True

        try:
            match = Match(match_id, match_key, (players[0], join_token), expires, "waiting")
            ctx.match_manager.register_match(match)
        except Exception:
            logger.warning("Could not create match", exc_info=True)
            ok = False
        finally:
            packet = Packets.envelope(Packets.ack(msg_id, ok=ok))
            await enqueue_out(packet, client)
            return


handlers: Dict[str, Dict[str, DataHandler]] = {
    "cts": {
        "player_action": Handlers.cts_player_action,
        "matchmaking_enter": Handlers.cts_matchmaking_enter,
        "matchmaking_quit": Handlers.cts_matchmaking_quit,
    },

    "icp": {
        "register_match": Handlers.icp_register_match,
    }
}
