"""Self-supervised label generation for intent prediction.

Generates training labels from trajectory geometry WITHOUT manual labeling:
- Position labels: future (dx, dy, dz) at +1s, +2s, +3s horizons
- Action labels: tactical action classification from displacement patterns
"""

import math
from typing import Optional

import numpy as np
import pandas as pd


class IntentLabeler:
    """Generates self-supervised training labels for intent prediction.

    Labels are derived from observing what the player ACTUALLY did
    in the future ticks after the prediction point. No human labeling needed.
    """

    # Action classes
    ACTION_HOLDING = 0
    ACTION_PUSHING = 1
    ACTION_ROTATING = 2
    ACTION_FALLING_BACK = 3
    NUM_ACTIONS = 4

    # Classification thresholds (game units at CS2 scale)
    HOLDING_MAX_DISPLACEMENT = 100    # max displacement in 2s to be "holding"
    PUSHING_MIN_DISPLACEMENT = 200    # min displacement toward enemy to be "pushing"
    FALLING_BACK_MIN_DISPLACEMENT = 150  # min displacement toward own spawn
    ROTATING_ANGLE_MIN = math.radians(60)  # min direction change for rotation
    ROTATING_MIN_DISPLACEMENT = 250

    def __init__(self, ct_spawn_center: tuple[float, float] = (1800, 2200),
                 t_spawn_center: tuple[float, float] = (-50, -750)):
        """Initialize with spawn zone centers for territory awareness.

        Args:
            ct_spawn_center: (x, y) center of CT spawn zone
            t_spawn_center: (x, y) center of T spawn zone
        """
        self.ct_spawn = ct_spawn_center
        self.t_spawn = t_spawn_center

    def get_position_labels(
        self,
        player_df: pd.DataFrame,
        tick: int,
        tickrate: int = 64,
    ) -> Optional[np.ndarray]:
        """Compute future position deltas as regression targets.

        Args:
            player_df: Per-player DataFrame sorted by tick
            tick: Current prediction tick
            tickrate: Server tickrate (default 64)

        Returns:
            Array of 9 floats: [dx_1s, dy_1s, dz_1s,
                                 dx_2s, dy_2s, dz_2s,
                                 dx_3s, dy_3s, dz_3s]
            Returns None if player dies before all horizons.
        """
        current = player_df[player_df["tick"] == tick]
        if current.empty:
            return None

        cx = float(current["X"].iloc[0])
        cy = float(current["Y"].iloc[0])
        cz = float(current["Z"].iloc[0])

        horizons = [tickrate, tickrate * 2, tickrate * 3]  # +1s, +2s, +3s
        deltas = []

        for h in horizons:
            future = player_df[player_df["tick"] == tick + h]
            if future.empty:
                return None  # player died or data missing

            # Check if still alive at this horizon
            if not future["is_alive"].iloc[0]:
                return None

            fx = float(future["X"].iloc[0])
            fy = float(future["Y"].iloc[0])
            fz = float(future["Z"].iloc[0])

            deltas.extend([fx - cx, fy - cy, fz - cz])

        return np.array(deltas, dtype=np.float32)

    def classify_action(
        self,
        player_df: pd.DataFrame,
        tick: int,
        is_ct: bool,
        tickrate: int = 64,
    ) -> int:
        """Classify tactical action from observed future trajectory.

        Examines the player's movement over [tick, tick + 2s] to
        determine what tactical action they were performing.

        Args:
            player_df: Per-player DataFrame
            tick: Current tick
            is_ct: Whether player is on CT team
            tickrate: Server tickrate

        Returns:
            Action class index (0=holding, 1=pushing, 2=rotating, 3=falling_back)
        """
        current = player_df[player_df["tick"] == tick]
        if current.empty:
            return self.ACTION_HOLDING

        cx = float(current["X"].iloc[0])
        cy = float(current["Y"].iloc[0])

        # Get position at mid-point and end of 2s window
        mid = player_df[player_df["tick"] == tick + tickrate]
        end = player_df[player_df["tick"] == tick + tickrate * 2]

        if end.empty:
            # Try shorter horizon
            end = player_df[player_df["tick"] == tick + tickrate]
            if end.empty:
                return self.ACTION_HOLDING
            ex = float(end["X"].iloc[0])
            ey = float(end["Y"].iloc[0])
            mx, my = (cx + ex) / 2, (cy + ey) / 2  # approximate mid
        else:
            ex = float(end["X"].iloc[0])
            ey = float(end["Y"].iloc[0])
            if not mid.empty:
                mx = float(mid["X"].iloc[0])
                my = float(mid["Y"].iloc[0])
            else:
                mx, my = (cx + ex) / 2, (cy + ey) / 2

        # Total displacement over 2s window
        total_disp = math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2)

        # Holding: barely moved
        if total_disp < self.HOLDING_MAX_DISPLACEMENT:
            return self.ACTION_HOLDING

        # Determine movement direction relative to spawns
        enemy_spawn = self.t_spawn if is_ct else self.ct_spawn
        own_spawn = self.ct_spawn if is_ct else self.t_spawn

        toward_enemy = self._moving_toward(cx, cy, ex, ey, enemy_spawn)
        toward_own = self._moving_toward(cx, cy, ex, ey, own_spawn)

        # Check for rotation (direction change between first and second half)
        angle1 = math.atan2(my - cy, mx - cx)
        angle2 = math.atan2(ey - my, ex - mx)
        angle_diff = abs(angle2 - angle1)
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff

        if angle_diff > self.ROTATING_ANGLE_MIN and total_disp > self.ROTATING_MIN_DISPLACEMENT:
            return self.ACTION_ROTATING

        # Falling back: moving toward own spawn
        if toward_own and total_disp > self.FALLING_BACK_MIN_DISPLACEMENT:
            return self.ACTION_FALLING_BACK

        # Pushing: moving toward enemy territory or moderate movement forward
        if toward_enemy and total_disp > self.PUSHING_MIN_DISPLACEMENT:
            return self.ACTION_PUSHING

        # Default: moderate movement, classify as pushing if moving, else holding
        if total_disp > self.HOLDING_MAX_DISPLACEMENT:
            return self.ACTION_PUSHING
        return self.ACTION_HOLDING

    def _moving_toward(
        self, cx: float, cy: float, fx: float, fy: float,
        target: tuple[float, float],
    ) -> bool:
        """Check if movement from (cx,cy) to (fx,fy) is toward a target point."""
        start_dist = math.sqrt((target[0] - cx) ** 2 + (target[1] - cy) ** 2)
        end_dist = math.sqrt((target[0] - fx) ** 2 + (target[1] - fy) ** 2)
        # Moving toward = getting closer to target
        return end_dist < start_dist

    def build_sample(
        self,
        player_df: pd.DataFrame,
        tick: int,
        is_ct: bool,
        tickrate: int = 64,
    ) -> Optional[dict]:
        """Generate a complete training sample at a given tick.

        Args:
            player_df: Per-player DataFrame
            tick: Current tick
            is_ct: Player team
            tickrate: Server tickrate

        Returns:
            {"pos_label": ndarray(9,), "action_label": int} or None
        """
        pos_label = self.get_position_labels(player_df, tick, tickrate)
        if pos_label is None:
            return None

        action_label = self.classify_action(player_df, tick, is_ct, tickrate)

        return {
            "pos_label": pos_label,
            "action_label": action_label,
        }
