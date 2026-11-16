# Phase 4 — The agent-ready brief

**Depends on:** Phase 2 (cooperative flow) and Phase 3 (structural checks in `validate_document`).
**Blocks:** nothing. This is the last phase; the effort-level verification in the README runs at its
end.
**Risk:** medium–high. There is no migration and no parser change, but the phase adds an agent,
changes three prompts and the orchestrator, and extends the MCP checks. The real risk is brief
quality. A verbose or speculative brief makes implementing agents *worse* than vibe coding, and no
test measures that (README "Cross-cutting risks" 1).

## Start here

**Prerequisites.** Phases 2 and 3 are complete. Each probe was run on 2026-11-13 and correctly
reported "not done", because neither phase had landed yet:

```bash
# Phase 2 done?  → both print nothing (the README's phase 2 probe)
grep -L "## Decisions needed" src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/templates/commands/phase_command.py
grep -n -E 'post_synthesis|AUTO_API_PROMPTS|phase_mode == "shape"|Task\(bp\)|--no-verify' src/platform/templates/commands/phase_command.py src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/template_helpers.py src/platform/models/phase.py
# Phase 3 done?  → output means done (the README's phase 3 probe; both halves must have landed)
grep -q "async def validate(" src/mcp/tools/phase_tools.py && grep -n "structural_findings" src/platform/templates/commands/phase_command.py
```

Phase 3's MCP half can land before its wiring, which is why its probe needs both halves. This phase
extends both.

**Already done?** Output means done. This is also the README's phase 4 probe:

```bash
test -f src/platform/templates/agents/phase_finalizer.py && grep -n "def brief_handoff_extension" src/platform/tui_adapters/claude_code.py
```

On 2026-11-13 it printed nothing and exited 1, so it reports "not done". None of the names this
phase introduces (`brief_handoff_extension`, `BRIEF_SECTIONS`, `BRIEF_SECTION_PLACEHOLDERS`,
`IMPLEMENTATION_BRIEF_EXAMPLE`, `PHASE_FINALIZER`, `phase-finalizer`, `review_target`) occurs
anywhere in `src/` or `tests/`, so the probe cannot match unrelated text. The finalizer file alone is
not enough: it exists early in this phase, because the registration tests need it. The handoff
lands late (Scope 10). `test -f` prints nothing, so the line has output only when both have
landed.

**Read first:**
1. [README.md](README.md), all of "Shared contracts". Scope 0 makes six amendments to it; read the
   current text before changing it.
2. [decisions.md](decisions.md):
   - "Brief prose lives under fixed H2 headings captured by `additional_sections`"
   - "The finalizer is a separate agent file"
   - "The writing agents put the `implementation.md` draft on disk themselves"
   - "The critic reviews drafts before the user sees them"
   - "respec-code and respec-patch are frozen"
   - "'Neutral' means a uniform meta-notation, not native syntax"
3. [findings.md](findings.md): F10, F14, F22, F24–F29, F31–F37.
4. [phase-2-cooperative-flow.md](phase-2-cooperative-flow.md), "The new `/respec-phase` step map"
   and work items 3–6, and [phase-3-structural-checks.md](phase-3-structural-checks.md), "How the
   checks fit the flow" and work items 1–3 and 6–9. This phase inserts into both.
5. `docs/phase-refactor/testing.md` and `CLAUDE.md`.
6. `docs/AGENT_DEVELOPMENT_GUIDELINES.md:911`, "F-String Template Safety in Commands". Every
   template you touch is a Python f-string.

**First action: confirm what phases 2 and 3 actually landed.** This document was written before
either existed. It cites pre-phase-2 template lines only for orientation, and names everything else
by the symbols the phase 2 and phase 3 documents commit to. Confirm each of these in the code; if one
differs, follow the code and correct this document:
- Phase 2's step map in `src/platform/templates/commands/phase_command.py`: Step 9 (critic review
  and automatic repair, `REVIEW_ROUND`, `REPAIR_ROUNDS`, `REVIEW_DECISION`), Step 10 (design review,
  whose last prompt offers "approve the design and go to sign-off"), Step 11 (sign-off, which uses
  `IMPLEMENTATION_PLAN_PATH`) and Step 12 (store and hand off).
  `PHASE_FILE_PATH` is still resolved in Step 1, and Step 3 sets `IMPLEMENTATION_PLAN_PATH`.
- Phase 2's invocation fields: `invoke_architect_draft`, `invoke_architect_revise`,
  `resume_architect` (one field for every mode, used with `ARCHITECT_MODE`), `invoke_critic_review`.
  The critic's invocation carries `review_round` and `project_config_context_markdown` (phase 2,
  "Invocation inputs").
- The architect writes `implementation.md` at
  `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md` with a `Write` grant scoped
  to `.respec-ai/plans/*/phases/*/implementation.md` (phase 2 work item 5; open call 1). If the user
  overturned that open call, read "If phase 2 overturned the Write grant" in Scope 6 first.
- Phase 3's names:
  - `src/utils/phase_structure.py`: `check_phase_structure`, `extract_cited_paths`,
    `check_implementation_structure`, `drop_accepted_findings`
  - `src/models/document_validation.py`: `StructuralCheck`, `FindingOwner` (`architect`,
    `orchestrator`), `CitedPathKind`, `StructuralFinding` (`check`, `location`, `subject`, `part`,
    `owner`, `detail`), `CitedPath` (`path`, `kind`, `cited_in`), `CONTENT_LOSS_WARNING`
  - `DocumentValidationResponse` in `src/utils/loop_state.py`, with `structural_findings`,
    `implementation_findings`, `paths_to_verify` and `skipped_checks`
  - the `key` and `implementation_markdown` parameters of `validate_document`, and the
    orchestrator's `validate_document_structure` field
  - the test file `tests/unit/utils/test_phase_structure.py`
- Phase 3's wiring:
  - the orchestrator's key-mode gate at the top of Step 9, with no `implementation_markdown`. It
    sends `owner: architect` findings to an architect `revise`, and puts `owner: orchestrator`
    findings, and architect findings left when the budget is spent, in `STRUCTURAL_LEFTOVERS`.
  - the architect's self-check with `implementation_markdown`
  - the critic's relay of `implementation_findings` as
    `[mechanical] [Implementation Plan Structure Invalid - BLOCKING]`
  - accept-as-is SDs that `drop_accepted_findings` honors

Then write B1. It touches only the model and has no dependencies.

**Judgment calls no test will catch.**
1. **Brevity is part of correctness.** Every H3 in the brief earns its place or holds exactly
   `- None`. `## Behaviors & Acceptance` is a traceability map, one line per item, not prose. As a
   yardstick, the `docs/phase-refactor/phase-*.md` documents (7–18 KB) are the format that already
   works with Claude Code. A generated brief much longer than those is probably padded.
2. **The finalizer is not a second designer.** It writes the brief around a design the user already
   approved. It never changes seams, the design narrative, decisions, delegation bounds or the build
   order. The critic's reviewed-sections check (Scope 8) is the only mechanical guard, so read real
   output.
3. **Delegation Bounds must be specific to the phase.** "Follow best practices" and "use good
   judgment" are worthless. Each line must name a seam, a module, a decision or a concrete
   condition.
4. **Calibrate the cold-start classification.** The test is: does the answer already exist in the
   brief or the repository (`[mechanical]`), or does it need a choice nobody made (`[judgment]`)?
   More than four cold-start questions at sign-off (one Claude Code batch, phase 2's
   `selection_batch_limit`) means the design review let gaps through. Fix the prompts, not the cap.
5. **Never guess a command.** Verify and exit commands come only from the project's `[commands]`
   table, or from a decision the user settled in the briefing (phase 1's fallback). A guessed command
   is where language bias returns.
6. **The design narrative lives in `#### Design Narrative`.** A probe on 2026-11-13 showed that
   text placed directly under `## Design Shape`, before its first `###`, is dropped on parse **and
   not reported by `find_content_loss`**. This is a fifth trap beyond F27's four; it is not yet in
   findings.md. It is a content-loss problem, not a structural one: once parsed, the text is gone, so
   a check over the stored `Phase` cannot see it. Scope 5 adds it to phase 3's `find_content_loss`
   override (B17).
7. **Imperative audit.** In actionable sections, `may`, `can`, `should`, `consider` and `try to` are
   banned (`tests/unit/templates/test_agent_templates.py:53-62`). Write discretion as "decide without
   asking", never as "the implementer may".
8. **f-string safety.** Runtime pseudocode variables never appear in single braces. The handoff text
   (Scope 10) is a plain string returned by the adapter, so its `{IMPLEMENTATION_PLAN_PATH}` stays
   literal for the orchestrator to substitute. Today that variable is set only inside Step 12.6
   (`src/platform/templates/commands/phase_command.py:1035-1036`), which phase 2 deletes. Phase 2
   sets it in Step 3 instead, so it exists before Step 10.5.
9. **Write prompt text imperatively.** The finalizer is covered by the imperative-language audit
   (Scope 11). When you turn this document's prose into template text, write "add", "decide without
   asking" and "return", never "may add" or "can".

**Line numbers.** Every anchor was verified on 2026-11-13, before phases 1–3 landed.
- **Should survive:** anchors in the frozen respec-code readers (`code_command.py`,
  `coder_contracts.py`, `spec_alignment_reviewer.py`), `tests/support/plan_extraction.py`, and most
  of `src/models/` and `src/utils/`. Two exceptions: phase 3 adds a `find_content_loss` override to
  `src/models/phase.py`, and moves `_BULLET_PATH` out of `src/utils/skeleton_generator.py:16` into
  `src/utils/skeleton_types.py` under a public name (phase 3 work items 2 and 4).
- **Will probably move:** everything else.
  - Phase 2 changes the critic's tool builder (the soft caps go, F36) and `PhaseCommandTools` (the
    act-specific fields and `mcp_tools_reference` go, F38).
  - It also adds a capability to `tool_enums.py` and the adapters (F13), and a phase-local
    `bp-pipeline` exception line after the shared Claude Code guardrail, which itself stays
    unchanged (F18).
  - Phases 1 and 2 delete or rewrite tests (F23, F36).
  - Phase 2 deletes the command's copy of `technical_phase_template` and re-points
    `tests/unit/templates/test_phase_section_references.py:21` to the architect's copy.
  - Phase 3 changes `src/mcp/tools/`.
- **Re-finding them:** each such anchor names its symbol, so search for the symbol.
- **Marked *pre-phase-2*:** template text phase 2 rewrites. Use these only to understand what
  existed.

## Goal

Turn the phase workflow's output into an implementation brief that any harness can plan from,
delegate from and verify against (decisions.md, "The phase output targets any agentic harness"):

- **`phase.md`** keeps its typed design layer. It gains four fixed H2 sections of agent-facing prose
  (`## Grounding`, `## Delegation Bounds`, `## Behaviors & Acceptance`, `## Guardrails`), stored as
  `additional_sections` with no migration (F26). It stops generating the detail fields nothing reads.
