import hashlib
import hmac

import server.generated.v1.packet_pb2 as packet_pb2

from server.settings import config

from typing import overload


class Packets:
    _id = 500_000_000 - 1

    @staticmethod
    def get_next_id() -> int:
        Packets._id += 1
        return Packets._id

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
    def matchmaking_enter_response(
        match_id: str,
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id
        packet.server_to_client.matchmaking_enter_response.match_id = match_id

        return packet

    @staticmethod
    def matchmaking_quit_response(
        match_id: str,
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id
        packet.server_to_client.matchmaking_quit_response.match_id = match_id

        return packet

    @staticmethod
    def register_match_response(
        joined_match_id: str,
        old_match_id: str,
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id
        packet.icp.register_match_response.joined_match_id = joined_match_id
        packet.icp.register_match_response.old_match_id = old_match_id

        return packet

    @staticmethod
    def inform_match_start(
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id
        packet.server_to_client.inform_match_start.SetInParent()

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