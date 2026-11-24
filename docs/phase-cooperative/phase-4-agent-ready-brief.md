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
extends both. On 2026-11-17 (stage S1) both probes reported done: the two phase 2 greps printed
nothing, and the phase 3 line printed `phase_command.py:872-874`.

**Already done?** Output means done. This is also the README's phase 4 probe:

```bash
test -f src/platform/templates/agents/phase_finalizer.py && grep -n "def brief_handoff_extension" src/platform/tui_adapters/claude_code.py
```

On 2026-11-13 it printed nothing and exited 1, so it reports "not done". None of the names this
phase introduces (`brief_handoff_extension`, `BRIEF_SECTIONS`, `BRIEF_SECTION_PLACEHOLDERS`,
`IMPLEMENTATION_BRIEF_EXAMPLE`, `PHASE_FINALIZER`, `phase-finalizer`, `review_target`) occurred
anywhere in `src/` or `tests/`, so the probe cannot match unrelated text. Stage S1 (2026-11-17)
added `BRIEF_SECTIONS`, `BRIEF_SECTION_PLACEHOLDERS` and `IMPLEMENTATION_BRIEF_EXAMPLE`; the probe
names neither file they live in, and it still printed nothing. The finalizer file alone is
not enough: it exists early in this phase, because the registration tests need it. The handoff
lands late (Scope 10). `test -f` prints nothing, so the line has output only when both have
landed. At the end of stage S6 (2026-11-17) it printed
`66:    def brief_handoff_extension(self) -> str | None:` and exited 0, so it reports "done".

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

**Confirmed against the code on 2026-11-17 (stage S1).** Everything above holds, with these
differences, which this document now follows:
- **The finalize step is Step 10.7, not 10.5.** Phase 2 gave Step 10 six sub-steps
  (`src/platform/templates/commands/phase_command.py`): 10.1 puts the draft on disk, 10.2 asks the
  open questions, 10.3 sends design-changing answers back, 10.4 is the final prompt, **10.5 is
  "Validate and record a hand edit"** and 10.6 "Act on the choice". So the new step is
  `#### Step 10.7: Finalize the brief`, a sub-step of Step 10 with no touchpoint token and no
  `WAIT for`. Every finalize-meaning "Step 10.5" in this document now reads 10.7; the hand-edit
  Step 10.5 keeps its number.
- **The approve route.** Step 10.4's option is labelled "Approve the design" (description "Go to
  sign-off"). Step 10.6 acts on it in its final `ELSE: Go to Step 11` (`phase_command.py:1246-1247` before phase 4; now `ELSE: Go to Step 10.7` at
  `:1352-1353`), the only route into Step 11 before phase 4; it now goes to Step 10.7, and Step 10.7 ends by going to
  Step 11. Step 4's resume and re-open routes reach Step 11 only through Steps 9 and 10, Step 11.1's
  design-changing answers return through Step 9, and Step 11.2's "Go back to design review" returns
  to Step 10. Step 4's "Show the handoff" goes straight to Step 12, which is not sign-off. Rule: no
  route into Step 11 may skip Step 10.7.
- **Variables.** `PHASE_FILE_PATH` is set in Step 1.3 (`:280`, `:305`). `IMPLEMENTATION_PLAN_PATH` is
  set in Step 3.3 (`:416`), so it exists before Step 10.7.
- **Invocation fields.** Phase 2 also has `invoke_architect_explore`. The agent inputs come from
  `_phase_agent_inputs` (`src/platform/template_helpers.py:187`), and `invoke_critic_review`
  (`:278-283`, now also `review_target`) passes `review_round` and `project_config_context_markdown`.
- **The architect's `Write` grant** was kept (open call 1 not overturned). It is declared in the
  `PhaseArchitectAgentTools.builtin_tools` ClassVar (`src/platform/models/phase.py`) as
  `(BuiltInToolCapability.WRITE, '.respec-ai/plans/*/phases/*/implementation.md')`, and
  `create_phase_architect_agent_tools` loops over that list; there is no separate builder call.
  The finalizer follows the same pattern (Scope 6).
- **Phase 3 also added** `UNSTORABLE_DOCUMENT` beside `CONTENT_LOSS_WARNING`. `success_criteria` is
  not frozen: `FROZEN_PHASES_FIELDS` (`src/utils/state_manager/base.py`) is objectives, scope,
  dependencies and deliverables.
- **Phase 3's gate fails closed.** Step 9's key-mode call has an `IF the call that sets VALIDATION
  fails` branch that ends the run before any agent is engaged (`phase_command.py:864-870` before phase 4, now `:992-1000`, pinned by
  `test_a_failed_gate_validation_ends_the_run_before_any_agent_is_engaged` in
  `tests/unit/templates/test_phase_structural_gate.py`). Step 10.7's gate and Step 11's once-more
  gate each get the same branch, pinned the same way (Scope 9).
- **The review-target tag cannot be a first line.** `get_feedback`
  (`src/mcp/tools/feedback_tools_unified.py`) renders each critic iteration as
  `## Iteration N - Score: X`, then the assessment summary, then the Blockers, Key Issues and
  Recommendations. It never renders the detailed feedback, and a line placed before the
  `# Critic Feedback:` heading is dropped on parse (probe, 2026-11-17). So the tag lives in the
  critic's `- **Assessment Summary**:` value, which starts with `Review target: design` or
  `Review target: brief`, then a dash and the summary; `get_feedback` shows it as the first line
  under each iteration heading. Scope 0 amendment 4, Scope 6 STEP 2 and Scope 8 now say so.
- **Phase 3's anchors** for the architect's self-check and the critic's relay: architect
  `STEP 4.5: Structural Self-Check` (`src/platform/templates/agents/phase_architect.py:628`; now `:658`), critic
  `STEP 5.5: Validate the Document` (`src/platform/templates/agents/phase_critic.py:237`; now `:256`) and its
  `IMPLEMENTATION PLAN STRUCTURE` relay. The critic's phase 2 file check is the marker
  `Step Names No Files`.
- **The location strings phase 3 actually emits** (probe, 2026-11-17), which Scope 5's ownership
  rule must match:
  - `phase.md`: `<H2> > <H3>` for a typed field (`Design Shape > Skeleton Index`,
    `Design Decisions > Open Design Decisions`, …), and the bare H2 name for an additional section,
    so a dangling ID in `## Grounding` has location `Grounding`.
  - `implementation.md`: `implementation-section-missing` has location `implementation.md`, with
    the section in `part` (`Build Order > Steps`, `Checklist`, `Policy`). Step heading, duplicate
    and no-steps findings use `implementation.md > Build Order > Steps`; Checklist findings use
    `implementation.md > Checklist`. A dangling ID uses its line's heading path:
    `implementation.md > Start here > Required reading`, `implementation.md > Exit criteria`, and
    `implementation.md > Build Order > Steps` for **every** step line, with no step number and no
    field label.

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
   literal for the orchestrator to substitute. Phase 2 deleted Step 12.6, where the variable used
   to be set, and sets it in Step 3.3 (`src/platform/templates/commands/phase_command.py:542`, was `:416`), so
   it exists before Step 10.7.
9. **Write prompt text imperatively.** The finalizer is covered by the imperative-language audit
   (Scope 11). When you turn this document's prose into template text, write "add", "decide without
   asking" and "return", never "may add" or "can".

**Line numbers.** Every anchor was verified on 2026-11-13, before phases 1–3 landed.
- **Should survive:** anchors in the frozen respec-code readers (`code_command.py`,
  `coder_contracts.py`, `spec_alignment_reviewer.py`), `tests/support/plan_extraction.py`, and most
  of `src/models/` and `src/utils/`. Two exceptions: phase 3 adds a `find_content_loss` override to
  `src/models/phase.py`, and moves `_BULLET_PATH` out of `src/utils/skeleton_generator.py:16` (landed: `BULLET_PATH` now lives in `src/utils/skeleton_types.py:15` and is imported at `:8`) into
  `src/utils/skeleton_types.py` under a public name (phase 3 work items 2 and 4).
- **Will probably move:** everything else.
  - Phase 2 changes the critic's tool builder (the soft caps go, F36) and `PhaseCommandTools` (the
    act-specific fields and `mcp_tools_reference` go, F38).
  - It also adds a capability to `tool_enums.py` and the adapters (F13), and a phase-local
    `bp-pipeline` exception line after the shared Claude Code guardrail, which itself stays
    unchanged (F18).
  - Phases 1 and 2 delete or rewrite tests (F23, F36).
  - Phase 2 deletes the command's copy of `technical_phase_template` and re-points
    `tests/unit/templates/test_phase_section_references.py:23` (was `:21`) to the architect's copy.
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
| B12 | The finalized brief is reviewed before sign-off without adding a touchpoint. Step 10.7 (after Step 10.6's "Approve the design" branch, before Step 11) invokes the finalizer, runs the key-mode gate, then the critic with `review_target: brief`; it holds no `WAIT for` and no touchpoint token. Its repair invocations are the finalizer's, never the architect's, and a failed gate call ends the run before any agent is engaged | the touchpoint budget (at most 3); repairs going to an agent that does not own the brief sections |
| B13 | The brief review never re-opens design judgment and never researches. The critic's `review_target == "brief"` branch carries none of the design-review rules, and Steps 10.7, 11 and 12 contain no `bp-pipeline` invocation and no route to Step 7 except back through Step 10 | the approve → critic → re-approve cycle (decisions.md, "The critic reviews drafts before the user sees them"); the cost invariant |
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
  (`tests/unit/templates/test_phase_section_references.py:92-101`, now `:94-102`) passes on day
  one. Extract its collision logic into a helper, and assert that the helper flags a synthetic
  `Design` H2 next to `Design Shape`. The positive half picks up the new names automatically,
  because the guard reads them from `technical_phase_template` (`:41-49`, now `:43-51`), imported
  from the architect after phase 2. Assert B2's first half by parsing that template with
  `Phase.parse_markdown`, not by matching strings. Done in stage S1: the helper is
  `tests/support/section_names.py`.
- **B5–B9, B17 and B18 are mostly pure-function tests.** B5–B9 and B18's ownership half go in
  phase 3's `tests/unit/utils/test_phase_structure.py`, one defect per fixture. Assert on `check`,
  `subject`, `part` and `owner`, never on `detail` wording (phase 3, judgment call 7). B17 goes in
  `tests/unit/models/test_content_loss_detection.py`. Its two routes (the hand edit and the
  `CONTENT_LOSS_WARNING` on `update_document`) sit beside phase 3's own route tests in
  `tests/unit/mcp/test_document_validation.py`, where their fixtures live. B18's routing half is a
  template-contract test beside phase 3's B15, in `tests/unit/templates/test_phase_structural_gate.py`.
  B18's ownership half also pins each finding's `location`, because the owner is computed from it.
- **B10 follows `tests/unit/templates/test_coder_split_phase9.py:31-46`.** Build both
  `OpenCodeAdapter` and `CodexAdapter` with `model_overrides` so the test stays hermetic (F37).
- **B12 and B13 assert structure through `tests/support/template_contract.py`.** Take
  `template_contract(rendered_command).step_body('10.7')` and assert `wait_prompt_count(...) == 0`.
  Assert that the body contains the rendered `invoke_finalizer` and `invoke_critic_brief_review`
  text and none of the rendered architect invocations. For B13, assert that the step bodies of 10.7,
  11 and 12 do not contain the rendered `invoke_bp_pipeline` text. `invoked_tools()` and
  `blocker_conditions()` read the whole string they are given, so build a contract over the
  extracted body. For the critic half, extract the `review_target == "brief"` branch the way
  `_phase_mode_branch_body` does (`tests/unit/templates/test_phase_implementation_plan_gate.py:49-66`),
  and assert that it names none of the design-review markers. Pin the fail-closed branch of Step
  10.7's gate and of Step 11's once-more gate the way
  `test_a_failed_gate_validation_ends_the_run_before_any_agent_is_engaged` pins Step 9's.
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
     architect". Its scoped `implementation.md` `Write` is declared in
     `PhaseFinalizerAgentTools.builtin_tools`, the ClassVar pattern the architect's grant uses. It reads the architect's exploration notes and writes none, so it gets no
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
   sign-off, Step 11.4, `src/platform/templates/commands/phase_command.py:1662-1697`, the seven
   `MATERIALIZATION_SDS.append` lines; was `:1407`, `:1414`, `:1423`, `:1428`) and
   `supersedes=unresolved-checks` (phase 2) have no `Affects:` line to copy. Phase 3's SD segment
   parser gains `affects` as a known key (Scope 5).