- **`implementation.md`** keeps every frozen respec-code contract (F33). It gains `## Start here`,
  `## Exit criteria` and `## Deviations`, and each `#### Step N:` becomes a self-contained delegation brief with
  dependencies, test IDs and a verify command taken from project config.
- **A new `respec-phase-finalizer` agent** writes that prose and the step briefs after the user
  approves the design.
- **The critic gains a cold-start check:** "for each step, what would a fresh agent have to guess?"
  It runs on the finalized brief before sign-off. Mechanical gaps are filled automatically, and
  judgment gaps are asked at sign-off. No touchpoint is added.
- **Sign-off ends with a TUI-tiered handoff:**
  - the portable core is the brief itself, on every TUI
  - Claude Code also gets a ready-to-run instruction to implement `implementation.md`, delegating
    independent steps to subagents and verifying each

Every item carries an ID (SD-n, T-n, SC-n, G-n, FLOW-n, Step N), so a harness assembles subagent
briefs by citing IDs instead of copying prose.

## Behaviors to pin (red step — write these first)

| # | Behavior | Protects against |
|---|---|---|
| B1 | The four brief sections render in one fixed order (Grounding, Delegation Bounds, Behaviors & Acceptance, Guardrails), whatever order they were written or stored in, ahead of any other additional section | the same brief reading differently from each backend, because jsonb does not keep key order (F27 #4) |
| B2 | The document structure the writing agents are shown (`phase_architect.technical_phase_template`, the one copy phase 2 keeps; the finalizer renders the same constants) parses to exactly the four brief sections as `additional_sections` and to no retired detail field, and no H2 name in it can shadow another | agents writing sections nothing reads; a new H2 silently swallowing another section's content (F27 #1) |
| B3 | The example `implementation.md` the writing agents are shown stays readable by frozen respec-code: contiguous `#### Step N:` headings under `## Build Order > ### Steps`, `## Checklist` items carrying `(Step N)` and `(verify: …)` for existing steps, and `## Policy` with a `DR-NNN` line. It also has `## Start here`, `## Exit criteria` and `## Deviations` | breaking respec-code's step scan, Checklist gate or DR format (F33) |
| B4 | Every step in that example is a complete delegation brief. Paired with a minimal `Phase` fixture that defines exactly the IDs and Skeleton Index paths the example cites, the real `check_implementation_structure` reports exactly its placeholder commands: one `implementation-checklist-item-malformed` per Checklist item, and one `implementation-command-placeholder` per step `Verify` command and per `## Exit criteria` command. Nothing else | prompts and checks drifting apart, so agents are shown a format the checks reject; an agent shipping the example's command unchanged |
| B5 | A partially written brief is reported as a structural finding, never as content loss: Delegation Bounds missing or short of its three H3s; some but not all of Grounding, Behaviors & Acceptance and Guardrails; an empty required H3 | mechanical brief defects reaching the user, or reaching an implementing agent unnoticed (F29) |
| B6 | A step that a cold-start agent could not execute is reported: a step that holds neither exactly the three draft fields nor all seven fields in order; `Depends on` naming a missing step, itself, or a cycle; `Files` naming no backticked path; step numbers that are not contiguous from 1; a finalize section present while another is missing. So is any command that is a placeholder under Scope 5's rule (empty, starting with `TODO`, `no_preference`, or containing a `<…>` placeholder token), whether in a step's `Verify`, a Checklist `(verify: …)` or `## Exit criteria`. Phase 1's `ask user` marker is never flagged | parallel delegation deadlocking or running out of order; a guessed or missing verify command (F25) |
| B7 | Every ID resolves and every contract item has an owner. Flagged: `T-`, `SC-`, `G-` and `Step N` references to nothing; Test List entries without a trailing `T-n`, or with a duplicate; once every step is finalized, a `T-n` that no step turns green; a Skeleton Index path in no step's `Files`; an open OD's `Affects:` ID that resolves to nothing. Nothing inside an SD entry is checked as a reference (phase 3's exemption), so a missing or stale `affects=` and a non-ID `supersedes=` value are never flagged | a seam or test silently left unimplemented; dangling pointers in a subagent brief; rejecting the SDs frozen respec-code writes (`src/utils/design_conformance.py:287`) |
| B8 | Once `## Grounding` exists, the agent-facing research list (`## Grounding > ### Research to read`) and the ledger (`### Research Requirements` `- Read:` lines) never disagree | an implementing agent reading research the user declined, or missing research the user approved |
| B9 | Malformed brief input never raises: a non-integer step number, a step with no fields, a missing H2, `implementation.md` not supplied. Each is a finding, or phase 3's `implementation.md: not passed` entry in `skipped_checks` | the F24 crash class repeating in the new checks |
| B10 | The orchestrator can dispatch the finalizer on every TUI. It is generated for all three adapters, granted in the phase command's tools, and invoked by its runtime name | an agent that exists but cannot be called: opencode's `'*': 'deny'` (`src/platform/tui_adapters/opencode.py:282-283`), codex's renamed agents |
| B11 | The finalizer holds only what its job needs: read the repo, read and update the phase document, read notes and feedback, validate, and write `implementation.md` (path-scoped on Claude Code). No question tool on any TUI, no Edit, no Bash, no critic, store-feedback or store-analysis tools | least-privilege regressions (F14); a subagent attempting to talk to the user (F10) |
| B12 | The finalized brief is reviewed before sign-off without adding a touchpoint. Step 10.5 (after Step 10's "approve the design and go to sign-off" choice, before Step 11) invokes the finalizer, runs the key-mode gate, then the critic with `review_target: brief`; it holds no `WAIT for` and no touchpoint token. Its repair invocations are the finalizer's, never the architect's | the touchpoint budget (at most 3); repairs going to an agent that does not own the brief sections |
| B13 | The brief review never re-opens design judgment and never researches. The critic's `review_target == "brief"` branch carries none of the design-review rules, and Steps 10.5, 11 and 12 contain no `bp-pipeline` invocation and no route to Step 7 except back through Step 10 | the approve → critic → re-approve cycle (decisions.md, "The critic reviews drafts before the user sees them"); the cost invariant |
| B14 | Every settled decision the orchestrator writes for an answered OD or CQ carries `affects=`, copied from the entry's `Affects:` line | "what it binds" being lost when the OD leaves `### Open Design Decisions` |
| B15 | Every TUI gets a working handoff, and Claude Code also gets the delegation instruction. The Step 12 output names both brief paths and the respec-code alternative on all three TUIs, and contains the delegation instruction exactly when `adapter.brief_handoff_extension is not None` | capping Claude Code for parity, or making the portable path depend on a Claude Code feature (memory: TUI capability tiering) |
| B16 | Everything this phase adds is language-neutral on all three TUIs: the finalizer, the brief example constants and the handoff text | language bias re-entering through the newest text (decisions.md, "Zero language bias") |
| B17 | Text between a mapped H2 and its first H3 is reported as content loss: to the user on a hand edit, and as `CONTENT_LOSS_WARNING` on an agent's `update_document` | the design narrative, or any prose an agent puts there, vanishing on parse with no report (judgment call 6) |
| B18 | Findings about the finalizer's content are owned by the finalizer, and reach only it. They carry `owner: finalizer`: every finding located in Grounding, Behaviors & Acceptance or Guardrails, every `success-criterion-malformed`, and every `implementation.md` finding located in a finalize-only section or field. Phase 3's `orchestrator` rules still win. Step 9's gate and the architect's self-check never act on them, and the design-review critic never relays them | the architect being sent repairs it is forbidden to make, burning the budget and reaching the user as unresolved checks (phase 3 B18's computed-ownership rule, extended) |

Notes on the less obvious rows:

- **B3 and B14 are legitimate string assertions.** B3's formats are parsed by `code_command.py:291`
  and `coder_contracts.py:139`. `affects=` is read by the finalizer's apply step (Scope 6, STEP 2),
  and phase 3's SD segment parser lists its known keys, so add `affects` to them in the same change.
  Say so in a comment in each test (testing.md, "Where a string assertion is still legitimate"). Run B3 through
  `tests/support/plan_extraction.py:13-25`, extended with the new section helpers, never through a
  copy of the format kept in the test.
- **B4 is the test that holds the prompts and the checks together.** It runs the real check
  functions on the real example constant, so a reworded example that breaks the format fails here.
  The example's commands are deliberately placeholders (Scope 4), so B4 asserts that the findings
  are exactly those placeholder findings. That also proves that an agent copying the example's
  command is caught. `check_implementation_structure(markdown, phase)` requires a `Phase`, so build
  a minimal fixture `Phase` in the test that defines the SD, T, SC and G IDs and the Skeleton Index
  paths the example cites. The cross-document checks then run and find nothing. Do not make the
  `phase` parameter optional for the test's sake (`CLAUDE.md`: no test logic in production).
- **B2's shadowing half needs a negative self-test.** The existing guard
  (`tests/unit/templates/test_phase_section_references.py:92-101`) passes on day one. Extract its
  collision logic into a helper, and assert that the helper flags a synthetic `Design` H2 next to
  `Design Shape`. The positive half picks up the new names automatically, because the guard reads
  them from `technical_phase_template` (`:41-49`), imported from the architect after phase 2. Assert
  B2's first half by parsing that template with `Phase.parse_markdown`, not by matching strings.
- **B5–B9, B17 and B18 are mostly pure-function tests.** B5–B9 and B18's ownership half go in
  phase 3's `tests/unit/utils/test_phase_structure.py`, one defect per fixture. Assert on `check`,
  `subject`, `part` and `owner`, never on `detail` wording (phase 3, judgment call 7). B17 goes in
  `tests/unit/models/test_content_loss_detection.py`. B18's routing half is a template-contract test
  beside phase 3's B15, in `tests/unit/templates/test_phase_structural_gate.py`.
- **B10 follows `tests/unit/templates/test_coder_split_phase9.py:31-46`.** Build both
  `OpenCodeAdapter` and `CodexAdapter` with `model_overrides` so the test stays hermetic (F37).
- **B12 and B13 assert structure through `tests/support/template_contract.py`.** Take
  `template_contract(rendered_command).step_body('10.5')` and assert `wait_prompt_count(...) == 0`.
  Assert that the body contains the rendered `invoke_finalizer` and `invoke_critic_brief_review`
  text and none of the rendered architect invocations. For B13, assert that the step bodies of 10.5,
  11 and 12 do not contain the rendered `invoke_bp_pipeline` text. `invoked_tools()` and
  `blocker_conditions()` read the whole string they are given, so build a contract over the
  extracted body. For the critic half, extract the `review_target == "brief"` branch the way
  `_phase_mode_branch_body` does (`tests/unit/templates/test_phase_implementation_plan_gate.py:41-58`),
  and assert that it names none of the design-review markers.
- **B16 is already enforced by phase 1's guard.** It renders every agent whose name starts with
  `respec-phase-` and every command, on all three TUIs (phase 1, Scope item 1), so it scans the
  finalizer, the example constants and the Claude Code handoff without changes. Its red step is phase
  1's existing negative self-test. Add one coverage assertion so the new text cannot silently fall
  out of the scan: the scanned set includes `respec-phase-finalizer`, a scanned agent body contains
  the text of `IMPLEMENTATION_BRIEF_EXAMPLE`, and the Claude Code command render contains
  `ClaudeCodeAdapter().brief_handoff_extension`.

## Scope

Work the items in order. Items 0–5 have no agent or orchestrator dependency. Items 6–10 build on
them.

### 0. Amend the shared contracts first (README "Shared contracts", in the same commit as the first code that depends on them)

The README rule is: "A phase that needs to change one changes it here first, in the same commit, and
says so." Six amendments:

1. **Agents and modes.**
   - **The finalizer's grant:** `get_previous_analysis` and `validate_document`, replacing "as the
     architect". It reads the architect's exploration notes and writes none, so it gets no
     `store_current_analysis` (least privilege, F14). It self-validates the way phase 3 has the
     architect do (phase 3 work item 8).
   - **The finalizer's inputs:** the standard IDs (`loop_id`, `plan_name`, `phase_name`) and
     `project_config_context_markdown`. No path input: it builds the `implementation.md` path
     exactly as the architect does after phase 2,
     `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md`. On the markdown platform
     that is the phase file's sibling, the rule frozen respec-code uses
     (`src/platform/templates/commands/code_command.py:230-231`).
   - **The critic's inputs:** add `review_target`, either `design` or `brief`, on every critic
     invocation. Phase 2's `invoke_critic_review` passes `design`. `phase_mode` stays `review`; this
     is not a new mode (decisions.md, "Kept from the previous effort"). Phase 2 already passes
     `review_round` and `project_config_context_markdown`.
   - **On `review_target=brief`,** the critic also receives `phase_file_path`, the orchestrator's
     `PHASE_FILE_PATH`, for the reviewed-sections check (Scope 8).
2. **Decision entry → IDs.** The finalizer's `## Decisions needed` entries use `OD-NNN`, numbered
   above every OD and SD number in the document. Like `CQ` entries, they exist only in its report:
   the finalizer never edits `## Design Decisions` (Scope 6, STEP 4).
3. **Settled decision entry.** Add `affects=<value>` after `rejected=`. It is required exactly when
   `supersedes=` names an OD or a CQ, and is copied verbatim from that entry's `Affects:` line. It is
   absent otherwise: `source=user-edit`, `source=implementation`, `source=materializer` (written at
   sign-off today, `src/platform/templates/commands/phase_command.py:923`) and
   `supersedes=unresolved-checks` (phase 2) have no `Affects:` line to copy. Phase 3's SD segment
   parser gains `affects` as a known key (Scope 5).
4. **Critic findings.** On a `review_target=brief` run:
   - `[mechanical]` findings, and open `structural_findings` from the Step 10.5 gate, are repaired by
     a fresh **finalizer** invocation, not by the architect's `revise`. They share one two-round
     budget, which resets when Step 10.5 starts.
   - `[judgment]` findings are asked at sign-off.
   - The critic's stored feedback starts with the line `Review target: design` or
     `Review target: brief`, so the finalizer acts only on brief findings (`get_feedback` is
     untagged, F31).
   - `FindingOwner` gains `finalizer`, computed as Scope 5 says. Structural repair in Step 10.5 goes
     to the finalizer; Step 9's gate is unchanged.
   - Add the critic's three new `[mechanical]` markers to the list of blockers the critic still
     raises (phase 3 work item 10 makes that list exhaustive): `Grounding Path Invalid`,
     `Step File Verb Invalid` and `Reviewed Section Changed` (Scope 8).
5. **Research recording (phase 4).** The README says that "the orchestrator keeps writing the
   `- Read:` lines there as well", which reads as the orchestrator writing both copies. Amend it:
   - The orchestrator writes only the ledger in `### Research Requirements`, exactly as in phases 2
     and 3.
   - The **finalizer** writes the agent-facing copy in `## Grounding > ### Research to read`, from
     the ledger's validated `- Read:` lines, adding the decision, seam and step tags. Step tags
     exist only at finalize, and the finalizer owns `## Grounding`.
   - Check 6 (Scope 5) keeps the two copies in agreement once `## Grounding` exists.
6. **New subsection "Brief format (phase 4)", plus two edits under "Section naming and
   frozen-reader compatibility".**
   - The new subsection holds the layouts in Scopes 2 and 3: the section and H3 names, the ID kinds,
     the step field labels, who writes what, and the finalizer-owned findings rule (Scope 5). The
     finalizer, the architect, the critic, the structural checks and the tests all consume them.
   - Amend the sentence that names `## Start here` and `## Exit criteria` as the added H2s, so that
     it also names `## Deviations`.
   - Record the probe result from judgment call 6.

### 1. Canonical order for the brief sections: `src/models/phase.py`

- Add the constant below next to `HEADER_FIELD_MAPPING` (`src/models/phase.py:14-43`). It is the
  single source of the four names. Templates and checks import it from here; a model never imports
  a template.

  ```python
  BRIEF_SECTIONS: ClassVar[tuple[str, ...]] = ('Grounding', 'Delegation Bounds', 'Behaviors & Acceptance', 'Guardrails')
  ```

- In `build_markdown`, the `additional_sections` loop (`src/models/phase.py:172-175`) changes. It emits the brief
  sections present, in `BRIEF_SECTIONS` order, then every other additional section in its existing
  order. Their position before `## Metadata` is unchanged. (B1)
- No field, column or migration. A probe on 2026-11-13 round-tripped all four names, including
  `Behaviors & Acceptance` with its `&`, through `parse_markdown` and `build_markdown` with no
  content loss.

### 2. The `phase.md` brief layout (the contract)

New H2 sections, all raw markdown in `additional_sections`:

```markdown
## Grounding
### Build on
- `<path>` — extend: <what and why> — informs: Step 2, Step 3
### Leave alone
- `<path>` — <why it must not change>
### Exemplars
- `<path>` — imitate for <pattern> — informs: Step 1
### Conventions
- `<path>` — governs <what> (the project's standards config, contributor guide or lint config)
### Research to read
- `.best-practices/<file>.md` — informs: SD-2, Step 3 — Source: RP-002

## Delegation Bounds
### Out of scope
- <anti-requirement, from the Overview's Scope and the plan>
### Implementer's discretion
- <what an implementing agent decides without asking>
### Escalate if
- <condition that requires stopping to ask the user>

## Behaviors & Acceptance
- Objective: <objective> → tests: T-1, T-3 → accepted by: SC-1
- Deliverable: <deliverable> → tests: T-4 → accepted by: SC-2
### Not covered by tests
- SC-3 — verified by <how>, when <when>

## Guardrails
### Invariants
- G-1: <must always hold, or must never happen>
### Error policy
- G-2: <how errors are surfaced, propagated or recovered>
### Security and performance
- G-3: <constraint> (target: SC-3)
### Deviation protocol
- When the repository contradicts this brief, stop the step and add a line under implementation.md's `## Deviations`. Continue only if the deviation stays within `### Implementer's discretion`; otherwise escalate.
```

Rules:

- **Every step reference is a `Step N` token.** Write `informs: Step 2, Step 3`, never `Steps: 2, 3`,
  so the dangling-reference check (Scope 5, check 11) sees each one.
- **Who writes what.** Everything the user reviews at design review is the architect's. Everything
  derived from the approved design afterwards is the finalizer's.
  - The architect writes, in `draft` and `revise`: `## Delegation Bounds`, `#### Design Narrative`,
    the Test List with trailing `T-n`, and `### Success Criteria` entries in the `SC-<n>:` form.
  - The finalizer writes `## Grounding`, `## Behaviors & Acceptance` and `## Guardrails`. In
    `### Success Criteria` it only completes a missing `measure:` and appends an `SC-<n>` for an
    objective, scope item or deliverable no criterion covers. It never edits, removes or renumbers
    an existing criterion.
- **Empty H3s are never omitted.** Every H3 above is required, and an empty one holds exactly
  `- None`. A brief H2 with no content at all is silently dropped on parse
  (`src/models/base.py:424`), so "empty" must still be `- None`.
- **One home per fact.** `## Behaviors & Acceptance` holds traceability only:
  - one line for every objective, scope item and deliverable
  - plus how each untested criterion is verified

  It never defines criteria. Two homes for one fact is the defect class phase-refactor phase 5's B2
  removed.
- **Typed homes are kept**, because code or frozen readers parse them (F33, F34):

  | Typed section | Phase 4 form |
  |---|---|
  | `### Success Criteria` | Each entry is `- SC-<n>: <measurable outcome> — measure: <a [commands] value or an observable check>`. Non-functional targets live here, with their measurement. Together they must cover every objective, scope item and deliverable (`src/platform/templates/agents/spec_alignment_reviewer.py:140`). |
  | `### Test List` | Each entry is `` - `<test path>::<observable behavior>` — T-<n> ``. The ID goes **after** the closing backtick: `parse_test_list` reads only the backticked text (`src/utils/skeleton_generator.py:16`, `:99-108`); a probe confirmed a trailing ` — T-3` parses cleanly. Inside the backticks it would become part of the test name. |
  | `### Skeleton Index` | Unchanged, with **no IDs**. A probe showed `Owner.m(a) -> R — S-1` parses with return type `R — S-1` (`src/utils/skeleton_types.py:6-9`, `:51-62`), which would flow into materialization and conformance. Cite a seam as `` `<path>` :: <Owner>.<member> ``. |
  | `### Settled Design Decisions` | Canonical SD entries with `rejected=` and, after Scope 0, `affects=`. This is the plan's "Decisions" row (decisions.md). |
  | `### Design Shape - Additional Sections` | Holds `#### Design Narrative`, a short narrative written by the architect and first in this section, next to `#### UX Contract`. `review_weighting.py` only tests for the UX marker (`src/utils/review_weighting.py:18`, `:63-65`), so a second H4 is harmless. |
  | `### Research Requirements` | Unchanged as the ledger (README "Research recording"). |
  | `### Implementation Plan References` | Unchanged; its `- Constraint:` lines are hard constraints (`coder_contracts.py:167`). |

- **Retired from generation.** The model fields stay; their destructive removal is a follow-up.
  Content moves as follows:

  | Retired | Its content goes to |
  |---|---|
  | `### Architecture`, `### System Design - Additional Sections` | `#### Design Narrative` and `### Collaboration And Wiring` |
  | `### Technology Stack` | `## Grounding > ### Conventions` (point at the config, never restate versions), plus SDs for stack choices |
  | `### Functional Requirements` | `### Test List` (T-n) and `## Behaviors & Acceptance` |
  | `### Non-Functional Requirements` | `### Success Criteria` (SC-n with `measure:`) and `## Guardrails > ### Security and performance` |
  | `### Development Plan` | `implementation.md` steps |
  | `### Testing Strategy` | `### Test List`, each step's tests and `Verify`, and `## Exit criteria` |
  | `### Integration Context` | `## Grounding > ### Build on` and `### Leave alone`, and `### Collaboration And Wiring` |
  | `### Implementation - Additional Sections` | the brief section it belongs to |
  | the domain H2 placeholders (`Data Models`, `API Design`, `Security Architecture`, `Performance Requirements`, `Deployment Architecture`, `CLI Commands`; pre-phase-2 `phase_command.py:45-52`) | seams and contracts go in `### Skeleton Index` and `#### Design Narrative`; UI goes in `#### UX Contract`; constraints go in `## Guardrails` and SC-n |

- **Accepted frozen-reader loss** (decisions.md, "respec-code and respec-patch are frozen"). Phase
  Technology Stack now finds nothing for these readers:
  - the coder, which ranks it fourth, below project config (`coder_contracts.py:216`), and falls
    back to it for commands only when `.respec-ai/config/` is absent (`:226`)
  - the reviewers, which reach it only after `project_config_context_markdown` and `stack.toml`
    (for example `src/platform/templates/agents/code_quality_reviewer.py:137`)
  - respec-patch's planner (`src/platform/templates/agents/patch_planner.py:33`)

  With project config present, the loss is low-priority context. Do not log this in deferred-issues;
  it is a recorded decision.

### 3. The `implementation.md` layout (the contract)

H2 order is as shown. The frozen contracts are listed after the block (F33).

```markdown
# Implementation Plan: <phase-name>

## Start here
### Prerequisites
- <condition> — check: `<command or path>`
### Required reading
- phase.md: Delegation Bounds; Guardrails; SD-1, SD-4; Grounding § Exemplars
### First action
- <one concrete action, normally Step 1's first file>

## Build Order
### Staging
<why this order; which steps run in parallel and why>
### Steps
#### Step 1: <title>
- **Goal:** <one-sentence outcome>
- **Context:** SD-1, G-2, `<path>` :: <Owner>.<member>, exemplar `<path>`, (per research: <pattern> from `.best-practices/<file>.md`)
- **Files:** create `<path>`; modify `<path>`
- **Depends on:** none
- **Tests to turn green:** T-1, T-2
- **Verify:** `<the [commands].test value for the language that owns these files>`
- **Done when:** <observable condition>

## Policy
### Execution Intent Policy
- Mode: … (unchanged from today's format)
### Deferred Risk Register
- DR-001 | status=… | severity=… | scope=… | reason=… (unchanged from today's format)

## Checklist
- [ ] <work item> (Step 1) (verify: `<command>`)

## Exit criteria
- `<each [commands] value that verifies the whole phase>` passes
- every T-n in phase.md's `### Test List` passes
- every SC-n holds as its `measure:` states

## Deviations
- None
```

- **Frozen and kept** (F33):
  - `## Build Order > ### Steps > #### Step N:`, with integer N contiguous from 1 (scanned at
    `src/platform/templates/commands/code_command.py:291`)
  - `## Checklist` items `- [ ] … (Step N) (verify: …)`, read in full before any coding
    (`coder_contracts.py:139`)
  - `## Policy`
  - the `(per research: … from …)` citation form (`coder_contracts.py:235`)
- **`Files` doubles as respec-code's dispatch signal.** respec-code classifies each step by the paths
  it names (`code_command.py:304-306`). A step with no paths silently defaults to backend
  (`:518`).
- **Draft and finalize fields.**
  - The architect's draft writes `Goal`, `Files` and `Depends on`, plus `### Staging`, `## Policy`
    and `## Checklist`. The Checklist stays the architect's: phase 2's draft already writes it
    (phase 2 B28), and phase 3's checks require it whenever `implementation.md` is checked
    (`implementation-section-missing`, `implementation-step-unverified`).
  - The finalizer adds `Context`, `Tests to turn green`, `Verify` and `Done when`, plus
    `## Start here`, `## Exit criteria` and `## Deviations` (`- None` when empty). It keeps every
    Checklist item, adds one for any step that has none, and makes each item's `(verify: …)` equal
    to its step's `Verify`.
  - A step holds either exactly the three draft fields or all seven, in the order shown. A partial
    step is a finding (B6). This rule needs no stage flag, and it lets a re-opened phase add a draft
    step next to finalized ones.
- **IDs are stable.**
  - Never renumber an existing T-n, SC-n or G-n, and never reuse a removed one's number. Gaps are
    allowed.
  - Steps stay contiguous (a frozen format). Only the architect's `revise` renumbers steps, and it
    updates every reference in both files when it does.
- **Field values.**
  - Each field is one bullet that starts with its bold label, exactly as shown: `- **Goal:**`,
    `- **Context:**`, `- **Files:**`, `- **Depends on:**`, `- **Tests to turn green:**`,
    `- **Verify:**`, `- **Done when:**`.
  - `Files` is `create` and `modify` items separated by `;`, each naming one backticked path.
    `create` names a path that does not exist yet. A Skeleton Index path is a `create` item: sign-off
    materializes its skeleton (create-only), and the step fills that skeleton in.
  - `Depends on` is `none`, or `Step N` items separated by commas.
  - `Tests to turn green` is T-IDs, or `none — <reason>`.
  - `Verify` holds at least one backticked command, one per language the step touches.
  - No `##` or `###` line ever appears inside a step.
- **Parallelism.** Steps whose `Depends on` are all complete run in parallel. Frozen respec-code still
  runs them in sequence, which is harmless.
- **`## Deviations`** is where implementing agents record departures from the brief, as
  `- DEV-<n> | Step <N> | expected: … | found: … | action: …`. It lives in `implementation.md`, not
  in `phase.md`, so the user-signed contract stays unchanged. The phase.md deviation protocol points
  here. Extra H2s in `implementation.md` are harmless to respec-code (F33).

### 4. Shared example constants: `src/platform/templates/phase_contract_grammar.py`

- **`BRIEF_SECTION_PLACEHOLDERS: dict[str, str]`,** keyed by `Phase.BRIEF_SECTIONS` and in that
  order. Each value is the H3 skeleton from Scope 2, with neutral placeholders.
  - Use it in `technical_phase_template`. After phase 2 there is one copy, in `phase_architect.py`
    (pre-phase-2 `phase_architect.py:18-63`). Phase 2 deletes the command's copy (pre-phase-2
    `phase_command.py:14-56`) and the six domain placeholders.
  - That copy drops every retired field, and gains `additional_sections=BRIEF_SECTION_PLACEHOLDERS`
    and a `design_shape_additional` that shows `#### Design Narrative` first.
  - The H2 shadowing guard then sees the new names, because it reads them from
    `technical_phase_template` (`tests/unit/templates/test_phase_section_references.py:21`, `:41-49`).
    Phase 2 re-points that import to the architect.
- **`IMPLEMENTATION_BRIEF_EXAMPLE: str`** replaces `implementation_plan_example` (pre-phase-2
  `phase_architect.py:73-110`, as phase 1 neutralized it).
  - It has three finalized steps. Steps 2 and 3 both depend only on Step 1, which shows parallel
    delegation.
  - It has one `DR-001` line with concrete values that match the extractor's pattern
    (`tests/support/plan_extraction.py:14-17`), for example
    `- DR-001 | status=accepted | severity=P2 | scope=global | reason=<why it is deferred>`. F36
    requires three steps and a DR line.
  - Its `Verify`, Checklist and `## Exit criteria` commands are angle-bracket placeholders that name
    the `[commands]` table, never a real command. Checks flag every one of them, by design (B4).
  - It is concrete enough for B3 and B4 to run real extraction and checks against it. It is also
    neutral: it follows phase 1's placeholder notation for paths, and `phase_contract_grammar.py` is
    in phase 1's probe.
- **Update the existing placeholders** in the same module, so that every agent is shown the Scope 2
  forms:
  - `TEST_LIST_PLACEHOLDER` gains the trailing `— T-<n>`, and drops its "see Testing Strategy"
    pointer, because that section is retired.
  - `SKELETON_INDEX_PLACEHOLDER` gets no ID.
  - `technical_phase_template` shows `success_criteria` in the `SC-<n>: … — measure: …` form, and
    `settled_design_decisions` in the canonical SD form with `affects=`.
- **Update the import** at `tests/unit/templates/test_phase_implementation_plan_gate.py:25`. Its
  tests at `:62` and `:71` keep passing against the new constant.
- **Sharing.** The finalizer imports both constants from this module. The architect imports both
  and is told which step fields and sections it writes in `draft` (Scope 3's draft fields, plus
  `## Checklist`). Neither template restates the layout in its own words.

### 5. Structural checks for the brief: extend phase 3's `src/utils/phase_structure.py`

Phase 3 built the module, the result models, the `validate_document` input for `implementation.md`
(`implementation_markdown`) and the wiring. This phase extends `check_phase_structure`,
`check_implementation_structure` and `extract_cited_paths`, adds one function
(`extract_implementation_paths`), adds check IDs to phase 3's `StructuralCheck`, and adds no new
tool parameter. Unit-test every check in
`tests/unit/utils/test_phase_structure.py`. Phase 3's rules carry over unchanged:
- Pure functions, no I/O, never raise. A malformed heading, a step with no fields or a missing
  section is a finding (B9).
- Each finding has exactly one correct fix, and its `detail` names that fix and no language.
- Check IDs are a contract: prompts cite them, tests assert on `check` and `subject`.
- When unsure, don't flag.

**Who repairs what.** Phase 3 gives every finding an `owner`, and its Step 9 gate, the architect's
self-check and the critic route by it. The architect never writes the finalizer's sections, so a
finding about them must never reach the architect: it would burn the repair budget and land on the
user. Add `FINALIZER = 'finalizer'` to `FindingOwner`, and compute it, never guess it (B18):
- A `phase.md` finding is `finalizer`-owned when its `location` starts with `Grounding`,
  `Behaviors & Acceptance` or `Guardrails`, or its `check` is `success-criterion-malformed`.
- An `implementation.md` finding is `finalizer`-owned when its `location` names a finalize-only
  section or field: `Start here`, `Exit criteria`, `Deviations`, `Context`, `Tests to turn green`,
  `Verify` or `Done when`. This replaces phase 3's "every `implementation.md` finding is
  `architect`" for those findings only.
- Phase 3's ownership rules for `orchestrator` are unchanged and take precedence.

Routing then needs no new mechanism:
- Phase 3's Step 9 gate builds its two lists from `owner: architect` and `owner: orchestrator`, so
  `finalizer` findings fall in neither and are ignored there. The architect's self-check fixes only
  `owner: architect`. The design-review critic relays only `owner: architect` implementation
  findings (Scope 8).
- In Step 10.5 (Scope 9), `architect` and `finalizer` findings go to the finalizer. An `architect`
  finding there means a section the finalizer reproduces has drifted, and the fix is to restore it.
  `orchestrator` findings go to `STRUCTURAL_LEFTOVERS`, as in phase 3.
- State the ownership rule once, in the README "Brief format (phase 4)" subsection.

Set `part` on each new finding to the faulty element (an H3 name, a field label, a step number, a
command), as phase 3 does, because accept-as-is SDs match on `<check> <subject> [<part>]`.

**`phase.md`** (`check_phase_structure`, reported in `structural_findings`). `location` is the
heading path of the offending section, as in phase 3:

| # | `check` | Fires when |
|---|---|---|
| 1 | `delegation-bounds-incomplete` | `## Design Shape` has content and `## Delegation Bounds` is absent, lacks one of its three H3s, or has an empty one (an empty H3 holds exactly `- None`). Owner `architect`. (B5) |
| 2 | `brief-section-incomplete` | One or two of Grounding, Behaviors & Acceptance and Guardrails are present (`location` names each missing one), or a present one lacks a required H3 from Scope 2 or has an empty one. Owner `finalizer`. (B5) |
| 3 | `test-entry-without-id` | A Test List entry has no trailing `— T-<n>` outside the backticks. A repeated `T-n` is phase 3's `duplicate-id`, extended to the T family. Owner `architect`. (B7) |
| 4 | `success-criterion-malformed` | At least one of the finalizer's three H2s is present, and a `### Success Criteria` entry does not start with `SC-<n>:` or has no `measure:` part. A repeated SC-n or G-n is `duplicate-id`. Owner `finalizer`. (B7) |
| 5 | `dangling-reference` (extended) | Phase 3's ID-integrity table gains three families, scanned **only** in the four brief H2s, `## Design Decisions` and `### Success Criteria` (a whole-document scan would flag ordinary prose such as a product name ending in `-7`). T is defined by a Test List entry's trailing `— T-<n>`; SC by a column-0 `- SC-<n>:` in Success Criteria; G by a column-0 `- G-<n>:` in Guardrails. A reference is a `T-<n>`, `SC-<n>` or `G-<n>` token at word boundaries, and numbers compare as integers. Phase 3's scan already covers `OD`, `SD`, `CQ`, `RP` and `FLOW` references. Keep phase 3's exemption: no token inside an SD entry is a reference, so an SD's `affects=` and a non-ID `supersedes=` such as respec-code's `supersedes=<qualified seam>` (`src/utils/design_conformance.py:287`) are never flagged. They are orchestrator-owned history that nobody can repair; the IDs are checked earlier, on the open OD's `Affects:` line, where the architect can fix them. The owner follows the `location` rule above. (B7) |
| 6 | `research-copies-disagree` | `## Grounding` is present, and the backticked path set under its `### Research to read` differs from the `- Read:` path set in `### Research Requirements`. `location` is `Grounding > Research to read`; `subject` names each path that is in only one. Owner `finalizer`. (B8) |

Phase 3 already reports an overlapping H2 name (`section-name-overlap`, phase 3 B12). Do not add a
second check for it.

Add `affects` to phase 3's known SD keys (phase 3 work item 2, "SD entries"). Otherwise the parser
appends the `affects=` segment to the preceding `rejected` value. `affects` is never required by the
per-source table: phase 3 cannot tell whether an OD had an `Affects:` line, and B14 pins the writer
instead.

**Text under a mapped H2 before its first H3** (judgment call 6) is content loss, not structure.
Add it to phase 3's `Phase.find_content_loss` override (phase 3 work item 4): for each H2 in
`Phase.HEADER_FIELD_MAPPING` other than `Metadata`, any non-blank line between the H2 and its first
`### ` line is reported as `<H2>: text before the first subsection is dropped on parse`. Phase 3
already routes that to the user on a hand edit and to the writing agent as `CONTENT_LOSS_WARNING`
on `update_document`. (B17)

**`implementation.md`** (`check_implementation_structure(markdown, phase)`, reported in
`implementation_findings`). Phase 3 already reports missing `## Build Order > ### Steps`,
`## Checklist` or `## Policy`; malformed step headings; no steps; duplicate step numbers; a
Checklist item without `(Step N)` or `(verify: …)`, or naming an unknown step; and a step no
Checklist item names. Add:

Each new finding's `location` is the heading path, ending in the field label for a step field, for
example `implementation.md > Step 2 > Verify` or `implementation.md > Exit criteria`. Its owner
follows from it (above).

| # | `check` | Fires when |
|---|---|---|
| 7 | `implementation-steps-not-contiguous` | The integer step numbers are not exactly 1…n (frozen respec-code scans them, `src/platform/templates/commands/code_command.py:291`). (B6) |
| 7 | `implementation-section-missing` (extended) | `## Policy` lacks `### Execution Intent Policy` or `### Deferred Risk Register`. (B6) |
| 8 | `implementation-step-fields-incomplete` | A step's field bullets, in order, are neither exactly `Goal`, `Files`, `Depends on` nor exactly all seven of Scope 3. Name the missing or misplaced label. (B6) |
| 8 | `implementation-step-files-missing` | A step's `Files` names no backticked path. respec-code classifies steps by these paths, and a step with none silently defaults to backend (`code_command.py:304-306`, `:518`). (B6) |
| 8 | `implementation-dependency-invalid` | `Depends on` names a step that does not exist, the step itself, or forms a cycle. Name the steps in the cycle. (B6) |
| 9 | `implementation-command-placeholder` | A step's `Verify` holds no backticked command, or any backticked command in a step's `Verify` or under `## Exit criteria` is a placeholder (rule below). (B6) |
| 10 | `implementation-finalize-section-missing` | Any of `## Start here`, `## Exit criteria` or `## Deviations` is present, or any step holds all seven fields, while another of the three is missing, `## Start here` lacks one of its three H3s, or `## Exit criteria` has no backticked command. (B6) |
| 11 | `dangling-reference` (extended) | An ID in a step's `Context` or `Tests to turn green` is undefined in the phase (T, SC and G families as in check 5; phase 3 already resolves the others). A `Step N` token in the four brief H2s or on an open OD's `Affects:` line names no step. SD entries stay exempt, as in check 5. (B7) |
| 11 | `seam-path-not-in-any-step` | A `### Skeleton Index` path appears in no step's `Files`. Read the path with the bullet grammar phase 3 promoted from `src/utils/skeleton_generator.py:16` into `src/utils/skeleton_types.py`. Never parse the signature (F24). Compare after stripping a leading `./`. (B7) |
| 11 | `test-not-in-any-step` | Every step holds all seven fields, and some Test List `T-n` appears in no step's `Tests to turn green`. (B7) |

**The placeholder rule** is one shared predicate. Extract it from phase 3's Checklist rule and use it
for step `Verify`, `## Exit criteria` and the Checklist `(verify: …)` groups, so the three never
disagree. A command is a placeholder when it:
- is empty after stripping, or starts with `TODO` in any case, optionally bracketed (phase 3's rule;
  phase 1's config validation reads the same values as missing, `_is_incomplete_value`,
  `src/platform/standards_config.py:331-333`)
- is `no_preference` (F25)
- is wholly a `[…]` placeholder (phase 3's rule)
- contains an angle-bracket placeholder token, matching `<[A-Za-z](?:[^<>]*[^\s<>])?>`. This matches
  `<command>` and `<the [commands].test value>`, and does not match shell redirection such as
  `cmd < in > out`.

A command that starts with `ask user` is phase 1's marker for a language with no configured command
(phase 1 item 7). It is never a placeholder, here as in phase 3.

Widening phase 3's Checklist rule from "wholly `<…>`" to "contains a `<…>` token" keeps phase 3's
existing tests green, because every input they flag is still flagged. Checklist placeholders keep
phase 3's `implementation-checklist-item-malformed` ID and `part: verify`.

**Cited paths.** Phase 3's `extract_cited_paths` already returns every `.best-practices/…md` mention,
so `### Research to read` needs nothing new. Add three `CitedPathKind` values:
- `grounding`: `extract_cited_paths` also returns every backticked path under `## Grounding`'s
  `### Build on`, `### Leave alone`, `### Exemplars` and `### Conventions`, with `cited_in` set to
  `Grounding > <H3>`. The path must exist.
- `create` and `modify`: a new `extract_implementation_paths(markdown: str) -> list[CitedPath]`
  beside it returns each step's `Files` paths, with `cited_in` set to
  `implementation.md > Step <N> > Files`. A `modify` path must exist; a `create` path must not.

`PhaseTools.validate` appends the second list to `paths_to_verify` when `implementation_markdown`
is given. Existence stays host-side (phase 3, judgment call 4): the critic and the finalizer check
these paths with Glob (Scopes 6 and 8).

### 6. The finalizer agent: new file `src/platform/templates/agents/phase_finalizer.py`

**Registration.** Every site below is required; B10 fails if any one is missing.

| Site | Change |
|---|---|
| `src/platform/tool_enums.py:154-155` | add `PHASE_FINALIZER = f'{_RESPEC_AGENT_PREFIX}phase-finalizer'` after `PHASE_CRITIC` |
| `src/platform/models/phase.py:211-234` (add after `PhaseCriticAgentTools`) | add `PhaseFinalizerAgentTools(AgentToolsModel)`. Its `respec_ai_tools` are `GET_DOCUMENT`, `UPDATE_DOCUMENT`, `GET_FEEDBACK`, `GET_PREVIOUS_ANALYSIS` and `VALIDATE_DOCUMENT`. Its `builtin_tools` are `READ`, `GLOB` and `GREP`. It has one inline-call field per MCP tool, rendered with the same arguments the architect's are after phases 2 and 3: `get_document` and `get_feedback` on `{LOOP_ID}` (today `src/platform/template_helpers.py:842-847`), `update_document` on `{PLAN_NAME}/{PHASE_NAME}` (`:848-853`), `get_previous_analysis` on `{LOOP_ID}`, and `validate_document` exactly as phase 3 work item 6 renders it for the architect. |
| `src/platform/models/__init__.py:20`, `:79` | import and export it |
| `src/platform/template_helpers.py:857-886` (add next to `create_phase_critic_agent_tools`) | add `create_phase_finalizer_agent_tools(tui_adapter)`. It also adds `WRITE` scoped to `.respec-ai/plans/*/phases/*/implementation.md`, with the same call phase 2 used for the architect (`builder.add_builtin_tool(BuiltInToolCapability.WRITE, '.respec-ai/plans/*/phases/*/implementation.md')`, phase 2 work item 3). |
| `src/platform/templates/agents/__init__.py:13-14`, `:31-32` | import and export `generate_phase_finalizer_template` |
| `src/platform/template_generator.py` | import the builder beside `src/platform/template_generator.py:28-29` and the generator beside `src/platform/template_generator.py:51-52`; add `'respec-phase-finalizer'` to `_AGENT_NAMES` after `'respec-phase-critic'` (`src/platform/template_generator.py:109-131`); build its tools beside `src/platform/template_generator.py:273-276`; add its `_parse_agent_spec` entry after `src/platform/template_generator.py:302` |
| `src/platform/template_helpers.py:170-171` | `builder.add_task_agent(RespecAIAgent.PHASE_FINALIZER)` in `create_phase_command_tools` |

The agent counts follow automatically, because `expected_agents_count` is derived
(`src/platform/template_generator.py:155-156`). On codex the runtime name becomes
`respec-phase-finalizer-agent` (`src/platform/tui_adapters/codex.py:369-375`).

**If phase 2 overturned the Write grant** (its open call 1): the finalizer gets no `WRITE`. It
returns the complete `implementation.md` body in an extra final report section, and the orchestrator
writes it, exactly as phase 2 then has it do for the architect. Amend README "Agents and modes" the
same way.

**Template.** Model it on the architect's frontmatter and TOOL INVOCATION block. Use
`model: {tools.tui_adapter.reasoning_model}`, because writing quality is the job. It is always
invoked fresh and rehydrates from MCP and disk, so it needs no `SendMessage` resume on any TUI.

- **Invocation contract.**
  - Scalars: `loop_id`, `plan_name`, `phase_name`.
  - Grouped: `project_config_context_markdown`.
  - Never conversation text or document bodies (README "Agents and modes").
  - `IMPLEMENTATION_PLAN_PATH` is `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md`,
    built exactly as the architect builds it (Scope 0, amendment 1).
- **STEP 1, retrieve.**
  - Get the document, the exploration notes (`get_previous_analysis`) and **always** the feedback.
    The feedback holds critic entries and round-tagged user entries (F31); the README re-engage rule
    applies to every writing agent.
  - The notes are empty after a re-run, because each run starts a new loop (phase 2, judgment calls).
    Then find build-on, leave-alone, exemplar and convention paths with Glob and Read.
  - Read `IMPLEMENTATION_PLAN_PATH`.
- **STEP 2, choose the scope from the inputs, never from a mode.**
  - **Full pass** when none of `## Grounding`, `## Behaviors & Acceptance` and `## Guardrails` is
    present. Any architect `revise` on a document that holds them removes them (Scope 7). Write all
    three, complete Success Criteria, expand every draft-only step, and write `## Start here` and
    `## Exit criteria`. Add `## Deviations` with `- None` if it is absent; never edit its lines.
  - **Otherwise, a targeted pass.** Change only what one of these names, and leave the rest as it is:
    - every step that holds only its draft fields: expand it
    - every finding `validate_document` reports
    - every `[mechanical]` finding in the latest critic entry, when that entry starts with
      `Review target: brief`. Skip a finding that no longer holds, and skip one an SD with
      `supersedes=unresolved-checks` accepted. Ignore `Review target: design` entries; those are the
      architect's.
    - every SD whose `supersedes=` names an OD or CQ and whose ID the brief does not yet cite: cite
      it where its `affects=` points. When the user left the choice to the implementer (a CQ's
      Option A), add one line citing the SD under `### Implementer's discretion`, or under
      `### Escalate if` when the SD says to stop and ask.
- **STEP 3, verify every path before citing it** (Glob or Read):
  - A Grounding, exemplar, convention or `modify` path exists.
  - A `create` path does not exist. Skip this one when `### Shape Gate` is `shape-amended`: a
    re-opened phase already has its skeletons and earlier work on disk.
  - Research paths come only from the ledger's `- Read:` lines, never invented.
- **STEP 4, write the `phase.md` brief** per Scope 2: Grounding, Behaviors & Acceptance, Guardrails,
  and the `measure:` parts and coverage additions in Success Criteria.
  - **MANDATORY:** reproduce verbatim the Overview, Module Layout, Skeleton Index, Collaboration And
    Wiring, Test List, Design Shape - Additional Sections (Design Narrative and UX Contract), Design
    Decisions, Delegation Bounds, Implementation Plan References and Research Requirements.
  - **The one exception:** add the Delegation Bounds lines STEP 2 names for SDs settled at sign-off.
  - Copy `## Metadata` as retrieved. Phase 2's storage rule keeps `### Shape Gate` whatever is sent.
- **STEP 5, expand `implementation.md`** per Scope 3.
  - **MANDATORY:** keep the reviewed step numbers, titles, `Goal`, `Depends on`, the paths in
    `Files`, the `### Staging` text and `## Policy`. The one correction allowed is a path's `create`
    or `modify` verb, flipped to match whether the path exists (STEP 3); the path itself never
    changes. If a step cannot be made self-contained without changing them, return a
    `## Decisions needed` entry instead of changing them.
  - **Constraint carry-forward:** keep every constraint citation the draft made (phase 2 moved that
    obligation into `draft`; `tests/unit/templates/test_phase_implementation_plan_gate.py:89`, F36),
    and cite each `- Constraint:` path in the `Context` of every step it binds.
  - Keep every Checklist item, add one for a step that has none, and make each item's
    `(verify: …)` equal its step's `Verify`.
- **STEP 6, commands.** `Verify`, Checklist and `## Exit criteria` commands come only from the
  `[commands]` table in `project_config_context_markdown` (keys `test`, `coverage`, `type_check`,
  `lint`), for the language that owns the files, or from an SD in which the user supplied one. Never
  write a guess. When a language has no usable command (phase 1's rule: no standards file, or a value
  that is empty, starts with `TODO` or is `no_preference`):
  - Write phase 1's exact marker wherever the command goes:
    `ask user — no test command configured for <language>; set [commands].test in .respec-ai/config/standards/<language>.toml`
    (phase 1 item 7), and add a `### Prerequisites` line under `## Start here` naming the language.
  - If no SD records the user's choice for that language (the briefing asks it, phase 2 work item
    5), also return a `## Decisions needed` entry: Option A, supply the command now; Option B, keep
    the marker, and the implementing agent asks for the command. Recommended: B. Set
    `result: needs-user`.
    - There is no "set `[commands].test` and re-run" option here, unlike the briefing's: Step 11 has
      no route that ends the run, and the marker already names the TOML to edit later. Never point
      to `/respec-standards`: it never edits canonical TOML (phase 1, item 7).
- **STEP 7, store and self-check.**
  - Write `IMPLEMENTATION_PLAN_PATH`, then call `update_document` for `phase.md`. If its response
    contains `CONTENT_LOSS_WARNING` (imported, not retyped; phase 3 work item 1), rewrite the named
    headings and update again.
  - Call `validate_document` in key mode with `implementation_markdown` set to what it wrote. Fix
    every `owner: finalizer` finding. Treat an `owner: architect` finding as drift in a section it
    reproduces, and restore that section from the retrieved document. Leave `owner: orchestrator`
    findings untouched. Glob every `paths_to_verify` entry: a missing `grounding` path is corrected
    or its line removed, and a `create` or `modify` path with the wrong verb gets the other verb
    (STEP 5). Repeat at most twice.
    The orchestrator's gate and the critic are the authority, not this self-check (phase 3 work
    item 8).
- **STEP 8, report** in the README's four-section format with `mode: finalize`.
  - `## For the user` is a short summary: sections written, number of steps, parallel groups, gaps.
    Never bodies.
  - `## Decisions needed` uses `OD-NNN` IDs numbered above every OD and SD number in the document,
    in the canonical form with an `Affects:` line. They live only in the report (Scope 0,
    amendment 2).
  - `## Research proposals` is always `- None`. Research after design approval would break the
    touchpoint budget and the cost invariant.
- **MANDATORY blocks, stated in the prompt** because opencode and codex do not enforce them (F14):
  - It writes only `IMPLEMENTATION_PLAN_PATH` and, through `update_document`, the phase document.
  - It never asks the user anything; questions go in `## Decisions needed` (F10).
  - It names no language.

### 7. The architect (post-phase-2 `phase_architect.py`)

- **`draft` and `revise`:**
  - Write `## Delegation Bounds` and `#### Design Narrative` (first under
    `### Design Shape - Additional Sections`, never as text directly under `## Design Shape`).
  - Give every Test List entry a trailing `T-n`.
  - Write `### Success Criteria` entries in the `SC-<n>:` form, covering every objective, scope item
    and deliverable.
  - Cite seams as `` `<path>` :: <Owner>.<member> ``.
  - Write the `implementation.md` draft with the draft fields from Scope 3, `### Staging`,
    `## Policy` and `## Checklist`.
  - Never write Grounding, Behaviors & Acceptance or Guardrails, and never write `## Start here`,
    `## Exit criteria` or the four finalize step fields.
- **`revise` after a finalize.** This happens when the user goes back to design review from
  sign-off, on a re-opened phase (`shape-amended`), or when a run resumed after Step 10.5 had run:
  - Remove `## Grounding`, `## Behaviors & Acceptance` and `## Guardrails` entirely, so the
    finalizer does a full pass after the next approval (Scope 6, STEP 2). This is the only change the
    architect makes to them.
  - A step whose `Goal`, `Files` or `Depends on` changes goes back to exactly its three draft fields,
    so the finalizer regenerates the rest. Unchanged finalized steps are kept.
  - `## Start here` and `## Exit criteria` stay as they are; the finalizer rewrites them.
  - `## Deviations` lines are never edited. They are the implementers' record, and they are design
    input for the re-open.
- **`explore`.** The complete exploration notes (one slot, every write is the full notes, F31) carry
  four lists of verified paths: build-on, leave-alone, exemplar and convention locations. The
  finalizer cites from these instead of re-exploring, when they survive (Scope 6, STEP 1).
- **Remove every remaining instruction to write a retired section** (Scope 2). Find them with:

  ```bash
  grep -n -E "Functional Requirements|Non-Functional|Development Plan|Testing Strategy|Integration Context|Technology Stack|### Architecture|Data Models|API Design" src/platform/templates/agents/phase_architect.py src/platform/templates/commands/phase_command.py src/platform/templates/agents/phase_critic.py
  ```

- **Update `tests/unit/templates/test_phase_design_layer.py:35` if the string is still present.** It
  asserts the literal `'Objectives, Scope, Deliverables, Development Plan'`. The path-free scope is
  now the Overview fields only. Paths are required in the design layer, `## Grounding` and step
  `Files`.

### 8. The critic (post-phase-2 `phase_critic.py`)

The `review` branch splits on the new scalar `review_target`, with branch headers written as
`IF review_target == "design":` and `ELIF review_target == "brief":`, so a test can extract each body
the way `_phase_mode_branch_body` does. Both branches store feedback whose first line is
`Review target: design` or `Review target: brief` (Scope 0, amendment 4).

- **`design`** is phase 2's check set, plus phase 3's relay, unchanged except for one filter. On a
  document that already holds finalize-only content (a re-opened or resumed phase), it raises no
  finding about that content, and it relays only `owner: architect` implementation findings (Scope
  5). Phase 3 left two phase 2 critic checks for phase 4 to replace (phase 3, Out of scope):
  - "every `#### Step N:` names the files it touches": delete it from the critic.
    `implementation-step-files-missing` (Scope 5) now reports it on both targets.
  - "every Test List entry is covered by some step": keep it in `design`, because draft steps carry
    no test IDs yet. `brief` does not carry it; `test-not-in-any-step` reports it there.

  Delegation Bounds specificity is deliberately
  not a critic check. It has no single correct fix, so it cannot be `[mechanical]`, and the user
  reviews the bounds at design review anyway (judgment call 3).
- **`brief`** runs only the checks below. It carries **none** of the design-review rules, judgment
  or mechanical: unjustified seam, under-surfaced decision, non-divergent options, plan constraint
  violation, implementation plan reference not applied, the UX Contract rules and the frontend
  decision classes. The user settled those at design review, and the finalizer never changes the
  sections they cover. (B13)

The `brief` checks:

0. **Phase 3's host checks.** Call `validate_document` in key mode with `implementation_markdown`
   set to a Read of `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md`. Relay each
   `owner: architect` and `owner: finalizer` `implementation_findings` entry exactly as phase 3
   writes it: `[mechanical] [Implementation Plan Structure Invalid - BLOCKING]: <check> <subject>
   [<part>] — <detail>`, dropping ` [<part>]` when `part` is empty. Never re-raise
   `structural_findings`; the Step 10.5 gate owns them.
1. **Cold-start check.** For each `#### Step N:`, take only that step's brief, the `phase.md`
   sections its `Context` cites, and the repository. List every point where a fresh agent would
   have to guess. Classify each:
   - **`[mechanical]`:** the answer exists in the brief or the repository but is not cited.
     Examples: a missing pointer, a file missing from `Files`, a missing T-n, an undeclared
     dependency on a file another step creates, a `Verify` value that does not match the config.
     These go to `### Blockers`.
   - **Not a gap:** a `Verify` that is phase 1's `ask user` marker, when an SD records the user's
     choice for that language or the finalizer's report already asks it. Raising it again would
     repeat a question the user has answered or is about to answer.
   - **`[judgment]`:** the answer needs a choice nobody made. Examples: unspecified error behavior,
     ambiguous seam semantics, a missing non-functional target. These go to `### Key Issues` and
     become `CQ-NNN`, where Option A is "leave it to the implementer's discretion (recorded under
     Delegation Bounds)" and Option B is "settle now: <the critic's proposal>". This fits the README
     rule that Option A is "keep as designed". Reuse a CQ ID for the same finding across rounds
     (phase 2, judgment calls).
