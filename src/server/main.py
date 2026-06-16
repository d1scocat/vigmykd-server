import asyncio

from socket import socket, AF_INET, SOCK_DGRAM

from server.context import ServerContext
from server.data.all_handler import SocketIOHandler
from server.models.match import MatchManager
from server.log import logger
from server.settings import config
from server.tasks.tasks import TaskManager

from server.srv import Server


async def main():
    with socket(AF_INET, SOCK_DGRAM) as server_socket:
        server_socket.bind(('0.0.0.0', config.port))
        server_socket.setblocking(False)

        logger.info(f"Listening on 0.0.0.0:{config.port}")

        match_manager = MatchManager()

        ctx = ServerContext(
            sock=server_socket,
            match_manager=match_manager
        )

        io_handler = SocketIOHandler(
            ctx=ctx,
            loop=asyncio.get_running_loop()
        )

        task_manager = TaskManager(
            ctx=ctx,
            io_handler=io_handler
        )
        await task_manager.start()

        server = Server(
            ctx=ctx,
            io_handler=io_handler
        )
        await server.loop()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info("Shutting down server")
