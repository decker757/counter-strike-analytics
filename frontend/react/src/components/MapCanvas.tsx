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

  useEffect(() => {
    const img = new window.Image();
    img.src = dust2;
    img.onload = () => setMapImage(img);
  }, []);


  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  });

  return (
    <Stage>
    <Layer>
        {mapImage && (
        <Image
            image={mapImage}
        />s
        )}

        {players.map(player => (
        <PlayerMarker key={player.id} player={player} />
        ))}
    </Layer>
    </Stage>
  );
}
