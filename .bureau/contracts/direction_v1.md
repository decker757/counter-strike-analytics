# Direction Contract v1.0.0

> **Ratified:** 2026-07-12 by the founding team Aegis Analytics (Soren Voss, Elara Chen, Viktor Kade)
>
> **Status:** Awaiting human approval
>
> **Supersedes:** None (initial contract)
>
> This contract defines **intent**, not implementation. All operational teams are bound to its spirit — the what and the why — but retain full freedom over the how.

---

## 1. What We Are Building

**A CS2 analytics platform that predicts and visualizes player intent — where players are going, what they're trying to do, and why — layered on top of a comprehensive match analytics foundation.**

### The core insight

No existing CS2 analytics tool predicts player *intent*. Leetify, Scope.gg, Noesis, Refrag, and SkyBox all show what *happened* — kill locations, heatmaps, economy graphs, stat dashboards. None answer the question: *what was the player trying to do, and what will they do next?*

Our platform answers this by combining:

1. **Spatial playback** (already working — 2D map, player markers, heatmaps)
2. **Comprehensive analytics** (Phase 1 — stats, economy, round timeline, player comparison)
3. **Intent prediction** (Phase 2-3 — predicted movement paths, action classification, strategy labels)
4. **Narrative intelligence** (Phase 5 — LLM-generated round summaries and coaching insights)

### Competitive positioning

| Dimension | Leetify | Scope.gg | Noesis | Refrag | **Ours** |
|-----------|---------|----------|--------|--------|----------|
| Stat dashboards | ✓✓✓ | ✓✓✓ | ✓ | ✓ | ✓✓ |
| Spatial replay | ✗ | ✗ | ✓✓✓ | ✓✓ | ✓✓✓ |
| Multi-round aggregation | ✗ | ✗ | ✓✓✓ | ✗ | ✓✓ |
| Economy analysis | ✓✓ | ✓✓ | ✗ | ✗ | ✓✓ |
| Intent prediction | ✗ | ✗ | ✗ | ✗ | **✓✓✓** |
| LLM coaching | ✓ (basic) | ✗ | ✗ | ✗ | **✓✓✓** |

### What "Intent Prediction" means

"Intent" is decomposed into three tiers of increasing ambition:

**Tier 1 — Movement Destination (MVP):** Given a player's recent trajectory and game state, predict their position T seconds into the future. This captures tactical decisions: heading to A site vs B, rotating through spawn, pushing a lane vs holding. Evaluated by Average Displacement Error (ADE) against actual positions.

**Tier 2 — Action Classification (v2):** Classify the player's current action from a tactical taxonomy: holding, pushing, rotating, falling back, flanking, executing, saving. Derived from position deltas, distance to objectives, velocity, and event context.

**Tier 3 — Strategic Role (v3):** Identify the player's role in the round: entry fragger, AWPer, support, lurker, IGL. Based on full-match positioning patterns and engagement statistics.

The "self-trained" model is a **Transformer encoder** (~1-10M parameters) trained from scratch on the user's own demo collection. It is NOT a large language model — LLMs are the wrong architecture for spatiotemporal prediction. The LLM enters in Phase 5 as a narrative layer that explains predictions in natural language.

---

## 2. MVP Definition

### The first concrete deliverable: Movement Pathway Prediction Overlay

**What ships:**

A user loads a demo. On the 2D map, each player's marker now has a predicted movement path — a colored arc showing where the model predicts they'll be in 1, 2, and 3 seconds. A "Show Intent" toggle (matching the existing Heatmap toggle pattern) enables/disables this overlay.

**Backend:**
- New endpoint `GET /api/intent/{tick}` returning predicted paths, zone labels, and intent classifications for all alive players
- Map zone definitions for Inferno and Dust2 (polygon-based, with adjacency graphs)
- Rule-based predictor: velocity extrapolation constrained by zone connectivity + simple heuristics for push/hold/rotate classification
- Parse cache: demos parsed once, stored as Parquet, loaded instantly on restart

**Frontend:**
- Intent overlay layer on the Konva map: colored arcs showing predicted paths (fading with time horizon), ghost markers at 1s/2s/3s ahead
- "Show Intent" toggle checkbox in the control panel
- Color-coded by team (blue CT / orange T), consistent with existing player markers
- Zone labels at arc endpoints

**Training pipeline (infrastructure, no model yet):**
- Script `backend/scripts/build_trajectory_dataset.py` that extracts training examples from parsed demos and writes to Parquet
- Each example: (player trajectory window, game context, future position) — fully self-supervised, no manual labeling

### Success criteria (falsifiable, pre-registered)

