import asyncio
import httpx
import random
import secrets
import uuid

from dataclasses import dataclass
from enum import IntEnum
from types import MappingProxyType

from server.data.factory import Packets, PacketSigner
from server.log import logger
from server.models.player import Facing, Position, Player, PlayerStatus, PlayerInput
from server.settings import player as pl, config
from server.systems.attack_system import AttackSystem
from server.systems.move_system import MoveSystem
from server.systems.world_system import WorldSystem
from server.world import loader
from server.world.headless import HeadlessWorld

import server.generated.v1.packet_pb2 as packet_pb2


@dataclass
class PendingInput:
    client_tick: int 
    player_input: PlayerInput


class MatchStatus(IntEnum):
    WAITING_FOR_INIT = 0
    ACCEPTING_PLAYERS = 1
    IN_GAME = 2


class Match:
    match_id: str
    _match_secret: str
    _players: dict[uuid.UUID, Player]
    expires: int
    status: MatchStatus
    max_players: int
    map_name: str

    def __init__(
        self,
        match_id: str,
        match_key: str,
        founder: tuple[uuid.UUID | str, str, str, int, int, tuple[str, int] | None],
        expires: int,
        world: HeadlessWorld,
        map_name: str,
        status: MatchStatus = MatchStatus.WAITING_FOR_INIT,
        max_players: int = 2
    ) -> None:
        self.match_id = match_id
        self._match_secret = match_key

        self.seed = secrets.randbits(64)
        random.seed(self.seed)

        self.world = world
        self.map_name = map_name

        uid, name, join_token, elo, games_played, client = founder
        if isinstance(uid, str):
            try:
                uid = uuid.UUID(uid)
            except Exception:
                logger.warning(f"Invalid player UUID {uid}")
                raise

        self._players = {uid: Player(
            player_id=uid,
            name=name,
            join_token=join_token,
            status=PlayerStatus.WAITING_FOR_MATCHMAKING_START,
            addr=client,
            position=Position(Facing.POS_X),
            elo=elo,
            games_played=games_played
        )}

        self.expires = expires
        self.status = status
        self.max_players = max_players

        self.move_system = MoveSystem()
        self.world_system = WorldSystem()
        self.attack_system = AttackSystem()

        self.input_buffers: dict[uuid.UUID, dict[int, PendingInput]] = {}

    @property
    def players(self):
        return MappingProxyType(self._players)

    @property
    def are_players_addressed(self):
        return all(player.addr is not None for player in self._players.values())

    def start_accepting(self):
        self.status = MatchStatus.ACCEPTING_PLAYERS

    def get_player(self, uuid: uuid.UUID) -> Player | None:
        return self._players.get(uuid)

    def _add_player(
        self,
        uuid: uuid.UUID,
        name: str,
        join_token: str | None,
        elo: int,
        games_played: int,
        client: tuple[str, int] | None
    ):
        player = Player(
            player_id=uuid,
            name=name,
            join_token=join_token,
            status=PlayerStatus.IN_MATCHMAKING_QUEUE,
            addr=client,
            # Assuming that _add_player is called on a non-empty queue only
            position=Position(Facing.POS_X),
            elo=elo,
            games_played=games_played
        )
        self._players[uuid] = player

    async def _remove_player(
        self,
        uuid: uuid.UUID,
        reason: str | None = None,
        reason_i18n: str | None = None,
        send_packet: bool = False,
        io_handler: 'server.data.all_handler.SocketIOHandler | None' = None
    ):
        player = self._players.pop(uuid, None)
        if not player:
            return

        logger.info("Kicked player %r from match %r. Reason: '%s'",
                    uuid, self.match_id, reason or "Not specified")
        
        if send_packet and io_handler and reason_i18n:
            packet = Packets.kicked_from_match(
                match_id=self.match_id,
                player_id=str(player.player_id),
                reason_i18n=reason_i18n
            )
            envelope = Packets.envelope(packet)

            await io_handler.enqueue_single_out(
                envelope,
                player.addr,
                needs_ack=True,
                ack_id=packet.msg_id
            )

        await self.check_victory(io_handler)

    def _is_accepting(self) -> bool:
        return (self.status == MatchStatus.ACCEPTING_PLAYERS) \
            and (len(self._players) < self.max_players)

    def get_player_by_token(self, join_token: str) -> Player | None:
        return next(
            (player for player in self._players.values() if player.join_token == join_token),
            None
        )

    def get_player_by_address(self, address: tuple[str, int]):
        return next(
            (player for player in self._players.values() if player.addr == address),
            None
        )

    def to_spawn(self, player: Player):
        spawn_idx = len(self._players)
        spawn = self.world.spawns.get(spawn_idx)
        if not spawn:
            logger.warning("Could not find a suitable spawnpoint %d for player %r",
                           spawn_idx, player.player_id)
            return

        player.position.x = spawn[0]
        player.position.y = spawn[1]
        logger.debug("Moved player %r to spawnpoint %r", player.player_id, spawn)

    def let_matchmake(self, player: Player):
        if player.player_id not in self._players:
            return  # a match can only modify its own players

        player.status = PlayerStatus.IN_MATCHMAKING_QUEUE
        player.join_token = None

    def queue_input(
        self,
        player: Player,
        client_tick: int,
        server_tick: int,
        payload: packet_pb2.PlayerMoveState
    ):
        self.input_buffers.setdefault(player.player_id, {})[client_tick] = PendingInput(
            client_tick=client_tick,
            player_input = PlayerInput(
                move_dir=payload.move_dir,
                duck=payload.duck,
                jump=payload.jump,
                dash=payload.dash,
                brake_dash=payload.brake_dash,
                reverse_dash=payload.reverse_dash,
                hang=payload.hang,
                parry=payload.parry,
                gravity_heavy=payload.gravity_heavy,
                gravity_light=payload.gravity_light,
                gravity_normal=payload.gravity_normal,

                punch=payload.punch,
                push=payload.push,
                stomp=payload.stomp,
            )
        )

    def simulate(self, tick: int):
        for player in self.players.values():
            buffer = self.input_buffers.get(player.player_id, {})

            if buffer:
                client_tick = min(buffer.keys())
                pending = buffer.pop(client_tick)
                final_input = pending.player_input
                player.last_input = final_input
                player.last_client_tick = client_tick
            else:
                if player.last_input:
                    final_input = PlayerInput(
                        move_dir=player.last_input.move_dir,
                        duck=player.last_input.duck,
                        dash=False,
                        jump=False
                    )
                else:
                    final_input = PlayerInput()

            other_players = [
                other
                for other in self.players.values()
                if other.player_id != player.player_id
            ]

            self.move_system.act_on(player, final_input)
            self.world_system.act_on(player, self.world)
            self.attack_system.act_on(player, final_input, other_players)

    async def check_victory(self, io_handler: 'server.data.all_handler.SocketIOHandler'):
        # add more conditions later
        if len(self._players) == 1:
            # one player just left lol
            # mark victory somehow later
            await self._remove_player(
                uuid=list(self._players.keys())[0],
                reason="Victory (by resignation)",
                reason_i18n="kick.victory-by-resignation",
                send_packet=True,
                io_handler=io_handler
            )

    def ensure_mana(self):
        for player in self._players.values():
            player.mana = min(pl.max_mana, player.mana + 1)


