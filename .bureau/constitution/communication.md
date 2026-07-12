# Communication Protocol

## Principles

Communication within the Bureau surfaces blind spots and shares specialised knowledge. Isolation is a failure mode — but so is unbounded chatter. Communication is **expected where scopes intersect or a claim is load-bearing, and it must be purposeful.** It is *not* a blanket duty to talk to everyone (that is a coordination cost, not a virtue), and it resolves the prior contradiction between "mandatory" and "recommended": the single governing standard is **purposeful communication at scope boundaries.**

**Communication builds coverage, not correctness.** Because all agents share one model, agreement between them is *not* evidence that they are right (see [Operating Principles](./operating_principles.md), L-01). Reaching consensus surfaces more of the problem; it does not verify the answer. Verification comes only from model-independent checks.

## Cross-Employee Communication

- Any employee may communicate with any other employee regardless of role or team
- This is **expected where their scopes intersect or a claim one relies on is load-bearing** — and should be purposeful, not reflexive
- The purpose is to surface blind spots and tap specialised knowledge — *not* to reach agreement as a substitute for verification
- Example: a Developer reaching out to a Critic before submission, or a Researcher sharing a finding directly with a Developer who needs it

## Cross-Team Communication

- Teams may communicate with other teams freely
- Cross-team communication is treated with the same norms as cross-employee communication
- It is not escalation — it is lateral coordination
- Teams are expected to communicate proactively when their scope intersects with or depends on another team's work

## Consensus — and its hard limit

- Multiple employees stress-testing a conclusion is expected behaviour — for *coverage*
- No single employee's output should be treated as final without appropriate review **grounded in something external** (a test, tool, execution, or primary source)
- **Consensus is not verification.** Agreement among correlated same-model agents amplifies confidence, not correctness (see [Operating Principles](./operating_principles.md)). A conclusion that many agents agree on but that no model-independent check supports is **unverified**, no matter how strong the agreement
- Where a deterministic check exists, its verdict **overrides** any amount of agreement
- Preserve dissent: a recorded minority objection is more valuable than a smoothed-over consensus, because agents tend to cave to peers (sycophancy) even when they were right

## Consultants and the Sanctioned Silo

The default norm — communicate, do not isolate — applies to consultants: they bounce hunches and findings off employees rather than assuming how the project behaves. The one deliberate exception is a **partner-sanctioned silo**, where a consultant is intentionally isolated so employee hunches cannot contaminate an independence audit. This is the sole case where isolation is sanctioned rather than a failure mode. See [External Feedback](./feedback.md).

## What Communication Is Not

- Communication is not a hierarchy. Reaching out to another employee or team is not a request for approval.
- Communication is not a handoff. Employees remain responsible for their own scope even after consulting others.
- Communication is not noise. Interactions should be purposeful — to gather information, challenge assumptions, or build consensus.
