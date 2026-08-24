# Phase 0 — Repairs & guard rails

**Depends on:** nothing. **Blocks:** everything.
**Risk:** very low. **Size:** roughly a day.

## Start here

**Prerequisites:** none. This is the first phase.

**Already done?** `grep -rn "Development Environment\|Test Organization" src/platform/templates/` —
no output means this phase is complete.

**Read first:** `docs/phase-refactor/README.md`, `docs/phase-refactor/testing.md`, `CLAUDE.md`. Findings F3, F4, F5, F6, F7,
F10, F20 in `docs/phase-refactor/findings.md` are the evidence for everything below.

**First action:** write the seven tests in *Behaviors to pin*, run `uv run pytest`, and confirm B1,
B3, B4, B5 fail. If any of them passes immediately, the test is not exercising the behavior — fix
the test before proceeding.

**Line numbers below were verified at design time.** Confirm each before acting; if one has moved,
search for the surrounding text and update this document as part of your change.

## Goal

Fix three live defects and install the tests that make two of them impossible to reintroduce. No
redesign, no new sections, no behavior change to the pipeline shape. This phase ships on its own and
delivers immediate user-visible value: `respec-phase` starts actually stopping for the user.

## Behaviors to pin (red step — write these first)

This phase is the ideal introduction to the discipline in [testing.md](testing.md): four of these
tests go red against *existing* code, so the red step costs nothing and produces real evidence the
harness works.

Write all of them, run them, and confirm each fails for the right reason before writing any fix.

| # | Behavior | Status today |
|---|---|---|
| B1 | An agent is never instructed to read a Phase section that cannot exist | **RED** (findings F3, F4) |
| B2 | No section name can shadow another and silently swallow its content | **RED for H3 pair** (finding F7) — "Functional Requirements" / "Non-Functional Requirements" collide under `## Implementation`; harmless today only because of fixed field-write order. Split into an H2 test (green) and an inverted known-defect H3 test, per B6/B7 style |
| B3 | Roadmap-seeded objectives survive an agent write | **RED** (finding F10) |
| B4 | The workflow waits for the user when the loop requests input | **RED** (findings F5, F6) |
| B5 | Every tool a command invokes is declared in its allowed-tools list | **RED** (finding F20) |
| B6 | A bare `---` inside a section truncates it | **green — documents a defect**, inverted in Phase 3 |
| B7 | A custom `###` under a mapped H2 is dropped | **green — documents a defect**, inverted in Phase 3 |

**B1** — `tests/unit/templates/test_phase_section_references.py`, new. Generate every template,
extract every Phase section an agent claims to read, assert each exists in the model or is a known
`additional_sections` H2. Name it for the behavior — `test_agents_never_reference_a_phase_section_that_cannot_exist`
— not for the mapping it inspects.

**B2** — asserts a property of `HEADER_FIELD_MAPPING` directly, which normally would be an
implementation-detail test. It earns its place because finding F7 means substring collisions cause
*silent content loss*, and this property is the only point at which that failure mode is checkable
before it happens. Name it
`test_no_section_name_can_shadow_another_and_silently_swallow_content`.

**B3** — extend `tests/unit/utils/test_state_manager.py`, parametrized across both backends per
[testing.md](testing.md). Store a phase, store again with mutated `objectives` via the
`store_document` path, assert the original survives.

