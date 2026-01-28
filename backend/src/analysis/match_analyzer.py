"""Match analysis module for overall match insights."""

from dataclasses import dataclass

from src.models import (
    Match,
    RoundState,
    RoundEndReason,
    Kill,
    EconomyState,
    BuyType,
)
from src.parsers import DemoParser, detect_trade_kills, get_multikills


@dataclass
class PlayerStats:
    """Individual player statistics."""

    steamid: str
    name: str
    team: str
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    headshots: int = 0
    first_kills: int = 0
    first_deaths: int = 0
    trade_kills: int = 0
    clutch_wins: int = 0
    multikills: dict = None  # {2: count, 3: count, 4: count, 5: count}

    def __post_init__(self):
        if self.multikills is None:
            self.multikills = {2: 0, 3: 0, 4: 0, 5: 0}

    @property
    def kd_ratio(self) -> float:
        return self.kills / self.deaths if self.deaths > 0 else self.kills

    @property
    def headshot_percentage(self) -> float:
        return (self.headshots / self.kills * 100) if self.kills > 0 else 0.0

    @property
    def kast(self) -> float:
        """Placeholder - needs round-by-round data."""
        return 0.0


@dataclass
class TeamStats:
    """Team-level statistics."""

    team: str
    rounds_won: int = 0
    rounds_lost: int = 0
    ct_rounds_won: int = 0
    ct_rounds_lost: int = 0
    t_rounds_won: int = 0
    t_rounds_lost: int = 0
    pistol_rounds_won: int = 0
    pistol_rounds_played: int = 0
    eco_rounds_won: int = 0
    eco_rounds_played: int = 0
    force_rounds_won: int = 0
    force_rounds_played: int = 0
    first_kills: int = 0
    first_deaths: int = 0

    @property
    def win_rate(self) -> float:
        total = self.rounds_won + self.rounds_lost
        return (self.rounds_won / total * 100) if total > 0 else 0.0

    @property
    def ct_win_rate(self) -> float:
        total = self.ct_rounds_won + self.ct_rounds_lost
        return (self.ct_rounds_won / total * 100) if total > 0 else 0.0

    @property
    def t_win_rate(self) -> float:
        total = self.t_rounds_won + self.t_rounds_lost
        return (self.t_rounds_won / total * 100) if total > 0 else 0.0

    @property
    def pistol_win_rate(self) -> float:
        return (self.pistol_rounds_won / self.pistol_rounds_played * 100) if self.pistol_rounds_played > 0 else 0.0

    @property
    def first_kill_rate(self) -> float:
        total = self.first_kills + self.first_deaths
        return (self.first_kills / total * 100) if total > 0 else 50.0


@dataclass
class MatchSummary:
    """Complete match analysis summary."""

    map_name: str
    team1_score: int  # Team that started CT
    team2_score: int  # Team that started T
    total_rounds: int
    team1_stats: TeamStats  # Team that started CT
    team2_stats: TeamStats  # Team that started T
    player_stats: dict[str, PlayerStats]
    key_rounds: list[dict]
    momentum_swings: list[dict]


