"""LLM integration — Ollama-powered explanations, narratives, and chat."""

from .client import LLMClient
from .prompts import (
    EXPLAIN_INTENT_PROMPT,
    ROUND_NARRATIVE_PROMPT,
    COACH_SYSTEM_PROMPT,
)
from .state_serializer import GameStateSerializer

__all__ = [
    "LLMClient",
    "GameStateSerializer",
    "EXPLAIN_INTENT_PROMPT",
    "ROUND_NARRATIVE_PROMPT",
    "COACH_SYSTEM_PROMPT",
]