2. **Reviewed sections are unchanged.** Compare the sections the finalizer must reproduce (Scope 6,
   STEP 4) between `phase_file_path` and `get_document`. The file on disk is the draft the user
   approved, because Step 10.5 writes it before the finalizer runs (Scope 9).
   - Any difference is `[mechanical]`, as `[Reviewed Section Changed - BLOCKING]`. The finding names
     the section and quotes the approved text, so the finalizer restores it without reading the disk
     copy.
   - `### Success Criteria` is append-only: added `SC-<n>` entries and completed `measure:` parts
     are not differences; an edited, removed or renumbered criterion is.
   - If `phase_file_path` cannot be read (phase 2: the draft-on-disk guarantee covers only the
     markdown platform), skip this check and say so in the feedback. Never report it as passed.
3. **Paths.** Glob every `paths_to_verify` entry from check 0, choosing the marker by `kind`, as
   phase 3 does for its kinds. Each failure is one `[mechanical]` blocker:
   - a missing `grounding` path: `[Grounding Path Invalid - BLOCKING]`; the finalizer corrects or
     removes the line
   - a missing `modify` path, or an existing `create` path: `[Step File Verb Invalid - BLOCKING]`;
     the finalizer flips the verb (Scope 6, STEP 5). Skip the `create` half when `### Shape Gate` is
     `shape-amended` (Scope 6, STEP 3).

   These need the project, so they run here and not on the server (F29).
