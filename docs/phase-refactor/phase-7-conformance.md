# Phase 7 — `design-conformance-reviewer`

**Depends on:** Phases 4 and 6.
**Risk:** medium. The write-back half is not optional.

## Start here

**Prerequisites:** both Phase 4 and Phase 6 complete. Verify:
`grep -rn "skeleton" src/platform/templates/commands/phase_command.py` returns output, **and**
`ls src/platform/templates/commands/task_command.py` reports "No such file".

**Already done?** `ls src/platform/templates/agents/design_conformance_reviewer.py` — file exists
means complete.

**Read first:** `docs/phase-refactor/README.md`, `docs/phase-refactor/testing.md`, `CLAUDE.md`, and the
deviation-is-classified entry in `docs/phase-refactor/decisions.md` — that entry is the specification for this
agent's judgment, and building a strict conformance checker instead is the obvious wrong turn.

**Study the existing pattern before writing:** `src/platform/templates/agents/reviewer_contracts.py`
and `spec_alignment_reviewer.py` (the closest sibling). This agent must conform to the shared
reviewer contract, not invent its own shape.

**First action:** write B1–B6, one per row of the classification table. Build a temp project whose
source diverges from its design record in exactly one way per test. The classification table *is* the
specification, so the tests are a direct transcription of it.

**The failure mode to watch for** is this agent becoming a conformance checker — blocking on
deviations that are legitimate discoveries. B3 and B6 exist to prevent that, and the final manual
check runs the pipeline on a feature where the design was genuinely wrong. The right outcome there is
a passing review plus an updated design record, not a blocked workflow.

**Do not skip the write-back.** Without it the design record silently becomes a lie and every later
phase reasons from a false picture — the exact drift this rework exists to prevent.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Close the loop between design and reality. A new reviewer in the respec-code review team compares
what was built against what was approved, classifies each divergence, and writes confirmed-legitimate
deviations back into `### Skeleton Index` so the design record stays true.

## The balance this strikes

The design is a hypothesis; implementation is the experiment. Enforcing conformance makes a wrong
design expensive to escape. Abandoning the record silently makes `### Skeleton Index` a lie, and every
subsequent phase then reasons from a false picture — which is precisely the drift this whole design
is meant to prevent.

The middle path: **the coder may deviate, must record it, and the record converges toward reality.**

That is also the honest answer to what the guardrail actually buys. It is not that the LLM must obey
the design — it is that when the coder departs, it departs from a pattern the user and the model
agreed on, visibly, with a reason.

## Behaviors to pin (red step — write these first)

The classification table below *is* the specification. Write one behavior test per row, named for the
situation rather than the classifier function.

| # | Behavior |
|---|---|
| B1 | A designed public method that was never implemented blocks the review |
| B2 | A new public method crossing a module boundary blocks the review |
| B3 | A new module-internal method does not block |
| B4 | A changed protocol without a recorded reason blocks |
| B5 | A changed protocol with a recorded reason passes, and the design record is updated to match |
| B6 | A cosmetic signature change does not block |
| B7 | Write-back never rewrites module layout or wiring |
| B8 | The reviewer is inactive when a phase has no design to conform to |

**B1–B6 are executable** — build a temp project with a known design record and a source tree that
diverges from it in exactly one way per test, then run the comparison. That is far stronger than
asserting the agent template mentions the rules, and it makes the classification logic genuinely
verifiable rather than aspirational.

**B5 is the one that matters most.** Without write-back the design record silently becomes a lie, and
every later phase reasons from a false picture — the exact drift this whole rework exists to prevent.
Assert the record *changed*, not merely that the review passed:

```python
def test_a_justified_signature_change_updates_the_design_record(project_with_justified_deviation):
    run_conformance_review(project_with_justified_deviation)
    assert design_record_signature_for('Neo4jClient.query') == implemented_signature_for('Neo4jClient.query')
```

**B7 is the containment test.** Write-back touches the seam index and the decision log only; a
divergence large enough to invalidate module layout is a shape amendment routed back to
`respec-phase`, not a silent rewrite.

**B3 and B6 are the anti-anchoring tests** — they prove the reviewer is not a conformance checker.
Their absence is how this agent quietly turns into one.

## Scope

### 1. The reviewer agent

