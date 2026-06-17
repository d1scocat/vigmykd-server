from server.models.player import Player, PlayerInput
from server.settings import phys
from server.systems import System


class MoveSystem(System[Player]):
    def act_on(self, sub: Player, player_input: PlayerInput):
        # === === === dashing === === === #
        if player_input.dash and not sub.position.dashing:
            sub.position.dashing = True
            sub.physics.dash_timer = phys.dash_duration_ticks

            dash_dir = player_input.move_dir if player_input.move_dir != 0 else 1
            sub.position.vel_x = dash_dir * phys.dash_speed

        if sub.position.dashing:
            sub.physics.dash_timer -= 1
            if sub.physics.dash_timer <= 0:
                sub.position.dashing = False

        # === === === x movement === === ===
        if sub.position.dashing:
            pass  # ignore normal movement and maintain momentum

        elif player_input.move_dir != 0:
            target_vel = player_input.move_dir * phys.move_speed
            if (player_input.move_dir > 0 and sub.position.vel_x < 0) or \
               (player_input.move_dir < 0 and sub.position.vel_x > 0):

                if sub.position.vel_x > 0:
                    sub.position.vel_x -= phys.decel_x
                    if sub.position.vel_x < 0: sub.position.vel_x = 0.0
                else:
                    sub.position.vel_x += phys.decel_x
                    if sub.position.vel_x > 0: sub.position.vel_x = 0.0
            else:
                sub.position.vel_x += player_input.move_dir * phys.accel_x

            # clamp
            if player_input.move_dir > 0 and sub.position.vel_x > target_vel:
                sub.position.vel_x = target_vel
            elif player_input.move_dir < 0 and sub.position.vel_x < target_vel:
                sub.position.vel_x = target_vel

        else:
            if sub.position.vel_x > 0:
                sub.position.vel_x -= phys.decel_x
                if sub.position.vel_x < 0:
                    sub.position.vel_x = 0.0
            elif sub.position.vel_x < 0:
                sub.position.vel_x += phys.decel_x
                if sub.position.vel_x > 0:
                    sub.position.vel_x = 0.0

        # === === === y movement: jump === === ===
        if player_input.jump and sub.position.is_grounded and not player_input.duck:
            sub.position.vel_y = phys.jump_force
            sub.position.is_grounded = False
            sub.physics.has_cut_jump = False

        # === === === y movement: gravity === === ===
        if not sub.position.is_grounded:
            # if let go while jumping, kill momentum! :)
            if not player_input.jump and sub.position.vel_y < 0 and not sub.physics.has_cut_jump:
                sub.position.vel_y *= phys.jump_cut_scalar
                sub.physics.has_cut_jump = True

            if sub.position.vel_y < 0:
                sub.position.vel_y += phys.gravity_rise
            else:
                sub.position.vel_y += phys.gravity_fall

            if sub.position.vel_y > phys.terminal_velocity:
                sub.position.vel_y = phys.terminal_velocity

        # === === === pos update === === ===
        sub.position.x += sub.position.vel_x
        sub.position.y += sub.position.vel_y

        # === === === collision, ground === === ===
        floor_y = 0.0  # (stub!)
        if sub.position.y <= floor_y:
            sub.position.y = floor_y
            sub.position.vel_y = 0.0
            sub.position.is_grounded = True

        # future: add collisions
