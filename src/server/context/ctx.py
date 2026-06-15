from socket import socket

from server.models.match import MatchManager


class ServerContext:
    def __init__(
        self,
        sock: socket,
        match_manager: MatchManager
    ):
        self.sock = sock
        self.match_manager = match_manager

