import asyncio

from server.context import ServerContext
from server.data.all_handler import SocketIOHandler


class Server:
    def __init__(
        self,
        ctx: ServerContext
    ):
        self.ctx = ctx
        self.in_handler = SocketIOHandler(self.ctx)

    async def loop(self):
        loop = asyncio.get_running_loop()
        asyncio.create_task(self.in_handler.enqueue_pending_in(loop))

        for _ in range(4):
            asyncio.create_task(self.in_handler.recv_worker())
        asyncio.create_task(self.in_handler.send_worker())

        await asyncio.Event().wait()
