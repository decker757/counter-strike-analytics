import { useState, memo } from "react";
import { Circle, Text, Group, Rect } from "react-konva";
import type { Player } from "../types/Player";

interface PlayerMarkerProps {
    player: Player;
    scale: number;
    x: number;
    y: number;
    offsetX: number;
    offsetY: number;
}

const PlayerMarker = memo(function PlayerMarker({ player, scale, x, y }: PlayerMarkerProps) {
    const [hovered, setHovered] = useState(false);
    const color = player.team_name === "CT" ? "#4da6ff" : "#ffb347";

    if (!player.is_alive) return null;

    const fontSize = Math.max(11, 13 * scale);
    const padding = 4 * scale;
    const tooltipY = y - 10 * scale - fontSize;

    return (
        <Group>
            <Circle
                x={x}
                y={y}
                radius={5 * scale}
                fill={color}
                stroke="white"
                strokeWidth={1}
                onMouseEnter={() => setHovered(true)}
                onMouseLeave={() => setHovered(false)}
            />
            {hovered && (
                <Group x={x} y={tooltipY}>
                    <Rect
                        x={-padding}
                        y={-fontSize - padding}
                        width={player.name.length * fontSize * 0.6 + padding * 2}
                        height={fontSize + padding * 2}
                        fill="rgba(0, 0, 0, 0.8)"
                        cornerRadius={3 * scale}
                    />
                    <Text
                        text={player.name}
                        fontSize={fontSize}
                        fill="white"
                        align="center"
                        y={-fontSize - padding / 2}
                    />
                </Group>
            )}
        </Group>
    );
});

export default PlayerMarker;