**B4** and **B5** — these need the template-contract helper described in
[testing.md](testing.md#generated-templates-srcplatformtemplates). Build the minimum it needs:
decision-branch extraction and tool declaration/invocation sets. Nothing more — it grows with later
phases.

```python
def test_workflow_waits_for_the_user_when_the_loop_requests_input(phase_command):
    branch = template_contract(phase_command).decision_branch('user_input')
    assert branch.blocks_for_user_response()
    assert branch.persists_user_feedback()

def test_every_tool_a_command_invokes_is_declared_in_its_allowed_tools(phase_command):
    contract = template_contract(phase_command)
    assert contract.invoked_tools() <= contract.declared_tools()
```

B5 catches finding F20 as a *class* of bug rather than as one instance, and it is the test that will
keep catching it as later phases add tools.

**B6 and B7 are deliberately inverted.** They assert the *current defective* behavior, so the defect
is documented and Phase 3 has a concrete test to flip when `validate_document` arrives. Name them so
the intent is unmistakable — `test_bare_hr_truncates_section_KNOWN_DEFECT_inverted_in_phase_3` — and
cross-reference Phase 3 in a comment. A future reader must not "fix" the test.

## Scope

### 1. Repair the phase USER_INPUT branch (green step for B4)

Findings F5 and F6.

Add `RespecAITool.STORE_USER_FEEDBACK` to `PhaseCommandTools.respec_ai_tools`
(`src/platform/models/phase.py:15-23`) plus the corresponding rendered field. Its absence is *why*
the branch never blocked.

Replace `phase_command.py:451-458`, modelled on the working equivalent at `task_command.py:438-455`.
Leave the DECOMPOSITION sub-branch at `:428-451` untouched above it.

```text
  ELSE:
    (Regular USER_INPUT handling for stagnation or checkpoint)
    Display LATEST_FEEDBACK to user with:
    - Current score and iteration
    - Priority improvement areas

    {selection_prompt_instructions}
    Header: "Phase Guidance"
    Question: "Phase quality is at {{LOOP_SCORE}}/100. How would you like to proceed?"
    Options:
      1. "Continue refining - address the listed issues"
      2. "Provide specific technical guidance"
      3. "Accept current quality and proceed"

    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 7. Continue with feedback storage immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

    IF option 1: USER_FEEDBACK_MARKDOWN = "User requested continued refinement"
    IF option 2: Prompt for guidance; USER_FEEDBACK_MARKDOWN = "## User Guidance\n{{guidance}}"
    IF option 3: USER_FEEDBACK_MARKDOWN = "User accepted current phase quality"

    {tools.store_user_feedback}
    Return to Step 5
```

Use `{selection_prompt_instructions}` and `WAIT for {selection_response_source}` — never a literal
tool name (finding F18).

B4 is the regression test for this bug. Note that it asserts the branch *blocks and persists*, not
that it contains any particular phrase — so it survives a later rewording of the prompt and still
fails if the blocking is removed.

### 2. Re-point the phantom section references (green step for B1)

Findings F3 and F4. **Interim targets** — Phase 2 replaces these with the real design sections.

- `coder.py:378` — `Phase Development Environment section` → `Phase System Design > Architecture section`
- `coder.py:380` — `Test Organization specifications` → `Phase Implementation > Testing Strategy section`
- `spec_alignment_reviewer.py:182` — `Development Environment sections` → `Phase System Design > Architecture section`
- `coder.py:177` — the B1 guard test caught a fourth phantom not in the original findings: `Phase Code Standards section`, which names a Phase section that has never existed. Re-pointed to `Phase System Design > Technology Stack section`. This is the same defect class as F3/F4 at a fourth call site.

The point is not that these are good targets; it is that they exist, so the guard test passes and the
coder stops being instructed to read nothing.

### 3. Repair frozen-field preservation (green step for B3)

Finding F10. Make `store_phase` preserve `FROZEN_PHASES_FIELDS` the way `update_phase` already does:
`src/utils/state_manager/in_memory.py:310-331` and the postgres equivalent around
`src/utils/state_manager/postgres.py:453-512`.

Finding F11's comment ("this ensures immutable initial fields... are preserved") becomes
literally true once `store_phase` preserves frozen fields — no separate edit needed.

Deliberately *not* in scope: allowing the user to edit frozen fields. That arrives with the gate in
Phase 3. For now the freeze simply works as originally intended.

### 4. Declare the Read capability (green step for B5)

Finding F20 — add `BuiltInToolCapability.READ` to `create_phase_command_tools`
(`src/platform/template_helpers.py:150-168`). `phase_command.py:551` already calls `Read()` without
holding it.

The B5 guard test caught two more instances of the same defect class, at the same call
site:

- `RespecAITool.LIST_DOCUMENTS` was invoked (`mcp__respec-ai__list_documents` in Step 9)
  but never declared — added to `PhaseCommandTools.respec_ai_tools`.
- `sync_plan_instructions` (Step 2.1) invokes the platform's plan-retrieval tool
  (`mcp__linear-server__get_document` for Linear) but `create_phase_command_tools` only
  declared the phase-scoped platform tools. Added `get_platform_adapter(platform_type)
  .retrieve_plan_tool` as a fourth declared platform tool.

## Out of scope

New Phase sections, the bundle restructure, skeletons, any gate, any Task changes.

## Exit criteria

- [x] B1–B5 were each observed **failing first**, then pass. Confirmed by `git stash`-ing all
      production fixes (new test files are untracked and survive the stash) and re-running the
      suite: all seven behaviors failed for the stated reason, then passed after `stash pop`.
- [x] B6, B7 pass and are named so their inverted intent is unmistakable.
- [x] No test in this phase asserts a template contains a specific phrase; all template assertions go
      through the contract helper (`tests/support/template_contract.py`).
- [x] `uv run pytest` green (1271 passed, 75 skipped — postgres-backed tests skip without a
      running database).
- [x] `uv run respec-ai regenerate` valid for all three TUIs — verified against a scratch project
      for `claude-code`, `opencode`, and `codex`; all three regenerated without error and the
      generated `respec-phase` command contains the WAIT/store_user_feedback branch and the
      corrected `allowed-tools` list.
- [ ] Manual: run `respec-phase` on a scratch project, force a checkpoint iteration, confirm it
      stops and waits rather than looping past. **Not performed** — this requires a live
      multi-agent orchestration session (real phase-architect/phase-critic runs), which is outside
      what this change could execute directly. The generated template was inspected instead (see
      above); a live run is still recommended before treating this phase as fully closed.
- [x] Manual: reword the USER_INPUT prompt text arbitrarily and confirm B4 still passes — that is the
      check that it pins behavior rather than phrasing. Done: temporarily reworded the Question
      string in `phase_command.py`, confirmed B4 still passed, then reverted the wording.
