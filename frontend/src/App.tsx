import MapCanvas from './components/MapCanvas'
import { useState, useEffect, useRef, useCallback } from 'react';
import type { RoundsData, RoundInfo } from "./types/Player"
import './App.css'

function App() {
  const [currentTick, setCurrentTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [replayEndTick, setReplayEndTick] = useState<number | null>(null);
  const [rounds, setRounds] = useState<RoundInfo[]>([]);
  const [replayRound, setReplayRound] = useState<number>(0);

  const tickRef = useRef(0);
  const lastFrameRef = useRef(0);
  const rafRef = useRef(0);

  useEffect(() => {
    async function fetchRounds() {
      try {
        const response = await fetch("http://localhost:8000/api/rounds");
        const data: RoundsData = await response.json();
        setRounds(data.rounds || []);
      } catch (error) {
        console.error("Error fetching rounds:", error);
      }
    }
    fetchRounds();
  }, []);

  const handleSeekToRound = useCallback((startTick: number, endTick: number) => {
    tickRef.current = startTick;
    setCurrentTick(startTick);
    setReplayEndTick(endTick);
    setIsPlaying(true);
  }, []);

  const handleReplayClick = useCallback(() => {
    const info = rounds.find((r) => r.round_num === replayRound);
    if (info) {
      handleSeekToRound(info.start_tick, info.end_tick);
    }
  }, [rounds, replayRound, handleSeekToRound]);

  useEffect(() => {
    if (replayEndTick !== null && currentTick >= replayEndTick) {
      setIsPlaying(false);
      setReplayEndTick(null);
    }
  }, [currentTick, replayEndTick]);

  useEffect(() => {
    tickRef.current = currentTick;
  }, [currentTick]);

  // RAF-based playback
  useEffect(() => {
    if (!isPlaying) {
      cancelAnimationFrame(rafRef.current);
      return;
    }

    lastFrameRef.current = 0;

    const loop = (now: number) => {
      if (lastFrameRef.current === 0) {
        lastFrameRef.current = now;
        rafRef.current = requestAnimationFrame(loop);
        return;
      }

      const elapsed = now - lastFrameRef.current;
      lastFrameRef.current = now;

      const msPerTick = 15.625 / playbackSpeed;
      tickRef.current += elapsed / msPerTick;

      const roundedTick = Math.round(tickRef.current);
      setCurrentTick(roundedTick);

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [isPlaying, playbackSpeed]);

  return (
    <div>
      {/* ── Control Bar ── */}
      <div className="control-bar animate-in">
        {/* Play/Pause */}
        <button
          className={`btn ${isPlaying ? 'btn-primary' : 'btn-success'}`}
          onClick={() => setIsPlaying(!isPlaying)}
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>

        {/* Speed selector */}
        <div className="control-group">
          <span className="speed-badge">
            {playbackSpeed}×
          </span>
          <select
            className="select"
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
          >
            <option value={0.5}>0.5×</option>
            <option value={1}>1×</option>
            <option value={2}>2×</option>
            <option value={4}>4×</option>
          </select>
        </div>

        <span className="control-divider" />

        {/* Tick counter */}
        <span className="tick-display">
          Tick {currentTick}
        </span>

        <span className="control-divider" />

        {/* Round replay */}
        <select
          className="select"
          value={replayRound}
          onChange={(e) => setReplayRound(Number(e.target.value))}
        >
          <option value={0}>↻ Replay Round…</option>
          {rounds.map((r) => (
            <option key={r.round_num} value={r.round_num}>
              Round {r.round_num} (T{r.start_tick}–{r.end_tick})
            </option>
          ))}
        </select>

        <button
          className="btn"
          onClick={handleReplayClick}
          disabled={replayRound === 0}
        >
          Go
        </button>
      </div>

      {/* ── Map ── */}
      <MapCanvas currentTick={currentTick} rounds={rounds} isPlaying={isPlaying} />
    </div>
  )
}

export default App
