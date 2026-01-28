"""Round outcome prediction model."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
import joblib


@dataclass
class PredictionResult:
    """Result of a round prediction."""

    team1_win_prob: float
    team2_win_prob: float
    predicted_winner: str
    confidence: float
    feature_importance: dict[str, float] | None = None


@dataclass
class ModelMetrics:
    """Evaluation metrics for the model."""

    accuracy: float
    auc_roc: float
    confusion_matrix: np.ndarray
    classification_report: str

    def __str__(self) -> str:
        return (
            f"Accuracy: {self.accuracy:.3f}\n"
            f"AUC-ROC: {self.auc_roc:.3f}\n"
            f"\nClassification Report:\n{self.classification_report}"
        )


class RoundPredictor:
    """Predict round outcomes based on economy and game state."""

    # Features used for prediction (in order)
    FEATURE_COLUMNS = [
        "round_num",
        "is_first_half",
        "is_pistol",
        "is_second_pistol",
        "team1_side_is_ct",
        "team1_total_money",
        "team1_avg_money",
        "team1_equipment_value",
        "team1_buy_type",
        "team1_is_eco",
        "team1_is_force",
        "team1_is_full",
        "team2_total_money",
        "team2_avg_money",
        "team2_equipment_value",
        "team2_buy_type",
        "team2_is_eco",
        "team2_is_force",
        "team2_is_full",
        "money_diff",
        "equip_diff",
        "money_ratio",
        "team1_score",
        "team2_score",
        "score_diff",
        "team1_won_prev",
        "team2_won_prev",
    ]

    MODEL_TYPES = {
        "logistic": LogisticRegression,
        "random_forest": RandomForestClassifier,
        "gradient_boosting": GradientBoostingClassifier,
    }

    def __init__(self, model_type: str = "gradient_boosting"):
        """
        Initialize predictor.

        Args:
            model_type: One of 'logistic', 'random_forest', 'gradient_boosting'
        """
        if model_type not in self.MODEL_TYPES:
            raise ValueError(f"Unknown model type: {model_type}. Choose from {list(self.MODEL_TYPES.keys())}")

        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self._is_fitted = False

    def _create_model(self) -> Any:
        """Create a new model instance with default hyperparameters."""
        if self.model_type == "logistic":
            return LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            )
        elif self.model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
        elif self.model_type == "gradient_boosting":
            return GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
            )

    def fit(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
        verbose: bool = True,
    ) -> "RoundPredictor":
        """
        Train the model.

        Args:
            features: DataFrame with feature columns
            labels: Series of labels (1 = team1 wins, 0 = team2 wins)
            verbose: Print training info

        Returns:
            self
        """
        # Ensure correct feature order
        X = features[self.FEATURE_COLUMNS].values
        y = labels.values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Create and train model
        self.model = self._create_model()
        self.model.fit(X_scaled, y)
        self._is_fitted = True

        if verbose:
            print(f"Trained {self.model_type} model on {len(y)} rounds")
            print(f"  Team1 wins: {sum(y)} ({sum(y)/len(y)*100:.1f}%)")
            print(f"  Team2 wins: {len(y)-sum(y)} ({(len(y)-sum(y))/len(y)*100:.1f}%)")

        return self

    def predict(self, features: pd.DataFrame) -> list[PredictionResult]:
        """
        Predict round outcomes.

        Args:
            features: DataFrame with feature columns

        Returns:
            List of PredictionResult objects
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        X = features[self.FEATURE_COLUMNS].values
        X_scaled = self.scaler.transform(X)

        probs = self.model.predict_proba(X_scaled)
        predictions = self.model.predict(X_scaled)

        # Get feature importance if available
        importance = self.get_feature_importance()

        results = []
        for i in range(len(predictions)):
            team1_prob = probs[i, 1]  # Probability of class 1 (team1 wins)
            team2_prob = probs[i, 0]  # Probability of class 0 (team2 wins)

            results.append(
                PredictionResult(
                    team1_win_prob=team1_prob,
                    team2_win_prob=team2_prob,
                    predicted_winner="team1" if predictions[i] == 1 else "team2",
                    confidence=max(team1_prob, team2_prob),
                    feature_importance=importance,
                )
            )

        return results

    def predict_single(self, features: dict) -> PredictionResult:
        """
        Predict outcome for a single round.

        Args:
            features: Dict of feature values

        Returns:
            PredictionResult
        """
        df = pd.DataFrame([features])
        return self.predict(df)[0]

    def evaluate(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
    ) -> ModelMetrics:
        """
        Evaluate model on test data.

        Args:
            features: Test features
            labels: True labels

        Returns:
            ModelMetrics with evaluation results
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before evaluation")

        X = features[self.FEATURE_COLUMNS].values
        X_scaled = self.scaler.transform(X)
        y_true = labels.values

        y_pred = self.model.predict(X_scaled)
        y_prob = self.model.predict_proba(X_scaled)[:, 1]

        return ModelMetrics(
            accuracy=accuracy_score(y_true, y_pred),
            auc_roc=roc_auc_score(y_true, y_prob),
            confusion_matrix=confusion_matrix(y_true, y_pred),
            classification_report=classification_report(
                y_true, y_pred, target_names=["Team2 Win", "Team1 Win"]
            ),
        )

    def get_feature_importance(self) -> dict[str, float] | None:
        """Get feature importance scores."""
        if not self._is_fitted:
            return None

        if hasattr(self.model, "feature_importances_"):
            # Tree-based models
            importance = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            # Linear models
            importance = np.abs(self.model.coef_[0])
        else:
            return None

        return dict(zip(self.FEATURE_COLUMNS, importance))

    def get_top_features(self, n: int = 10) -> list[tuple[str, float]]:
        """Get top N most important features."""
        importance = self.get_feature_importance()
        if not importance:
            return []

        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        return sorted_features[:n]

    def save(self, path: str | Path):
        """Save model to disk."""
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before saving")

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, path / "model.joblib")
        joblib.dump(self.scaler, path / "scaler.joblib")

        # Save metadata
        metadata = {
            "model_type": self.model_type,
            "feature_columns": self.FEATURE_COLUMNS,
        }
        joblib.dump(metadata, path / "metadata.joblib")

    @classmethod
    def load(cls, path: str | Path) -> "RoundPredictor":
        """Load model from disk."""
        path = Path(path)

        metadata = joblib.load(path / "metadata.joblib")
        predictor = cls(model_type=metadata["model_type"])
        predictor.model = joblib.load(path / "model.joblib")
        predictor.scaler = joblib.load(path / "scaler.joblib")
        predictor._is_fitted = True

        return predictor


def train_and_evaluate(
    demo_paths: list[str | Path],
    model_type: str = "gradient_boosting",
    test_size: float = 0.2,
    save_path: str | Path | None = None,
) -> tuple[RoundPredictor, ModelMetrics]:
    """
    Convenience function to train and evaluate a model.

    Args:
        demo_paths: List of demo file paths
        model_type: Model type to use
        test_size: Fraction of data for testing
        save_path: Optional path to save the model

    Returns:
        Tuple of (trained predictor, test metrics)
    """
    from src.ml.datasets import DatasetBuilder

    # Build dataset
    builder = DatasetBuilder(demo_paths)
    dataset = builder.build_round_dataset(include_incomplete=False)

    print(f"\nDataset: {len(dataset)} rounds from {len(demo_paths)} demos")

    # Split data
    train_data, test_data = dataset.train_test_split(
        test_size=test_size, by_demo=True
    )
    print(f"Train: {len(train_data)} rounds")
    print(f"Test: {len(test_data)} rounds")

    # Train model
    predictor = RoundPredictor(model_type=model_type)
    predictor.fit(train_data.features, train_data.labels)

    # Evaluate
    metrics = predictor.evaluate(test_data.features, test_data.labels)
    print(f"\n{metrics}")

    # Show top features
    print("\nTop 10 Important Features:")
    for feature, importance in predictor.get_top_features(10):
        print(f"  {feature}: {importance:.4f}")

    # Save if requested
    if save_path:
        predictor.save(save_path)
        print(f"\nModel saved to {save_path}")

    return predictor, metrics
