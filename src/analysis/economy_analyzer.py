"""Economy analysis module for buy patterns and economic tendencies."""

from dataclasses import dataclass, field

from src.models import RoundState, EconomyState, BuyType
from src.parsers import DemoParser


@dataclass
class BuyPatternStats:
    """Statistics about a team's buy patterns."""

    team: str
    total_rounds: int = 0

    # Buy type distribution
    pistol_rounds: int = 0
    eco_rounds: int = 0
    force_rounds: int = 0
    full_buy_rounds: int = 0
    bonus_rounds: int = 0

    # Win rates by buy type
    eco_wins: int = 0
    force_wins: int = 0
    full_buy_wins: int = 0

    # Economic efficiency
    total_money_spent: int = 0
    rounds_with_awp: int = 0

    @property
    def eco_rate(self) -> float:
        """Percentage of rounds played on eco."""
        return (self.eco_rounds / self.total_rounds * 100) if self.total_rounds > 0 else 0.0

    @property
    def force_rate(self) -> float:
        """Percentage of rounds played on force buy."""
        return (self.force_rounds / self.total_rounds * 100) if self.total_rounds > 0 else 0.0

    @property
    def eco_win_rate(self) -> float:
        return (self.eco_wins / self.eco_rounds * 100) if self.eco_rounds > 0 else 0.0

    @property
    def force_win_rate(self) -> float:
        return (self.force_wins / self.force_rounds * 100) if self.force_rounds > 0 else 0.0

    @property
    def full_buy_win_rate(self) -> float:
        return (self.full_buy_wins / self.full_buy_rounds * 100) if self.full_buy_rounds > 0 else 0.0


@dataclass
class EconomicSwing:
    """Represents a significant economic shift."""

    round_num: int
    team: str
    swing_type: str  # "reset", "recovery", "bonus", "break"
    money_before: int
    money_after: int
    description: str


@dataclass
class EconomySummary:
    """Complete economy analysis summary."""

    team1_patterns: BuyPatternStats  # Team that started CT
    team2_patterns: BuyPatternStats  # Team that started T
    economic_swings: list[EconomicSwing]
    round_by_round: list[dict]
    money_differential: list[tuple[int, int]]  # (round_num, team1_money - team2_money)


