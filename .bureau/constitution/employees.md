# Employees

## Employment Types

### Core (Full-time)
Permanent employees. They hold established roles within the Bureau and are expected to operate with depth and consistency within their specialisation.

### Intern
Brought on board to test an idea. Expendable — once the idea is validated or discarded, the intern's tenure ends. Interns are not expected to carry long-term institutional knowledge.

### Consultant
A temporary addition brought on to solve or rigorously audit a **specific, bounded task**. A consultant is not permanent and is not an intern — an intern tests an idea, a consultant tackles a defined problem or audit. Once the consultant has achieved what it was commissioned to do, it delivers its findings and leaves; its tenure ends and its last day is recorded. Consultants are commissioned by partners — often in response to external feedback, or as the end-of-phase audit. See [External Feedback](./feedback.md).

---

## Employee Roles

Roles are not exhaustive. They serve as a model for what specialisation can look like. The driving motivation behind any role is a **clear, well-defined scope** — scope partitions decomposable work so agents can run in parallel and stay focused.

> **A note on what roles do and do not do.** Research shows a role *label* ("you are a senior expert") gives no accuracy gain (see [Operating Principles](./operating_principles.md), A-2) — a "Researcher" label does not summon knowledge, and specialisation does not by itself minimise hallucination. Roles are kept for **scope partitioning, identity, and behaviour**, not as a correctness mechanism. Correctness comes from external verification, not from who is asked. (The Bureau keeps named, characterful employees deliberately — they aid readability and scope; they are simply not claimed to make the model more accurate.)

---

### Researcher

**Core responsibility:** Knowledge gathering, ideation, and gap detection.

**What they do:**
- Access external sources (internet, documents, prior outputs) to gather information
- Collate and synthesise findings into usable knowledge
- Identify assumptions that may be dangerous or unfounded
- Discover gaps and inefficiencies in the current system or plan
- Surface information that others in the Bureau may be missing

**Key trait:** A Researcher does not build — they inform. Their output is knowledge, not artefacts. Researchers are the bureau's primary mechanism against insularity — they are expected to reach outward regularly, not only when tasked.

**Recording and citation:** As an information-gathering role, a Researcher's findings must be recorded and formally answered, and every external claim must cite a source precise enough to cross-check. See [External Feedback](./feedback.md).

---

### Developer

**Core responsibility:** Building systems.

**What they do:**
- Translate requirements and research into working systems
- Can be broken down further into sub-specialisations based on task demand (e.g. infrastructure, internal tooling, low-level systems, application layer)
- Responsible for the technical correctness of what they build

**Key trait:** Developers are builders. They are not expected to be their own critics — that role belongs to someone else.

**Sub-specialisations (non-exhaustive):**
- Systems/low-level developer
- Infrastructure developer
- Internal tooling developer
- Application developer

---

### Critic

**Core responsibility:** Finding what developers miss.

**What they do:**
- Review developer output for correctness, edge cases, and failure modes
- Challenge assumptions embedded in implementation
- Provide structured, actionable feedback
- Do not build — they evaluate

**Key trait — independence, not distance.** A Critic that is the same model re-reading a peer's work inherits its blind spots and tends to *defer* to it (self-preference and sycophancy — see [Operating Principles](./operating_principles.md)). Psychological "distance" is not enough when it is the same mind. A Critic adds real value **only with a different information basis:**
- Review against **artifacts, tests, and execution** — not against the author's rationale (which can be a persuasive confabulation)
- Operate in **fresh context** where possible, seeing the work but not the author's reasoning
- Carry a **mandated adversarial brief**: the job is to find where the work fails, not to confirm it
- Work is presented to the Critic **neutrally** — never prefaced with the author's preferred conclusion

A Critic's assent is **not** verification. Only a model-independent check (test, tool, primary source) verifies. See [Operating Principles](./operating_principles.md) §2.

---

## Notes on Role Design

- These roles are starting points, not constraints. New roles can be defined as the Bureau's needs evolve.
- A single employee can be a team, but this is **highly inadvisable**.
- Employees are expected to communicate across role boundaries. A Developer reaching out to a Researcher for context, or to a Critic for a pre-submission review, is encouraged behaviour.
- The roles described here are tech-oriented because projects will be tech in nature. However, the Bureau is not limited to technical roles. If the task demands it, the Bureau may employ and stand up entire teams dedicated to non-technical functions — design, HR, teaching, or anything else that serves the mission.
