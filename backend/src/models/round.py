"""Round state and result models."""

from enum import Enum

from pydantic import BaseModel


class RoundEndReason(str, Enum):
    """How a round ended."""

    CT_WIN_ELIMINATION = "ct_win_elimination"
    CT_WIN_DEFUSE = "ct_win_defuse"
    CT_WIN_TIME = "ct_win_time"
    T_WIN_ELIMINATION = "t_win_elimination"
    T_WIN_BOMB = "t_win_bomb"
    UNKNOWN = "unknown"


class RoundResult(BaseModel):
    """Result of a completed round."""

    round_num: int
    winner: str  # "CT" or "T"
    end_reason: RoundEndReason
    ct_score: int
    t_score: int


class RoundState(BaseModel):
    """State tracking for a round."""

    round_num: int
    start_tick: int
    end_tick: int | None = None
    freeze_end_tick: int | None = None  # When buy time ends

    # Result (populated when round ends)
    result: RoundResult | None = None

    @property
    def duration_ticks(self) -> int | None:
        if self.end_tick is None:
            return None
        return self.end_tick - self.start_tick

    @property
    def is_complete(self) -> bool:
        return self.result is not None
