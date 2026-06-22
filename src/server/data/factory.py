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
    def request_match_info_response(
        players: list['server.models.player.Player'],
        your_id: str,
        rng_seed: int,
        server_tick: int,
        map_name: str,
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        from server.models.player import Facing

        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id
        packet.server_to_client.request_match_info_response.your_id = your_id
        packet.server_to_client.request_match_info_response.rng_seed = rng_seed
        packet.server_to_client.request_match_info_response.initial_server_tick = server_tick
        packet.server_to_client.request_match_info_response.map_name = map_name

        packet_players = []
        for player in players:
            data = packet_pb2.PlayerData()
            data.uuid = str(player.player_id)
            data.name = player.name
            data.position.x = player.position.x
            data.position.y = player.position.y

            data.position.facing = \
                packet_pb2.Facing.FACING_NEG_X \
                if player.position.facing == Facing.NEG_X \
                else packet_pb2.Facing.FACING_POS_X

            packet_players.append(data)

        packet.server_to_client.request_match_info_response.players.extend(packet_players)

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
    def reconcile(
        server_tick: int,
        last_client_tick: int,
        players: list['server.models.player.Player'],
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        from server.models.player import Facing

        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id

        packet.server_to_client.reconcile.server_tick = server_tick
        packet.server_to_client.reconcile.last_client_tick = last_client_tick

        packet_players = []

        for player in players:
            rec_data = packet_pb2.ReconcileData()

            rec_data.uuid = str(player.player_id)
            rec_data.facing = (
                packet_pb2.Facing.FACING_NEG_X
                if player.position.facing == Facing.NEG_X
                else packet_pb2.Facing.FACING_POS_X
            )

            rec_data.x = player.position.x
            rec_data.y = player.position.y
            rec_data.vel_x = player.position.vel_x
            rec_data.vel_y = player.position.vel_y

            rec_data.is_grounded = player.position.is_grounded
            rec_data.is_ducking = player.position.ducking
            rec_data.is_dashing = player.position.dashing

            rec_data.dash_timer = player.physics.dash_timer
            rec_data.coyote_timer = player.physics.coyote_timer
            rec_data.jump_buffer_timer = player.physics.jump_buffer_timer
            rec_data.last_jump_pressed = player.physics.last_jump_pressed
            rec_data.last_dash_pressed = player.physics.last_dash_pressed
            rec_data.hang_timer = player.physics.hang_timer
            rec_data.invulnerable_timer = player.physics.invulnerable_timer
            rec_data.heavy_gravity_timer = player.physics.heavy_gravity_timer
            rec_data.light_gravity_timer = player.physics.light_gravity_timer
            rec_data.stun_timer = player.physics.stun_timer

            rec_data.brake_dash = player.cooldowns.brake_dash
            rec_data.reverse_dash = player.cooldowns.reverse_dash
            rec_data.hang = player.cooldowns.hang
            rec_data.parry = player.cooldowns.parry
            rec_data.heavy = player.cooldowns.heavy
            rec_data.light = player.cooldowns.light
            rec_data.normal = player.cooldowns.normal
            rec_data.push = player.cooldowns.push
            rec_data.stomp = player.cooldowns.stomp
            rec_data.punch = player.cooldowns.punch

            rec_data.combo_hits = player.combo.hits
            rec_data.combo_timer = player.combo.timer
            rec_data.combo_broken = player.combo.broken

            rec_data.mana = player.mana
            rec_data.health = player.health

            packet_players.append(rec_data)

        packet.server_to_client.reconcile.players.extend(packet_players)

        return packet

    @staticmethod
    def kicked_from_match(
        match_id: str,
        player_id: str,
        reason_i18n: str,
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        from server.models.player import Facing

        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id

        packet.server_to_client.kicked_from_match.match_id = match_id
        packet.server_to_client.kicked_from_match.player_id = player_id
        packet.server_to_client.kicked_from_match.reason_i18n = reason_i18n

        return packet

    @staticmethod
    def lost_match(
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id

        packet.client_to_server.lost_match.SetInParent()

        return packet

    @staticmethod
    def won_match(
        msg_id: int | None = None
    ):
        """`envelope()` a packet before sending!"""
        if msg_id is None:
            msg_id = Packets.get_next_id()

        packet = packet_pb2.Packet()
        packet.msg_id = msg_id

        packet.client_to_server.won_match.SetInParent()

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