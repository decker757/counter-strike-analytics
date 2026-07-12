# External Feedback

## Purpose

The Bureau operates with autonomy but is not a closed system. External feedback — from the human, a stakeholder, or any source outside the Bureau — is a legitimate and expected input. This document defines how that feedback enters the Bureau and how it is accounted for.

External feedback is never blocking. The Bureau does not halt to wait for it. But once received, it must be formally considered — feedback is never silently absorbed or silently ignored.

## Intake

External feedback can arrive at any time, during any phase. When it does:

1. The feedback is recorded to `.bureau/feedback/` with the date received and its source
2. The feedback is routed to the **partners**, who own the decision on how it is accounted for
3. Operational teams continue their current work — intake does not interrupt in-flight delivery

## Partner Deliberation

Partners hold a meeting to decide how the feedback is accounted for. This may be a scheduled meeting or an urgent session if the feedback warrants it (see [Partners](./partners.md)). The meeting reaches one of the following outcomes:

| Outcome | When it applies |
|---------|-----------------|
| **Carry on** | The subsequent phases, as already planned, already address the feedback. No structural change is needed. The decision and its reasoning are recorded. |
| **Replan** | The feedback reveals that the current phase plan is insufficient or misdirected. Partners revise the phase plan — this may reshape milestones, scope, or the ordering of work. New work produced enters the [Backlog](./backlog.md). |
| **Escalate to founding** | The feedback challenges the intent itself — the *what* or the *why*. This is direction-level and belongs to the founding team, who revise the direction contract (see [Founding Team](./founding_team.md)). |
| **Stand up a consultant** | The feedback names a specific, bounded problem best solved by a temporary team. Partners commission a consultancy team (see below). |

Partner decisions require consensus. A split means no decision is made, and partners reconvene (see [Partners](./partners.md)). Every feedback item's disposition is recorded to `.bureau/feedback/` — including the decision to carry on unchanged, with the reasoning.

## Consultants

A **consultant** is a temporary addition to the Bureau, stood up to solve or audit one specific, bounded task. A consultant is not a core employee and not an intern:

- **Core** — permanent, established role
- **Intern** — temporary, brought on to test an idea
- **Consultant** — temporary, brought on to solve or rigorously audit a specific task

A consultant (or a consultancy team) exists only for the duration of its task. Once it has achieved what it was commissioned to do, it delivers its findings and **leaves** — its tenure ends and it is recorded with a last day like any other employee (see [Teams](./teams.md) records).

Consultants may be commissioned:
- By partners in response to external feedback
- At the end of a phase as a standing recommendation (below)

### Naming

A consultancy team receives **two** names at commissioning, both recorded like any team ([Teams](./teams.md)):

- A **descriptive scope title** — what it audits, e.g. "Adversarial Security Audit" or "Test-Coverage Assessment"
- A **firm-style alias** — a consulting-firm-flavoured name for identity and readability of records, e.g. *Mandragora*, *Bain Cycles*, *PricewaterhouseCoverage*, *The Untainted Group*

The alias is flavour, not function — the scope title is authoritative. Both are recorded so findings can be attributed to a named firm and cross-checked later.

## End-of-Phase Consultancy Audit

It is **recommended that at the end of every phase the Bureau stands up multiple consultancy teams to rigorously check every aspect of the project** before the phase is considered closed.

- Each consultancy team is scoped to a distinct aspect — correctness, security, performance, coverage, documentation, alignment with the direction contract, or any dimension the phase demands
- Consultancy teams operate with the distance of a Critic: they are not invested in the work they audit
- Their findings feed back into the Bureau as feedback items, deliberated by partners like any other external feedback
- Once the audit is complete and its findings are dispositioned, the consultancy teams leave

This closes each phase with a rigorous, independent check rather than the Bureau grading its own work in isolation.

## Findings Are Recorded and Formally Answered

Auditor independence is only real if findings cannot be quietly shelved. Therefore:

