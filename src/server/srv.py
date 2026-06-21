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
        # debug
        self.tps_tick_count = 0
        self.tps_last_time = io_handler.loop.time()

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

        # cba to extract, maybe later
        RECONCILE_INTERVAL = 4
        MAX_STEPS = 5

        tick_counter = 0

        while True:
            now = loop.time()
            accumul += (now - last)
            last = now

            steps = 0

            while accumul >= delta and steps < MAX_STEPS:
                self.ctx.match_manager.simulate(self.ctx.tick)
                self.ctx.advance_simul()

                tick_counter += 1

                if tick_counter % RECONCILE_INTERVAL == 0:
                    asyncio.create_task(
                        self.ctx.match_manager.share_reconcile(
                            self.ctx.tick,
                            self.io_handler
                        )
                    )

                    asyncio.create_task(
                        self.ctx.match_manager.check_keepalive_players(
                            self.ctx.tick,
                            self.io_handler
                        )
                    )

                accumul -= delta
                steps += 1

            # TPS logging
            now = loop.time()
            self.tps_tick_count += steps

            elapsed = now - self.tps_last_time
            if elapsed >= 2.0:
                tps = self.tps_tick_count / elapsed
                logger.info(f"TPS: {tps:.2f}")
                self.tps_tick_count = 0
                self.tps_last_time = now

            sleep = (last + delta) - loop.time()
            if sleep > 0:
                await asyncio.sleep(sleep)
