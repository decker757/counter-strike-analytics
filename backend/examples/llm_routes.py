"""LLM-powered coaching API routes.

Registers LLM endpoints on the existing FastAPI app. All endpoints
handle the case where Ollama is not running by returning status messages
rather than errors — the LLM is an enhancement, not a requirement.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import examples.position_analysis as pa
from src.ml.intent.llm.client import LLMClient
from src.ml.intent.llm.prompts import (
    EXPLAIN_INTENT_PROMPT,
    ROUND_NARRATIVE_PROMPT,
    COACH_SYSTEM_PROMPT,
    COACH_QUERY_PROMPT,
)
from src.ml.intent.llm.state_serializer import GameStateSerializer

# Module-level state
_llm_client: LLMClient | None = None
_chat_history: list[dict[str, str]] = []


def _get_client() -> LLMClient:
    """Get or create the LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


@pa.app.get("/api/llm/status")
async def get_llm_status():
    """Check LLM availability (non-blocking — runs HTTP check in thread)."""
    client = _get_client()
    available = await asyncio.to_thread(client.is_available)
    return {
        "available": available,
        "model": client.model,
        "message": "Ollama is running and model is ready." if available
                   else f"Ollama not available. Install: ollama pull {client.model}",
    }


@pa.app.get("/api/llm/explain/{tick}")
async def explain_tick(tick: int):
    """Generate natural language explanation of predicted intents at a tick.

    Returns tactical insight about what each player is likely doing and why.
    """
    df = pa.df
    if df.empty:
        return {"status": "no_data", "text": "No match data loaded."}

    client = _get_client()
    if not client.is_available():
        return {
            "status": "unavailable",
            "text": "",
            "message": f"Ollama not running. Install: ollama pull {client.model}",
        }

    # Serialize game state
    serializer = GameStateSerializer()

    # Try to get intent predictions
    intent_data = None
    try:
        from examples.intent_routes import _get_rule_predictor
        predictor = _get_rule_predictor()
        intent_data = predictor.predict(tick, df)
    except Exception:
        pass

    game_state = serializer.serialize_tick_state(tick, df, intent_data)
    intent_text = _serialize_intent_for_prompt(intent_data)

    prompt = EXPLAIN_INTENT_PROMPT.format(
        game_state=game_state,
        intent_predictions=intent_text or "(No intent predictions available)",
    )

    # Run blocking LLM call in thread to avoid blocking the async event loop
    result = await asyncio.to_thread(
        client.generate, prompt, system=COACH_SYSTEM_PROMPT, max_tokens=512
    )

    return {
        "tick": tick,
        "text": result.get("text", ""),
        "status": result.get("status", "error"),
        "elapsed_seconds": result.get("elapsed_seconds", 0),
    }


def _serialize_intent_for_prompt(intent_data: dict | None) -> str:
    """Convert intent prediction JSON to a compact text format for the prompt."""
    if not intent_data or not intent_data.get("players"):
        return "(No intent predictions available)"

    lines = []
    for p in intent_data["players"]:
        action = p.get("action", "?")
        conf = p.get("confidence", 0)
        zone = p.get("predicted_zone") or p.get("current_zone", "?")
        preds = p.get("predictions", [])
        if preds:
            last = preds[-1]
            lines.append(
                f"  - {p['name']} ({p['team']}): predicted {action} toward {zone} "
                f"(confidence {conf:.0%}), 3s position: ({last['x']:.0f}, {last['y']:.0f})"
            )
    return "\n".join(lines)


@pa.app.get("/api/llm/round/{round_num}")
async def narrate_round(round_num: int):
    """Generate a natural language narrative summary of a round."""
    client = _get_client()
    if not client.is_available():
        return {
            "status": "unavailable",
            "text": "",
            "message": f"Ollama not running. Install: ollama pull {client.model}",
        }

    # Gather round data from position_analysis globals
    serializer = GameStateSerializer()

    # Build round info from available boundaries
    round_info = {"round_num": round_num, "start_tick": "?", "end_tick": "?"}
    try:
        tick_boundaries = pa.tick_boundaries
        round_numbers = pa.round_numbers
        for i, r in enumerate(round_numbers):
            if int(r) == round_num:
                start = int(tick_boundaries[i])
                end = int(tick_boundaries[i + 1] - 1) if i + 1 < len(tick_boundaries) else int(pa.df["tick"].max()) if not pa.df.empty else "?"
                round_info = {"round_num": round_num, "start_tick": start, "end_tick": end}
                break
    except Exception:
        pass

    round_data = serializer.serialize_round_summary(round_num, round_info)
    prompt = ROUND_NARRATIVE_PROMPT.format(round_num=round_num, round_data=round_data)

    result = await asyncio.to_thread(
        client.generate, prompt, system=COACH_SYSTEM_PROMPT, max_tokens=400
    )

    return {
        "round_num": round_num,
        "text": result.get("text", ""),
        "status": result.get("status", "error"),
        "elapsed_seconds": result.get("elapsed_seconds", 0),
    }


@pa.app.post("/api/llm/chat")
async def chat_with_coach(request: dict):
    """Conversational chat with the AI coach.

    Request body:
    {
      "message": "Why did the T side lose round 5?",
      "history": []  // optional conversation history
    }
    """
    global _chat_history

    client = _get_client()
    if not client.is_available():
        return {
            "status": "unavailable",
            "text": "",
            "message": f"Ollama not running. Install: ollama pull {client.model}",
        }

    user_message = request.get("message", "")
    if not user_message:
        return {"status": "error", "text": "", "message": "No message provided."}

    # Build match context
    df = pa.df
    serializer = GameStateSerializer()
    match_context = serializer.serialize_match_context(
        df, map_name=pa.map_name
    )

    prompt = COACH_QUERY_PROMPT.format(
        match_context=match_context,
        user_query=user_message,
    )

    result = await asyncio.to_thread(
        client.generate,
        prompt,
        system=COACH_SYSTEM_PROMPT,
        max_tokens=400,
        temperature=0.8,
    )

    # Maintain conversation history
    if not request.get("history"):
        _chat_history = []

    _chat_history.append({"role": "user", "content": user_message})
    if result.get("text"):
        _chat_history.append({"role": "assistant", "content": result["text"]})

    return {
        "text": result.get("text", ""),
        "status": result.get("status", "error"),
        "elapsed_seconds": result.get("elapsed_seconds", 0),
        "history": _chat_history[-10:],  # keep last 10 messages
    }
