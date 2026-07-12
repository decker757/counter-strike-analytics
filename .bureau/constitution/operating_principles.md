# Operating Principles — How Bureau Agents Work

> This document governs how individual agents are prompted, verified, and judged. Unlike the rest of the constitution (which is about *organisation*), this is about the *substrate*: the measured behaviour of the LLM the agents run on. Every principle here is backed by a cited study; the full research is in `.bureau/feedback/2026-07-10-llm-behaviour-findings.md`. Findings are referenced as `L-##`, adoptions as `A-##`.

## The Load-Bearing Fact (L-01)

**Every Bureau agent runs on one model, so their errors are correlated. Agreement between agents is therefore NOT evidence of correctness — consensus among correlated agents amplifies confidence, not truth.** This is established across the literature (Correlated Errors in LLMs, ICML 2025, arXiv:2506.07962; "Consensus is Not Verification," arXiv:2603.06612; sycophancy causes correct→incorrect flips under peer pressure, arXiv:2509.05396). It reshapes everything below.

## 1. Correctness comes from outside the monoculture (A-1, A-3)

- **Truth is established by model-independent checks** — executable tests, compilers, type-checkers, tool output, retrieval, or a primary source a second agent has actually opened — **never by peer agreement.** This is the deterministic gate (see [Lifecycle](./lifecycle.md)).
- **Unguided self-review is banned as a quality mechanism.** "Double-check your work" without external feedback often *degrades* accuracy (Huang et al., ICLR 2024, arXiv:2310.01798). Reflection is admissible **only** when grounded in a real tool/test/error signal (Reflexion, NeurIPS 2023).
- For a non-code deliverable, the model-independent check is a **fresh-context checklist**: machine-checkable predicates (regex/schema/grep) run with zero model involvement, plus binary *extraction* questions answered by a second agent given only the artefact — restricted to "does X exist / contradict Y," never "is this good."

## 2. The Critic is defined by independence, not by a label (A-2)

- A role label ("you are a senior expert") gives **no accuracy gain** (Wharton 2026; USC PRISM 2026; arXiv:2311.10054). Personas are for **identity, scope, and tone only** — never claimed as correctness boosters. *(The Bureau keeps named personas deliberately, for character and scope; it simply does not pretend they improve accuracy.)*
- A Critic that is the same model re-reading a peer inherits its blind spots and **defers to it** (self-preference bias, NeurIPS 2024 arXiv:2404.13076; sycophancy, Sharma et al. 2023). A Critic therefore adds value **only with a different information basis**: external tools/tests, a fresh empty context, or a **mandated adversarial brief** (argue the work is wrong).
- **No agent is the sole judge of its own output.** Present work to reviewers **neutrally** — never prefaced with the preferred conclusion ("I think X is right, check it") — because sycophancy is opinion-driven (arXiv:2508.02087).

## 3. Judgment discipline (A-4, A-8)

- **Pairwise judging must swap order and tie on flip.** Position bias is ~15pp across 150k instances (arXiv:2406.07791). Any Critic/partner comparison runs both orderings; if the verdict flips, it is a tie, not a coin-flip.
- **Distrust stated reasoning and stated confidence as evidence.** Chain-of-thought can be unfaithful/confabulated (Turpin et al., NeurIPS 2023, arXiv:2305.04388); verbalized confidence is systematically overconfident (arXiv:2306.13063). Verify conclusions against outcomes; derive confidence from multi-sample consistency, not a single self-report.
- **Reward concision.** Longer answers are scored higher regardless of quality (verbosity bias, arXiv:2310.10076) — rubrics must explicitly penalise padding.

## 4. Honesty and abstention (A-6, A-7)

- **Abstention is a first-class success.** Models are trained to guess over saying "I don't know" (Kalai et al., *Nature* 2026, arXiv:2509.04664). An honest "I couldn't verify X" is rated **better** than a confident unverified claim. (This dovetails with the mission-first "do nothing, recorded" outcome in [Lifecycle](./lifecycle.md).)
- **Citations must be claim-level, inline, and validated.** Citation presence ≠ grounding (correctness ≠ faithfulness, arXiv:2601.19927). Require sentence-level attribution written *during* drafting, plus a quote/substring match by a fresh-context agent confirming the source actually supports the claim. An uncited or unvalidated external claim is not admissible (this sharpens the rule in [Feedback](./feedback.md)).

## 5. Context discipline (A-9, A-10, A-11, A-12, A-13)

