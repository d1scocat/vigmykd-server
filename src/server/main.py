import asyncio

from socket import socket, AF_INET, SOCK_DGRAM

from server.settings import config
from server.log import logger

from server.srv import Server


async def main():
    with socket(AF_INET, SOCK_DGRAM) as server_socket:
        server_socket.bind(('0.0.0.0', config.port))
        server_socket.setblocking(False)

        logger.info(f"Listening on 0.0.0.0:{config.port}")

        server = Server(sock=server_socket)
        await server.loop()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info("Shutting down server")
