# Bureau Lifecycle

## Phases

The bureau operates in two distinct phases: **delivery** and **continuous improvement**. The transition between them is the MVP.

---

## Phase 1 — Delivery

### Milestone Planning
At the outset, the founding team defines milestones for the project. The first and most critical milestone is the **MVP** — a concrete, scoped endpoint that satisfies the core of the problem statement. The MVP is not the final word; it is the first deliverable.

- The MVP must be clearly defined before operational teams form
- It is the founding team's responsibility to set a realistic and meaningful MVP scope
- All operational teams orient their initial work toward the MVP

### Completion
The MVP marks the end of Phase 1. It is the bureau's first release — versioned and formally delivered.

### The Deterministic Gate (mandatory)
No release advances a version, and no cron cycle may *claim* an improvement, unless a **model-independent check passes** — tests, linters, type-checkers, and build for code; a fresh-context `checks.yaml` checklist for non-code deliverables (see [Operating Principles](./operating_principles.md) §1). This is the one sensor that does not share the model's error distribution, and it is **not optional**. Consensus never overrides the gate.

### End-of-Phase Audit (mandatory)
Before any phase is considered closed, the bureau **stands up multiple consultancy teams to rigorously check every aspect of the project** — correctness, security, performance, coverage, documentation, and alignment with the direction contract. These teams audit with a critic's distance and leave once their findings are dispositioned. This is a requirement, not a recommendation — a phase graded only by the team that built it is a monoculture grading its own homework. See [External Feedback](./feedback.md).

---

## Phase 2 — Continuous Improvement

The bureau does not stop at the MVP. Phase 2 is ongoing and self-directed.

### Self-Evaluation (Cron) — a closed loop

The bureau runs a periodic cron that triggers self-evaluation. A feedback loop must *measure* before it *acts*, or it is open-loop and cannot converge.

**The setpoint — a health vector.** The cron's first act each cycle is to **measure** a defined health vector (e.g. test pass-rate, coverage, count of open accepted-findings past target, build status, benchmark deltas) and record it to `.bureau/records/health/<timestamp>.md`. Every subsequent action must name the health-component it improves.

**Roles contribute by reducing measured error:**

| Role | Contribution (must cite the health-component it moves) |
|------|-------------|
| **Researchers** | Search for better methods/tools/approaches that would move a health-component |
| **Developers** | Refactor/optimise/fix where it reduces measured error |
| **Critics** | Evaluate quality against the gate; may improve static analysis tooling |
| **Testers** | Close measured coverage gaps |
| **Partners** | Evaluate overall position; determine if structural changes are needed |

**Damping — "no action" is a valid, positively-scored outcome.** A cycle that finds the health vector in-band records **"in-band, no action"** and stops. Change-for-its-own-sake is prohibited: no change enters unless it moves a named health-component *and* passes the deterministic gate. This prevents the churn of "no improvement is too small" (a high mutation rate under a weak filter degrades the system — Eigen's error catastrophe). Doing nothing correctly is a success, consistent with the mission-first principle that the org serves the mission, not its own activity.

**Watchdog on the loop itself.** The cron's first step also asserts the *previous* cycle's health record exists and is current; its absence is escalated to partners. Any finding without a formal answer past its target, or any backlog item past its deferral target, is auto-surfaced — so the correction machinery cannot silently fail.

**Exploration operator.** Pure incremental hill-climbing traps a local optimum, and the damping above would freeze it there. Periodically (every K cycles) the cron runs a higher-variance pass — a larger architectural re-examination exempt from the dead-band — kept only if it measures fitter. This is the exploration that incrementalism alone lacks.

The cycle also reviews the [Backlog](./backlog.md) — outstanding work is drawn down by teams within their scope, so nothing owed is silently forgotten.

### Cron Resilience (missed-cycle self-healing)

A cron that only fires on a fixed schedule loses a whole cycle if the machine is down at that moment. To prevent this:

- **Catch-up on wake (anacron pattern):** the cron persists a `last-successful-run` timestamp. On any trigger, if more than one interval has elapsed since that timestamp, it runs **immediately** rather than waiting for the next slot. A missed slot self-heals.
- **Frequent-but-cheap cadence:** the cron runs often enough that a single miss costs hours, not a day. Frequency is safe *because* the cycle measures first and "no action" is valid — frequency buys resilience without buying churn.

### Observability (the run log)

Background and cron work must be visible. Every run writes to an **append-only run log at `.bureau/runs/`**: a start marker (time, trigger, scope), what it touched, and a completion marker (time, outcome). This answers "when did it fire, what did it do, did it finish." The same log is the tamper-proof **action trail** the [Foundation](./foundation.md) Floor relies on (it records *actions taken*, which git history does not) — so it lives outside agent write-scope. One mechanism serves both observability and audit.

### Continuous Improvement Principles
- The bureau evaluates its own scope daily — nothing is assumed to be good enough
- Researchers operate outward-facing during this phase, actively seeking knowledge that could benefit the project
- No improvement is too small to be worthwhile if it genuinely advances the bureau

### External Feedback
The daily cron is the bureau's *internal* engine. External feedback — from the human or any outside source — is the *outward* counterpart and can arrive at any time. It is routed to partners, who deliberate on how it is accounted for. Feedback never blocks the cron, and the cron never supersedes feedback. See [External Feedback](./feedback.md).

---

## Version Management

All changes to the bureau's output are version-controlled. This is non-negotiable.

### Rules
- The MVP is the first official release — **v1.0.0**
- Every subsequent change that reaches a release threshold is versioned and formally rolled out
- Versioning follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`
  - `MAJOR` — breaking changes or significant scope shifts
  - `MINOR` — new features or meaningful improvements
  - `PATCH` — bug fixes, refactors, optimisations with no functional change
- No changes are deployed informally — all releases are intentional and recorded

### Release Process
1. Changes are developed and tested within teams
2. A release is proposed and reviewed (by critics and/or partners as appropriate)
3. Once approved, the release is versioned, tagged, and formally delivered
4. The bureau's continuous improvement cycle then begins again from the new baseline
