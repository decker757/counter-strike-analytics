"""Map zone graph for intent prediction — loads zone definitions and provides spatial queries."""

import json
import math
from pathlib import Path
from typing import Optional

# Map configs directory (relative to project root)
_CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config" / "maps"

# Bounding box cache loaded from YAML map configs (used if zones JSON missing)
_MAP_BOUNDS: dict[str, dict] = {}


class MapZoneGraph:
    """Spatial graph of named tactical zones for a CS2 map.

    Each zone is a polygon with an adjacency list. Used to predict where a
    player is heading based on current zone and movement direction.
    """

    def __init__(self, map_name: str):
        """Load zone graph for a given map.

        Args:
            map_name: e.g. 'de_inferno' or 'de_dust2'
        """
        self.map_name = map_name
        self.zones: dict[str, dict] = {}  # zone_id -> zone data
        self._load_zones()

    def _load_zones(self):
        """Load zone definitions from JSON config file."""
        json_path = _CONFIG_DIR / f"{self.map_name}_zones.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Zone config not found: {json_path}\n"
                f"Create zone definitions at {json_path}"
            )

        with open(json_path, "r") as f:
            data = json.load(f)

        for zone in data.get("zones", []):
            self.zones[zone["id"]] = zone

    def get_zone(self, x: float, y: float) -> Optional[str]:
        """Find which zone contains the given game coordinates.

        Uses point-in-polygon test against rectangular zone bounds.
        If no zone contains the point, returns the nearest zone by center distance.

        Args:
            x: Game X coordinate
            y: Game Y coordinate

        Returns:
            Zone ID string, or None if map has no zones loaded
        """
        if not self.zones:
            return None

        # First pass: exact containment via rectangular bounds from map YAML
        # We check against the map config YAML which has precise bounds
        map_bounds = _MAP_BOUNDS.get(self.map_name, {})
        zone_bounds = map_bounds.get("zones", {})

        for zone_id, bounds in zone_bounds.items():
            if "min_x" in bounds and "max_x" in bounds:
                if bounds["min_x"] <= x <= bounds["max_x"] and \
                   bounds["min_y"] <= y <= bounds["max_y"]:
                    return zone_id

        # Second pass: find nearest zone by center distance
        nearest_zone = None
        nearest_dist = float("inf")
        for zone_id, bounds in zone_bounds.items():
            if "min_x" in bounds and "max_x" in bounds:
                cx = (bounds["min_x"] + bounds["max_x"]) / 2
                cy = (bounds["min_y"] + bounds["max_y"]) / 2
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_zone = zone_id

        return nearest_zone

    def get_adjacent_zones(self, zone_id: str) -> list[str]:
        """Get zones directly connected to the given zone.

        Args:
            zone_id: Zone identifier

        Returns:
            List of adjacent zone IDs (empty list if zone not found)
        """
        zone = self.zones.get(zone_id)
        if zone is None:
            return []
        return zone.get("adjacent", [])

    def predict_next_zone(
        self,
        current_zone: str,
        vel_x: float,
        vel_y: float,
        num_alive_ct: int = 5,
        num_alive_t: int = 5,
        is_ct: bool = True,
    ) -> Optional[str]:
        """Predict the most likely next zone a player will enter.

        Uses velocity direction to choose among adjacent zones.
        If no adjacent zone aligns with velocity, returns current zone.

        Args:
            current_zone: Player's current zone
            vel_x: X velocity component (game units/tick)
            vel_y: Y velocity component (game units/tick)
            num_alive_ct: Number of CT players alive (for territory awareness)
            num_alive_t: Number of T players alive (for territory awareness)
            is_ct: Whether this player is on CT side

        Returns:
            Predicted next zone ID, or None if current zone unknown
        """
        if current_zone is None:
            return None

        adjacent = self.get_adjacent_zones(current_zone)
        if not adjacent:
            return current_zone

        # Compute velocity direction vector and magnitude
        speed = math.sqrt(vel_x ** 2 + vel_y ** 2)
        if speed < 1.0:
            # Player is nearly stationary — stay in current zone
            return current_zone

        # Normalize velocity direction
        dir_x = vel_x / speed
        dir_y = vel_y / speed

        # Get center of current zone
        current_center = self._get_zone_center(current_zone)
        if current_center is None:
            return adjacent[0] if adjacent else current_zone

        # For each adjacent zone, compute dot product between velocity
        # direction and the direction from current zone to adjacent zone.
        # Higher dot product = player is heading toward that zone.
        best_zone = None
        best_dot = -2.0  # cosine similarity range is [-1, 1]

        for adj_id in adjacent:
            adj_center = self._get_zone_center(adj_id)
            if adj_center is None:
                continue

            # Direction from current zone center to adjacent zone center
            to_adj_x = adj_center[0] - current_center[0]
            to_adj_y = adj_center[1] - current_center[1]
            to_adj_dist = math.sqrt(to_adj_x ** 2 + to_adj_y ** 2)
            if to_adj_dist < 1.0:
                continue
            to_adj_x /= to_adj_dist
            to_adj_y /= to_adj_dist

            # Dot product: how aligned is velocity with direction to this zone?
            dot = dir_x * to_adj_x + dir_y * to_adj_y
            if dot > best_dot:
                best_dot = dot
                best_zone = adj_id

        # Territory awareness: bias toward friendly territory if retreating
        if best_dot < 0.3 and best_zone is not None:
            # Velocity doesn't strongly align with any adjacent zone.
            # Check if player is retreating toward spawn
            for adj_id in adjacent:
                adj_zone = self.zones.get(adj_id, {})
                if is_ct and adj_zone.get("is_ct_spawn"):
                    best_zone = adj_id
                    break
                if not is_ct and adj_zone.get("is_t_spawn"):
                    best_zone = adj_id
                    break

        return best_zone if best_zone else current_zone

    def _get_zone_center(self, zone_id: str):
        """Get the center coordinates of a zone from map YAML config bounds."""
        map_bounds = _MAP_BOUNDS.get(self.map_name, {})
        zone_bounds = map_bounds.get("zones", {})
        bounds = zone_bounds.get(zone_id) or zone_bounds.get(
            zone_id.replace("_", "")
        )
        if bounds and "min_x" in bounds and "max_x" in bounds:
            cx = (bounds["min_x"] + bounds["max_x"]) / 2
            cy = (bounds["min_y"] + bounds["max_y"]) / 2
            return (cx, cy)
        return None

    def get_bombsite_zone(self, site: str) -> Optional[str]:
        """Get the zone ID for a bombsite.

        Args:
            site: 'A' or 'B'

        Returns:
            Zone ID like 'a_site' or 'b_site', or None
        """
        target = f"{site.lower()}_site"
        for zone_id, zone in self.zones.items():
            if zone_id == target and zone.get("is_bombsite"):
                return zone_id
        return None

    def get_spawn_zone(self, is_ct: bool) -> Optional[str]:
        """Get the spawn zone for a team.

        Args:
            is_ct: True for CT spawn, False for T spawn

        Returns:
            Zone ID, or None
        """
        for zone_id, zone in self.zones.items():
            if is_ct and zone.get("is_ct_spawn"):
                return zone_id
            if not is_ct and zone.get("is_t_spawn"):
                return zone_id
        return None


