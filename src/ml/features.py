"""Feature extraction for ML models."""

from src.parsers import DemoParser
from src.models import BuyType


class RoundFeatureExtractor:
    """Extract features for round-level prediction."""

    # Buy type encoding
    BUY_TYPE_MAP = {
        BuyType.PISTOL: 0,
        BuyType.ECO: 1,
        BuyType.FORCE: 2,
        BuyType.FULL: 3,
        BuyType.BONUS: 4,
    }

    def __init__(self, parser: DemoParser):
        self.parser = parser
        self._rounds = parser.get_rounds()
        self._economy = parser.get_economy_by_round()
        self._kills = None  # Lazy load

    def extract_round_features(self, round_num: int) -> dict | None:
        """
        Extract features for a single round.

        Returns dict of features or None if round data unavailable.
        """
        economy = self._economy.get(round_num)
        if not economy:
            return None

        # Find the round state
        round_state = None
        for r in self._rounds:
            if r.round_num == round_num:
                round_state = r
                break

        if not round_state:
            return None

        is_first_half = round_num <= 12

        # Map economy to team1 (started CT) and team2 (started T)
        if is_first_half:
            team1_econ = economy.ct_economy
            team2_econ = economy.t_economy
            team1_side = "CT"
            team2_side = "T"
        else:
            team1_econ = economy.t_economy
            team2_econ = economy.ct_economy
            team1_side = "T"
            team2_side = "CT"

        # Get previous round result for momentum features
        prev_round_winner = None
        if round_num > 1:
            for r in self._rounds:
                if r.round_num == round_num - 1 and r.result:
                    prev_winner_side = r.result.winner
                    prev_first_half = (round_num - 1) <= 12
                    if prev_first_half:
                        prev_round_winner = "team1" if prev_winner_side == "CT" else "team2"
                    else:
                        prev_round_winner = "team1" if prev_winner_side == "T" else "team2"
                    break

        # Calculate score at start of this round
        team1_score = 0
        team2_score = 0
        for r in self._rounds:
            if r.round_num >= round_num:
                break
            if r.result:
                r_first_half = r.round_num <= 12
                if r_first_half:
                    if r.result.winner == "CT":
                        team1_score += 1
                    else:
                        team2_score += 1
                else:
                    if r.result.winner == "T":
                        team1_score += 1
                    else:
                        team2_score += 1

        features = {
            # Round context
            "round_num": round_num,
            "is_first_half": int(is_first_half),
            "is_pistol": int(round_num in (1, 13)),
            "is_second_pistol": int(round_num == 13),

            # Team1 (started CT) features
            "team1_side_is_ct": int(team1_side == "CT"),
            "team1_total_money": team1_econ.total_money,
            "team1_avg_money": team1_econ.average_money,
            "team1_equipment_value": team1_econ.equipment_value,
            "team1_buy_type": self.BUY_TYPE_MAP.get(team1_econ.buy_type, 0),
            "team1_is_eco": int(team1_econ.buy_type == BuyType.ECO),
            "team1_is_force": int(team1_econ.buy_type == BuyType.FORCE),
            "team1_is_full": int(team1_econ.buy_type in (BuyType.FULL, BuyType.BONUS)),

            # Team2 (started T) features
            "team2_total_money": team2_econ.total_money,
            "team2_avg_money": team2_econ.average_money,
            "team2_equipment_value": team2_econ.equipment_value,
            "team2_buy_type": self.BUY_TYPE_MAP.get(team2_econ.buy_type, 0),
            "team2_is_eco": int(team2_econ.buy_type == BuyType.ECO),
            "team2_is_force": int(team2_econ.buy_type == BuyType.FORCE),
            "team2_is_full": int(team2_econ.buy_type in (BuyType.FULL, BuyType.BONUS)),

            # Relative features
            "money_diff": team1_econ.total_money - team2_econ.total_money,
            "equip_diff": team1_econ.equipment_value - team2_econ.equipment_value,
            "money_ratio": team1_econ.total_money / max(team2_econ.total_money, 1),

            # Score features
            "team1_score": team1_score,
            "team2_score": team2_score,
            "score_diff": team1_score - team2_score,

            # Momentum features
            "team1_won_prev": int(prev_round_winner == "team1") if prev_round_winner else 0,
            "team2_won_prev": int(prev_round_winner == "team2") if prev_round_winner else 0,
        }

        return features

    def extract_all_rounds(self) -> list[dict]:
        """Extract features for all rounds."""
        features = []
        for r in self._rounds:
            if r.result:
                f = self.extract_round_features(r.round_num)
                if f:
                    features.append(f)
        return features
