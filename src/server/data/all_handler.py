import asyncio
import time

from google.protobuf.message import Message
from google.protobuf.message import DecodeError

from collections import deque
from dataclasses import dataclass, field

from server.context import ServerContext
from server.data.factory import PacketSigner
from server.data.handlers import handlers, UDPAddress
from server.log import logger
from server.settings import config

import server.generated.v1.packet_pb2 as packet_pb2


MKey = tuple[int, UDPAddress]


@dataclass
class _WaitingAck:
    message: bytes
    addr: UDPAddress
    last_sent: float = field(default_factory=time.monotonic)
    attempts: int = 0


@dataclass
class _WaitingPacket:
    message: bytes
    addr: UDPAddress
    needs_ack: bool = False
    msg_id: int | None = None


class SocketIOHandler:
    def __init__(
        self,
        ctx: ServerContext,
        loop: asyncio.AbstractEventLoop
    ):
        self._waiting_ack: dict[MKey, _WaitingAck] = {}

        self._processed_set: set[MKey] = set()
        self._processed_queue: deque[MKey] = deque(maxlen=config.keep_processed)

        self.incoming = asyncio.Queue(maxsize=config.queue_size)
        self.outgoing: asyncio.Queue[_WaitingPacket] = asyncio.Queue(maxsize=config.queue_size)

        self.ctx = ctx
        self.loop = loop

    async def enqueue_single_out(
        self,
        packet: Message,
        client: UDPAddress,
        needs_ack: bool = False,
        ack_id: int | None = None
    ):
        await self.outgoing.put(_WaitingPacket(
            packet.SerializeToString(),
            client,
            needs_ack,
            ack_id
        ))

    async def enqueue_pending_in(self):
        while True:
            data, client = await self.loop.sock_recvfrom(self.ctx.sock, config.packet_size)
            await self.incoming.put((data, client))

    async def recv_worker(self):
        try:
            while True:
                await self._recv()
        except asyncio.CancelledError:
            logger.info("recv_worker stopped")
            raise

    async def send_worker(self):
        try:
            while True:
                await self._send()
        except asyncio.CancelledError:
            logger.info("send_worker stopped")
            raise

    async def send_unacked_worker(self):
        try:
            while True:
                await self._send_unacked()
        except asyncio.CancelledError:
            logger.info("send_unacked_worker stopped")
            raise
    
    async def _recv(self):
        data, client = await self.incoming.get()  # we await, so no asyncio.QueueEmpty ever

        try:
            envelope = packet_pb2.Envelope()
            envelope.ParseFromString(data)
            if not self._check_ack(envelope, client):
                await self.handle_envelope(envelope, client)
        except DecodeError:
            logger.warning("Malformed packet from %s", client)
            return
        except Exception:
            logger.exception("Worker failure while receiving packet from %s", client)
        finally:
            self.incoming.task_done()

    async def _send(self):
        msg = await self.outgoing.get()

        data = msg.message
        client = msg.addr
        ack_id = msg.msg_id

        try:
            logger.info(f"[NET] PHYSICALLY SENDING {len(data)} bytes to {client}")
            await self.loop.sock_sendto(self.ctx.sock, data, client)
        except Exception:
            logger.warning("Failed to send a packet", exc_info=True)
        else:
            if msg.needs_ack and ack_id is not None:
                self._waiting_ack[(ack_id, client)] = _WaitingAck(
                    message=data,
                    addr=client,
                    # give it a grace period of `reack_interval` before
                    # the worker reaches it and tries to resend
                    last_sent=time.monotonic() + config.reack_interval
                )
        finally:
            self.outgoing.task_done()

    async def _send_unacked(self):
        now = time.monotonic()

        expired = []

        for m_key, message in list(self._waiting_ack.items()):
            data = message.message
            client = message.addr
            last_sent = message.last_sent
            attempts = message.attempts

            if attempts >= config.max_ack_attempts:
                expired.append(m_key)
                continue

            if now - last_sent > config.reack_interval:
                try:
                    if m_key not in self._waiting_ack:  # concurrency inc.
                        continue
                    await self.loop.sock_sendto(self.ctx.sock, data, client)
                except Exception:
                    logger.warning("Could not retransmit ack-waiting message to %s", client)
                else:
                    message.last_sent = now
                    message.attempts += 1

        for item in expired:
            logger.debug("Packet %s expired after %s retries", item, config.max_ack_attempts)
            self._waiting_ack.pop(item, None)

        await asyncio.sleep(config.reack_interval)

    def _check_ack(self, envelope: packet_pb2.Envelope, client: UDPAddress):
        if envelope.WhichOneof("payload") != "packet":
            return False

        packet = envelope.packet
        if packet.WhichOneof("payload") != "client_to_server":
            return False

        cts = packet.client_to_server
        if cts.WhichOneof("payload") != "ack":
            return False

        ack = cts.ack
        msg_id = ack.acknowledged_msg_id
        self._waiting_ack.pop((msg_id, client), None)
        return True

    async def handle_envelope(self, envelope: packet_pb2.Envelope, client: UDPAddress):
        match envelope.WhichOneof("payload"):
            case "signed_packet":
                signed_packet = envelope.signed_packet
                if not PacketSigner.verify(signed_packet):
                    logger.warning("Invalid signature from %s", client)
                    return

                packet = signed_packet.payload
                msg_id = packet.msg_id

                if self._was_processed((msg_id, client)):
                    return

                match packet.WhichOneof("payload"):
                    case "icp":
                        await self._dispatch(packet.icp, client, msg_id, "icp")
                    case _:
                        logger.debug("Unhandled signed packet payload: %s",
                                     packet.WhichOneof("payload"))

            case "packet":
                packet = envelope.packet
                msg_id = packet.msg_id

                if self._was_processed((msg_id, client)):
                    return

                match packet.WhichOneof("payload"):
                    case "server_to_client":
                        # Throw away (how tf did it get here anyway?)
                        return
                    case "client_to_server":
                        await self._dispatch(packet.client_to_server, client, msg_id, "cts")

            case _:
                logger.debug("Unhandled envelope payload: %s", envelope.WhichOneof("payload"))

    async def _dispatch(self, packet: Message, client: UDPAddress, msg_id: int, packet_type: str):
        payload_name = packet.WhichOneof("payload")
        if payload_name is None:
            return

        discovered_handlers = handlers.get(packet_type)
        if not discovered_handlers:
            logger.debug("No handlers discovered for %s", packet_type)
            return
        
        handler = discovered_handlers.get(payload_name)
        if not handler:
            logger.debug("No handler found for packet_type %s, payload_name %s", packet_type, payload_name)
            return

        try:
            await handler(
                getattr(packet, payload_name),
                client,
                self.ctx,
                self,
                msg_id
            )
        except Exception:
            logger.exception("Handler failed for %s from %s", payload_name, client)
        finally:
            self._process((msg_id, client))

    def _process(self, key: MKey):
        if len(self._processed_queue) == self._processed_queue.maxlen:
            oldest_key = self._processed_queue[0]
            self._processed_set.discard(oldest_key)

        self._processed_queue.append(key)
        self._processed_set.add(key)

    def _was_processed(self, key: MKey):
        return key in self._processed_set