class MatchAnalyzer:
    """Analyzer for complete match insights."""

    def __init__(self, parser: DemoParser):
        self.parser = parser
        self._match: Match | None = None
        self._kills: list[Kill] | None = None
        self._rounds: list[RoundState] | None = None
        self._economy: dict[int, EconomyState] | None = None

    def analyze(self) -> MatchSummary:
        """Run full match analysis."""
        self._match = self.parser.get_match()
        self._kills = detect_trade_kills(self.parser.get_kills(), tickrate=self.parser.tickrate)
        self._rounds = self.parser.get_rounds()
        self._economy = self.parser.get_economy_by_round()

        player_stats = self._compute_player_stats()
        team1_stats, team2_stats = self._compute_team_stats()
        key_rounds = self._identify_key_rounds()
        momentum = self._analyze_momentum()

        return MatchSummary(
            map_name=self._match.map_name,
            team1_score=team1_stats.rounds_won,
            team2_score=team2_stats.rounds_won,
            total_rounds=self._match.total_rounds,
            team1_stats=team1_stats,
            team2_stats=team2_stats,
            player_stats=player_stats,
            key_rounds=key_rounds,
            momentum_swings=momentum,
        )

    def _compute_player_stats(self) -> dict[str, PlayerStats]:
        """Compute per-player statistics."""
        stats: dict[str, PlayerStats] = {}

        # Initialize from match rosters
        for steamid, name in self._match.team_ct.players.items():
            stats[steamid] = PlayerStats(steamid=steamid, name=name, team="CT")
        for steamid, name in self._match.team_t.players.items():
            stats[steamid] = PlayerStats(steamid=steamid, name=name, team="T")

        # Process kills
        kills_by_round: dict[int, list[Kill]] = {}
        for kill in self._kills:
            if kill.round_num not in kills_by_round:
                kills_by_round[kill.round_num] = []
            kills_by_round[kill.round_num].append(kill)

            # Count kills
            if kill.attacker_steamid and kill.attacker_steamid in stats:
                stats[kill.attacker_steamid].kills += 1
                if kill.headshot:
                    stats[kill.attacker_steamid].headshots += 1
                if kill.is_trade:
                    stats[kill.attacker_steamid].trade_kills += 1

            # Count deaths
            if kill.victim_steamid in stats:
                stats[kill.victim_steamid].deaths += 1

            # Count assists
            if kill.assister_steamid and kill.assister_steamid in stats:
                stats[kill.assister_steamid].assists += 1

        # First kills/deaths
        for round_num, round_kills in kills_by_round.items():
            if round_kills:
                round_kills.sort(key=lambda k: k.tick)
                first_kill = round_kills[0]
                if first_kill.attacker_steamid and first_kill.attacker_steamid in stats:
                    stats[first_kill.attacker_steamid].first_kills += 1
                if first_kill.victim_steamid in stats:
                    stats[first_kill.victim_steamid].first_deaths += 1

        # Multikills
        multikills = get_multikills(self._kills)
        for steamid, counts in multikills.items():
            if steamid in stats:
                stats[steamid].multikills = counts

        return stats

    def _compute_team_stats(self) -> tuple[TeamStats, TeamStats]:
        """Compute team-level statistics.

        Note: team1_stats = team that started as CT (CT first half, T second half)
              team2_stats = team that started as T (T first half, CT second half)
        """
        team1_stats = TeamStats(team="Team1 (started CT)")
        team2_stats = TeamStats(team="Team2 (started T)")

        def get_starting_team_winner(round_num: int, winner_side: str) -> str:
            """Map round winner side to starting team.

            First half (rounds 1-12): CT side = team1, T side = team2
            Second half (rounds 13+): CT side = team2, T side = team1
            """
            is_first_half = round_num <= 12
            if is_first_half:
                return "team1" if winner_side == "CT" else "team2"
            else:
                return "team2" if winner_side == "CT" else "team1"

        def get_starting_team_for_side(round_num: int, side: str) -> str:
            """Map current side to starting team."""
            is_first_half = round_num <= 12
            if is_first_half:
                return "team1" if side == "CT" else "team2"
            else:
                return "team2" if side == "CT" else "team1"

        for r in self._rounds:
            if not r.result:
                continue

            round_num = r.round_num
            winner_side = r.result.winner  # "CT" or "T" - the side that won
            winning_team = get_starting_team_winner(round_num, winner_side)
            losing_team = "team2" if winning_team == "team1" else "team1"

            # Determine which side each starting team is on this round
            is_first_half = round_num <= 12
            team1_side = "CT" if is_first_half else "T"
            team2_side = "T" if is_first_half else "CT"

            # Get economy info
            economy = self._economy.get(round_num)

            # Get buy type for each starting team (based on their current side)
            if economy:
                team1_buy = economy.ct_economy.buy_type if team1_side == "CT" else economy.t_economy.buy_type
                team2_buy = economy.ct_economy.buy_type if team2_side == "CT" else economy.t_economy.buy_type
            else:
                team1_buy = BuyType.FULL
                team2_buy = BuyType.FULL

            # Pistol rounds (1 and 13)
            if round_num in (1, 13):
                team1_stats.pistol_rounds_played += 1
                team2_stats.pistol_rounds_played += 1
                if winning_team == "team1":
                    team1_stats.pistol_rounds_won += 1
                else:
                    team2_stats.pistol_rounds_won += 1

            # Win/loss tracking
            if winning_team == "team1":
                team1_stats.rounds_won += 1
                team2_stats.rounds_lost += 1
                # Track which side team1 won on
                if team1_side == "CT":
                    team1_stats.ct_rounds_won += 1
                    team2_stats.t_rounds_lost += 1
                else:
                    team1_stats.t_rounds_won += 1
                    team2_stats.ct_rounds_lost += 1
            else:
                team2_stats.rounds_won += 1
                team1_stats.rounds_lost += 1
                # Track which side team2 won on
                if team2_side == "CT":
                    team2_stats.ct_rounds_won += 1
                    team1_stats.t_rounds_lost += 1
                else:
                    team2_stats.t_rounds_won += 1
                    team1_stats.ct_rounds_lost += 1

            # Eco/force tracking for team1
            if team1_buy == BuyType.ECO:
                team1_stats.eco_rounds_played += 1
                if winning_team == "team1":
                    team1_stats.eco_rounds_won += 1
            elif team1_buy == BuyType.FORCE:
                team1_stats.force_rounds_played += 1
                if winning_team == "team1":
                    team1_stats.force_rounds_won += 1

            # Eco/force tracking for team2
            if team2_buy == BuyType.ECO:
                team2_stats.eco_rounds_played += 1
                if winning_team == "team2":
                    team2_stats.eco_rounds_won += 1
            elif team2_buy == BuyType.FORCE:
                team2_stats.force_rounds_played += 1
                if winning_team == "team2":
                    team2_stats.force_rounds_won += 1

        # First kill rate
        for r in self._rounds:
            round_num = r.round_num
            kills = [k for k in self._kills if k.round_num == round_num]
            if kills:
                kills.sort(key=lambda k: k.tick)
                first = kills[0]
                if first.attacker_team:
                    fk_team = get_starting_team_for_side(round_num, first.attacker_team)
                    fd_team = "team2" if fk_team == "team1" else "team1"

                    if fk_team == "team1":
                        team1_stats.first_kills += 1
                        team2_stats.first_deaths += 1
                    else:
                        team2_stats.first_kills += 1
                        team1_stats.first_deaths += 1

        return team1_stats, team2_stats

    def _identify_key_rounds(self) -> list[dict]:
        """Identify key rounds (eco wins, clutches, close rounds)."""
        key_rounds = []

        for r in self._rounds:
            if not r.result:
                continue

            economy = self._economy.get(r.round_num)
            if not economy:
                continue

            winner = r.result.winner
            loser = "T" if winner == "CT" else "CT"

            winner_buy = economy.ct_economy.buy_type if winner == "CT" else economy.t_economy.buy_type
            loser_buy = economy.ct_economy.buy_type if loser == "CT" else economy.t_economy.buy_type

            # Eco win (winner on eco beat full buy)
            if winner_buy == BuyType.ECO and loser_buy == BuyType.FULL:
                key_rounds.append({
                    "round": r.round_num,
                    "type": "eco_win",
                    "winner": winner,
                    "description": f"{winner} won eco round vs full buy",
                })

            # Force buy win
            if winner_buy == BuyType.FORCE and loser_buy == BuyType.FULL:
                key_rounds.append({
                    "round": r.round_num,
                    "type": "force_win",
                    "winner": winner,
                    "description": f"{winner} won force buy vs full buy",
                })

            # Bomb-related clutch situations
            if r.result.end_reason == RoundEndReason.CT_WIN_DEFUSE:
                key_rounds.append({
                    "round": r.round_num,
                    "type": "defuse",
                    "winner": "CT",
                    "description": "CT won by defusing bomb",
                })
            elif r.result.end_reason == RoundEndReason.T_WIN_BOMB:
                key_rounds.append({
                    "round": r.round_num,
                    "type": "bomb_explode",
                    "winner": "T",
                    "description": "T won by bomb explosion",
                })

        return key_rounds

    def _analyze_momentum(self) -> list[dict]:
        """Identify momentum swings (3+ round streaks broken)."""
        swings = []
        streak_team = None
        streak_count = 0

        for r in self._rounds:
            if not r.result:
                continue

            winner = r.result.winner

            if winner == streak_team:
                streak_count += 1
            else:
                if streak_count >= 3:
                    swings.append({
                        "round": r.round_num,
                        "type": "momentum_shift",
                        "from_team": streak_team,
                        "to_team": winner,
                        "broken_streak": streak_count,
                        "description": f"{winner} broke {streak_team}'s {streak_count}-round streak",
                    })
                streak_team = winner
                streak_count = 1

        return swings


def analyze_match(demo_path: str) -> MatchSummary:
    """Convenience function to analyze a demo file."""
    parser = DemoParser(demo_path)
    analyzer = MatchAnalyzer(parser)
    return analyzer.analyze()
