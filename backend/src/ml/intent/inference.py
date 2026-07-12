"""Inference orchestrator for intent prediction.

Holds parsed data, trained model, and scaler in memory.
Provides lazy initialization (trains on first request, then caches).
Supports both ML and rule-based prediction modes.
"""

import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import torch

from .features import IntentFeatureExtractor, FEATURE_DIM
from .trainer import IntentTrainer, DEFAULT_MODEL_DIR
from .model import IntentTransformer


class IntentInference:
    """High-level orchestrator for ML-powered intent prediction.

    Usage:
        inference = IntentInference("data/demos/match.dem")
        inference.initialize()  # trains model on first call
        result = inference.predict(5000)  # batch inference for all players
    """

    # Action class names (must match IntentLabeler)
    ACTION_NAMES = ["holding", "pushing", "rotating", "falling_back"]

    def __init__(self, demo_path: str | Path):
        """Initialize inference engine.

        Args:
            demo_path: Path to CS2 demo file
        """
        self.demo_path = Path(demo_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Lazy-initialized state
        self._model: Optional[IntentTransformer] = None
        self._df: Optional[pd.DataFrame] = None
        self._feature_cols: list[str] = []
        self._is_trained = False
        self._training_time: float = 0.0
        self._training_metrics: dict = {}

    def initialize(self, force_retrain: bool = False) -> bool:
        """Initialize the model — train if needed, load if cached.

        Args:
            force_retrain: If True, retrain even if checkpoint exists

        Returns:
            True if model is ready for inference
        """
        # Check for cached checkpoint
        checkpoint_path = self._get_checkpoint_path()
        if checkpoint_path and checkpoint_path.exists() and not force_retrain:
            print(f"Loading cached model from {checkpoint_path}")
            model = IntentTrainer.load_checkpoint(checkpoint_path, self.device)
            if model is not None:
                self._model = model
                self._is_trained = True
                # Also need to parse for the DataFrame
                if self._df is None:
                    self._parse_and_preprocess()
                return True

        # Train the model
        print(f"Training intent model on {self.device}...")
        t0 = time.time()

        trainer = IntentTrainer(
            self.demo_path,
            device=self.device,
            batch_size=256,
        )

        try:
            self._model, self._training_metrics = trainer.train(
                epochs=30, verbose=True
            )
            self._feature_cols = trainer.feature_cols
            self._training_time = time.time() - t0
            self._is_trained = True

            # Save checkpoint
            trainer.save_checkpoint(self._model)
            print(f"Training completed in {self._training_time:.1f}s")

            return True
        except Exception as e:
            print(f"Training failed: {e}")
            self._is_trained = False
            return False

    def _parse_and_preprocess(self):
        """Parse demo and build preprocessed DataFrame for inference."""
        extractor = IntentFeatureExtractor(self.demo_path)
        raw_df = extractor.parse()
        self._df = extractor.preprocess(raw_df)
        self._feature_cols = [c for c in self._df.columns if c.startswith("feat_")]

    def _get_checkpoint_path(self) -> Optional[Path]:
        """Get expected checkpoint path for this demo."""
        import hashlib
        try:
            with open(self.demo_path, "rb") as f:
                file_head = f.read(65536)
            demo_hash = hashlib.md5(file_head).hexdigest()[:12]
            return DEFAULT_MODEL_DIR / f"intent_{demo_hash}.pt"
        except Exception:
            return None

    def predict(self, tick: int, df: Optional[pd.DataFrame] = None) -> dict:
        """Predict intent for all alive players at a given tick.

        Args:
            tick: Current game tick
            df: Optional raw DataFrame from position_analysis (used if ML not ready)

        Returns:
            Dict with 'tick' and 'players' list, same format as RuleBasedIntentPredictor
        """
        # Ensure parsed data is available
        if self._df is None:
            self._parse_and_preprocess()

        if self._df is None:
            return {"tick": tick, "players": [], "error": "No data available"}

        # Get alive players at this tick
        tick_data = self._df[self._df["tick"] == tick]
        if tick_data.empty:
            return {"tick": tick, "players": []}

        alive = tick_data[tick_data["is_alive"] == True]
        if alive.empty:
            return {"tick": tick, "players": []}

        predictions = []

        if self._is_trained and self._model is not None:
            # ML inference
            predictions = self._predict_ml(tick, alive)
        else:
            # Fall back to rule-based style prediction
            predictions = self._predict_fallback(tick, alive)

        return {"tick": tick, "players": predictions}

    def _predict_ml(self, tick: int, alive: pd.DataFrame) -> list[dict]:
        """Run ML model inference for alive players."""
        if self._df is None or self._model is None:
            return []

        feat_cols = self._feature_cols
        if not feat_cols:
            feat_cols = [c for c in self._df.columns if c.startswith("feat_")]

        sequences = []
        players_info = []

        for _, player in alive.iterrows():
            steamid = str(player["steamid"])
            player_df = self._df[self._df["steamid"] == steamid].sort_values("tick")

            # Build sequence
            idx = player_df["tick"].searchsorted(tick)
            if idx < 32:
                continue

            start_idx = idx - 31
            end_idx = idx + 1
            window_df = player_df.iloc[start_idx:end_idx]

            if len(window_df) < 16:
                continue

            features = window_df[feat_cols].values.astype(np.float32)
            if len(features) < 32:
                pad = np.tile(features[0], (32 - len(features), 1))
                features = np.vstack([pad, features])
            features = features[-32:]

            sequences.append(features)
            players_info.append({
                "steamid": steamid,
                "name": player.get("name", "Unknown"),
                "team": "CT" if player.get("team_name") == "CT" else "T",
                "x": float(player["X"]),
                "y": float(player["Y"]),
                "z": float(player.get("Z", 0)),
            })

        if not sequences:
            return []

        # Batch inference
        batch = torch.from_numpy(np.stack(sequences)).float().to(self.device)
        pos_deltas, action_probs, confidence = self._model.predict(batch)

        pos_deltas = pos_deltas.cpu().numpy()
        action_probs = action_probs.cpu().numpy()
        confidence = confidence.cpu().numpy()

        results = []
        tickrate = 64
        horizons = [("+1s", tickrate), ("+2s", tickrate * 2), ("+3s", tickrate * 3)]

        for i, info in enumerate(players_info):
            # Build predicted path from deltas
            pred_path = []
            for j, (label, h) in enumerate(horizons):
                pred_path.append({
                    "horizon": label,
                    "tick": tick + h,
                    "x": round(info["x"] + float(pos_deltas[i, j * 3]), 1),
                    "y": round(info["y"] + float(pos_deltas[i, j * 3 + 1]), 1),
                    "z": round(info["z"] + float(pos_deltas[i, j * 3 + 2]), 1),
                })

            # Action probabilities
            action_idx = int(np.argmax(action_probs[i]))
            probs_dict = {
                self.ACTION_NAMES[k]: float(action_probs[i, k])
                for k in range(len(self.ACTION_NAMES))
            }

            results.append({
                "steamid": info["steamid"],
                "name": info["name"],
                "team": info["team"],
                "current_position": {"x": info["x"], "y": info["y"], "z": info["z"]},
                "predictions": pred_path,
                "action": self.ACTION_NAMES[action_idx],
                "action_probs": probs_dict,
                "confidence": round(float(confidence[i]), 2),
                "current_zone": None,
                "predicted_zone": None,
            })

        return results

    def _predict_fallback(self, tick: int, alive: pd.DataFrame) -> list[dict]:
        """Fallback prediction when ML model isn't trained.

        Uses simple velocity extrapolation without zone awareness.
        """
        results = []
        for _, player in alive.iterrows():
            steamid = str(player["steamid"])
            x = float(player["X"])
            y = float(player["Y"])
            z = float(player.get("Z", 0))

            # Simple extrapolation: use velocity if available
            vel_x = float(player.get("velocity_X", 0) or 0)
            vel_y = float(player.get("velocity_Y", 0) or 0)

            # If no velocity data, try to compute from position features
            if abs(vel_x) < 0.01 and abs(vel_y) < 0.01:
                vel_x = float(player.get("feat_vel_x", 0) or 0) * 100
                vel_y = float(player.get("feat_vel_y", 0) or 0) * 100

            tickrate = 64
            pred_path = []
            for h_label, h in [("+1s", tickrate), ("+2s", tickrate * 2), ("+3s", tickrate * 3)]:
                damping = 1.0 - (h / (tickrate * 3)) * 0.5
                pred_path.append({
                    "horizon": h_label,
                    "tick": tick + h,
                    "x": round(x + vel_x * h * damping, 1),
                    "y": round(y + vel_y * h * damping, 1),
                    "z": round(z, 1),
                })

            results.append({
                "steamid": steamid,
                "name": player.get("name", "Unknown"),
                "team": "CT" if player.get("team_name") == "CT" else "T",
                "current_position": {"x": x, "y": y, "z": z},
                "predictions": pred_path,
                "action": "holding",
                "action_probs": {"holding": 0.7, "pushing": 0.1, "rotating": 0.1, "falling_back": 0.1},
                "confidence": 0.3,
                "current_zone": None,
                "predicted_zone": None,
            })

        return results

    @property
    def model_info(self) -> dict:
        """Return information about the current model."""
        if self._is_trained and self._model is not None:
            return {
                "mode": "ml",
                "status": "trained",
                "model_type": "IntentTransformer",
                "num_params": self._model.num_params,
                "device": self.device,
                "training_time_seconds": round(self._training_time, 1),
                "val_loss": round(self._training_metrics.get("best_val_loss", 0), 4),
                "pos_mae": round(self._training_metrics.get("final_pos_mae", 0), 2),
                "num_training_samples": self._training_metrics.get("num_samples", 0),
            }
        else:
            return {
                "mode": "ml",
                "status": "not_trained",
                "message": "ML model not yet trained. Call initialize() or "
                           "make a prediction request to trigger training.",
            }
