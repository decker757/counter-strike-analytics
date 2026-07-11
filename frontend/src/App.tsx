import MapCanvas from './components/MapCanvas'
import { useState, useEffect } from 'react';
import type { RoundsData, RoundInfo } from "./types/Player"
import './App.css'

function App() {
  const [currentTick, setCurrentTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [replayEndTick, setReplayEndTick] = useState<number | null>(null);
  const [rounds, setRounds] = useState<RoundInfo[]>([]);
  const [replayRound, setReplayRound] = useState<number>(0);

  // Fetch available rounds for replay
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

  const handleSeekToRound = (startTick: number, endTick: number) => {
    setCurrentTick(startTick);
    setReplayEndTick(endTick);
    setIsPlaying(true);
  };

  const handleReplayClick = () => {
    const info = rounds.find((r) => r.round_num === replayRound);
    if (info) {
      handleSeekToRound(info.start_tick, info.end_tick);
    }
  };

  // Auto-stop at round end
  useEffect(() => {
    if (replayEndTick !== null && currentTick >= replayEndTick) {
      setIsPlaying(false);
      setReplayEndTick(null);
    }
  }, [currentTick, replayEndTick]);

  // Tick playback timer
  useEffect(() => {
    let interval: number | undefined;

    if (isPlaying) {
      const msPerTick = 15.6 / playbackSpeed;

      interval = window.setInterval(() => {
        setCurrentTick((prev) => prev + 1);
      }, msPerTick);
    } else {
      clearInterval(interval);
    }

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed]);

  return (
    <div>
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>CS2 Match Analysis</h2>
        <p>Current Tick: {currentTick}</p>

        <button onClick={() => setIsPlaying(!isPlaying)}>
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <select onChange={(e) => setPlaybackSpeed(Number(e.target.value))}>
          <option value='1'>1x Speed</option>
          <option value='2'>2x Speed</option>
          <option value='4'>4x Speed</option>
        </select>

        <select
          value={replayRound}
          onChange={(e) => setReplayRound(Number(e.target.value))}
          style={{ marginLeft: 12 }}
        >
          <option value={0}>Replay Round...</option>
          {rounds.map((r) => (
            <option key={r.round_num} value={r.round_num}>
              Round {r.round_num}
            </option>
          ))}
        </select>

        <button
          onClick={handleReplayClick}
          disabled={replayRound === 0}
          style={{
            opacity: replayRound === 0 ? 0.5 : 1,
            cursor: replayRound === 0 ? 'default' : 'pointer',
          }}
        >
          Replay
        </button>
      </div>

      <MapCanvas currentTick={currentTick} />
    </div>
  )
}

export default App
