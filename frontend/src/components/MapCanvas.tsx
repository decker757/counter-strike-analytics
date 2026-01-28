import { Stage, Layer, Image } from "react-konva";
import { useEffect, useState } from "react";
import PlayerMarker from "./PlayerMarker";
import type { Player } from "../types/Player";
import dust2 from "../assets/maps/dust2.png"
//import dust2 from "../assets/maps/Cs2_dust2_overview.webp";

interface MapCanvasProps {
  players: Player[];
}



export default function MapCanvas({ players }: MapCanvasProps) {
  const [mapImage, setMapImage] = useState<HTMLImageElement | null>(null);
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  });

  useEffect(() => {
    const img = new window.Image();
    img.src = dust2;
    img.onload = () => setMapImage(img);
  }, []);

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

  // Calculate scale to fit map within viewport while maintaining aspect ratio
  const getScaleFactor = () => {
    if (!mapImage) return { scale: 1, width: 0, height: 0 };

    const padding = 40; // Add padding around the map
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

        {players.map(player => (
          <PlayerMarker
            key={player.id}
            player={player}
            scale={scale}
            offsetX={(dimensions.width - width) / 2}
            offsetY={(dimensions.height - height) / 2}
          />
        ))}
      </Layer>
    </Stage>
  );
}
