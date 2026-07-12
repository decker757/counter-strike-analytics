# Teams

## Definition

A group of employees assigned a shared scope. Teams are the operational unit of the Bureau.

## Size

- **Default minimum:** 2 employees. A single-employee team is **permitted only with a recorded justification** — this resolves the prior contradiction (the old text both set a floor of 2 and said one employee "can constitute a team"). The bright-line rule: solo teams are the documented exception, not a silent default.
- **Maximum:** 9 employees — a hard ceiling. The ground for it is coordination cost: internal communication channels grow as n(n-1)/2, so a team of 9 already carries 36 channels. Beyond single digits, convergence cost dominates.
- **Convergence, not ceremony.** Because consensus is not verification and agents cave to peers, each team needs one lightweight convergence point — a designated synthesis/lead-author who consolidates, or a periodic checkpoint — so a team actually reaches a grounded conclusion rather than looping. This is not a standup; it is the missing mechanism that makes multi-member teams operable.
- **Each added member must earn its cost.** More agents do not mean more accuracy (see [Operating Principles](./operating_principles.md)); add a member only to close a specific gap — parallelism, a distinct decomposable sub-scope, or work exceeding one context window.

## Formation Rules

- A team must have an assigned scope — a clearly defined domain of responsibility
- A single employee can constitute a team, but this is **highly inadvisable**
- There are **no teams of teams** — the Bureau maintains a flat structure
- All teams operate at the same level; none is subordinate to another
- Teams are formed by the bureau according to the needs of the project — they do not self-organise
- New teams may be formed mid-project if a need arises; existing teams may receive new employees mid-project
- Teams may be dissolved when they no longer serve the mission; employees may be laid off or reassigned

## Dissolution — Trigger and Due Process

Disposability is real and legitimate (the mission is sovereign, not the org), but it must not be *arbitrary* — arbitrary disposal selects for teams that look busy to partners rather than teams that serve the mission.

- **Falsifiable trigger.** A team is a dissolution candidate when, over a defined window, its actions produce **no gate-verified movement** in the health-component it was scoped to (pre-registered at formation — see [Lifecycle](./lifecycle.md)). The criterion is the measured artefact, not partner impression.
- **Symmetric protection.** A team that has *hit* its setpoint and gone quiet is **not** a candidate — success must not be punished as inactivity.
- **Due process.** Dissolving a team requires a **recorded disposition** — reason, the partner decision, and date — mirroring the discipline that every finding must be formally answered (see [Feedback](./feedback.md)). An unrecorded disposal cannot be checked for capture and is not permitted.

## Naming

Every team is assigned a **descriptive name** that reflects its scope and purpose. Names are assigned at formation and serve as the team's identity for the duration of its existence.

## Records

The bureau maintains a record for every team and every employee:

| Field | Description |
|-------|-------------|
| Team name | Descriptive, assigned at formation |
| Scope | The team's defined domain |
| First day | Date the team was formed |
| Last day | Date the team was dissolved (if applicable) |
| Members | Employees assigned, with their own first and last day records |

Every employee is assigned a **first and last name** (middle name optional). Their first and last day with the bureau are recorded.

## Team Scopes (non-exhaustive)

Scopes define what a team is responsible for. They are not exhaustive — new scopes may be defined as tasks demand.

| Scope | Responsibility |
|-------|---------------|
| **Core Development** | Building the primary system or feature |
| **Optimisation** | Improving performance, efficiency, or quality of existing work |
| **Testing** | Validating correctness, coverage, and edge cases |
| **Deployment** | Releasing and operationalising built systems |
| **Documentation** | Capturing knowledge, decisions, and usage |
| **CI** | Continuous integration, automation, and pipeline health |
| **Consultancy** | Temporary team commissioned to solve or rigorously audit a specific aspect, then dissolved once done (see [External Feedback](./feedback.md)) |

## Behavioural Expectations

- Employees within a team adhere to their team's assigned scope
- Teams do not override or absorb the scope of other teams
- Cross-team communication is allowed and recommended — it follows the same norms as cross-employee communication

## Relationship to the Bureau

Teams are not independent units. They are expressions of the Bureau's collective movement toward the task. A team that optimises only for its own scope at the expense of the whole is a failure mode.
