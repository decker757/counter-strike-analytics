import { Circle } from "react-konva";
import type { Player } from "../types/Player";

interface PlayerMarkerProps {
    player: Player;
}

export default function PlayerMarker({ player }: PlayerMarkerProps) {
    const color = player.team === "CT" ? "#4da6ff" : "#ffb347";

    if (!player.alive) return null;

    return (
        <Circle
          x = {player.x}
          y = {player.y}
          radius = {5}
          fill = {color}
        />
    );
}