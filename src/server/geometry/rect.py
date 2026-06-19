from dataclasses import dataclass


@dataclass
class Rect:
    """
    only what's necessary!
    """
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    def colliderect(self, other: 'Rect') -> bool:
        """AABB"""
        return (
            self.left < other.right and
            self.right > other.left and
            self.top < other.bottom and 
            self.bottom > other.top
        )
