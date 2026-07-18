import { Stage, Layer, Image } from "react-konva";
import { useEffect, useState, useMemo } from "react";
import PlayerMarker from "./PlayerMarker";
import HeatmapLayer from "./HeatmapLayer";
import IntentLayer from "./IntentLayer";
import ChatPanel from "./ChatPanel";
import type { Player, PlayerInfo, HeatmapData, RoundInfo } from "../types/Player";
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
}

export default function MapCanvas({ currentTick, rounds }: MapCanvasProps) {
  const [players, setPlayers] = useState<Player[]>([]);
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
  const [selectedRound, setSelectedRound] = useState<number>(0); // 0 = all rounds

  //Map loading hook
  useEffect(() => {
    async function loadMap() {
        const response = await fetch("http://localhost:8000/api/map");
        const data: MapResponse = await response.json();

        // Strip "de_" prefix from map name (e.g. "de_inferno" → "inferno")
        const mapKey = data.map_name.replace(/^de_/, "") as keyof typeof mapImages;

        // Set active map bounds based on loaded map
        const bounds = MAP_CONFIG[mapKey];
        if (bounds) {
          setActiveMapBounds(bounds);
        }

        const img = new window.Image();
        img.src = mapImages[mapKey];

        img.onload = () => {
            setMapImage(img);
        };
    }
    loadMap();
  }, []);

  // Fetch player list for heatmap filter
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

  // Fetch heatmap data when filters change
  useEffect(() => {
    async function fetchHeatmap() {
      try {
        const sampleRate = selectedRound > 0 ? 8 : (selectedPlayer ? 64 : 128);
        const params = new URLSearchParams();
        if (selectedPlayer) params.set("steamid", selectedPlayer);
        if (selectedTeam) params.set("team", selectedTeam);
        params.set("round_num", String(selectedRound));
        params.set("sample_rate", String(sampleRate));

        const url = `http://localhost:8000/api/heatmap?${params.toString()}`;
        console.log("Fetching heatmap:", url);
        const response = await fetch(url);
        const data: HeatmapData = await response.json();
        console.log("Heatmap data received:", data.steamid, "team:", data.team, "round:", data.round_num, "positions:", data.positions?.length);
        setHeatmapPositions(data.positions || []);
      } catch (error) {
        console.error("Error fetching heatmap data:", error);
      }
    }
    fetchHeatmap();
  }, [selectedPlayer, selectedTeam, selectedRound]);

  //window resize hook
  useEffect(() => {
    const handleResize = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  //data fetching hook
  useEffect(() => {
    const fetchTickData = async () => {
      if (Number.isInteger(currentTick) == false || currentTick % 2 != 0) {
        return
      }
      try {
        const response = await fetch(`http://localhost:8000/api/state/${currentTick}`);
        if (!response.ok) throw new Error("Network response was not ok");
        const data = await response.json();
        setPlayers(data);
      } catch (error) {
        console.error("Error fetching player positions:", error);
      }
    };

    fetchTickData();
  }, [currentTick]);

  // Calculate scale to fit map within viewport while maintaining aspect ratio
  const { scale, width, height } = useMemo(() => {
    if (!mapImage) return { scale: 1, width: 0, height: 0 };

    const padding = 0;
    const availableWidth = dimensions.width - padding;
    const availableHeight = dimensions.height - padding;

    const scaleX = availableWidth / mapImage.width;
    const scaleY = availableHeight / mapImage.height;
    const scale = Math.min(scaleX, scaleY);

    return {
      scale,
      width: mapImage.width * scale,
      height: mapImage.height * scale
    };
  }, [mapImage, dimensions]);

  // Memoized coordinate conversion — recomputes only when bounds/dimensions change
  const getCanvasCoords = useMemo(() => {
    const bounds = activeMapBounds;
    const xcoorperpixel = (bounds.maxX - bounds.minX) / (width || 1);
    const ycoorperpixel = (bounds.maxY - bounds.minY) / (height || 1);
    const offsetX = (dimensions.width - width) / 2;

    return (gameX: number, gameY: number) => {
      if (gameX === undefined || gameY === undefined) return { x: 0, y: 0 };
      const gameXnorm = gameX - bounds.minX;
      const gameYnorm = bounds.maxY - gameY;
      return {
        x: (gameXnorm / xcoorperpixel) + offsetX,
        y: (gameYnorm / ycoorperpixel),
      };
    };
  }, [activeMapBounds, width, height, dimensions.width]);

  const mapOffsetX = (dimensions.width - width) / 2;
  const mapOffsetY = (dimensions.height - height) / 2;

  return (
    <div style={{ position: "relative" }}>
      {/* Controls overlay */}
      <div style={{
        position: "absolute",
        top: 10,
        left: 10,
        zIndex: 10,
        background: "rgba(0, 0, 0, 0.75)",
        padding: "10px 14px",
        borderRadius: 8,
        display: "flex",
        gap: 12,
        alignItems: "center",
        color: "#fff",
        fontSize: 13,
        fontFamily: "sans-serif",
      }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={showHeatmap}
            onChange={(e) => setShowHeatmap(e.target.checked)}
          />
          Heatmap
        </label>

        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={showIntent}
            onChange={(e) => setShowIntent(e.target.checked)}
          />
          Show Intent
        </label>

        {(showHeatmap || showIntent) && (
          <>
            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              style={{ padding: "3px 6px", fontSize: 13, borderRadius: 4 }}
            >
              <option value="">All Teams</option>
              <option value="CT">CT</option>
              <option value="TERRORIST">T</option>
            </select>
            <select
              value={selectedPlayer}
              onChange={(e) => setSelectedPlayer(e.target.value)}
              style={{ padding: "3px 6px", fontSize: 13, borderRadius: 4 }}
            >
              <option value="">All Players</option>
              {playerList
                .filter((p) => !selectedTeam || p.team_name === selectedTeam)
                .map((p) => (
                  <option key={p.steamid} value={p.steamid}>
                    {p.name} ({p.team_name})
                  </option>
                ))}
            </select>
            <select
              value={selectedRound}
              onChange={(e) => setSelectedRound(Number(e.target.value))}
              style={{ padding: "3px 6px", fontSize: 13, borderRadius: 4 }}
            >
              <option value="0">All Rounds</option>
              {rounds.map((r) => (
                <option key={r.round_num} value={r.round_num}>
                  Round {r.round_num}
                </option>
              ))}
            </select>
          </>
        )}

        <button
          onClick={() => setShowChat(!showChat)}
          style={{
            padding: "4px 10px",
            background: showChat ? "#4CAF50" : "rgba(255,255,255,0.15)",
            border: "none",
            borderRadius: 4,
            color: "#fff",
            cursor: "pointer",
            fontSize: 12,
            whiteSpace: "nowrap",
          }}
        >
          🤖 Coach Chat
        </button>
      </div>

      <Stage width={dimensions.width} height={dimensions.height}>
        {/* Layer 1: Map image */}
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

        {/* Layer 2: Heatmap (between map and markers) */}
        <Layer>
          {showHeatmap && heatmapPositions.length > 0 && (
            <HeatmapLayer
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

        {/* Layer 2.5: Intent predictions (between heatmap and markers) */}
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

        {/* Layer 3: Player markers (on top) */}
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

      {/* Chat Panel overlay */}
      <ChatPanel
        currentTick={currentTick}
        visible={showChat}
        onClose={() => setShowChat(false)}
      />
    </div>
  );
}
