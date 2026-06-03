import os

from socket import socket, AF_INET, SOCK_DGRAM

import server.generated.proto.v1.packet_pb2 as packet_pb2

from server.settings import config
from server.log import logger

try:
    with socket(AF_INET, SOCK_DGRAM) as server_socket:
        server_socket.bind(('0.0.0.0', config.port))
        server_socket.settimeout(1.0)

        logger.info(f"Listening on 0.0.0.0:{config.port}")

        while True:
            try:
                data, client = server_socket.recvfrom(1024)
                packet = packet_pb2.Packet()
                packet.ParseFromString(data)
                print(packet)
            except TimeoutError:
                continue
except KeyboardInterrupt:
    logger.info("Shutting down server")