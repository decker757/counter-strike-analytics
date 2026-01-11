"""Event extraction utilities for demo parsing."""

from src.models import Kill, GrenadeEvent, DamageEvent


def detect_trade_kills(kills: list[Kill], trade_window_ms: int = 5000, tickrate: int = 64) -> list[Kill]:
    """
    Detect trade kills and mark them.

    A trade kill occurs when a player is killed shortly after getting a kill.

    Args:
        kills: List of kills to analyze
        trade_window_ms: Time window in milliseconds to consider a trade
        tickrate: Demo tickrate for time calculation

    Returns:
        Same kills list with is_trade and trade_window_ticks populated
    """
    trade_window_ticks = int((trade_window_ms / 1000) * tickrate)

    # Group kills by round
    kills_by_round: dict[int, list[Kill]] = {}
    for kill in kills:
        if kill.round_num not in kills_by_round:
            kills_by_round[kill.round_num] = []
        kills_by_round[kill.round_num].append(kill)

    # Check each kill for trade potential
    for round_num, round_kills in kills_by_round.items():
        # Sort by tick
        round_kills.sort(key=lambda k: k.tick)

        for i, kill in enumerate(round_kills):
            if kill.attacker_steamid is None:
                continue

            # Check if the attacker was killed recently (making this kill a trade)
            for j in range(i - 1, -1, -1):
                prev_kill = round_kills[j]
                tick_diff = kill.tick - prev_kill.tick

                if tick_diff > trade_window_ticks:
                    break

                # Check if this kill's attacker was the victim of the previous kill
                # and the killer is on the same team as the traded teammate
                if (
                    prev_kill.victim_steamid == kill.attacker_steamid
                    and prev_kill.victim_team == kill.attacker_team
                ):
                    kill.is_trade = True
                    kill.trade_window_ticks = tick_diff
                    break

    return kills


def calculate_adr(damage_events: list[DamageEvent], rounds_played: int) -> dict[str, float]:
    """
    Calculate Average Damage per Round for each player.

    Args:
        damage_events: List of damage events
        rounds_played: Total rounds played

    Returns:
        Dictionary mapping steamid to ADR
    """
    damage_by_player: dict[str, int] = {}

    for event in damage_events:
        if event.attacker_steamid is None:
            continue
        if event.attacker_team == event.victim_team:
            continue  # Exclude team damage

        if event.attacker_steamid not in damage_by_player:
            damage_by_player[event.attacker_steamid] = 0
        damage_by_player[event.attacker_steamid] += event.damage

    return {
        steamid: damage / rounds_played
        for steamid, damage in damage_by_player.items()
    }


def get_opening_duels(kills: list[Kill]) -> list[tuple[Kill, bool]]:
    """
    Extract opening duels (first kill of each round).

    Returns:
        List of tuples (kill, won_round) where won_round indicates
        if the team that got the opening kill won the round
    """
    # Group by round
    kills_by_round: dict[int, list[Kill]] = {}
    for kill in kills:
        if kill.round_num not in kills_by_round:
            kills_by_round[kill.round_num] = []
        kills_by_round[kill.round_num].append(kill)

    opening_kills = []
    for round_num, round_kills in kills_by_round.items():
        if not round_kills:
            continue

        # Get first kill of round
        round_kills.sort(key=lambda k: k.tick)
        first_kill = round_kills[0]
        opening_kills.append((first_kill, None))  # Won round status would need round result

    return opening_kills


def get_multikills(kills: list[Kill]) -> dict[str, dict[int, int]]:
    """
    Count multi-kills (2k, 3k, 4k, 5k) per player.

    Returns:
        Dict mapping steamid -> {2: count, 3: count, 4: count, 5: count}
    """
    # Group kills by round and player
    kills_by_round_player: dict[int, dict[str, int]] = {}

    for kill in kills:
        if kill.attacker_steamid is None:
            continue

        if kill.round_num not in kills_by_round_player:
            kills_by_round_player[kill.round_num] = {}

        player_kills = kills_by_round_player[kill.round_num]
        if kill.attacker_steamid not in player_kills:
            player_kills[kill.attacker_steamid] = 0
        player_kills[kill.attacker_steamid] += 1

    # Aggregate multi-kill counts
    multikills: dict[str, dict[int, int]] = {}

    for round_num, player_kills in kills_by_round_player.items():
        for steamid, kill_count in player_kills.items():
            if kill_count >= 2:
                if steamid not in multikills:
                    multikills[steamid] = {2: 0, 3: 0, 4: 0, 5: 0}
                if kill_count >= 5:
                    multikills[steamid][5] += 1
                elif kill_count >= 4:
                    multikills[steamid][4] += 1
                elif kill_count >= 3:
                    multikills[steamid][3] += 1
                else:
                    multikills[steamid][2] += 1

    return multikills


def filter_grenade_events(
    events: list[GrenadeEvent],
    grenade_type: str | None = None,
    min_enemies_affected: int = 0,
) -> list[GrenadeEvent]:
    """
    Filter grenade events by type and effectiveness.

    Args:
        events: List of grenade events
        grenade_type: Filter by type (smoke, flashbang, hegrenade, molotov, etc.)
        min_enemies_affected: Minimum enemies affected (for flashes)

    Returns:
        Filtered list of events
    """
    filtered = events

    if grenade_type:
        filtered = [e for e in filtered if e.grenade_type == grenade_type]

    if min_enemies_affected > 0:
        filtered = [e for e in filtered if e.enemies_flashed >= min_enemies_affected]

    return filtered
