"""Demo parsing and extraction layer."""

from .demo_parser import DemoParser
from .events import (
    detect_trade_kills,
    calculate_adr,
    get_opening_duels,
    get_multikills,
    filter_grenade_events,
)
from .economy import (
    classify_buy_type,
    calculate_loss_bonus,
    get_economy_timeline,
    analyze_eco_round_performance,
    detect_economic_resets,
)
from .player_state import (
    calculate_team_spread,
    calculate_team_centroid,
    get_alive_players,
    calculate_player_velocity,
    detect_rotation,
    get_player_positions_by_round,
)

__all__ = [
    # Main parser
    "DemoParser",
    # Event utilities
    "detect_trade_kills",
    "calculate_adr",
    "get_opening_duels",
    "get_multikills",
    "filter_grenade_events",
    # Economy utilities
    "classify_buy_type",
    "calculate_loss_bonus",
    "get_economy_timeline",
    "analyze_eco_round_performance",
    "detect_economic_resets",
    # Player state utilities
    "calculate_team_spread",
    "calculate_team_centroid",
    "get_alive_players",
    "calculate_player_velocity",
    "detect_rotation",
    "get_player_positions_by_round",
]
