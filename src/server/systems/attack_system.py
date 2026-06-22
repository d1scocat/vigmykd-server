from server.models.player import Facing, Player, PlayerInput
from server.settings import phys, player
from server.systems import System


class AttackSystem(System[Player]):
    def act_on(self, sub: Player, player_input: PlayerInput, others: list[Player]):
        if player_input.parry and sub.cooldowns.can_parry and sub.mana >= player.parry_mana_cost:
            sub.physics.invulnerable_timer = player.parry_ticks
            sub.cooldowns.cooldown_parry()

        sub.physics.invulnerable_timer = max(0, sub.physics.invulnerable_timer - 1)
        sub.physics.stun_timer = max(0, sub.physics.stun_timer - 1)
        sub.combo.timer = max(0, sub.combo.timer - 1)

        # === === === push (no damage, kb) === === ===
        if player_input.push and sub.cooldowns.can_push:
            print("[DEBUG] push 1")
            success = False

            for other in others:
                if other.physics.invulnerable_timer > 0:
                    continue

                dx = other.position.x - sub.position.x
                dy = abs(other.position.y - sub.position.y)

                if abs(dx) > player.push_range or dy <= player.push_vertical_tolerance:
                    continue

                print(f"[DEBUG] Push suitable player is {other.player_id!r}")

                direction = 1 if dx >= 0 else -1
                other.position.vel_x += direction * player.push_force_x
                other.position.vel_y += player.push_force_y
                other.position.is_grounded = False
                other.physics.invulnerable_timer = player.push_iframes
                other.break_combo()

                success = True

            if success:
                sub.cooldowns.cooldown_push()

        # === === === stomp (small aoe damage, kb)
        if player_input.stomp and sub.position.is_grounded and sub.cooldowns.can_stomp:
            print("[DEBUG] stomp 1")
            success = False

            for other in others:
                if other.physics.invulnerable_timer > 0:
                    continue

                dx = other.position.x - sub.position.x
                dy = other.position.y - sub.position.y
                dist_sq = dx**2 + dy**2

                if dist_sq > (player.stomp_range ** 2):
                    continue

                print(f"[DEBUG] Stomp suitable player is {other.player_id!r}")

                dist = dist_sq ** 0.5
                nx = dx / dist
                ny = min(-0.2, dy / dist)  # bias upward

                strength = 1 - (dist / player.stomp_range)

                other.position.is_grounded = False
                other.physics.invulnerable_timer = player.stomp_iframes
                other.break_combo()

                other.position.vel_x += nx * player.stomp_knockback_x * strength
                other.position.vel_y += ny * player.stomp_knockback_y * strength

                other.health -= player.stomp_damage

                success = True

            if success:
                sub.cooldowns.cooldown_stomp()

        # === === === punch (damage, 4 hits in a row lead to kb + stun) === === ===
        if player_input.punch and sub.cooldowns.can_punch:
            print("[DEBUG] punch 1")
            success = False

            for other in others:
                if other.physics.invulnerable_timer > 0:
                    continue

                dx = other.position.x - sub.position.x
                dy = other.position.y - sub.position.y
                dist_sq = dx**2 + dy**2

                if dist_sq > (player.punch_range ** 2):
                    continue

                print(f"[DEBUG] Punch suitable player is {other.player_id!r}")

                dist = dist_sq ** 0.5

                other.health -= player.punch_damage
                other.physics.invulnerable_timer = player.punch_iframes
                other.break_combo()

                sub.combo.hits += 1
                sub.combo.timer = player.punch_combo_window_ticks

                if sub.combo.hits >= player.punches_to_knockdown:
                    other.physics.stun_timer = player.punch_stun_ticks
                    other.position.vel_x += (dx / max(dist, 0.0001)) * player.punch_knockdown_kb_x
                    other.position.vel_y = -player.punch_knockdown_kb_y
                    other.position.is_grounded = False

                recoil_dir = -1 if dx > 0 else 1
                sub.position.vel_x += recoil_dir * player.punch_recoil_x
                sub.position.vel_y += player.punch_recoil_y

                success = True

            if success:
                sub.cooldowns.cooldown_punch()
