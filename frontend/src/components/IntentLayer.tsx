import { useEffect, useState, useRef, useMemo } from "react";
import { Group, Circle, Line, Text } from "react-konva";
import type { IntentPlayerPrediction, IntentResponse } from "../types/Intent";

interface MapBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface IntentLayerProps {
  tick: number;
  mapBounds: MapBounds;
  imageWidth: number;
  imageHeight: number;
  offsetX: number;
  offsetY: number;
  visible: boolean;
  selectedTeam: string;
  selectedPlayer: string;
}

const ACTION_COLORS: Record<string, string> = {
  holding: "#00FF00",       // bright green
  pushing: "#00BFFF",       // deep sky blue
  rotating: "#FFD700",      // gold
  falling_back: "#FF4444",  // bright red
};

const HORIZON_OPACITIES = [1.0, 0.8, 0.5];
const HORIZON_RADII = [8, 6, 4];
const FETCH_INTERVAL_TICKS = 32;

function gameToStage(
  gameX: number, gameY: number,
  bounds: MapBounds, canvasW: number, canvasH: number,
  offX: number, offY: number
): { x: number; y: number } {
  const xRange = bounds.maxX - bounds.minX;
  const yRange = bounds.maxY - bounds.minY;
  return {
    x: ((gameX - bounds.minX) / xRange) * canvasW + offX,
    y: ((bounds.maxY - gameY) / yRange) * canvasH + offY,
  };
}

export default function IntentLayer({
  tick,
  mapBounds,
  imageWidth,
  imageHeight,
  offsetX,
  offsetY,
  visible,
  selectedTeam,
  selectedPlayer,
}: IntentLayerProps) {
  const [intentData, setIntentData] = useState<IntentResponse | null>(null);
  const lastFetchTick = useRef(-1);
  const lastFilters = useRef({ team: "", player: "" });

  const boundsRef = useRef(mapBounds);
  boundsRef.current = mapBounds;
  const imgWRef = useRef(imageWidth);
  imgWRef.current = imageWidth;
  const imgHRef = useRef(imageHeight);
  imgHRef.current = imageHeight;
  const offXRef = useRef(offsetX);
  offXRef.current = offsetX;
  const offYRef = useRef(offsetY);
  offYRef.current = offsetY;

  useEffect(() => {
    if (!visible) {
      setIntentData(null);
      return;
    }

    // Refetch immediately if filters changed
    const filtersChanged =
      selectedTeam !== lastFilters.current.team ||
      selectedPlayer !== lastFilters.current.player;
    lastFilters.current = { team: selectedTeam, player: selectedPlayer };

    if (filtersChanged) {
      lastFetchTick.current = -1;
    }

    // Throttle
    if (tick - lastFetchTick.current < FETCH_INTERVAL_TICKS && lastFetchTick.current > 0 && !filtersChanged) {
      return;
    }

    const requestTick = tick;
    lastFetchTick.current = tick;

    async function fetchIntent() {
      try {
        const params = new URLSearchParams();
        if (selectedTeam) params.set("team", selectedTeam);
        if (selectedPlayer) params.set("steamid", selectedPlayer);

        const url = `http://localhost:8000/api/intent/${requestTick}?${params.toString()}`;
        const resp = await fetch(url);
        if (!resp.ok) return;
        const data: IntentResponse = await resp.json();

        // Always accept the data — don't cancel stale responses
        // (the latest response always wins since fetch ordering is preserved by throttle)
        if (!data.error && data.players && data.players.length > 0) {
          setIntentData(data);
        }
      } catch (_e) {
        // Silently ignore — transient failures are normal
      }
    }

    fetchIntent();
  }, [tick, visible, selectedTeam, selectedPlayer]);

  const elements = useMemo(() => {
    if (!intentData || !visible) return null;

    const b = boundsRef.current;
    const w = imgWRef.current;
    const h = imgHRef.current;
    const ox = offXRef.current;
    const oy = offYRef.current;

    return intentData.players.map((player: IntentPlayerPrediction) => {
      const color = ACTION_COLORS[player.action] || "#FFFFFF";
      const current = gameToStage(
        player.current_position.x, player.current_position.y, b, w, h, ox, oy
      );

      const items: React.ReactNode[] = [];

      // Pulsing dot at current position to verify coordinates
      items.push(
        <Circle
          key={`${player.steamid}-current`}
          x={current.x} y={current.y}
          radius={7}
          fill={color}
          stroke="#fff"
          strokeWidth={2}
          opacity={0.9}
        />
      );

      let prevX = current.x;
      let prevY = current.y;

      player.predictions.forEach((pred, i) => {
        const predPos = gameToStage(pred.x, pred.y, b, w, h, ox, oy);
        const opacity = HORIZON_OPACITIES[i] || 0.5;
        const radius = HORIZON_RADII[i] || 4;

        // Thick arrow-like line from prev to predicted
        items.push(
          <Line
            key={`${player.steamid}-arc-${i}`}
            points={[prevX, prevY, predPos.x, predPos.y]}
            stroke={color}
            strokeWidth={3}
            opacity={opacity}
            lineCap="round"
          />
        );
        // Bright circle at predicted position
        items.push(
          <Circle
            key={`${player.steamid}-ghost-${i}`}
            x={predPos.x} y={predPos.y}
            radius={radius}
            fill={color}
            stroke="#fff"
            strokeWidth={1}
            opacity={opacity}
          />
        );
        prevX = predPos.x;
        prevY = predPos.y;
      });

      // Large action label
      if (player.predictions.length > 0) {
        const lp = gameToStage(player.predictions[0].x, player.predictions[0].y, b, w, h, ox, oy);
        items.push(
          <Text
            key={`${player.steamid}-label`}
            x={lp.x + 10} y={lp.y - 14}
            text={`${player.action} (${Math.round(player.confidence * 100)}%)`}
            fontSize={12}
            fill={color}
            stroke="#000"
            strokeWidth={3}
            fillAfterStrokeEnabled={true}
            opacity={1.0}
            fontStyle="bold"
          />
        );
      }

      return <Group key={player.steamid}>{items}</Group>;
    });
  }, [intentData, visible]);

  if (!visible) return null;
  if (!intentData || intentData.players.length === 0) return null;

  return <Group>{elements}</Group>;
}
