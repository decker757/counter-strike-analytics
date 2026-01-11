"""Match and team models."""

from pydantic import BaseModel

from .round import RoundState


class Team(BaseModel):
    """Team information."""

    name: str | None = None
    clan_tag: str | None = None
    players: dict[str, str]  # steamid -> player name


class Match(BaseModel):
    """Complete match data."""

    demo_path: str
    map_name: str

    # Teams
    team_ct: Team
    team_t: Team

    # Match structure
    rounds: list[RoundState]

    # Final score
    ct_score: int = 0
    t_score: int = 0

    @property
    def total_rounds(self) -> int:
        return len(self.rounds)

    @property
    def winner(self) -> str | None:
        if self.ct_score >= 13:
            return "CT"
        elif self.t_score >= 13:
            return "T"
        return None  # Draw or incomplete

    @property
    def is_complete(self) -> bool:
        """Check if match reached a conclusion (13 wins or OT finish)."""
        return self.ct_score >= 13 or self.t_score >= 13

    @property
    def is_overtime(self) -> bool:
        return self.ct_score >= 13 and self.t_score >= 13
