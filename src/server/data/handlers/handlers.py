from typing import Awaitable, Callable, Dict, TypeAlias

import server.generated.v1.packet_pb2 as packet_pb2

from server.context import ServerContext
from server.data.factory import Packets
from server.models.match import Match
from server.log import logger

from google.protobuf.message import Message


UDPAddress: TypeAlias = tuple[str, int]
DataHandler: TypeAlias = Callable[
    [Message, UDPAddress, ServerContext, 'server.data.all_handler.SocketIOHandler', int],
    Awaitable[None]
]

class ActionFailed(Exception):
    pass


class CTSHandlers:
    @staticmethod
    async def cts_player_moved(
        payload: packet_pb2.PlayerMoveState,
        client: UDPAddress,
        ctx: ServerContext,
        io_handler: 'server.data.all_handler.SocketIOHandler',
        msg_id: int,
    ):
        player = ctx.match_manager.find_player_by_addr(client)
        if not player:
            return

        match = ctx.match_manager.find_player_match(player.player_id)
        if not match:
            return

        client_tick: int = payload.client_tick
        server_tick = ctx.tick

        match.queue_input(player, client_tick, server_tick, payload)
        player.keepalive(server_tick)

    @staticmethod
    async def cts_matchmaking_enter(
        payload: packet_pb2.MatchmakingEnter,
        client: UDPAddress,
        ctx: ServerContext,
        io_handler: 'server.data.all_handler.SocketIOHandler',
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

            logger.info(f"Player {player.player_id!r} claimed address {client!r}")
            player.claim_address(client)
            player.keepalive(ctx.tick)

            match.to_spawn(player)
            match.let_matchmake(player)

            packet = Packets.envelope(Packets.matchmaking_enter_response(match_id))
            await io_handler.enqueue_single_out(packet, client)
        except ActionFailed:
            ok = False
        finally:
            packet = Packets.envelope(Packets.ack(msg_id, ok=ok))
            await io_handler.enqueue_single_out(packet, client)
            return

    @staticmethod
    async def cts_matchmaking_quit(
        payload: packet_pb2.MatchmakingQuit,
        client: UDPAddress,
        ctx: ServerContext,
        io_handler: 'server.data.all_handler.SocketIOHandler',
        msg_id: int,
    ):
        ok = True

        try:
            player = ctx.match_manager.find_player_by_addr(client)
            if not player:
                raise ActionFailed

            match = ctx.match_manager.find_player_match(player.player_id)
            if not match:
                raise ActionFailed

            ctx.match_manager.quit_player(player.player_id)  # can fail silently for idempotency

            packet = Packets.envelope(Packets.matchmaking_enter_response(match.match_id))
            await io_handler.enqueue_single_out(packet, client)
        except ActionFailed:
            ok = False
        finally:
            packet = Packets.envelope(Packets.ack(msg_id, ok=ok))
            await io_handler.enqueue_single_out(packet, client)
            return

    @staticmethod
    async def cts_request_match_info(
        payload: packet_pb2.RequestMatchInfo,
        client: UDPAddress,
        ctx: ServerContext,
        io_handler: 'server.data.all_handler.SocketIOHandler',
        msg_id: int,
    ):
        player = ctx.match_manager.find_player_by_addr(client)
        if not player:
            return

        match = ctx.match_manager.find_player_match(player.player_id)
        if not match:
            return

        packet = Packets.envelope(Packets.request_match_info_response(
            list(match.players.values()),
            str(player.player_id),
            match.seed,
            ctx.tick,
            match.map_name
        ))

        await io_handler.enqueue_single_out(packet, client)


class ICPHandlers:
    @staticmethod
    async def icp_register_match(
        payload: packet_pb2.InternalCommunicationPacket.RegisterMatch,
        client: UDPAddress,
        ctx: ServerContext,
        io_handler: 'server.data.all_handler.SocketIOHandler',
        msg_id: int,
    ):
        match_id: str = payload.match_id
        match_key: str = payload.match_key

        player: packet_pb2.InternalCommunicationPacket.PlayerBrief = list(payload.players)[0]
        player_id = player.id
        player_name = player.name

        join_token: str = payload.join_token  # for players[0]
        expires: int = payload.expires

        ok = True
        joined_match_id = match_id

        try:
            # Before creating a match, check whether there are any matches queuing
            joined_existing = False
            
            # Or maybe you're already in a match??
            joined_match = ctx.match_manager.find_player_match(player_id)
            if joined_match is not None:
                joined_match_id = joined_match.match_id
                joined_existing = True

            if not joined_existing:
                for match in ctx.match_manager.find_queuing_matches():
                    if ctx.match_manager.add_player(
                        match.match_id,
                        player_id,
                        player_name,
                        join_token,
                        None
                    ):
                        # to send a RegisterMatchResponse with the correct ID
                        joined_match_id = match.match_id
                        joined_existing = True
                        break

            if not joined_existing:
                name, world = ctx.match_manager.random_map()
                match = Match(
                    match_id,
                    match_key,
                    (player_id, player_name, join_token, None),
                    expires,
                    world,
                    name
                )
                ctx.match_manager.register_match(match)
        except Exception:
            logger.warning("Could not create match", exc_info=True)
            ok = False
        finally:
            packet = Packets.envelope(Packets.ack(msg_id, ok=ok))
            await io_handler.enqueue_single_out(packet, client)

            if ok:
                await io_handler.enqueue_single_out(
                    Packets.envelope(
                        Packets.register_match_response(
                            joined_match_id=joined_match_id,
                            old_match_id=match_id
                        )
                    ),
                    client
                )


handlers: Dict[str, Dict[str, DataHandler]] = {
    "cts": {
        "player_move_state": CTSHandlers.cts_player_moved,
        "matchmaking_enter": CTSHandlers.cts_matchmaking_enter,
        "matchmaking_quit": CTSHandlers.cts_matchmaking_quit,
        "request_match_info": CTSHandlers.cts_request_match_info,
    },

    "icp": {
        "register_match": ICPHandlers.icp_register_match,
    }
}