class EconomyAnalyzer:
    """Analyzer for economic patterns and tendencies."""

    def __init__(self, parser: DemoParser):
        self.parser = parser
        self._rounds: list[RoundState] | None = None
        self._economy: dict[int, EconomyState] | None = None

    def analyze(self) -> EconomySummary:
        """Run full economy analysis."""
        self._rounds = self.parser.get_rounds()
        self._economy = self.parser.get_economy_by_round()

        team1_patterns = self._analyze_buy_patterns("team1")
        team2_patterns = self._analyze_buy_patterns("team2")
        swings = self._detect_economic_swings()
        round_by_round = self._build_round_timeline()
        money_diff = self._calculate_money_differential()

        return EconomySummary(
            team1_patterns=team1_patterns,
            team2_patterns=team2_patterns,
            economic_swings=swings,
            round_by_round=round_by_round,
            money_differential=money_diff,
        )

    def _analyze_buy_patterns(self, team: str) -> BuyPatternStats:
        """Analyze buy patterns for a specific team.

        Args:
            team: "team1" (started CT) or "team2" (started T)
        """
        stats = BuyPatternStats(team=team)

        for r in self._rounds:
            if not r.result:
                continue

            economy = self._economy.get(r.round_num)
            if not economy:
                continue

            round_num = r.round_num
            is_first_half = round_num <= 12

            # Determine which side this team is on this round
            if team == "team1":
                current_side = "CT" if is_first_half else "T"
            else:
                current_side = "T" if is_first_half else "CT"

            team_economy = economy.ct_economy if current_side == "CT" else economy.t_economy

            # Determine if this team won
            winner_side = r.result.winner
            if is_first_half:
                winning_team = "team1" if winner_side == "CT" else "team2"
            else:
                winning_team = "team2" if winner_side == "CT" else "team1"
            won = winning_team == team

            stats.total_rounds += 1
            stats.total_money_spent += team_economy.equipment_value

            buy_type = team_economy.buy_type

            if buy_type == BuyType.PISTOL:
                stats.pistol_rounds += 1
            elif buy_type == BuyType.ECO:
                stats.eco_rounds += 1
                if won:
                    stats.eco_wins += 1
            elif buy_type == BuyType.FORCE:
                stats.force_rounds += 1
                if won:
                    stats.force_wins += 1
            elif buy_type == BuyType.FULL:
                stats.full_buy_rounds += 1
                if won:
                    stats.full_buy_wins += 1
            elif buy_type == BuyType.BONUS:
                stats.bonus_rounds += 1

        return stats

    def _detect_economic_swings(self) -> list[EconomicSwing]:
        """Detect significant economic shifts (tracks by starting team, not side)."""
        swings = []
        eco_threshold = 2000  # Average per player

        prev_economy: dict[str, int] = {"team1": 0, "team2": 0}

        for r in self._rounds:
            economy = self._economy.get(r.round_num)
            if not economy:
                continue

            round_num = r.round_num
            is_first_half = round_num <= 12

            for team in ["team1", "team2"]:
                # Determine which side this team is on
                if team == "team1":
                    current_side = "CT" if is_first_half else "T"
                else:
                    current_side = "T" if is_first_half else "CT"

                team_econ = economy.ct_economy if current_side == "CT" else economy.t_economy
                current_avg = team_econ.average_money
                prev_avg = prev_economy[team]

                team_label = "Team1" if team == "team1" else "Team2"

                # Detect reset (high to low)
                if prev_avg > 3500 and current_avg < eco_threshold:
                    swings.append(EconomicSwing(
                        round_num=r.round_num,
                        team=team,
                        swing_type="reset",
                        money_before=int(prev_avg),
                        money_after=int(current_avg),
                        description=f"{team_label} was economically reset",
                    ))

                # Detect recovery (low to high)
                elif prev_avg < eco_threshold and current_avg > 3500:
                    swings.append(EconomicSwing(
                        round_num=r.round_num,
                        team=team,
                        swing_type="recovery",
                        money_before=int(prev_avg),
                        money_after=int(current_avg),
                        description=f"{team_label} recovered economy to full buy",
                    ))

                prev_economy[team] = current_avg

        return swings

    def _build_round_timeline(self) -> list[dict]:
        """Build detailed round-by-round economic timeline."""
        timeline = []

        for r in self._rounds:
            economy = self._economy.get(r.round_num)
            if not economy:
                continue

            round_num = r.round_num
            is_first_half = round_num <= 12

            # Map sides to starting teams
            team1_side = "CT" if is_first_half else "T"
            team2_side = "T" if is_first_half else "CT"

            team1_econ = economy.ct_economy if team1_side == "CT" else economy.t_economy
            team2_econ = economy.ct_economy if team2_side == "CT" else economy.t_economy

            # Determine winning team
            if r.result:
                winner_side = r.result.winner
                if is_first_half:
                    winning_team = "team1" if winner_side == "CT" else "team2"
                else:
                    winning_team = "team2" if winner_side == "CT" else "team1"
            else:
                winning_team = None

            entry = {
                "round": r.round_num,
                "team1_money": team1_econ.total_money,
                "team1_avg": team1_econ.average_money,
                "team1_buy": team1_econ.buy_type.value,
                "team1_side": team1_side,
                "team2_money": team2_econ.total_money,
                "team2_avg": team2_econ.average_money,
                "team2_buy": team2_econ.buy_type.value,
                "team2_side": team2_side,
                "winner": winning_team,
                "end_reason": r.result.end_reason.value if r.result else None,
            }
            timeline.append(entry)

        return timeline

    def _calculate_money_differential(self) -> list[tuple[int, int]]:
        """Calculate money differential (team1 - team2) per round."""
        diffs = []

        for r in self._rounds:
            economy = self._economy.get(r.round_num)
            if not economy:
                continue

            round_num = r.round_num
            is_first_half = round_num <= 12

            team1_side = "CT" if is_first_half else "T"
            team1_money = economy.ct_economy.total_money if team1_side == "CT" else economy.t_economy.total_money
            team2_money = economy.t_economy.total_money if team1_side == "CT" else economy.ct_economy.total_money

            diff = team1_money - team2_money
            diffs.append((round_num, diff))

        return diffs

    def get_buy_tendency_by_economy_state(self, team: str) -> dict:
        """
        Analyze buy tendencies based on economic state.

        Args:
            team: "team1" (started CT) or "team2" (started T)

        Returns what the team typically does in different economic situations.
        """
        tendencies = {
            "after_loss": {"eco": 0, "force": 0, "full": 0, "total": 0},
            "after_win": {"eco": 0, "force": 0, "full": 0, "total": 0},
            "low_money": {"eco": 0, "force": 0, "full": 0, "total": 0},  # <$2500 avg
            "medium_money": {"eco": 0, "force": 0, "full": 0, "total": 0},  # $2500-$4000
            "high_money": {"eco": 0, "force": 0, "full": 0, "total": 0},  # >$4000
        }

        prev_won: bool | None = None

        for r in self._rounds:
            if not r.result:
                continue

            economy = self._economy.get(r.round_num)
            if not economy:
                continue

            round_num = r.round_num
            is_first_half = round_num <= 12

            # Determine which side this team is on
            if team == "team1":
                current_side = "CT" if is_first_half else "T"
            else:
                current_side = "T" if is_first_half else "CT"

            team_econ = economy.ct_economy if current_side == "CT" else economy.t_economy
            buy_type = team_econ.buy_type.value

            # Determine if this team won
            winner_side = r.result.winner
            if is_first_half:
                winning_team = "team1" if winner_side == "CT" else "team2"
            else:
                winning_team = "team2" if winner_side == "CT" else "team1"
            won = winning_team == team

            # Skip pistol rounds for tendency analysis
            if buy_type == "pistol":
                prev_won = won
                continue

            # Categorize buy type
            if buy_type == "eco":
                buy_cat = "eco"
            elif buy_type == "force":
                buy_cat = "force"
            else:
                buy_cat = "full"

            # After win/loss tendencies
            if prev_won is not None:
                key = "after_win" if prev_won else "after_loss"
                tendencies[key][buy_cat] += 1
                tendencies[key]["total"] += 1

            # Money-based tendencies
            avg_money = team_econ.average_money
            if avg_money < 2500:
                key = "low_money"
            elif avg_money < 4000:
                key = "medium_money"
            else:
                key = "high_money"

            tendencies[key][buy_cat] += 1
            tendencies[key]["total"] += 1

            prev_won = won

        return tendencies

    def get_economy_impact_on_wins(self, team: str) -> dict:
        """Analyze how economy affects win probability.

        Args:
            team: "team1" (started CT) or "team2" (started T)
        """
        buckets = {
            "disadvantage_large": {"wins": 0, "total": 0},  # >$5000 behind
            "disadvantage_small": {"wins": 0, "total": 0},  # $1000-$5000 behind
            "even": {"wins": 0, "total": 0},  # Within $1000
            "advantage_small": {"wins": 0, "total": 0},  # $1000-$5000 ahead
            "advantage_large": {"wins": 0, "total": 0},  # >$5000 ahead
        }

        for r in self._rounds:
            if not r.result:
                continue

            economy = self._economy.get(r.round_num)
            if not economy:
                continue

            round_num = r.round_num
            is_first_half = round_num <= 12

            # Determine which side this team is on
            if team == "team1":
                current_side = "CT" if is_first_half else "T"
            else:
                current_side = "T" if is_first_half else "CT"

            team_money = economy.ct_economy.total_money if current_side == "CT" else economy.t_economy.total_money
            opp_money = economy.t_economy.total_money if current_side == "CT" else economy.ct_economy.total_money

            diff = team_money - opp_money

            # Determine if this team won
            winner_side = r.result.winner
            if is_first_half:
                winning_team = "team1" if winner_side == "CT" else "team2"
            else:
                winning_team = "team2" if winner_side == "CT" else "team1"
            won = winning_team == team

            if diff < -5000:
                bucket = "disadvantage_large"
            elif diff < -1000:
                bucket = "disadvantage_small"
            elif diff <= 1000:
                bucket = "even"
            elif diff <= 5000:
                bucket = "advantage_small"
            else:
                bucket = "advantage_large"

            buckets[bucket]["total"] += 1
            if won:
                buckets[bucket]["wins"] += 1

        # Calculate win rates
        for bucket in buckets.values():
            bucket["win_rate"] = (bucket["wins"] / bucket["total"] * 100) if bucket["total"] > 0 else 0

        return buckets


def analyze_economy(demo_path: str) -> EconomySummary:
    """Convenience function to analyze economy from a demo file."""
    parser = DemoParser(demo_path)
    analyzer = EconomyAnalyzer(parser)
    return analyzer.analyze()