New `src/platform/templates/agents/design_conformance_reviewer.py`, following the existing reviewer
pattern (`reviewer_contracts.py`, and `spec_alignment_reviewer.py` as the closest sibling).

**Input:** `phase.md` `### Skeleton Index`, plus the current source tree.
**Method:** extract current public signatures from the modules named in the index; diff against the
index entries.

**Classification** — this is the substance of the agent, and the reason it is not just a diff:

| Delta | Handling |
|---|---|
| **Missing** — designed message never implemented | `[BLOCKING]` unless recorded as intentionally dropped |
| **Added, crosses a module boundary** | `[BLOCKING]` — a new seam invented ad hoc is the original complaint reappearing |
| **Added, module-internal** | Fine. Not a seam, not binding |
| **Signature changed — protocol** (params, return type) | Needs a recorded reason; `[BLOCKING]` without one |
| **Signature changed — cosmetic** (param rename, ordering) | Score lane |
| **Dropped as irrelevant** | Fine when recorded |

The "recorded reason" comes from the coder's iteration handoff report `Deviations:` field
(`coder.py` ITERATION HANDOFF OUTPUT FORMAT) — this field did not exist when this document was
written and was added as part of this phase's work, since B4/B5 cannot be told apart without it.

Blocking markers must match the forms recognized at `src/utils/loop_state.py:48` — `[BLOCKING]`,
`[Severity:P0]`, `severity=P0`, `**[P0]**` — and reach the gate through `review-consolidator`, which
is already in `_MARKER_BLOCKER_GATE_CRITICS` (finding F16). No new set membership needed.

### 2. Registration

- `src/platform/reviewer_mapping.py:25-34` — add to the base list in `resolve_active_reviewers`,
  conditional on the phase having a non-empty `### Skeleton Index`. Follow the
  `has_coding_standards_file()` pattern at `:14-22` for the conditional.
- `code_command.py:329-405` — add to the `ACTIVE_REVIEWERS` block.
- `src/platform/tool_enums.py` — new `RespecAIAgent` member.
- `src/platform/template_generator.py` — `_AGENT_NAMES` and `_get_agent_specs` (finding F17 applies
  to commands, not agents, but verify counts).
- `src/platform/models/code.py` — a `*AgentTools` model.
- `src/platform/template_helpers.py` — a tools builder, and add the agent to the `add_task_agent`
  list for `respec-code`.

Also register in `patch_command.py`'s reviewer resolution — amendments diverge from design at least
as often as initial implementations.

### 3. The write-back

**The important half.** Without it the index silently becomes a lie.

After the review cycle consolidates and deviations are confirmed legitimate, append to `phase.md`:

```
- SD-### | source=implementation | supersedes=<index entry> | reason=<from handoff report>
```

and update `### Skeleton Index` to match the implemented reality.

Mechanism: `code_command.py` already updates the Phase document at `:1095`
(`store_phase_document` with `Status: "IMPLEMENTED"`). Extend that existing write rather than adding
a new one — it is already inside the sanctioned storage path.

Constraint: the write-back touches `### Skeleton Index` and `### Settled Design Decisions` only. It
must not rewrite `### Module Layout` or `### Collaboration And Wiring` — a deviation large enough to
invalidate those is a `#### Shape Amendment Request`, routed back to `respec-phase`.

Verify this interacts correctly with `patch_command.py`'s byte-integrity gate (finding F21): the gate
runs on patch, not code, but the two must not disagree about which sections are writable.

## Out of scope

Changing what the coder does. Enforcing conformance beyond the classification above.

## Exit criteria

- [x] B1–B8 pinned as executable tests in `tests/unit/utils/test_design_conformance.py` (B1-B7) and
      `tests/unit/platform_tests/test_reviewer_mapping.py` (B8), one per classification row, no gaps.
      **Caveat:** written alongside the implementation rather than strictly red-first — each was
      confirmed to fail for the right reason by mutation after the fact (see the live verification
      below), not by writing the test before any code existed. That is a real departure from this
      project's test-first discipline and is recorded here rather than glossed over.
- [x] `tests/unit/templates/test_review_agent_templates.py` — `TestDesignConformanceReviewerTemplate`
      plus inclusion in the cross-cutting `test_all_review_agents_use_sonnet` /
      `test_all_review_agents_have_required_sections` checks. Deliberately *not* added to
      `test_all_code_reviewers_enforce_grounded_file_line_evidence`: that contract is for reviewers
      producing prose findings against file:line evidence, and this reviewer's findings are structured
      classifier output (`qualified_name`/`kind`) from `check-conformance`, not free-form review prose
      — forcing that shape on would be applying the wrong contract, not conforming to the right one.
