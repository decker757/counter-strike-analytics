"""Main demo parser wrapper around demoparser2."""

from pathlib import Path

import pandas as pd
from demoparser2 import DemoParser as DemoParser2

from src.models import (
    Match,
    Team,
    RoundState,
    RoundResult,
    RoundEndReason,
    PlayerState,
    PlayerFrame,
    Kill,
    BombEvent,
    EconomyState,
    TeamEconomy,
    BuyType,
)
from src.utils.config import get_economy_config


class DemoParser:
    """High-level interface for parsing CS2 demo files."""

    # Fields to extract for player state
    PLAYER_FIELDS = [
        "tick",
        "steamid",
        "name",
        "team_name",
        "X",
        "Y",
        "Z",
        "health",
        "armor_value",
        "has_helmet",
        "has_defuser",
        "current_equip_value",
        "cash_spent_this_round",
        "start_balance",
        "active_weapon",
        "is_alive",
    ]

    def __init__(self, demo_path: str | Path):
        self.demo_path = Path(demo_path)
        if not self.demo_path.exists():
            raise FileNotFoundError(f"Demo file not found: {self.demo_path}")

        self._parser = DemoParser2(str(self.demo_path))
        self._header = self._parser.parse_header()

        # Cached data
        self._rounds: list[RoundState] | None = None
        self._kills: list[Kill] | None = None
        self._economy: dict[int, EconomyState] | None = None

    @property
    def map_name(self) -> str:
        """Get the map name from demo header."""
        return self._header.get("map_name", "unknown")

    @property
    def tickrate(self) -> int:
        """Get the demo tickrate."""
        return self._header.get("tickrate", 64)

    def get_rounds(self) -> list[RoundState]:
        """Parse and return round information."""
        if self._rounds is not None:
            return self._rounds

        round_start = self._parser.parse_event("round_start")
        round_end = self._parser.parse_event("round_end")

        try:
            round_freeze_end = self._parser.parse_event("round_freeze_end")
        except Exception:
            round_freeze_end = pd.DataFrame(columns=["tick"])

        # Deduplicate by taking the last occurrence of each round
        round_start = round_start.drop_duplicates(subset=["round"], keep="last")
        round_end_dedup = round_end.drop_duplicates(subset=["round"], keep="last")

        # Use round_end as the authoritative source for which rounds were played
        # (round_start may have warmup rounds, round_end only has real rounds)
        all_round_nums = sorted(round_end_dedup["round"].unique())

        rounds = []
        ct_score = 0
        t_score = 0

        for round_num in all_round_nums:
            # Find round_start for this round (if exists)
            start_row = round_start[round_start["round"] == round_num]
            if len(start_row) > 0:
                start_tick = int(start_row["tick"].iloc[0])
            else:
                # Estimate from previous round or use round_end tick
                start_tick = None

            # Find round_end for this round
            end_row = round_end_dedup[round_end_dedup["round"] == round_num]
            end_tick = int(end_row["tick"].iloc[0]) if len(end_row) > 0 else None

            # Find freeze end tick
            if start_tick is not None:
                freeze_row = round_freeze_end[
                    (round_freeze_end["tick"] > start_tick)
                    & (round_freeze_end["tick"] < (end_tick or float("inf")))
                ].head(1)
                freeze_end_tick = int(freeze_row["tick"].iloc[0]) if len(freeze_row) > 0 else None
            else:
                freeze_end_tick = None

            # Parse result from round_end
            result = None
            if len(end_row) > 0:
                # CS2 returns winner as string "CT" or "T"
                winner = str(end_row["winner"].iloc[0]).upper()
                if winner not in ("CT", "T"):
                    winner = "unknown"

                # CS2 returns reason as string like "ct_killed", "t_killed", "bomb_exploded", etc.
                reason_str = str(end_row["reason"].iloc[0]).lower()
                end_reason = self._parse_round_end_reason(reason_str, winner)

                # Update scores
                if winner == "CT":
                    ct_score += 1
                elif winner == "T":
                    t_score += 1

                result = RoundResult(
                    round_num=int(round_num),
                    winner=winner,
                    end_reason=end_reason,
                    ct_score=ct_score,
                    t_score=t_score,
                )

            rounds.append(
                RoundState(
                    round_num=int(round_num),
                    start_tick=start_tick or (end_tick - 10000 if end_tick else 0),
                    end_tick=end_tick,
                    freeze_end_tick=freeze_end_tick,
                    result=result,
                )
            )

        self._rounds = rounds
        return rounds

    def _parse_round_end_reason(self, reason: str, winner: str) -> RoundEndReason:
        """Convert CS2 reason string to RoundEndReason enum."""
        reason = reason.lower()

        if "bomb_exploded" in reason or "target_bombed" in reason:
            return RoundEndReason.T_WIN_BOMB
        elif "bomb_defused" in reason or "defuse" in reason:
            return RoundEndReason.CT_WIN_DEFUSE
        elif "time" in reason or "round_draw" in reason:
            return RoundEndReason.CT_WIN_TIME
        elif "ct_killed" in reason or "ct_win" in reason:
            return RoundEndReason.CT_WIN_ELIMINATION
        elif "t_killed" in reason or "t_win" in reason:
            return RoundEndReason.T_WIN_ELIMINATION
        elif winner == "CT":
            return RoundEndReason.CT_WIN_ELIMINATION
        elif winner == "T":
            return RoundEndReason.T_WIN_ELIMINATION

        return RoundEndReason.UNKNOWN

    def get_kills(self) -> list[Kill]:
        """Parse and return all kills."""
        if self._kills is not None:
            return self._kills

        kills_df = self._parser.parse_event("player_death")
        rounds = self.get_rounds()

        kills = []
        for _, row in kills_df.iterrows():
            tick = int(row["tick"])
            round_num = self._tick_to_round(tick, rounds)

            kill = Kill(
                tick=tick,
                round_num=round_num,
                attacker_steamid=str(row.get("attacker_steamid")) if pd.notna(row.get("attacker_steamid")) else None,
                attacker_name=row.get("attacker_name"),
                attacker_team=self._normalize_team(row.get("attacker_team_name")),
                victim_steamid=str(row["user_steamid"]),
                victim_name=row["user_name"],
                victim_team=self._normalize_team(row.get("user_team_name")),
                victim_x=float(row.get("user_X", 0)),
                victim_y=float(row.get("user_Y", 0)),
                victim_z=float(row.get("user_Z", 0)),
                weapon=row.get("weapon", "unknown"),
                headshot=bool(row.get("headshot", False)),
                penetrated=bool(row.get("penetrated", False)),
                noscope=bool(row.get("noscope", False)),
                thrusmoke=bool(row.get("thrusmoke", False)),
                attackerblind=bool(row.get("attackerblind", False)),
                assister_steamid=str(row.get("assister_steamid")) if pd.notna(row.get("assister_steamid")) else None,
                assister_name=row.get("assister_name"),
                flash_assist=bool(row.get("assistedflash", False)),
            )
            kills.append(kill)

        self._kills = kills
        return kills

    def get_bomb_events(self) -> list[BombEvent]:
        """Parse bomb-related events."""
        events = []

        # Bomb planted
        try:
            planted = self._parser.parse_event("bomb_planted")
            rounds = self.get_rounds()
            for _, row in planted.iterrows():
                tick = int(row["tick"])
                events.append(
                    BombEvent(
                        tick=tick,
                        round_num=self._tick_to_round(tick, rounds),
                        event_type="plant",
                        player_steamid=str(row.get("user_steamid")),
                        player_name=row.get("user_name"),
                        x=float(row.get("user_X", 0)),
                        y=float(row.get("user_Y", 0)),
                        z=float(row.get("user_Z", 0)),
                        site=row.get("site"),
                    )
                )
        except Exception:
            pass

        # Bomb defused
        try:
            defused = self._parser.parse_event("bomb_defused")
            for _, row in defused.iterrows():
                tick = int(row["tick"])
                events.append(
                    BombEvent(
                        tick=tick,
                        round_num=self._tick_to_round(tick, rounds),
                        event_type="defuse",
                        player_steamid=str(row.get("user_steamid")),
                        player_name=row.get("user_name"),
                    )
                )
        except Exception:
            pass

        # Bomb exploded
        try:
            exploded = self._parser.parse_event("bomb_exploded")
            for _, row in exploded.iterrows():
                tick = int(row["tick"])
                events.append(
                    BombEvent(
                        tick=tick,
                        round_num=self._tick_to_round(tick, rounds),
                        event_type="explode",
                    )
                )
        except Exception:
            pass

        return sorted(events, key=lambda e: e.tick)

    def get_player_frames(
        self,
        tick_interval: int = 1,
        rounds: list[int] | None = None,
    ) -> list[PlayerFrame]:
        """
        Get player state frames.

        Args:
            tick_interval: Sample every N ticks (1 = every tick)
            rounds: Only return frames for these rounds (None = all)

        Returns:
            List of PlayerFrame objects with all player states per tick
        """
        df = self._parser.parse_ticks(self.PLAYER_FIELDS)
        round_states = self.get_rounds()

        # Add round number to each row
        df["round_num"] = df["tick"].apply(lambda t: self._tick_to_round(t, round_states))

        # Filter by rounds if specified
        if rounds:
            df = df[df["round_num"].isin(rounds)]

        # Sample ticks
        if tick_interval > 1:
            unique_ticks = df["tick"].unique()[::tick_interval]
            df = df[df["tick"].isin(unique_ticks)]

        # Group by tick and build frames
        frames = []
        for tick, group in df.groupby("tick"):
            players = []
            for _, row in group.iterrows():
                # Handle active_weapon - might be int (weapon ID) or string
                active_weapon = row.get("active_weapon")
                if active_weapon is not None and not isinstance(active_weapon, str):
                    active_weapon = str(active_weapon)

                players.append(
                    PlayerState(
                        tick=int(tick),
                        steamid=str(row["steamid"]),
                        name=row["name"],
                        team=self._normalize_team(row["team_name"]),
                        x=float(row["X"]),
                        y=float(row["Y"]),
                        z=float(row["Z"]),
                        health=int(row.get("health", 100)),
                        armor=int(row.get("armor_value", 0)),
                        has_helmet=bool(row.get("has_helmet", False)),
                        has_defuser=bool(row.get("has_defuser", False)),
                        is_alive=bool(row.get("is_alive", True)),
                        money=int(row.get("start_balance", 0)),
                        equipment_value=int(row.get("current_equip_value", 0)),
                        active_weapon=active_weapon,
                        round_num=int(row["round_num"]) if pd.notna(row["round_num"]) else None,
                    )
                )

            round_num = players[0].round_num if players else None
            frames.append(PlayerFrame(tick=int(tick), round_num=round_num, players=players))

        return frames

    def get_economy_by_round(self) -> dict[int, EconomyState]:
        """Get economy state at the start of each round."""
        if self._economy is not None:
            return self._economy

        rounds = self.get_rounds()
        economy_config = get_economy_config()
        eco_max = economy_config["buy_thresholds"]["eco_max"]
        force_max = economy_config["buy_thresholds"]["force_max"]

        economy = {}
        for round_state in rounds:
            # Get player data at freeze time end (buy phase complete)
            tick = round_state.freeze_end_tick or round_state.start_tick

            try:
                df = self._parser.parse_ticks(
                    ["steamid", "team_name", "start_balance", "current_equip_value"],
                    ticks=[tick],
                )
            except Exception:
                continue

            if df.empty:
                continue

            ct_data = df[df["team_name"].str.upper().str.contains("CT", na=False)]
            t_data = df[~df["team_name"].str.upper().str.contains("CT", na=False)]

            ct_money = {str(row["steamid"]): int(row["start_balance"]) for _, row in ct_data.iterrows()}
            t_money = {str(row["steamid"]): int(row["start_balance"]) for _, row in t_data.iterrows()}

            ct_equip = int(ct_data["current_equip_value"].sum()) if len(ct_data) > 0 else 0
            t_equip = int(t_data["current_equip_value"].sum()) if len(t_data) > 0 else 0

            ct_total = sum(ct_money.values())
            t_total = sum(t_money.values())
            ct_avg = ct_total / len(ct_money) if ct_money else 0
            t_avg = t_total / len(t_money) if t_money else 0

            # Classify buy type
            def classify_buy(avg: float, round_num: int) -> BuyType:
                if round_num in (1, 13):  # Pistol rounds
                    return BuyType.PISTOL
                if avg < eco_max:
                    return BuyType.ECO
                if avg < force_max:
                    return BuyType.FORCE
                return BuyType.FULL

            economy[round_state.round_num] = EconomyState(
                round_num=round_state.round_num,
                ct_economy=TeamEconomy(
                    team="CT",
                    round_num=round_state.round_num,
                    player_money=ct_money,
                    total_money=ct_total,
                    average_money=ct_avg,
                    equipment_value=ct_equip,
                    buy_type=classify_buy(ct_avg, round_state.round_num),
                ),
                t_economy=TeamEconomy(
                    team="T",
                    round_num=round_state.round_num,
                    player_money=t_money,
                    total_money=t_total,
                    average_money=t_avg,
                    equipment_value=t_equip,
                    buy_type=classify_buy(t_avg, round_state.round_num),
                ),
            )

        self._economy = economy
        return economy

    def get_match(self) -> Match:
        """Build complete Match object."""
        rounds = self.get_rounds()

        # Get players from first frame
        frames = self.get_player_frames(tick_interval=1000)
        first_frame = frames[0] if frames else None

        ct_players = {}
        t_players = {}
        if first_frame:
            for p in first_frame.players:
                if p.team == "CT":
                    ct_players[p.steamid] = p.name
                else:
                    t_players[p.steamid] = p.name

        # Final score
        ct_score = sum(1 for r in rounds if r.result and r.result.winner == "CT")
        t_score = sum(1 for r in rounds if r.result and r.result.winner == "T")

        return Match(
            demo_path=str(self.demo_path),
            map_name=self.map_name,
            team_ct=Team(players=ct_players),
            team_t=Team(players=t_players),
            rounds=rounds,
            ct_score=ct_score,
            t_score=t_score,
        )

    def _tick_to_round(self, tick: int, rounds: list[RoundState]) -> int:
        """Map a tick to its round number."""
        for r in rounds:
            if r.start_tick <= tick and (r.end_tick is None or tick <= r.end_tick):
                return r.round_num
        return 0  # Pre-game or unknown

    def _normalize_team(self, team_name: str | None) -> str:
        """Normalize team name to CT or T."""
        if not team_name:
            return "unknown"
        upper = team_name.upper()
        if "CT" in upper or "COUNTER" in upper:
            return "CT"
        if "T" in upper or "TERRORIST" in upper:
            return "T"
        return team_name
