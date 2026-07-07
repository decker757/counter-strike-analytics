import MapCanvas from './components/MapCanvas'
import { useState, useEffect } from 'react';
import type { Player } from "./types/Player"
import './App.css'




function App() {
  const [currentTick, setCurrentTick] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 1x, 2x, etc.

  useEffect(() => {
    let interval: number | undefined;

    if (isPlaying) {
      // 64 ticks per second is roughly 15.6ms per tick
      // We divide by playbackSpeed to go faster (e.g., 2x speed)
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
      </div>

      <MapCanvas currentTick={currentTick} />
    </div>
  )
}

export default App




/*
const mockPlayers: Player[] = [
  {
    steamid: "1",
    name: "s1mple",
    x: 400,
    y: 300,
    team: "T",
    alive: true
  },
  {
    id: "2",
    name: "device",
    x: 450,
    y: 350,
    team: "CT",
    alive: true
  }
];
*/