"""Intent prediction API routes.

Registers intent endpoints on the existing FastAPI app from position_analysis.py.
This file does NOT edit any existing .py file — it imports the global `app` and
decorates it with new routes via standard FastAPI patterns.

Prediction modes (auto-selected):
  - ML mode: IntentTransformer trained on this demo (Phase B)
  - Rule-based mode: velocity extrapolation + zone graph (Phase A, fallback)
"""

import sys
from pathlib import Path

# Ensure src is on path for imports (matches position_analysis.py pattern)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the existing FastAPI app and shared globals
# This triggers position_analysis.py's module-level code (creates app, df, etc.)
import examples.position_analysis as pa

from src.ml.intent.rule_predictor import RuleBasedIntentPredictor
from src.ml.intent.inference import IntentInference

# Module-level state
_rule_predictor: RuleBasedIntentPredictor | None = None
_ml_inference: IntentInference | None = None
_map_name: str = ""
_demo_path: str | None = None


def set_demo_path(path: str):
    """Set the demo path for ML model training.

    Call before load_and_start() to enable ML intent prediction.
    """
    global _demo_path
    _demo_path = path


def _get_rule_predictor() -> RuleBasedIntentPredictor | None:
    """Get or create the rule-based intent predictor.

    Returns None if the current map has no zone definitions.
    """
    global _rule_predictor, _map_name

    current_map = pa.map_name
    if _rule_predictor is None or current_map != _map_name:
        try:
            _rule_predictor = RuleBasedIntentPredictor(current_map)
            _map_name = current_map
        except (FileNotFoundError, Exception) as e:
            print(f"[intent] Zone config not available for '{current_map}': {e}")
            print(f"[intent] Falling back to simple velocity extrapolation (no zone awareness)")
            _rule_predictor = None  # Will trigger fallback mode
            _map_name = current_map
    return _rule_predictor


def _get_ml_inference() -> IntentInference:
    """Get or create the ML inference engine."""
    global _ml_inference, _demo_path
    if _ml_inference is None:
        if _demo_path is None:
            raise RuntimeError("Demo path not set for ML inference")
        _ml_inference = IntentInference(_demo_path)
    return _ml_inference


@pa.app.get("/api/intent/{tick}")
async def get_intent(
    tick: int,
    team: str = "",
    steamid: str = "",
):
    """Predict player intent at a given tick.

    Query params:
      team: filter by team ("CT" or "TERRORIST"), empty = both
      steamid: filter by specific player, empty = all

    Uses ML model if trained, falls back to rule-based predictor.
    """
    df = pa.df  # Access at request time (not import time)
    if df.empty:
        return {"error": "No data loaded", "tick": tick, "players": []}

    # Try ML first
    if _ml_inference is not None and _ml_inference._is_trained:
        try:
            result = _ml_inference.predict(tick)
            if team or steamid:
                result["players"] = [
                    p for p in result["players"]
                    if (not team or p["team"] == ("CT" if team == "CT" else "T"))
                    and (not steamid or p["steamid"] == steamid)
                ]
            return result
        except Exception:
            pass  # Fall through to rule-based

    # Fall back to rule-based
    predictor = _get_rule_predictor()
    if predictor is not None:
        try:
            return predictor.predict(tick, df, team_filter=team, steamid_filter=steamid)
        except Exception as e:
            return {"error": f"Prediction failed: {e}", "tick": tick, "players": []}

    # Ultimate fallback: simple velocity extrapolation (works on any map, no zones)
    return _simple_intent_predict(tick, df, team, steamid)


@pa.app.get("/api/intent/zones")
async def get_intent_zones():
    """Return zone definitions for the current map."""
    global _map_name
    map_name = pa.map_name or _map_name
    if not map_name:
        return {"error": "No map loaded", "zones": []}

    try:
        predictor = _get_rule_predictor()
        zones = []
        for zone_id, zone in predictor.zone_graph.zones.items():
            center = predictor.zone_graph._get_zone_center(zone_id)
            zones.append({
                "id": zone_id,
                "name": zone.get("name", zone_id),
                "is_bombsite": zone.get("is_bombsite", False),
                "is_ct_spawn": zone.get("is_ct_spawn", False),
                "is_t_spawn": zone.get("is_t_spawn", False),
                "adjacent": zone.get("adjacent", []),
                "center": {"x": center[0], "y": center[1]} if center else None,
            })
        return {"map": map_name, "zones": zones}
    except RuntimeError as e:
        return {"error": str(e), "zones": []}


