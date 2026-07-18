import { useEffect, useState, useRef, useMemo } from "react";
import { Group, Circle, Line, Text, Rect } from "react-konva";
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
  holding: "#4CAF50",       // green — stationary defense
  pushing: "#FF6D00",       // orange — aggressive push
  rotating: "#2196F3",      // blue — repositioning
  falling_back: "#F44336",  // red — retreating
};

const ACTION_LABELS: Record<string, string> = {
  holding: "Holding",
  pushing: "Pushing",
  rotating: "Rotating",
  falling_back: "Falling Back",
};

const HORIZON_OPACITIES = [1.0, 0.65, 0.35];
const HORIZON_RADII = [7, 5, 3];
const HORIZON_STROKE_WIDTH = [3, 2, 1.5];
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

    const filtersChanged =
      selectedTeam !== lastFilters.current.team ||
      selectedPlayer !== lastFilters.current.player;
    lastFilters.current = { team: selectedTeam, player: selectedPlayer };

    if (filtersChanged) {
      lastFetchTick.current = -1;
    }

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
        if (!data.error && data.players && data.players.length > 0) {
          setIntentData(data);
        }
      } catch (_e) {
        // Silently ignore transient failures
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

      // ── Shadow glow at current position ──
      items.push(
        <Circle
          key={`${player.steamid}-glow`}
          x={current.x} y={current.y}
          radius={14}
          fill={color}
          opacity={0.2}
        />
      );

      // ── Current position marker ──
      items.push(
        <Circle
          key={`${player.steamid}-current`}
          x={current.x} y={current.y}
          radius={7}
          fill={color}
          stroke="#fff"
          strokeWidth={2.5}
          opacity={0.95}
        />
      );

      // ── Direction indicator (small line in velocity direction) ──
      if (player.predictions.length > 0) {
        const first = gameToStage(
          player.predictions[0].x, player.predictions[0].y, b, w, h, ox, oy
        );
        const dx = first.x - current.x;
        const dy = first.y - current.y;
        const dirLen = Math.sqrt(dx * dx + dy * dy);
        if (dirLen > 5) {
          const ndx = (dx / dirLen) * 20;
          const ndy = (dy / dirLen) * 20;
          items.push(
            <Line
              key={`${player.steamid}-dir`}
              points={[current.x, current.y, current.x + ndx, current.y + ndy]}
              stroke={color}
              strokeWidth={3}
              opacity={0.8}
              lineCap="round"
            />
          );
        }
      }

      // ── Predicted path with gradient-style fading ──
      let prevX = current.x;
      let prevY = current.y;

      player.predictions.forEach((pred, i) => {
        const predPos = gameToStage(pred.x, pred.y, b, w, h, ox, oy);
        const opacity = HORIZON_OPACITIES[i] || 0.35;
        const radius = HORIZON_RADII[i] || 3;
        const sw = HORIZON_STROKE_WIDTH[i] || 1.5;

        // Dashed connector line
        items.push(
          <Line
            key={`${player.steamid}-arc-${i}`}
            points={[prevX, prevY, predPos.x, predPos.y]}
            stroke={color}
            strokeWidth={sw}
            opacity={opacity}
            lineCap="round"
            dash={i === 0 ? [] : [6, 4]}
          />
        );

        // Predicted position dot
        items.push(
          <Circle
            key={`${player.steamid}-ghost-${i}`}
            x={predPos.x} y={predPos.y}
            radius={radius}
            fill={color}
            stroke="#fff"
            strokeWidth={0.8}
            opacity={opacity}
          />
        );

        prevX = predPos.x;
        prevY = predPos.y;
      });

      // ── Action label with confidence ──
      const labelText = `${ACTION_LABELS[player.action] || player.action} ${Math.round(player.confidence * 100)}%`;
      const labelY = current.y - 28;

      // Background pill
      const labelWidth = labelText.length * 6.5 + 16;
      items.push(
        <Rect
          key={`${player.steamid}-label-bg`}
          x={current.x - labelWidth / 2}
          y={labelY - 10}
          width={labelWidth}
          height={20}
          fill="rgba(0, 0, 0, 0.75)"
          cornerRadius={10}
          stroke={color}
          strokeWidth={1.5}
          opacity={0.9}
        />
      );

      items.push(
        <Text
          key={`${player.steamid}-label`}
          x={current.x - labelWidth / 2}
          y={labelY - 10}
          width={labelWidth}
          height={20}
          text={labelText}
          fontSize={11}
          fill={color}
          align="center"
          verticalAlign="middle"
          fontStyle="bold"
        />
      );

      // ── Zone info (subtle, below label) ──
      const zoneText = player.objective_zone
        ? `${player.current_zone || "?"} → ${player.objective_zone}`
        : player.current_zone || "";
      if (zoneText && zoneText.length > 2) {
        items.push(
          <Text
            key={`${player.steamid}-zone`}
            x={current.x - 60}
            y={labelY + 14}
            width={120}
            height={14}
            text={zoneText}
            fontSize={9}
            fill="rgba(255,255,255,0.5)"
            align="center"
            fontStyle="italic"
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
