"""Training pipeline for the Intent Transformer model.

Assembles training data from a demo, builds PyTorch DataLoaders,
trains the IntentTransformer, and saves/loads checkpoints.
"""

import hashlib
import math
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from .features import IntentFeatureExtractor, FEATURE_DIM
from .labels import IntentLabeler
from .model import IntentTransformer


# Default checkpoint directory
DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent.parent / "data" / "models"


class TrajectoryDataset(Dataset):
    """PyTorch Dataset for intent prediction training samples.

    Each sample: (sequence_features, pos_label, action_label)
    """

    def __init__(
        self,
        sequences: np.ndarray,
        pos_labels: np.ndarray,
        action_labels: np.ndarray,
    ):
        self.sequences = torch.from_numpy(sequences).float()
        self.pos_labels = torch.from_numpy(pos_labels).float()
        self.action_labels = torch.from_numpy(action_labels).long()

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int):
        return (
            self.sequences[idx],
            self.pos_labels[idx],
            self.action_labels[idx],
        )


class IntentTrainer:
    """Trains the IntentTransformer model on parsed demo data.

    Usage:
        trainer = IntentTrainer("data/demos/match.dem")
        model, metrics = trainer.train(epochs=30)
        trainer.save_checkpoint(model)
    """

    def __init__(
        self,
        demo_path: str | Path,
        device: str = "cpu",
        seq_len: int = 32,
        batch_size: int = 256,
        val_split: float = 0.2,
    ):
        """Initialize trainer.

        Args:
            demo_path: Path to CS2 demo file
            device: 'cpu' or 'cuda'
            seq_len: Sequence window length in ticks
            batch_size: Training batch size
            val_split: Fraction of data for validation (split by round)
        """
        self.demo_path = Path(demo_path)
        self.device = device
        self.seq_len = seq_len
        self.batch_size = batch_size
        self.val_split = val_split

        self.demo_hash: Optional[str] = None
        self.feature_cols: list[str] = []

    def prepare_data(
        self,
    ) -> tuple[DataLoader, DataLoader]:
        """Parse demo, extract features, generate labels, build DataLoaders.

        Returns:
            (train_loader, val_loader) tuple
        """
        print("Parsing demo with extended intent fields...")
        t0 = time.time()

        # Parse and preprocess
        extractor = IntentFeatureExtractor(self.demo_path)
        raw_df = extractor.parse()
        df = extractor.preprocess(raw_df)
        self.feature_cols = [c for c in df.columns if c.startswith("feat_")]
        self.feature_cols = self.feature_cols[:FEATURE_DIM]

        print(f"Preprocessing: {len(df)} rows → feature dim={len(self.feature_cols)}")
        print(f"Parse + preprocess: {time.time() - t0:.1f}s")

        # Compute demo hash for checkpoint naming
        with open(self.demo_path, "rb") as f:
            file_head = f.read(65536)  # first 64KB
        self.demo_hash = hashlib.md5(file_head).hexdigest()[:12]

        # Generate training samples
        print("Generating self-supervised training labels...")
        t0 = time.time()
        samples = self._generate_samples(df)
        print(f"Generated {len(samples['sequences'])} samples in {time.time() - t0:.1f}s")

        if len(samples["sequences"]) < 100:
            raise ValueError(
                f"Only {len(samples['sequences'])} valid training samples. "
                "The demo may be too short or have insufficient data."
            )

        # Split by round index (not random) to prevent temporal leakage
        n_total = len(samples["sequences"])
        n_val = max(1, int(n_total * self.val_split))
        # Use last N% for validation (temporal split)
        indices = np.arange(n_total)
        val_indices = indices[-n_val:]
        train_indices = indices[:-n_val]

        print(f"Train: {len(train_indices)} samples, Val: {len(val_indices)} samples")

        train_dataset = TrajectoryDataset(
            samples["sequences"][train_indices],
            samples["pos_labels"][train_indices],
            samples["action_labels"][train_indices],
        )
        val_dataset = TrajectoryDataset(
            samples["sequences"][val_indices],
            samples["pos_labels"][val_indices],
            samples["action_labels"][val_indices],
        )

        train_loader = DataLoader(
            train_dataset, batch_size=self.batch_size, shuffle=True
        )
        val_loader = DataLoader(
            val_dataset, batch_size=self.batch_size, shuffle=False
        )

        return train_loader, val_loader

    def _generate_samples(
        self, df: pd.DataFrame
    ) -> dict[str, np.ndarray]:
        """Extract training samples from preprocessed DataFrame.

        Args:
            df: Preprocessed DataFrame from IntentFeatureExtractor.preprocess()

        Returns:
            Dict with 'sequences', 'pos_labels', 'action_labels' arrays
        """
        extractor = IntentFeatureExtractor(self.demo_path)
        extractor.scaler_stats = {}  # not needed here

        labeler = IntentLabeler()

        # Group by player
        sequences_list = []
        pos_list = []
        action_list = []

        feat_cols = [c for c in df.columns if c.startswith("feat_")]
        players = df["steamid"].unique()

        for steamid in players:
            player_df = df[df["steamid"] == steamid].sort_values("tick")
            is_ct = (player_df["team_name"].iloc[0] == "CT") if len(player_df) > 0 else True

            ticks = player_df["tick"].values

            # Sample ticks at stride to reduce redundancy
            stride = max(1, self.seq_len // 4)  # every 8 ticks
            for i in range(self.seq_len, len(ticks) - 192, stride):
                tick = int(ticks[i])

                # Check player is alive at this tick and 3s into the future
                current_row = player_df[player_df["tick"] == tick]
                if current_row.empty or not current_row["is_alive"].iloc[0]:
                    continue

                # Build feature sequence
                seq = self._build_sequence_array(
                    player_df, feat_cols, tick, self.seq_len
                )
                if seq is None:
                    continue

                # Generate labels
                sample = labeler.build_sample(player_df, tick, is_ct)
                if sample is None:
                    continue

                sequences_list.append(seq)
                pos_list.append(sample["pos_label"])
                action_list.append(sample["action_label"])

        if not sequences_list:
            raise ValueError(
                "No valid training samples could be generated. "
                "Ensure the demo has enough ticks of alive player data."
            )

        return {
            "sequences": np.array(sequences_list, dtype=np.float32),
            "pos_labels": np.array(pos_list, dtype=np.float32),
            "action_labels": np.array(action_list, dtype=np.int64),
        }

    def _build_sequence_array(
        self,
        player_df: pd.DataFrame,
        feat_cols: list[str],
        tick: int,
        window: int,
    ) -> Optional[np.ndarray]:
        """Build a (window, features) array for one player at one tick."""
        player_sorted = player_df.sort_values("tick")
        idx = player_sorted["tick"].searchsorted(tick)
        if idx < window:
            return None

        start_idx = idx - window + 1
        end_idx = idx + 1
        window_df = player_sorted.iloc[start_idx:end_idx]

        if len(window_df) < window // 2:
            return None

        features = window_df[feat_cols].values.astype(np.float32)
        if len(features) < window:
            pad = np.tile(features[0], (window - len(features), 1))
            features = np.vstack([pad, features])

        return features[-window:]

    def train(
        self,
        epochs: int = 30,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        patience: int = 8,
        verbose: bool = True,
    ) -> tuple[IntentTransformer, dict]:
        """Train the intent prediction model.

        Args:
            epochs: Maximum training epochs
            lr: Initial learning rate
            weight_decay: AdamW weight decay
            patience: Early stopping patience (epochs)
            verbose: Print progress

        Returns:
            (trained_model, training_metrics) tuple
        """
        # Prepare data
        train_loader, val_loader = self.prepare_data()

        # Create model
        model = IntentTransformer(
            input_dim=len(self.feature_cols),
        ).to(self.device)

        if verbose:
            print(f"\nModel: {model}")
            print(f"Training on {self.device}")

        # Loss functions
        pos_criterion = nn.MSELoss()
        action_criterion = nn.CrossEntropyLoss()

        optimizer = torch.optim.AdamW(
            model.parameters(), lr=lr, weight_decay=weight_decay
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=4
        )

        best_val_loss = float("inf")
        best_epoch = 0
        epochs_no_improve = 0
        history = {"train_loss": [], "val_loss": [], "val_pos_mae": []}

        for epoch in range(epochs):
            # Training
            model.train()
            train_loss_total = 0.0
            for batch in train_loader:
                seq, pos_labels, action_labels = (
                    batch[0].to(self.device),
                    batch[1].to(self.device),
                    batch[2].to(self.device),
                )

                optimizer.zero_grad()
                pos_pred, action_pred = model(seq)

                pos_loss = pos_criterion(pos_pred, pos_labels)
                act_loss = action_criterion(action_pred, action_labels)
                loss = pos_loss + 0.5 * act_loss

                loss.backward()
                optimizer.step()

                train_loss_total += loss.item()

            avg_train_loss = train_loss_total / len(train_loader)

            # Validation
            model.eval()
            val_loss_total = 0.0
            val_pos_errors = []
            with torch.no_grad():
                for batch in val_loader:
                    seq, pos_labels, action_labels = (
                        batch[0].to(self.device),
                        batch[1].to(self.device),
                        batch[2].to(self.device),
                    )

                    pos_pred, action_pred = model(seq)
                    pos_loss = pos_criterion(pos_pred, pos_labels)
                    act_loss = action_criterion(action_pred, action_labels)
                    val_loss_total += (pos_loss + 0.5 * act_loss).item()

                    # Mean absolute position error
                    pos_mae = torch.abs(pos_pred - pos_labels).mean().item()
                    val_pos_errors.append(pos_mae)

            avg_val_loss = val_loss_total / len(val_loader)
            avg_pos_mae = np.mean(val_pos_errors) if val_pos_errors else float("inf")

            history["train_loss"].append(avg_train_loss)
            history["val_loss"].append(avg_val_loss)
            history["val_pos_mae"].append(avg_pos_mae)

            scheduler.step(avg_val_loss)

            if verbose and (epoch % 5 == 0 or epoch == epochs - 1):
                print(
                    f"Epoch {epoch+1:2d}/{epochs} | "
                    f"train_loss: {avg_train_loss:.4f} | "
                    f"val_loss: {avg_val_loss:.4f} | "
                    f"pos_mae: {avg_pos_mae:.2f} units"
                )

            # Early stopping
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_epoch = epoch
                epochs_no_improve = 0
                # Save best model state
                self._best_state = {
                    k: v.cpu().clone() for k, v in model.state_dict().items()
                }
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    if verbose:
                        print(f"Early stopping at epoch {epoch+1} "
                              f"(best: epoch {best_epoch+1}, val_loss={best_val_loss:.4f})")
                    break

        # Restore best model
        if hasattr(self, "_best_state"):
            model.load_state_dict(self._best_state)

        metrics = {
            "best_val_loss": best_val_loss,
            "best_epoch": best_epoch,
            "final_pos_mae": avg_pos_mae,
            "history": history,
            "num_samples": len(train_loader.dataset) + len(val_loader.dataset),
            "num_epochs": epoch + 1,
        }

        if verbose:
            print(f"\nTraining complete. Best val_loss: {best_val_loss:.4f} "
                  f"(epoch {best_epoch+1})")

        return model, metrics

    def save_checkpoint(
        self,
        model: IntentTransformer,
        model_dir: str | Path | None = None,
    ) -> Path:
        """Save model checkpoint.

        Args:
            model: Trained model
            model_dir: Directory for checkpoints (default: data/models/)

        Returns:
            Path to saved checkpoint file
        """
        if model_dir is None:
            model_dir = DEFAULT_MODEL_DIR
        model_dir = Path(model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)

        filename = f"intent_{self.demo_hash}.pt"
        path = model_dir / filename

        checkpoint = {
            "model_state_dict": model.state_dict(),
            "model_config": {
                "input_dim": model.input_dim,
                "d_model": model.d_model,
                "num_layers": model.encoder.num_layers,
            },
            "feature_cols": self.feature_cols,
            "demo_hash": self.demo_hash,
            "demo_path": str(self.demo_path),
        }
        torch.save(checkpoint, path)
        print(f"Checkpoint saved to {path}")
        return path

    @staticmethod
    def load_checkpoint(
        path: str | Path,
        device: str = "cpu",
    ) -> Optional[IntentTransformer]:
        """Load a saved model checkpoint.

        Args:
            path: Path to checkpoint file
            device: Device to load model on

        Returns:
            IntentTransformer model, or None if loading fails
        """
        path = Path(path)
        if not path.exists():
            return None

        try:
            checkpoint = torch.load(path, map_location=device, weights_only=False)
            config = checkpoint["model_config"]
            model = IntentTransformer(
                input_dim=config["input_dim"],
                d_model=config.get("d_model", 128),
                num_layers=config.get("num_layers", 4),
            ).to(device)
            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()
            return model
        except Exception as e:
            print(f"Error loading checkpoint {path}: {e}")
            return None