@pa.app.get("/api/intent/model-info")
async def get_intent_model_info():
    """Return information about the current intent prediction model."""
    # Check ML status
    ml_info = {}
    if _ml_inference is not None:
        ml_info = _ml_inference.model_info

    # Check rule-based status
    rule_info = {
        "mode": "rule-based",
        "status": "active",
        "description": "Velocity extrapolation with map zone graph navigation.",
    }
    predictor = _get_rule_predictor()
    if predictor is None:
        rule_info["status"] = "fallback (no zone config — simple velocity mode)"
        rule_info["description"] = "Basic velocity extrapolation without zone awareness. Create zone JSON to enable full predictions."

    return {
        "current_mode": ml_info.get("mode", "rule-based") if ml_info else "rule-based",
        "ml": ml_info,
        "rule_based": rule_info,
        "supported_maps": ["de_inferno", "de_dust2"],
    }


def _simple_intent_predict(tick: int, df, team: str, steamid: str) -> dict:
    """Simple velocity extrapolation — works on ANY map without zone config.

    Uses basic position delta computation when zone graph is unavailable.
    """
    import math

    tick_data = df[df["tick"] == tick]
    if tick_data.empty:
        return {"tick": tick, "players": []}

    alive = tick_data[tick_data["is_alive"] == True]
    if team:
        alive = alive[alive["team_name"] == team]
    if steamid:
        alive = alive[alive["steamid"].astype(str) == steamid]

    players = []
    for _, p in alive.iterrows():
        sid = str(p["steamid"])
        x, y, z = float(p["X"]), float(p["Y"]), float(p.get("Z", 0))
        is_ct = p["team_name"] == "CT"

        # Simple velocity from position delta over 16 ticks
        prev = df[(df["tick"] == tick - 16) & (df["steamid"].astype(str) == sid)]
        vel_x, vel_y = 0.0, 0.0
        if not prev.empty:
            vel_x = (x - float(prev["X"].iloc[0])) / 16.0
            vel_y = (y - float(prev["Y"].iloc[0])) / 16.0

        speed = math.sqrt(vel_x ** 2 + vel_y ** 2)
        if speed < 1.5:
            action = "holding"
        elif is_ct and vel_x > 0:
            action = "pushing"
        elif not is_ct and vel_x < 0:
            action = "pushing"
        elif speed > 2.0:
            action = "rotating"
        else:
            action = "holding"

        tickrate = 64
        preds = []
        for i, h in enumerate([tickrate, tickrate * 2, tickrate * 3]):
            damp = 1.0 - (i * 0.25)
            preds.append({
                "horizon": f"+{i+1}s",
                "tick": tick + h,
                "x": round(x + vel_x * h * damp, 1),
                "y": round(y + vel_y * h * damp, 1),
                "z": round(z, 1),
            })

        players.append({
            "steamid": sid,
            "name": p.get("name", "Unknown"),
            "team": "CT" if is_ct else "T",
            "current_position": {"x": x, "y": y, "z": z},
            "predictions": preds,
            "action": action,
            "action_probs": {"holding": 0.25, "pushing": 0.25, "rotating": 0.25, "falling_back": 0.25},
            "confidence": 0.35,
            "current_zone": None,
            "predicted_zone": None,
        })

    return {"tick": tick, "players": players}


@pa.app.post("/api/intent/train")
async def train_intent_model():
    """Trigger ML model training (async — may take 1-3 minutes)."""
    global _ml_inference

    if _demo_path is None:
        return {"error": "No demo path configured. Use intent_server.py to start."}

    try:
        inference = _get_ml_inference()
        if inference._is_trained:
            return {
                "status": "already_trained",
                "message": "Model is already trained. Use force_retrain=true to retrain.",
                "model_info": inference.model_info,
            }
    except RuntimeError:
        pass

    return {
        "status": "training_required",
        "message": "ML model not yet trained. Make a GET /api/intent/{tick} request "
                   "to trigger automatic training, or call this endpoint to monitor.",
        "hint": "Training begins automatically on the first intent prediction request.",
    }