4. **Commands.** Every `Verify` value equals the `[commands]` value for the owning language in
   `project_config_context_markdown`, the command an SD records, or phase 1's `ask user` marker when
   that language has no usable command. A mismatch is `[mechanical]`. This is the same match phase 3
   leaves the critic for Checklist commands (phase 3 work item 9).
5. **Coverage.**
   - The SC-n entries cover every objective, scope item and deliverable. A gap is `[mechanical]`;
     the finalizer appends the missing criterion.
   - Each SC-n is measurable. An unknown target value is `[judgment]`: the user supplies the number.

A finding settled by an SD (`supersedes=CQ-…`, or `supersedes=unresolved-checks`) is never raised
again (README "Critic findings").

### 9. The orchestrator (post-phase-2 `phase_command.py`, `template_helpers.py`, `PhaseCommandTools`)

**New `PhaseCommandTools` fields** (`src/platform/models/phase.py:14`), rendered in
`create_phase_command_tools` (`src/platform/template_helpers.py:160`). The names follow phase 2's
`invoke_architect_*` / `invoke_critic_review` convention:
- **`invoke_finalizer`:** `adapter.render_agent_invocation('respec-phase-finalizer', 'write the
  agent-ready brief and step delegation briefs for the approved design', …)`, with the Scope 6
  inputs. The description is user-visible prompt text on opencode (README "Agents and modes"), so it
  names no language.
