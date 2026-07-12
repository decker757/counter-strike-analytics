#!/usr/bin/env python
"""Intent prediction server — position analysis + player intent prediction.

This is the entry point for running the CS2 analytics platform WITH
intent prediction enabled. It registers intent API routes on the existing
FastAPI app and then starts the standard position analysis server.

Usage:
    python examples/intent_server.py <demo_path>

Example:
    python examples/intent_server.py data/demos/match.dem

The server starts on http://localhost:8000 with all existing endpoints
(/api/state, /api/map, /api/players, /api/rounds, /api/heatmap) plus
new intent prediction endpoints (/api/intent/{tick}, /api/intent/zones,
/api/intent/model-info).

NO existing .py files are modified. Intent routes are registered on the
global FastAPI app object via standard Python import + decorator pattern.
"""

import sys
from pathlib import Path

# Add src to path (matches position_analysis.py pattern)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Step 1: Import intent_routes — this triggers registration of intent API
# routes on the global FastAPI app object from position_analysis.py.
# The import also triggers position_analysis.py's module-level code,
# creating the global `app` and initializing `df = pd.DataFrame()`.
import examples.intent_routes as intent_routes  # noqa: F401 — side-effect import
import examples.llm_routes as llm_routes  # noqa: F401 — side-effect import

# Step 2: Import load_and_start from position_analysis.
# By this point, the app object exists and has all routes registered
# (original routes from position_analysis.py + intent routes from intent_routes.py).
from examples.position_analysis import load_and_start

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/intent_server.py <demo_path>")
        print("Example: python examples/intent_server.py data/demos/match.dem")
        print()
        print("This starts the CS2 analytics server WITH intent prediction enabled.")
        print("All standard endpoints plus /api/intent/{tick} are available.")
        sys.exit(1)

    demo_path = sys.argv[1]
    print(f"Starting intent prediction server with demo: {demo_path}")
    print("Intent prediction mode: rule-based + ML (auto-trains on first request)")
    print("API endpoints: /api/intent/{tick}, /api/intent/zones, /api/intent/model-info")
    print()

    # Set demo path for ML model training (Phase B)
    intent_routes.set_demo_path(demo_path)

    # load_and_start parses the demo and blocks in uvicorn.run(app).
    # The app now has all intent routes registered.
    load_and_start(demo_path)
