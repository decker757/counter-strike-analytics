"""Game state serializer — converts structured match data to compact text summaries.

These text summaries are designed to fit efficiently in LLM context windows
(~500-1000 tokens) while preserving the tactical details needed for coaching insights.
"""

import pandas as pd


class GameStateSerializer:
    """Converts CS2 game state to natural language summaries for LLM consumption.

    The summaries are compact but information-dense, using CS2 terminology
    that local LLMs understand well.
    """

    @staticmethod
    def serialize_tick_state(
        tick: int,
        df: pd.DataFrame,
        intent_data: dict | None = None,
    ) -> str:
        """Serialize game state at a specific tick into a compact text summary.

        Args:
            tick: Current game tick
            df: Raw DataFrame from position_analysis
            intent_data: Optional intent prediction results

        Returns:
            Compact text summary (~200-400 tokens)
        """
        tick_data = df[df["tick"] == tick]
        if tick_data.empty:
            return f"[No data available at tick {tick}]"

        alive = tick_data[tick_data["is_alive"] == True]
        dead = tick_data[tick_data["is_alive"] == False]

        lines = [f"**Tick {tick}**"]

        # Team composition
        ct = alive[alive["team_name"] == "CT"]
        t = alive[alive["team_name"] == "TERRORIST"]
        lines.append(
            f"Alive: {len(ct)} CT, {len(t)} T "
            f"(Dead: {len(dead[dead['team_name'] == 'CT'])} CT, "
            f"{len(dead[dead['team_name'] == 'TERRORIST'])} T)"
        )

        # Player positions
        lines.append("\n**Player Positions:**")
        for _, p in alive.iterrows():
            team = "CT" if p["team_name"] == "CT" else "T"
            name = p.get("name", "Unknown")
            x, y, z = float(p["X"]), float(p["Y"]), float(p.get("Z", 0))
            lines.append(f"  - {name} ({team}): ({x:.0f}, {y:.0f}, {z:.0f})")

        # Intent predictions if available
        if intent_data and intent_data.get("players"):
            lines.append("\n**Predicted Intents:**")
            for pred in intent_data["players"]:
                action = pred.get("action", "unknown")
                conf = pred.get("confidence", 0)
                zone = pred.get("predicted_zone") or pred.get("current_zone", "?")
                lines.append(
                    f"  - {pred['name']} ({pred['team']}): {action} "
                    f"toward {zone} (confidence: {conf:.0%})"
                )

        # Game context (if available from extended fields)
        sample = tick_data.iloc[0]
        if "is_bomb_planted" in sample and sample["is_bomb_planted"]:
            lines.append("\n**Bomb planted!**")

        return "\n".join(lines)

    @staticmethod
    def serialize_round_summary(
        round_num: int,
        round_info: dict,
        kills: list[dict] | None = None,
    ) -> str:
        """Serialize a completed round into a summary for narrative generation.

        Args:
            round_num: Round number
            round_info: Round data from /api/rounds with additional context
            kills: Optional list of kill events in this round

        Returns:
            Round summary text
        """
        lines = [
            f"**Round {round_num}**",
            f"Start tick: {round_info.get('start_tick', '?')}, "
            f"End tick: {round_info.get('end_tick', '?')}",
        ]

        if kills:
            lines.append(f"\n**Kills ({len(kills)}):**")
            for k in kills[:10]:  # limit to first 10 for context window
                lines.append(
                    f"  - {k.get('attacker_name', '?')} "
                    f"[{k.get('weapon', '?')}] → "
                    f"{k.get('victim_name', '?')}"
                )

        return "\n".join(lines)

    @staticmethod
    def serialize_match_context(
        df: pd.DataFrame,
        map_name: str = "",
        tick: int = 0,
    ) -> str:
        """Serialize high-level match context for the chat interface.

        Args:
            df: Raw DataFrame
            map_name: Current map
            tick: Current playback tick

        Returns:
            Match context summary
        """
        lines = [
            f"Map: {map_name}",
            f"Current tick: {tick}",
        ]

        if not df.empty:
            players = df[["steamid", "name", "team_name"]].drop_duplicates("steamid")
            ct_players = players[players["team_name"] == "CT"]["name"].tolist()
            t_players = players[players["team_name"] == "TERRORIST"]["name"].tolist()
            lines.append(f"CT: {', '.join(ct_players[:5])}")
            lines.append(f"T: {', '.join(t_players[:5])}")

        return "\n".join(lines)
