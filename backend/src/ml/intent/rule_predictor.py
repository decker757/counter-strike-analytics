"""Rule-based intent predictor — predicts player movement and actions without ML.

Uses the indexed DataFrame for O(1) tick lookups instead of
O(N) cache iteration or DataFrame scans.
"""

import math
from typing import Optional

import numpy as np
import pandas as pd


class RuleBasedIntentPredictor:
    """Predicts player intent using velocity extrapolation and zone graph.

    No ML, no training — predictions are computed live from parsed tick data.
    Uses the indexed DataFrame directly for O(log N) position lookups.
    """

    TEAM_CT = "CT"
    TEAM_T = "TERRORIST"

    ACTION_HOLDING = "holding"
    ACTION_PUSHING = "pushing"
    ACTION_ROTATING = "rotating"
    ACTION_FALLING_BACK = "falling_back"

    HOLDING_SPEED_THRESHOLD = 1.5
    PUSHING_DISPLACEMENT_MIN = 200
    ROTATING_DIR_CHANGE_MIN = math.radians(60)
    FALLING_BACK_DISPLACEMENT_MIN = 150

    HORIZONS = [64, 128, 192]

    def __init__(self, map_name: str):
        clean_name = map_name.replace("de_", "")
        self.map_name = f"de_{clean_name}"
        from .zone_graph import MapZoneGraph
        self.zone_graph = MapZoneGraph(self.map_name)

        # Reference to the indexed DataFrame (set on first predict call)
        self._df: pd.DataFrame | None = None

    def _get_position(self, tick: int, steamid: str) -> tuple | None:
        """O(log N) position lookup using indexed DataFrame (was O(1) dict lookup
        but with huge memory overhead and slow build time)."""
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

    def predict(
        self, tick: int, df: pd.DataFrame,
        team_filter: str = "", steamid_filter: str = "",
    ) -> dict:
        """Predict intent for alive players at a given tick.

        Uses O(1) indexed DataFrame lookup instead of O(N) cache iteration.
        """
        # Store reference to indexed DataFrame
        self._df = df

        # O(1) index lookup to find all players at this tick (was O(N) cache iteration)
        try:
            tick_data = df.loc[tick]
        except KeyError:
            return {"tick": tick, "players": []}
        if isinstance(tick_data, pd.Series):
            tick_data = tick_data.to_frame().T

        # Filter to alive players
        alive = tick_data[tick_data['is_alive'] == True]
        if team_filter:
            alive = alive[alive['team_name'] == team_filter]
        if steamid_filter:
            alive = alive[alive['steamid'].astype(str) == steamid_filter]

        if alive.empty:
            return {"tick": tick, "players": []}

        # Count teams for zone-aware predictions
        ct_alive = int((alive['team_name'] == self.TEAM_CT).sum())
        t_alive = int((alive['team_name'] == self.TEAM_T).sum())

        predictions = []
        for _, p in alive.iterrows():
            sid = str(p['steamid'])
            x, y, z = float(p['X']), float(p['Y']), float(p.get('Z', 0))
            is_ct = p['team_name'] == self.TEAM_CT

            vel_x, vel_y = self._compute_velocity_fast(sid, tick)
            current_zone = self.zone_graph.get_zone(x, y)
            next_zone = self.zone_graph.predict_next_zone(
                current_zone, vel_x, vel_y, ct_alive, t_alive, is_ct
            )
            pred_path = self._extrapolate_path(
                x, y, z, vel_x, vel_y, tick, current_zone, next_zone
            )
            action, _ = self._classify_action_fast(
                sid, tick, vel_x, vel_y, current_zone, is_ct
            )
            speed = math.sqrt(vel_x ** 2 + vel_y ** 2)
            conf = self._compute_confidence(speed, current_zone, next_zone, action)

            action_probs = {"holding": 0.1, "pushing": 0.1, "rotating": 0.1, "falling_back": 0.1}
            action_probs[action] = 0.7

            predictions.append({
                "steamid": sid,
                "name": p.get('name', 'Unknown'),
                "team": "CT" if is_ct else "T",
                "current_position": {"x": x, "y": y, "z": z},
                "predictions": pred_path,
                "action": action,
                "action_probs": action_probs,
                "confidence": conf,
                "current_zone": current_zone,
                "predicted_zone": next_zone,
            })

        return {"tick": tick, "players": predictions}

    def _compute_velocity_fast(self, steamid: str, tick: int) -> tuple[float, float]:
        """Fast velocity using indexed DataFrame lookups (no cache needed)."""
        cur = self._get_position(tick, steamid)
        if cur is None:
            return (0.0, 0.0)
        cx, cy = cur[0], cur[1]

        vel_x_total = 0.0
        vel_y_total = 0.0
        weight_sum = 0.0

        lookbacks = [(4, 0.5), (8, 0.3), (16, 0.15), (32, 0.05)]
        for lookback, weight in lookbacks:
            prev = self._get_position(tick - lookback, steamid)
            if prev is not None:
                vel_x_total += weight * (cx - prev[0]) / lookback
                vel_y_total += weight * (cy - prev[1]) / lookback
                weight_sum += weight

        if weight_sum > 0:
            return (vel_x_total / weight_sum, vel_y_total / weight_sum)
        return (0.0, 0.0)

    def _classify_action_fast(
        self, steamid: str, tick: int,
        vel_x: float, vel_y: float,
        current_zone: Optional[str], is_ct: bool,
    ) -> tuple[str, float]:
        """Classify action using indexed DataFrame lookups."""
        speed = math.sqrt(vel_x ** 2 + vel_y ** 2)

        if speed < self.HOLDING_SPEED_THRESHOLD:
            return (self.ACTION_HOLDING, 0.7)

        cur = self._get_position(tick, steamid)
        fut = self._get_position(tick + 64, steamid)
        if cur is None or fut is None:
            return (self.ACTION_PUSHING, 0.5) if speed > 1.5 else (self.ACTION_HOLDING, 0.5)

        cx, cy = cur[0], cur[1]
        fx, fy = fut[0], fut[1]
        disp = math.sqrt((fx - cx) ** 2 + (fy - cy) ** 2)

        spawn_zone = self.zone_graph.get_spawn_zone(not is_ct)
        own_spawn = self.zone_graph.get_spawn_zone(is_ct)

        moving_toward_enemy = self._is_moving_toward(cx, cy, fx, fy, spawn_zone)
        moving_toward_own = self._is_moving_toward(cx, cy, fx, fy, own_spawn)

        # Rotation check
        mid = self._get_position(tick + 32, steamid)
        direction_changed = False
        if mid is not None:
            angle1 = math.atan2(mid[1] - cy, mid[0] - cx)
            angle2 = math.atan2(fy - mid[1], fx - mid[0])
            angle_diff = abs(angle2 - angle1)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            direction_changed = angle_diff > self.ROTATING_DIR_CHANGE_MIN

        if disp < self.FALLING_BACK_DISPLACEMENT_MIN:
            return (self.ACTION_HOLDING, 0.7)
        if moving_toward_own and disp > self.FALLING_BACK_DISPLACEMENT_MIN:
            return (self.ACTION_FALLING_BACK, 0.65)
        if direction_changed and disp > self.PUSHING_DISPLACEMENT_MIN:
            return (self.ACTION_ROTATING, 0.6)
        if moving_toward_enemy and disp > self.PUSHING_DISPLACEMENT_MIN:
            return (self.ACTION_PUSHING, 0.65)
        return (self.ACTION_PUSHING, 0.5)

    def _is_moving_toward(self, cx, cy, fx, fy, target_zone) -> bool:
        if target_zone is None:
            return False
        center = self.zone_graph._get_zone_center(target_zone)
        if center is None:
            return False
        start_dist = math.sqrt((center[0] - cx) ** 2 + (center[1] - cy) ** 2)
        end_dist = math.sqrt((center[0] - fx) ** 2 + (center[1] - fy) ** 2)
        return end_dist < start_dist

    def _extrapolate_path(
        self, x, y, z, vel_x, vel_y, tick, current_zone, next_zone,
    ) -> list[dict]:
        predictions = []
        labels = ["+1s", "+2s", "+3s"]
        for i, horizon in enumerate(self.HORIZONS):
            damping = 1.0 - (i * 0.25)
            adj_vel_x = vel_x * damping
            adj_vel_y = vel_y * damping

            if next_zone and next_zone != current_zone:
                center = self.zone_graph._get_zone_center(next_zone)
                if center:
                    pull = 0.15 * (1 + i)
                    dx = center[0] - x
                    dy = center[1] - y
                    dist = math.sqrt(dx ** 2 + dy ** 2)
                    if dist > 1:
                        adj_vel_x += pull * (dx / dist) * abs(vel_x)
                        adj_vel_y += pull * (dy / dist) * abs(vel_y)

            predictions.append({
                "horizon": labels[i],
                "tick": tick + horizon,
                "x": round(x + adj_vel_x * horizon, 1),
                "y": round(y + adj_vel_y * horizon, 1),
                "z": round(z, 1),
            })
        return predictions

    def _compute_confidence(self, speed, current_zone, next_zone, action) -> float:
        conf = 0.5
        if speed > 2.0:
            conf += 0.15
        elif speed < 0.5:
            conf += 0.1
        if next_zone and next_zone != current_zone:
            conf += 0.1
        if action == self.ACTION_HOLDING:
            conf += 0.1
        elif action == self.ACTION_FALLING_BACK:
            conf -= 0.05
        return round(min(0.95, max(0.3, conf)), 2)
