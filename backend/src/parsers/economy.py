"""Economy analysis utilities."""

from src.models import EconomyState, BuyType, RoundState, RoundResult
from src.utils.config import get_economy_config


def classify_buy_type(
    average_money: float,
    round_num: int,
    previous_round_won: bool | None = None,
    previous_buy_type: BuyType | None = None,
) -> BuyType:
    """
    Classify the buy type based on average team money and context.

    Args:
        average_money: Average money per player on the team
        round_num: Current round number
        previous_round_won: Whether team won the previous round
        previous_buy_type: What the team bought previous round

    Returns:
        BuyType classification
    """
    config = get_economy_config()
    eco_max = config["buy_thresholds"]["eco_max"]
    force_max = config["buy_thresholds"]["force_max"]

    # Pistol rounds
    if round_num in (1, 13):
        return BuyType.PISTOL

    # Check for bonus round (won previous eco/force)
    if (
        previous_round_won
        and previous_buy_type in (BuyType.ECO, BuyType.FORCE)
        and average_money >= force_max
    ):
        return BuyType.BONUS

    # Standard classification
    if average_money < eco_max:
        return BuyType.ECO
    if average_money < force_max:
        return BuyType.FORCE
    return BuyType.FULL


def calculate_loss_bonus(consecutive_losses: int) -> int:
    """
    Calculate loss bonus amount based on loss streak.

    Args:
        consecutive_losses: Number of rounds lost in a row

    Returns:
        Loss bonus amount in dollars
    """
    config = get_economy_config()
    base = config["loss_bonus"]["base"]
    increment = config["loss_bonus"]["increment"]
    max_streak = config["loss_bonus"]["max_streak"]

    streak = min(consecutive_losses, max_streak)
    return base + (streak * increment)


def get_economy_timeline(
    economy_states: dict[int, EconomyState],
    rounds: list[RoundState],
) -> list[dict]:
    """
    Build a timeline of economy states with round results.

    Args:
        economy_states: Economy state by round number
        rounds: List of round states with results

    Returns:
        List of dicts with economy and result info per round
    """
    timeline = []

    for round_state in rounds:
        economy = economy_states.get(round_state.round_num)
        if not economy:
            continue

        entry = {
            "round_num": round_state.round_num,
            "ct_buy_type": economy.ct_economy.buy_type.value,
            "t_buy_type": economy.t_economy.buy_type.value,
            "ct_total_money": economy.ct_economy.total_money,
            "t_total_money": economy.t_economy.total_money,
            "ct_equipment_value": economy.ct_economy.equipment_value,
            "t_equipment_value": economy.t_economy.equipment_value,
            "winner": round_state.result.winner if round_state.result else None,
            "end_reason": round_state.result.end_reason.value if round_state.result else None,
        }
        timeline.append(entry)

    return timeline


def analyze_eco_round_performance(
    economy_states: dict[int, EconomyState],
    rounds: list[RoundState],
    team: str,
) -> dict:
    """
    Analyze how well a team performs on eco rounds.

    Args:
        economy_states: Economy state by round number
        rounds: Round states with results
        team: Team to analyze ("CT" or "T")

    Returns:
        Stats about eco round performance
    """
    eco_rounds = 0
    eco_wins = 0
    force_rounds = 0
    force_wins = 0

    for round_state in rounds:
        if not round_state.result:
            continue

        economy = economy_states.get(round_state.round_num)
        if not economy:
            continue

        team_economy = economy.ct_economy if team == "CT" else economy.t_economy
        won = round_state.result.winner == team

        if team_economy.buy_type == BuyType.ECO:
            eco_rounds += 1
            if won:
                eco_wins += 1
        elif team_economy.buy_type == BuyType.FORCE:
            force_rounds += 1
            if won:
                force_wins += 1

    return {
        "eco_rounds": eco_rounds,
        "eco_wins": eco_wins,
        "eco_win_rate": eco_wins / eco_rounds if eco_rounds > 0 else 0,
        "force_rounds": force_rounds,
        "force_wins": force_wins,
        "force_win_rate": force_wins / force_rounds if force_rounds > 0 else 0,
    }


def detect_economic_resets(
    economy_states: dict[int, EconomyState],
    rounds: list[RoundState],
) -> list[int]:
    """
    Detect rounds where a team was economically reset (forced to eco after loss).

    Returns:
        List of round numbers where economic resets occurred
    """
    reset_rounds = []
    config = get_economy_config()
    eco_threshold = config["buy_thresholds"]["eco_max"]

    prev_round: RoundState | None = None

    for round_state in rounds:
        if prev_round and prev_round.result:
            economy = economy_states.get(round_state.round_num)
            if not economy:
                continue

            loser = "T" if prev_round.result.winner == "CT" else "CT"
            loser_economy = economy.ct_economy if loser == "CT" else economy.t_economy

            # Reset detected if team lost and now has eco money
            if loser_economy.average_money < eco_threshold:
                reset_rounds.append(round_state.round_num)

        prev_round = round_state

    return reset_rounds
