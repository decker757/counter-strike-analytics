import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
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

# Round boundary arrays (tick -> round number mapping)
# tick_boundaries[i] = tick where round (i+1) starts
tick_boundaries = np.array([])
round_numbers = np.array([])  # corresponding round numbers
available_rounds = []  # list of round numbers for the dropdown (excluding warmup)


@app.get("/api/state/{tick}")
async def get_tick_state(tick: int):
    global df
    if df.empty:
        return {"error": "No data loaded"}

    # O(1) index lookup instead of O(N) df[df['tick'] == tick]
    try:
        tick_data = df.loc[tick]
    except KeyError:
        return []
    if isinstance(tick_data, pd.Series):
        tick_data = tick_data.to_frame().T
    return tick_data.to_dict(orient="records")


@app.get("/api/map")
async def get_map():
    return {
        "map_name": map_name
    }


@app.get("/api/players")
async def get_players():
    global df
    if df.empty:
        return {"error": "No data loaded"}
    players = df[['steamid', 'name', 'team_name']].drop_duplicates(subset='steamid').copy()
    # Convert steamid to string to avoid JavaScript precision loss (steamids are 64-bit ints)
    players['steamid'] = players['steamid'].astype(str)
    return players.to_dict(orient="records")


@app.get("/api/rounds")
async def get_rounds():
    """Return available rounds with their tick ranges."""
    global tick_boundaries, round_numbers, df
    if df.empty:
        return {"rounds": []}

    # Build tick ranges for each round
    rounds_info = []
    for i, r in enumerate(round_numbers):
        start = int(tick_boundaries[i])
        # End tick is the next boundary minus 1, or the last tick in the demo
        if i + 1 < len(tick_boundaries):
            end = int(tick_boundaries[i + 1]) - 1
        else:
            end = int(df['tick'].max())
        rounds_info.append({
            "round_num": int(r),
            "start_tick": start,
            "end_tick": end,
        })
    return {"rounds": rounds_info}


def _get_round_for_tick(tick: int) -> int:
    """Map a tick value to its round number. Returns 0 for warmup."""
    global tick_boundaries, round_numbers
    if len(tick_boundaries) == 0:
        return 0
    # Find the last boundary that is <= tick
    idx = np.searchsorted(tick_boundaries, tick, side='right') - 1
    if idx < 0:
        return 0  # before first boundary = warmup
    return int(round_numbers[idx])


@app.get("/api/heatmap")
async def get_heatmap(steamid: str = "", team: str = "", sample_rate: int = 64, round_num: int = 0):
    """
    Returns sampled alive positions.
    - steamid: filter by player (empty = all players)
    - team: filter by team "CT" or "T" (empty = both teams)
    - sample_rate: sample every N rows
    - round_num: filter to specific round (0 = all rounds excluding warmup)
    """
    global df
    if df.empty:
        return {"error": "No data loaded"}

    # Start with alive players only
    player_data = df[df['is_alive'] == True]

    # Filter by player if specified
    if steamid:
        player_data = player_data[player_data['steamid'].astype(str) == steamid]

    # Filter by team if specified
    if team:
        player_data = player_data[player_data['team_name'] == team]

    if player_data.empty:
        return {"positions": [], "steamid": steamid, "team": team, "round_num": round_num}

    # Filter by round if specified, otherwise exclude warmup (round 0)
    if round_num > 0:
        player_data = player_data[player_data['round_num'] == round_num]
    else:
        # Default: exclude warmup (round 0), include all real rounds (1+)
        player_data = player_data[player_data['round_num'] > 0]

    if player_data.empty:
        return {"positions": [], "steamid": steamid, "team": team, "round_num": round_num}

    # Sample evenly across the match
    sampled = player_data.iloc[::sample_rate]

    return {
        "steamid": steamid or "all",
        "team": team or "all",
        "round_num": round_num,
        "positions": sampled[['X', 'Y']].to_dict(orient="records")
    }


def load_and_start(demo_path: str):
    global df, map_name, tick_boundaries, round_numbers, available_rounds
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
    # Sort by tick and set as index for O(1) lookups (was O(N) full scan before)
    df = df.sort_values('tick').set_index('tick', drop=False)

    header = parser.parse_header()
    map_name = header.get("map_name", "unknown")
    print(f"Map: {map_name}")

    # Build round boundaries
    # CS2 event structure:
    #   round_start: round 1 ticks are warmup, rounds 2+ are real game rounds
    #   round_end:   round_end[N] marks end of actual round N-1 (e.g. round_end[2] = round 1 end)
    #   round_announce_match_start: the tick where the pistol round officially begins
    print("Building round boundaries...")

    # Get match start (end of warmup)
    match_start_events = parser.parse_event('round_announce_match_start')
    warmup_end_tick = int(match_start_events['tick'].values[0]) if len(match_start_events) > 0 else 0
    print(f"Warmup ends at tick {warmup_end_tick}")

    round_ends = parser.parse_event('round_end').sort_values('tick')

    # Build mapping: round N starts at tick X
    # Round 1 (pistol): warmup_end_tick → first round_end tick
    # Round N (N>=2):  round_start[N] → round_end[N+1]
    round_starts_df = parser.parse_event('round_start')
    # For rounds 2+, get the start tick from round_start
    starts_lookup = {}
    for _, row in round_starts_df.iterrows():
        r = int(row['round'])
        if r >= 2:  # only real rounds (round_start round 1 = warmup)
            starts_lookup[r] = int(row['tick'])

    # Round 1 entry
    tick_boundaries_list = [warmup_end_tick]
    round_numbers_list = [1]

    # Add rounds 2+ from round_start/round_end
    ends_by_round = {}
    for _, row in round_ends.iterrows():
        ends_by_round[int(row['round'])] = int(row['tick'])

    num_real_rounds = len(round_ends)  # round_end has entries for rounds 2..N+1
    for r in range(2, num_real_rounds + 2):  # actual game rounds 2, 3, ...
        if r in starts_lookup:
            tick_boundaries_list.append(starts_lookup[r])
            round_numbers_list.append(r)

    tick_boundaries = np.array(tick_boundaries_list)
    round_numbers = np.array(round_numbers_list)

    # Pre-compute round_num column vectorized (was O(N) Python listcomp per heatmap request)
    tick_values = df['tick'].values
    indices = np.searchsorted(tick_boundaries, tick_values, side='right') - 1
    indices = np.clip(indices, 0, len(round_numbers) - 1)
    df['round_num'] = round_numbers[indices]
    print(f"Round column computed for {len(df)} rows.")

    # Build available rounds list (all real rounds including pistol round 1)
    available_rounds = list(range(1, num_real_rounds + 1))
    print(f"Rounds available: {available_rounds}")

    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/position_analysis.py <demo_path>")
        print("Example: python examples/position_analysis.py data/demos/match.dem")
        sys.exit(1)

    load_and_start(sys.argv[1])
