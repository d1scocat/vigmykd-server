from socket import socket

from server.models.match import MatchManager


class ServerContext:
    def __init__(
        self,
        sock: socket
    ):
        self.sock = sock

        self.match_manager = MatchManager()

