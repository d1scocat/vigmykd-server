import asyncio

from server.settings import config
from server.log import logger
from server.models.match import MatchManager
from server.tasks import Task


class MatchStarter(Task):
    def __init__(
        self,
        match_manager: MatchManager
    ):
        self.match_manager = match_manager

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
        ...