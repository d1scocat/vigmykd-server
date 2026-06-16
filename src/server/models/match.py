import uuid

from enum import IntEnum
from types import MappingProxyType
from typing import Dict, Tuple

from server.log import logger
from server.models.player import Player, PlayerStatus


class MatchStatus(IntEnum):
    WAITING_FOR_INIT = 0
    ACCEPTING_PLAYERS = 1
    IN_GAME = 2


class Match:
    match_id: str
    _match_secret: str
    _players: Dict[uuid.UUID, Player]
    expires: int
    status: MatchStatus
    max_players: int

    def __init__(
        self,
        match_id: str,
        match_key: str,
        founder: Tuple[uuid.UUID | str, str, Tuple[str, int]],
        expires: int,
        status: MatchStatus = MatchStatus.WAITING_FOR_INIT,
        max_players: int = 2
    ) -> None:
        self.match_id = match_id
        self._match_secret = match_key

        uid, join_token, client = founder
        if isinstance(uid, str):
            try:
                uid = uuid.UUID(uid)
            except Exception:
                logger.warning(f"Invalid player UUID {uid}")
                raise

        self._players = {uid: Player(
            uuid=uid,
            join_token=join_token,
            status=PlayerStatus.WAITING_FOR_MATCHMAKING_START,
            addr=client
        )}

        self.expires = expires
        self.status = status
        self.max_players = max_players

    @property
    def players(self):
        return MappingProxyType(self._players)

    def start_accepting(self):
        self.status = MatchStatus.ACCEPTING_PLAYERS

    def get_player(self, uuid: uuid.UUID) -> Player | None:
        return self._players.get(uuid)

    def _add_player(self, uuid: uuid.UUID, join_token: str | None, client: Tuple[str, int]):
        player = Player(uuid, join_token, PlayerStatus.IN_MATCHMAKING_QUEUE, client)
        self._players[uuid] = player

    def _is_accepting(self) -> bool:
        return (self.status == MatchStatus.ACCEPTING_PLAYERS) \
            and (len(self._players) < self.max_players)

    def get_player_by_token(self, join_token: str) -> Player | None:
        return next(
            (player for player in self._players.values() if player.join_token == join_token),
            None
        )

    def let_matchmake(self, player: Player):
        if player.uuid not in self._players:
            return  # a match can only modify its own players

        player.status = PlayerStatus.IN_MATCHMAKING_QUEUE
        player.join_token = None


class MatchManager:
    def __init__(self) -> None:
        self._matches: Dict[str, Match] = {}

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
            except:
                return None

        return next(
            (k for k in [match.get_player(player_id) for match in self._matches.values()] if k),
            None
        )

    def find_player_match(self, player_id: uuid.UUID | str) -> Match | None:
        if isinstance(player_id, str):
            try:
                player_id = uuid.UUID(player_id)
            except:
                return None

        return next(
            (match for match in self._matches.values() if match.get_player(player_id) is not None),
            None
        )

    def add_player(
        self,
        match_id: str,
        player_id: uuid.UUID | str,
        join_token: str | None,
        client: Tuple[str, int]
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

        match._add_player(player_id, join_token, client)
        return True

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
            await player.inform_game_start(match, io_handler)