- **`invoke_critic_brief_review`:** the critic with its usual IDs plus `phase_mode: review`,
  `review_target: brief`, `review_round`, `phase_file_path` and `project_config_context_markdown`.
- **`brief_handoff_extension`:** see Scope 10.

Also add `review_target: design` to phase 2's `invoke_critic_review` (Scope 0, amendment 1).

**`IMPLEMENTATION_PLAN_PATH`.** Phase 2's Step 3 sets it as
`dirname(PHASE_FILE_PATH)/implementation.md`, the derivation frozen respec-code uses
(`code_command.py:230-231`). Confirm that it is set before Step 10.5. On the markdown platform it is
the file the architect and the finalizer write. Step 11 and the handoff use it.

**Step 10.5: Finalize the Brief.** A new step between Step 10 and Step 11. Phase 2's tests anchor on
step numbers, so add it as `10.5` and renumber nothing. Step 10's "approve the design and go to
sign-off" choice goes to Step 10.5, not to Step 11. The step has no touchpoint token and no `WAIT for` (B12; phase 2 B10).
0. Set `REPAIR_ROUNDS = 0`, `STRUCTURAL_LEFTOVERS = []` and `BRIEF_QUESTIONS = []`. Write the current MCP document
   (`get_document`) to `PHASE_FILE_PATH`, the same way Step 10 writes each review iteration.
   - The critic's reviewed-sections check compares against this copy. Step 10 may have recorded SDs
     after its own disk write, so without this write the critic would ask for them to be
     "restored" away.
   - This write cannot clobber a hand edit: phase 2's Step 10 re-reads the disk before acting on any
     choice, and runs the hand-edit path (then Step 9) when the file differs from what it wrote.
