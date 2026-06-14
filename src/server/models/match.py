import uuid

from typing import Dict, Tuple

from server.log import logger
from server.models.player import Player, PlayerStatus


class Match:
    match_id: str
    _match_secret: str
    _players: Dict[uuid.UUID, Player]
    expires: int
    status: str

    def __init__(
        self,
        match_id: str,
        match_key: str,
        founder: Tuple[uuid.UUID | str, str],
        expires: int,
        status: str
    ) -> None:
        self.match_id = match_id
        self._match_secret = match_key

        uid, join_token = founder
        if isinstance(uid, str):
            try:
                uid = uuid.UUID(uid)
            except Exception:
                logger.warning(f"Invalid player UUID {uid}")
                raise

        self._players = {uid: Player(
            uuid=uid, join_token=join_token, status=PlayerStatus.WAITING_FOR_MATCHMAKING_START
        )}

        self.expires = expires
        self.status = status

    def get_player(self, uuid: uuid.UUID) -> Player | None:
        return self._players.get(uuid)

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

    def get_match(self, match_id: str):
        return self._matches.get(match_id)

    def register_match(self, match: Match):
        mid = match.match_id
        if mid in self._matches:
            return  # fail silently for idempotency
        self._matches[mid] = match

    def drop_match(self, match_id: str):
        self._matches.pop(match_id, None)
        # other logic later

    def start_match(self, match_id: str):
        if match_id not in self._matches:
            return

        match = self._matches[match_id]
        match.status = "started"
        for player in match._players.values():
            player.status = PlayerStatus.ENTERING_GAME
