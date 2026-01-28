"""Dataset building utilities for ML training."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import pandas as pd
from tqdm import tqdm

from src.parsers import DemoParser
from src.models import RoundState, EconomyState, BuyType


@dataclass
class RoundDataset:
    """Dataset of round-level features and outcomes."""

    features: pd.DataFrame
    labels: pd.Series
    metadata: pd.DataFrame  # round_num, demo_path, map_name

    def __len__(self) -> int:
        return len(self.labels)

    def to_parquet(self, path: str | Path):
        """Save dataset to parquet files."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self.features.to_parquet(path / "features.parquet")
        self.labels.to_frame("label").to_parquet(path / "labels.parquet")
        self.metadata.to_parquet(path / "metadata.parquet")

    @classmethod
    def from_parquet(cls, path: str | Path) -> "RoundDataset":
        """Load dataset from parquet files."""
        path = Path(path)
        features = pd.read_parquet(path / "features.parquet")
        labels = pd.read_parquet(path / "labels.parquet")["label"]
        metadata = pd.read_parquet(path / "metadata.parquet")
        return cls(features=features, labels=labels, metadata=metadata)

    def train_test_split(
        self,
        test_size: float = 0.2,
        by_demo: bool = True,
        random_state: int = 42,
    ) -> tuple["RoundDataset", "RoundDataset"]:
        """
        Split dataset into train and test sets.

        Args:
            test_size: Fraction of data for test set
            by_demo: If True, split by demo (no data leakage between demos)
            random_state: Random seed
        """
        import numpy as np

        np.random.seed(random_state)

        if by_demo:
            # Split by demo to prevent leakage
            demos = self.metadata["demo_path"].unique()
            np.random.shuffle(demos)
            n_test = max(1, int(len(demos) * test_size))
            test_demos = set(demos[:n_test])

            test_mask = self.metadata["demo_path"].isin(test_demos)
            train_mask = ~test_mask
        else:
            # Random split
            n_test = int(len(self) * test_size)
            indices = np.random.permutation(len(self))
            test_indices = set(indices[:n_test])
            test_mask = pd.Series([i in test_indices for i in range(len(self))])
            train_mask = ~test_mask

        train = RoundDataset(
            features=self.features[train_mask].reset_index(drop=True),
            labels=self.labels[train_mask].reset_index(drop=True),
            metadata=self.metadata[train_mask].reset_index(drop=True),
        )
        test = RoundDataset(
            features=self.features[test_mask].reset_index(drop=True),
            labels=self.labels[test_mask].reset_index(drop=True),
            metadata=self.metadata[test_mask].reset_index(drop=True),
        )
        return train, test


class DatasetBuilder:
    """Build ML datasets from demo files."""

    def __init__(self, demo_paths: list[str | Path]):
        self.demo_paths = [Path(p) for p in demo_paths]

    @classmethod
    def from_directory(cls, directory: str | Path, pattern: str = "*.dem") -> "DatasetBuilder":
        """Create builder from all demos in a directory."""
        directory = Path(directory)
        demos = list(directory.glob(pattern))
        return cls(demos)

    def build_round_dataset(
        self,
        include_incomplete: bool = False,
        show_progress: bool = True,
    ) -> RoundDataset:
        """
        Build a dataset for round outcome prediction.

        Features include economy, buy type, side, etc.
        Label is 1 if team1 (starting CT) wins, 0 otherwise.
        """
        from src.ml.features import RoundFeatureExtractor

        all_features = []
        all_labels = []
        all_metadata = []

        iterator = tqdm(self.demo_paths, desc="Processing demos") if show_progress else self.demo_paths

        for demo_path in iterator:
            try:
                parser = DemoParser(demo_path)
                rounds = parser.get_rounds()
                economy = parser.get_economy_by_round()
                map_name = parser.map_name

                extractor = RoundFeatureExtractor(parser)

                for r in rounds:
                    if not r.result:
                        continue

                    # Skip incomplete matches unless requested
                    if not include_incomplete:
                        final_round = rounds[-1]
                        if final_round.result:
                            max_score = max(
                                final_round.result.ct_score,
                                final_round.result.t_score
                            )
                            if max_score < 13:
                                break

                    features = extractor.extract_round_features(r.round_num)
                    if features is None:
                        continue

                    # Label: 1 if team1 (started CT) wins this round
                    round_num = r.round_num
                    is_first_half = round_num <= 12
                    winner_side = r.result.winner

                    if is_first_half:
                        team1_won = 1 if winner_side == "CT" else 0
                    else:
                        team1_won = 1 if winner_side == "T" else 0

                    all_features.append(features)
                    all_labels.append(team1_won)
                    all_metadata.append({
                        "round_num": round_num,
                        "demo_path": str(demo_path),
                        "map_name": map_name,
                    })

            except Exception as e:
                if show_progress:
                    tqdm.write(f"Error processing {demo_path}: {e}")
                continue

        if not all_features:
            raise ValueError("No valid rounds found in any demo")

        return RoundDataset(
            features=pd.DataFrame(all_features),
            labels=pd.Series(all_labels),
            metadata=pd.DataFrame(all_metadata),
        )