def load_map_bounds():
    """Pre-load map bounding boxes from YAML configs for zone lookup.

    Called once at module import to populate _MAP_BOUNDS cache.
    Uses the existing YAML configs that have zone bounds defined.
    """
    global _MAP_BOUNDS

    # Inferno bounds from existing YAML
    _MAP_BOUNDS["de_inferno"] = {
        "zones": {
            "t_spawn": {"min_x": -500, "max_x": 400, "min_y": -1100, "max_y": -400},
            "mid": {"min_x": -200, "max_x": 800, "min_y": -400, "max_y": 600},
            "second_mid": {"min_x": 600, "max_x": 1400, "min_y": -200, "max_y": 600},
            "top_mid": {"min_x": 400, "max_x": 1200, "min_y": 600, "max_y": 1200},
            "apartments": {"min_x": 1200, "max_x": 2000, "min_y": -200, "max_y": 600},
            "long_a": {"min_x": 1600, "max_x": 2400, "min_y": 100, "max_y": 700},
            "short_a": {"min_x": 1400, "max_x": 2000, "min_y": 600, "max_y": 1200},
            "a_site": {"min_x": 1700, "max_x": 2600, "min_y": 400, "max_y": 1400},
            "pit": {"min_x": 2400, "max_x": 3000, "min_y": 200, "max_y": 800},
            "library": {"min_x": 2200, "max_x": 2800, "min_y": 1000, "max_y": 1600},
            "arch": {"min_x": 1600, "max_x": 2200, "min_y": 1400, "max_y": 2000},
            "banana": {"min_x": -600, "max_x": 200, "min_y": 600, "max_y": 1800},
            "car": {"min_x": -200, "max_x": 400, "min_y": 1600, "max_y": 2200},
            "construction": {"min_x": -400, "max_x": 200, "min_y": 2000, "max_y": 2600},
            "b_site": {"min_x": -300, "max_x": 600, "min_y": 2400, "max_y": 3200},
            "ct_spawn": {"min_x": 1400, "max_x": 2200, "min_y": 1800, "max_y": 2600},
            "ct_apps": {"min_x": 800, "max_x": 1400, "min_y": 2000, "max_y": 2800},
        }
    }

    # Dust2 bounds from existing YAML
    _MAP_BOUNDS["de_dust2"] = {
        "zones": {
            "t_spawn": {"min_x": -648, "max_x": 248, "min_y": -800, "max_y": -200},
            "t_ramp": {"min_x": -200, "max_x": 600, "min_y": -200, "max_y": 600},
            "mid_doors": {"min_x": -600, "max_x": 0, "min_y": 600, "max_y": 1200},
            "mid": {"min_x": -800, "max_x": 400, "min_y": 1200, "max_y": 2000},
            "long_doors": {"min_x": 1100, "max_x": 1600, "min_y": 0, "max_y": 600},
            "long_a": {"min_x": 1100, "max_x": 1700, "min_y": 600, "max_y": 1600},
            "a_site": {"min_x": 800, "max_x": 1700, "min_y": 2000, "max_y": 2800},
            "catwalk": {"min_x": 200, "max_x": 900, "min_y": 1800, "max_y": 2400},
            "upper_tunnels": {"min_x": -1100, "max_x": -400, "min_y": 400, "max_y": 1200},
            "lower_tunnels": {"min_x": -1800, "max_x": -1100, "min_y": 800, "max_y": 1600},
            "b_site": {"min_x": -1800, "max_x": -1000, "min_y": 2200, "max_y": 3000},
            "ct_spawn": {"min_x": -400, "max_x": 400, "min_y": 2600, "max_y": 3200},
            "ct_mid": {"min_x": -200, "max_x": 600, "min_y": 2000, "max_y": 2600},
        }
    }


# Load bounds at import time
load_map_bounds()
