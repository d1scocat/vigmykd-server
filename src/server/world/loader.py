import json

from pathlib import Path

from server.log import logger
from server.world.headless import HeadlessWorld


MAPS_PATH = Path.cwd() / "resources" / "maps"


def load_map(name: str) -> HeadlessWorld | None:
    world_dir = MAPS_PATH / name
    if not world_dir.is_dir():
        return None

    mapdata_file = world_dir / f"{name}.mapdata"
    if not mapdata_file.is_file():
        return None
    
    try:
        mapdata = json.loads(mapdata_file.read_text())
        return HeadlessWorld(
            tmj_path=(world_dir / mapdata["map_json"]),
            tsj_path=(world_dir / mapdata["tileset_json"]),
        )
    except Exception:
        logger.exception("Failed to load map %s", name)
        return None


def load_maps(skip_malformed: bool) -> dict[str, HeadlessWorld]:
    result = {}

    for name in MAPS_PATH.iterdir():
        if name.is_dir():
            logger.info("Loading map %s...", name)

            world = load_map(name.name)
            if not skip_malformed and world is None:
                raise ValueError(f"Could not load world {name}")

            result[name.name] = world

    logger.info("🏡 Loaded %d maps", len(result))
    return result
