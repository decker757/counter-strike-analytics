import { Stage, Layer, Image } from "react-konva";
import { useEffect, useState } from "react";
import PlayerMarker from "./PlayerMarker";
import type { Player } from "../types/Player";
import dust2 from "../assets/maps/dust2.png"

const DUST2_CONFIG = {
  minX: -2203,
  maxX: 1768,
  minY: -1163,
  maxY: 3117,
}

interface MapCanvasProps {
  currentTick: number;
}

export default function MapCanvas({ currentTick }: MapCanvasProps) {
  const [players, setPlayers] = useState<Player[]>([]);
  const [mapImage, setMapImage] = useState<HTMLImageElement | null>(null);
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  });

  //Map loading hook
  useEffect(() => {
    const img = new window.Image();
    img.src = dust2;
    img.onload = () => setMapImage(img);
  }, []);

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
      if (Number.isInteger(currentTick) == false) {
        return
      }
      try {
        const response = await fetch(`http://localhost:8000/api/state/${currentTick}`);
        if (!response.ok) throw new Error("Network response was not ok");
        const data = await response.json();
        //console.log(data);
        setPlayers(data);
      } catch (error) {
        console.error("Error fetching player positions:", error);
      }
    };

    fetchTickData();
  }, [currentTick]); //Re-runs whenever tick updates

  // Calculate scale to fit map within viewport while maintaining aspect ratio
  const getScaleFactor = () => {
    if (!mapImage) return { scale: 1, width: 0, height: 0 };

    const padding = 0; // Add padding around the map
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
  };

  const { scale, width, height } = getScaleFactor();

  const getCanvasCoords = (gameX: number, gameY: number) => {
    /*
    // 1. Translate Game Coords to 1024x1024 Radar pixels
    const radarX = (gameX - DUST2_CONFIG.pos_x) / DUST2_CONFIG.scale;
    const radarY = (DUST2_CONFIG.pos_y - gameY) / DUST2_CONFIG.scale;

    // 2. Scale those pixels to match your actual onscreen map size
    // Your code uses (radar / 1024) to find the percentage across the map
    const canvasX = (radarX * (width / 1024)) + ((dimensions.width - width) / 2);
    const canvasY = (radarY * (height / 1024)) + ((dimensions.height - height) / 2);
    */

    if (gameX === undefined || gameY === undefined) return { x: 0, y: 0 };

    // 1. Calculate the percentage of where the player is within the boundaries
    const percentX = (gameX - DUST2_CONFIG.minX) / (DUST2_CONFIG.maxX - DUST2_CONFIG.minX);
    const percentY = (DUST2_CONFIG.maxY - gameY) / (DUST2_CONFIG.maxY - DUST2_CONFIG.minY);

    // 2. Map percentage to your 1080px image space
    const imageX = percentX * 1000;
    const imageY = percentY * 1000;

    // 3. Apply the responsive canvas scaling and centering
    // 'width', 'height', and 'dimensions' come from your existing state
    const canvasX = (imageX * (width / 1000)) + ((dimensions.width - width) / 2);
    const canvasY = (imageY * (height / 1000)) + ((dimensions.height - height) / 2);

    return { x: canvasX, y: canvasY };
};

  return (
    <Stage width={dimensions.width} height={dimensions.height}>
      <Layer>
        {mapImage && (
          <Image
            image={mapImage}
            width={width}
            height={height}
            x={(dimensions.width - width) / 2}
            y={(dimensions.height - height) / 2}
          />
        )}

        {players.map(player => {
          console.log(player.X)
          console.log(player.Y)
          if (player.X === undefined || player.Y === undefined) return null;

          const coords = getCanvasCoords(player.X, player.Y);
          console.log(coords)

          return (
            <PlayerMarker
              key={player.steamid}
              player={player}
              x={coords.x}   // Use the calculated X
              y={coords.y}   // Use the calculated Y
              scale={scale}
              offsetX={0}
              offsetY={0}
            />
          );
        })}
      </Layer>
    </Stage>
  );
}



/*
<PlayerMarker
            key={player.steamid}
            player={player}
            scale={scale}
            offsetX={(dimensions.width - width) / 2}
            offsetY={(dimensions.height - height) / 2}
          />
*/