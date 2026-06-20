from server.models.player import Facing, Player, PlayerInput
from server.settings import phys
from server.systems import System


class MoveSystem(System[Player]):
    def act_on(self, sub: Player, player_input: PlayerInput):
        if player_input.jump:
            sub.physics.jump_buffer_timer = phys.jump_buffer_ticks
        elif sub.physics.jump_buffer_timer > 0:
            sub.physics.jump_buffer_timer -= 1

        # === === === dashing === === === #
        if player_input.dash and not sub.position.dashing:
            sub.position.dashing = True
            sub.physics.dash_timer = phys.dash_duration_ticks

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
                dash_dir = player_input.move_dir if player_input.move_dir != 0 else 1
                sub.position.vel_x = dash_dir * phys.dash_speed
                sub.position.vel_y = 0.0

        if sub.position.dashing:
            sub.physics.dash_timer -= 1
            if sub.physics.dash_timer <= 0:
                sub.position.dashing = False

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

                #if (player_input.move_dir > 0 and sub.position.vel_x < 0) or \
                #    (player_input.move_dir < 0 and sub.position.vel_x > 0):
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
        can_jump = sub.position.is_grounded or sub.physics.coyote_timer > 0
        has_jump_buffer = sub.physics.jump_buffer_timer > 0

        if has_jump_buffer and not player_input.duck and can_jump:
            sub.position.vel_y = phys.jump_force
            sub.position.is_grounded = False
            sub.physics.coyote_timer = 0
            sub.physics.jump_buffer_timer = 0

        # === === === y movement: gravity === === ===
        if not sub.position.is_grounded:
            if sub.position.vel_y < 0:
                if not player_input.jump:
                    sub.position.vel_y += phys.gravity_rise * phys.fast_fall_multiplier
                else:
                    sub.position.vel_y += phys.gravity_rise
            else:
                sub.position.vel_y += phys.gravity_fall

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