1. Invoke the finalizer with `{tools.invoke_finalizer}`, and wait for its report.
   - `failed` or a malformed report: stop with the detail shown (fail-closed).
   - `needs-user`: its `## Decisions needed` join `BRIEF_QUESTIONS`, the sign-off queue.
2. Run `{tools.validate_document_structure}`, phase 3's key-mode gate call. It carries no
   `implementation_markdown`: the orchestrator never holds that body (phase 3, "Why the critic
   verifies cited paths"). Implementation findings reach the orchestrator through the critic's relay
   in step 3, and the finalizer has already self-checked. Write `structural_findings` literally, as
   phase 3 does.
   - `FINALIZER_FINDINGS` = the `structural_findings` whose owner is `finalizer` or `architect`
     (Scope 5). `ORCHESTRATOR_FINDINGS` = those whose owner is `orchestrator`.
   - If `FINALIZER_FINDINGS` is not empty and `REPAIR_ROUNDS < 2`: `REPAIR_ROUNDS += 1`, invoke the
     finalizer again with `{tools.invoke_finalizer}`, and return to this step. No user prompt is on
     this path.
   - Otherwise `STRUCTURAL_LEFTOVERS` = every finding in both lists, written exactly as phase 3's
     gate writes it (`<check> <subject> [<part>] — <detail>`), so an accept-as-is SD matches it on
     later rounds.
3. `REVIEW_ROUND += 1`, then invoke the critic with `{tools.invoke_critic_brief_review}`. Keep phase
   2's fail-closed persistence checks. Then `BRIEF_REVIEW_DECISION = decide_loop_next_action`:
   - `completed`: go to Step 11.
   - `refine` or `user_input` while `REPAIR_ROUNDS < 2`: `REPAIR_ROUNDS += 1`, invoke the finalizer
     (never the architect), and return to step 2. `user_input` is repaired like `refine`, as in
     phase 2's Step 9: the score-stagnation rule can return it before any repair has run (phase 2,
     B18).
   - `refine` or `user_input` with no repair rounds left: set `UNRESOLVED_CHECKS` =
     `STRUCTURAL_LEFTOVERS` + the latest `### Blockers`, and go to Step 11. A `completed` decision
     with non-empty `STRUCTURAL_LEFTOVERS` sets `UNRESOLVED_CHECKS = STRUCTURAL_LEFTOVERS` (phase 3's
     rule for Step 9).
   - Give `user_input` its own `ELIF BRIEF_REVIEW_DECISION == "user_input":` branch holding both
     cases, as phase 2 does in Step 9.
   - Any other value ends the workflow (fail-closed).
   - Add the critic's `CQ-NNN` entries to `BRIEF_QUESTIONS`.
