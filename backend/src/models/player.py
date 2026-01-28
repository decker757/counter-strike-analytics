"""Player state and frame models."""

from pydantic import BaseModel


class PlayerState(BaseModel):
    """Snapshot of a player's state at a specific tick."""

    tick: int
    steamid: str
    name: str
    team: str  # "CT" or "T"

    # Position
    x: float
    y: float
    z: float

    # Status
    is_alive: bool
    health: int = 100
    armor: int = 0
    has_helmet: bool = False
    has_defuser: bool = False

    # Economy
    money: int = 0
    equipment_value: int = 0

    # Inventory (weapon names)
    active_weapon: str | None = None
    weapons: list[str] = []

    # Computed fields
    round_num: int | None = None


class PlayerFrame(BaseModel):
    """All player states for a single tick."""

    tick: int
    round_num: int | None = None
    players: list[PlayerState]

    @property
    def ct_players(self) -> list[PlayerState]:
        return [p for p in self.players if p.team == "CT"]

    @property
    def t_players(self) -> list[PlayerState]:
        return [p for p in self.players if p.team == "T"]

    @property
    def ct_alive(self) -> int:
        return sum(1 for p in self.ct_players if p.is_alive)

    @property
    def t_alive(self) -> int:
        return sum(1 for p in self.t_players if p.is_alive)
