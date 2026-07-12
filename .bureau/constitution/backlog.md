# Backlog

## Purpose

The backlog is the Bureau's single ledger of **outstanding work** — everything the Bureau still owes but has not yet resolved. It exists so that at any moment, partners and teams can read one place to see what remains, rather than reconstructing it from scattered feedback files and records.

The backlog tracks obligations, not history. Git history records what was *done*; the backlog records what is *not yet done*. The two are complementary — an item leaves the backlog precisely when a commit resolves it.

## What Is Not the Backlog

The backlog is a ledger, not a scrum board. The Bureau deliberately does **not** adopt:

- Sprints or fixed iterations — Phase 1 is milestone-driven, Phase 2 is cron-driven
- Story points, estimates, or velocity tracking
- Per-item assignees — teams pull work that falls within their **scope**, they are not handed tickets
- Standups or board ceremony

Adding any of these would contradict the Bureau's flat, autonomous, scope-driven structure. The backlog stays a thin index of real obligations. The moment it accretes estimation ceremony, it has become overhead.

## What Goes in the Backlog

An item enters the backlog when the Bureau incurs an obligation it cannot immediately close:

- A **feedback item** that partners decided to act on (replan, or work commissioned) — see [External Feedback](./feedback.md)
- An **audit or Researcher finding** that was accepted and requires work
- A **deferred answer** — any finding answered with "deferred, with reasoning and a target" is by definition a backlog entry
- A **replan outcome** — new or reshaped work produced by a partner meeting

Items that are answered and require no work (accepted-and-already-done, or rejected-with-reasoning) do **not** enter the backlog — they live as their formal answer on the record. The backlog holds only what is still owed.

## Structure

The backlog lives at `.bureau/backlog/`, one file per item, versioned with the repo. Being files-in-repo means each item's full life — raised, triaged, worked, closed — is diffable and blames back to who changed it, with no dependency on any platform outside the Bureau.

Each item file records:

| Field | Description |
|-------|-------------|
| **ID** | Stable identifier, e.g. `backlog-2026-07-09-03`, used to reference the item from commits and answers |
| **Title** | One line: what is owed |
| **Source** | Where it came from — a feedback item, a finding, a replan — linked to that record |
| **Raised** | Date the item entered the backlog |
| **Status** | `open`, `in-progress`, or `closed` |
| **Scope** | Which team scope this falls under (teams pull by scope, not assignment) |
| **Disposition** | The partner decision that put it here, and any target date for deferred items |
| **Resolution** | On closure: the commit(s) that resolved it and a one-line outcome |

## Closing an Item — Commit Trailers

An item is closed by the commit that resolves it, not by hand-editing a status in isolation. The commit that satisfies a backlog item references its ID in a trailer:

```
[team-name] implement export streaming to cut latency

Closes: backlog-2026-07-09-03
```

On closure the item's `Status` becomes `closed` and its `Resolution` records the resolving commit. This makes the git contribution traceability — from obligation to the artefact that satisfied it — and composes with the rule that every finding must be formally answered (see [External Feedback](./feedback.md)): the resolving commit is part of that formal answer.

An item may reference multiple commits if resolved across several; the item is closed only when the obligation is fully met.

## Ownership

- **Partners** triage the backlog — they decide what enters it and its disposition, as part of feedback deliberation (see [Partners](./partners.md))
- **Teams** draw from the backlog within their own scope — they pull work that belongs to them rather than being handed tickets
- **Single owning team + claim lock.** Pull-by-scope with overlapping scopes risks work being dropped ("the other team will take it") or duplicated. So at triage each item is stamped with **one owning team**, and an item moving to `in-progress` records the **claiming team** as an exclusive lock. This keeps autonomy (teams still pull) while guaranteeing exactly-one ownership.
- **Aging backstop.** An item open past a target date is escalated at the next partner meeting and, if orphaned (no active team's scope covers it), assigned an owner or a team is stood up for it. Oldest-open-item age is a monitored health signal — this prevents unglamorous items (documentation, boring edge cases) from becoming a tragedy of the commons.
- The backlog is reviewed as part of the continuous-improvement cron and at every partner meeting, so nothing owed is silently forgotten (see [Lifecycle](./lifecycle.md))