- [x] `uv run pytest` green (1360 passed, 73 skipped, 0 failed). `regenerate` verified programmatically
      for `ClaudeCodeAdapter` and `CodexAdapter` (19 agents each, including
      `respec-design-conformance-reviewer`); `OpenCodeAdapter` requires a one-time
      `respec-ai models opencode` configuration step unrelated to this phase and was not separately
      re-verified, but its regeneration path is exercised by the existing (green) `test_opencode_sync.py`
      suite.
- [x] Manual, run live against a real scratch git repository (`scratchpad/phase7-e2e`, since removed):
      committed a real `KBClient` implementation matching a hand-authored Skeleton Index
      (`KBClient.__init__(entries: list[str]) -> None`, `KBClient.query(keyword: str) -> list[str]`),
      then ran the actual `respec-ai check-conformance` CLI — not a mocked call — against six
      real mutations of `src/kb/client.py`, one per classification row:
      - Deleted the `query` method entirely → `blockers: [{"qualified_name": "KBClient.query", "kind":
        "missing", ...}]`.
      - Added a new `close()` method plus a real `src/kb/consumer.py` importing `KBClient` and calling
        `client.close()` → `blockers: [{"qualified_name": "KBClient.close", "kind":
        "added_cross_module", ...}]`.
      - Removed `consumer.py`, kept `close()` uncalled anywhere else → zero blockers, `findings:
        [{"kind": "added_internal", ...}]`.
      - Added a required `limit: int` parameter to `query` with no recorded deviation → `blockers:
        [{"kind": "protocol_changed_unrecorded", ...}]`.
      - Same change, this time with `deviations=[{"qualified_name": "KBClient.query", "reason": "added
        limit to cap unbounded scans on large entry sets"}]` in the payload → zero blockers,
        `updated_skeleton_index` came back with the new `limit: int` parameter spliced in, and
        `new_settled_decisions` contained a real `- SD-### | source=implementation |
        supersedes=KBClient.query(keyword: str) -> list[str] | reason=...` line. This is the row the
        phase document calls out as the one that matters most, and it round-tripped correctly.
      - Renamed `keyword` to `search_term` (same type, same return) with no deviation recorded → zero
        blockers, `findings: [{"kind": "cosmetic_changed", ...}]`.
      `git status` after all six runs showed only the source file I edited by hand — the CLI itself
      never wrote to disk across any of them, confirming the filesystem-boundary claim structurally
      and empirically, not just by the tool grant (`generate_design_conformance_reviewer_template`
      was inspected directly: its rendered `tools:` line has no `Write` capability).
- [x] Manual: confirmed structurally rather than by inspection alone — `ConformanceReport` has no field
      capable of carrying `### Module Layout` or `### Collaboration And Wiring` content, so write-back
      cannot touch them by construction. `test_write_back_only_returns_skeleton_index_and_settled_decision_fields`
      asserts the field set directly.
- [ ] Manual: run `respec-patch` afterward and confirm the phase-integrity gate still passes. **Not
      executed live** — reasoned through instead: `patch_command.py`'s byte-integrity gate (F21) diffs
      `PHASE_MARKDOWN` against `UPDATED_PHASE_MARKDOWN` *within a single `respec-patch` run*, both
      freshly fetched at that point, so a write-back that already landed during a prior `respec-code`
      run is simply part of the baseline the next `respec-patch` diffs against — there is no stored
      "original" from before the write-back for the gate to compare against. This reasoning was not
      exercised against a live two-command sequence.
- [ ] Manual: run the full pipeline on a feature where the design was *wrong* in a way the coder must
      work around. **Not executed** — this requires a live multi-agent `respec-code` session (the
      actual `respec-design-conformance-reviewer` subagent invoked by a real orchestrator, not the
      `check-conformance` CLI called directly), which is out of reach of an implementation pass alone.
      Everything downstream of "the reviewer has a classifier result" was exercised for real above;
      what remains unverified is the agent's own judgment in translating that result into the review
      markdown and deciding when a divergence is large enough to route to `respec-phase` instead of
      writing back.
