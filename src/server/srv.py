import asyncio

from server.context import ServerContext
from server.data.all_handler import SocketIOHandler
from server.log import logger
from server.settings import config


class Server:
    def __init__(
        self,
        ctx: ServerContext,
        io_handler: SocketIOHandler
    ):
        self.ctx = ctx
        self.io_handler = io_handler

    async def loop(self):
        asyncio.create_task(self.io_handler.enqueue_pending_in())

        for _ in range(4):
            asyncio.create_task(self.io_handler.recv_worker())
        asyncio.create_task(self.io_handler.send_worker())
        asyncio.create_task(self.io_handler.send_unacked_worker())

        asyncio.create_task(self.tps_worker(self.io_handler.loop))

        await asyncio.Event().wait()

    @property
    def tick_delta(self):
        return 1 / config.tps

    async def tps_worker(self, loop: asyncio.AbstractEventLoop):
        delta = self.tick_delta
        accumul = 0.0
        last = loop.time()

        while True:
            now = loop.time()
            accumul += (now - last)
            last = now

            while accumul >= delta:
                try:
                    await self.ctx.match_manager.simulate_and_share(self.ctx.tick, self.io_handler)
                except Exception:
                    logger.exception("TPS worker failure")
                self.ctx.advance_simul()
                accumul -= delta

            sleep = delta - accumul
            if sleep > 0.0:
                await asyncio.sleep(sleep)
