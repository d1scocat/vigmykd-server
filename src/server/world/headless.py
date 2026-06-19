import json

from dataclasses import dataclass, field
from pathlib import Path

from server.geometry import Rect


@dataclass
class Tileset:
    cols: int
    tile_width: int
    tile_height: int
    first_gid: int
    collisions: dict[int, list[Rect]] = field(default_factory=dict)

    @classmethod
    def load(cls, tsj_path: Path, first_gid: int) -> 'Tileset':
        data = json.loads(tsj_path.read_text())

        cols = data["columns"]
        tile_width = data["tilewidth"]
        tile_height = data["tileheight"]

        collisions = {}

        for tile_data in data.get("tiles", []):
            tile_id = tile_data["id"]  # zero-indexed

            if "objectgroup" in tile_data:
                tile_collisions = []
                for obj in tile_data["objectgroup"]["objects"]:
                    tile_collisions.append(Rect(
                        obj["x"], obj["y"], obj["width"], obj["height"]
                    ))

                collisions[tile_id] = tile_collisions

        return cls(
            cols=cols,
            tile_width=tile_width,
            tile_height=tile_height,
            first_gid=first_gid,
            collisions=collisions
        )

    def get_sprite_coords(self, map_gid: int) -> tuple[int, int]:
        tile_id = map_gid - self.first_gid

        x = tile_id % self.cols
        y = tile_id // self.cols
        return (x, y)


@dataclass
class MapData:
    width: int
    height: int
    tile_width: int
    tile_height: int
    first_gid: int
    grid: list[list[int]]

    @classmethod
    def load(cls, tmj_path: Path) -> 'MapData':
        data = json.loads(tmj_path.read_text())

        width= data["width"]
        height = data["height"]
        tile_width = data["tilewidth"]
        tile_height = data["tileheight"]

        first_layer_data = None
        for layer in data["layers"]:
            if layer["type"] == "tilelayer" and layer["visible"]:
                first_layer_data = layer
                break

        if first_layer_data is None:
            raise ValueError(
                f"Could not find visible tile layer while loading {tmj_path.resolve()}"
            )

        grid = []
        fl_data = first_layer_data["data"]

        for y in range(height):
            grid.append(fl_data[(y * width):((y+1)*width)])

        return cls(
            width=width,
            height=height,
            tile_width=tile_width,
            tile_height=tile_height,
            first_gid=data["tilesets"][0]["firstgid"],
            grid=grid
        )


class HeadlessWorld:
    collision_grid: list[list[list[Rect]]]

    def __init__(self, tmj_path: Path, tsj_path: Path):
        self.map_data = MapData.load(tmj_path)
        self.tileset = Tileset.load(tsj_path, self.map_data.first_gid)

        self._build_collision_grid()

    def get_collision(self, rect: Rect) -> Rect | None:
        tw, th = self.map_data.tile_width, self.map_data.tile_height
        w, h = self.map_data.width, self.map_data.height

        start_x = int(max(0, rect.left // tw))
        end_x = int(min(w - 1, rect.right // tw))
        
        start_y = int(max(0, (rect.top // th)))
        end_y = int(min(h - 1, rect.bottom // th))

        for y in range(start_y, end_y + 1):
            for x in range(start_x, end_x + 1):
                for coll in self.collision_grid[y][x]:
                    if rect.colliderect(coll):
                        return coll

        return None

    def _build_collision_grid(self):
        self.collision_grid = [
            [[] for _ in range(self.map_data.width)]
            for _ in range(self.map_data.height)
        ]

        tw, th = self.map_data.tile_width, self.map_data.tile_height
        w, h = self.map_data.width, self.map_data.height

        for y in range(h):
            for x in range(w):
                gid = self.map_data.grid[y][x]
                if gid == 0:
                    continue  # empty space

                tile_id = gid - self.tileset.first_gid
                local_collisions = self.tileset.collisions.get(tile_id, [])

                for coll in local_collisions:
                    self.collision_grid[y][x].append(Rect(
                        x * tw + coll.x,
                        y * th + coll.y,
                        coll.width,
                        coll.height
                    ))