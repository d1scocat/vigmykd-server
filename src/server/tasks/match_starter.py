import asyncio
import time

from server.data.all_handler import SocketIOHandler
from server.settings import config
from server.log import logger
from server.models.match import MatchManager, MatchStatus
from server.tasks import Task


class MatchStarter(Task):
    def __init__(
        self,
        match_manager: MatchManager,
        io_handler: SocketIOHandler,
    ):
        self.match_manager = match_manager
        self.io_handler = io_handler

        self._shutdown_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self):
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self.check_matches_loop())

    async def stop(self):
        if self._task is not None and not self._task.done():
            self._shutdown_event.set()
            await self._task

    async def check_matches_loop(self):
        while not self._shutdown_event.is_set():
            try:
                await self.do_once()
            except Exception:
                logger.warning("⚠️ MatchStarter failed once", exc_info=True)

            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=config.match_task_interval
                )
                break
            except asyncio.TimeoutError:
                continue

    async def do_once(self):
        # todo: debug and check whether things actually happen
        for match_id, match in self.match_manager.matches.items():
            if time.time() >= match.expires:
                self.match_manager.drop_match(match_id)
                continue

            if match.status == MatchStatus.ACCEPTING_PLAYERS:
                if len(match.players) >= match.max_players:
                    await self.match_manager.start_match(match_id, self.io_handler)
