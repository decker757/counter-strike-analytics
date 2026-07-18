"""Rule-based intent predictor with zone-graph pathfinding.

Predicts player movement using:
1. Multi-timescale velocity estimation with outlier rejection
2. BFS pathfinding through map zone graph toward objectives
3. Blended short-term (velocity) + long-term (zone path) predictions
4. Context-aware action classification
"""

import math
from collections import deque
from typing import Optional

import numpy as np
import pandas as pd


class RuleBasedIntentPredictor:
    """Predicts player intent using velocity extrapolation and zone-graph pathfinding.

    No ML required — uses the map zone graph for tactical path awareness.
    """

    TEAM_CT = "CT"
    TEAM_T = "TERRORIST"

    ACTION_HOLDING = "holding"
    ACTION_PUSHING = "pushing"
    ACTION_ROTATING = "rotating"
    ACTION_FALLING_BACK = "falling_back"

    HOLDING_SPEED_THRESHOLD = 1.5       # game units/tick below which player is "holding"
    PUSHING_DISPLACEMENT_MIN = 200      # min displacement over 1s to count as pushing
    ROTATING_DIR_CHANGE_MIN = math.radians(60)  # min direction change for rotation
    FALLING_BACK_DISPLACEMENT_MIN = 150

    HORIZONS = [64, 128, 192]           # +1s, +2s, +3s at 64 tickrate
    HORIZON_LABELS = ["+1s", "+2s", "+3s"]

    def __init__(self, map_name: str):
        clean_name = map_name.replace("de_", "")
        self.map_name = f"de_{clean_name}"
        from .zone_graph import MapZoneGraph
        self.zone_graph = MapZoneGraph(self.map_name)
        self._df: pd.DataFrame | None = None

        # Pre-compute shortest paths between all zone pairs
        self._zone_paths: dict[tuple[str, str], list[str]] = {}

    # ── public API ──────────────────────────────────────────────

    def predict(
        self, tick: int, df: pd.DataFrame,
        team_filter: str = "", steamid_filter: str = "",
    ) -> dict:
        """Predict intent for alive players at a given tick."""
        self._df = df

        try:
            tick_data = df.loc[tick]
        except KeyError:
            return {"tick": tick, "players": []}
        if isinstance(tick_data, pd.Series):
            tick_data = tick_data.to_frame().T

        alive = tick_data[tick_data['is_alive'] == True]
        if team_filter:
            alive = alive[alive['team_name'] == team_filter]
        if steamid_filter:
            alive = alive[alive['steamid'].astype(str) == steamid_filter]

        if alive.empty:
            return {"tick": tick, "players": []}

        ct_alive = int((alive['team_name'] == self.TEAM_CT).sum())
        t_alive = int((alive['team_name'] == self.TEAM_T).sum())

        predictions = []
        for _, p in alive.iterrows():
            sid = str(p['steamid'])
            x, y, z = float(p['X']), float(p['Y']), float(p.get('Z', 0))
            is_ct = p['team_name'] == self.TEAM_CT

            result = self._predict_player(sid, tick, x, y, z, is_ct, ct_alive, t_alive)
            predictions.append(result)

        return {"tick": tick, "players": predictions}

    # ── per-player prediction ───────────────────────────────────

    def _predict_player(
        self, steamid: str, tick: int,
        x: float, y: float, z: float,
        is_ct: bool, ct_alive: int, t_alive: int,
    ) -> dict:
        """Full prediction pipeline for a single player."""
        current_zone = self.zone_graph.get_zone(x, y)

        # 1. Robust velocity estimation
        vel_x, vel_y, speed = self._estimate_velocity(steamid, tick, x, y)

        # 2. Determine likely objective based on team role
        objective_zone = self._determine_objective(
            current_zone, is_ct, ct_alive, t_alive, vel_x, vel_y
        )

        # 3. Find zone path to objective
        zone_path = self._find_path(current_zone, objective_zone)

        # 4. Predict next zone (immediate)
        next_zone = self.zone_graph.predict_next_zone(
            current_zone, vel_x, vel_y, ct_alive, t_alive, is_ct
        )

        # 5. Classify action
        action, action_probs = self._classify_action(
            steamid, tick, vel_x, vel_y, speed,
            current_zone, next_zone, objective_zone, is_ct,
        )

        # 6. Generate predicted positions (blended velocity + zone path)
        pred_path = self._generate_path(
            x, y, z, vel_x, vel_y, tick,
            current_zone, zone_path, objective_zone,
        )

        # 7. Confidence
        conf = self._compute_confidence(
            speed, current_zone, next_zone, objective_zone, action, zone_path
        )

        return {
            "steamid": steamid,
            "name": self._get_player_name(steamid, tick),
            "team": "CT" if is_ct else "T",
            "current_position": {"x": x, "y": y, "z": z},
            "predictions": pred_path,
            "action": action,
            "action_probs": action_probs,
            "confidence": conf,
            "current_zone": current_zone,
            "predicted_zone": next_zone,
            "objective_zone": objective_zone,
            "zone_path": zone_path,
        }

    # ── velocity estimation ─────────────────────────────────────

    def _estimate_velocity(
        self, steamid: str, tick: int, cx: float, cy: float,
    ) -> tuple[float, float, float]:
        """Multi-timescale velocity with recency weighting and outlier rejection."""
        cur = self._get_position(tick, steamid)
        if cur is None:
            return (0.0, 0.0, 0.0)

        estimates = []
        weights = []
        # Lookback windows: (ticks, weight)
        lookbacks = [(4, 0.40), (8, 0.30), (16, 0.20), (32, 0.10)]

        for lookback, weight in lookbacks:
            prev = self._get_position(tick - lookback, steamid)
            if prev is not None:
                vx = (cx - prev[0]) / lookback
                vy = (cy - prev[1]) / lookback
                estimates.append((vx, vy, weight))

        if not estimates:
            return (0.0, 0.0, 0.0)

        # Reject outliers: drop estimates more than 2 stddev from median
        if len(estimates) >= 3:
            speeds = [math.sqrt(e[0]**2 + e[1]**2) for e in estimates]
            median_speed = sorted(speeds)[len(speeds) // 2]
            filtered = []
            for e, s in zip(estimates, speeds):
                if median_speed < 0.5 or abs(s - median_speed) / max(median_speed, 0.1) < 2.5:
                    filtered.append(e)
            if filtered:
                estimates = filtered

        # Weighted average
        total_w = sum(e[2] for e in estimates)
        if total_w > 0:
            vel_x = sum(e[0] * e[2] for e in estimates) / total_w
            vel_y = sum(e[1] * e[2] for e in estimates) / total_w
        else:
            vel_x, vel_y = 0.0, 0.0

        speed = math.sqrt(vel_x**2 + vel_y**2)
        return (vel_x, vel_y, speed)

    # ── objective selection ─────────────────────────────────────

    def _determine_objective(
        self, current_zone: str | None, is_ct: bool,
        ct_alive: int, t_alive: int,
        vel_x: float, vel_y: float,
    ) -> str | None:
        """Determine the player's likely objective zone.

        T side: push toward the nearest bombsite
        CT side: defend between enemy spawn direction and bombsite
        """
        if current_zone is None:
            return None

        zone = self.zone_graph.zones.get(current_zone, {})

        if is_ct:
            # CT: if already at a bombsite, stay. Otherwise move to defend.
            if zone.get("is_bombsite"):
                return current_zone
            # Move toward the bombsite that T are likely heading toward
            # Simple heuristic: pick the bombsite farther from T spawn
            a_site = self.zone_graph.get_bombsite_zone("A")
            b_site = self.zone_graph.get_bombsite_zone("B")
            if a_site and b_site:
                # Prefer the site closer to current position (defend the nearest)
                a_path = self._find_path(current_zone, a_site)
                b_path = self._find_path(current_zone, b_site)
                if len(a_path) <= len(b_path):
                    return a_site
                return b_site
            return a_site or b_site
        else:
            # T: push toward a bombsite
            # If already on a bombsite, hold
            if zone.get("is_bombsite"):
                return current_zone
            # Pick the bombsite we're moving toward
            a_site = self.zone_graph.get_bombsite_zone("A")
            b_site = self.zone_graph.get_bombsite_zone("B")
            if a_site and b_site:
                a_center = self.zone_graph._get_zone_center(a_site)
                b_center = self.zone_graph._get_zone_center(b_site)
                if a_center and b_center and self._df is not None:
                    # Use velocity alignment
                    try:
                        tick_data = self._df.loc[self._df.index[0]]
                    except Exception:
                        pass
                    # Simple: pick the closer bombsite
                    # Get current position from zone center
                    cc = self.zone_graph._get_zone_center(current_zone)
                    if cc:
                        dist_a = math.hypot(a_center[0] - cc[0], a_center[1] - cc[1])
                        dist_b = math.hypot(b_center[0] - cc[0], b_center[1] - cc[1])
                        # Velocity-weighted: prefer the site we're moving toward
                        if abs(vel_x) + abs(vel_y) > 0.5:
                            dot_a = vel_x * (a_center[0] - cc[0]) + vel_y * (a_center[1] - cc[1])
                            dot_b = vel_x * (b_center[0] - cc[0]) + vel_y * (b_center[1] - cc[1])
                            if dot_a > dot_b:
                                return a_site
                            return b_site
                        return a_site if dist_a < dist_b else b_site
                return a_site
            return a_site or b_site

    # ── pathfinding through zone graph ──────────────────────────

    def _find_path(self, start: str | None, end: str | None) -> list[str]:
        """BFS shortest path through zone adjacency graph."""
        if start is None or end is None:
            return []
        if start == end:
            return [start]

        cache_key = (start, end)
        if cache_key in self._zone_paths:
            return self._zone_paths[cache_key]

        # BFS
        queue = deque([[start]])
        visited = {start}

        while queue:
            path = queue.popleft()
            current = path[-1]

            zone = self.zone_graph.zones.get(current, {})
            for adj in zone.get("adjacent", []):
                if adj == end:
                    result = path + [end]
                    self._zone_paths[cache_key] = result
                    return result
                if adj not in visited:
                    visited.add(adj)
                    queue.append(path + [adj])

        # No path found
        self._zone_paths[cache_key] = [start]
        return [start]

    # ── position prediction ─────────────────────────────────────

    def _generate_path(
        self, x: float, y: float, z: float,
        vel_x: float, vel_y: float, tick: int,
        current_zone: str | None,
        zone_path: list[str],
        objective_zone: str | None,
    ) -> list[dict]:
        """Generate predicted positions blending velocity and zone-path awareness.

        Short-term (+1s): pure velocity extrapolation
        Medium-term (+2s): blend velocity with zone center pull
        Long-term (+3s): pull toward objective zone center
        """
        preds = []
        speed = math.sqrt(vel_x**2 + vel_y**2)

        for i, horizon in enumerate(self.HORIZONS):
            # Velocity damping (player slows over time)
            damping = max(0.15, 1.0 - (i * 0.30))
            vx_damped = vel_x * damping
            vy_damped = vel_y * damping

            px = x + vx_damped * horizon
            py = y + vy_damped * horizon

            # Zone-aware adjustment: pull toward next zone centers
            zone_pull = 0.0
            if zone_path and len(zone_path) > 1:
                # Determine which zone in the path we'd be at by this horizon
                zone_idx = min(i + 1, len(zone_path) - 1)
                target_zone_id = zone_path[zone_idx]
                center = self.zone_graph._get_zone_center(target_zone_id)
                if center:
                    # Pull strength increases with horizon
                    zone_pull = 0.15 * (1 + i)
                    dx = center[0] - px
                    dy = center[1] - py
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 1:
                        pull_strength = zone_pull * max(speed, 1.0)
                        px += (dx / dist) * pull_strength * horizon
                        py += (dy / dist) * pull_strength * horizon

            # Objective pull: long-term bias toward objective
            if objective_zone and i >= 1:
                obj_center = self.zone_graph._get_zone_center(objective_zone)
                if obj_center:
                    obj_pull = 0.05 * i
                    dx = obj_center[0] - px
                    dy = obj_center[1] - py
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 1:
                        px += (dx / dist) * obj_pull * horizon * max(speed, 0.5)
                        py += (dy / dist) * obj_pull * horizon * max(speed, 0.5)

            preds.append({
                "horizon": self.HORIZON_LABELS[i],
                "tick": tick + horizon,
                "x": round(px, 1),
                "y": round(py, 1),
                "z": round(z, 1),
            })

        return preds

    # ── action classification ───────────────────────────────────

    def _classify_action(
        self, steamid: str, tick: int,
        vel_x: float, vel_y: float, speed: float,
        current_zone: str | None,
        next_zone: str | None,
        objective_zone: str | None,
        is_ct: bool,
    ) -> tuple[str, dict[str, float]]:
        """Classify player action with zone-aware context."""
        probs = {"holding": 0.0, "pushing": 0.0, "rotating": 0.0, "falling_back": 0.0}

        # Stationary / very slow
        if speed < self.HOLDING_SPEED_THRESHOLD:
            probs["holding"] = 0.75
            probs["pushing"] = 0.10
            probs["rotating"] = 0.10
            probs["falling_back"] = 0.05
            return (self.ACTION_HOLDING, probs)

        # Check movement relative to objective
        cur = self._get_position(tick, steamid)
        fut = self._get_position(tick + 64, steamid)

        if cur is not None and fut is not None:
            cx, cy = cur[0], cur[1]
            fx, fy = fut[0], fut[1]
            disp = math.sqrt((fx - cx)**2 + (fy - cy)**2)

            # Determine if moving toward objective or spawn
            moving_to_obj = False
            moving_to_spawn = False
            if objective_zone:
                obj_center = self.zone_graph._get_zone_center(objective_zone)
                if obj_center:
                    d_start = math.hypot(obj_center[0] - cx, obj_center[1] - cy)
                    d_end = math.hypot(obj_center[0] - fx, obj_center[1] - fy)
                    moving_to_obj = d_end < d_start

            spawn_zone = self.zone_graph.get_spawn_zone(is_ct)
            if spawn_zone:
                spawn_center = self.zone_graph._get_zone_center(spawn_zone)
                if spawn_center:
                    d_start = math.hypot(spawn_center[0] - cx, spawn_center[1] - cy)
                    d_end = math.hypot(spawn_center[0] - fx, spawn_center[1] - fy)
                    moving_to_spawn = d_end < d_start

            # Direction change check (rotation)
            mid = self._get_position(tick + 32, steamid)
            direction_changed = False
            if mid is not None:
                angle1 = math.atan2(mid[1] - cy, mid[0] - cx)
                angle2 = math.atan2(fy - mid[1], fx - mid[0])
                diff = abs(angle2 - angle1)
                if diff > math.pi:
                    diff = 2 * math.pi - diff
                direction_changed = diff > self.ROTATING_DIR_CHANGE_MIN

            # Zone change check
            zone_changing = current_zone != next_zone and next_zone is not None

            if moving_to_spawn and disp > self.FALLING_BACK_DISPLACEMENT_MIN:
                probs["falling_back"] = 0.65
                probs["holding"] = 0.05
                probs["pushing"] = 0.10
                probs["rotating"] = 0.20
                return (self.ACTION_FALLING_BACK, probs)

            if direction_changed and disp > self.PUSHING_DISPLACEMENT_MIN:
                probs["rotating"] = 0.60
                probs["pushing"] = 0.20
                probs["holding"] = 0.10
                probs["falling_back"] = 0.10
                return (self.ACTION_ROTATING, probs)

            if moving_to_obj and disp > self.PUSHING_DISPLACEMENT_MIN:
                probs["pushing"] = 0.65
                probs["rotating"] = 0.15
                probs["holding"] = 0.10
                probs["falling_back"] = 0.10
                return (self.ACTION_PUSHING, probs)

            if zone_changing and disp > self.PUSHING_DISPLACEMENT_MIN:
                probs["pushing"] = 0.55
                probs["rotating"] = 0.20
                probs["holding"] = 0.15
                probs["falling_back"] = 0.10
                return (self.ACTION_PUSHING, probs)

            if disp < self.FALLING_BACK_DISPLACEMENT_MIN:
                probs["holding"] = 0.70
                probs["pushing"] = 0.15
                probs["rotating"] = 0.10
                probs["falling_back"] = 0.05
                return (self.ACTION_HOLDING, probs)

        # Default: pushing if moving, holding if slow
        if speed > 1.5:
            probs["pushing"] = 0.45
            probs["rotating"] = 0.25
            probs["holding"] = 0.20
            probs["falling_back"] = 0.10
            return (self.ACTION_PUSHING, probs)
        else:
            probs["holding"] = 0.65
            probs["pushing"] = 0.15
            probs["rotating"] = 0.10
            probs["falling_back"] = 0.10
            return (self.ACTION_HOLDING, probs)

    # ── confidence scoring ──────────────────────────────────────

    def _compute_confidence(
        self, speed: float,
        current_zone: str | None,
        next_zone: str | None,
        objective_zone: str | None,
        action: str,
        zone_path: list[str],
    ) -> float:
        """Compute prediction confidence (0.0-1.0)."""
        conf = 0.45  # base confidence

        # Higher speed = more predictable direction
        if speed > 3.0:
            conf += 0.15
        elif speed > 1.5:
            conf += 0.10
        elif speed < 0.3:
            conf += 0.05  # stationary is easy to predict

        # Zone path exists and is clear
        if len(zone_path) >= 3:
            conf += 0.12
        elif len(zone_path) >= 2:
            conf += 0.06

        # Clear objective
        if objective_zone and objective_zone == next_zone:
            conf += 0.08

        # Action-specific adjustments
        if action == self.ACTION_HOLDING:
            conf += 0.08
        elif action == self.ACTION_FALLING_BACK:
            conf -= 0.05
        elif action == self.ACTION_PUSHING and zone_path and len(zone_path) >= 2:
            conf += 0.05

        # Zone change gives more certainty
        if next_zone and next_zone != current_zone:
            conf += 0.05

        return round(min(0.95, max(0.25, conf)), 2)

    # ── DataFrame helpers ───────────────────────────────────────

    def _get_position(self, tick: int, steamid: str) -> tuple | None:
        """O(log N) position lookup using indexed DataFrame."""
        df = self._df
        if df is None:
            return None
        try:
            tick_data = df.loc[tick]
        except KeyError:
            return None
        if isinstance(tick_data, pd.Series):
            tick_data = tick_data.to_frame().T
        match = tick_data[tick_data['steamid'].astype(str) == str(steamid)]
        if match.empty:
            return None
        row = match.iloc[0]
        return (
            float(row['X']), float(row['Y']),
            float(row.get('Z', 0)),
            bool(row.get('is_alive', True)),
            str(row.get('team_name', '')),
            str(row.get('name', 'Unknown')),
        )

    def _get_player_name(self, steamid: str, tick: int) -> str:
        """Get player name from DataFrame."""
        pos = self._get_position(tick, steamid)
        if pos:
            return pos[5]
        return "Unknown"
