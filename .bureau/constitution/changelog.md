# Constitution Changelog

The constitution carries its own version, separate from product releases. Every amendment is recorded here with its reasoning, so no future cycle relitigates an undocumented decision (see [Foundation](./foundation.md) §5).

---

## v2.0.0 — 2026-07-10 — The Self-Correcting Rework

**Origin.** A meta-effort in which the Bureau used its own founding process to scrutinise and improve its constitution. Three founding panels (The Charter Assembly, The Extended Bench, The Keystone Panel) and an 8-researcher LLM-Behaviour Study Group produced four direction contracts (`.bureau/contracts/direction_v1..v4.md`) and three findings ledgers (`.bureau/feedback/2026-07-10-*`). Ratified by the human.

**Why a MAJOR bump.** The order of authority and the addition of a Floor above the mission are a significant scope shift in how the Bureau is governed.

### Added
- **`foundation.md`** — new top-of-constitution document. Establishes the order of authority `Human > Floor > Mission > Plan`; the thin, harness-enforced Floor; the mission as a canonical versioned artefact with a surviving guardian; the supremacy clause; and the self-amendment protocol with entrenched clauses. *Reason: the prior constitution could revise its direction contract and its product, but had no rule for amending itself, no limit above the mission, and orphaned mission-authority on founding dissolution — the single largest structural gap.*
- **`operating_principles.md`** — new document capturing 20 evidence-backed adoptions (A-1…A-20) from the LLM-behaviour research. *Reason: the constitution governed the organisation but never the substrate — how agents are actually prompted, verified, and judged on a single-model monoculture.*

### Changed
- **`overview.md`** — mission restated as the *task outcome* (not "orchestrate team structure"); "consensus strengthens output" replaced with "consensus is coverage, not correctness"; flatness scoped honestly to *operations* (partners named as a governance layer). *Reason: the old mission was org-centric, contradicting mission-first; consensus among correlated agents amplifies error (L-01); the flat/partner contradiction was unacknowledged.*
- **`communication.md`** — "mandatory/maximal" communication scoped to "purposeful, at scope boundaries" (resolves the mandatory-vs-recommended contradiction); consensus explicitly subordinated to model-independent checks; dissent preserved. *Reason: unbounded communication is O(n²) cost; agreement ≠ verification.*
- **`employees.md`** — Critic redefined around *independence via external grounding* (fresh context, adversarial brief, review against tests not rationale) rather than mere "distance"; added the note that role/persona labels do not improve accuracy (kept for scope/identity only). *Reason: a same-model Critic shares the author's blind spots and defers to it (self-preference + sycophancy).*
- **`teams.md`** — resolved the min-size contradiction (solo teams permitted only with recorded justification); grounded the max-9 ceiling in coordination cost; added an intra-team convergence point; added a falsifiable dissolution trigger + due-process record + symmetric protection for successful-but-quiet teams; "each added member must earn its cost." *Reason: fix the clause contradiction; make disposal non-arbitrary; more agents ≠ more accuracy.*
- **`partners.md`** — added a bounded deadlock ceiling (new proposals default to status quo; corrective matters escalate consultant → guardian → human); added the interpretation/precedent (adjudication) function; added an external check on partners (governance audit + human). *Reason: unbounded "no decision" could freeze the Bureau; there was no interpreter for the constitution's own text and no check on partners but partners.*
- **`lifecycle.md`** — cron converted to a closed loop (health-vector setpoint, measure-before-act, "in-band no action" as a valid positively-scored outcome, damping, watchdog, exploration operator); deterministic gate made mandatory; end-of-phase audit made mandatory; added cron resilience (catch-up-on-wake + frequent-cheap cadence) and observability (append-only run log at `.bureau/runs/`). *Reason: the cron was open-loop and rewarded activity (Goodhart/churn); the only model-independent sensor was optional; the human asked for missed-cycle resilience and visibility.*
- **`feedback.md`** — citation upgraded from present-and-locatable to **validated** (a second agent opens the source and quote-matches); added the error register (`.bureau/errors/`) and the governance audit. *Reason: a citation's presence does not establish grounding; a self-critical system must remember its own errors.*
- **`backlog.md`** — added single owning team + claim lock + aging backstop. *Reason: pull-by-scope with overlapping scopes drops or duplicates work.*
- **`founding_team.md`** — mission-guardian authority must survive dissolution; falsifiable success criteria mandatory before work; contract placed below constitution/mission in the supremacy order. *Reason: "escalate to founding" could point at a dissolved body; "make it better" is unfalsifiable.*

### Rejected (recorded so they are not relitigated)
- Persona-as-accuracy-booster; naive majority vote as correctness; multi-agent debate as an intrinsic truth-finder; "add random noise to context"; fine-tuning-based fixes. See `.bureau/feedback/2026-07-10-llm-behaviour-findings.md` §7.
- Cutting the employee-naming / first-and-last-day grammar: **kept** by explicit human decision (character/scope value), despite its context cost.

### Open points carried forward
- "Obey the law" placed as near-hard policy *just below* the Floor (not above the mission); the human may elect to promote it into the Floor.
- The health-vector components, the non-code deterministic oracle spec, and the deadlock hearing-count are left for the operational build to define and pre-register.

---

## v1.0.0 — prior — The original constitution
The founding framework: overview, employees, teams, communication, founding team, partners, lifecycle, external feedback, backlog. Eloquent and internally consistent, but with the structural gaps addressed above.