4. **Critic findings.** On a `review_target=brief` run:
   - `[mechanical]` findings, and open `structural_findings` from the Step 10.7 gate, are repaired by
     a fresh **finalizer** invocation, not by the architect's `revise`. They share one two-round
     budget, which resets when Step 10.7 starts.
   - `[judgment]` findings are asked at sign-off.
   - The critic's `- **Assessment Summary**:` value starts with `Review target: design` or
     `Review target: brief`, then a dash and the summary. `get_feedback` shows it as the first line
     under each `## Iteration N - Score: X` heading, so the finalizer acts only on brief findings
     (`get_feedback` is otherwise untagged, F31; see "Confirmed against the code" in Start here).
   - `FindingOwner` gains `finalizer`, computed as Scope 5 says. Structural repair in Step 10.7 goes
     to the finalizer; Step 9's gate is unchanged.
   - Add the critic's three new `[mechanical]` markers to the list of blockers the critic still
     raises (phase 3 work item 10 makes that list exhaustive): `Grounding Path Invalid`,
     `Step File Verb Invalid` and `Reviewed Section Changed` (Scope 8). *Stage S5 added two more*,
     because Scope 8's cold-start and coverage checks need markers: `Cold Start Gap` and
     `Success Criterion Missing`, plus the `[judgment]` markers `Cold Start Decision` and
     `Unmeasured Success Criterion`. README "Critic findings" names all of them.
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

   **Landed in stage S1 (2026-11-17).** All six amendments are in README "Shared contracts", using
   Step 10.7 and the Assessment Summary tag. The finalizer's Agents-table row names the
   `builtin_tools` grant; the critic's and the finalizer's inputs are sub-bullets of "Inputs". The
   `affects=` rule is worded "copied verbatim from the settled entry's `Affects:` line when it has
   one", and stays out of the per-source required table, because the validator never requires it
   (Scope 5). The judgment call 6 probe was re-run on 2026-11-17, after phase 3's
   `find_content_loss` override landed, with the same result; it is recorded under "Section naming"
   without a finding number, since F40 is Scope 12's. The "Brief format (phase 4)" subsection
   follows "Section naming and frozen-reader compatibility".

### 1. Canonical order for the brief sections: `src/models/phase.py`

- Add the constant below next to `HEADER_FIELD_MAPPING` (`src/models/phase.py:24-52`, constant now at `:54`). It is the
  single source of the four names. Templates and checks import it from here; a model never imports
  a template.

  ```python
  BRIEF_SECTIONS: ClassVar[tuple[str, ...]] = ('Grounding', 'Delegation Bounds', 'Behaviors & Acceptance', 'Guardrails')
  ```

- In `build_markdown`, the `additional_sections` loop (`src/models/phase.py:172-175` before phase 4, now `:266-275`) changes. It emits the brief
  sections present, in `BRIEF_SECTIONS` order, then every other additional section in its existing
  order. Their position before `## Metadata` is unchanged. (B1)
- No field, column or migration. A probe on 2026-11-13 round-tripped all four names, including
  `Behaviors & Acceptance` with its `&`, through `parse_markdown` and `build_markdown` with no
  content loss.

**Landed in stage S1 (2026-11-17).** `Phase.BRIEF_SECTIONS` sits right after
`HEADER_FIELD_MAPPING` (`src/models/phase.py:23-52`, constant at `:53-58`), and the ordering is in
`build_markdown`'s additional-sections block (`:242-247`). B1 is
`TestBriefSectionOrder` in `tests/unit/models/test_phase_additional_sections.py`: every stored
order of the four, a subset, and brief H2s written out of order then re-parsed.

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
- When the repository contradicts this brief, stop the step and add a line under implementation.md's `## Deviations`, numbered from DEV-1 up, in the form `- DEV-<n> | Step <N> | expected: … | found: … | action: …`. Continue only if the deviation stays within `### Implementer's discretion`; otherwise escalate.
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
  | `### Test List` | Each entry is `` - `<test path>::<observable behavior>` — T-<n> ``. The ID goes **after** the closing backtick: `parse_test_list` reads only the backticked text (`src/utils/skeleton_generator.py:16`, `:99-108`); a probe confirmed that a trailing `— T-3`, after a space, parses cleanly. Inside the backticks it would become part of the test name. |
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
  it names (`code_command.py:304-311`). A step with no paths silently defaults to backend
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
    materializes its skeleton (create-only) for a language that has a materializer, and the step
    fills that skeleton in. *Stage correction (pass B):* the brief says so (an existing `create`
    item is a skeleton to fill), and the skeleton Prerequisites line and `Fill in` First action are
    written only for a language whose `### Language Authoring Notes` section does not say that no
    materializer is registered; any other language's First action is `Create <path>`.
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
    `technical_phase_template` (`tests/unit/templates/test_phase_section_references.py:23`, `:43-51`).
    Phase 2 re-pointed that import to the architect.
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
- **Update the import** at `tests/unit/templates/test_phase_implementation_plan_gate.py:25` (now
  `:27`). Its tests at `:62` and `:71` (now `:69` and `:78`) keep passing against the new constant.
- **Sharing.** The finalizer imports both constants from this module. The architect imports both
  and is told which step fields and sections it writes in `draft` (Scope 3's draft fields, plus
  `## Checklist`). Neither template restates the layout in its own words.

**Landed in stage S1 (2026-11-17).**
- `src/platform/templates/phase_contract_grammar.py` now imports `Phase` and builds
  `BRIEF_SECTION_PLACEHOLDERS` by zipping `Phase.BRIEF_SECTIONS` with the four skeletons.
  `## Behaviors & Acceptance` shows a `Scope item:` line beside the Objective and Deliverable
  lines, because the rule is one line per objective, scope item and deliverable. Its path
  placeholders are descriptive (`<path to code this phase extends>`), in phase 1's notation.
- `IMPLEMENTATION_BRIEF_EXAMPLE` replaces `implementation_plan_example`, which is gone from
  `phase_architect.py`. The example cites, from phase 3's ID families, only `SD-1`. Phase 3's tests
  resolve every OD, SD, CQ, RP and FLOW ID in `implementation.md` against their `design()`
  fixture, which defines SD-001, so any other such ID would dangle there. T, SC and G IDs are free.
  It cites `SD-1`, `G-1`, `G-2`, `SC-2`, `T-1` to `T-4`, and three Skeleton Index paths as
  `create` items: `<path to the repository query module>`, `<path to the cache module>` and
  `<path to the result list component>`. B4's fixture defines exactly those.
  - **The Checklist keeps `(verify: <…>)` without backticks**, matching README's frozen-reader line
    and phase 1's `(verify: ask user — …)` marker. Phase 3's placeholder rule strips backticks, so
    either form is checked. Step `Verify` and `## Exit criteria` commands are backticked, because
    checks 9 and 10 look for backticked commands. Nothing else under `## Exit criteria` is
    backticked, so only commands count as commands there.
  - Each step's `Files` names its own test file, so no two steps share a placeholder path.
  - **All three steps share one `Verify` placeholder text.** Phase 3 collapses findings that share a
    finding key (`<check> <subject> [<part>]`). If check 9 used the command as `subject`, B4's
    "one `implementation-command-placeholder` per step `Verify` command" would collapse to one, so
    its `subject` names the step (for example `Step 2`, `part: Verify`).
- `TEST_LIST_PLACEHOLDER` gained `— T-<n>` and lost the Testing Strategy pointer.
  `SKELETON_INDEX_PLACEHOLDER` already had no ID and is unchanged.
- `technical_phase_template` (`src/platform/templates/agents/phase_architect.py`) drops the nine
  retired fields, keeps `additional_details_additional` (not on the retired table), and gains
  `additional_sections=BRIEF_SECTION_PLACEHOLDERS`, a `design_shape_additional` whose only heading
  is `#### Design Narrative` (its text says a UX Contract block follows only for a UI phase),
  `SC-<n>: … — measure: …` Success Criteria and a canonical SD with `affects=`. The template shows
  no `#### UX Contract` heading: that heading triggers UX review weighting, Step 10.1's notice and
  the critic's UX Contract rules, and a backend-only phase must emit none.
- **Re-pointed, none deleted.** `tests/unit/templates/test_phase_implementation_plan_gate.py` and
  `tests/unit/utils/test_phase_structure.py` import `IMPLEMENTATION_BRIEF_EXAMPLE`. Phase 3's two
  example tests keep their expectations: on the new constant the phase 3 checks still report
  exactly the three Checklist placeholders, and nothing once they are concrete. Phase 3 does not
  check step `Verify` or `## Exit criteria`; B4 supersedes both tests once Scope 5 does.
  `test_content_loss_detection.py`, `test_phase_cooperative_flow.py`,
  `test_phase_section_references.py` and `test_phase_structural_gate.py` still import
  `technical_phase_template` from the architect, and pass unchanged.
- **B2 and B3** are in `tests/unit/templates/test_phase_brief_format.py`. B2 parses
  `technical_phase_template` with `Phase.parse_markdown` after swapping in a real phase name, as
  `test_phase_structural_gate.py` does. The H2 collision rule moved to
  `tests/support/section_names.py` (`h2_collisions`, `mapped_h2_names`), which
  `test_phase_section_references.py` now uses; its negative self-test is a synthetic `Design` H2
  beside `Design Shape`. B3 uses new `tests/support/plan_extraction.py` helpers
  (`extract_section`, `extract_h2_names`, `extract_checklist_items`).
- **Not done here; Scope 7 owns it.** The architect still embeds the example under "Copy this
  structure exactly" (`phase_architect.py:715-722`) with no line saying it writes only the draft
  fields in `draft`. STEP 3 still describes steps as **Objective**/**Files**/**Actions**
  (`:497-499`), and the carry-forward block names an `**Actions**` item (`:484`). It still tells the
  architect to write retired sections (`:465-467`, the list near `:942`, and OUTPUT DETAIL
  GUIDELINES). The architect is now shown all four brief H2s in its mandatory structure, but no rule
  yet stops it writing the finalizer's three. The "Sharing" bullet above can be met only with that
  rewrite.

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
- A `phase.md` finding is `finalizer`-owned when the first segment of its `location` is
  `Grounding`, `Behaviors & Acceptance` or `Guardrails`, or its `check` is
  `success-criterion-malformed`.
