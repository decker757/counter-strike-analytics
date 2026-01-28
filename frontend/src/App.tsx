import MapCanvas from './components/MapCanvas'
import type { Player } from "./types/Player"
import './App.css'

const mockPlayers: Player[] = [
  {
    id: "1",
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

function App() {

  return (
    <MapCanvas players={mockPlayers} />
  )
}

export default App
