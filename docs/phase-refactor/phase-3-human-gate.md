# Phase 3 — `validate_document` + the human gate

**Depends on:** Phase 2. **Blocks:** Phases 4 and 5.
**Risk:** medium-high — this is where the UX will feel wrong first.

## Start here

**Prerequisites:** Phase 2 complete. Verify: `grep -n "module_layout" src/models/phase.py` returns
output.

**Already done?** `grep -n "phase_mode" src/platform/templates/commands/phase_command.py` — output
means complete. (`validate_document` alone is not a reliable signal: it landed first as its own
piece, see Progress below, before the gate flow that consumes it.)

**Progress as of 2026-08-24:** `validate_document` (`MCPModel.find_content_loss` +
`DocumentToolsInterface.validate` + the MCP tool + `RespecAITool.VALIDATE_DOCUMENT`) is implemented
and tested — this satisfies B1-B3. The `allow_frozen_field_edits` override on
`store_phase`/`update_phase` (both backends) is implemented and tested at the state-manager layer —
this satisfies B6 and half of B5 (the override works; the template-layer `source=user-edit` SD
recording it's paired with in §4 does not exist yet). **Not started:** the two-act `phase_command.py`
rewrite (§2-§5, B4, B7-B10), and `template_contract.py` extensions for B7-B10. Postgres parity for
the frozen-field override was mirrored by hand but is untested — the postgres suite is skipped
without a live DB in this environment; verify `tests/integration/test_state_manager_model_roundtrip.py`
covers it (check whether its fixture accepts `allow_frozen_field_edits`) before relying on it.

**Read first:** `docs/phase-refactor/README.md`, `docs/phase-refactor/testing.md`, `CLAUDE.md`, and **all of**
`docs/phase-refactor/decisions.md` — this phase implements four decisions that were reversed during design
(critic-after-approval, no decision cap, frozen-fields-repaired, reuse of the existing loop type).
Implementing the pre-reversal version would look reasonable and be wrong. Findings F5, F7, F8, F9,
F15, F16, F18, F22 apply.

**First action (done — see Progress above):** build `validate_document` and invert Phase 0's B6/B7
tests. It is ordinary Python on strings, fully testable without prompt machinery, and every later
step of this phase depends on it. Do not start the gate flow until the validator is green.

**Next action:** the two-act `phase_command.py` rewrite (§2 below), as two separate commits:
1. **Mechanical first** — insert the new Step 3 (read `### Shape Gate`, branch shape vs detail act)
   and renumber the existing 10 steps into the §2 table below, re-pointing every internal
   back-reference (`Return to Step N`, `resume at Step N`, the `refine` branch at what is currently
   `phase_command.py:435-437`). No behavior change. Get the suite green before moving on — do not mix
   this with the gate behavior below in the same diff, it makes a 1172-line template unreviewable.
2. **Then** layer in the design conversation (§3), the edit gate (§4), and the joint gate (§5),
   extending `tests/support/template_contract.py` as needed for B7-B10 (its current four methods —
   `declared_tools`, `invoked_tools`, `decision_branch`, `blocker_conditions` — don't yet cover the
   `APPROVED_VERSION` comparison the joint gate needs).

**The single most important thing to get right** is that the critic runs *after* the user approves,
not before. If you find yourself writing an architect↔critic loop that resolves to a quality
threshold and then shows the user the result, stop and re-read `decisions.md`.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Put the user inside the design loop. The phase workflow splits into two acts; in the shape act the
user reviews and edits the design, approves it, and only then does the critic run — as a safety net
on their judgment rather than a gatekeeper ahead of it.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A user edit that the parser would silently discard is reported instead |
| B2 | A bare `---` inside a section is reported (**inverts Phase 0's B6**) |
| B3 | A custom `###` under a mapped H2 is reported (**inverts Phase 0's B7**) |
| B4 | A user's hand edit to any design section survives into stored state |
| B5 | A user edit to a roadmap-seeded field is accepted at the gate and recorded |
| B6 | An agent write to a roadmap-seeded field is still rejected (Phase 0's B3, unchanged) |
| B7 | The design act does not close until the user has approved *and* the critic has passed |
| B8 | A design that changes after approval requires re-approval |
| B9 | The user can override critic findings, and the override is recorded |
| B10 | Every user prompt in the act blocks and can be answered on every TUI |

**B2 and B3 are the inverted Phase 0 tests.** Flip them here — that pairing is the clearest possible
demonstration that `validate_document` fixed a real defect, and it is why Phase 0 wrote them in the
first place.

**B7 and B8 are the heart of the phase** and pin the ordering decision from
[decisions.md](decisions.md). Express them as loop-state behavior, not as step numbering:

```python
def test_design_act_does_not_close_until_user_approves_and_critic_passes(): ...
def test_design_changed_after_approval_requires_reapproval(): ...
```

B8 exercises the `Phase.version` mechanism (finding F22). Drive it by storing a modified phase
between approval and the gate check, and assert the act loops back rather than proceeding.

**B10** is the TUI-parametrized test from [testing.md](testing.md) — the abstraction only earns its
keep if a Codex user gets a working prompt too (finding F18).

## 1. `validate_document` (build first)

The gate has a human hand-editing `phase.md`, and per findings F7–F9 the parser matches headings by
substring, truncates on a bare `---`, and silently drops custom H3s under mapped H2s. Silently
discarding the *user's* edits would be strictly worse than the opacity being fixed — and an LLM
orchestrator cannot call `Phase.parse_markdown` itself to find out.

Add `DocumentToolsInterface.validate(content) -> MCPResponse` in a shared mixin
(`src/mcp/tools/base.py`, implemented once, reused by all document types):

1. `parse_markdown(content)` → `build_markdown()`.
2. For every `(h2, h3)` in `HEADER_FIELD_MAPPING`, extract from both input and round-trip. Report any
   heading non-empty in the input but empty or truncated after.
3. Report every `###` in the input that sits under a mapped H2 but is not in the mapping.
4. Report every bare `---` inside a mapped section.

Register in `src/mcp/tools/document_tools.py`, `src/mcp/server.py`, `RespecAITool`
(`tool_enums.py:109-115`), and `PhaseCommandTools`.

This is the green step for B1–B3. Because the validator is ordinary Python operating on strings, it
is fully testable without any prompt machinery — write the behaviors as documents-in, reports-out,
one test per loss mode.

## 2. The two-act flow

`src/platform/templates/commands/phase_command.py`.

| Step | Content |
|---|---|
| 1–2 | Parse inputs, locate `phases/*/phase.md`, sync disk→MCP |
| **3** | **NEW** — read `### Shape Gate`; `unshaped`/`shape-proposed` → shape act, `shape-settled`/`shape-amended` → detail act. Explicit user instruction can force a re-shape |
| 4 | Init `SHAPE_LOOP_ID` (`loop_type="phase"` — see finding F15), link to document |
| **5** | Architect, `phase_mode="shape"` |
| **6** | **Design conversation** (below) |
| **7** | **Skeleton opt-in** — `multiSelect` over internal classes the architect flags as consequential |
| **8** | **Write `phase.md` to disk, block for editing** |
| **9** | **Re-read, validate, diff, record**; set `APPROVED_VERSION = Phase.version` |
| **10** | **Critic runs on the approved design**, `phase_mode="shape"` |
| **11** | **Joint gate** (below) |
| **12** | Gate → `shape-settled`; enter detail act |
| 13–16 | `DETAIL_LOOP_ID`, architect + critic `phase_mode="detail"`, **existing** decision protocol unchanged |
| 17–18 | Research synthesis + validation — unchanged (`:466-768`), output to `research/` |
| 19 | Completion contract |

Add `phase_mode` as a scalar input to both architect and critic, per the `phase2_mode` /
`validation_mode` precedent (`AGENT_DEVELOPMENT_GUIDELINES.md:180-186`). Reuse
`CriticAgent.PHASE_CRITIC` — see finding F16 for why a new critic would silently gate nothing.

### The protocol exception — state it explicitly

`phase_command.py:417-428` declares that `refine` must never consult the user. **In the shape act
only**, `refine` routes to the user instead of auto-refining. This must be written into the command
as a named exception, not left implicit, or it reads as a violation of the mandatory decision
protocol. The detail act keeps the current protocol verbatim.

## 3. Step 6 — the design conversation

`### Open Design Decisions` entries, format enforced by the critic:

```
- OD-001 | title: <one line>
  - Option A: <name> — <tradeoff>
  - Option B: <name> — <tradeoff>
  - Recommended: <A|B> — <why>
```

**No cap on the count** — see [decisions.md](decisions.md). Instead:

- **Rank by blast radius** — how much must change if this is reversed after implementation. Highest
  first, so attention goes where reversal is expensive.
- **Explicit user exit** — every prompt offers *"accept the recommended default for all remaining."*
  Stopping is a decision, not a silent cutoff.
- **Critic catches under-surfacing** — Step 10 blocks on *"a consequential choice was never surfaced
  as a decision."*
- **Options must genuinely diverge** — a decision with an obvious answer is itself a blocker.
  Fatigue comes from bad decisions, not many.

Each answer appends
`- SD-00n | source=user-menu | supersedes=OD-00n | decision=… | rationale=… | binding=yes`.

Use `{selection_prompt_instructions}` / `WAIT for {selection_response_source}` throughout (finding F18).
Every prompt carries the full non-termination block:

```
WAIT for {selection_response_source}.
DO NOT treat this as workflow completion, cancellation, or failure.
After the user responds, resume at Step <N>. Continue immediately.
DO NOT explain that the workflow is stopping unless the user asks why.
```

## 4. Step 8/9 — the edit gate

**Step 8** writes `phase.md` to the phase directory, states the two rules that keep the parser from
eating edits (do not rename, add, or delete headings; no bare `---` inside a section), then blocks on:
*done editing* / *no edits, continue* / *send it back for another shape pass*.

The menu selection is the **only** "done editing" signal — no mtime polling, no file watching. This
renders identically on Codex (finding F18).

**Step 9** re-reads, runs `validate_document`, and if anything would be dropped shows which headings
and why, offering fix-and-retry (max 3) / drop-those-edits / abort. Then diffs per-heading and appends
for each change:

```
- SD-### | source=user-edit | section=<H2 > H3> | decision=<one-line summary> | binding=yes
```

**Frozen fields are editable here and only here.** Phase 0 made the freeze bind agents; this is the
sanctioned human exception, recorded explicitly. Persist via `store_document` and re-write the
reconciled markdown back to disk so MCP and disk agree byte-for-byte on exit.

**Who wins:** disk wins at this gate and nowhere else; MCP is authoritative everywhere else.

Amend the storage-restriction banner at `phase_command.py:805-819` to permit these gate writes.

## 5. Step 11 — the joint gate

```
CRITIC_RESULT = decide_loop_next_action(SHAPE_LOOP_ID)

IF completed AND Phase.version == APPROVED_VERSION:
    → shape settled, proceed

IF completed AND Phase.version != APPROVED_VERSION:
    → design changed after approval; re-approve (return to Step 8)

OTHERWISE (refine or user_input):
    → Display critic findings, blockers first
    → {selection_prompt_instructions}
      "The critic flagged N issues with the design you approved. How do you want to handle them?"
        1. "Address all of them — refine the design"
        2. "Address some — let me pick"
        3. "Override: these are acceptable, proceed anyway"  (records an SD with rationale)
    → WAIT for {selection_response_source}   [+ non-termination block]
    → store_user_feedback(direction)
    → Return to Step 5 (architect refines under USER direction, not autonomously)
```

`Phase.version` increments on every store (finding F22), so approval tracking needs no new state.

Option 3 matters: the critic must not be able to hold a design hostage over a judgment call the user
has already made. It only has to be recorded.

## Out of scope

Skeleton files on disk (Phase 4), `implementation.md` (Phase 5), Task removal (Phase 6).

## Exit criteria

- [ ] B1–B10 observed failing first, then pass.
- [ ] Phase 0's B6 and B7 are now inverted and green — the defect they documented is fixed.
- [ ] Template assertions go through the contract helper. Specifically, **no test asserts that a step
      contains the non-termination block verbatim** — assert that the branch blocks for a user
      response, which is the behavior that block exists to produce.
- [ ] `uv run pytest` green; `regenerate` valid for all three TUIs.
- [ ] Manual: decisions arrive ranked by consequence; "accept remaining defaults" works.
- [ ] Manual: hand-edit a section — the edit survives with a `source=user-edit` SD entry.
- [ ] Manual: insert `---` mid-section — it is caught, not silently eaten.
- [ ] Manual: edit a frozen `### Objectives` at the gate — allowed and recorded; confirm an agent
      refinement still cannot change it.
- [ ] Manual: the critic runs *after* approval and its findings return as a conversation.
- [ ] Manual: reword every prompt in the act arbitrarily; the suite stays green. If it goes red, those
      tests are pinning phrasing rather than behavior — fix them, not the wording.
