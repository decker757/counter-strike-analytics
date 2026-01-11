"""Player state extraction and analysis utilities."""

import math

from src.models import PlayerFrame, PlayerState


def calculate_team_spread(players: list[PlayerState]) -> float:
    """
    Calculate how spread out a team is (standard deviation of distances from centroid).

    Higher values = more spread out, lower values = grouped together.
    """
    if len(players) < 2:
        return 0.0

    # Calculate centroid
    centroid_x = sum(p.x for p in players) / len(players)
    centroid_y = sum(p.y for p in players) / len(players)

    # Calculate distances from centroid
    distances = []
    for p in players:
        dist = math.sqrt((p.x - centroid_x) ** 2 + (p.y - centroid_y) ** 2)
        distances.append(dist)

    # Return standard deviation
    mean_dist = sum(distances) / len(distances)
    variance = sum((d - mean_dist) ** 2 for d in distances) / len(distances)
    return math.sqrt(variance)


def calculate_team_centroid(players: list[PlayerState]) -> tuple[float, float, float]:
    """Calculate the centroid (average position) of a team."""
    if not players:
        return (0.0, 0.0, 0.0)

    return (
        sum(p.x for p in players) / len(players),
        sum(p.y for p in players) / len(players),
        sum(p.z for p in players) / len(players),
    )


def get_alive_players(frame: PlayerFrame, team: str | None = None) -> list[PlayerState]:
    """Get alive players from a frame, optionally filtered by team."""
    players = frame.players
    if team:
        players = [p for p in players if p.team == team]
    return [p for p in players if p.is_alive]


def calculate_player_velocity(
    current: PlayerState,
    previous: PlayerState,
    tick_interval: int,
    tickrate: int = 64,
) -> float:
    """
    Calculate player velocity between two states.

    Returns:
        Velocity in units per second
    """
    if tick_interval == 0:
        return 0.0

    dx = current.x - previous.x
    dy = current.y - previous.y
    dz = current.z - previous.z

    distance = math.sqrt(dx**2 + dy**2 + dz**2)
    time_seconds = tick_interval / tickrate

    return distance / time_seconds


def detect_rotation(
    frames: list[PlayerFrame],
    player_steamid: str,
    distance_threshold: float = 500.0,
) -> list[dict]:
    """
    Detect significant player rotations (large position changes).

    Args:
        frames: Sequence of player frames
        player_steamid: Player to track
        distance_threshold: Minimum distance to consider a rotation

    Returns:
        List of rotation events with tick, start/end positions
    """
    rotations = []
    prev_pos = None
    prev_tick = None

    for frame in frames:
        player = next((p for p in frame.players if p.steamid == player_steamid), None)
        if not player or not player.is_alive:
            prev_pos = None
            prev_tick = None
            continue

        current_pos = (player.x, player.y)

        if prev_pos is not None:
            distance = math.sqrt(
                (current_pos[0] - prev_pos[0]) ** 2 +
                (current_pos[1] - prev_pos[1]) ** 2
            )

            if distance >= distance_threshold:
                rotations.append({
                    "start_tick": prev_tick,
                    "end_tick": frame.tick,
                    "start_pos": prev_pos,
                    "end_pos": current_pos,
                    "distance": distance,
                    "round_num": frame.round_num,
                })

        prev_pos = current_pos
        prev_tick = frame.tick

    return rotations


def get_player_positions_by_round(
    frames: list[PlayerFrame],
    round_num: int,
) -> dict[str, list[tuple[float, float]]]:
    """
    Get all positions for each player in a specific round.

    Returns:
        Dict mapping steamid to list of (x, y) positions
    """
    positions: dict[str, list[tuple[float, float]]] = {}

    for frame in frames:
        if frame.round_num != round_num:
            continue

        for player in frame.players:
            if not player.is_alive:
                continue

            if player.steamid not in positions:
                positions[player.steamid] = []
            positions[player.steamid].append((player.x, player.y))

    return positions
