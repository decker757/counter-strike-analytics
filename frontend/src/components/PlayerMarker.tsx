import { Circle } from "react-konva";
import type { Player } from "../types/Player";

interface PlayerMarkerProps {
    player: Player;
    scale: number;
    offsetX: number;
    offsetY: number;
}

export default function PlayerMarker({ player, scale, offsetX, offsetY }: PlayerMarkerProps) {
    const color = player.team === "CT" ? "#4da6ff" : "#ffb347";

    if (!player.alive) return null;

    return (
        <Circle
          x={player.x * scale + offsetX}
          y={player.y * scale + offsetY}
          radius={5}
          fill={color}
        />
    );
}