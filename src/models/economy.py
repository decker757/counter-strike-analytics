"""Economy state and buy type models."""

from enum import Enum

from pydantic import BaseModel


class BuyType(str, Enum):
    """Classification of team buy for a round."""

    PISTOL = "pistol"  # Pistol rounds (1, 16)
    ECO = "eco"  # Saving money (<$2000 average)
    FORCE = "force"  # Force buy ($2000-$3500 average)
    FULL = "full"  # Full buy (>$3500 average)
    BONUS = "bonus"  # Won previous round on eco/force


class TeamEconomy(BaseModel):
    """Economy state for a team at round start."""

    team: str  # "CT" or "T"
    round_num: int

    # Individual player money
    player_money: dict[str, int]  # steamid -> money

    # Aggregates
    total_money: int
    average_money: float
    equipment_value: int

    # Classification
    buy_type: BuyType
    loss_bonus: int = 0  # 1-4 indicating loss streak bonus level

    @property
    def player_count(self) -> int:
        return len(self.player_money)


class EconomyState(BaseModel):
    """Full economy snapshot at round start."""

    round_num: int
    ct_economy: TeamEconomy
    t_economy: TeamEconomy

    @property
    def ct_total(self) -> int:
        return self.ct_economy.total_money

    @property
    def t_total(self) -> int:
        return self.t_economy.total_money

    @property
    def economy_advantage(self) -> str:
        """Which team has economic advantage."""
        diff = self.ct_total - self.t_total
        if abs(diff) < 5000:
            return "even"
        return "CT" if diff > 0 else "T"
