import asyncio

from server.context import ServerContext
from server.data.all_handler import SocketIOHandler
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
        while True:
            start = loop.time()

            self.ctx.match_manager.simulate_and_share(self.ctx.tick, self.io_handler)
            # switch to this vvv   if ^^^ ever gets too slow:
            # await loop.run_in_executor(
            #     None,
            #     self.ctx.match_manager.simulate_and_share,
            #     self.ctx.tick,
            #     self.io_handler
            # )

            self.ctx.advance_simul()
            elapsed = loop.time() - start
            await asyncio.sleep(max(0, delta - elapsed))