- An `implementation.md` finding is `finalizer`-owned when its `location` names a finalize-only
  section or field: `Start here`, `Exit criteria`, `Deviations`, `Context`, `Tests to turn green`,
  `Verify` or `Done when`. This replaces phase 3's "every `implementation.md` finding is
  `architect`" for those findings only.
- Phase 3's ownership rules for `orchestrator` are unchanged and take precedence.
- **Match the location strings phase 3 actually emits** ("Confirmed against the code" in Start
  here), and pin them in tests. Two of them do not carry what this rule reads. A phase 3
  `dangling-reference` on any step line has location `implementation.md > Build Order > Steps`, with
  no step number or field label. `implementation-section-missing` has location `implementation.md`
  and puts the section in `part`. Either give the new findings locations that name their section
  or field, or extend the rule to read `part`. Never guess an owner from `detail`.

Routing then needs no new mechanism:
- Phase 3's Step 9 gate builds its two lists from `owner: architect` and `owner: orchestrator`, so
  `finalizer` findings fall in neither and are ignored there. The architect's self-check fixes only
  `owner: architect`. The design-review critic relays only `owner: architect` implementation
  findings (Scope 8).
- In Step 10.7 (Scope 9), `architect` and `finalizer` findings go to the finalizer. An `architect`
  finding there means a section the finalizer reproduces has drifted, and the fix is to restore it.
  `orchestrator` findings go to `STRUCTURAL_LEFTOVERS`, as in phase 3.
- State the ownership rule once, in the README "Brief format (phase 4)" subsection.

Set `part` on each new finding to the faulty element (an H3 name, a field label, a step number, a
command), as phase 3 does, because accept-as-is SDs match on `<check> <subject> [<part>]`.
Phase 3 also collapses findings that share that key, so a `subject` must tell repeated defects
apart: `IMPLEMENTATION_BRIEF_EXAMPLE`'s three steps share one `Verify` placeholder, and B4 expects
one `implementation-command-placeholder` per step. Name the step in `subject` (for example
`Step 2`, `part: Verify`), not the command text.

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
`###` line is reported as `<H2>: text before the first subsection is dropped on parse`. Phase 3
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
| 8 | `implementation-step-files-missing` | A step's `Files` names no backticked path. respec-code classifies steps by these paths, and a step with none silently defaults to backend (`code_command.py:304-311`, `:518`). (B6) |
| 8 | `implementation-dependency-invalid` | `Depends on` names a step that does not exist, the step itself, or forms a cycle. Name the steps in the cycle. (B6) |
| 9 | `implementation-command-placeholder` | A step's `Verify` holds no backticked command and does not start with phase 1's `ask user` marker, or any backticked command in a step's `Verify` or under `## Exit criteria` is a placeholder (rule below). (B6) |
| 10 | `implementation-finalize-section-missing` | Any of `## Start here`, `## Exit criteria` or `## Deviations` is present, or any step holds all seven fields, while another of the three is missing, `## Start here` lacks one of its three H3s, or `## Exit criteria` has no backticked command. (B6) |
| 11 | `dangling-reference` (extended) | An ID in a step's `Context` or `Tests to turn green` is undefined in the phase (T, SC and G families as in check 5; phase 3 already resolves the others). A `Step N` token in the four brief H2s or on an open OD's `Affects:` line names no step. SD entries stay exempt, as in check 5. (B7) |
| 11 | `seam-path-not-in-any-step` | A `### Skeleton Index` path appears in no step's `Files`. Read the path with the bullet grammar phase 3 promoted from `src/utils/skeleton_generator.py:16` into `src/utils/skeleton_types.py`. Never parse the signature (F24). Compare after stripping a leading `./`. (B7) |
| 11 | `test-not-in-any-step` | Every step holds all seven fields, and some Test List `T-n` appears in no step's `Tests to turn green`. (B7) |

**The placeholder rule** is one shared predicate. Extract it from phase 3's Checklist rule and use it
for step `Verify`, `## Exit criteria` and the Checklist `(verify: …)` groups, so the three never
disagree. A command is a placeholder when it:
- is empty after stripping, or starts with `TODO` in any case, optionally bracketed (phase 3's rule;
  phase 1's config validation reads the same values as missing, `_is_incomplete_value`,
  `src/platform/standards_config.py:324-326`)
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

**Landed in stage S2 (2026-11-17): stubs and the contract the red tests pin.** The 13 check IDs,
`FindingOwner.FINALIZER`, the three `CitedPathKind` values and an `extract_implementation_paths` that
returns `[]` are in place; S3 implements the checks to the tests below. Where this table is more
precise than the rows above, the table is the contract.

| `check` | `location` | `subject` | `part` | `owner` |
|---|---|---|---|---|
| `delegation-bounds-incomplete`, section absent | `Delegation Bounds` | `Delegation Bounds` | empty | architect |
| `delegation-bounds-incomplete`, H3 missing or empty | `Delegation Bounds > <H3>` | `Delegation Bounds` | `<H3>` | architect |
| `brief-section-incomplete`, section absent | `<H2>` | `<H2>` | empty | finalizer |
| `brief-section-incomplete`, H3 missing or empty | `<H2> > <H3>` | `<H2>` | `<H3>` | finalizer |
| `test-entry-without-id` | `Design Shape > Test List` | the entry line, stripped | empty | architect |
| `duplicate-id`, T | `Design Shape > Test List` | `T-<n>` as written | empty | architect |
| `success-criterion-malformed`, no measure | `Additional Details > Success Criteria` | `SC-<n>` | `measure` | finalizer |
| `success-criterion-malformed`, no ID | `Additional Details > Success Criteria` | the entry line, stripped | `id` | finalizer |
| `duplicate-id`, SC | `Additional Details > Success Criteria` | `SC-<n>` | empty | finalizer once any of the finalizer's three H2s is present; architect otherwise |
| `duplicate-id`, G | `Guardrails` | `G-<n>` | empty | finalizer |
| `dangling-reference`, T, SC or G in `phase.md` | the section's location: the bare H2 for a brief section | the token | empty | by location; located in Success Criteria, finalizer once any of the finalizer's three H2s is present |
| `research-copies-disagree` | `Grounding > Research to read` | the path | empty | finalizer |
| `implementation-section-missing`, Policy H3 | `implementation.md > Policy` | `implementation.md` | `Policy > <H3>` | architect |
| `implementation-steps-not-contiguous` | `implementation.md > Build Order > Steps` | `Steps` | empty | architect |
| `implementation-step-fields-incomplete` | `implementation.md > Step <N> > <label>` | `Step <N>` | `<label>` | by label |
| `implementation-step-files-missing` | `implementation.md > Step <N> > Files` | `Step <N>` | `Files` | architect |
| `implementation-dependency-invalid`, missing step or itself | `implementation.md > Step <N> > Depends on` | `Step <N>` | `Step <M>`, as named | architect |
| `implementation-dependency-invalid`, cycle | `implementation.md > Step <N> > Depends on` | `Step <N>`, the lowest in the cycle | `cycle` | architect |
| `implementation-command-placeholder`, step | `implementation.md > Step <N> > Verify` | `Step <N>` | `Verify` | finalizer |
| `implementation-command-placeholder`, exit | `implementation.md > Exit criteria` | `Exit criteria` | the command, without backticks | finalizer |
| `implementation-finalize-section-missing`, section absent | `implementation.md > <H2>` | `<H2>` | empty | finalizer |
| `implementation-finalize-section-missing`, Start here H3 | `implementation.md > Start here > <H3>` | `Start here` | `<H3>` | finalizer |
| `implementation-finalize-section-missing`, no exit command | `implementation.md > Exit criteria` | `Exit criteria` | `command` | finalizer |
| `dangling-reference` on a line inside a step | `implementation.md > Step <N> > <label>` (an indented continuation line belongs to the field above it), or `implementation.md > Step <N>` off a field | the token | empty | by location |
| `dangling-reference`, `Step N` in `phase.md` | the `phase.md` section's location | `Step <N>` | empty | by location |
| `seam-path-not-in-any-step` | `implementation.md > Build Order > Steps` | the Skeleton Index path as written | empty | architect |
| `test-not-in-any-step` | `implementation.md > Build Order > Steps > Tests to turn green` | `T-<n>` | empty | finalizer |

- **Ownership reads `location` by segment.** A `phase.md` finding is the finalizer's when the first
  segment of its `location` is `Grounding`, `Behaviors & Acceptance` or `Guardrails`, so an
  additional section named `Grounding Notes` stays the architect's. An `implementation.md` finding is
  the finalizer's when any segment after `implementation.md` is a finalize-only section or field.
  This re-owns phase 3's own findings too: a dangling `OD-042` in `## Grounding`, or a dangling
  `SD-9` in a step's `Context`, in `## Start here > ### Required reading` or in `## Exit criteria`,
  is the finalizer's.
- **Phase 3's step-line location changes.** Lines inside a step are located at
  `implementation.md > Step <N> > <label>` (or `implementation.md > Step <N>` when the line is neither a
  field bullet nor an indented line continuing one), no longer at `implementation.md > Build Order > Steps`; nothing in `src/` read the
  old string. Step-heading, duplicate, no-steps, Staging and Checklist locations are unchanged.
  `test_every_finding_is_located_where_its_owner_is_computed_from` pins every row above.
- **Step fields.** A field bullet is a column-0 `- **<label>:**` with one of the seven labels; other
  lines are ignored. The target is all seven when any finalize-only label is present, otherwise the
  three draft labels. Each missing label is one finding. When none is missing, an order break is one
  finding whose `part` is the first label, in written order, that stands where the target order puts
  another; when the draft labels keep their relative order and none repeats, only a finalize label
  can be named, so a misplaced `Context` is the finalizer's. A step with no field bullets reports its three draft labels. A missing `Files` is only
  `implementation-step-fields-incomplete`, never also `implementation-step-files-missing`. The lines
  after a malformed or duplicate step heading, up to the next heading, belong to no step: they get
  no field checks and never count toward the step that shares the number.
- **Commands.** A step's `Verify` passes when it holds at least one backticked command and none of its
  backticked commands is a placeholder, or when its value starts with phase 1's `ask user` marker,
  backticked or not. `cmd < in > out` is not a placeholder anywhere.
- **Scoping.** Check 3 applies to the column-0 entries phase 3 already reads as test entries, so a
  malformed bullet reports only its malformation. Check 4 runs only when one of the finalizer's three
  H2s is present; duplicate SC IDs are reported regardless. T, SC and G references are checked only
  in the four brief H2s, `## Design Decisions` (SD entries exempt) and Success Criteria for
  `phase.md`, and only in a step's `Context` and `Tests to turn green` for `implementation.md`. `Step N`
  tokens in `phase.md` are checked only with `implementation.md` passed. Check 11's seam check runs
  only when the plan has a step; its T coverage check only when every step holds all seven fields.
