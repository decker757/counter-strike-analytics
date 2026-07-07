import { Circle } from "react-konva";
import type { Player } from "../types/Player";

interface PlayerMarkerProps {
    player: Player;
    scale: number;
    x: number;
    y: number;
    offsetX: number;
    offsetY: number;
}

export default function PlayerMarker({ player, scale, x, y }: PlayerMarkerProps) {
    const color = player.team_name === "CT" ? "#4da6ff" : "#ffb347";

    if (!player.is_alive) return null;

    return (
        <Circle
          x={x}
          y={y}
          radius={5 * scale}
          fill={color}
          stroke="white"
          strokeWidth={1}
        />
    );
}