4. No `bp-pipeline` invocation, and no route to Step 7, anywhere in Steps 10.5, 11 or 12. Research is
   reachable again only through Step 11's "go back to design review" (B13).

**Step 11 (Sign-off)** stays touchpoint 3:
- Show the finalizer's `## For the user`, then `UNRESOLVED_CHECKS` as one decision (accept as-is, or
  go back to design review), then the queued decisions: the finalizer's ODs and the brief review's
  CQs, kept in their own list (`BRIEF_QUESTIONS`) apart from any architect OD or design-review CQ
  still open. The portable core asks one per prompt; Claude Code batches up to
  `selection_batch_limit` per call (phase 2).
- **`BRIEF_QUESTIONS` answers never go to the architect.** Phase 2's Step 11 sends an answer that
  changes the design back through `revise`, Step 9 and Step 10. That rule stays for architect ODs and
  design-review CQs. A `BRIEF_QUESTIONS` answer, including a CQ's Option B, binds a step, a
  guardrail or a criterion, all of which the finalizer owns, so the finalizer applies it (next
  bullet). A user who wants the design itself changed picks "go back to design review".
- Record each OD or CQ answer as an SD with `affects=` (B14). An accept-as-is answer to
  `UNRESOLVED_CHECKS` is phase 2's `supersedes=unresolved-checks` SD, quoting each finding as written.