| ID | Criterion | Baseline | Threshold | Verdict |
|----|-----------|----------|-----------|---------|
| S1 | Trajectory ADE at T=3s | Constant-velocity linear extrapolation | ADE < 80% of baseline | — |
| S2 | Zone classification accuracy | Random zone (uniform) | > 65% top-1 on held-out demo, ≥100 transitions | — |
| S3 | Playback framerate with intent overlay | — | ≥30fps at 2x playback speed | — |
| S4 | Self-training pipeline completes | — | 5 demos → trained model in <5 min on CPU, no manual labeling | — |
| S5 | End-to-end integration | — | Load demo → click "Show Intent" → predictions visible in ≤2s | — |

### Explicitly OUT of MVP scope
- No trained neural network for prediction (the rule-based system ships first; the ML model replaces it in Phase 3)
- No LLM of any kind
- No player stat dashboards or economy charts
- No round outcome prediction in the UI
- No multi-demo comparison
- No utility/grenade visualization
- Map zones only for Inferno and Dust2 (the two maps currently supported)

---

## 3. Feature Roadmap

### Phase 1: Core Analytics Foundation
*Prerequisite for everything below. The existing app is playback + heatmap only.*

- **Unified parser backend** — Replace raw `demoparser2` calls in `position_analysis.py` with the project's `DemoParser` class; all API endpoints serve from structured Pydantic models
- **Parse cache** — Parse once, store as Parquet per demo; subsequent loads are instant
- **Player stat cards** — K/D, ADR, headshot%, first kills, trade kills, multi-kill counts, per-player
- **Economy timeline** — Round-by-round bar chart: team money, buy type colors
- **Match dashboard** — Score, round results, economy graph, kill feed with map positions
- **Tick scrubber** — Free timeline scrubbing (not just round boundaries)

### Phase 2: Intent MVP (This contract's MVP)
- Rule-based intent predictor (zone graph + velocity extrapolation)
- `GET /api/intent/{tick}` endpoint
- Intent overlay on map (prediction arcs, ghost markers, zone labels)
- Training data pipeline (trajectory dataset as Parquet)
- Intent toggle control in the UI

### Phase 3: ML-Powered Intent
- Transformer encoder trained on user's demos, replacing rule-based predictor
- Probabilistic intent heatmap (2D probability density of future position)
- Confidence visualization (uncertainty cones, opacity by confidence)
- Round outcome prediction surfaced in UI (existing `RoundPredictor` integration)
- Multi-demo model training and evaluation

### Phase 4: Tactical Analysis
- Team formation detection (executes, defaults, split pushes)
- Kill position map (markers at kill locations with weapon/victim tooltips)
- Utility visualization (smokes, flashes, molotovs on the timeline)
- Opening duel analysis with round outcome correlation
- Multi-round aggregation (Noesis-style: overlay positions from N rounds on one map)

### Phase 5: LLM Integration
- Round narrative generator (3-5 sentence post-round summaries from structured data)
- Intent explanation ("Player is likely rotating because bomb was spotted A and teammate died mid")
- Coach query mode (NL → structured query → map visualization)
- Post-match report generation (PDF/HTML with stats, graphs, key moments)

---

## 4. Key Architectural Decisions

### AD-1: Unify parser paths
The two separate parser setups (`position_analysis.py` raw path vs `src/parsers/demo_parser.py` project parser) must be unified. The project `DemoParser` becomes the single canonical parser. The web API serves from structured Pydantic models, not raw DataFrames.

### AD-2: Parse-once, store as Parquet
No database yet — Parquet files provide columnar storage well-suited to time-series position data. Parsed demos persist to `backend/data/parses/{demo_hash}/`. The existing `RoundDataset.to_parquet()` pattern is extended to all parsed data.

### AD-3: Map zone system
Each map defines zones as named polygons with an adjacency graph. Zones are hand-authored (there are only ~7 competitive maps, and the app currently supports 2). Zones drive both rule-based prediction (next zone = adjacent along movement vector) and ML features (zone ID as categorical input).

### AD-4: Pre-computed intent predictions
Intent predictions are computed at parse time and stored alongside frame data. The API serves pre-computed predictions as static data (no live inference during playback). The rule-based MVP can optionally compute live since it's fast; the ML model path pre-computes.

### AD-5: ML architecture
Transformer encoder (d_model=128, nhead=4, num_layers=4), trained from scratch. Input: position history + game context (zone, team, alive count, bomb status, time). Output: future positions over next 64-192 ticks. Trained via self-supervision on the user's demo collection. No external data or pre-trained weights required.

### AD-6: Frontend state management
For MVP: extract a `useGameState` custom hook. For Phase 3+: introduce Zustand with slices (playback, filters, intent, analytics). All API calls move into a typed `api.ts` module.