class MatchManager:
    def __init__(self) -> None:
        self._matches: dict[str, Match] = {}
        self._worlds = loader.load_maps(skip_malformed=False)

    def random_map(self):
        return random.choice(list(self._worlds.items()))

    @property
    def matches(self):
        return MappingProxyType(self._matches)

    def get_match(self, match_id: str):
        return self._matches.get(match_id)

    def register_match(self, match: Match):
        mid = match.match_id
        if mid in self._matches:
            return  # fail silently for idempotency
        self._matches[mid] = match
        match.start_accepting()

    def drop_match(self, match_id: str):
        self._matches.pop(match_id, None)  # other logic later

    def find_queuing_matches(self) -> list[Match]:
        return [match for match in self._matches.values() if match._is_accepting()]

    def find_player_by_id(self, player_id: uuid.UUID | str) -> Player | None:
        if isinstance(player_id, str):
            try:
                player_id = uuid.UUID(player_id)
            except Exception:
                return None

        return next(
            (p for p in [match.get_player(player_id) for match in self._matches.values()] if p),
            None
        )

    def find_player_by_addr(self, address: tuple[str, int]) -> Player | None:
        return next(
            (k for k in [match.get_player_by_address(address)
                         for match
                         in self._matches.values()]
                if k),
            None
        )

    def find_player_match(self, player_id: uuid.UUID | str) -> Match | None:
        if isinstance(player_id, str):
            try:
                player_id = uuid.UUID(player_id)
            except Exception:
                return None

        return next(
            (match for match in self._matches.values() if match.get_player(player_id) is not None),
            None
        )

    def add_player(
        self,
        match_id: str,
        player_id: uuid.UUID | str,
        name: str,
        join_token: str | None,
        elo: int,
        games_played: int,
        client: tuple[str, int] | None
    ) -> bool:
        if isinstance(player_id, str):
            try:
                player_id = uuid.UUID(player_id)
            except Exception:
                return False

        if match_id not in self._matches:
            return False

        match = self._matches[match_id]
        if not match._is_accepting():
            return False

        match._add_player(player_id, name, join_token, elo, games_played, client)
        return True

    async def quit_player(
        self,
        player_id: uuid.UUID | str,
        reason: str | None = None,
        reason_i18n: str | None = None,
        send_packet: bool = False,
        io_handler: 'server.data.all_handler.SocketIOHandler | None' = None
    ):
        if isinstance(player_id, str):
            try:
                player_id = uuid.UUID(player_id)
            except Exception:
                return False

        match = self.find_player_match(player_id)
        if match:
            await match._remove_player(player_id, reason, reason_i18n, send_packet, io_handler)
            if len(match.players) == 0:
                self._matches.pop(match.match_id, None)

    async def start_match(
        self,
        match_id: str,
        io_handler: 'server.data.all_handler.SocketIOHandler'
    ):
        if match_id not in self._matches:
            return

        match = self._matches[match_id]
        match.status = MatchStatus.IN_GAME
        for player in match._players.values():
            player.status = PlayerStatus.ENTERING_GAME
            await player.inform_game_start(io_handler)

    def simulate(self, tick: int, io_handler: 'server.data.all_handler.SocketIOHandler'):
        done = []
        for match_id, match in self._matches.items():
            if match.status != MatchStatus.IN_GAME:
                continue

            match.simulate(tick)

            for player in match._players.values():
                if player.health <= 0:
                    lost = Packets.lost_match()
                    asyncio.run(io_handler.enqueue_single_out(Packets.envelope(lost), player.addr, True, lost.msg_id))

                    winner = next((pl for pl in match._players.values() if pl.player_id != player.player_id), None)
                    if winner:
                        won = Packets.lost_match()
                        asyncio.run(io_handler.enqueue_single_out(Packets.envelope(won), player.addr, True, won.msg_id))

                        asyncio.run(_notify_api(winner=winner, loser=player))

                    done.append(match_id)

        for match_id in done:
            match = self._matches.pop(match_id, None)
            del match

    async def _notify_api(self, *, winner: Player, loser: Player):
        winner_id = str(winner.player_id)
        loser_id = str(loser.player_id)
        packet = Packets.envelope(PacketSigner.sign(Packets.game_over(winner_id, loser_id)))
        result = packet.SerializeToString()

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{config.server_url}/api/v1/matchmaking/end", json={"payload": result})
            logger.info("Notified API about ending match, response: %d", resp.status_code)

    async def share_reconcile(self, tick: int, io_handler: 'server.data.all_handler.SocketIOHandler'):
        for _, match in self._matches.items():
            if match.status != MatchStatus.IN_GAME:
                continue

            for player in match.players.values():
                response_data = Packets.reconcile(
                    server_tick=tick,
                    last_client_tick=player.last_client_tick,
                    players=list(match.players.values())
                )

                envelope = Packets.envelope(response_data)

                await io_handler.enqueue_single_out(envelope, player.addr)

    async def check_keepalive_players(
        self,
        server_tick: int,
        io_handler: 'server.data.all_handler.SocketIOHandler'
    ):
        to_kick = []

        for match in self._matches.values():
            for player in match.players.values():
                if not player.is_keepalive(server_tick):
                    to_kick.append(player)

        for player in to_kick:
            match = self.find_player_match(player.player_id)
            if not match:
                continue  # wtf?

            await self.quit_player(
                player.player_id,
                "No keepalive for 10+ seconds",
                "kick.no-keepalive",
                True,
                io_handler
            )

    def ensure_mana(self):
        for match in self._matches.values():
            match.ensure_mana()