- **`affects`** is a known SD key, observable as `settled-entry-malformed SD-n [rejected]` on an entry
  whose empty `rejected=` is followed by `affects=`.
- **Cited paths.** Grounding paths are `grounding`, with `cited_in` `Grounding > <H3>` for the four H3s
  other than `### Research to read`. `extract_implementation_paths` returns each step's `Files`
  paths as `create` or `modify`, with `cited_in` `implementation.md > Step <N> > Files`, and
  `PhaseTools.validate` appends them to `paths_to_verify` in both modes exactly when
  `implementation_markdown` is passed (`tests/unit/mcp/test_document_validation.py`).
- **B17.** The rule covers each mapped H2 other than `Metadata` whose mapping entries are all two
  levels deep. Blank lines are not loss, text before the first H3 of an additional section is kept
  and not reported, and a single-H2 mapping (`Plan`'s sections) is that field's own content.
- **Fixtures.** Phase 3's shared fixtures in `tests/unit/utils/test_phase_structure.py` and
  `tests/unit/mcp/test_document_validation.py` now have the phase-4 shape with every expected row
  unchanged: Test List entries end in `— T-<n>`; designed phases carry a complete `## Delegation
  Bounds` (placed before the typed sections in `phase_markdown`, because an unclosed fence swallows
  every later additional section); steps use the draft fields, with `Files` covering the Skeleton
  Index; injected steps carry draft fields; the overlap test uses `Rollout` names; and the
  distinct-names test uses complete brief bodies. A probe with crude versions of checks 1, 3, 8 and 11
  cut the phase 3 fallout from 227 tests to the corpus test and the two taught-example tests. Those
  two now run against `brief_phase()`, which defines what the example cites; the placeholder test
  expects the Verify and Exit criteria placeholders too. Phase 3's corpus test stays red until S3
  adds documents that trigger the 13 new checks.

**Landed in stage S3 (2026-11-17).** The checks are in `src/utils/phase_structure.py`. B17 is
`Phase._text_before_first_subsection` (`src/models/phase.py`). `PhaseTools.validate` appends
`extract_implementation_paths` to `paths_to_verify` when `implementation_markdown` is passed
(`with_structural_checks`, `src/mcp/tools/phase_tools.py`). The corpus test now carries:

- a `## Grounding` section
- a `T-7` entry and an unnumbered success criterion
- a second document without Delegation Bounds
- a third, finalized plan

`test_a_malformed_brief_is_reported_as_a_finding_never_raised` is new.

Where the rows and the S2 table are silent, these are the readings. Each was chosen so that a
doubtful case is not flagged.

- **Ownership** is computed once, after phase 3's key collapse (`_owned`). Orchestrator findings keep
  their owner. Every other finding goes to the finalizer exactly when its location says so;
  `implementation.md` segments compare case-insensitively. `implementation.md`-located findings are
  listed before the `phase.md` `Step N` findings, so when two collapse on one key, the
  `implementation.md` one is kept.
- **Step fields.** A field bullet is a column-0 `-`, `*` or `+` bullet whose bold label is one of the
  seven, written `**Goal:**` or `**Goal**:`, in any case.
  - Indented and blank lines after a field bullet continue that field, for its value and its
    location. A `Verify` listing one command per indented sub-bullet therefore passes.
  - A column-0 line that is not a field bullet ends the field, and is located at
    `implementation.md > Step <N>`.
- **Headings** match case-insensitively: `## Start here`, `## Exit criteria` and `## Deviations`, the
  Policy and Start here H3s in `implementation.md`, and the brief H3s in `phase.md`. Phase 3's exact
  matches on `## Checklist`, `## Policy` and `### Steps` are unchanged.
- **Step numbers.** Contiguity, `Depends on` and `phase.md` `Step N` tokens compare against every
  numbered `#### Step` heading, malformed ones included, as phase 3's Checklist rule does. A
  malformed heading is then reported once, not also as a gap or a dangling step.
  - `phase.md` `Step N` tokens are checked only when the plan has a valid step.
  - No step number is converted to an integer: a 5000-digit one would raise.
- **Cycles** are strongly connected components, found iteratively (Kosaraju), so a 3000-step chain
  cannot exhaust the stack. The detail names up to six of their steps.
- **Exit criteria.** A line that starts with the unbackticked `ask user` marker counts as a command
  (B6: the marker is never flagged).
- **Success Criteria.** An entry with neither an `SC-<n>:` ID nor a `measure:` part gets both
  findings, `id` and `measure`, with the line as subject. Bold markers are ignored when reading
  `SC-<n>:` and `G-<n>:`.
- **Test IDs.** The trailing ID may follow an em dash, an en dash or a hyphen.
- **Research copies.** `### Research to read` contributes the first backticked span of each bullet,
  so a backticked module path in `informs:` is not read as research. The ledger contributes its
  `- Read:` paths, read as phase 3 reads them. Paths compare after stripping a leading `./` and a
  trailing `/`.
- **Grounding cited paths** are the leading backticked path of each bullet (the Test List bullet
  grammar), never every backticked span. A span such as `` `QueryCache.get` `` is therefore never
  sent to Glob.
- **`Files` verbs.** Each backticked path takes the nearest `create` or `modify` before it within its
  `;` item, on its own line. A path with no verb before it in its item is not returned.
- **Details** never echo a path or a command, because either can carry an extension the language
  guard flags. The `subject` or `part` carries it instead.
- **B17.** An H1 line also ends the wait for the first H3. All callers pass a single phase.
- **`## Deviations` lines are never scanned for references.** They are the implementers' record,
  which no agent may edit, so a finding on an ID they cite would have no fix its owner may make. This
  is the same reason phase 3 exempts SD entries.

**Open for Scope 6.** `success-criterion-malformed` is the finalizer's by check, including part
`id`. Scope 2 says the finalizer never edits an existing criterion, so its prompt must allow one
repair: prefixing an unnumbered criterion with the next unused `SC-<n>:`. Without it, the finding
has no fix its owner may make. **Resolved in stage S4:** the finalizer's STEP 4 allows exactly that
prefix, and nothing else, on an existing criterion.

### 6. The finalizer agent: new file `src/platform/templates/agents/phase_finalizer.py`

**Registration.** Every site below is required; B10 fails if any one is missing.

| Site | Change |
|---|---|
| `src/platform/tool_enums.py:154-155` | add `PHASE_FINALIZER = f'{_RESPEC_AGENT_PREFIX}phase-finalizer'` after `PHASE_CRITIC` |
| `src/platform/models/phase.py:211-234` (add after `PhaseCriticAgentTools`) | add `PhaseFinalizerAgentTools(AgentToolsModel)`. Its `respec_ai_tools` are `GET_DOCUMENT`, `UPDATE_DOCUMENT`, `GET_FEEDBACK`, `GET_PREVIOUS_ANALYSIS` and `VALIDATE_DOCUMENT`. Its `builtin_tools` are `READ`, `GLOB`, `GREP` and `(BuiltInToolCapability.WRITE, '.respec-ai/plans/*/phases/*/implementation.md')`, the ClassVar pattern phase 2 kept for the architect. It has one inline-call field per MCP tool, rendered with the same arguments the architect's are after phases 2 and 3: `get_document` and `get_feedback` on `{LOOP_ID}` (today `src/platform/template_helpers.py:842-847`), `update_document` on `{PLAN_NAME}/{PHASE_NAME}` (`:848-853`), `get_previous_analysis` on `{LOOP_ID}`, and `validate_document` exactly as phase 3 work item 6 renders it for the architect. |
| `src/platform/models/__init__.py:20`, `:79` | import and export it |
| `src/platform/template_helpers.py:846-871` (add next to `create_phase_critic_agent_tools`) | add `create_phase_finalizer_agent_tools(tui_adapter)`. Like `create_phase_architect_agent_tools` (`:805-843`), it loops over the model's `respec_ai_tools` and `builtin_tools`, so the scoped `WRITE` comes from the ClassVar; there is no separate builder call. |
| `src/platform/templates/agents/__init__.py:13-14`, `:31-32` | import and export `generate_phase_finalizer_template` |
| `src/platform/template_generator.py` | import the builder beside `src/platform/template_generator.py:28-29` and the generator beside `src/platform/template_generator.py:51-52`; add `'respec-phase-finalizer'` to `_AGENT_NAMES` after `'respec-phase-critic'` (`src/platform/template_generator.py:109-131`); build its tools beside `src/platform/template_generator.py:273-276`; add its `_parse_agent_spec` entry after `src/platform/template_generator.py:302` |
| `src/platform/template_helpers.py:170-171` | `builder.add_task_agent(RespecAIAgent.PHASE_FINALIZER)` in `create_phase_command_tools` |

The agent counts follow automatically, because `expected_agents_count` is derived
(`src/platform/template_generator.py:157-158`, `expected_agents_count`). On codex the runtime name becomes
`respec-phase-finalizer-agent` (`src/platform/tui_adapters/codex.py:389-392`, `_agent_runtime_name`).

**If phase 2 overturned the Write grant** (its open call 1; it did not, 2026-11-17): the finalizer gets no `WRITE`. It
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
  - *Stage correction (pass B).* Read `phase_file_path`, the approved copy Step 10.7 writes, as the
    restore source for the reviewed sections. A repair run is a fresh invocation whose retrieved
    document is the previous pass's output, so without the file an architect-owned drift finding has
    nothing to restore from. `### Success Criteria` (append-only) and the `## Delegation Bounds`
    lines that cite an SD superseding an OD or a CQ come from the retrieved document, not the file.
    If the file cannot be read, the retrieved document stands in. `implementation.md` has no approved
    copy: its restore source stays the text STEP 1 retrieved.
- **STEP 2, choose the scope from the inputs, never from a mode.**
  - **Full pass** when none of `## Grounding`, `## Behaviors & Acceptance` and `## Guardrails` is
    present. Any architect `revise` on a document that holds them removes them (Scope 7). Write all
    three, complete Success Criteria, expand every draft-only step, and write `## Start here` and
    `## Exit criteria`. Add `## Deviations` with `- None` if it is absent; never edit its lines.
    *Stage correction (pass B):* also apply every SD whose `supersedes=` names an OD or a CQ to each
    step, guardrail and criterion its `affects=` names, citing its ID at each place that does not
    already cite it; a user-supplied command goes where STEP 6 says; `## Delegation Bounds` stays as
    reviewed. Otherwise answers given at sign-off drop out when a go-back and revise regenerates the
    brief.
  - **Otherwise, a targeted pass.** Change only what one of these names, and leave the rest as it is:
    - every step that holds only its draft fields: expand it
    - every finding `validate_document` reports
    - every `[mechanical]` finding in the latest critic entry, when that entry's assessment summary
      (the first line under its `## Iteration N - Score: X` heading) starts with
      `Review target: brief`. Skip a finding that no longer holds, and skip one an SD with
      `supersedes=unresolved-checks` accepted. Ignore entries whose summary starts with
      `Review target: design`; those are the architect's.
    - every SD whose `supersedes=` names an OD or CQ and whose ID the brief does not yet cite:
      apply its decision to what its `affects=` names, and cite its ID there. A command the user
      supplied replaces phase 1's marker wherever that language's command goes. When the user left
      the choice to the implementer (a CQ's Option A), add one line citing the SD under
      `### Implementer's discretion`, or under `### Escalate if` when the SD says to stop and ask.
      *Corrected in stage S4:* this said only "cite it where its `affects=` points". Scope 9 has
      the finalizer apply every `BRIEF_QUESTIONS` answer, a CQ's Option B and the verify-command
      OD's Option A included, and a citation alone would leave the marker in place.
- **STEP 3, verify every path before citing it** (Glob or Read):
  - A Grounding, exemplar, convention or `modify` path exists.
  - Each `Files` verb matches the disk: `modify` for a path that exists, `create` for one that
    does not, flipped when it does not match (STEP 5's one allowed correction). *Corrected in stage
    S4:* this replaces "a `create` path does not exist; skip this when `### Shape Gate` is
    `shape-amended`". Phase 2's B24 forbids any phase subagent to set, test or branch on a marker
    value, and `test_no_phase_subagent_sets_tests_or_branches_on_a_stage_marker_value`
    (`tests/unit/templates/test_phase_cooperative_flow.py`) counts every occurrence of every
    `ShapeGate` value in the body. The rule needs no marker. On a first pass the skeletons do not
    exist until Step 11.4, so they stay `create`. On a re-opened phase they exist, so they become
    `modify`, which is true for the implementer. `seam-path-not-in-any-step` reads every backticked
    path in `Files` whatever its verb, and materialization is create-only, so nothing downstream
    depends on the verb.
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
- **STEP 6, commands.** `Verify` and Checklist `(verify: …)` commands are the `[commands].test`
  value (one rule for the architect, the design critic, the finalizer and the brief critic, as in
  phases 1 and 3; *stage correction, pass B*); `## Exit criteria` commands are any `[commands]` value
  (`test`, `coverage`, `type_check`, `lint`). Both come only from `project_config_context_markdown`,
  for the language that owns the files, or from an SD in which the user supplied one. Never
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
    reproduces, and restore that section from the approved copy at `phase_file_path` (never
    `### Success Criteria`, which is append-only). Leave `owner: orchestrator`
    findings untouched. Glob every `paths_to_verify` entry: a missing `grounding` path is corrected
    or its line removed, and a `create` or `modify` path with the wrong verb gets the other verb
    (STEP 5). Glob reads `[` as a character class, so write each `[` of a path as `[[]` (a route
    segment such as `[id]` then matches itself); the brief critic's path check does the same. Repeat at most twice.
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

**Landed in stage S4 (2026-11-17).**
- **Registration.** Every site is in, at these anchors:
  - `PHASE_FINALIZER` at `src/platform/tool_enums.py:157`
  - `PhaseFinalizerAgentTools` at `src/platform/models/phase.py:198`, with its `WRITE` grant in
    `builtin_tools` like the architect's
  - the import and export at `src/platform/models/__init__.py:20` and `:80`
  - `create_phase_finalizer_agent_tools` at `src/platform/template_helpers.py:876`, after
    `create_phase_critic_agent_tools` (`:848`)
  - `add_task_agent(RespecAIAgent.PHASE_FINALIZER)` at `:220`
  - `src/platform/templates/agents/__init__.py:15` and `:34`
  - in `src/platform/template_generator.py`: the imports at `:30` and `:54`, `_AGENT_NAMES` at
    `:120`, the tools at `:277` and the spec at `:304`
  - codex's rename is `_agent_runtime_name` (`src/platform/tui_adapters/codex.py:389`)
  - `expected_agents_count` (`template_generator.py:157`) moved every count pin by itself
- **The grant** is `get_document`, `update_document`, `get_feedback` (`count=1`, as the architect's:
  the latest critic entry plus every user entry), `get_previous_analysis`, `validate_document`
  (phase 3's key-mode call with `implementation_markdown`), and `Read`, `Glob`, `Grep`, and
  `Write(.respec-ai/plans/*/phases/*/implementation.md)`.
- **New shared constants** in `src/platform/templates/phase_contract_grammar.py`:
  - `SUCCESS_CRITERION_PLACEHOLDER`. The architect's `technical_phase_template` now uses it, and
    the rendered architect is byte-identical.
  - `ASK_USER_COMMAND_MARKER`: phase 1's exact text, which the architect and the critic still
    write literally.
  - `DESIGN_REVIEW_TAG` and `BRIEF_REVIEW_TAG`: the Assessment Summary prefixes (Scope 0,
    amendment 4). The finalizer imports them, and the critic is to import them in Scope 8, so the
    critic and the finalizer cannot drift apart.
- **Readings the template fixes** where the steps above are silent:
  - **User entries.** `## User Input` entries are context only, and whatever the user decided
    reaches the finalizer as an SD. The finalizer stores no notes, so it cannot track which entries
    are new the way the architect does.
  - **Delegation Bounds.** Its lines are added only in a targeted pass, for an SD whose
    `supersedes=` names an OD or CQ that the brief does not yet cite. A full pass never touches the
    section, so the critic's reviewed-sections check cannot see a difference.
  - **Unfixable critic findings.** A brief critic finding whose fix would change what a MANDATORY
    REVIEWED block keeps is skipped. It reaches the user through Step 10.7's unresolved checks,
    where "go back to design review" is offered. It is not turned into an OD, because an OD answer
    goes to the finalizer, which cannot apply a design change.
  - **Drift.** An `owner: architect` finding is restored from the approved text a
    `Reviewed Section Changed` entry quotes, or else from the text STEP 1 retrieved. When that text
    already carries the finding, it is left.
  - **Full pass.** It expands only the steps that hold just their draft fields. A finalized step
    kept by a post-finalize `revise` keeps its fields, and STEP 7 corrects any ID it cites that no
    longer resolves.
- **Tests.** `tests/unit/templates/test_phase_finalizer.py` holds B10, B11 and the template's
  contract:
  - its inputs
  - the MCP tools it holds equal the ones it invokes, and nothing else is invoked
  - it rehydrates before choosing its scope
  - it writes both files before validating them
  - a content-loss check after every store
  - owner routing in the self-check, and the `paths_to_verify` kinds it globs
  - its write path matches the grant and the architect's path
  - the review tags, phase 1's marker, `- None` research, and canonical decision entries
  - the shared forms shown verbatim

  The B10 runtime-name test checks the adapter's rendered invocation against the written artifact
  on each TUI. That the command actually invokes the finalizer is S6's (`invoke_finalizer`,
  Scope 9).
- **Scope 11 changes.**
  - The finalizer joined `TestAgentImperativeLanguageAudit`, the B8 four-section-report and B24
    stage-marker tests in `test_phase_cooperative_flow.py`, and phase 3's "only MCP tools they
    declare" test.
  - `test_phase_relay_guards.py` scans every agent spec and lists none, so it needed no edit.
  - The B16 coverage assertion is in `test_phase_language_neutrality.py`: `REQUIRED_TEMPLATES`
    includes the finalizer, and a scanned agent body holds `IMPLEMENTATION_BRIEF_EXAMPLE` and every
    `BRIEF_SECTION_PLACEHOLDERS` body, compared line by line with indentation stripped.
    `ClaudeCodeAdapter().brief_handoff_extension` waits for S6.

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
  sign-off, on a re-opened phase (`shape-amended`), or when a run resumed after Step 10.7 had run:
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

**Landed in stage S5 (2026-11-17).** The architect (`src/platform/templates/agents/phase_architect.py`)
now does all of the above. Re-found anchors: STEP 3's draft branch (`ELIF phase_mode == "draft"`),
the revise branch, STEP 4.5's `paths_to_verify` loop, and the "IMPLEMENTATION PLAN STRUCTURE
(CONCRETE EXAMPLE)" lead-in. Readings this stage fixed:
- **The revise trigger is the sections, never the marker.** The rule fires when the document holds
  any of `## Grounding`, `## Behaviors & Acceptance` or `## Guardrails`. Its names come from
  `Phase.BRIEF_SECTIONS` minus Delegation Bounds. Scope 7's "on a re-opened phase
  (`shape-amended`)" is only the motivation: phase 2's B24 forbids an agent to test a marker value.
  The rule runs "whatever STEP 2 found", because Step 11's missing-`implementation.md` path (Scope
  9) runs a `revise` with nothing new that still has to strip the sections. Removal is real on
  both backends: an agent `update_document` without the three H2s drops them from
  `additional_sections` (probe on InMemory and the dev Postgres, 2026-11-17).
- **The architect acts only on design-review findings.** `LATEST_BLOCKERS` and `LATEST_KEY_ISSUES`
  are read only from a critic entry whose first line starts with `DESIGN_REVIEW_TAG`. After "go
  back to design review" from sign-off, the latest entry is the brief review's, and its findings
  are the finalizer's. The architect's `get_feedback` has `count=1`.
- **Draft fields.** Steps carry `- **Goal:**`, `- **Files:**` and `- **Depends on:**`. A `Files`
  verb follows the disk (`create` for a path that does not exist yet, a Skeleton Index path
  included until sign-off writes it), matching the finalizer's S4 rule. The carry-forward block's
  `**Actions**` item became "the Goal of a step it binds". The embedded example keeps its
  finalized form, and its lead-in names the three parts and three fields the architect writes.
- **Retired sections.** The spec's grep finds no hit in the architect, the critic, the command or
  `create_phase.py`. `tests/unit/templates/test_phase_brief_format.py` pins it with
  `retired_section_mentions` (`tests/support/section_names.py`), which reads the names from the
  retired fields' `HEADER_FIELD_MAPPING` entries; S1's `RETIRED_FIELDS` moved there.
  Re-homed:
  - PLAN_ARCHITECTURE goes to the Design Shape.
  - PLAN_TECHNOLOGY_DECISIONS goes to the design and its decisions.
  - PLAN_QUALITY_BAR goes to SC-n entries with their `measure:`.
  - PLAN_ANTI_REQUIREMENTS goes to `### Out of scope`; it used to go to the Overview's Scope,
    which is frozen.
  - STEP 1.5's "apply the constraint into … Architecture" now says Design Shape.
  - "Omit the content instead of TBD/N/A" now says a required H3 holds `- None`.
- **Pinned literals updated.**
  - `tests/unit/templates/test_phase_design_layer.py:35` now asserts
    `in Objectives, Scope, Deliverables (the Overview)` and that `Development Plan` is absent.
  - `test_phase_architect_template_requires_semantic_reference_application`
    (`tests/unit/templates/test_agent_templates.py`) now asserts `Design Shape` in place of
    `Architecture`.
- **Tests:** `tests/unit/templates/test_phase_brief_format.py`, "Scope 7" (draft fields, design
  half in the shared forms, never the finalizer's sections, revise after finalize, the four
  note lists against the finalizer's, design-review findings only, retired sections), and
  `tests/unit/templates/test_phase_structural_gate.py`:
  - the architect's Glob kinds
  - its self-check owner (day-one green; break evidence)

### 8. The critic (post-phase-2 `phase_critic.py`)

The `review` branch splits on the new scalar `review_target`, with branch headers written as
`IF review_target == "design":` and `ELIF review_target == "brief":`, so a test can extract each body
the way `_phase_mode_branch_body` does. Both branches store feedback whose `- **Assessment Summary**:`
value starts with `Review target: design` or `Review target: brief`, then a dash and the summary
(Scope 0, amendment 4). `get_feedback` drops anything before the feedback's H1 and never renders the
detailed feedback, so the summary is the only place the tag survives.

- **`design`** is phase 2's check set, plus phase 3's relay, unchanged except for one filter. On a
  document that already holds finalize-only content (a re-opened or resumed phase), it raises no
  finding about that content, and it relays only `owner: architect` implementation findings (Scope
  5). Phase 3 left two phase 2 critic checks for phase 4 to replace (phase 3, Out of scope):
  - "every `#### Step N:` names the files it touches" (the `Step Names No Files` marker): delete it
    from the critic.
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
   [<part>] — <detail>`, dropping the space and `[<part>]` when `part` is empty. Never re-raise
   `structural_findings`; the Step 10.7 gate owns them.
1. **Cold-start check.** For each `#### Step N:`, take only that step's brief, the `phase.md`
   sections its `Context` cites, and the repository. List every point where a fresh agent would
   have to guess. Classify each:
   - **`[mechanical]`:** the answer exists in the brief or the repository but is not cited.
     Examples: a missing pointer, a missing T-n. These go to `### Blockers`. A `Verify` value that
     does not match the config is check 4's.
   - **Not a gap:** a `Verify` that is phase 1's `ask user` marker. Either an SD records the user's
     choice for that language, or the finalizer's own decision asks it at sign-off (Scope 6, STEP
     6). Raising it again would repeat a question the user has answered or is about to answer.
     *Corrected in stage S5:* this said "or the finalizer's report already asks it", but the
     critic never sees the finalizer's report; the finalizer always asks when no SD records the
     choice, so the marker is never a gap.
   - **A design gap, not a finding:** a gap that only a change to what the finalizer keeps would
     close (a file missing from `Files`, an undeclared dependency on a file another step creates)
     goes to `### Recommendations` as advisory, and to the critic's `## For the user`, as "going
     back to design review closes it". *Corrected in stage S5:* the spec listed both as
     `[mechanical]` examples, but Scope 6 STEP 5 forbids the finalizer to change the paths in
     `Files` or `Depends on`, so the finding would have no fix its owner may make. It would burn
     both repair rounds and reach the user as an unresolved check. Going back to design review is
     still offered at sign-off.
   - **`[judgment]`:** the answer needs a choice nobody made. Examples: unspecified error behavior,
     ambiguous seam semantics, a missing non-functional target. These go to `### Key Issues` and
     become `CQ-NNN`, where Option A is "leave it to the implementer's discretion (recorded under
     Delegation Bounds)" and Option B is "settle now: <the critic's proposal>". This fits the README
     rule that Option A is "keep as designed". Reuse a CQ ID for the same finding across rounds
     (phase 2, judgment calls).
2. **Reviewed sections are unchanged.** Compare the sections the finalizer must reproduce (Scope 6,
   STEP 4) between `phase_file_path` and `get_document`. The file on disk is the draft the user
   approved, because Step 10.7 writes it before the finalizer runs (Scope 9).
   - Any difference is `[mechanical]`, as `[Reviewed Section Changed - BLOCKING]`. The finding names
     the section and quotes the approved text, so the finalizer restores it without reading the disk
     copy.
   - `### Success Criteria` is append-only: added `SC-<n>` entries, completed `measure:` parts and a
     the `(target: <value>, SD-<n>)` suffix (after one space) an SD supplied for an unmeasured criterion
     are not differences; an edited, removed or renumbered criterion is.
   - If `phase_file_path` cannot be read (phase 2: the draft-on-disk guarantee covers only the
     markdown platform), skip this check and say so in the feedback. Never report it as passed.
3. **Paths.** Glob every `paths_to_verify` entry from check 0, choosing the marker by `kind`, as
   phase 3 does for its kinds. Each failure is one `[mechanical]` blocker:
   - a missing `grounding` path: `[Grounding Path Invalid - BLOCKING]`; the finalizer corrects or
     removes the line
   - a missing `modify` path, or an existing `create` path: `[Step File Verb Invalid - BLOCKING]`;
     the finalizer flips the verb (Scope 6, STEP 5). *Corrected in stage S4:* there is no
     `shape-amended` exception. The finalizer writes `modify` for every path that exists (Scope 6,
     STEP 3), so on a re-opened phase an existing skeleton path is no longer a `create` item. A
     marker test in the critic would also break phase 2's B24, which already covers the critic.

   These need the project, so they run here and not on the server (F29).

   **Found in stage S4: a live regression for Scopes 7 and 8; no test catches it.** Since stage
   S3, `validate_document` adds each step's `Files` paths to `paths_to_verify` as `create` or
   `modify` whenever `implementation_markdown` is passed, and the architect's self-check and the
   design-review critic both pass it.
   - The architect's STEP 4.5 (`src/platform/templates/agents/phase_architect.py:641-648` before S5, now `:658-683`) Globs
     every entry cited in text it owns, with no `kind` filter, and "cites the file that exists, or
     removes the citation" when nothing matches. A draft's `create` path never exists yet, so the
     architect would strip or replace its own `create` items.
   - The critic's Cited Paths check (`phase_critic.py`, "For each entry in
     VALIDATION.paths_to_verify") names a marker only for `read`, `best-practices` and
     `constraint`, so a `create`, `modify` or `grounding` entry has no defined outcome on
     `design`.

   Scope 7 limits the architect's Glob to the `read`, `constraint` and `best-practices` kinds, and
   Scope 8 does the same on `design` and adds this check's markers on `brief`. The finalizer
   already globs only `grounding`, `create` and `modify`. **Fixed in stage S5**, pinned by
   `test_the_architect_globs_only_the_kinds_of_path_it_cites_itself` and
   `test_each_review_checks_existence_only_for_its_kinds_of_path_choosing_the_marker_by_kind`
   (`tests/unit/templates/test_phase_structural_gate.py`).
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

**Landed in stage S5 (2026-11-17).** `src/platform/templates/agents/phase_critic.py`:
- **Structure.** `## REVIEW CHECKS` is one `text` block:
  - `IF review_target == "design":` and `ELIF review_target == "brief":` hold their checks inline,
    and a closing `ELSE:` fails closed.
  - The MANDATORY PHASE MODE PROTOCOL also rejects an unknown `review_target` before anything is
    stored.
  - Each branch sets `REVIEW_TAG` to `DESIGN_REVIEW_TAG` or `BRIEF_REVIEW_TAG` (imported). The
    stored `- **Assessment Summary**:` value is `[REVIEW_TAG] — [one sentence]`.
  - STEP 3 takes the Progress baseline only from earlier entries of the same target, and counts
    every entry's CQ IDs.
  - STEP 4 (the plan) runs only on `design`.
- **Inputs.** `review_target` is a Scalar Input. `phase_file_path` is under its own
  `### Brief Review Inputs` heading, so phase 2's
  `test_every_input_the_orchestrator_passes_is_one_the_agent_declares` can tell a brief-only input
  apart: its rows now name the extra headings an invocation passes.
- **Design branch.** Phase 2's and phase 3's checks, with these changes:
  - `Step Names No Files` is deleted.
  - The relay is filtered to `owner: architect`.
  - Cited Paths is limited to `read`, `best-practices` and `constraint`.
  - A paragraph forbids findings about finalized content on a re-opened or resumed phase.
  - Plan Constraint Fit and the reference-application check are re-homed off the retired sections
    (Design Shape, decisions, `### Out of scope`, SC-n with `measure:`). Before this, they would
    have raised false Plan Constraint Violations against sections no longer generated.
- **Brief branch.** Checks 0–5 only, naming no design-review marker.
  - **Markers:**
    - check 1: `[mechanical] [Cold Start Gap - BLOCKING]` and `[judgment] [Cold Start Decision]`
    - check 2: `[mechanical] [Reviewed Section Changed - BLOCKING]`
    - check 3: `Grounding Path Invalid` and `Step File Verb Invalid`
    - check 4: reuses `Verify Command Not Configured`
    - check 5: `[mechanical] [Success Criterion Missing - BLOCKING]` and
      `[judgment] [Unmeasured Success Criterion]`

    No marker slug contains `coverage`, which phase 2's research guard rejects.
  - **Check 2** compares `REVIEWED_PHASE_SECTIONS`, a new constant in `phase_contract_grammar.py`
    that the finalizer now also renders (the render is unchanged apart from line wrapping).
    - Beyond the Success Criteria rule, two more things are not a difference: the next unused
      `SC-<n>:` prefixed to an unnumbered criterion (S4's one allowed edit), and an added
      Delegation Bounds line citing an SD that supersedes an OD or CQ (Scope 6 STEP 2's
      exception). Without them, a targeted repair pass inside Step 10.7 would be ordered to undo
      itself.
    - The approved text is quoted on the blocker's one line, each line break written as
      `QUOTED_LINE_BREAK` (`⏎`). A probe (2026-11-17) showed `get_feedback` flattens a multi-line
      blocker and splits its nested bullets into separate marker-less blockers. The finalizer's
      restore rule names the same mark.
  - **Check 3** globs only `grounding`, `create` and `modify`. A missing `read` or `constraint`
    path sits in lines the finalizer reproduces, so it is not the finalizer's to fix, and the
    design review checked it.
  - **Check 4** also requires each `## Exit criteria` command to be a config value, and each
    Checklist `(verify: …)` to equal its step's `Verify` (Scope 3's finalizer rule; a mismatch has
    one fix).
- **Tests:**
  - `tests/unit/templates/test_phase_brief_review.py` (new): B13's critic half, the branch
    structure and fail-closed `ELSE`, the inputs, the tag, the three markers, check 2 and its
    skip, and the quote form. Branches are read with `TemplateContract.condition_block`
    (`tests/support/template_contract.py`), which stops at the block's end so the last branch
    never takes in the output format.
  - `tests/unit/templates/test_phase_structural_gate.py`:
    - B16's relay half is rewritten per target.
    - The existence test is per target.
    - `_KEPT_MECHANICAL_RULES` drops `step-names-no-files` and adds the five new mechanical
      markers.
    - B18's routing half: finalizer findings fall in neither Step 9 list.
  - `test_critic_raises_implementation_plan_defects_as_mechanical_findings` and
    `test_template_declares_exactly_the_inputs_the_orchestrator_passes`
    (`tests/unit/templates/test_agent_templates.py`) are updated for the deleted marker and the new
    inputs.
- **Left for S6 (Scope 9):**
  - `invoke_critic_review` does not pass `review_target: design` yet, so the three
    `respec-phase-critic-invoke_critic_review` cases of
    `test_every_input_the_orchestrator_passes_is_one_the_agent_declares` are red until it does.
  - S6 also adds the row `(CRITIC, 'invoke_critic_brief_review', ('### Brief Review Inputs',))`.

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
  The critic declares `phase_file_path` under its own `### Brief Review Inputs` heading (stage S5),
  so add the row `(CRITIC, 'invoke_critic_brief_review', ('### Brief Review Inputs',))` to
  `test_every_input_the_orchestrator_passes_is_one_the_agent_declares`
  (`tests/unit/templates/test_phase_cooperative_flow.py`).
- **`brief_handoff_extension`:** see Scope 10.

Also add `review_target: design` to phase 2's `invoke_critic_review` (Scope 0, amendment 1). Since
stage S5 the critic declares `review_target`, so the three
`respec-phase-critic-invoke_critic_review` cases of
`test_every_input_the_orchestrator_passes_is_one_the_agent_declares` stay red until this lands.

**`IMPLEMENTATION_PLAN_PATH`.** Phase 2's Step 3 sets it as
`dirname(PHASE_FILE_PATH)/implementation.md`, the derivation frozen respec-code uses
(`code_command.py:230-231`). It is set in Step 3.3 (`phase_command.py:542`), before Step 10.7. On
the markdown platform it is the file the architect and the finalizer write. Step 11 and the handoff use it.

**Step 10.7: Finalize the brief.** A new `#### Step 10.7: Finalize the brief` after Step 10.6 and
before Step 11. Phase 2's tests anchor on step numbers, and 10.5 and 10.6 are taken (the hand edit
and the choice), so add it as `10.7` and renumber nothing. Step 10.6's "Approve the design" branch
(its final `ELSE`) goes to Step 10.7, not to Step 11, and Step 10.7 ends by going to Step 11, so no
route into Step 11 skips it. The step has no touchpoint token and no `WAIT for` (B12; phase 2 B10).

