import time

from typing import Awaitable, Callable

from server.context import ServerContext
from server.data.all_handler import SocketIOHandler
from server.log import logger
from server.tasks.match_starter import MatchStarter


class TaskManager:
    def __init__(
        self,
        ctx: ServerContext,
        io_handler: SocketIOHandler
    ):
        self._tasks = [
            MatchStarter(
                match_manager=ctx.match_manager,
                io_handler=io_handler
            )
        ]

    async def start(self):
        start = time.perf_counter()
        amount = len(self._tasks)

        for idx, task in enumerate(self._tasks):
            task_name = task.__class__.__name__
            try:
                logger.info(f"⌚ {idx}/{amount}. Task {task_name} "
                            f"started in {await self.gettimeof(task.start):3f}ms")
            except Exception:
                logger.warning(f"⚠️ Failed to start task {task_name}")
                raise

        logger.info(f"✅ Started all {amount} tasks in {time.perf_counter() - start:3f}ms")

    async def stop(self):
        start = time.perf_counter()
        amount = len(self._tasks)

        for idx, task in enumerate(self._tasks):
            task_name = task.__class__.__name__
            try:
                logger.info(f"⌚ {idx}/{amount}. Task {task_name} "
                            f"stopped in {await self.gettimeof(task.stop):3f}ms")
            except Exception:
                logger.warning(f"⚠️ Failed to stop task {task_name}")
                raise

        logger.info(f"✅ Stopped all {amount} tasks in {time.perf_counter() - start:3f}ms")

    async def gettimeof(self, callable: Callable[..., Awaitable[None]]) -> float:
        start = time.perf_counter()
        await callable()
        elapsed = time.perf_counter() - start
        return elapsed
