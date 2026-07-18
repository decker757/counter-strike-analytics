import { useEffect, useRef, useState } from "react";
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
  return {
    x: ((gameX - bounds.minX) / xRange) * canvasW,
    y: ((bounds.maxY - gameY) / yRange) * canvasH,
  };
}

const COLOR_STOPS: Array<{ t: number; r: number; g: number; b: number }> = [
  { t: 0.0, r: 0, g: 0, b: 40 },
  { t: 0.15, r: 0, g: 100, b: 200 },
  { t: 0.35, r: 0, g: 200, b: 180 },
  { t: 0.55, r: 50, g: 230, b: 50 },
  { t: 0.75, r: 230, g: 230, b: 0 },
  { t: 0.95, r: 240, g: 80, b: 0 },
  { t: 1.0, r: 240, g: 20, b: 0 },
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
  if (canvasW <= 0 || canvasH <= 0) return null;

  // Reuse or create canvas
  const canvas = reuseCanvas || document.createElement("canvas");
  canvas.width = canvasW;
  canvas.height = canvasH;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.clearRect(0, 0, canvasW, canvasH);

  // Adaptive parameters: fewer points → larger radius + higher intensity
  const radius = Math.round(12 + 200 / Math.sqrt(Math.max(positions.length, 1)));
  const intensity = Math.min(0.3, 1.5 / Math.sqrt(Math.max(positions.length, 1)));

  // Pass 1: Accumulate density
  ctx.globalCompositeOperation = "lighter";
  for (const pos of positions) {
    const { x, y } = gameToHeatmapPixel(pos.X, pos.Y, bounds, canvasW, canvasH);
    if (x < -radius || x > canvasW + radius || y < -radius || y > canvasH + radius) continue;

    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, `rgba(255, 255, 255, ${intensity})`);
    gradient.addColorStop(0.3, `rgba(255, 255, 255, ${intensity * 0.6})`);
    gradient.addColorStop(1, "rgba(255, 255, 255, 0)");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  // Pass 2: Colorize
  ctx.globalCompositeOperation = "source-over";
  const imageData = ctx.getImageData(0, 0, canvasW, canvasH);
  const data = imageData.data;
  for (let i = 0; i < data.length; i += 4) {
    const alpha = data[i + 3];
    if (alpha > 1) {
      const density = Math.min(1, alpha / 255);
      const color = lerpColor(density);
      data[i] = color.r;
      data[i + 1] = color.g;
      data[i + 2] = color.b;
      data[i + 3] = Math.min(alpha * 3, 220);
    }
  }
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
  const offscreenRef = useRef<HTMLCanvasElement | null>(null);
  // Debounce only for resize events
  const resizeTimerRef = useRef<ReturnType<typeof setTimeout>>();
  // Track if the trigger was a resize vs a data change
  const lastDimsRef = useRef({ w: imageWidth, h: imageHeight });

  // Immediate render for data changes (positions, visible, bounds)
  useEffect(() => {
    // Clear: discard any stale canvas so next render starts fresh
    if (!visible || positions.length === 0 || imageWidth <= 0 || imageHeight <= 0) {
      setHeatmapCanvas(null);
      offscreenRef.current = null; // force fresh canvas on next data
      return;
    }

    const dimsChanged =
      imageWidth !== lastDimsRef.current.w || imageHeight !== lastDimsRef.current.h;
    lastDimsRef.current = { w: imageWidth, h: imageHeight };

    // For resize events: same data, different size — reuse canvas, debounce
    if (dimsChanged) {
      if (resizeTimerRef.current) clearTimeout(resizeTimerRef.current);
      resizeTimerRef.current = setTimeout(() => {
        const renderId = ++renderIdRef.current;
        const canvas = renderHeatmap(positions, mapBounds, imageWidth, imageHeight, offscreenRef.current);
        if (canvas) offscreenRef.current = canvas;
        if (renderIdRef.current === renderId && canvas) setHeatmapCanvas(canvas);
      }, 150);
      return () => {
        if (resizeTimerRef.current) clearTimeout(resizeTimerRef.current);
      };
    }

    // For data changes: always create a FRESH canvas (never reuse old data canvas)
    offscreenRef.current = null;
    const renderId = ++renderIdRef.current;
    const rafId = requestAnimationFrame(() => {
      const canvas = renderHeatmap(positions, mapBounds, imageWidth, imageHeight, null);
      if (canvas) offscreenRef.current = canvas;
      if (renderIdRef.current === renderId && canvas) setHeatmapCanvas(canvas);
    });
    return () => cancelAnimationFrame(rafId);
  }, [positions, mapBounds, imageWidth, imageHeight, visible]);

  if (!visible || !heatmapCanvas) return null;

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