- **Every** finding from a consultant or consultancy team is recorded to `.bureau/feedback/` — no finding is dropped, softened, or absorbed silently
- **Every** recorded finding receives a **formal answer** on the record: accepted, rejected (with reasoning), or deferred (with reasoning and a target). Partners cannot make a finding disappear by declining to act — declining is itself an answer that must be written down and justified
- A finding and its answer are linked so any later reader — or a future auditor — can trace what was raised, what was decided, and why
- Any finding whose answer requires work that cannot be closed immediately — accepted-and-to-be-done, or deferred-with-a-target — enters the [Backlog](./backlog.md) so the obligation is tracked until a commit resolves it

This applies to consultants specifically, but the underlying rule is general (below).

## Citation and Recording for Information-Gathering Roles

Any employee whose role is **gathering information from external sources** — Researchers, consultants performing an audit, or any role reaching outward — is bound by the same discipline:

- **All findings must be recorded and formally answered.** The recording-and-answer rule above is not unique to consultants; it governs every outward-facing role.
- **Citation is mandatory — and must be validated, not merely present.** Every claim drawn from an external source must carry a **claim-level, inline** citation precise enough to locate. But a citation's *presence* does not establish grounding: models readily produce plausible, correctly-formatted citations that do not support the claim (correctness ≠ faithfulness). Therefore a load-bearing external claim is admissible only once a **second agent, in fresh context, has opened the source and confirmed (by quote/substring match) that it actually supports the claim.** Unvalidated external claims are marked provisional and may not be load-bearing. See [Operating Principles](./operating_principles.md) §4.
- Citation exists so auditors and employees can **cross-check** each other. This mutual verifiability — a second agent actually reading the source — is a core defence against hallucination, precisely because the checker draws on something the author cannot fabricate.

## The Error Register

A self-critical system that does not remember its own mistakes re-derives them every cycle. The Bureau keeps an **error register** at `.bureau/errors/`: whenever a belief is overturned — by a test, an audit, external feedback, or a later reversal — it records *"we believed X; it was wrong because Y; the tell was Z."* The self-evaluation cron (see [Lifecycle](./lifecycle.md)) consults it, so past failure modes are checked against new work rather than repeated.

## Governance Audit

Beyond per-aspect end-of-phase audits, a periodic **governance audit** examines the bureau's own machinery — including partner conduct, mission-alignment, and whether the findings ledger is complete (no finding silently unlogged or unanswered). It reports to the **human**, not to partners, giving the audit function real independence as a check on the structural stewards themselves (see [Partners](./partners.md)).

## Consultant Engagement — Default and Exception

Consultants are subject to the Bureau's core principle that isolation is a failure mode (see [Communication Protocol](./communication.md)), but with a deliberate exception.

### Default — engaged, not siloed

By default a consultant does **not** operate in a silo. Their hunches and findings are bounced off the Bureau's employees before being finalised:

- A consultant must not make **assumptions** about the project. When their work depends on how the project actually behaves, they verify it with the employees who know — they do not guess
- Employees consulted in this way are **not required to make changes**. Their role here is purely to inform and to confirm or correct the consultant's understanding — not to act on the finding
- This keeps consultants factually grounded without turning them into another source of change

### Exception — sanctioned silo

There are scenarios where a consultant benefits from operating **in a silo** — deliberately isolated from employees so that employee hunches cannot influence the consultant and propagate a hallucination into the audit. The clearest case is an independence audit: the whole value is an untainted outside view.

- A silo is **sanctioned by partners** when they commission the consultant — it is a deliberate choice, recorded, not a default
- A siloed consultant still must not invent facts; where it cannot consult employees, it relies on citable external sources and the recorded artefacts of the project, and it flags any assumption it was forced to make so it can be checked afterward
- The trade-off is explicit: engagement guards against the consultant's own ignorance of the project; silo guards against the employees' errors contaminating the consultant. Partners choose which risk matters more for a given audit

## Relationship to Continuous Improvement

In Phase 2, the daily cron is the Bureau's *internal* mechanism for pushing itself forward (see [Lifecycle](./lifecycle.md)). External feedback is the *outward* counterpart — it is how the world reaches in. Both are legitimate inputs; the cron never supersedes external feedback, and external feedback never blocks the cron.
