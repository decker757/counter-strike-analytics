# Founding Team — "Aegis Analytics"

## Formation

- **Team name:** Aegis Analytics (Founding)
- **Scope:** Vision, strategy, and direction-setting for the CS2 Analytics Platform
- **First day:** 2026-07-12
- **Status:** Active (oversight)

## Members

| Name | Role | First Day | Status |
|------|------|-----------|--------|
| Soren Voss | Strategist | 2026-07-12 | Active |
| Elara Chen | Researcher | 2026-07-12 | Active |
| Viktor Kade | Critic | 2026-07-12 | Active |

## Member Profiles

### Soren Voss — Strategist
Defines what success looks like. Drafted the MVP scope of rule-based movement pathway prediction with map zone navigation, the 5-phase feature roadmap, and the 7 key architectural decisions. Argues that "intent" should be decomposed into trajectory → action → strategy tiers, and that the MVP must be visible, interactive, and falsifiable.

### Elara Chen — Researcher
Investigated the CS2 analytics competitive landscape, ML prior art, data availability, and UI/UX patterns. Surfaced David Durst's MLMove as the most directly applicable prior art (Stanford 2024), confirmed that demoparser2 provides 170+ fields per tick including button states and view angles, identified the competitive gap (no tool combines intent prediction + spatial viz + LLM narratives), and mapped the public dataset ecosystem (OpenCS2, CS2-10k, EgoCS-400K).

### Viktor Kade — Critic
Challenged the core assumptions: "player intent" is critically underspecified (5+ possible interpretations), an LLM is likely the wrong tool for structured game-state prediction, no ground-truth intent labels exist in demo data, and the current architecture has foundation gaps (no database, dual parser paths, polling architecture) that must be addressed before AI features. Rated the LLM-for-prediction approach as BLOCKER-level ambiguity.

## Key Tensions Resolved

1. **LLM role:** Rejected LLM as prediction engine; adopted LLM as narrative/explanation layer in Phase 5. The prediction model is a small Transformer encoder trained on the user's own demos.
2. **"Intent" definition:** Decomposed into three tiers: Tier 1 (movement destination, MVP), Tier 2 (action classification, v2), Tier 3 (strategic role, v3).
3. **Build vs. buy foundation:** Analytics foundation (Phase 1) must precede AI features (Phases 3-5), but the rule-based intent MVP (Phase 2) can ship early to establish the API contract.
4. **Self-trained meaning:** The trajectory prediction model is trained from scratch on the user's own demo collection — not a pre-trained model from external data. This is genuinely "self-trained" and achievable on a single machine.

## Direction Contract

See [direction_v1.md](../../contracts/direction_v1.md) for the ratified direction contract.
