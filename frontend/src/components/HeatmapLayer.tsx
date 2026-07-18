import { useEffect, useRef, useState, useCallback } from "react";
import { Image as KonvaImage } from "react-konva";

interface MapBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface HeatmapLayerProps {
  positions: Array<{ X: number; Y: number }>;
  mapBounds: MapBounds;
  imageWidth: number;
  imageHeight: number;
  visible: boolean;
  offsetX?: number;
  offsetY?: number;
}

/**
 * Convert game coordinate to pixel on the heatmap canvas.
 * The heatmap canvas is exactly the size of the scaled map image.
 */
function gameToHeatmapPixel(
  gameX: number,
  gameY: number,
  bounds: MapBounds,
  canvasW: number,
  canvasH: number
): { x: number; y: number } {
  const xRange = bounds.maxX - bounds.minX;
  const yRange = bounds.maxY - bounds.minY;

  const normX = (gameX - bounds.minX) / xRange;
  const normY = (bounds.maxY - gameY) / yRange;

  return {
    x: normX * canvasW,
    y: normY * canvasH,
  };
}

const COLOR_STOPS: Array<{ t: number; r: number; g: number; b: number }> = [
  { t: 0.0, r: 0, g: 0, b: 40 },       // dark blue (low density)
  { t: 0.15, r: 0, g: 100, b: 200 },    // blue
  { t: 0.35, r: 0, g: 200, b: 180 },    // cyan
  { t: 0.55, r: 50, g: 230, b: 50 },    // green
  { t: 0.75, r: 230, g: 230, b: 0 },    // yellow
  { t: 0.95, r: 240, g: 80, b: 0 },     // orange
  { t: 1.0, r: 240, g: 20, b: 0 },      // red (high density)
];

function lerpColor(t: number): { r: number; g: number; b: number } {
  t = Math.max(0, Math.min(1, t));

  let lower = COLOR_STOPS[0];
  let upper = COLOR_STOPS[COLOR_STOPS.length - 1];

  for (let i = 0; i < COLOR_STOPS.length - 1; i++) {
    if (t >= COLOR_STOPS[i].t && t <= COLOR_STOPS[i + 1].t) {
      lower = COLOR_STOPS[i];
      upper = COLOR_STOPS[i + 1];
      break;
    }
  }

  const range = upper.t - lower.t;
  const factor = range === 0 ? 0 : (t - lower.t) / range;

  return {
    r: Math.round(lower.r + (upper.r - lower.r) * factor),
    g: Math.round(lower.g + (upper.g - lower.g) * factor),
    b: Math.round(lower.b + (upper.b - lower.b) * factor),
  };
}

function renderHeatmap(
  positions: Array<{ X: number; Y: number }>,
  bounds: MapBounds,
  canvasW: number,
  canvasH: number,
  reuseCanvas?: HTMLCanvasElement | null,
): HTMLCanvasElement | null {
  if (canvasW <= 0 || canvasH <= 0) {
    console.warn("Heatmap: invalid canvas dimensions", canvasW, canvasH);
    return null;
  }

  console.log(`Heatmap: rendering ${positions.length} points onto ${canvasW}x${canvasH} canvas`);

  // Reuse existing canvas or create a new one
  const canvas = reuseCanvas || document.createElement("canvas");
  canvas.width = canvasW;
  canvas.height = canvasH;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.clearRect(0, 0, canvasW, canvasH);

  // Adaptive parameters: fewer points → larger radius + higher intensity
  const radius = Math.round(12 + 200 / Math.sqrt(positions.length));
  const intensity = Math.min(0.3, 1.5 / Math.sqrt(positions.length));

  console.log(`Heatmap: adaptive radius=${radius}, intensity=${intensity.toFixed(4)}`);

  // Pass 1: Accumulate density
  ctx.globalCompositeOperation = "lighter";

  let onCanvas = 0;
  for (const pos of positions) {
    const { x, y } = gameToHeatmapPixel(pos.X, pos.Y, bounds, canvasW, canvasH);

    if (x < -radius || x > canvasW + radius ||
        y < -radius || y > canvasH + radius) {
      continue;
    }
    onCanvas++;

    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, `rgba(255, 255, 255, ${intensity})`);
    gradient.addColorStop(0.3, `rgba(255, 255, 255, ${intensity * 0.6})`);
    gradient.addColorStop(1, "rgba(255, 255, 255, 0)");

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  console.log(`Heatmap: ${onCanvas}/${positions.length} points on canvas`);

  // Pass 2: Colorize
  ctx.globalCompositeOperation = "source-over";
  const imageData = ctx.getImageData(0, 0, canvasW, canvasH);
  const data = imageData.data;
  let coloredPixels = 0;

  for (let i = 0; i < data.length; i += 4) {
    const alpha = data[i + 3];

    if (alpha > 1) {
      const density = Math.min(1, alpha / 255);
      const color = lerpColor(density);

      data[i] = color.r;
      data[i + 1] = color.g;
      data[i + 2] = color.b;
      data[i + 3] = Math.min(alpha * 3, 220);
      coloredPixels++;
    }
  }

  console.log(`Heatmap: colored ${coloredPixels} pixels`);

  ctx.putImageData(imageData, 0, 0);
  return canvas;
}

export default function HeatmapLayer({
  positions,
  mapBounds,
  imageWidth,
  imageHeight,
  visible,
  offsetX = 0,
  offsetY = 0,
}: HeatmapLayerProps) {
  const [heatmapCanvas, setHeatmapCanvas] = useState<HTMLCanvasElement | null>(null);
  const renderIdRef = useRef(0);
  // Reuse a single offscreen canvas to avoid GC pressure
  const offscreenRef = useRef<HTMLCanvasElement | null>(null);
  // Debounce resize-triggered re-renders
  const resizeTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const doRender = useCallback(() => {
    if (!visible || positions.length === 0 || imageWidth <= 0 || imageHeight <= 0) {
      setHeatmapCanvas(null);
      return;
    }

    const renderId = ++renderIdRef.current;

    const rafId = requestAnimationFrame(() => {
      console.log("HeatmapLayer: starting render, id=", renderId);
      const start = performance.now();

      const canvas = renderHeatmap(
        positions, mapBounds, imageWidth, imageHeight,
        offscreenRef.current,
      );
      // Keep reference for reuse
      if (canvas) {
        offscreenRef.current = canvas;
      }

      const elapsed = performance.now() - start;
      console.log(`HeatmapLayer: render took ${elapsed.toFixed(1)}ms`);

      if (renderIdRef.current === renderId && canvas) {
        setHeatmapCanvas(canvas);
      }
    });

    return () => cancelAnimationFrame(rafId);
  }, [positions, mapBounds, imageWidth, imageHeight, visible]);

  useEffect(() => {
    // Debounce resize-triggered renders by 150ms
    if (resizeTimerRef.current) {
      clearTimeout(resizeTimerRef.current);
    }
    resizeTimerRef.current = setTimeout(() => {
      doRender();
    }, 150);

    return () => {
      if (resizeTimerRef.current) {
        clearTimeout(resizeTimerRef.current);
      }
    };
  }, [doRender]);

  if (!visible || !heatmapCanvas) {
    console.log("HeatmapLayer: returning null", { visible, hasCanvas: !!heatmapCanvas });
    return null;
  }

  console.log("HeatmapLayer: rendering KonvaImage", { offsetX, offsetY, imageWidth, imageHeight });

  return (
    <KonvaImage
      image={heatmapCanvas}
      x={offsetX}
      y={offsetY}
      width={imageWidth}
      height={imageHeight}
      opacity={0.7}
    />
  );
}