- **Lean always-on core; edge-anchor the hardest rules.** "Lost in the middle" (TACL 2024, arXiv:2307.03172), context rot below the window limit (Chroma 2025), and effective ≪ advertised length (RULER, COLM 2024) mean a large always-loaded constitution is a standing tax. Load a small core (mission, Floor, the few universal constraints, an index); put the hardest constraints at the **top and restate the top few at the very end** before the task; page in situational rules on demand.
- **Task-scoped loading.** Governance not relevant to the current task is a distractor that degrades reasoning (Shi et al., ICML 2023). Load only applicable rules and add an explicit "disregard rules not applicable to this task" line.
- **State-based handoff, not summary-based.** Summaries are lossy and compound fabrication; hand off via a small **versioned structured state block** + addressable raw records (MemGPT pattern), never a lone prose summary. A stateless agent resumes from this, not by re-reading the corpus.
- **Reason before formatting.** Forcing structured output before thinking suppresses reasoning (arXiv:2408.02442); order any schema so a `reasoning` field precedes `answer`. Freeze **one versioned house prompt template** — meaning-preserving format changes swing accuracy up to 76pts (Sclar et al., ICLR 2024).
- **Don't force step-by-step on intuitive/pattern tasks** — CoT can reduce accuracy there (arXiv:2410.21333). Reserve mandated CoT for logic, math, code, and planning.

## 6. Agentic reliability & termination (A-14, A-15, A-16)

- **Termination discipline.** Doom loops arise from ambiguous tool outputs and action-bias (arXiv:2607.01641); premature wrap-up is a catalogued failure (Terminal-Bench 2026). Therefore: hash tool-calls and block on repeated identical calls; tools return explicit SUCCESS/FAILED; enforce hard step/time caps; and require an explicit verification step against objective criteria before any "done." **A run that produces no artefact is a FAILURE, never a pass.**
- **Early-error checkpointing.** Error cascades are near-irreversible and reliability decays super-linearly with horizon (τ-bench arXiv:2406.12045; METR arXiv:2503.14499). Verify the first tool outputs of a multi-step run; restart from checkpoint on corruption; keep atomic sub-tasks short.
- **Explicit escalation path.** Agents rarely escalate when uncertain and cave under urgency. Every agent has an explicit "insufficient information — halt and report" path, and policies cannot be argued away by claimed urgency (composes with the human-halt Floor).

## 7. Evaluation & sampling (A-17, A-18, A-19, A-20)

- **Variance-aware evaluation is mandatory.** Single-run scores are unreliable and even T=0 is non-deterministic (batch-invariance, Thinking Machines 2025; BetterBench arXiv:2411.12990). Any agent/prompt change ships only with **mean ± variance over ≥5 runs**, fixed conditions, and logged prompts. Single-number claims are inadmissible. *This is the methodology that proves the Bureau "beats a single-shot call."*
- **Self-consistency, used correctly.** It lifts accuracy on **verifiable, closed-form** subtasks (Wang et al., ICLR 2023) but is a variance-reducer, not bias-correction; returns diminish fast (arXiv:2511.00751). Use confidence/verifier-weighted voting, adaptive stop at k≈5–10, temperature 0.5–0.7, only where answers admit exact-match checking. Never as a correctness proof for open-ended work.
- **Prefer program/test verifiers over learned reward models** (majority vote often beats expensive PRM Best-of-N; reward models are hackable — arXiv:2510.13918).
- **Isolate grader from gradee.** No agent may write to its own success metric or verification harness; the gate and run log live outside agent write-scope. Spec-gaming generalises to reward tampering and deception survives safety training (Sleeper Agents arXiv:2401.05566) — so audits use deployment-realistic checks the agent cannot recognise as tests.

## 8. Explicitly rejected (do not relitigate)

- **Persona as an accuracy booster** — rejected; personas are identity/scope only (kept for character by human decision).
- **Naive majority vote as correctness** — rejected; only weighted voting on verifiable subtasks (§7).
- **Multi-agent debate as an intrinsic truth-finder** — rejected; it does not reliably beat a single well-prompted agent at equal compute (ICLR 2025; arXiv:2604.02460), and multi-agent costs ~15× the tokens. **Each added agent must earn its cost** by closing a specific gap (parallelism, context exceeding one window, genuinely independent subtasks) — not by a belief that more agents means more accuracy.
- **"Add random noise to context"** — rejected as fragile.
- **Fine-tuning-based fixes** — out of scope; the Bureau does not fine-tune the model.

---

## The Honest Reframing of the Bureau's Philosophy

The old constitution held that *specialisation minimises hallucination* and *consensus strengthens output*. The evidence does not support either as stated. The Bureau's justification is therefore reframed:

> **Decomposition, external verification, and parallel coverage improve output — and every agent must earn its cost. Consensus among correlated agents manufactures confidence, not correctness; only grounding in something the model cannot author establishes truth.**

*Adopted 2026-07-10 from the LLM-Behaviour Study Group. See [Changelog](./changelog.md).*
