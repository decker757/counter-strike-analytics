# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (Python)
```bash
cd backend
pip install -r requirements.txt                          # install deps
python examples/position_analysis.py <path/to/demo.dem>   # start API server on :8000
```

### Frontend (React + TypeScript + Vite)
```bash
cd frontend
npm install                                               # install deps
npm run dev                                               # dev server on :5173
npm run build                                             # production build (tsc + vite)
npx tsc -p tsconfig.app.json --noEmit                     # type-check only
```

### Run the visual analysis app
```bash
# Terminal 1
cd backend
python examples/position_analysis.py data/demos/<demo>.dem

# Terminal 2
cd frontend
npm run dev
# Open http://localhost:5173
```

## Architecture

This is a full-stack CS2 analytics toolkit: Python backend parses `.dem` replay files and serves data via FastAPI; a React/Konva frontend renders a 2D overhead map with animated player markers and heatmaps.

### Two separate parser paths

The codebase has **two independent parser setups** that both wrap `demoparser2`:

1. **`backend/examples/position_analysis.py`** — Uses `demoparser2.DemoParser` directly. Parses raw tick data into a single pandas DataFrame at startup and serves it via FastAPI. This is the backend for the web visualization. Fields: `tick, steamid, name, team_name, X, Y, Z, is_alive`.

2. **`backend/src/parsers/demo_parser.py`** — The project's own `DemoParser` wrapper class. Adds round mapping, team name normalization, economy extraction, and returns structured Pydantic models (`Match`, `PlayerFrame`, `Kill`, etc.). Used by the analysis and ML modules.

These two paths use **different field naming conventions**: the raw path uses uppercase `X, Y, Z` and `team_name`; the project parser normalizes to lowercase `x, y, z` and `team` ("CT"/"T").

### Frontend data flow

- `App.tsx` manages playback state (`currentTick`, `isPlaying`, `playbackSpeed`) and round replay controls
- `MapCanvas.tsx` polls `GET /api/state/{tick}` every even tick, converts game coordinates to canvas pixels, renders player markers
- `HeatmapLayer.tsx` fetches `GET /api/heatmap` with filter params, renders density via offscreen canvas → Konva Image
- `PlayerMarker.tsx` renders colored circles (CT=blue, T=orange) with hover tooltips
- Coordinate transform: `canvasX = (gameX - minX) / (maxX - minX) * width + offset`, Y is inverted (game Y goes up, canvas Y goes down)

### Heatmap API filters

All three filters combine: `GET /api/heatmap?steamid=&team=&round_num=&sample_rate=`
- `steamid` empty = all players, `team` empty = both teams, `round_num=0` = all rounds
- Round 0 = warmup (always excluded from heatmap data)
- Single rounds use finer sampling (`sample_rate=8` vs `64`)

### Round numbering

CS2 events use inconsistent round numbering across event types. The backend normalizes this:
- `round_start` round 1 = warmup; rounds 2+ = real game rounds
- `round_end` round N = end of actual round N-1 (off by one from round_start)
- `round_announce_match_start` tick marks warmup end
- Backend rebuilds: round 1 = pistol round (from match_start to first round_end), rounds 2+ from round_start boundaries
- Warmup ticks return round 0 from `_get_round_for_tick()`

### Map bounds

Defined in `frontend/src/components/MapCanvas.tsx` as `MAP_CONFIG`. Backend map configs at `backend/config/maps/` are used by the analysis modules but NOT by the web visualization. The backend returns map names with `de_` prefix (e.g. `de_inferno`); the frontend strips this to find the matching map image and bounds.

## Gotchas

- **SteamID precision**: SteamIDs are 64-bit integers (`uint64`). JSON numbers lose precision in JavaScript for values > 2^53. Always convert steamids to strings in API responses.
- **Team names from raw parser**: `demoparser2` returns `"CT"` and `"TERRORIST"` (not "T"). The heatmap team filter dropdown uses `"CT"` / `"TERRORIST"`.
- **The `/api/map` route must have a leading slash** — FastAPI requires `@app.get("/api/map")`.
- **Vite has no proxy configured** — all API calls use absolute URLs (`http://localhost:8000`). CORS is enabled on the backend for development.