### AD-7: LLM strategy
LLM used for explanation, not prediction. A small local model (e.g., Llama 5.1 8B, Qwen 3.6 32B) running via Ollama. Receives structured game-state summaries as context, generates natural language insights. No fine-tuning required — in-context only. This is Phase 5; earlier phases have zero LLM dependency.

---

## 5. Constraints and Boundaries

### All teams must respect:

1. **Parse once.** No team may introduce a third parser path. All demo data flows through `DemoParser` (AD-1).

2. **Stay local.** This is a desktop/self-hosted tool. No cloud dependencies for core functionality. The LLM in Phase 5 runs locally via Ollama. API calls stay within localhost.

3. **No manual labeling required.** The "self-trained" promise means all training data is derived automatically from demos. No feature may require a human to label game states.

4. **SteamID as string, always.** SteamIDs are 64-bit integers that lose precision in JavaScript. All API responses must serialize them as strings.

5. **Map bounds from backend.** Map configurations (bounds, zones, images) should be served by the backend, not hardcoded in the frontend. The existing `MAP_CONFIG` hardcoding in `MapCanvas.tsx` is technical debt to be resolved in Phase 1.

6. **Performance budget.** Playback at 2x speed must maintain ≥30fps. Heatmap rendering must not block the main thread. Intent prediction overlay must not degrade playback.

7. **Backward compatibility.** The existing demo playback + heatmap functionality must continue working throughout all phases. New features are additive; nothing is removed without a deprecation notice.

8. **Falsifiable claims only.** Any claim that a feature "improves" something must be backed by a pre-registered metric and a baseline measurement, following the pattern set by criteria S1-S5.

---

## 6. Open Questions

These are questions the founding team could not resolve and that operational teams should be aware of. Answers may evolve as we build.

| # | Question | Current Best Answer | Risk if Wrong |
|---|----------|---------------------|---------------|
| Q1 | How many demo files does the user have for training? | Unknown. The system should work with as few as 5 demos (MVP) and scale to thousands. | Model underfits with too few demos; Phase 3 delayed. |
| Q2 | What GPU/hardware is available? | Assume CPU-only for MVP training, consumer GPU (RTX 3060+) for Phase 3+. | Phase 3 training too slow on CPU-only. Provide a CPU-friendly model size option. |
| Q3 | Is the zone system worth the manual authoring cost? | Yes for 2 maps (MVP). Re-evaluate at 7 maps. | Zone authoring becomes a bottleneck. Auto-clustering with manual labels as fallback. |
| Q4 | How should intent predictions be evaluated beyond metrics? | Criteria S1-S2 are quantitative. Qualitative: manual review of prediction arcs on known demos. | Predictions are mathematically good but tactically nonsense. Add domain-expert review step. |
| Q5 | What if the user really wants an LLM they can "talk to"? | Phase 5 delivers this, but earlier phases do not. If this is a hard requirement, Phase 5 should be pulled forward or done in parallel. | User perceives the product as incomplete without NL interface. |
| Q6 | Should we support CS:GO demos or CS2 only? | CS2 only. CS:GO demos have different format and events. The `demoparser2` library is CS2-specific. | Locks out CS:GO demo archives. Acceptable — CS2 replaced CS:GO in 2023. |
| Q7 | Multi-language support for LLM narratives? | English only for MVP through Phase 5. The LLM layer can be prompted in any language; local models like Qwen support Chinese, etc. | Non-English users excluded from narrative features. Mitigated by model choice. |

---

## 7. Governance

### Mission Guardian
The founding team (Aegis Analytics) serves as the mission guardian. If the founding team is dissolved, guardianship transfers to the human. The guardian owns the recurring question: **"Is this mission still good, safe, and worth pursuing?"** and holds the standing to halt and escalate.

### Amendment
This contract may be amended by the founding team (or successor partners) through the process defined in the constitution ([Foundation](../constitution/foundation.md) §5). Amendments require recorded reasoning and adversarial review. The human ratifies any change to the MVP definition or the constraints in §5.

### Version
This is v1.0.0 of the direction contract. It follows Semantic Versioning:
- **MAJOR** — Change to the MVP definition or core intent
- **MINOR** — New phase added, architectural decision changed, constraint added/removed
- **PATCH** — Clarification, open question resolved, wording improvement

---

*Drafted by the founding team Aegis Analytics: Soren Voss (Strategist), Elara Chen (Researcher), Viktor Kade (Critic). The research report informing this contract cites 20+ sources across the CS2 analytics landscape, esports AI research, and demo data specifications. Full agent transcripts available in the session record.*
