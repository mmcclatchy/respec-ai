# Phase 6 — Shape-aware review weighting

**Depends on:** Phases 1 and 4. **Blocks:** nothing; phase 7's score is decorative without it.
**Risk:** moderate-high. This changes composite scores for every project, and a mistake degrades loop
convergence in ways that are hard to attribute.

## Start here

**Prerequisites:** Phase 1 complete (the extension map classifies paths by domain) and Phase 4 complete
(UX Contract presence is a domain signal). Verify: `grep -rn "LanguageMaterializer" src/utils/` and
`grep -n "UX Contract" src/platform/templates/agents/phase_architect.py` both return output.

**Already done?** `grep -n "specialist_groups\|domain_share" src/mcp/tools/feedback_tools_unified.py` —
output means complete.

**Read first:** [README.md](README.md) (*"Score is not the lever; blockers are"*, and cross-cutting risk
#2), `docs/phase-refactor/testing.md`, `CLAUDE.md`, and [findings.md](findings.md) **F11**, **F12**. In
[decisions.md](decisions.md) read *"Domain weights scale with phase shape"* — it was a reversal, and the
original position (fixed pool, blockers only) is one you may find yourself re-deriving.

**First action:** write B1 — a backend-only phase scores *numerically identically* to before — and keep
it green through every subsequent change. It is the regression-safety property for the whole phase, and
cross-cutting risk #2 in the README.

**The load-bearing subtlety, and the thing most likely to be got wrong:** domain shares must come from
the **Phase design**, not from per-iteration changed files. `_detect_stagnation`
(`src/utils/loop_state.py:146-157`) compares score deltas across iterations. If weights shift because
the changed-file mix shifted, a score drop is indistinguishable from a weighting artifact, and
stagnation detection silently stops working. Design-derived shares are stable for the whole loop while
still reflecting composition. B4 pins this and it is not optional.

**One judgment call:** the exact floor, ceiling, and curve. Guidance below, but the numbers are a
starting point rather than a derivation — validate them against real phases before settling.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Make the domain weight pool responsive to what the phase is actually about, so that a phase whose
entire point is the UI does not score the UI at 7.5/100.

## The problem

`_phase1_core_weights` (`feedback_tools_unified.py:39-43`) holds 85 and
`_phase1_domain_weight_pool` (`:44`) is a fixed 15.0, split evenly among active specialists (`:45-50`,
division at `:653-660`).

Weights renormalize correctly when a reviewer is absent — `_compute_weighted_score:685` divides by
`active_weight_total` — so a backend project loses nothing by having no frontend reviewer (**F11**).
That part works.

The defect is the inverse. On a frontend-dominant phase the frontend reviewer still gets ~7.5/100. The
thing the phase is about carries almost no weight, and `_detect_stagnation` will never see its opinions
move the composite. Combined with **F12** — blockers bypass the score entirely — the practical effect is
that a domain reviewer's *score* is decorative and only its *blockers* function.

Phase 7 is built to drive the loop through blockers regardless. This phase makes the score meaningful
as well, so that "the composite says 82" tells you something true about a frontend phase.

## Design

### Shares come from the Phase design

Derive domain shares from the Phase document: `### Skeleton Index` and `### Module Layout` paths
classified by domain via phase 1's extension map, plus the presence of a UX Contract as a frontend
signal.

Computed deterministically MCP-side from `loop_id` — `consolidate_review_cycle` already has it and can
retrieve the Phase. **No new parameter, no migration**, and the orchestrator (which is prose, and
therefore non-deterministic) stays out of it.

A phase amendment that changes the design legitimately changes the weights. That is a re-scoping, not
drift.

### Bounds

- **Floor: 15.** A backend-only phase produces numerically identical scores to today. Assert by test
  (B1); do not assume it.
- **Ceiling: ~35.** Core reviewers always keep the majority. AQC, spec-alignment, and code-quality apply
  to frontend code too — a frontend phase must not stop caring whether the tests pass or whether the
  implementation matches the spec.
- **Core scales down proportionally**, preserving core reviewers' ratios to each other. After phase 0
  those are AQC 25 / spec-alignment 30 / code-quality 20 / design-conformance 20; the relationship
  between them should be unchanged by rescaling.
- **Total stays 100.**

### Specialist grouping

Replace the flat `_phase1_specialists` set (`:45-50`) with domain-keyed groups, so that when phase 7
adds a reviewer to the frontend domain it splits the *frontend domain's* share rather than re-dividing
the whole pool among one more member. Backend, database, and infrastructure weights then stay identical
to today regardless of what happens on the frontend side.

This is the mechanism that keeps phase 7 from silently diluting existing projects.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A backend-only phase produces a composite **numerically identical** to the pre-change model |
| B2 | A frontend-dominant phase raises the domain pool and lowers core proportionally |
| B3 | Core reviewers retain the majority at every point in the range, including the ceiling |
| B4 | Weights are **identical across iterations of the same loop**, even when the changed-file mix differs |
| B5 | A phase with no Skeleton Index renormalizes `design-conformance-reviewer` away cleanly |
| B6 | Adding a second frontend-domain reviewer does not change backend/database/infrastructure weights |
| B7 | A mixed phase lands between the bounds, monotonically in the frontend share |

**B4 is the one that protects stagnation detection** and the one a naive implementation fails. **B1**
is the regression guard. **B6** is what phase 7 depends on.

## Scope

**`src/mcp/tools/feedback_tools_unified.py`**
- `_phase1_domain_weight_pool` (`:44`) becomes a computed range rather than a constant.
- `_phase1_specialists` (`:45-50`) becomes domain-keyed groups.
- `_phase1_weights_for_results` (`:649-666`) takes the domain shares into account; the per-specialist
  division at `:653-660` splits within a domain rather than across the whole pool.
- A new deterministic helper that reads the Phase from `loop_id` and returns domain shares. Keep it
  pure and separately testable — it is the part with real logic.

**Domain classification** reuses phase 1's extension map. Do not add a second classification path; that
is the drift hazard that produced **F1** and **F14**.

## Out of scope

- **Changing what blockers do.** They remain the hard gate (**F12**). This phase makes the score
  meaningful; it does not make it sufficient.
- **Per-phase configurable weights.** Rejected in [decisions.md](decisions.md) — a wrong setting would
  silently skew every review with no signal.
- **Core weight values.** Set in phase 0. This phase rescales them proportionally; it does not
  relitigate their ratios.
- **Adding any reviewer.** Phase 7.

## Exit criteria

- B1–B7 green, with **B1 and B4 given particular scrutiny**.
- Run a real loop on a frontend-dominant phase and confirm the composite is a believable statement about
  frontend quality — that a bad UI scores visibly worse than a good one, which is the whole point and
  which no unit test asserts.
- Run a real loop on a backend phase and confirm scores are unchanged from before the phase landed. If
  they moved, you can say by how much and why.
- Confirm `decide_loop_next_action` still behaves sensibly near the threshold on both phase shapes —
  weight changes move scores, and a threshold tuned against the old model may need revisiting.
- `uv run pytest` clean.
