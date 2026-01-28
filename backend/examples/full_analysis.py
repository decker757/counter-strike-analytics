"""
Example: Full match and economy analysis.

Run from project root:
    python examples/full_analysis.py data/demos/your_demo.dem
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis import analyze_match, EconomyAnalyzer
from src.parsers import DemoParser


def main(demo_path: str):
    print(f"Analyzing: {demo_path}")
    print("=" * 60)

    # Full match analysis
    match = analyze_match(demo_path)

    print(f"\nMAP: {match.map_name}")
    print(f"SCORE: Team1 {match.team1_score} - {match.team2_score} Team2")
    print(f"ROUNDS: {match.total_rounds}")

    # Check if match is complete
    max_score = max(match.team1_score, match.team2_score)
    if max_score >= 13:
        winner = "Team1" if match.team1_score >= 13 else "Team2"
        print(f"RESULT: {winner} wins!")
    else:
        print(f"STATUS: INCOMPLETE (need 13 to win, highest is {max_score})")

    print("(Team1 = started CT, Team2 = started T)")

    # Team stats
    print("\n" + "-" * 60)
    print("TEAM PERFORMANCE")
    print("-" * 60)

    t1 = match.team1_stats
    t2 = match.team2_stats

    print(f"\n{'Overall':<25} {'Team1':>15} {'Team2':>15}")
    print("-" * 55)
    print(f"{'Total Rounds Won':<25} {t1.rounds_won:>15} {t2.rounds_won:>15}")
    print(f"{'Win Rate':<25} {t1.win_rate:>14.1f}% {t2.win_rate:>14.1f}%")

    t1_pistol = f"{t1.pistol_rounds_won}/{t1.pistol_rounds_played}"
    t2_pistol = f"{t2.pistol_rounds_won}/{t2.pistol_rounds_played}"
    print(f"{'Pistol Rounds Won':<25} {t1_pistol:>15} {t2_pistol:>15}")
    print(f"{'First Kill Rate':<25} {t1.first_kill_rate:>14.1f}% {t2.first_kill_rate:>14.1f}%")

    # Detailed side breakdown
    print("\n" + "-" * 60)
    print("SIDE-BY-SIDE PERFORMANCE")
    print("-" * 60)

    # Team1 breakdown
    print(f"\nTeam1 (started CT):")
    print(f"  CT Side: {t1.ct_rounds_won}W - {t1.ct_rounds_lost}L ({t1.ct_win_rate:.0f}% win rate) [Rounds 1-12]")
    print(f"  T Side:  {t1.t_rounds_won}W - {t1.t_rounds_lost}L ({t1.t_win_rate:.0f}% win rate) [Rounds 13+]")

    # Team2 breakdown
    print(f"\nTeam2 (started T):")
    print(f"  T Side:  {t2.t_rounds_won}W - {t2.t_rounds_lost}L ({t2.t_win_rate:.0f}% win rate) [Rounds 1-12]")
    print(f"  CT Side: {t2.ct_rounds_won}W - {t2.ct_rounds_lost}L ({t2.ct_win_rate:.0f}% win rate) [Rounds 13+]")

    # Top players
    print("\n" + "-" * 60)
    print("TOP PLAYERS (by K-D)")
    print("-" * 60)

    players = sorted(
        match.player_stats.values(),
        key=lambda p: p.kills - p.deaths,
        reverse=True
    )[:5]

    print(f"\n{'Name':<20} {'Team':<8} {'K':<4} {'D':<4} {'A':<4} {'HS%':<6} {'FK':<4}")
    print("-" * 55)
    for p in players:
        team_label = "Team1" if p.team == "CT" else "Team2"
        print(f"{p.name[:19]:<20} {team_label:<8} {p.kills:<4} {p.deaths:<4} {p.assists:<4} {p.headshot_percentage:<5.1f}% {p.first_kills:<4}")

    # Key rounds
    if match.key_rounds:
        print("\n" + "-" * 60)
        print("KEY ROUNDS")
        print("-" * 60)
        for kr in match.key_rounds[:8]:
            print(f"  Round {kr['round']:>2}: {kr['description']}")

    # Momentum swings
    if match.momentum_swings:
        print("\n" + "-" * 60)
        print("MOMENTUM SWINGS")
        print("-" * 60)
        for ms in match.momentum_swings:
            print(f"  Round {ms['round']:>2}: {ms['description']}")

    # Economy analysis
    print("\n" + "=" * 60)
    print("ECONOMY ANALYSIS")
    print("=" * 60)

    parser = DemoParser(demo_path)
    econ_analyzer = EconomyAnalyzer(parser)
    econ = econ_analyzer.analyze()

    t1_pat = econ.team1_patterns
    t2_pat = econ.team2_patterns

    print(f"\n{'Buy Type Distribution':<25} {'Team1':>15} {'Team2':>15}")
    print("-" * 55)
    print(f"{'Eco Rounds':<25} {t1_pat.eco_rounds:>15} {t2_pat.eco_rounds:>15}")
    print(f"{'Force Rounds':<25} {t1_pat.force_rounds:>15} {t2_pat.force_rounds:>15}")
    print(f"{'Full Buy Rounds':<25} {t1_pat.full_buy_rounds:>15} {t2_pat.full_buy_rounds:>15}")

    print(f"\n{'Win Rates by Buy Type':<25} {'Team1':>15} {'Team2':>15}")
    print("-" * 55)
    print(f"{'Eco Win Rate':<25} {t1_pat.eco_win_rate:>14.1f}% {t2_pat.eco_win_rate:>14.1f}%")
    print(f"{'Force Win Rate':<25} {t1_pat.force_win_rate:>14.1f}% {t2_pat.force_win_rate:>14.1f}%")
    print(f"{'Full Buy Win Rate':<25} {t1_pat.full_buy_win_rate:>14.1f}% {t2_pat.full_buy_win_rate:>14.1f}%")

    # Buy tendencies
    print("\n" + "-" * 60)
    print("BUY TENDENCIES")
    print("-" * 60)

    for team_key, team_label in [("team1", "Team1"), ("team2", "Team2")]:
        tendencies = econ_analyzer.get_buy_tendency_by_economy_state(team_key)
        print(f"\n{team_label}:")

        after_loss = tendencies["after_loss"]
        if after_loss["total"] > 0:
            eco_pct = after_loss["eco"] / after_loss["total"] * 100
            force_pct = after_loss["force"] / after_loss["total"] * 100
            print(f"  After loss: {eco_pct:.0f}% eco, {force_pct:.0f}% force, {100-eco_pct-force_pct:.0f}% full")

    # Economy impact
    print("\n" + "-" * 60)
    print("ECONOMY IMPACT ON WIN RATE")
    print("-" * 60)

    for team_key, team_label in [("team1", "Team1"), ("team2", "Team2")]:
        impact = econ_analyzer.get_economy_impact_on_wins(team_key)
        print(f"\n{team_label}:")
        print(f"  Large disadvantage (>$5k behind): {impact['disadvantage_large']['win_rate']:.0f}% win rate")
        print(f"  Even economy: {impact['even']['win_rate']:.0f}% win rate")
        print(f"  Large advantage (>$5k ahead): {impact['advantage_large']['win_rate']:.0f}% win rate")

    # Economic swings
    if econ.economic_swings:
        print("\n" + "-" * 60)
        print("ECONOMIC SWINGS")
        print("-" * 60)
        for swing in econ.economic_swings[:6]:
            print(f"  Round {swing.round_num:>2}: {swing.description}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/full_analysis.py <demo_path>")
        sys.exit(1)

    main(sys.argv[1])