0. Set `REPAIR_ROUNDS = 0` and `STRUCTURAL_LEFTOVERS = []`. Set `BRIEF_QUESTIONS = []` only on a full pass (none of
   `## Grounding`, `## Behaviors & Acceptance`, `## Guardrails` present: the finalizer's STEP 2 test); on a targeted
   pass keep the entries no SD supersedes, so a go-back then approve with no change keeps the finalizer's
   open questions. `BRIEF_QUESTIONS` and `BRIEF_SUMMARY` are initialized at the start of the run. Write the current MCP document
   (`get_document`) to `PHASE_FILE_PATH`, the same way Step 10 writes each review iteration.
   - The critic's reviewed-sections check compares against this copy. Step 10 may have recorded SDs
     after its own disk write, so without this write the critic would ask for them to be
     "restored" away.
   - This write cannot clobber a hand edit: phase 2's Step 10 re-reads the disk before acting on any
     choice, and runs the hand-edit path (then Step 9) when the file differs from what it wrote.
1. Invoke the finalizer with `{tools.invoke_finalizer}`, and wait for its report.
   - `failed` or a malformed report: stop with the detail shown (fail-closed).
   - `needs-user`: its `## Decisions needed` join `BRIEF_QUESTIONS`, the sign-off queue.
2. Run `{tools.validate_document_structure}`, phase 3's key-mode gate call. If the call fails, end
   the run with the exact error before any agent is engaged, as Step 9's gate does
   (`phase_command.py:864-870`). It carries no `implementation_markdown`: the orchestrator never holds that body (phase 3, "Why the critic
   verifies cited paths"). Implementation findings reach the orchestrator through the critic's relay
   in step 3, and the finalizer has already self-checked. Write `structural_findings` literally, as
   phase 3 does.
   - `FINALIZER_FINDINGS` = the `structural_findings` whose owner is `finalizer` or `architect`
     (Scope 5). `ORCHESTRATOR_FINDINGS` = those whose owner is `orchestrator`.
   - If `FINALIZER_FINDINGS` is not empty and `REPAIR_ROUNDS < 2`: `REPAIR_ROUNDS += 1`, invoke the
     finalizer again with `{tools.invoke_finalizer}`, and return to this step's gate (the
     `BRIEF GATE:` label, never the top of Step 10.7). No user prompt is on this path.
   - Otherwise `STRUCTURAL_LEFTOVERS` = every finding in both lists, written exactly as phase 3's
     gate writes it (`<check> <subject> [<part>] — <detail>`), so an accept-as-is SD matches it on
     later rounds.
3. `REVIEW_ROUND += 1`, then invoke the critic with `{tools.invoke_critic_brief_review}`. Keep phase
   2's fail-closed persistence checks. Then `BRIEF_REVIEW_DECISION = decide_loop_next_action`:
   - `completed`: go to Step 11.
   - `refine` or `user_input` while `REPAIR_ROUNDS < 2`: `REPAIR_ROUNDS += 1`, invoke the finalizer
     (never the architect), and return to step 2 (`BRIEF GATE:`). `user_input` is repaired like `refine`, as in
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
   - Keep the critic's latest `## For the user` as `BRIEF_REVIEW_SUMMARY`. It names each design gap
     that only going back to design review closes (Scope 8 check 1). No repair round can close such
     a gap, because the finalizer may not change the paths in `Files` or `Depends on`, so the
     critic raises it as advisory, not as a finding. *Added in stage S5.*
4. No `bp-pipeline` invocation, and no route to Step 7, anywhere in Steps 10.7, 11 or 12. Research is
   reachable again only through Step 11's "go back to design review" (B13).

**Step 11 (Sign-off)** stays touchpoint 3:
- Show the finalizer's `## For the user`, then `BRIEF_REVIEW_SUMMARY` when it names a design gap
  (its fix is the "go back to design review" choice offered next), then `UNRESOLVED_CHECKS` as one
  decision (accept as-is, or go back to design review), then the queued decisions: the finalizer's ODs and the brief review's
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
  the key-mode gate **once**, with the same fail-closed branch as Step 9's gate.
  Do not invoke the critic again: re-running it after the user decides is the cycle this effort
  removed. If the gate still reports findings, ask them as one unresolved-checks decision in this
  same step, guarded so it appears only then. It adds no touchpoint.
- Then continue with phase 2's Step 11: its single sign-off prompt, then, in phase 2's order, the
  `implementation.md` existence check, materialization, one `store_document` carrying the
  constraint line and `shape-settled`, the final write of `phase.md` to disk, and the commit offer.
  "Go back to design review" returns to Step 10. A `revise` removes the finalizer's sections (Scope 7), so
  the brief is written in full after the next approval; an approval with no change keeps them and Step 10.7
  repairs and reviews the brief again, keeping its unanswered questions.
- **The finalized brief reaches the disk before the sign-off.** Step 11.1 starts by writing the stored
  document to `PHASE_FILE_PATH` (and updating `LAST_WRITTEN_PHASE_MARKDOWN`), and writes it again after the
  finalizer applies the sign-off answers, so the user reads what they sign and a stopped run never leaves
  the approved design as the only copy. No write is added inside Step 10.7's BRIEF GATE loop.
- **Fresh budget on a send-back.** Each route from Step 11 into Step 9 (the design-change send-back and the
  missing-plan revise) sets `REPAIR_ROUNDS = 0`.
- **One change to that sequence:** Step 10.7 checks for `implementation.md` before its first finalizer pass and
  goes to Step 11.3 when it is missing, so the rebuild below is reached from there too. If the check finds `implementation.md` missing,
  re-engage the architect in `revise` once, as phase 2 does, but then go to Step 9 instead of
  continuing the sign-off. The finalizer cannot rebuild the file, because the draft fields,
  `### Staging`, `## Policy` and `## Checklist` are the architect's (Scope 3). That `revise` also
  strips the finalizer's sections (Scope 7), so the design passes review and Step 10.7 again before
  sign-off. If the file is missing again when Step 10.7 or Step 11 is next reached, fail closed.
- **A hand edit at sign-off is never overwritten (review fix, 2026-11-18).** The finalized brief is
  on disk at the sign-off prompt, so the user can edit it there, and Step 11.5's final write would
  replace that edit. Like Step 10.4, Step 11.2 re-reads `PHASE_FILE_PATH` before acting on any
  choice. When it differs from `LAST_WRITTEN_PHASE_MARKDOWN`, it sets `REVIEW_CHOICE` to "I edited
  phase.md myself", resets `REPAIR_ROUNDS` and goes to Step 10.5, which validates and records the
  edit and goes to Step 9; the design is approved again before sign-off
  (`test_a_hand_edit_made_at_sign_off_is_reviewed_before_any_sign_off_choice_acts`).

**Every SD writer** for an answered OD or CQ includes `affects=`, in Steps 6, 10 and 11.
Pre-phase-2 examples are at `phase_command.py:573-574` and `:580-581`.

**Step 12's storage banner** (phase 2 rewrites it to name every disk write) also names Step 10.7's
write of `PHASE_FILE_PATH` and the finalizer's `implementation.md`.

**The handoff** (Scope 10) is shown in Step 12. Step 4's `shape-settled` branch reaches it when the
user chooses the handoff instead of re-opening (README "Stage marker"): its "Show the handoff"
choice goes to Step 12, as phase 2 decided ("Step 4's 'show the handoff' goes to Step 12, whose
platform store rewrites the same content", phase-2-cooperative-flow.md). *Corrected in stage S6:*
this said the handoff is shown "in Step 12, and in Step 4's `shape-settled` branch". Rendering it
in Step 4 as well would show it twice on that route, and ending the run in Step 4 instead would
overturn phase 2's routing.

**Landed in stage S6 (2026-11-17).** Re-found anchors:
- `PhaseCommandTools.invoke_finalizer`, `invoke_critic_brief_review` and `brief_handoff_extension`
  (`src/platform/models/phase.py:44-52`), rendered in `create_phase_command_tools`
  (`src/platform/template_helpers.py:282-300`).
  - `invoke_finalizer` passes the three IDs and `project_config_context_markdown`, with no
    `phase_mode`, because the finalizer declares none.
  - `invoke_critic_review` gained `review_target: design`.
- In `src/platform/templates/commands/phase_command.py`:
  - Step 10.6's final `ELSE` goes to Step 10.7 (`:1353`).
  - `#### Step 10.7: Finalize the brief` is at `:1356`, with its gate at `BRIEF GATE:` (`:1378`).
  - Step 11.1 is at `:1455` and Step 11.3 at `:1591`; Step 12.3 renders the handoff (`:1794`).
  - The new Python helpers are `_finalizer_engagement`, `_critic_persistence_checks`,
    `_brief_checks_decision` and `_brief_handoff` (`:40-128`).

Readings this stage fixed where the steps above are silent:
- **One heading, one re-entry point.** Step 10.7 is one `####` heading with no Step sub-headers,
  so `step_body('10.7')` holds all of it. Every repair returns to the `BRIEF GATE:` label, never to
  the top: re-running step 0 would reset the budget (no repair loop would end) and rewrite
  `PHASE_FILE_PATH` with the finalized brief, so the critic's reviewed-sections check would compare
  the brief with itself.
- **Brief state stays out of the design-review variables.** Step 10.7 uses its own names:
  - `BRIEF_VALIDATION` and `BRIEF_CRITIC_REPORT`, alongside `FINALIZER_REPORT`,
    `BRIEF_REVIEW_SUMMARY` and Step 11's `SIGN_OFF_VALIDATION`.
  - It never writes `CRITIC_REPORT` or `OPEN_CRITIC_QUESTIONS`, so Step 11.1's `REMAINING` and a
    return to Step 10 never see a brief CQ.
  - It reuses Step 9's `PRE_PHASE_LOOP_STATUS`, `POST_PHASE_LOOP_STATUS` and `PHASE_FEEDBACK`,
    because Steps 9 and 10.7 now share one persistence block. Step 9's render changed only by
    `review_target: design` (diffed on all three TUIs).
  - Step 0 also resets `UNRESOLVED_CHECKS`. Step 10.2 already clears it, so this is only a guard
    against stale findings.
- **`BRIEF_QUESTIONS`.** It takes the finalizer's ODs from every finalizer report. An OD is skipped
  when an entry with the same title and Affects line is already queued, because a repair re-raises
  an unanswered verify-command OD. The brief review's CQs come from the latest review only, as in
  Step 9.
- **Step 11 keeps its numbering.** The additions sit in Step 11.1, after phase 2's `REMAINING` loop
  and its design-change send-back: a design-changing answer regenerates the brief anyway. Phase 2's
  tests read the first accept-all branch of Step 11 and count exactly two
  `DESIGN_CHANGE_SD_IDS.append` lines there. The order is:
  1. `BRIEF_SUMMARY`: the `## For the user` of Step 10.7's first finalizer pass, captured once (on a full pass, or when none is held). A
     repair round's report describes only that repair, so it is never shown here.
  2. `BRIEF_REVIEW_SUMMARY`, when it names a design gap
  3. the unresolved-checks decision
  4. the `BRIEF_QUESTIONS` loop
  5. one store
  6. the guarded once-more pass

  Details:
  - **The unresolved-checks decision** offers "Accept as-is" (phase 2's unresolved-checks SD) or
    "Go back to design review". Both clear `UNRESOLVED_CHECKS`, so Step 10.2 never offers the
    architect the brief's findings.
  - **The `BRIEF_QUESTIONS` loop** offers accept-all, and asks for the command when the user picks
    the verify OD's "Supply the command now". It never touches `DESIGN_CHANGE_SD_IDS`.
  - **The once-more pass** is the finalizer, then the `SIGN_OFF_VALIDATION` gate with its
    fail-closed branch. `UNRESOLVED_CHECKS` becomes every finding that gate reports, whatever its
    owner, because no repair follows. Then a second guarded decision runs, which stores its own
    accept SD.
  - **The once-more trigger** is the spec's literal rule: any SD this step recorded that supersedes
    an OD or a CQ, `REMAINING` answers included.
- **The missing-plan route.** Step 3.3 sets `IMPLEMENTATION_PLAN_REBUILT = false`. The first miss
  at Step 11.3 sets it to true, stores the feedback, revises, then goes to Step 9. A second miss
  fails closed before the architect is engaged again.
- **The handoff** is built by `_brief_handoff` before the f-string. Its braced names stay literal
  for the orchestrator to substitute, and the extension is appended only when
  `tools.brief_handoff_extension` is non-empty.
- **Prose updates.** The preamble's disk-write sentence, Responsibilities, the Orchestration
  Pattern, relay rules 1 and 5, and Step 12's storage items 2 and 4 now name Step 10.7, the
  finalizer and `affects=`.

Tests:
- `tests/unit/templates/test_phase_brief_review.py`, "Orchestrator half" (B12, B13, B14 and B18's
  routing half for Step 10.7), plus the Step 11 contract:
  - the brief questions are asked apart and never reach the architect
  - one finalizer pass and one gate, and no second review
  - both unresolved-checks decisions are recorded or return to design review
  - the plan is rebuilt once, then fails closed

  Its checkers (`routes_into_sign_off`, `research_reached`, `sd_writers_missing_affects`) have
  negative self-tests.
- `tests/unit/templates/test_phase_handoff.py` (B15).
- `test_the_scan_covers_the_claude_code_handoff_instruction` (B16's handoff half,
  `tests/unit/templates/test_phase_language_neutrality.py`).
- The `invoke_finalizer` and `invoke_critic_brief_review` rows of
  `test_every_input_the_orchestrator_passes_is_one_the_agent_declares`.
- `test_critic_review_is_invoked_with_the_round_it_stores_under_and_the_config_context`
  (`tests/unit/platform_tests/test_tool_enums_and_validation.py`) now pins `review_target: design`
  too.

### 10. The TUI-tiered handoff

- **`src/platform/tui_adapters/base.py`.** Add a property `brief_handoff_extension -> str | None`
  returning `None`, next to `subagent_invocation_guardrail`
  (`src/platform/tui_adapters/base.py:85-87`; was `:77-79`). It follows the pattern of
  `ask_user_question_tool_name` (`src/platform/tui_adapters/base.py:39-47`). It is not a
  `BuiltInToolCapability`: it grants no tool, it only renders text.
- **`src/platform/tui_adapters/claude_code.py`.** Override it beside the guardrail property
  (`src/platform/tui_adapters/claude_code.py:61-63`; was `:47-49`), returning a plain (non-f) string. opencode and
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
  (`src/platform/models/phase.py:33`) until its retirement is decided.

**Landed in stage S6 (2026-11-17).**
- **The adapters.**
  - `TuiAdapter.brief_handoff_extension` returns `None` (`src/platform/tui_adapters/base.py:90`),
    beside `subagent_invocation_guardrail` (`:86`).
  - `ClaudeCodeAdapter` overrides it (`src/platform/tui_adapters/claude_code.py:66`), returning
    the class constant `_BRIEF_HANDOFF_EXTENSION` (`:49`), a plain string holding the text above.
- **The command.** `_brief_handoff` builds the portable core with the core's runtime names as
  literal braces. It interpolates only `code_command_invocation`, unwrapped: codex's rendering
  already carries backticks. The extension is indented beneath a line that tells the orchestrator to
  show it, with the same values filled in, for a fresh session.
- **Only Step 12.3 renders it.** Step 4's "Show the handoff" reaches it there (Scope 9's corrected
  handoff line).
- **The README phase 4 probe** prints a match: `66:    def brief_handoff_extension(self) -> str | None:`.

### 11. Tests that change

- **`tests/unit/templates/test_agent_templates.py:676`** (`TestAgentImperativeLanguageAudit`, was `:660-679`,
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
- **`tests/unit/templates/test_phase_implementation_plan_gate.py:25`:** update the import (Scope 4;
  done in stage S1, now `:27`).
- **`tests/unit/templates/test_phase_design_layer.py:35`:** see Scope 7.
- **New tests**, colocated with their precedents:
  - B1 in `tests/unit/models/test_phase_additional_sections.py`
  - B2–B4 in a new `tests/unit/templates/test_phase_brief_format.py`
  - B5–B9 and B18's ownership half in phase 3's `tests/unit/utils/test_phase_structure.py`, and
    B18's routing half in phase 3's `tests/unit/templates/test_phase_structural_gate.py`
  - B17 in `tests/unit/models/test_content_loss_detection.py`, and its two routes in
    `tests/unit/mcp/test_document_validation.py`
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
  These belong to phase 2. Phase 4 adds Step 10.7, the sign-off additions in Scope 9, the
  architect's post-finalize `revise` rule (Scope 7) and the handoff, and nothing else to the flow.
- **Handoff extensions for opencode or codex.** Each gets the declaration point (`None`) only.
- **Enforcing the `implementation.md` write scope on opencode or codex** (F14, decisions.md caveat).
- **Re-running design judgment, or research, after design approval.**

## Exit criteria

- [x] B1–B18 each observed failing first, for the right reason, then passing.
- [x] `uv run pytest` is green (3265 passed, 1 skipped, 2026-11-17). Phase 2 removes tests, so compare against the count phase 3 left,
      not the README's 2026-11-13 baseline.
- [x] The guard tests pass on all three TUIs, the finalizer included: language neutrality, no
      question tool in any agent, no `context: fork`, and H2 shadowing. Each guard's negative
      self-test fires.
- [x] `uv run respec-ai regenerate --force --tui all` completes in a scratch project, with model
      tiers configured for opencode and codex first (F37). Inspect the output directly:
  - Claude Code: the finalizer agent file exists, its `tools` hold
    `Write(.respec-ai/plans/*/phases/*/implementation.md)` and no `AskUserQuestion`, and
    `respec-phase.md`'s `allowed-tools` holds `Task(respec-phase-finalizer)`.
  - opencode: `permission.task` allows the finalizer.
  - codex: an agent named `respec-phase-finalizer-agent` exists, and the command invokes that name.
- [x] The completion probe in **Start here** reports "done".
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

  **Headless run on 2026-11-18** (method in [phase-2-manual-checks.md](phase-2-manual-checks.md),
  "Headless run"; sonnet subagents):
  - **End to end (P4.1-P4.3) passes.** Approval went to sign-off with zero prompts in four runs: the
    finalizer, one structure check, then the brief critic. The brief summary was never displayed
    (D1). Going back from sign-off reran the finalizer, and `phase.md`'s three sections were
    regenerated with the new test. `implementation.md` changed in the affected step, not in Start
    here, Exit criteria or Deviations. No retired section appeared, and the frozen formats were
    kept.
  - **Brief quality (P4.5) passes, with issues.** Grounding paths exist, Delegation Bounds are
    specific, Behaviors & Acceptance is a map, and every step has all seven fields. Sign-off asked
    no cold-start questions. Sizes were 10.4-20.4 KB for the two files together. The finalizer left
    the approved design untouched. The issues:
    - `Files` says `create` for files an earlier phase writes, and `Prerequisites: None` despite a
      cross-phase dependency;
    - stale SD text survived review;
    - the per-path materializer SDs are padding (D6).
  - **Frozen readers (P4.4) are partial.** The gate passed, and the coder's first action was reading
    `implementation.md`. respec-code did not display its step-detection line.
  - **P4.6 and P4.7 were not run.**
- [x] README "Shared contracts" is amended per Scope 0, findings.md has F40 per Scope 12, the README
      phase 4 probe prints a match, and every `file:line` in this document has been re-verified
      against the code you leave behind.

**Landed in stage S7 (2026-11-17): documents and exit verification.**
- **F40** is in findings.md and cited from the README's "Section naming" bullet. The range is now
  F1-F40 and the count 40 in README.md, decisions.md and findings.md. The README phase 4 probe prints
  `66:    def brief_handoff_extension(self) -> str | None:`. Phase 2's two probes print nothing, and
  phase 3's prints a match.
- **Anchors re-verified** against the code as it now stands. Corrected: `phase_command.py` (Step 10.6
  `:1352-1353`, Step 9 gate `:992-1000`, Step 3.3 `:542`, the seven materializer SDs
  `:1662-1697`), `phase_architect.py` STEP 4.5 `:658`, `phase_critic.py` STEP 5.5 `:256`,
  `models/phase.py` (`HEADER_FIELD_MAPPING` `:24-52`, `build_markdown` loop `:266-275`),
  `template_helpers.py` `_phase_agent_inputs` `:187` and `invoke_critic_review` `:278-283`,
  `template_generator.py` `:157-158`, `codex.py` `_agent_runtime_name` `:389-392`,
  `test_phase_section_references.py:23`, `test_agent_templates.py:676`. Anchors the document
  labels "before phase 4" or "pre-phase-2" are historical and stay.
- **Exit verification.** Regenerate in a scratch project with a scratch HOME gave Claude Code 22,
  OpenCode 21 and Codex 21 agents, and every inspection above passed (57 checks). The real HOME
  config checksums did not change. A scripted end-to-end check through `DocumentTools` stored a
  finalized brief and reported no structural and no implementation findings.
- **Not ticked** (they need a live session): the manual end-to-end run, brief quality, frozen
  readers and the two-language effort-level run. They are written as cold-runnable steps in
  [phase-2-manual-checks.md](phase-2-manual-checks.md) under "Phase 4". OpenCode checks there are
  unverified and not blocking.
