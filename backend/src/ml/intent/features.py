"""Feature extraction for tick-level intent prediction.

Calls demoparser2 directly with extended fields (35+) not used by the
existing DemoParser. Builds normalized feature vectors and sliding
time-windows for sequence model training.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from demoparser2 import DemoParser as RawDemoParser


# Extended fields for intent prediction — 37 fields covering
# position, orientation, movement, combat state, perception, game context.
# These are ALL available from demoparser2 but NOT extracted by the
# existing DemoParser's PLAYER_FIELDS (which only has 16 fields).
INTENT_FIELDS = [
    # Position
    "tick", "steamid", "name", "team_name",
    "X", "Y", "Z",
    # Orientation
    "pitch", "yaw",
    # Velocity (components)
    "velocity_X", "velocity_Y", "velocity_Z",
    # Alive/health
    "is_alive", "health",
    # Weapon state
    "active_weapon_name",
    "is_scoped", "zoom_lvl",
    "is_in_reload", "shots_fired", "accuracy_penalty",
    # Movement state
    "is_walking", "stamina",
    # Objective state
    "is_defusing", "in_bomb_zone", "which_bomb_zone",
    # Perception
    "flash_duration", "flash_max_alpha",
    # Game context (shared across all players)
    "game_phase", "is_freeze_period", "is_bomb_planted",
    "num_player_alive_ct", "num_player_alive_t",
    # Button states (7 primary buttons)
    "FORWARD", "LEFT", "RIGHT", "BACK",
    "FIRE", "RELOAD", "WALK",
]

# Feature dimension after encoding
FEATURE_DIM = 50

# Weapon category mapping (active_weapon_name → category index)
WEAPON_CATEGORIES = {
    # Pistols
    "usp_silencer": 0, "hkp2000": 0, "glock": 0, "p250": 0,
    "deagle": 0, "elite": 0, "fiveseven": 0, "tec9": 0,
    "cz75a": 0, "revolver": 0,
    # SMGs
    "mp9": 1, "mac10": 1, "mp7": 1, "mp5sd": 1,
    "ump45": 1, "p90": 1, "bizon": 1,
    # Rifles
    "ak47": 2, "m4a1_silencer": 2, "m4a1": 2,
    "famas": 2, "galilar": 2, "sg556": 2, "aug": 2,
    "ssg08": 2,
    # Snipers
    "awp": 3, "scar20": 3, "g3sg1": 3,
    # Shotguns
    "nova": 4, "xm1014": 4, "mag7": 4, "sawedoff": 4,
    # Heavy
    "m249": 5, "negev": 5,
    # Grenades
    "hegrenade": 6, "flashbang": 6, "smokegrenade": 6,
    "molotov": 6, "incgrenade": 6, "decoy": 6,
    # Knife/Other
    "knife": 7, "knife_t": 7, "taser": 7, "c4": 7,
}
NUM_WEAPON_CATS = 8  # 0-7

# Game phase mapping
GAME_PHASE_MAP = {
    "freezetime": 0,
    "live": 1,
    "warmup": 2,
    "intermission": 3,
}


class IntentFeatureExtractor:
    """Extracts and normalizes features for tick-level intent prediction.

    Uses raw demoparser2 (NOT the project's DemoParser) to access the
    full 170+ field set. Builds preprocessed DataFrames and sliding
    window sequences for training and inference.
    """

    def __init__(self, demo_path: str | Path):
        """Initialize with a demo file path.

        Args:
            demo_path: Path to a CS2 .dem file
        """
        self.demo_path = Path(demo_path)
        self.scaler_stats: dict[str, dict] = {}

    def parse(self) -> pd.DataFrame:
        """Parse the demo with extended intent fields.

        Returns:
            Raw DataFrame with 37 columns from demoparser2
        """
        parser = RawDemoParser(str(self.demo_path))
        df = pd.DataFrame(parser.parse_ticks(INTENT_FIELDS))
        print(f"IntentFeatureExtractor: parsed {len(df)} rows "
              f"({len(df['tick'].unique())} ticks, "
              f"{len(df['steamid'].unique())} players)")
        return df

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize and encode raw fields into a numerical feature matrix.

        Args:
            df: Raw DataFrame from parse()

        Returns:
            Preprocessed DataFrame with FEATURE_DIM numerical columns,
            indexed by (tick, steamid)
        """
        result = df.copy()

        # --- Continuous features (scale to [0,1] or standardize) ---

        # X, Y: center and scale per map
        x_center = result["X"].median()
        y_center = result["Y"].median()
        x_scale = result["X"].std() or 1.0
        y_scale = result["Y"].std() or 1.0
        result["feat_x"] = (result["X"] - x_center) / x_scale
        result["feat_y"] = (result["Y"] - y_center) / y_scale
        result["feat_z"] = result["Z"] / 200.0  # Z rarely exceeds 200

        # Pitch: -89 to 89 degrees → [-1, 1]; yaw: -180 to 180 → [-1, 1]
        result["feat_pitch"] = result["pitch"].fillna(0).clip(-89, 89) / 89.0
        result["feat_yaw"] = result["yaw"].fillna(0).clip(-180, 180) / 180.0

        # Velocity: scale by max observed
        vel_max = max(
            result["velocity_X"].abs().max() or 1,
            result["velocity_Y"].abs().max() or 1,
            result["velocity_Z"].abs().max() or 1,
            1.0,
        )
        result["feat_vel_x"] = result["velocity_X"].fillna(0) / vel_max
        result["feat_vel_y"] = result["velocity_Y"].fillna(0) / vel_max
        result["feat_vel_z"] = result["velocity_Z"].fillna(0) / vel_max

        # Health: 0-100
        result["feat_health"] = result["health"].fillna(0).clip(0, 100) / 100.0

        # Stamina: 0-100
        result["feat_stamina"] = result["stamina"].fillna(0).clip(0, 100) / 100.0

        # Flash: normalize by max alpha
        flash_max = result["flash_max_alpha"].max() or 255.0
        if flash_max < 1:
            flash_max = 255.0
        result["feat_flash"] = (
            result["flash_duration"].fillna(0).clip(0, flash_max) / flash_max
        )

        # Accuracy penalty: clip to reasonable range
        acc_max = result["accuracy_penalty"].max() or 1.0
        result["feat_accuracy"] = (
            result["accuracy_penalty"].fillna(0).clip(0, acc_max) / max(acc_max, 1)
        )

        # Shots fired: normalize
        shots_max = result["shots_fired"].max() or 1.0
        result["feat_shots_fired"] = (
            result["shots_fired"].fillna(0).clip(0, shots_max) / max(shots_max, 1.0)
        )

        # Zoom level: 0, 1, or 2 → [0, 1]
        result["feat_zoom"] = result["zoom_lvl"].fillna(0).clip(0, 2) / 2.0

        # --- Binary/boolean features ---
        result["feat_is_alive"] = result["is_alive"].astype(float)
        result["feat_team"] = (result["team_name"] == "CT").astype(float)
        result["feat_is_scoped"] = result["is_scoped"].fillna(0).astype(float)
        result["feat_is_reload"] = result["is_in_reload"].fillna(0).astype(float)
        result["feat_is_walking"] = result["is_walking"].fillna(0).astype(float)
        result["feat_is_defusing"] = result["is_defusing"].fillna(0).astype(float)
        result["feat_in_bomb_zone"] = result["in_bomb_zone"].fillna(0).astype(float)
        result["feat_bomb_planted"] = result["is_bomb_planted"].fillna(0).astype(float)
        result["feat_freeze"] = result["is_freeze_period"].fillna(0).astype(float)

        # Button states (7 bools)
        for btn in ["FORWARD", "LEFT", "RIGHT", "BACK", "FIRE", "RELOAD", "WALK"]:
            col = f"feat_btn_{btn.lower()}"
            result[col] = result[btn].fillna(0).astype(float)

        # --- Categorical features ---

        # Weapon category: one-hot into 8 columns
        weapon_cat = result["active_weapon_name"].fillna("unknown").apply(
            lambda w: WEAPON_CATEGORIES.get(w.lower() if isinstance(w, str) else "unknown", 7)
        )
        for c in range(NUM_WEAPON_CATS):
            result[f"feat_weapon_{c}"] = (weapon_cat == c).astype(float)

        # Bomb zone: 0=none, 1=A, 2=B → [0, 1]
        result["feat_bomb_zone"] = (
            result["which_bomb_zone"].fillna(0).clip(0, 2) / 2.0
        )

        # Game phase: map string to ordinal
        result["feat_game_phase"] = (
            result["game_phase"]
            .fillna("live")
            .apply(lambda g: GAME_PHASE_MAP.get(str(g).lower(), 1))
            / 3.0
        )

        # Player counts: normalize by 5
        result["feat_alive_ct"] = (
            result["num_player_alive_ct"].fillna(5).clip(0, 5) / 5.0
        )
        result["feat_alive_t"] = (
            result["num_player_alive_t"].fillna(5).clip(0, 5) / 5.0
        )

        # --- Store scaler stats for inference ---
        self.scaler_stats = {
            "x_center": x_center,
            "y_center": y_center,
            "x_scale": x_scale,
            "y_scale": y_scale,
            "vel_max": vel_max,
            "flash_max": flash_max,
            "acc_max": acc_max,
            "shots_max": shots_max,
        }

        # Select only the feature columns
        feat_cols = [c for c in result.columns if c.startswith("feat_")]
        return result[["tick", "steamid", "name", "team_name", "X", "Y", "Z",
                        "is_alive"] + feat_cols]

    def build_sequence(
        self,
        df: pd.DataFrame,
        steamid: str,
        tick: int,
        window: int = 32,
    ) -> np.ndarray | None:
        """Build a time-windowed feature sequence for one player.

        Extracts rows [tick - window + 1, tick] for the given player
        and returns a (window, feature_dim) numpy array.

        Args:
            df: Preprocessed DataFrame from preprocess()
            steamid: Player's SteamID
            tick: Current tick
            window: Number of ticks in the sequence window

        Returns:
            (window, FEATURE_DIM) array, or None if insufficient history
        """
        player_df = df[df["steamid"].astype(str) == str(steamid)]
        if player_df.empty:
            return None

        # Get the feature columns
        feat_cols = [c for c in df.columns if c.startswith("feat_")]

        # Find the tick index
        player_df = player_df.sort_values("tick")
        idx = player_df["tick"].searchsorted(tick)
        if idx < window:
            return None  # Not enough history

        start_idx = idx - window + 1
        end_idx = idx + 1  # inclusive of tick
        window_df = player_df.iloc[start_idx:end_idx]

        if len(window_df) < window // 2:
            return None  # Too sparse

        # Pad or truncate to exactly window ticks
        features = window_df[feat_cols].values.astype(np.float32)
        if len(features) < window:
            # Pad at the start with the first frame's values
            pad = np.tile(features[0], (window - len(features), 1))
            features = np.vstack([pad, features])

        return features[-window:]  # ensure exactly window


def parse_and_preprocess(demo_path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Convenience: parse a demo and return preprocessed DataFrame + scaler stats.

    Args:
        demo_path: Path to demo file

    Returns:
        (preprocessed_df, scaler_stats_dict)
    """
    extractor = IntentFeatureExtractor(demo_path)
    raw_df = extractor.parse()
    preprocessed = extractor.preprocess(raw_df)
    return preprocessed, extractor.scaler_stats