- If this step recorded any SD that supersedes an OD or CQ, invoke the finalizer **once** more, then
  the key-mode gate **once**.
  Do not invoke the critic again: re-running it after the user decides is the cycle this effort
  removed. If the gate still reports findings, ask them as one unresolved-checks decision in this
  same step, guarded so it appears only then. It adds no touchpoint.
- Then continue with phase 2's Step 11: its single sign-off prompt, then, in phase 2's order, the
  `implementation.md` existence check, materialization, one `store_document` carrying the
  constraint line and `shape-settled`, the final write of `phase.md` to disk, and the commit offer.
  "Go back to design review" returns to Step 10. The architect's next `revise` then removes the
  finalizer's sections (Scope 7), and Step 10.5 runs again after the next approval.
- **One change to that sequence:** if the existence check finds `implementation.md` missing,
  re-engage the architect in `revise` once, as phase 2 does, but then go to Step 9 instead of
  continuing the sign-off. The finalizer cannot rebuild the file, because the draft fields,
  `### Staging`, `## Policy` and `## Checklist` are the architect's (Scope 3). That `revise` also
  strips the finalizer's sections (Scope 7), so the design passes review and Step 10.5 again before
  sign-off. If the file is missing again when Step 11 is next reached, fail closed.

**Every SD writer** for an answered OD or CQ includes `affects=`, in Steps 6, 10 and 11.
Pre-phase-2 examples are at `phase_command.py:573-574` and `:580-581`.

**Step 12's storage banner** (phase 2 rewrites it to name every disk write) also names Step 10.5's
write of `PHASE_FILE_PATH` and the finalizer's `implementation.md`.

**The handoff** (Scope 10) is shown in Step 12, and in Step 4's `shape-settled` branch when the user
chooses the handoff instead of re-opening (README "Stage marker").

### 10. The TUI-tiered handoff

- **`src/platform/tui_adapters/base.py`.** Add a property `brief_handoff_extension -> str | None`
  returning `None`, next to `subagent_invocation_guardrail`
  (`src/platform/tui_adapters/base.py:77-79`). It follows the pattern of
  `ask_user_question_tool_name` (`src/platform/tui_adapters/base.py:39-46`). It is not a
  `BuiltInToolCapability`: it grants no tool, it only renders text.
- **`src/platform/tui_adapters/claude_code.py`.** Override it beside the guardrail property
  (`src/platform/tui_adapters/claude_code.py:47-49`), returning a plain (non-f) string. opencode and
  codex inherit `None`, which is the declaration point; build nothing for them (memory: TUI
  capability tiering).
- **Wiring.** `create_phase_command_tools` stores `adapter.brief_handoff_extension or ''`. The
  command template builds the extension block in Python before the f-string, and includes it only
  when the value is non-empty. This is the same pattern as the architect's Design Sync note.
- **The portable core, on every TUI**, shown as rendered. In the f-string, write the runtime
  variables as `{{PHASE_FILE_PATH}}` and `{{IMPLEMENTATION_PLAN_PATH}}`;
  `{tools.code_command_invocation}` is the only real interpolation.

  ```text
  Brief ready.
  - Contract: {PHASE_FILE_PATH}
  - Plan:     {IMPLEMENTATION_PLAN_PATH}
  Hand implementation.md to your coding agent. It starts at "## Start here"; every step under
  "## Build Order > ### Steps" is a self-contained brief with its own Verify command.
  Or run the respec-code workflow: {tools.code_command_invocation}
  ```

- **The Claude Code extension**, printed as a ready-to-run instruction for a fresh session:

  ```text
  Implement {IMPLEMENTATION_PLAN_PATH}, using {PHASE_FILE_PATH} as the contract.
  1. Read "## Start here" and complete it first.
  2. Work through "## Build Order > ### Steps". Whenever several steps have every step in their
     "Depends on" complete, run them in parallel, one subagent per step. Give each subagent only
     that step's brief and the phase.md sections and IDs its "Context" cites.
  3. When a subagent returns, run the step's "Verify" command yourself and confirm "Done when"
     before starting any step that depends on it. Only then tick its "## Checklist" item. If a
     "Verify" value starts with "ask user", ask me for the command first.
  4. Stop and ask me if any condition under "## Delegation Bounds > ### Escalate if" occurs.
     Record any deviation under "## Deviations", as "## Guardrails > ### Deviation protocol" says.
  5. Finish by running every command under "## Exit criteria".
  ```

- **respec-code stays offered** through `{tools.code_command_invocation}`
  (`src/platform/models/phase.py:59`) until its retirement is decided.

### 11. Tests that change

- **`tests/unit/templates/test_agent_templates.py:660-679`** (`TestAgentImperativeLanguageAudit`,
  the `templates` list): add the finalizer to the audited templates (F36).
- **`tests/unit/templates/test_phase_language_neutrality.py`:** add the B16 coverage assertion. The
  guard already scans the finalizer by its `respec-phase-` prefix (phase 1, Scope item 1).
- **Phase 2's `tests/unit/templates/test_phase_relay_guards.py`** (B5, no agent declares the
  question tool): if it lists agents explicitly, add the finalizer.
- **Phase 2's `tests/unit/templates/test_phase_cooperative_flow.py`** (B8, the four-section
  report): add the finalizer's template.
- **Phase 3's `tests/unit/templates/test_phase_structural_gate.py`** (B16): add the finalizer to "agents
  invoke only the MCP tools they declare". Rewrite B16's "relays every `implementation_findings`
  entry" half to Scope 8's per-target rule: `owner: architect` only on `design`, `architect` and
  `finalizer` on `brief`.
- **Phase 3's B18 tests** (computed ownership): if they pin "every `implementation.md` finding is
  `architect`", narrow that to findings outside the finalize-only locations, which are now
  `finalizer` (Scope 5, B18).
- **`tests/unit/templates/test_phase_implementation_plan_gate.py:25`:** update the import (Scope 4).
- **`tests/unit/templates/test_phase_design_layer.py:35`:** see Scope 7.
- **New tests**, colocated with their precedents:
  - B1 in `tests/unit/models/test_phase_additional_sections.py`
  - B2–B4 in a new `tests/unit/templates/test_phase_brief_format.py`
  - B5–B9 and B18's ownership half in phase 3's `tests/unit/utils/test_phase_structure.py`, and
    B18's routing half in phase 3's `tests/unit/templates/test_phase_structural_gate.py`
  - B17 in `tests/unit/models/test_content_loss_detection.py`
  - B10 and B11 in a new `tests/unit/templates/test_phase_finalizer.py`
  - B12–B14 in a new `tests/unit/templates/test_phase_brief_review.py`
  - B15 in a new `tests/unit/templates/test_phase_handoff.py`

### 12. Documents

- README "Shared contracts", per Scope 0.
- README phase 4 probe: it already carries this document's two-part "Already done?" command.
  Confirm it prints a match.
- Add the "text under a mapped H2 is dropped and not reported" probe (judgment call 6) to
  findings.md as **F40**, and cite it from the README's "Section naming" bullet. Update every
  "F1–F39" range and the "39 verified findings" count in README.md, decisions.md and findings.md.
- Log anything found but out of scope in [deferred-issues.md](deferred-issues.md).

## Out of scope

- **Destructive removal** of the retired `Phase` fields, their `HEADER_FIELD_MAPPING` entries and
  their columns. That is the planned follow-up migration. This phase only stops generating them; a
  hand-written section still round-trips.
- **Updating respec-code or respec-patch readers** (decisions.md). Phase 4 keeps their formats; it
  does not teach them the new sections. The one sanctioned respec-code edit,
  `code_command.py:221`, belongs to phase 2.
- **Deciding whether to retire respec-code**, respec-patch or the conformance reviewer.
- **Making `implementation.md` a `DocumentType`** (decisions.md rejects it), or adding a second input
  path for it. Scope 5 reuses phase 3's `implementation_markdown`.
- **Changing the parser's substring matching or `---` truncation.** This phase avoids the traps by
  naming and hygiene, and reports them through checks (F27).
- **Changes to the relay protocol, the stage marker, the research flow or the materialize CLI.**
  These belong to phase 2. Phase 4 adds Step 10.5, the sign-off additions in Scope 9, the
  architect's post-finalize `revise` rule (Scope 7) and the handoff, and nothing else to the flow.
- **Handoff extensions for opencode or codex.** Each gets the declaration point (`None`) only.
- **Enforcing the `implementation.md` write scope on opencode or codex** (F14, decisions.md caveat).
- **Re-running design judgment, or research, after design approval.**

## Exit criteria

- [ ] B1–B18 each observed failing first, for the right reason, then passing.
- [ ] `uv run pytest` is green. Phase 2 removes tests, so compare against the count phase 3 left,
      not the README's 2026-11-13 baseline.
- [ ] The guard tests pass on all three TUIs, the finalizer included: language neutrality, no
      question tool in any agent, no `context: fork`, and H2 shadowing. Each guard's negative
      self-test fires.
- [ ] `uv run respec-ai regenerate --force --tui all` completes in a scratch project, with model
      tiers configured for opencode and codex first (F37). Inspect the output directly:
  - Claude Code: the finalizer agent file exists, its `tools` hold
    `Write(.respec-ai/plans/*/phases/*/implementation.md)` and no `AskUserQuestion`, and
    `respec-phase.md`'s `allowed-tools` holds `Task(respec-phase-finalizer)`.
  - opencode: `permission.task` allows the finalizer.
  - codex: an agent named `respec-phase-finalizer-agent` exists, and the command invokes that name.
- [ ] The completion probe in **Start here** reports "done".
- [ ] **Manual:** run a real phase end to end on a scratch project.
  - There are at most three touchpoints.
  - No prompt appears between design approval and sign-off.
  - At sign-off, choose "go back to design review", ask for one change, and sign off again. The
    finalizer's sections are regenerated, not left stale.
  - `phase.md` contains no retired section.
  - `implementation.md` keeps `#### Step N:`, `## Checklist` and `## Policy`.
- [ ] **Manual: judge brief quality** against judgment calls 1–4. Read the generated `phase.md` and
      `implementation.md`:
  - every Grounding path is real
  - Delegation Bounds are specific
  - Behaviors & Acceptance is a map, not prose
  - every step reads as executable from cold
- [ ] **Manual: frozen readers still work.** respec-code runs on a phase-4 brief:
  - the `shape-settled` gate passes
  - the steps are found, so dispatch is not silently backend-only
  - the coder reads the Checklist
- [ ] **Effort-level verification** (README "Per-phase exit criteria"):
  - Run real phases on scratch projects in two languages respec-ai has no special support for (for
    example Go and Elixir), plus one language that has a materializer.
  - Hand each brief to a fresh Claude Code session using the handoff's Claude Code instruction.
  - Confirm it implements the steps with no clarifying guesses.
  - Record what it had to guess in [deferred-issues.md](deferred-issues.md), or fix the prompts.
- [ ] README "Shared contracts" is amended per Scope 0, findings.md has F40 per Scope 12, the README
      phase 4 probe prints a match, and every `file:line` in this document has been re-verified
      against the code you leave behind.
