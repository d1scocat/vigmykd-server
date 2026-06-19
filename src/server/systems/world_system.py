from server.models.player import Player
from server.settings import player
from server.systems import System
from server.world.headless import HeadlessWorld


class WorldSystem(System[Player]):
    def act_on(self, sub: Player, world: HeadlessWorld):
        # === === === collisions and pos update === === ===

        # === === === x axis === === ==
        sub.position.x += sub.position.vel_x
        coll_rect = world.get_collision(sub.rect)

        if coll_rect:
            overlap_left = (sub.position.x + player.hitbox_width) - coll_rect.left
            overlap_right = coll_rect.right - sub.position.x

            if abs(overlap_left) < abs(overlap_right):
                sub.position.x = coll_rect.left - player.hitbox_width
            else:
                sub.position.x = coll_rect.right

            sub.position.vel_x = 0

        # === === === y axis === === ==
        sub.position.y += sub.position.vel_y
        coll_rect = world.get_collision(sub.rect)

        if coll_rect:
            overlap_top = (sub.position.y + player.hitbox_height) - coll_rect.top
            overlap_bottom = coll_rect.bottom - sub.position.y

            if abs(overlap_top) < abs(overlap_bottom):
                sub.position.y = coll_rect.top - player.hitbox_height
                sub.position.is_grounded = True
            else:
                sub.position.y = coll_rect.bottom
                sub.position.is_grounded = False

            sub.position.vel_y = 0
        else:
            sub.position.is_grounded = False
