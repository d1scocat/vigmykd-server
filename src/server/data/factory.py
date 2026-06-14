import hashlib
import hmac

from server.generated.proto.v1 import packet_pb2 as packet_pb2

from server.settings import config

from typing import overload


class Packets:
    # _id = 20_000_000_000

    @staticmethod
    def get_next_id() -> int:
        # STC messages don't require IDs generally, because the server does not
        # expect an Ack from the client. Just return 0, uncomment this in the future if needed
        # Packets._id += 1
        # return Packets._id
        return 0

    @staticmethod
    def ack(
        msg_id: int,
        ok: bool
    ):
        """`envelope()` a packet before sending!"""
        packet = packet_pb2.Packet()
        packet.msg_id = Packets.get_next_id()
        packet.server_to_client.ack.acknowledged_msg_id = msg_id
        packet.server_to_client.ack.ok = ok

        return packet

    @staticmethod
    @overload
    def envelope(
        payload: packet_pb2.Packet,
    ) -> packet_pb2.Envelope:
        ...

    @staticmethod
    @overload
    def envelope(
        payload: packet_pb2.SignedPacket,
    ) -> packet_pb2.Envelope:
        ...

    @staticmethod
    def envelope(payload):
        env = packet_pb2.Envelope()

        if isinstance(payload, packet_pb2.Packet):
            env.packet.CopyFrom(payload)
        elif isinstance(payload, packet_pb2.SignedPacket):
            env.signed_packet.CopyFrom(payload)
        else:
            raise TypeError(f"Unsupported payload type: {type(payload)}")

        return env


class PacketSigner:
    @staticmethod
    def verify(
        signed_packet: packet_pb2.SignedPacket,
    ) -> bool:
        expected = hmac.new(
            config.signature.encode("utf-8"),
            signed_packet.payload.SerializeToString(),
            hashlib.sha256,
        ).digest()

        return hmac.compare_digest(
            expected,
            signed_packet.signature,
        )