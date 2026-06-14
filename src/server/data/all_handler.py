import asyncio

from google.protobuf.message import Message

from server.context import ServerContext
from server.data.factory import PacketSigner
from server.data.handlers import handlers, UDPAddress
from server.log import logger
from server.settings import config

import server.generated.v1.packet_pb2 as packet_pb2


class SocketIOHandler:
    def __init__(
        self,
        ctx: ServerContext
    ):
        self.incoming = asyncio.Queue(maxsize=config.queue_size)
        self.outgoing = asyncio.Queue(maxsize=config.queue_size)
        self.ctx = ctx

    async def enqueue_single_out(self, value: bytes, client: UDPAddress):
        await self.outgoing.put((value, client))

    async def enqueue_pending_in(self, loop: asyncio.AbstractEventLoop):
        while True:
            data, client = await loop.sock_recvfrom(self.ctx.sock, 2048)
            await self.incoming.put((data, client))

    async def recv_worker(self):
        while True:
            await self._recv()

    async def send_worker(self):
        while True:
            await self._send()
    
    async def _recv(self):
        data, client = await self.incoming.get()  # we await, so no asyncio.QueueEmpty ever

        try:
            envelope = packet_pb2.Envelope()
            try:
                envelope.ParseFromString(data)
                await self.handle_envelope(envelope, client)
            except Exception:
                logger.warning(f"Malformed packet from {client}")
        except Exception:
            logger.exception("Worker failure", exc_info=True)
        finally:
            self.incoming.task_done()

    async def _send(self):
        data, client = await self.outgoing.get()
        try:
            self.ctx.sock.sendto(data, client)
        finally:
            self.outgoing.task_done()

    async def handle_envelope(self, envelope: packet_pb2.Envelope, client: UDPAddress):
        match envelope.WhichOneof("payload"):
            case "signed_packet":
                signed_packet = envelope.signed_packet
                if not PacketSigner.verify(signed_packet):
                    logger.warning(f"Invalid signature from {client}")
                    return

                packet = signed_packet.payload
                msg_id = packet.msg_id
                match packet.WhichOneof("payload"):
                    case "icp":
                        await self._dispatch(packet.icp, client, msg_id, "icp")

            case "packet":
                packet = envelope.packet
                msg_id = packet.msg_id
                match packet.WhichOneof("payload"):
                    case "server_to_client":
                        # Throw away (how tf did it get here anyway?)
                        return
                    case "client_to_server":
                        await self._dispatch(packet.client_to_server, client, msg_id, "cts")

    async def _dispatch(self, packet: Message, client: UDPAddress, msg_id: int, type: str):
        payload_name = packet.WhichOneof("payload")
        if payload_name is None:
            return

        discovered_handlers = handlers.get(type)
        if not discovered_handlers:
            return
        
        handler = discovered_handlers.get(payload_name)
        if not handler:
            return

        await handler(
            getattr(packet, payload_name),
            client,
            self.ctx,
            self.enqueue_single_out,
            msg_id
        )
