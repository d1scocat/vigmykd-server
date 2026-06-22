from server.models.player import Facing, Player, PlayerInput
from server.settings import phys, player
from server.systems import System


class MoveSystem(System[Player]):
    def act_on(self, sub: Player, player_input: PlayerInput):
        sub.cooldowns.reduce()

        # === === === dashing === === === #
        dash_just_pressed = player_input.dash and not sub.physics.last_dash_pressed
        can_dash = sub.mana >= player.dash_mana_cost

        if dash_just_pressed and not sub.position.dashing and can_dash:
            sub.position.dashing = True
            sub.physics.dash_timer = phys.dash_duration_ticks + 1
            sub.physics.coyote_timer = 0
            sub.mana -= player.dash_mana_cost

            # plunge down
            if not sub.position.is_grounded and player_input.duck:
                sub.position.vel_x = 0.0
                sub.position.vel_y = min(phys.dash_plunge_speed, phys.terminal_velocity)

            # dashing in place (jumping up high)
            elif sub.position.is_grounded and player_input.move_dir == 0 and not player_input.duck:
                sub.position.vel_x = 0.0
                sub.position.vel_y = phys.max_jump_force
                sub.position.is_grounded = False

            # just dashing
            else:
                dash_dir = (
                    player_input.move_dir
                    if player_input.move_dir != 0
                    else (
                        1 if sub.position.facing == Facing.POS_X else -1
                    )
                )
                
                sub.position.vel_x = dash_dir * phys.dash_speed
                sub.position.vel_y = 0.0

        if sub.position.dashing:
            sub.physics.dash_timer -= 1

            if sub.physics.dash_timer <= 0:
                sub.position.dashing = False

            reversing = player_input.reverse_dash and sub.mana >= player.reverse_dash_mana_cost
            if reversing and sub.cooldowns.can_reverse_dash:
                sub.position.vel_x *= -1
                sub.mana -= player.reverse_dash_mana_cost
                sub.cooldowns.cooldown_reverse_dash()

            if sub.position.dashing and player_input.brake_dash and sub.cooldowns.can_brake_dash:
                sub.position.dashing = False
                sub.position.vel_x *= 0.1
                sub.cooldowns.cooldown_brake_dash()

        sub.physics.last_dash_pressed = player_input.dash

        # === === === x movement === === ===
        if sub.position.dashing:
            if not sub.position.is_grounded and player_input.duck:
                sub.position.vel_x = 0.0  # no x-axis movement during plunge
            else:
                pass  # ignore normal movement and maintain momentum

        else:
            is_airborne = not sub.position.is_grounded

            current_move_speed = phys.air_move_speed if is_airborne else phys.move_speed
            current_accel_x = phys.air_accel_x if is_airborne else phys.accel_x
            current_decel_x = phys.air_decel_x if is_airborne else phys.decel_x

            if player_input.move_dir != 0:
                target_vel = player_input.move_dir * current_move_speed

                # decelerating?
                if (player_input.move_dir * sub.position.vel_x) < 0:
                    self._decelerate(sub, current_decel_x)

                # accelerating then
                else:
                    sub.position.vel_x += player_input.move_dir * current_accel_x

                # clamp
                if (player_input.move_dir > 0 and sub.position.vel_x > target_vel) or \
                    (player_input.move_dir < 0 and sub.position.vel_x < target_vel):
                    sub.position.vel_x = target_vel

            # slowing down due to no input
            else:
                self._decelerate(sub, current_decel_x)

        if not sub.position.is_grounded and not sub.position.dashing:
            sub.position.vel_x *= phys.air_drag

        # update facing
        if sub.position.vel_x > 0:
            sub.position.facing = Facing.POS_X
        elif sub.position.vel_x < 0:
            sub.position.facing = Facing.NEG_X

        # === === === coyote time === === ===
        if sub.position.is_grounded:
            sub.physics.coyote_timer = phys.coyote
        else:
            if sub.physics.coyote_timer > 0:
                sub.physics.coyote_timer -= 1

        # === === === y movement: jump === === ===
        jump_just_pressed = player_input.jump and not sub.physics.last_jump_pressed

        if jump_just_pressed:
            sub.physics.jump_buffer_timer = phys.jump_buffer_ticks
        elif sub.physics.jump_buffer_timer > 0:
            sub.physics.jump_buffer_timer -= 1

        can_jump = sub.position.is_grounded or sub.physics.coyote_timer > 0
        has_jump_buffer = sub.physics.jump_buffer_timer > 0

        if (jump_just_pressed or has_jump_buffer) and not player_input.duck and can_jump:
            sub.position.vel_y = phys.jump_force
            sub.position.is_grounded = False
            sub.physics.coyote_timer = 0
            sub.physics.jump_buffer_timer = 0

        sub.physics.last_jump_pressed = player_input.jump

        # === === === y movement: hanging === === ===
        will_hang = (
            player_input.hang and
            not sub.position.is_grounded and
            sub.cooldowns.can_hang and
            sub.physics.hang_timer <= 0 and
            sub.mana >= player.hang_mana_cost
        )

        if will_hang:
            sub.physics.hang_timer = player.hang_ticks
            sub.mana -= player.hang_mana_cost
            sub.cooldowns.cooldown_hang()

        # === === === y movement: gravity === === ===
        sub.physics.heavy_gravity_timer = max(0, sub.physics.heavy_gravity_timer - 1)
        sub.physics.light_gravity_timer = max(0, sub.physics.light_gravity_timer - 1)

        if player_input.gravity_normal:
            is_of_use = sub.physics.light_gravity_timer > 0 or sub.physics.heavy_gravity_timer > 0
            if is_of_use and sub.mana >= player.normal_mana_cost and sub.cooldowns.can_normal:
                sub.physics.light_gravity_timer = 0
                sub.physics.heavy_gravity_timer = 0
                sub.mana -= player.normal_mana_cost
                sub.cooldowns.cooldown_normal()

        can_gravity = sub.physics.light_gravity_timer == 0 and sub.physics.heavy_gravity_timer == 0
        if player_input.gravity_heavy:
            if can_gravity and sub.mana >= player.heavy_mana_cost and sub.cooldowns.can_heavy:
                sub.physics.heavy_gravity_timer = player.heavy_ticks
                sub.mana -= player.heavy_mana_cost
                sub.cooldowns.cooldown_heavy()

        if player_input.gravity_light:
            if can_gravity and sub.mana >= player.light_mana_cost and sub.cooldowns.can_light:
                sub.physics.light_gravity_timer = player.light_ticks
                sub.mana -= player.light_mana_cost
                sub.cooldowns.cooldown_light()

        gravity_multiplier = (
            player.light_scalar if sub.physics.light_gravity_timer > 0
            else (
                player.heavy_scalar if sub.physics.heavy_gravity_timer > 0
                else 1.0
            )
        )

        if not sub.position.is_grounded:
            if sub.physics.hang_timer > 0:
                sub.physics.hang_timer -= 1
                sub.position.vel_y = 0

            else:
                if sub.position.vel_y < 0:
                    if not player_input.jump:
                        sub.position.vel_y += (
                            phys.gravity_rise * phys.fast_fall_multiplier * gravity_multiplier
                        )
                    else:
                        sub.position.vel_y += phys.gravity_rise * gravity_multiplier
                else:
                    sub.position.vel_y += phys.gravity_fall * gravity_multiplier

            if sub.position.vel_y > phys.terminal_velocity:
                sub.position.vel_y = phys.terminal_velocity

    def _decelerate(self, sub: Player, current_decel_x: float):
        if sub.position.vel_x > 0:
            sub.position.vel_x -= current_decel_x
            if sub.position.vel_x < 0:
                sub.position.vel_x = 0.0

        else:
            sub.position.vel_x += current_decel_x
            if sub.position.vel_x > 0:
                sub.position.vel_x = 0.0
