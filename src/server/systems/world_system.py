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
            if sub.position.vel_x > 0:
                sub.position.x = coll_rect.left - player.hitbox_width
            elif sub.position.vel_x < 0:
                sub.position.x = coll_rect.right

            sub.position.vel_x = 0

        # === === === y axis === === ==
        sub.position.y += sub.position.vel_y
        coll_rect = world.get_collision(sub.rect)
        if coll_rect:
            if sub.position.vel_y > 0:
                sub.position.y = coll_rect.top - player.hitbox_height
                sub.position.is_grounded = True
            elif sub.position.vel_y < 0:
                sub.position.y = coll_rect.bottom

            sub.position.vel_y = 0
        else:
            sub.position.is_grounded = False
