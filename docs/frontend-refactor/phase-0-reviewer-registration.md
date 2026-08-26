# Phase 0 — Reviewer registration repair

**Depends on:** nothing. **Blocks:** every other phase.
**Risk:** low mechanically, but it changes composite scores for every existing project.

## Start here

**Prerequisites:** none. This is the first phase.

**Already done?** `grep -n "DESIGN_CONFORMANCE_REVIEWER" src/models/enums.py` — output means complete.

**Read first:** [README.md](README.md), `docs/phase-refactor/testing.md`, `CLAUDE.md`, and
[findings.md](findings.md) **F1** (the bug) and **F11** (how weights work). The
[decisions.md](decisions.md) entry *"`design-conformance-reviewer` is core-tier and domain-neutral"*
explains the weight choice.

**First action:** write B1 — the roster cross-check test — and watch it fail. It is the test whose
absence let this bug ship, and it is what protects every reviewer added in phases 6 and 7 from the
same fate. Writing it first also tells you immediately whether anything *else* is unregistered.

**This is a live bug, not a refactor.** `/respec-code` is currently broken on any phase with a
non-empty Skeleton Index — which is all of them since the v2 refactor's phase 4. Treat it as a
regression fix that happens to be phase 0 of a larger effort, and consider landing it as its own
commit ahead of the rest.

**One thing here needs your judgment:** the weight rebalance changes scores for projects running
today. The recommended split is below, but confirm it against how your loops actually behave before
committing — if your threshold sits near a boundary, a 5-point core shift is not cosmetic.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Make `design-conformance-reviewer` a registered, weighted, scoreable reviewer, and make it impossible
for a future reviewer to be rostered without being registered.

## The bug

`resolve_active_reviewers` (`src/platform/reviewer_mapping.py:33`) appends
`'design-conformance-reviewer'` whenever the phase has a Skeleton Index. The same append is duplicated
in prose at `code_command.py:329` and `patch_command.py:397`, and `template_helpers.py:1031` has the
agent store with `max_score='50'`.

`CriticAgent` (`src/models/enums.py:70-83`) has no such member. `store_reviewer_result` calls
`_parse_reviewer_name` at `feedback_tools_unified.py:275` — *before* any other validation — which
raises `ToolError('Unknown reviewer_name: design-conformance-reviewer')` at `:730-735`. The reviewer
cannot store; `consolidate_review_cycle` then hard-fails at `:336-339` on the missing submission.

Introduced in `22cfd24`. See **F1**.

**Note a second-order trap while you are in this code.** The max-score check at `:276-280` is
`if expected_max_score is not None` — a lookup miss silently skips validation. So adding the enum
member *without* adding the `_reviewer_max_scores` entry produces a reviewer that stores successfully
with any `max_score` and then fails at weight resolution instead. Both entries are required; B2 pins
this.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | Every reviewer name `resolve_active_reviewers()` can return, under every mode combination, parses to a `CriticAgent` |
| B2 | Every such reviewer has a `_reviewer_max_scores` entry, and it equals the `max_score` its agent template is generated with |
| B3 | Every such reviewer resolves to a weight in `_phase1_weights_for_results` without raising |
| B4 | `design-conformance-reviewer` appears in the consolidated reviewer detail table |
| B5 | A phase with no Skeleton Index does not roster it, and the remaining reviewers' weights renormalize to 100 |
| B6 | A backend phase with a Skeleton Index consolidates end-to-end without `ToolError` |

B1–B3 are the durable ones. Write them as a single parameterized sweep over
`resolve_active_reviewers()` output rather than as assertions about `design-conformance-reviewer`
specifically — the point is that the *class* of bug becomes impossible, not that this instance is
fixed. B2 must read the `max_score` from the generated template rather than hardcoding `50`, or it
will not catch the next divergence.

## Scope

**`src/models/enums.py`**
- Add `DESIGN_CONFORMANCE_REVIEWER = 'design-conformance-reviewer'` to `CriticAgent` (`:70-83`).
- Add a `'DESIGN-CONFORMANCE'` alias to the `from_header` alias dict (`:93-107`), matching the
  existing shorthand convention (`'FRONTEND'`, `'SPEC-ALIGNMENT'`, …).

**`src/mcp/tools/feedback_tools_unified.py`**
- `_reviewer_max_scores` (`:29-38`) — add the reviewer at **50**. This must equal the hardcoded
  `max_score='50'` at `template_helpers.py:1031` or every store is rejected at `:276-280`.
- `_phase1_review_universe` (`:51-59`) — add it, or it is absent from the consolidated detail table
  at `:392-400` even when it scored.
- `_phase1_core_weights` (`:39-43`) — add it at **20**, and rebalance:

| Reviewer | Before | After |
|---|---|---|
| `automated-quality-checker` | 25 | 25 |
| `spec-alignment-reviewer` | 35 | 30 |
| `code-quality-reviewer` | 25 | 20 |
| `design-conformance-reviewer` | — | 20 |
| **core total** | **85** | **85** |
| domain pool | 15 | 15 |

**Why core rather than pooled.** Its `max_score` is 50; only AQC and spec-alignment are 50, and every
domain specialist is 25. Pooling a 50-point reviewer would make it worth roughly 5 points of composite
— clearly not the intent encoded in its max score. It scores conformance to the approved Skeleton
Index, which is closest in kind to spec-alignment.

**Why it stays domain-neutral.** It checks conformance to the approved design contract, which
pure-backend phases have as much as frontend ones. It remains gated on `has_skeleton_index`, **not** on
frontend presence. When a phase has no Skeleton Index it is simply not rostered and its weight
renormalizes away (**F11**). Its 20 points participate in phase 6's rebalancing like any other core
weight.

**`src/platform/templates/agents/review_consolidator*`**
- Add the reviewer's section to the merge format, alongside the other reviewers.

**`tests/unit/platform_tests/test_reviewer_mapping.py`**
- Add B1–B3 as the cross-check sweep. The existing assertions at `:95-100` check only string presence;
  leave them, but they are not sufficient.
- `tests/unit/templates/test_template_generator.py` and `test_feedback_enums.py` carry agent/enum
  counts that will need updating.

## Out of scope

- **Any weighting that varies by phase shape.** That is phase 6. Here the pool stays a fixed 15 and
  core stays a fixed 85.
- **Deduplicating the three roster copies** (`reviewer_mapping.py`, `code_command.py`,
  `patch_command.py`). Their drift is what let this bug ship, and consolidating them is tempting — but
  two of the three are *prose inside generated prompts*, not code, so this is a larger change than it
  looks. B1–B3 make the drift detectable, which is what matters now. Phase 7 touches all three again;
  reconsider then.
- **Any frontend work.** Nothing in this phase is frontend-specific.

## Exit criteria

- B1–B6 green.
- `respec-ai regenerate` completes for all three TUIs.
- **A full `/respec-code` run on a real phase with a non-empty Skeleton Index reaches consolidation
  without `Unknown reviewer_name`.** This is the gate for the entire refactor — do not start phase 1
  until it passes. A unit test alone is not sufficient evidence here; the bug lived in the seam between
  a prompt-level roster and a code-level enum, and only an end-to-end run exercises that seam.
- Composite scores for a backend phase are stable and explainable. If they moved, you can say by how
  much and why.
- `uv run pytest` clean.
