from typing import Awaitable, Callable, Dict, TypeAlias

import server.generated.v1.packet_pb2 as packet_pb2

from server.context import ServerContext
from server.data.factory import Packets
from server.models.match import Match, MatchStatus
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
            packet = Packets.envelope(Packets.matchmaking_enter_response(match_id))
            await enqueue_out(packet, client)
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
        player_id: str = list(payload.players)[0]
        join_token: str = payload.join_token  # for players[0]
        expires: int = payload.expires

        ok = True
        joined_match_id = match_id

        try:
            # Before creating a match, check whether there are any matches queuing
            joined_existing = False
            
            # Or maybe you're already in a match??
            if ctx.match_manager.find_player_by_id(player_id):
                joined_match_id = ctx.match_manager.find_player_match(player_id)
                joined_existing = True

            if not joined_existing:
                for match in ctx.match_manager.find_queuing_matches():
                    if ctx.match_manager.add_player(match.match_id, player_id, join_token):
                        # to send a RegisterMatchResponse with the correct ID
                        joined_match_id = match.match_id
                        joined_existing = True
                        break

            if not joined_existing:
                match = Match(match_id, match_key, (player_id, join_token), expires)
                ctx.match_manager.register_match(match)
        except Exception:
            logger.warning("Could not create match", exc_info=True)
            ok = False
        finally:
            packet = Packets.envelope(Packets.ack(msg_id, ok=ok))
            await enqueue_out(packet, client)

            if ok:
                await enqueue_out(Packets.envelope(Packets.register_match_response(
                    joined_match_id=joined_match_id,
                    old_match_id=match_id
                )), client)


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
