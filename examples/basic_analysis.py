"""
Example: Basic match analysis using the new structure.

Run from project root:
    python examples/basic_analysis.py data/demos/your_demo.dem
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers import (
    DemoParser,
    detect_trade_kills,
    get_economy_timeline,
    analyze_eco_round_performance,
    calculate_team_spread,
    get_alive_players,
)


def main(demo_path: str):
    print(f"Parsing demo: {demo_path}")
    print("-" * 50)

    # Initialize parser
    parser = DemoParser(demo_path)

    # Get match overview
    match = parser.get_match()
    print(f"Map: {match.map_name}")
    print(f"Score: CT {match.ct_score} - {match.t_score} T")
    print(f"Rounds played: {match.total_rounds}")
    print()

    # Get kills and detect trades
    kills = parser.get_kills()
    kills = detect_trade_kills(kills, tickrate=parser.tickrate)

    trade_kills = [k for k in kills if k.is_trade]
    headshot_kills = [k for k in kills if k.headshot]

    print(f"Total kills: {len(kills)}")
    print(f"Trade kills: {len(trade_kills)}")
    print(f"Headshot kills: {len(headshot_kills)} ({100*len(headshot_kills)/len(kills):.1f}%)")
    print()

    # Economy analysis
    economy = parser.get_economy_by_round()
    rounds = parser.get_rounds()

    timeline = get_economy_timeline(economy, rounds)
    print("Economy Timeline (first 5 rounds):")
    for entry in timeline[:5]:
        print(f"  Round {entry['round_num']}: CT={entry['ct_buy_type']} vs T={entry['t_buy_type']} -> {entry['winner']}")
    print()

    # Eco round performance
    ct_eco_stats = analyze_eco_round_performance(economy, rounds, "CT")
    t_eco_stats = analyze_eco_round_performance(economy, rounds, "T")

    print("Eco Round Performance:")
    print(f"  CT: {ct_eco_stats['eco_wins']}/{ct_eco_stats['eco_rounds']} eco wins ({100*ct_eco_stats['eco_win_rate']:.0f}%)")
    print(f"  T:  {t_eco_stats['eco_wins']}/{t_eco_stats['eco_rounds']} eco wins ({100*t_eco_stats['eco_win_rate']:.0f}%)")
    print()

    # Player positioning sample
    print("Sample positioning analysis (Round 5):")
    frames = parser.get_player_frames(tick_interval=64, rounds=[5])
    if frames:
        mid_frame = frames[len(frames) // 2]
        ct_alive = get_alive_players(mid_frame, "CT")
        t_alive = get_alive_players(mid_frame, "T")

        ct_spread = calculate_team_spread(ct_alive)
        t_spread = calculate_team_spread(t_alive)

        print(f"  CT alive: {len(ct_alive)}, spread: {ct_spread:.0f} units")
        print(f"  T alive: {len(t_alive)}, spread: {t_spread:.0f} units")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/basic_analysis.py <demo_path>")
        print("Example: python examples/basic_analysis.py data/demos/match.dem")
        sys.exit(1)

    main(sys.argv[1])
