# Phase 5 — `implementation.md` + its gate

**Depends on:** Phase 3. **Independent of:** Phase 4. **Blocks:** Phase 6.
**Risk:** medium.

## Start here

**Prerequisites:** Phase 3 complete. Verify: `grep -rn "validate_document" src/mcp/tools/` returns
output. Phase 4 is *not* required.

**Already done?** `grep -rln "implementation.md" src/platform/templates/` — output means complete.

**Read first:** `docs/v2/README.md`, `docs/v2/testing.md`, `CLAUDE.md`, and the `implementation.md`
entry in `docs/v2/decisions.md`.

**First action:** read `src/platform/templates/agents/task_planner.py` end to end. This phase
migrates five distinct pieces of logic out of it, and Phase 6 deletes the file. Anything you miss
here is lost. The migration table below is the checklist, but read the source to confirm it is
complete before relying on it.

**Do not remove anything from the Task workflow in this phase.** Task keeps generating throughout;
the redundancy is deliberate so nothing breaks while the replacement is proven. Removal is Phase 6.

**One thing must happen in a single commit:** adding `### Execution Intent Policy` and deleting
`#### Delivery Intent Override`. Doing only the first leaves two sources of truth for delivery
intent, which is the ambiguity this phase exists to remove.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Give build strategy a home and a conversation. Removing the Task workflow (Phase 6) would otherwise
silently delete the one place implementation ordering got deliberate attention — this phase rebuilds
it inside `respec-phase`, as a discussion rather than a byproduct.

Task still exists and still generates throughout this phase. The redundancy is deliberate: nothing
breaks while the replacement is proven.

## Why a separate gate

*What the system is* and *in what order we build it* are different conversations, and the second only
makes sense once the first has settled. Folding them into one gate would either bury the ordering
discussion under the design discussion or force both before either is ready.

In practice this gate is lighter than the shape gate and will often be "looks right, go." Its value
is catching things like *"don't build the cache before the query path is proven."*

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | The generated plan's step format is readable by the consumers that scan it |
| B2 | Delivery intent has exactly one source of truth |
| B3 | Every constraint from the phase's references reaches the plan |
| B4 | The plan gate blocks and the user's alterations reach the generated plan |
| B5 | Deferred risks are recorded in a form the coding workflow can read |

**B1 is the legitimate string assertion**, and the reason is worth stating in the test itself:
`#### Step N:` is *parsed* by `code_command.py:315` and `patch_command.py:454`, so the exact format is
the contract. Assert it by running the real scanner against the generated plan rather than by
matching the literal — that way the test tracks the consumer if the consumer changes:

```python
def test_generated_plan_steps_are_readable_by_the_coding_workflow_scanner(implementation_plan):
    assert extract_steps(implementation_plan)  # same extraction the code workflow performs
```

**B2 is the anti-regression test for a defect this phase deliberately removes.** Two homes for
delivery intent is what forced the three-level precedence chain at `code_command.py:406-465`. Assert
that only one section anywhere in the generated Phase declares delivery intent — that keeps the
ambiguity from creeping back in a later edit.

**B3** is the carry-forward behavior migrated out of `task_planner.py:199-208`. Give it a phase with
constraints in its references and assert each appears somewhere actionable in the plan. Assert on
*presence in the plan*, not on which section — the section is an implementation choice.

## Scope

### 1. `implementation.md`

New file in the phase bundle (`phases/{phase}/implementation.md`). A plain file referenced by
`phase.md` — **not** a `DocumentType`, not MCP-stored, not loop-scored. Agents read it by path, the
same way `phase_command.py:551` already reads `.best-practices/*.md`.

Structure, carried over from the Task document so `respec-code` keeps working:

```
# Implementation Plan: {phase-name}

## Build Order
### Staging          — what lands first, what depends on what
### Steps            — `#### Step N:` with **Objective** / **Actions**

## Policy
### Execution Intent Policy    — Mode / Source / Tie-Break
### Deferred Risk Register     — DR-### | status= | severity= | scope= | reason=

## Checklist         — `- [ ]` items, each with (Step N) and (verify: command)
```

**Keep the `#### Step N:` format.** `code_command.py:315` and `patch_command.py:454` scan for it.

### 2. Logic migrated out of `task_planner.py`

Migrate now; delete the file in Phase 6.

| From | To |
|---|---|
| Execution intent resolution (`task_planner.py:205-210`) | `### Execution Intent Policy` |
| Deferred Risk Register (`:270-284`), same `DR-###` format | `### Deferred Risk Register` |
| Checklist / Steps structure (`:382-398`) | `## Build Order`, `## Checklist` |
| Constraint hierarchy + carry-forward (`:179-204`) | architect detail mode in `phase_architect.py` |
| Research Read Log (`:220-226`) | an `- Applied: <where>` line under each `- Read:` block in `### Research Requirements`. No new section — the parser at `phase_command.py:487-490` already tolerates indented metadata |

Dropped, not migrated: Task naming and the Task-level DECOMPOSITION path (`:353-367`, `:435-459`) —
Phase has its own decomposition route at `phase_command.py:428-451`.

**Delete `#### Delivery Intent Override`** from `phase_architect.py:416-425` in the same commit that
adds `### Execution Intent Policy`. Two homes for delivery intent is the ambiguity that
`code_command.py:406-465` currently resolves with a three-level precedence chain; moving the section
without removing the old one preserves the problem.

### 3. Architect mode

`phase_architect.py` gains an implementation-plan mode alongside `shape` and `detail`. It runs after
the shape settles and produces `implementation.md` from the settled Module Layout, Skeleton Index,
and Test List.

### 4. The gate

New step in `phase_command.py`, after the shape gate closes:

```
Present the implementation plan as a walkthrough:
  build order and why, what lands first, what is deferred and why

{selection_prompt_instructions}
Header: "Implementation Plan"
Question: "Here's the order I'd build this. Does it look right?"
Options:
  1. "Looks right — proceed"
  2. "Alter specific parts — let me say which"
  3. "Provide direction and regenerate"

WAIT for {selection_response_source}.
DO NOT treat this as workflow completion, cancellation, or failure.
After the user responds, resume at this step. Continue immediately.
DO NOT explain that the workflow is stopping unless the user asks why.
```

Options 2 and 3 store user feedback and regenerate. Option 1 writes `implementation.md` and proceeds.

### 5. Reference from `phase.md`

Point `## Additional Details > ### Implementation Plan References` at
`phases/{phase}/implementation.md`. Reuses an existing section — no new field.

## Out of scope

Removing Task (Phase 6). Rewiring `code_command` to read `implementation.md` — that happens in
Phase 6, when Task actually goes away. This phase produces the file; nothing consumes it yet.

## Exit criteria

- [ ] B1–B5 observed failing first, then pass.
- [ ] `#### Delivery Intent Override` removed from `phase_architect.py` **in the same commit** that
      adds `### Execution Intent Policy`, with B2 green across the pair.
- [ ] Template assertions go through the contract helper, except B1, which deliberately asserts the
      parsed format and says so in a comment.
- [ ] `uv run pytest` green; `regenerate` valid for all three TUIs.
- [ ] Manual: run a phase; the implementation-plan walkthrough appears after the shape gate; option 2
      alters the plan; the resulting `implementation.md` reflects the change.
- [ ] Manual: `respec-task` and `respec-code` still work unchanged — Task is still present, and the
      redundancy is deliberate until Phase 6.
