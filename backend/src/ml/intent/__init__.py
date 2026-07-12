"""Intent prediction — rule-based and ML-powered player intent forecasting.

Phase A: RuleBasedIntentPredictor (zone graph + velocity extrapolation)
Phase B: IntentTransformer (PyTorch sequence model, trained on demo data)
Phase C: LLM integration (Ollama-powered explanations and chat)
"""

from .zone_graph import MapZoneGraph
from .rule_predictor import RuleBasedIntentPredictor
from .model import IntentTransformer
from .trainer import IntentTrainer
from .inference import IntentInference

__all__ = [
    "MapZoneGraph",
    "RuleBasedIntentPredictor",
    "IntentTransformer",
    "IntentTrainer",
    "IntentInference",
]
