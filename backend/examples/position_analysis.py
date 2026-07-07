import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from demoparser2 import DemoParser

map_name = ""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

df = pd.DataFrame()

@app.get("/api/state/{tick}")
async def get_tick_state(tick: int):
    global df
    if df.empty:
        return {"error": "No data loaded"}
    
    # Filter for just the players at this specific tick
    tick_data = df[df['tick'] == tick]
    return tick_data.to_dict(orient="records")


@app.get("api/map")
async def get_map():
    return {
        "map_name": map_name
    }

def load_and_start(demo_path: str):
    global df
    print(f"Parsing demo: {demo_path}")
    
    # Use the fields from your project schema
    PLAYER_FIELDS = [
        "tick", "steamid", "name", "team_name", 
        "X", "Y", "Z", "is_alive"
    ]
    
    parser = DemoParser(demo_path)
    print("Extracting ticks... this may take a moment.")
    df = pd.DataFrame(parser.parse_ticks(PLAYER_FIELDS))
    print(f"Ready! Loaded {len(df)} rows.")
    
    map_name = parser.map_name
    
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)

'''
from src.parsers import (
    DemoParser
)
'''


'''
from src.parsers import (
    DemoParser,
    detect_trade_kills,
    get_economy_timeline,
    analyze_eco_round_performance,
    calculate_team_spread,
    get_alive_players,
)

from src.models import (
    PlayerFrame,
)


def main(demo_path: str):
    print(f"Parsing demo: {demo_path}")
    print("-" * 50)
    
    # Initialize parser
    parser = DemoParser(demo_path)
    PLAYER_FIELDS = ["tick", "steamid", "name", "X", "Y", "is_alive", "team_name"]
    
    print("Parsing demo...")
    df = pd.DataFrame(parser.parse_ticks(PLAYER_FIELDS))
    print("Ready!")
    
    print(df)
    
    @app.get("/api/state/{tick}")
    async def get_tick_state(tick: int):
        # Filter for just the players at this specific tick
        tick_data = df[df['tick'] == tick]
        
        # Return as a list of player objects
        return tick_data.to_dict(orient="records")
'''



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/basic_analysis.py <demo_path>")
        print("Example: python examples/basic_analysis.py data/demos/match.dem")
        sys.exit(1)

    load_and_start(sys.argv[1])
