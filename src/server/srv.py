import asyncio

from server.context import ServerContext
from server.data.all_handler import SocketIOHandler


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

        await asyncio.Event().wait()
