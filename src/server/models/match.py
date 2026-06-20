import uuid
import random
import secrets

from collections import deque
from enum import IntEnum
from types import MappingProxyType

from server.data.factory import Packets
from server.log import logger
from server.models.player import Facing, Position, Player, PlayerStatus, PlayerInput
from server.systems.move_system import MoveSystem
from server.systems.world_system import WorldSystem
from server.world import loader
from server.world.headless import HeadlessWorld

import server.generated.v1.packet_pb2 as packet_pb2


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
        founder: tuple[uuid.UUID | str, str, str, tuple[str, int] | None],
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

        uid, name, join_token, client = founder
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
            position=Position(Facing.POS_X)
        )}

        self.expires = expires
        self.status = status
        self.max_players = max_players

        self.move_system = MoveSystem()
        self.world_system = WorldSystem()

        self.input_buffers: dict[uuid.UUID, dict[int, PlayerInput]] = {}

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

    def _add_player(self, uuid: uuid.UUID, name: str, join_token: str | None, client: tuple[str, int] | None):
        player = Player(
            player_id=uuid,
            name=name,
            join_token=join_token,
            status=PlayerStatus.IN_MATCHMAKING_QUEUE,
            addr=client,
            # Assuming that _add_player is called on a non-empty queue only
            position=Position(Facing.POS_X)
        )
        self._players[uuid] = player

    def _remove_player(self, uuid: uuid.UUID):
        self._players.pop(uuid, None)

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
        """Queues input for the upcoming server tick."""
        if client_tick <= player.last_client_tick:
            return

        player_input = PlayerInput(
            move_dir=payload.move_dir,
            duck=payload.duck,
            jump=payload.jump,
            dash=payload.dash
        )

        buffer = self.input_buffers.setdefault(player.player_id, {})
        buffer[client_tick] = player_input

    def simulate(self, tick: int):
        for player in self.players.values():
            buffer = self.input_buffers.get(player.player_id, {})

            next_expected_tick = player.last_client_tick + 1
            final_input = None

            if next_expected_tick in buffer:
                final_input = buffer.pop(next_expected_tick)
                player.last_client_tick = next_expected_tick
                player.last_input = final_input
                logger.info(f"[SERVER] {tick=}, {player.player_id=} | Processing input for client_tick {next_expected_tick}")

            elif player.last_client_tick == 0 and buffer:
                oldest_tick = min(buffer.keys())
                final_input = buffer.pop(oldest_tick)
                player.last_client_tick = oldest_tick
                player.last_input = final_input
                logger.info(f"[SERVER] {tick=}, {player.player_id=} | Bootstrapping seq with client_tick {oldest_tick}")

            else:
                final_input = player.last_input or PlayerInput()
                logger.info(f"[SERVER] {tick=}, {player.player_id=} | No input for {next_expected_tick}, using last_input")

            self.move_system.act_on(player, final_input)
            self.world_system.act_on(player, self.world)

            logger.info(f"[SERVER] {tick=}, {player.player_id=} | Finished calculating position: {player.position!r}")

    def kick_player(self, player: Player, reason: str | None = None):
        if player.player_id not in self._players:
            return
        
        self._players.pop(player.player_id, None)
        logger.info("Kicked player %r from match %r. Reason: '%s'",
                    player.player_id, self.match_id, reason or "Not specified")
        self.check_victory()

    def check_victory(self):
        # add more conditions later
        if len(self._players) == 1:
            # one player just left loll
            # mark victory somehow later
            self.kick_player(list(self._players.values())[0])


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

        match._add_player(player_id, name, join_token, client)
        return True

    def quit_player(self, player_id: uuid.UUID | str):
        if isinstance(player_id, str):
            try:
                player_id = uuid.UUID(player_id)
            except Exception:
                return False

        match = self.find_player_match(player_id)
        if match:
            match._remove_player(player_id)
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

    async def simulate_and_share(self, tick: int, io_handler: 'server.data.all_handler.SocketIOHandler'):
        for _, match in self._matches.items():
            if match.status != MatchStatus.IN_GAME:
                continue

            match.simulate(tick)

            for player in match.players.values():
                response_data = Packets.reconcile(
                    server_tick=tick,
                    last_client_tick=player.last_client_tick,
                    players=list(match.players.values())
                )

                envelope = Packets.envelope(response_data)

                await io_handler.enqueue_single_out(envelope, player.addr)

    async def check_keepalive_players(self, server_tick: int):
        to_kick: dict[Match, list[Player]] = {}

        for match in self._matches.values():
            for player in match.players.values():
                if player.is_keepalive(server_tick):
                    continue

                to_kick.setdefault(match, []).append(player)
        
        for match, players in to_kick.items():
            for player in players:
                match.kick_player(player, "Keepalive packets missing for 10+ seconds")
