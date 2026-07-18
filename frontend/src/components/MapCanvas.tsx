import { Stage, Layer, Image } from "react-konva";
import { useEffect, useState, useMemo } from "react";
import PlayerMarker from "./PlayerMarker";
import HeatmapLayer from "./HeatmapLayer";
import IntentLayer from "./IntentLayer";
import ChatPanel from "./ChatPanel";
import { ErrorBoundary } from "./ErrorBoundary";
import { useTickBuffer } from "../hooks/useTickBuffer";
import type { PlayerInfo, HeatmapData, RoundInfo } from "../types/Player";
import dust2 from "../assets/maps/dust2.png";
import inferno from "../assets/maps/inferno.png";

interface MapBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

const MAP_CONFIG: Record<string, MapBounds> = {
  dust2: {
    minX: -2203,
    maxX: 1768,
    minY: -1163,
    maxY: 3117,
  },
  inferno: {
    minX: -1730,
    maxX: 2664,
    minY: -769,
    maxY: 3514,
  }
};

type MapResponse = {
    map_name: keyof typeof mapImages;
};

const mapImages = {
  inferno,
  dust2,
};

interface MapCanvasProps {
  currentTick: number;
  rounds: RoundInfo[];
  isPlaying: boolean;
}

export default function MapCanvas({ currentTick, rounds, isPlaying }: MapCanvasProps) {
  const players = useTickBuffer(currentTick);

  const [mapImage, setMapImage] = useState<HTMLImageElement | null>(null);
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  });
  const [activeMapBounds, setActiveMapBounds] = useState<MapBounds>(MAP_CONFIG.inferno);

  // Heatmap state
  const [playerList, setPlayerList] = useState<PlayerInfo[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<string>("");
  const [selectedTeam, setSelectedTeam] = useState<string>("");
  const [showHeatmap, setShowHeatmap] = useState<boolean>(false);
  const [showIntent, setShowIntent] = useState<boolean>(false);
  const [showChat, setShowChat] = useState<boolean>(false);
  const [heatmapPositions, setHeatmapPositions] = useState<Array<{ X: number; Y: number }>>([]);
  const [selectedRound, setSelectedRound] = useState<number>(0);

  // Map loading
  useEffect(() => {
    async function loadMap() {
        const response = await fetch("http://localhost:8000/api/map");
        const data: MapResponse = await response.json();
        const mapKey = data.map_name.replace(/^de_/, "") as keyof typeof mapImages;
        const bounds = MAP_CONFIG[mapKey];
        if (bounds) setActiveMapBounds(bounds);
        const img = new window.Image();
        img.src = mapImages[mapKey];
        img.onload = () => setMapImage(img);
    }
    loadMap();
  }, []);

  // Player list
  useEffect(() => {
    async function fetchPlayers() {
      try {
        const response = await fetch("http://localhost:8000/api/players");
        const data: PlayerInfo[] = await response.json();
        setPlayerList(data);
      } catch (error) {
        console.error("Error fetching player list:", error);
      }
    }
    fetchPlayers();
  }, []);

  // Heatmap fetch
  useEffect(() => {
    setHeatmapPositions([]);
    const controller = new AbortController();

    async function fetchHeatmap() {
      try {
        const sampleRate = selectedRound > 0 ? 8 : (selectedPlayer ? 64 : 128);
        const params = new URLSearchParams();
        if (selectedPlayer) params.set("steamid", selectedPlayer);
        if (selectedTeam) params.set("team", selectedTeam);
        params.set("round_num", String(selectedRound));
        params.set("sample_rate", String(sampleRate));

        const url = `http://localhost:8000/api/heatmap?${params.toString()}`;
        const response = await fetch(url, { signal: controller.signal });
        const data: HeatmapData = await response.json();
        setHeatmapPositions(data.positions || []);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          console.error("Error fetching heatmap data:", error);
        }
      }
    }
    fetchHeatmap();
    return () => controller.abort();
  }, [selectedPlayer, selectedTeam, selectedRound]);

  // Window resize
  useEffect(() => {
    const handleResize = () => {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Memoized scale
  const { scale, width, height } = useMemo(() => {
    if (!mapImage) return { scale: 1, width: 0, height: 0 };
    const availableWidth = dimensions.width;
    const availableHeight = dimensions.height;
    const scaleX = availableWidth / mapImage.width;
    const scaleY = availableHeight / mapImage.height;
    const s = Math.min(scaleX, scaleY);
    return { scale: s, width: mapImage.width * s, height: mapImage.height * s };
  }, [mapImage, dimensions]);

  // Memoized coordinate conversion
  const getCanvasCoords = useMemo(() => {
    const bounds = activeMapBounds;
    const xr = (bounds.maxX - bounds.minX) / (width || 1);
    const yr = (bounds.maxY - bounds.minY) / (height || 1);
    const ox = (dimensions.width - width) / 2;
    return (gameX: number, gameY: number) => {
      if (gameX === undefined || gameY === undefined) return { x: 0, y: 0 };
      return {
        x: ((gameX - bounds.minX) / xr) + ox,
        y: ((bounds.maxY - gameY) / yr),
      };
    };
  }, [activeMapBounds, width, height, dimensions.width]);

  const mapOffsetX = (dimensions.width - width) / 2;
  const mapOffsetY = (dimensions.height - height) / 2;

  const hasPlayers = players.length > 0;

  return (
    <div style={{ position: "relative" }}>
      {/* ── Map Loading Overlay ── */}
      {!mapImage && (
        <div className="map-loading">
          <div className="map-loading-text">
            <span className="loading-dot" />
            <span className="loading-dot" />
            <span className="loading-dot" />
            &nbsp;Loading map…
          </div>
        </div>
      )}

      {/* ── Controls Overlay ── */}
      <div style={{
        position: "absolute",
        top: 80,
        left: 16,
        zIndex: 10,
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}>
        <div className="glass-panel" style={{ padding: "10px 14px", display: "flex", flexDirection: "column", gap: 8 }}>
          {/* Heatmap toggle */}
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showHeatmap}
              onChange={(e) => setShowHeatmap(e.target.checked)}
            />
            🔥 Heatmap
          </label>

          {/* Intent toggle */}
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showIntent}
              onChange={(e) => setShowIntent(e.target.checked)}
            />
            🎯 Show Intent
          </label>

          {/* Filters (visible when either is active) */}
          {(showHeatmap || showIntent) && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 2, paddingTop: 6, borderTop: "1px solid var(--border-subtle)" }}>
              <select
                className="select"
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="">All Teams</option>
                <option value="CT">🔵 CT</option>
                <option value="TERRORIST">🟠 T</option>
              </select>

              <select
                className="select"
                value={selectedPlayer}
                onChange={(e) => setSelectedPlayer(e.target.value)}
                style={{ width: "100%" }}
              >
                <option value="">All Players</option>
                {playerList
                  .filter((p) => !selectedTeam || p.team_name === selectedTeam)
                  .map((p) => (
                    <option key={p.steamid} value={p.steamid}>
                      {p.name}
                    </option>
                  ))}
              </select>

              {showHeatmap && (
                <select
                  className="select"
                  value={selectedRound}
                  onChange={(e) => setSelectedRound(Number(e.target.value))}
                  style={{ width: "100%" }}
                >
                  <option value="0">All Rounds</option>
                  {rounds.map((r) => (
                    <option key={r.round_num} value={r.round_num}>
                      Round {r.round_num}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}
        </div>

        {/* Buffer loading indicator */}
        {isPlaying && !hasPlayers && (
          <div className="glass-panel" style={{ padding: "6px 12px", display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-secondary)" }}>
            <span className="loading-dot" />
            <span className="loading-dot" />
            <span className="loading-dot" />
            Buffering…
          </div>
        )}

        {/* Chat toggle */}
        <button
          className={`btn ${showChat ? 'btn-primary glow-active' : ''}`}
          onClick={() => setShowChat(!showChat)}
          style={{ width: "100%" }}
        >
          🤖 Coach Chat
        </button>
      </div>

      {/* ── Konva Stage ── */}
      <Stage width={dimensions.width} height={dimensions.height}>
        <Layer>
          {mapImage && (
            <Image
              image={mapImage}
              width={width}
              height={height}
              x={mapOffsetX}
              y={mapOffsetY}
            />
          )}
        </Layer>

        <Layer>
          {showHeatmap && heatmapPositions.length > 0 && (
            <HeatmapLayer
              key={`${selectedPlayer}|${selectedTeam}|${selectedRound}`}
              positions={heatmapPositions}
              mapBounds={activeMapBounds}
              imageWidth={width}
              imageHeight={height}
              visible={showHeatmap}
              offsetX={mapOffsetX}
              offsetY={mapOffsetY}
            />
          )}
        </Layer>

        <Layer>
          {showIntent && (
            <IntentLayer
              tick={currentTick}
              mapBounds={activeMapBounds}
              imageWidth={width}
              imageHeight={height}
              offsetX={mapOffsetX}
              offsetY={mapOffsetY}
              visible={showIntent}
              selectedTeam={selectedTeam}
              selectedPlayer={selectedPlayer}
            />
          )}
        </Layer>

        <Layer>
          {players.map(player => {
            if (player.X === undefined || player.Y === undefined) return null;
            const coords = getCanvasCoords(player.X, player.Y);
            return (
              <PlayerMarker
                key={player.steamid}
                player={player}
                x={coords.x}
                y={coords.y}
                scale={scale}
                offsetX={0}
                offsetY={0}
              />
            );
          })}
        </Layer>
      </Stage>

      {/* ── Chat Panel ── */}
      <div className="chat-container">
        <ErrorBoundary>
          <ChatPanel
            currentTick={currentTick}
            visible={showChat}
            onClose={() => setShowChat(false)}
          />
        </ErrorBoundary>
      </div>
    </div>
  );
}
