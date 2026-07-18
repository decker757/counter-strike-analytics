import { useEffect, useRef, useState, useCallback } from "react";
import type { Player } from "../types/Player";

const CHUNK_SIZE = 256; // ticks per fetch (~2s of buffer at 1x speed)
const BASE_URL = "http://localhost:8000";

/**
 * Prefetching tick buffer for smooth playback.
 *
 * Instead of fetching one tick at a time (N HTTP round-trips/sec),
 * this fetches chunks of 256 ticks at once and serves them from a
 * local Map cache. A background prefetch keeps the next chunk ready.
 */
export function useTickBuffer(currentTick: number): Player[] {
  const cache = useRef<Map<number, Player[]>>(new Map());
  const [players, setPlayers] = useState<Player[]>([]);
  const pending = useRef<Map<number, AbortController>>(new Map());
  // Track the last tick we served so we don't re-render on same tick
  const lastServedRef = useRef(-1);

  const fetchChunk = useCallback((chunkStart: number) => {
    // Already fetching this chunk
    if (pending.current.has(chunkStart)) return;

    const controller = new AbortController();
    pending.current.set(chunkStart, controller);

    fetch(
      `${BASE_URL}/api/state-range?start=${chunkStart}&end=${chunkStart + CHUNK_SIZE}`,
      { signal: controller.signal },
    )
      .then((r) => r.json())
      .then((data) => {
        if (!data.states) return;
        for (const [tickStr, tickPlayers] of Object.entries(data.states)) {
          cache.current.set(Number(tickStr), tickPlayers as Player[]);
        }
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Buffer fetch failed:", err);
        }
      })
      .finally(() => {
        pending.current.delete(chunkStart);
      });
  }, []);

  useEffect(() => {
    const tick = currentTick;
    if (tick < 0) return;

    // Serve from cache
    const cached = cache.current.get(tick);
    if (cached && tick !== lastServedRef.current) {
      lastServedRef.current = tick;
      setPlayers(cached);
      return;
    }

    // Cache miss — fetch the chunk containing this tick
    const chunkStart = Math.floor(tick / CHUNK_SIZE) * CHUNK_SIZE;
    fetchChunk(chunkStart);

    // Also prefetch the next chunk
    const nextChunk = chunkStart + CHUNK_SIZE;
    if (!cache.current.has(nextChunk)) {
      fetchChunk(nextChunk);
    }

    // Garbage collect: remove chunks more than 5 chunks away
    const minKeep = chunkStart - CHUNK_SIZE * 2;
    const maxKeep = chunkStart + CHUNK_SIZE * 3;
    for (const key of cache.current.keys()) {
      if (key < minKeep || key > maxKeep) {
        cache.current.delete(key);
      }
    }

    // Cancel far-away pending fetches
    for (const [start, ctrl] of pending.current) {
      if (Math.abs(start - chunkStart) > CHUNK_SIZE * 4) {
        ctrl.abort();
        pending.current.delete(start);
      }
    }
  }, [currentTick, fetchChunk]);

  return players;
}
