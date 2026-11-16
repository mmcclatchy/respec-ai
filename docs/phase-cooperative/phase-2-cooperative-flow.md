# Phase 2 — The cooperative flow

**Depends on:** Phase 1. **Blocks:** Phase 4, and phase 3's wiring into the draft step (phase 3's
MCP-side checks can be built in parallel with this phase).
**Risk:** high. This phase rewrites the 1,833-line orchestrator, both phase agents and the critic's
loop contract at once. It adds a storage rule whose failure silently marks an unapproved draft as
settled (README "Cross-cutting risks" 2). Its opencode research path has never been run.

## Start here

**Prerequisite: phase 1 is complete.** Both of these must hold:

```bash
uv run pytest -q tests/unit/templates/test_phase_language_neutrality.py          # must exit 0
grep -n -i -E "python|typescript|\.tsx|jsx" src/platform/templates/phase_contract_grammar.py   # must print nothing
```

On 2026-11-13, at commit `a64f0dc`, both fail, which is expected before phase 1. The test file does
not exist yet, so pytest exits with code 4, and the grep prints hits at lines 12, 17, 20, 22, 32 and
33. Do not start until both hold. This phase rewrites every phase-workflow template, and without
phase 1's denylist guard nothing would catch reintroduced language bias.

**Already done?** Phase 2 is done only when both commands print nothing. The README's phase 2 probe
is these same two lines.

```bash
# Report contract: grep -L lists each file still missing it
grep -L "## Decisions needed" src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/templates/commands/phase_command.py
# Residue probe: prints a line for each removed mechanism still present
grep -n -E 'post_synthesis|AUTO_API_PROMPTS|phase_mode == "shape"|Task\(bp\)|--no-verify' src/platform/templates/commands/phase_command.py src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/template_helpers.py src/platform/models/phase.py
```

Both were run on 2026-11-13:
- The first printed all three paths. No file under `src/` or `tests/` contains
  `## Decisions needed`, so it cannot match unrelated text.
- The second printed 35 lines. `Task\(bp\)` does not match `Task(bp-pipeline)`.

**Read first, in this order:**
1. `docs/phase-cooperative/README.md`. Read every subsection of **Shared contracts**. This phase
   implements most of them, and they are not repeated here: agents and modes, the report format,
   decision and research entries, the relay protocol, the stage marker, research recording, critic
   findings, and bp invocation per TUI.
2. `docs/phase-cooperative/decisions.md`. These sections apply:
   - "The critic reviews drafts before the user sees them"
   - "`implementation.md` is reviewed inside the design review"
   - "Only the orchestrator talks to the user"
   - "The architect always fetches feedback"
   - "Research is proposed by the architect and approved by the user"
   - "Research runs through `bp-pipeline` directly"
   - "The stage marker is orchestrator-owned"
   - "respec-code and respec-patch are frozen"
   - "The writing agents put the `implementation.md` draft on disk themselves"
3. Findings F1–F19, F22, F29–F31 and F33–F39 in `docs/phase-cooperative/findings.md`. If that file
   is missing, stop: this document cites findings by number and does not restate them.
4. `docs/phase-refactor/testing.md`, the testing method. Template tests assert the contract, not
   the prose.
5. `CLAUDE.md`, and `docs/AGENT_DEVELOPMENT_GUIDELINES.md:911` ("F-String Template Safety in
   Commands"). Every template is a Python f-string, so every literal brace is doubled, and
   generation-time branches are computed in the function body, never inside the f-string.

**Anchors.** Every `file:line` here was verified at commit `a64f0dc`. Phase 1 edits
`phase_architect.py`, `phase_critic.py`, `phase_command.py` and `phase_contract_grammar.py` before
you get here, so expect template anchors to have moved. Each one carries a quoted string or a named
section; search for that, and correct the anchor in this document as part of your change.

**Recommended first action.** Pin B1 and B2 and make B1 pass, which is work item 1, before
touching any template. It is the smallest change, it is pure Python on both backends, and it is the
one failure that turns a prompt mistake into a silently settled design. Then do B5–B7 (B5 and B7
with their negative self-tests; B6 is red today on Claude Code), then the work items in order.

**Two open calls — both CONFIRMED by the user on 2026-11-13 (recorded in decisions.md): the agents
get the scoped `implementation.md` Write grant, and the respec-code gate edit is allowed. Do not
re-ask. M7's result still gets recorded.** The original framing, kept for context:
1. **The `implementation.md` Write grant.** decisions.md, "The writing agents put the
   `implementation.md` draft on disk themselves", is marked as an open call for this phase. The
   README contract assumes the grant. Its cost is that on opencode and codex the path scope is
   enforced by the prompt alone (F14).
   - **Unverified on Claude Code too.** The sub-agents doc never says a path specifier inside a
     subagent's `tools` list narrows the tool. It documents only that a specifier in
     `disallowedTools` removes the whole tool ("Restrict which tools a subagent can use"). Commit
     `35a954b` found that Claude Code matches file permissions on `Edit(path)` only, never on
     `Write(path)`. Until manual check M7 passes, tell the user that the scope may rest on the
     prompt on all three TUIs. decisions.md's caveat already says so; record M7's result there.
   - **Default:** adopt it. Change that decision's status line to "decided in phase 2" with the date.
   - **If the user overturns it:** the architect returns the body in its report and the orchestrator
     writes the file. That is decisions.md's rejected alternative 2. Amend README "Agents and modes"
     in the same commit.
2. **The respec-code gate edit** (work item 10). It is the single sanctioned edit to frozen
   respec-code.
   - **Default:** make it.
   - **If the user rejects it:** log the open window in `deferred-issues.md`, as decisions.md
     instructs. The window is a re-opened (`shape-amended`) phase passing respec-code's gate before
     it has been signed off again.

**Judgment calls no test will catch:**
- **Brief quality is the feature** (README "Cross-cutting risks" 1). The tests below prove routing
  and contracts, not that the briefing is useful or the draft is sound. Read a real briefing and a
  real draft before calling this phase done.
- **Claude Code subagents start in the background by default.** Their report arrives as a completion
  notification in a later turn (sub-agents doc, "Which subagents run in the background"). While fork
  mode is on, the default in interactive sessions, Claude cannot block on a subagent at all. Fork
  mode also lets Claude start forks on its own ("Turn fork mode off"), and the guardrail already
  forbids unnamed forks (`src/platform/tui_adapters/claude_code.py:33`). Every invocation step must
  say: wait for the report; do not continue the workflow and do not prompt the user until it
  arrives. Only a live run shows whether the wording holds.
- **The imperative-language audits will reject soft words in actionable sections.**
  `_BANNED_ACTION_PATTERNS` (`tests/unit/templates/test_agent_templates.py:53-62`) bans `should`,
  `consider`, `may`, `can` and others. It applies under `_AGENT_ACTION_SECTION_TOKENS`
  (`tests/unit/templates/test_agent_templates.py:64`) and `_COMMAND_ACTION_SECTION_TOKENS`
  (`tests/unit/templates/test_command_templates.py:26`), which include every `### Step ` heading and
  every `MANDATORY ` banner.
  - So "the user can edit phase.md" fails the audit.
  - Write "Edit phase.md directly, then choose …" instead.
- **Classifying new critic checks.** Use one rule: if two reviewers would agree both that the
  finding exists and on its single fix, it is `[mechanical]`; otherwise it is `[judgment]`. The
  table in work item 4 settles every existing marker. Apply the same rule to anything you add.
- **CQ IDs stay stable across rounds.** The critic reads its previous feedback and reuses a `CQ-NNN`
  for the same finding. A drifting ID re-asks a question the user already answered.
- **The disk-mirror guarantee (B23) covers only the markdown platform.** On Linear and GitHub,
  Step 2's sync reads the platform record (`src/platform/adapters/linear.py:15-30`). That record
  holds the sparse roadmap phase until Step 12 stores the signed-off version. A re-run on those
  platforms before sign-off therefore restarts from explore and asks the briefing again. Work
  item 13 logs this; do not fix it here.
- **Exploration notes do not survive a re-run.** `store_current_analysis` is one slot per loop (F31),
  and each run starts a new loop. On resume, `revise` mode must tolerate an empty
  `get_previous_analysis` and re-read what it needs. Feedback is per loop too, so a re-run starts
  with only the round-0 guidance entry.

## Goal

`/respec-phase` becomes a design conversation with at most three human touchpoints on the happy
path: briefing, design review and sign-off.
- The orchestrator is the only party that talks to the user (F10).
- The architect and critic do the heavy work in their own contexts and return the fixed report.
- Research runs only when the user approves it.
- The critic reviews every draft before the user sees it.
- Mechanical problems are repaired without the user.
- Judgment calls arrive as questions.

This phase also:
- Fixes the surviving correctness bugs by construction:
  - F1: Step 16 is deleted.
  - F2: the architect always fetches feedback.
  - F3: only the orchestrator writes the marker.
  - F4: the storage rule.
  - F5: `implementation.md` is drafted with the design.
- Removes the two-act split, the FSDD rubric and its 90-point loop, Step 16's menus, automatic API
  research, and the post-synthesis critic.

It runs on the **current** section set. The agent-ready brief format arrives in phase 4.

## Behaviors to pin (red step — write these first)

| # | Behavior | Pinned in |
|---|---|---|
| B1 | An agent's write never changes the stage marker. `update_document` keeps the live `### Shape Gate` on both state managers, whatever the incoming markdown says or omits, and whatever `allow_frozen_field_edits` is set to (F4). | `tests/integration/test_state_manager_model_roundtrip.py`, `state_manager` fixture |
| B2 | The orchestrator's write does change the marker. `store_document`, including the disk sync at the start of a run, stores the value it is given. Paired with B1, the rule reads "agents cannot", not "nobody can". | same |
| B3 | Every critic review in a run is kept. Stores with an increasing `review_round` grow the loop history. The loop completes exactly when the latest review has an empty `### Blockers` (score 100) and never while blockers remain (score 0) (F9). A loop that has already decided `completed` re-decides to a non-completed status when a later review stores blockers, because the design-review loop runs the critic again on the same loop: `refine` for the history `[100, 0]`. Do not pin when stagnation fires; that is loop internals, and Step 9's routing (B18) must hold either way. Verified at `a64f0dc`: there is no terminal-status guard. `decide_next_loop_action` recomputes from the latest feedback on every call (`src/utils/loop_state.py:73-102`), and `store_critic_feedback` upserts without checking status (`src/mcp/tools/feedback_tools_unified.py:58-89`). | `tests/unit/models/test_enhanced_loop_state.py` |
| B4 | The critic stores each review under the round the orchestrator passes, and scores on Blockers alone. Its invocation carries `review_round`; its template stores `iteration` from that value. No length tier, section count or point deduction remains (F7, F9). | `tests/unit/templates/test_agent_templates.py`, `TestPhaseCriticTemplate` |
| B5 | No subagent can be asked to talk to the user. No agent spec on any TUI grants that TUI's question tool (F10). A negative self-test proves the checker fires. | new `tests/unit/templates/test_phase_relay_guards.py` |
| B6 | The orchestrator declares the question tool it prompts with (F12), on every TUI that has one. codex has none (`src/platform/tui_adapters/codex.py:72`). | same; plus the extended invoked ⊆ declared test |
| B7 | No command can run as a fork. No raw `generate_command_template` output, for any command on any TUI, sets `context: fork` (F11). A negative self-test proves the checker fires. | same |
| B8 | Every subagent returns the fixed four-section report, and the orchestrator stops on a failed or malformed one. The architect and critic templates require `## For the user`, `## Decisions needed`, `## Research proposals` and `## Status`, in order, with `- None` for an empty section. The command branches on `## Status` `result`, and `failed` or a malformed report ends the workflow. | new `tests/unit/templates/test_phase_cooperative_flow.py` |
| B9 | A decision is recorded only from a user's answer. Every write of a `source=user` SD in the command comes after a blocking prompt in the same step (F10). Match `source=user` only when a space follows it, because `source=user-edit` also contains `source=user`. | same |
| B10 | The happy path has at most three touchpoints. At most three steps carry the touchpoint token, and they are briefing, design review and sign-off. Every `WAIT for` outside them sits under a condition naming its trigger. A negative self-test proves the checker fires. | same, with the `wait_sites()` helper (work item 7) |
| B11 | Every user prompt blocks and has a resume point, and the prompts are identically shaped on all three TUIs. This re-anchors `tests/unit/templates/test_phase_shape_act_gate.py:86` and `tests/unit/templates/test_phase_shape_act_gate.py:100`. | same |
| B12 | Research costs nothing unless approved. On the deny-all path no `bp-pipeline` invocation is reachable. The single dispatch site runs only `[approved]` lines, after the approval prompt. This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:163`. A negative self-test proves the checker fires. | same |
| B13 | A declined proposal is never offered again. Only a genuinely new gap is offered, and only once. This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:208`. | same |
| B14 | Research dispatch names something runnable on every TUI. `Task(bp-pipeline)` is granted, and the invocation names `bp-pipeline` exactly on all three TUIs, never `respec-bp-pipeline-agent` on codex. There is no `Task(bp)`, `Skill(bp)` or `$bp` (F15). | same; `tests/unit/platform_tests/test_tool_enums_and_validation.py` |
| B15 | When bp is unavailable the workflow degrades and never terminates. The preflight is `best-practices-rag check --tui <tui>`. On failure the run continues without research and tells the user. This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:184`. | `test_phase_cooperative_flow.py` |
| B16 | Only validated research becomes a `- Read:` line, and dispatch is bounded. A result counts only if it contains `BP_PIPELINE_COMPLETE. Output:` and the file exists. `synthesis-only` items run at most 3 in parallel; `web-research` items run one at a time (F17). This re-anchors `tests/unit/templates/test_command_templates.py:353`. | same |
| B17 | Nothing makes research mandatory. There are no automatic API prompts and no post-synthesis critic, and no critic finding concerns research coverage or declined research (F8). This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:128`. | same; `TestPhaseCriticTemplate` |
| B18 | The user only sees a design the critic has reviewed. Mechanical findings get two automatic repair rounds, then reach the user as one "unresolved checks" decision. The loop's `user_input` status is repaired like `refine` while repair rounds remain, and routes to that decision once they are spent. It can arrive before any repair (Step 9). Every loop-decision branch compares against a real `LoopStatus` value (F1). This re-anchors `tests/unit/templates/test_phase_workflow_gates.py:19`. | same |
| B19 | Critic judgment calls reach the user as questions and never block. Unjustified seams, under-surfaced decisions, non-divergent options and plan-constraint fit are `[judgment]` `CQ-NNN` entries, never blocker conditions. Sign-off requires every `CQ` to be answered or its default accepted. This re-anchors `tests/unit/templates/test_agent_templates.py:583`, `tests/unit/templates/test_agent_templates.py:838` and `tests/unit/templates/test_phase_design_layer.py:52`. | same; `TestPhaseCriticTemplate` |
| B20 | A send-back is never lost. Direction is stored with its round tag before the architect is re-engaged. The architect fetches all feedback on every engagement, with no loop-status gate (F2). It decides what is new by `## User Input <i>` position, not by round number, so the round-0 guidance and a round-0 briefing answer are both applied. | same; architect template tests |
| B21 | Re-engagement works on every TUI, at every re-engagement: explore to draft, a relayed briefing question, an automatic repair, and a design-review change. Claude Code resumes the same architect with `SendMessage` and falls back to a fresh invocation. opencode and codex re-invoke fresh, and no rendered opencode or codex template mentions `SendMessage` (F13). | same |
| B22 | A re-run resumes from the stage marker. `unshaped` goes to explore. `shape-proposed` and `shape-amended` go to critic review, then design review, from the synced draft. `shape-settled` offers to re-open or shows the handoff. | same |
| B23 | Nothing the orchestrator stores is lost to the sync at the start of a re-run (markdown platform). Every orchestrator `store_document` is followed by writing the same markdown to `PHASE_FILE_PATH`: briefing SDs and research marks, `- Read:` lines, the marker, and the draft before every design-review round. | same |
| B24 | Only the orchestrator writes the marker, with the README values: `shape-proposed` at the first draft, `shape-settled` at every sign-off, `shape-amended` at a re-open. No architect or critic instruction sets, tests or branches on a marker value (F3). The one tolerated occurrence is the `### Shape Gate` line inside the architect's embedded example structure: `technical_phase_template` is `Phase(...).build_markdown()`, which always emits `unshaped` (`phase_architect.py:18-66`, rendered at `:1075`). B1 makes that line inert, and the test excludes that block. | same; agent template tests |
| B25 | A hand edit of `phase.md` is validated, diffed into `source=user-edit` SDs, and stored. This re-anchors `tests/unit/templates/test_phase_shape_act_gate.py:71`. | same |
| B26 | Skeletons materialize only after sign-off, and a conflict prompt appears only when a target file exists. Unmaterialized and unintrospectable paths are shown to the user and recorded. This re-anchors `tests/unit/templates/test_phase_skeleton_materialization_gate.py`. | same |
| B27 | A commit is offered, never automatic, and never bypasses hooks. The commit runs only after the user says yes, and no `--no-verify` appears anywhere in the phase command. | same |
| B28 | The signed-off output still feeds frozen respec-code. Draft mode carries constraint carry-forward and the `#### Step N:`, Checklist and DR formats, and respec-code's gate accepts only `shape-settled` (F33, F34). The gate half exists only if the user accepts open call 2; if it is rejected, drop that half and log the window instead. This re-anchors `tests/unit/templates/test_phase_implementation_plan_gate.py:89`. | that file; new test beside `tests/unit/templates/test_task_removal_workflow.py:59` |
| B29 | The UX Contract is surfaced at design review when present. This re-anchors `tests/unit/templates/test_ux_contract.py:91`. | that file |
| B30 | create-phase validates before it stores, and still works from roadmap. The completeness gate comes before the MCP store in reading order, and the invocation contract and output protocol are unchanged. | `tests/unit/templates/test_agent_templates.py`, `TestCreatePhaseTemplate` |

**Notes for the red step:**
- **B2, B3 and the guards in B5 and B7 pass on day one.**
  - B2 describes today's `store_phase`. Its job is to keep the B1 fix from freezing the marker for
    the orchestrator too. Prove it by temporarily applying the B1 change to `store_phase` as well,
    watching B2 go red, then reverting.
  - B3 characterizes loop machinery that already works once iterations differ; its red half is B4.
  - B5 and B7 hold today. Each gets a negative self-test that feeds the same checker function a
    synthetic violating input (an `AgentSpec` granting the question tool; a template string with a
    `context: fork` frontmatter line), so each is proven to fire.
- **Build agent specs hermetically.** Use `CodexAdapter(model_overrides=…)` and
  `OpenCodeAdapter(model_overrides=…)`, following
  `tests/unit/templates/test_coder_split_phase9.py:31-41` (F37).
- **The postgres half of B1 and B2 skips without a database** (`tests/conftest.py:270`). Run it
  against a live database before calling B1 green.
- **The touchpoint token is a contract string.** Any template test that asserts it says so in a
  comment, per testing.md's exception.

## Scope

### The new `/respec-phase` step map

Tests anchor on step numbers through `template_contract.step_body()`, so keep these numbers. The
decision variable in Step 9 must match `_BRANCH_HEADER_PATTERN`
(`tests/support/template_contract.py:21-24`), so name it `REVIEW_DECISION`.

| Step | Heading (touchpoint token where shown) | Replaces, at `a64f0dc` |
|---|---|---|
| 1 | Parse User Inputs and Locate Phase File | Step 1, `phase_command.py:189-317`, unchanged |
| 2 | Sync the Plan and Phase | Step 2, `phase_command.py:319-338`, unchanged |
| 3 | Set Up the Run | Steps 4, 4.2 and 4.5, `phase_command.py:352-425`, plus the new setup actions in work item 6 |
| 4 | Route on the Stage Marker | Step 3, `phase_command.py:340-350` |
| 5 | Explore | Step 5, `phase_command.py:427-452` |
| 6 | Briefing (TOUCHPOINT) | Steps 5.5 and 6, `phase_command.py:454-596` |
| 7 | Run Approved Research | `_bp_synthesis_orchestration_block`, `phase_command.py:59-122`; Step 16.5, `phase_command.py:1281-1469` |
| 8 | Draft | Step 12.5, `phase_command.py:987-1011`; Steps 13, 13.2 and 14, `phase_command.py:1060-1137` |
| 9 | Critic Review and Automatic Repair | Step 10, `phase_command.py:774-792`; Steps 15 and 16, `phase_command.py:1139-1279` |
| 10 | Design Review (TOUCHPOINT) | Steps 7, 8 and 9, `phase_command.py:598-772`; Step 11, `phase_command.py:794-852` |
| 11 | Sign-off (TOUCHPOINT) | Steps 11.5 and 12, `phase_command.py:854-985`; Step 12.6, `phase_command.py:1013-1058` |
| 12 | Store and Hand Off | Steps 17 and 18, `phase_command.py:1555-1628` |

**Deleted outright:**
- Step 16.6 (`phase_command.py:1471-1553`).
- The tail sections `phase_command.py:1630-1832`: Quality Assessment, Research Integration, the
  error-scenario JSON, Expected Output Structure, Context Preservation, Implementation Integration
  Notes and Success Metrics.
- Context Preservation claims *"Complete conversation history passed to each agent invocation"*
  (`phase_command.py:1806`), which contradicts the relay contract.
- Keep the Phase Name Normalization rules (`phase_command.py:1751-1767`).
- Step 7, the skeleton opt-in (`phase_command.py:598-636`), has no successor. Draft lists only
  public seams in the Skeleton Index and emits no `internal` tag. As a backstop,
  `src/utils/skeleton_generator.py:133-152` still drops an `internal, consequential` entry that
  lacks `user-selected`, so a stray one never materializes.

### Work items

**1. The stage-marker storage rule (B1, B2).**
- **The change.** In both `update_phase` implementations, carry `shape_gate` from the existing row
  into `final_phase`, exactly as frozen fields are carried, and unconditionally, so that
  `allow_frozen_field_edits` does not lift it.
  - postgres: `src/utils/state_manager/postgres.py:584-601` (*"frozen_fields = ("* … *"'version':
    existing_data['version'] + 1,"*)
  - in-memory: `src/utils/state_manager/in_memory.py:396-412`
- **Why unconditionally.** `update_document` exposes the flag to agents
  (`src/mcp/tools/document_tools.py:71-81`).
- **Leave `store_phase` alone.** It is the orchestrator and sync path, so it keeps writing the
  incoming value.
- **Where the tests go.** Next to `test_update_phase_agent_write_still_cannot_change_frozen_fields`
  (`tests/integration/test_state_manager_model_roundtrip.py:407`).
- **Cases to cover:**
  - an agent markdown that omits `### Shape Gate` entirely, where the parser defaults it to
    `unshaped` (`src/models/phase.py:88`)
  - an agent markdown that sets a different value
  - the flag set to `True`

**2. TUI capabilities and adapter methods (B14, B15, B21).**
- **`SEND_MESSAGE`.** Add `SEND_MESSAGE = 'send_message'` to `BuiltInToolCapability`
  (`src/platform/tool_enums.py:51-94`). Map it to `'SendMessage'` in the Claude Code map
  (`src/platform/tui_adapters/claude_code.py:59-79`) and to `None` in the opencode and codex maps.
  `tests/unit/platform_tests/test_tui_adapters.py:88-92` fails until every adapter decides.
- **The external-agent method.** Add `render_external_agent_invocation(agent_name, description,
  params)` to `TuiAdapter`.
  - The base implementation delegates to `render_agent_invocation`. That is correct for Claude Code
    and for opencode (`src/platform/tui_adapters/opencode.py:203-224`).
  - codex overrides it to use the exact name: today's helper renames every agent to
    `respec-<x>-agent` (`src/platform/tui_adapters/codex.py:369-375`).
  - Keep the codex close-after-harvest line (`src/platform/tui_adapters/codex.py:261`).
- **The bp TUI name.** Add an abstract `best_practices_tui` property, the `--tui` value
  `best-practices-rag check` accepts: `claude`, `opencode` or `codex`. This mirrors
  `_normalize_tui_name` (`src/cli/services/best_practices_preflight.py:48-51`). The adapter modules
  must not import CLI commands (`tests/unit/platform_tests/test_tui_adapters.py:81-86`), so this is
  a property, not an import.
- **The batch limit.** Add a `selection_batch_limit: int` property to `TuiAdapter`: 1 in the base,
  4 on Claude Code. The limit of 4 comes from the `AskUserQuestion` schema; confirm it against the
  live tool definition (manual check M3).
- **Verified: `best-practices-rag check --tui <tui>` confirms that bp-pipeline is installed.** It
  checks `agents/bp-pipeline.md` for claude, `prompts/bp-pipeline.md` for opencode and
  `agents/bp-pipeline.toml` for codex
  (`~/.local/share/uv/tools/best-practices-rag/lib/python3.14/site-packages/best_practices_rag/cli.py:401-426`,
  installed v0.2.16).
  - It also fails when Neo4j is unreachable or the Exa key is missing.
  - Treat any non-zero exit as "bp unavailable: continue without research".
  - It confirms the agent file exists, not that it can be dispatched. opencode dispatchability
    remains manual check M1.
  - README "bp invocation per TUI" still calls this unverified. Replace that sentence with this
    result (work item 13).

**3. Models and invocation helpers.**

`PhaseCommandTools` (`src/platform/models/phase.py:14-185`):
- **Delete these fields:**
  - the six invocations: `src/platform/models/phase.py:34-55`
  - `store_plan` and `get_plan`, which the template never uses: `src/platform/models/phase.py:62`,
    `src/platform/models/phase.py:65`
  - `decide_shape_loop_action`: `src/platform/models/phase.py:69`
  - the shape-act fields: `src/platform/models/phase.py:75-79`
  - `phase_command_reference` and `roadmap_command_invocation`, whose only users were Step 16's
    decomposition branch and Step 16.5's policy banner: `src/platform/models/phase.py:56-57`
  - `plan_command_invocation` (`src/platform/models/phase.py:58`), whose only user is the deleted
    error-scenario tail (`phase_command.py:1690`)
  - `mcp_tools_reference`, which always renders empty (F38): `src/platform/models/phase.py:106-127`,
    and its use at `src/platform/templates/commands/phase_command.py:185`
- **Add these fields:**
  - `invoke_architect_explore`, `invoke_architect_draft` and `invoke_architect_revise`, built with
    `render_agent_invocation`
  - `resume_architect`: the `SendMessage` text addressed to `ARCHITECT_AGENT_ID` with
    `phase_mode: ARCHITECT_MODE` and the usual IDs, when the adapter maps `SEND_MESSAGE`; an empty
    string otherwise. A single field serves every mode. The template branches on it at generation
    time, in the function body. Where it is empty, the rendered step shows only the fresh
    invocation and never mentions resuming (B21).
  - `invoke_critic_review`
  - `invoke_bp_pipeline`, built with `render_external_agent_invocation`
  - `bp_preflight_command`
  - `store_document_user_edit`, which renames `store_document_gate_edit`. It keeps
    `allow_frozen_field_edits='true'`.

In `create_phase_command_tools` (`src/platform/template_helpers.py:160-354`):
- Replace the grant at `src/platform/template_helpers.py:172` (*"builder.add_builtin_tool(
  BuiltInToolCapability.TASK, 'bp')"*) with `'bp-pipeline'`.
- Add `_add_adapter_question_tool(builder, adapter)` (`src/platform/template_helpers.py:119-121`)
  for F12.
- Add `builder.add_optional_builtin_tool(BuiltInToolCapability.SEND_MESSAGE)`.
- Keep the Write grant at `src/platform/template_helpers.py:182` and the Glob grant at
  `src/platform/template_helpers.py:185`.

Invocation inputs follow README "Agents and modes":
- **Agents** get `phase_mode`, `loop_id`, `plan_name`, `phase_name` and
  `project_config_context_markdown`. Critic invocations gain that config context too (F22), plus
  `review_round`.
- **Drop `optional_instructions` and `workflow_guidance_markdown`** from every invocation
  (`src/platform/template_helpers.py:209-210`, `src/platform/template_helpers.py:222-223`,
  `src/platform/template_helpers.py:235-236`, `src/platform/template_helpers.py:248`,
  `src/platform/template_helpers.py:259`, `src/platform/template_helpers.py:270`). The contract
  forbids passing conversation text. Step 3 stores Step 1's `WORKFLOW_GUIDANCE_MARKDOWN` as feedback
  tagged `[round 0 | briefing]`, and agents read it through `get_feedback`. This keeps the README
  contract unchanged.
- **Description strings are user-visible on opencode** (README "Agents and modes"), so state the
  mode accurately and neutrally. For example, `explore` is "explore the plan, the codebase and the
  local knowledge base, then return the briefing report".

`PhaseArchitectAgentTools` (`src/platform/models/phase.py:188-208`):
- **Tools:** `GET_DOCUMENT`, `UPDATE_DOCUMENT`, `GET_FEEDBACK`, `STORE_CURRENT_ANALYSIS` and
  `GET_PREVIOUS_ANALYSIS`.
  - Drop `LINK_LOOP_TO_DOCUMENT`, which is granted but unused.
  - Drop the `get_loop_status` field (`src/platform/models/phase.py:205`), which closes F2.
  - Add `store_analysis` and `get_analysis` invocation fields.
- **Built-ins** (`create_phase_architect_agent_tools`, `src/platform/template_helpers.py:822-854`):
  - add `WRITE` scoped to `.respec-ai/plans/*/phases/*/implementation.md` (open call 1)
  - keep the optional `DESIGN_SYNC`

`PhaseCriticAgentTools` (`src/platform/models/phase.py:211-234`):
- **Tools:** drop `GET_LOOP_STATUS` and its field, because the round comes from `review_round` now.
- **Soft caps:** delete `phase_length_soft_cap` and `phase_shape_soft_cap`
  (`src/platform/models/phase.py:226-229`).
- **Factory:** `create_phase_critic_agent_tools` (`src/platform/template_helpers.py:857-886`) loses
  both soft-cap parameters.

**4. The critic's `review` mode** (`src/platform/templates/agents/phase_critic.py`).

**Replace:**
- The mode protocol (`phase_critic.py:232-250`): the only mode is `review`. Keep the `phase_mode`
  scalar (decisions.md "Kept from the previous effort").
- The invocation contract and guidance contract (`phase_critic.py:197-229`). The inputs become
  `phase_mode`, `loop_id`, `plan_name`, `phase_name`, `review_round` and
  `project_config_context_markdown`. `validation_mode` and `workflow_guidance_markdown` go. Guidance
  is read from the `[round 0 | briefing]` feedback entry, and every guidance path is still read.
- The output scope (`phase_critic.py:164-193`). The final message becomes the four-section report,
  replacing *"Feedback stored to MCP."* (`:168`). Feedback is still stored with the store tool, with
  `iteration = review_round`, and `overall_score` is 100 when `### Blockers` is empty and 0
  otherwise.
  - Keep the parser-contract and storage-failure lines (`:170-192`);
    `tests/unit/templates/test_agent_templates.py:569` asserts them.
  - **`- None` means two different things.** The report rule (empty report section = `- None`)
    applies to the four report sections only.
  - The stored `CriticFeedback` keeps today's rule (`:178`): an empty `### Blockers` has no bullet
    at all.
  - A `- None` blocker fails parsing (`src/models/feedback.py:19-25`, `:49-59`).
- STEPs 3–6 (`phase_critic.py:836-866`). They become the review checks, the fixed score rule, and the
  store with `iteration = review_round`. STEP 3's plan-constraint bullets (`:842-848`) stay as
  `[judgment]` checks.
- OUTPUT FORMAT's Important Notes (`phase_critic.py:1360-1383`). Drop the post-synthesis, shape and
  section-scoring bullets, and say that `iteration` is `review_round`.
- COMPLETION (`phase_critic.py:1477-1487`) becomes the four-section report. The critic's
  `## Research proposals` is always `- None`, because research is never a critic concern (B17).
- The `phase_feedback_template` example (`phase_critic.py:8-137`):
  - Drop the point allocations.
  - Show `[mechanical]` entries under `blockers` and `[judgment]` entries under `key_issues`.
  - Move Plan Constraint Violation from `blockers` to `key_issues`.
  - Drop the two API markers.

**Delete:**
- `PHASE MODE: SHAPE` (`phase_critic.py:252-318`). Its checks move into `review`.
- `DOCUMENT SCOPE` (`phase_critic.py:320-337`, F6).
- The Two-Lane contract (`phase_critic.py:339-349`, F7).
- Validation modes (`phase_critic.py:351-414`).
- Step 2.5's length tiers (`phase_critic.py:436-504`).
- API detection (`phase_critic.py:635-770`, F8).
- The FSDD framework (`phase_critic.py:867-1075`).
- The `GATE CHECK` (`phase_critic.py:1078-1086`) and `SHAPE_SOFT_CAP` (`phase_critic.py:1093-1096`).
- Domain-specific scoring and scoring methodology (`phase_critic.py:1200-1347`).
- Refinement behavior (`phase_critic.py:1385-1417`).
- ERROR HANDLING and QUALITY CRITERIA (`phase_critic.py:1419-1475`). They score, check `Synthesize:`
  prompts, and validate per-API coverage.

**Keep:**
- Loop-id validation.
- Plan retrieval (`phase_critic.py:822-835`).
- `Read:` path validation (`phase_critic.py:506-633`), minus its API and `Synthesize:` fields.
- Implementation Plan Reference checks (`phase_critic.py:771-818`).
- BINDING SCOPE and the Design Shape blocker rules (`phase_critic.py:1098-1191`).

**Add:**
- Read `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md`, the path the architect
  writes. A missing file is a `[mechanical]` finding.
- Mechanical checks:
  - every `#### Step N:` names the files it touches
  - every Checklist item carries `(Step N)` and a `(verify: …)` whose command is one of these:
    - the owning language's `[commands].test` in `project_config_context_markdown`
    - the command a `source=user` SD records for that language (the briefing's Option B, below)
    - phase 1's `ask user` marker, for a language with no usable command

    Accepting the SD command matters. Without it, a command the user typed in the briefing is a
    `[mechanical]` finding the architect cannot repair, and it reaches the user a second time.
  - every Test List entry is covered by some step (BINDING SCOPE item 5)
- Read-only in the prompt (F14): never edit the document, never write files.
- A finding that an SD settles (`supersedes=CQ-NNN`, or the accepted unresolved checks) is never
  raised again.

Every finding starts with its classification tag (README "Critic findings"):
- **`[mechanical]` findings** keep the `- BLOCKING]` suffix and go in `### Blockers`. They are what
  `template_contract.blocker_conditions()` reads.
- **`[judgment]` findings** drop the suffix (for example `- [judgment] [Unjustified Seam]: …`), go
  in `### Key Issues`, and appear in the report as `CQ-NNN` entries.
  - Option A is "keep as designed"; Option B is the critic's alternative.
  - The critic gives a `Recommended` value for every finding. For an unjustified seam it recommends
    B.

Classification of every marker in `phase_critic.py` at `a64f0dc` (line of first occurrence):

| Marker | Class | Reason |
|---|---|---|
| Research Path Invalid (`phase_critic.py:125`) | mechanical | The path does not exist, so the only fix is the real path or no line. |
| Best-Practices Reference Invalid (`phase_critic.py:126`) | mechanical | Same. |
| API Research Coverage Missing (`phase_critic.py:127`) | **removed** | F8. |
| API Research Final Docs Missing (`phase_critic.py:128`) | **removed** | F8; post-synthesis only. |
| Plan Constraint Violation (`phase_critic.py:129`) | judgment | The fix is either to conform or to record a deviation, which is plan-constraint fit. |
| Under-Surfaced Decision (`phase_critic.py:278`) | judgment | Whether a choice is consequential is a trade-off. README lists it. |
| Non-Divergent Decision Options (`phase_critic.py:287`) | judgment | The better alternative is a design choice. README lists it. |
| Malformed Decision Entry (`phase_critic.py:296`) | mechanical | A field is missing. README lists it. |
| Implementation Plan Reference Invalid (`phase_critic.py:793`) | mechanical | The path does not exist. |
| Implementation Plan Reference Not Applied (`phase_critic.py:813`) | judgment | The fix is either to apply the constraint or to justify why it does not apply. |
| Unjustified Seam (`phase_critic.py:1129`) | judgment | README lists it. |
| Empty Test List (`phase_critic.py:1134`) | mechanical | A field is missing. |
| Test List Names File Not Behavior (`phase_critic.py:1138`) | mechanical | README: "a Test List entry with no behavior". |
| Skeleton Index Module Mismatch (`phase_critic.py:1143`) | mechanical | README lists it. |
| UX Contract Flow Missing Pass Condition (`phase_critic.py:1152`) | mechanical | A field is missing. If the architect cannot derive the condition from the flow's stated outcome without a user preference, it raises an `OD-NNN`, and that counts as the fix. |
| UX Contract Route Missing Auth (`phase_critic.py:1161`) | mechanical | Same escape. |
| Missing State Ownership / Undecided Screen Decomposition / Missing Component Provenance / Missing Design Source (`phase_critic.py:1175-1191`) | mechanical | Presence only. The single fix is to surface an `OD-NNN`, and the user answers it through the relay. `tests/unit/templates/test_frontend_elicitation_phase10.py:114` and `tests/unit/templates/test_frontend_elicitation_phase10.py:122` stay green unchanged. |

Rewrite the `#### Design Research` paragraph (`phase_critic.py:1193-1198`): it now says that no
finding ever concerns research coverage, the research ledger, or declined proposals (B17).

**5. The architect's `explore`, `draft` and `revise` modes**
(`src/platform/templates/agents/phase_architect.py`).

**Structure:**
- Keep the mode branches as `IF phase_mode == "explore":` / `ELIF phase_mode == "draft":` /
  `ELIF phase_mode == "revise":`. `_phase_mode_branch_body`
  (`tests/unit/templates/test_phase_implementation_plan_gate.py:41-58`) parses that header shape.
- Replace the invocation contract (`phase_architect.py:172-208`) and the mode protocol
  (`phase_architect.py:212-234`).
- Replace STEP 0 (`phase_architect.py:238-257`, *"IF LOOP_STATUS.iteration >= 1"*). Every engagement,
  fresh or resumed, first calls `get_document`, then `get_feedback`, then `get_previous_analysis`,
  unconditionally (F2).
- Rewrite STEP 2 (`phase_architect.py:452-459`). It applies the user's feedback, not only the
  critic's, but not every critic section.
  - **From the critic,** only the latest review's `### Blockers` (`[mechanical]`) are applied.
  - `### Key Issues` are `[judgment]` CQs that the user decides. The architect acts on one only
    through the SD the orchestrator writes (`supersedes=CQ-NNN`).
  - `### Recommendations` are advisory.
  - Today's *"Address ALL items in `### Key Issues`"* (`:456`) would override the user, so it goes.
  - **What counts as new is decided by position, not by round.** `get_feedback` numbers user
    entries `## User Input <i>` in insertion order (`src/mcp/tools/feedback_tools_unified.py:189-193`).
    The architect records in its notes the highest `<i>` it has applied, and applies every entry
    above it. With empty notes, it applies every entry.
  - Several entries share a round: the guidance, the briefing answers and relayed questions are all
    round 0. A round-number watermark would therefore drop the briefing direction, which is F2 again.
  - A `[question]` entry is answered in `## For the user`, and nothing else changes unless the entry
    asks for a change.
- Delete these instructions to set the marker, and remove every marker value from the template
  (B24):
  - `phase_architect.py:543-545` (*"set `### Shape Gate` to `shape-proposed`"*)
  - the gate checks at `phase_architect.py:561` and `phase_architect.py:618`
- Every mode persists before returning (README "Relay protocol" step 2). STEP 4
  (`phase_architect.py:719-729`) becomes: every mode calls `update_document`, then
  `store_current_analysis`.
  - The document goes through `update_document`.
  - The complete notes go through `store_current_analysis`: reuse candidates, exemplar files,
    constraints read, KB results, the approach sketch and the highest `## User Input` index applied.
- Workflow guidance handling (`phase_architect.py:638-644`) reads the guidance from the
  `[round 0 | briefing]` feedback entry instead of an input. It still reads every listed guidance
  path.
- Where `PLAN_DELIVERY_INTENT_POLICY` is said to be consumed by `implementation-plan`
  (`phase_architect.py:656-659`, `:712-714`), say `draft` and `revise` instead. The same goes for
  the IMPLEMENTATION PLAN STRUCTURE heading note (`:760-761`).
- STEP 5 and COMPLETION (`phase_architect.py:731-756`, `phase_architect.py:1383-1391`) become the
  four-section report.

**`explore`:**
- **Grounding.** Read the plan, its context variables and its constraints (keep STEP 0.5, 0.55 and
  1.5: `phase_architect.py:259-304`, `phase_architect.py:387-450`), and the roadmap phase's Overview.
  Search the existing code for reuse candidates and exemplar files, and cite only paths it has
  opened.
- **Local KB lookups** decide each proposal's tier, and are read-only. Run `generate-slug`, then
  `check-file-cache` **without** `--model` (F17), then `query-kb`, then
  `Glob(.best-practices/*.md)`.
  - These replace the API inventory and protocol in STEP 0.6 (`phase_architect.py:306-375`).
  - Keep the `query-kb` flag rules (`phase_architect.py:334-338`, `phase_architect.py:1316-1331`);
    `tests/unit/templates/test_agent_templates.py:815` pins them.
  - If the KB is unavailable, say so in `## For the user` and propose nothing on that basis. Delete
    the "add all topics" fallbacks at `phase_architect.py:345-348` and
    `phase_architect.py:1343-1348` (F19).
- **Persist** through `update_document`:
  - `OD-NNN` entries in `### Open Design Decisions`, in the canonical nested form, ranked by blast
    radius. Keep the UI decision classes, with Design Source first (`phase_architect.py:511-538`).
    Rewrite the stale Step 3/5/6 references at `phase_architect.py:525-527` to say that choosing A
    ends the run after the briefing. The user designs, then re-runs. The marker is still
    `unshaped`, so the re-run explores again and does not re-ask settled decisions. This is the
    same "no new resume machinery" behavior as `docs/frontend-refactor/decisions.md:622-624`. The
    orchestrator side is Step 6.
  - The research ledger in `### Research Requirements`: one RP line per proposal, using the README
    format and tiers. `in-kb:<path>` lines are uncapped. Explore never writes a mark; marks and
    `- Read:` lines are the orchestrator's.
  - Retire the `#### Design Research` block (`phase_architect.py:497-505`, and
    `DESIGN_RESEARCH_PLACEHOLDER` in the grammar module).
  - Replace the `research_requirements` placeholder in `technical_phase_template`
    (`phase_architect.py:35-43`), which still shows `Synthesize:` lines, with one example RP line and
    one example `- Read:` line in the README formats.
  - Rewrite the remaining `Synthesize:` instructions in RP terms:
    - KNOWLEDGE BASE INTEGRATION (`phase_architect.py:1285-1297`)
    - Scanning Process item 6 (`:1331`)
    - Research Identification Challenges (`:1350-1359`)

    Keep "zero proposals is valid" and "never fill a quota".
- **The proposal cap.** At most **3** RP lines with tier `synthesis-only` or `web-research` per
  explore. Each names what it informs.
- **Missing verify commands.** If a project language's verify command is missing (phase 1's
  empty / `TODO` / `no_preference` rule, F25), explore returns it as an `OD-NNN`:
  - Option A: set `[commands].test` in `.respec-ai/config/standards/<language>.toml`, then re-run.
    Choosing it ends the run after the briefing (Step 6). Never point to `/respec-standards`: it
    never edits canonical TOML (`src/platform/templates/commands/standards_command.py:16`; phase 1,
    item 7).
  - Option B: the user supplies the command now; the orchestrator records it as an SD, and the
    architect uses it.
  - Option C: leave phase 1's `(verify: ask user — …)` marker; the implementing agent asks for the
    command. This is phase 1's "Leave the marker" answer, moved into the briefing. Phase 3 accepts
    the marker, and phase 4 builds on it.
  - Recommended: C, so that "accept the recommended default for all remaining" never ends the run.

  The architect never guesses a command.
- **Report.** `## For the user` holds the briefing:
  - the architect's understanding of the phase
  - what exists to build on
  - an approach sketch: module map and flow
  - the research: "will use" for `in-kb` lines, and the proposals with their tiers

  `## Decisions needed` holds the ODs; `## Research proposals` holds the RP lines.

**`draft`:**
- **The phase document.** In one pass on the current sections:
  - The design layer: Module Layout, Skeleton Index (meta-notation, F24), Collaboration And Wiring,
    Test List, and Design Shape - Additional Sections, with the UX Contract when present.
  - SDs carried forward verbatim, and only the ODs still open. Where an OD is still open, the
    design follows its Recommended option and says so; Step 10 relies on this.
  - Every current detail section. Success Criteria must cover every objective, scope item and
    deliverable (F34).
  - `- Constraint:` lines.
  - The ledger, preserved verbatim. The orchestrator owns its RP marks and its `- Read:` lines. The
    one addition draft and revise may make is a nested `- Applied: <where>` line under a `- Read:`
    entry that a step cites (today's carry-forward, `phase_architect.py:610-613`). Frozen reviewers
    read those lines (`src/platform/templates/agents/code_quality_reviewer.py:63`).
- **`implementation.md`.** Write it to `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md`
  with the scoped Write grant. Follow `implementation_plan_example` (`phase_architect.py:73-110`),
  which phase 1 has neutralized.
  - The build rules of the old `implementation-plan` branch move here (`phase_architect.py:570-613`):
    - constraint carry-forward
    - the structure bullets, including the Execution Intent Policy derivation from
      `PLAN_DELIVERY_INTENT_POLICY` and the DR format
    - the Checklist verify rule, extended for the briefing's answer: a language whose
      missing-verify-command OD was settled with Option B uses the command its `source=user` SD
      records, verbatim; Option C keeps phase 1's marker. Keep the strings
      `test_agent_templates.py:872` pins (`never a hardcoded`, `[commands].test`)
    - the `- Applied:` carry-forward

    Drop its gate check and its "only inputs" restriction (`:561-568`, F5).
  - Say in the prompt that this is the only file it may write (F14).
- **Report.** `## For the user` is the design summary: module map, public seams, behaviors, build
  order and decisions. `## Research proposals` holds at most **1** new gap, and only one absent
  from the ledger.

**`revise`:** apply the new feedback to the phase document and to `implementation.md`. The report's
`## For the user` summarizes what changed, item by item. `## Research proposals` holds at most 1 new
gap.

**Delete:**
- The shape/implementation-plan/detail branches (`phase_architect.py:461-631`).
- The stale *"downstream task workflow"* line (`phase_architect.py:447`).
- The "~10 Pages" heading and page allocation (`phase_architect.py:904-912`). Keep the Quality Check
  bullets that follow (`phase_architect.py:914-924`); `tests/unit/templates/test_phase_design_layer.py:41`
  pins one of them.
- The Test Case IDs exclusion (`phase_architect.py:896-898`), which contradicts the Test List.
- The domain-specific section lists and examples (`phase_architect.py:1028-1060`,
  `phase_architect.py:1121-1203`) and their checklist (`phase_architect.py:1239-1247`).
- REFINEMENT BEHAVIOR (`phase_architect.py:1255-1283`).
- The `Synthesize:` format (`phase_architect.py:1299-1314`). The RP line replaces it.
- The six domain-specific `additional_sections` placeholders (`phase_architect.py:55-62`). Domain
  content goes under the `### <H2> - Additional Sections` H4 mechanism, which avoids the F27 traps.
- The matching instructions to emit domain H2s: the domain-H2 block (`phase_architect.py:1088-1111`)
  and *"Put genuinely new sections as standalone H2 headers"* (`:1116`). Keep the rest of the
  CRITICAL CONSTRAINTS (`:1113-1117`).
- "When Decomposing Phases" (`phase_architect.py:954-959`). Its only consumer was Step 16's
  decomposition branch.

**6. The orchestrator rewrite** (`src/platform/templates/commands/phase_command.py`). Every subagent
step follows README "Relay protocol" to the letter. Specific requirements per step:

- **Forbidden literals.** The residue probe's strings must not appear in any of the five probed
  files, not even inside a prohibition: `--no-verify`, `Task(bp)`, `post_synthesis`,
  `AUTO_API_PROMPTS` and `phase_mode == "shape"`.
  - README's bp section contains exactly such a sentence, so copying it is the likely way to trip
    this.
  - Write the rule without the literal. For example, write "never disable commit hooks" instead of
    "never pass --no-verify".
  - Otherwise the probe never reads "done".
  - **One more forbidden literal: `"complete"` in double quotes.** The kept test
    `tests/unit/templates/test_command_templates.py:481` asserts that the phase command does not
    contain it. The report's `result: complete` must therefore be matched unquoted or reached as an
    `ELSE`.

- **Report handling (every subagent step).**
  - Name all four report headings literally in the template, inline in backticks rather than as
    headings of the command file. The README probe greps the command for `## Decisions needed`.
  - A report is **malformed** when any of these hold:
    - any of the four H2s is missing or out of order
    - text precedes `## For the user`
    - `## Status` has no `result` of `complete`, `needs-user` or `failed`
  - `complete` and `needs-user` route identically: the step's next action runs, and every entry in
    `## Decisions needed` and `## Research proposals` is asked at the next touchpoint.
  - `failed`, or a malformed report, ends the workflow with the `detail` line shown.
  - Branch on a variable whose name contains `DECISION`, for example `REPORT_DECISION`, so
    `template_contract.decision_branch()` can find the branches for B8.
- **Disk mirror (B23).** Every orchestrator `store_document` is followed by writing the same markdown
  to `PHASE_FILE_PATH` with Write. Step 2's markdown sync is Read-then-store
  (`src/platform/adapters/markdown.py:14-24`), so an interrupt anywhere after the briefing would
  otherwise wipe the SDs, the `[declined]` marks and the marker. The write renders on every
  platform, as today's Step 8 write does (`phase_command.py:651`). It protects a re-run only on the
  markdown platform; the Linear and GitHub gap is deferred (judgment calls; work item 13).
- **IDs and marks.**
  - **SD IDs** are the next number above every `SD-NNN` already in the document, three digits. They
    never reuse the superseded OD's number, as today's `SD-{{OD.number}}` does
    (`phase_command.py:573`).
  - **RP marks** are appended as the last token of the RP line, after any `source=user`, for
    example `… | tier: synthesis-only [approved]`. Keeping a `will use` (`in-kb`) line marks it
    `[approved]`; dropping it marks it `[declined]`.
  - **Round tags** are `[round N | …]`, where N is `REVIEW_ROUND` when the entry is stored: 0 before
    the first critic review. The tag is context for the architect. It does not decide newness; see
    work item 5, STEP 2.
  - **Sources of the decisions asked:**
    - ODs come from the current document's `### Open Design Decisions`, because the document wins
      on any mismatch with a report (README).
    - CQs come from the latest critic report only.
    - RPs come from the ledger.

- **Header.**
  - Keep `{tools.tui_adapter.subagent_invocation_guardrail}` (`phase_command.py:139`).
  - Add a phase-local line right after it: `bp-pipeline` is the one external agent this workflow
    dispatches, at Step 7 only, for user-approved research only, using the exact invocation shown.
  - The guardrail at `src/platform/tui_adapters/claude_code.py:30-34` is shared by every command, so
    it stays unchanged (F18).
  - Rewrite the Overview, Responsibilities and Orchestration Pattern (`phase_command.py:134-183`) for
    the relay flow.
- **Step 3.**
  - Initialize the one `LoopType.PHASE` loop, link it, and verify the link. Keep the fail-closed
    checks in `phase_command.py:369-396`.
  - Load `PROJECT_CONFIG_CONTEXT_MARKDOWN` (keep `phase_command.py:408-425`), including phase 1's
    `respec-ai language-guidance` call, its non-terminating fallback and its
    `### Language Authoring Notes` block (phase 1, item 5).
    - Step 3 runs before Step 4 routes, so every route that reaches the architect has the config
      context. That closes the gap phase 1 logs in `deferred-issues.md` ("Step 3's settled route
      skips Step 4.5"); delete that row (work item 13).
  - Set `IMPLEMENTATION_PLAN_PATH = dirname(PHASE_FILE_PATH)/implementation.md`, the derivation
    today's Step 12.6 uses (`phase_command.py:1035-1036`) and frozen respec-code uses
    (`src/platform/templates/commands/code_command.py:230-231`). Step 11 and phase 4 read it.
  - Store `WORKFLOW_GUIDANCE_MARKDOWN` with the `[round 0 | briefing]` tag.
  - Run `{tools.bp_preflight_command}` through Bash and set `BP_AVAILABLE` from its exit code.
  - Initialize `REVIEW_ROUND = 0` and `REPAIR_ROUNDS = 0`, and clear `ARCHITECT_AGENT_ID`.
- **Step 4.** Read `### Shape Gate` from the synced document and route (B22):
  - `unshaped` goes to Step 5.
  - `shape-proposed` and `shape-amended` go to Step 9, then Step 10.
  - `shape-settled` gets a guarded prompt: re-open, or show the handoff. Re-open writes
    `shape-amended` with `store_document`, then goes to Step 9.
  - An explicit re-open request in `OPTIONAL_INSTRUCTIONS` skips the prompt.
- **Re-engaging the architect (every site).** Set `ARCHITECT_MODE`, then:
  - Use `{tools.resume_architect}` when it is non-empty and `ARCHITECT_AGENT_ID` is set.
  - Otherwise use the fresh invocation for that mode. Also fall back to it when the send is refused
    or the agent cannot be reached.
  - On Claude Code, whenever a fresh invocation runs, record the agent ID it returns in
    `ARCHITECT_AGENT_ID`.
  - Wait for the report and parse `## Status`. `failed` or a malformed report ends the workflow
    with the detail shown.

  This applies at every re-engagement (README "Relay protocol" step 6):
  - Step 8, explore to draft, where the exploration in context matters most
  - the Step 6 and Step 10 question relays
  - Step 9's repair
  - Step 10's change, design-changing answer and hand-edit abort
  - Step 7's follow-up
  - Step 11's missing-file retry
- **Steps 5 and 8.**
  - Step 5 is always a fresh `explore` invocation.
  - Step 8 re-engages in `draft`.
  - After the first draft, write `shape-proposed` with `store_document`.
- **Step 6 (Briefing, TOUCHPOINT).**
  - Show `## For the user`.
  - Ask every OD in rank order. Every prompt offers "accept the recommended default for all
    remaining".
  - Ask each RP in turn: approve, deny or edit. `in-kb` lines are listed as "will use" and the user
    can drop them. Offer "add your own".
  - When `BP_AVAILABLE` is false, offer only the `in-kb` lines, and say once that bp is unavailable.
    Leave the other RP lines unmarked: unavailability is not a denial, so a later run with bp
    available offers them again.
  - For an edited or user-added RP, recompute the tier with `generate-slug`, `check-file-cache` and
    `query-kb`. If the tier rose, ask again; that prompt is guarded.
  - Hold the free-form conversation in plan-conversation pacing: 1–2 questions per message
    (`src/platform/templates/commands/plan_conversation_command.py:87-94`).
  - Selection prompts: one per prompt in the portable core. On Claude Code, batch them, at most
    `min(2, selection_batch_limit)` per call in the briefing and up to `selection_batch_limit` at
    design review and sign-off.
  - A question that needs new codebase knowledge is stored as `[round N | question]`, the architect
    is re-engaged in `explore` (resumed where possible), and its answer is shown.
  - Record everything per README "Relay protocol" step 5, with SDs, RP marks and tagged feedback all
    written only after a `WAIT for` (B9). Then mirror the document to disk.
  - **A decision that needs work outside this run ends the run.** Two options do: Design Source
    Option A (design first) and the missing-verify-command Option A (set `[commands].test` in the
    language's standards TOML).
    - When the user picks either, record the SD, mirror to disk, and tell the user what to do.
    - Then end the run cleanly: not a failure, and no research or draft.
    - The marker is still `unshaped`, so the re-run explores again and asks only what is still open.
  - Then go to Step 7.
- **Step 7 (the single bp-pipeline dispatch site, B12–B16).**
  - It is entered from two places, and `RETURN_TO` records which:
    - From Step 6, `RETURN_TO` is Step 8.
    - From Step 10, after a newly offered RP was approved, `RETURN_TO` is "Step 10 follow-up". If this
      step wrote any new `- Read:` line, store `[round N | review]` naming them, re-engage the
      architect in `revise`, and go to Step 9. Otherwise go back to Step 10's final prompt.
  - **First, the free documents.** For every `[approved]` `in-kb:<path>` line whose file exists,
    write its `- Read:` line (`Source: in-kb`). This needs no bp, so it runs even when nothing else
    does.
  - Select only `[approved]` lines with tier `synthesis-only` or `web-research`. If there are none,
    or `BP_AVAILABLE` is false, store and mirror the `in-kb` lines and go to `RETURN_TO` with no
    invocation. When bp is unavailable, say once that approved research was skipped.
  - Compute each input at dispatch time from local commands only (README "bp invocation per TUI";
    field names from `~/.config/best-practices-rag/references/bp-pipeline-interface.md:7-28`):
    - `MODE: codegen`
    - `TECH` and `TOPICS`, from the RP line
    - `QUERY`, the RP line's Query; `PRIMARY_QUERY`, the versioned query with
      "official documentation" appended (`~/.claude/commands/bp.md:133-135`)
    - `OUTPUT_FILE`: `.best-practices/<slug>.md`, from `generate-slug`
    - `TECH_VERSIONS_JSON` and `CUTOFF_DATE` from
      `~/.config/best-practices-rag/references/tech-versions.md`
    - the coverage fields, routed as bp's Step 4 routes them (`~/.claude/commands/bp.md:115-131`):
      - full coverage: `COVERED_TECHS` and `ALL_QUERIED_TECHS`
      - partial gap: `UNCOVERED_TECH`, `COVERED_TECHS` and `ALL_QUERIED_TECHS`
      - full gap: `ALL_QUERIED_TECHS` only
    - `LANGUAGES`: the project's `[project].languages` from `.respec-ai/config/stack.toml`
      (`src/platform/standards_config.py:373-375`). `LANGUAGE_AGNOSTIC: "true"` is used only when
      no language is declared.
  - Deduplicate by `OUTPUT_FILE`, so two proposals never write one file.
  - Run the `synthesis-only` items first, at most 3 in parallel, then the `web-research` items one at
    a time. Only the gap path writes the fixed `/tmp` Exa files
    (`~/.claude/agents/bp-pipeline.md:93-121`, F17).
  - Accept an item only when its result contains `BP_PIPELINE_COMPLETE. Output: <path>` and the file
    exists. Anything else fails that item and records nothing; it never exits the workflow.
  - For each accepted document, write its `- Read:` line into `### Research Requirements`
    (`Source: RP-NNN`) in the same `store_document` as the `in-kb` lines, then mirror to disk.
- **Step 9.**
  - `REVIEW_ROUND += 1`, then invoke the critic with it.
  - Keep the fail-closed persistence checks from `phase_command.py:1143-1184`, with their variable
    names and error strings, which `test_command_templates.py:812` asserts. The iteration checks
    work now that rounds grow.
  - The emptiness check needs one change. `get_feedback` also returns user entries, and Step 3
    stores one before any review, so its output is never empty. Check instead that `PHASE_FEEDBACK`
    contains `## Iteration <REVIEW_ROUND> -`, the header `get_feedback` writes per critic entry
    (`src/mcp/tools/feedback_tools_unified.py:167`).
  - `REVIEW_DECISION = decide_loop_next_action`:
    - `completed` goes to Step 10.
    - `refine` or `user_input`, while `REPAIR_ROUNDS < 2`: increment `REPAIR_ROUNDS`, re-engage the
      architect in `revise` (the user is not told), and return to Step 9. `user_input` does not mean
      "repairs exhausted". With 0/100 scores, the score-stagnation rule (`loop_state.py:146-157`)
      returned `user_input` for the histories `[100, 100, 0]` and `[0, 0, 0]` in a probe on
      2026-11-13, before any repair had run.
    - `refine` or `user_input` with no repair rounds left: set `UNRESOLVED_CHECKS` from the
      latest review's `### Blockers` in `PHASE_FEEDBACK`, and go to Step 10.
    - Give `user_input` its own `ELIF REVIEW_DECISION == "user_input":` branch holding both cases,
      so `decision_branch('user_input')` finds it.
    - Any other value ends the workflow (fail-closed).
  - Collect the CQ entries from the latest critic report only, for Step 10. The critic reuses CQ
    IDs across rounds. `REPAIR_ROUNDS` resets each time Step 10 sends work back.
- **Step 10 (Design Review, TOUCHPOINT).**
  - Write the current MCP document to `PHASE_FILE_PATH` (B23).
  - Show:
    - the architect's latest `## For the user` (absent on a resumed run, which has no architect
      report yet)
    - the UX Contract notice when present (keep `phase_command.py:663-668`)
    - the critic's `## For the user`
    - `UNRESOLVED_CHECKS` as one decision: send back with direction, or accept as-is
  - Ask the open ODs, the CQs, and, when `BP_AVAILABLE`, every unmarked RP line in the ledger. That
    is normally only the one new gap from draft or revise, plus any line left unmarked because bp was
    unavailable earlier. An approved RP goes to Step 7 with `RETURN_TO` = "Step 10 follow-up".
  - **An answer that changes the design goes back to the architect before the final prompt.** That
    is an OD answered with anything but its Recommended option (the draft follows Recommended), or a
    CQ answered with Option B. Store `[round N | review]` naming the new SD IDs, re-engage the
    architect in `revise`, and go back to Step 9. If an RP was also approved, run Step 7 first; its
    follow-up's single `revise` then carries both the new SD IDs and the new `- Read:` lines.
  - **A question that needs new codebase knowledge** is relayed as in Step 6, in `revise` mode. If
    the report's `persisted` is `nothing`, return to this step's final prompt; otherwise go to
    Step 9.
  - Then a single prompt: approve the design and go to sign-off; tell me what to change; or "I edited
    phase.md myself".
  - **Re-read the disk first, whatever the choice.** If `PHASE_FILE_PATH` differs from what this step
    wrote, run the hand-edit path before acting on the choice. Today's Step 8 validates either way
    for the same reason (`phase_command.py:691-694`). A change request must never silently discard a
    hand edit.
  - **Change.** Store the direction as `[round N | review]`, re-engage the architect in `revise`,
    and go back to Step 9.
  - **Hand edit.** Keep today's path (`phase_command.py:704-764`), with these changes:
    - The steps stay the same: re-read, `validate_document`, show content loss to the user, diff into
      `source=user-edit` SDs, store through `store_document_user_edit`, write the result back to
      disk, then go to Step 9.
    - **The marker survives a hand edit.** Before storing, set `### Shape Gate` in the edited
      markdown back to the value the orchestrator last wrote. That store path is
      `store_document`, which writes the marker (B2), and a hand edit is not a sign-off.
    - The "Abort — send back to architect" option (`:740-743`) now stores the validation report as
      `[round N | review]`, re-engages the architect in `revise`, and goes to Step 9 instead of
      Step 5.
    - User-edit SDs keep today's `section=<H2 > H3>` field (`:752`) and get real SD IDs.
  - **Accepting unresolved checks** records `- SD-NNN | source=user | supersedes=unresolved-checks |
    decision=accept as-is: <each finding verbatim> | …`.
    - `unresolved-checks` is a new reserved `supersedes` token.
    - Amend README's settled-decision contract in the same commit, which README requires ("changes
      it here first"). Work item 13 lists every amendment.
- **Step 11 (Sign-off, TOUCHPOINT).**
  - Ask every remaining OD and CQ, or accept their defaults. An answer that changes the design
    follows Step 10's rule: revise, then Step 9, then Step 10.
  - Then a single prompt: sign off and commit the files this run wrote; sign off without committing;
    or go back to design review.
  - On sign-off, in this order:
    1. Confirm `implementation.md` exists at `IMPLEMENTATION_PLAN_PATH` (set in Step 3). If it is
       missing, re-engage the architect in `revise` once, then fail closed.
    2. Run materialization, keeping `phase_command.py:862-956`. The scratch-file writes, the CLI
       call and its fail-closed exit, the conflict prompts and the SD recording all stay.
       - Conflict prompts stay guarded, so they appear only when target files exist.
       - Reword their resume line from "resume this FOR loop" (`:901`) to "resume at Step 11 …".
         Today that block has one WAIT and no "resume at Step" marker, which breaks B11's
         waits == resumes check once it lives in Step 11.
       - The three conflict-choice SDs (`phase_command.py:906`, `:911`, `:916`) become
         `source=user`, because they answer a prompt.
       - The merge-time unresolved-conflict SD (`:941`) becomes `source=materializer`, because it
         reports a tool outcome rather than an answer.
       - The existing `source=materializer` SDs stay
         (`tests/unit/templates/test_phase_skeleton_materialization_gate.py:81`).
    3. In one `store_document`, ensure `` - Constraint: `<PHASE_DIR>/implementation.md` `` is
       present (keep `phase_command.py:1040-1047`) and set `### Shape Gate` to `shape-settled`. If
       materialization fails closed, the phase is not marked settled. That keeps today's "before
       the gate flips" guarantee (`phase_command.py:856-859`).
    4. Write that final document to `PHASE_FILE_PATH`.
    5. Commit, only if the user chose to.
       - Stage exactly `PHASE_FILE_PATH`, `IMPLEMENTATION_PLAN_PATH` and `WRITTEN_PATHS`
         (`phase_command.py:956`) with `git add --`, never `-A`.
       - Never stage the two scratch files.
       - Run `git commit` with today's heredoc form (`:961-963`) and hooks enabled (B27), for
         example with the message `design: sign off <PHASE_NAME>`.
       - If a hook rejects the commit, show its output and leave the files uncommitted; never retry
         with hooks disabled.
- **Step 12.**
  - Keep platform storage (`phase_command.py:1594-1608`) and the completion contract, including the
    fields `tests/unit/templates/test_command_templates.py:666` asserts.
  - The handoff names `{tools.code_command_invocation}`
    (`tests/unit/platform_tests/test_tui_adapters.py:895`). The TUI-tiered handoff is phase 4's.
  - Rewrite the storage restriction banner (`phase_command.py:1557-1580`) so it names exactly the
    disk writes this flow makes:
    - `PHASE_FILE_PATH`, after every orchestrator `store_document` (the disk mirror), and the
      hand-edit write-back
    - the two materialization scratch files at Step 11
    - the architect's `implementation.md`
- **Removed:**
  - `technical_phase_template` (`phase_command.py:13-56`) and the Expected Output Structure that
    renders it (`:1776`); the architect owns the structure. Drop the imports that only they used:
    `indent`, `PhaseStatus`, `Phase` and the grammar placeholders (`phase_command.py:1`, `:3-4`,
    `:6-10`).
  - Re-point both imports of the command's copy to
    `src.platform.templates.agents.phase_architect.technical_phase_template`:
    `tests/unit/templates/test_phase_section_references.py:21` and
    `tests/unit/models/test_content_loss_detection.py:21`. A grep of `tests` and `src` on
    2026-11-13 found no other importer.
  - Phase 1's verify-command prompt inside Step 12.6 was cut before phase 1 was implemented (phase
    1, item 7, "Cut from this phase"), so there is nothing to delete beyond Step 12.6 itself. Confirm
    with `grep -n "USER_VERIFY_COMMANDS\|VERIFY_MARKERS_KEPT" src` (no output). The briefing's
    missing-verify-command OD is the first place the user is asked.

**7. Template-contract helper extensions** (`tests/support/template_contract.py`; test-only).
- **Recognize two tools without parentheses.** `_BUILTIN_CALL_PATTERN`
  (`tests/support/template_contract.py:15`) recognizes only `Read|Write|Glob|Bash|Grep|Task`
  followed by `(`. Also recognize `AskUserQuestion` and `SendMessage` as invoked tool names, so
  `tests/unit/templates/test_phase_workflow_gates.py:31` catches F12-class gaps on Claude Code.
  opencode's `question` is too common a word to pattern-match, so B6 covers that TUI directly.
- **Add `wait_sites()`.** It returns each `WAIT for` line with its step number and whether it is
  guarded.
  - A WAIT is guarded when any enclosing block header is `IF`, `ELIF` or `ELSE`. Find the enclosing
    headers by walking up to lines of strictly smaller indentation, repeatedly.
  - `FOR`, `WHILE` and `REPEAT` are loops, not guards.
- **Add `touchpoint_steps()`.** It returns the step numbers whose heading carries `TOUCHPOINT`.

**8. Existing tests, by fate.** This extends F36 with tests F36 did not list. Line numbers are each
test's `def` line unless the row says otherwise. Paths are under `tests/unit/templates/` unless a path
is given.

| Test | Fate |
|---|---|
| `test_phase_workflow_gates.py:19` | re-anchor (B18): once repair rounds are spent, the `user_input` branch routes to Step 10, which blocks and persists feedback. The branch body itself holds neither a `WAIT for` nor `store_user_feedback`, so the test follows the route |
| `test_phase_workflow_gates.py:31` | keep; extend the helper (work item 7) |
| `test_phase_workflow_gates.py:52` | remove |
| `test_phase_shape_act_gate.py:31`, `:43`, `:61` | remove |
| `test_phase_shape_act_gate.py:71` | re-anchor on Step 10 (B25) |
| `test_phase_shape_act_gate.py:86`, `:100` | keep the pattern over every step that has a WAIT (B11) |
| `test_phase_skeleton_materialization_gate.py:33`, `:46`, `:59` | re-anchor: only Step 11's sign-off path reaches `materialize-skeletons` (B26) |
| `test_phase_skeleton_materialization_gate.py:70`, `:81` | keep; anchor on Step 11 |
| `test_phase_implementation_plan_gate.py:62`, `:71`, `:76` | keep |
| `test_phase_implementation_plan_gate.py:89` | re-anchor on the `draft` branch (B28) |
| `test_phase_implementation_plan_gate.py:100` | remove |
| `test_agent_templates.py:440`, `:451`, `:462`, `:487`, `:559`, `:607` | remove |
| `test_agent_templates.py:474` | rewrite: keep both path-validity markers; drop the API assertions |
| `test_agent_templates.py:540` | drop the `get_loop_status` assertion |
| `test_agent_templates.py:547` | rewrite for `review`, `review_round` and config context; guidance comes from feedback |
| `test_agent_templates.py:569` | keep the parser-contract strings |
| `test_agent_templates.py:583`, `:838` | re-anchor (B19): `[judgment]` CQ, not a blocker condition |
| `test_agent_templates.py:596` | rewrite (B4): `iteration` comes from `review_round` |
| `test_agent_templates.py:618` | keep: Malformed Decision Entry is a mechanical blocker in `review`. Phase 3 deletes it later, when the check moves to `validate_document` (phase 3 work item 9) |
| `test_agent_templates.py:891` | rewrite: guidance is read from the round-0 briefing feedback entry, and every guidance path is still read |
| `test_agent_templates.py:903`, `:956` | remove |
| `test_agent_templates.py:932` | rewrite as the RP line shape (Technologies/Topics/Query) |
| `test_agent_templates.py:383-437` (`TestCreatePhaseTemplate`), `:661`, `:815`, `:872` | keep |
| `test_command_templates.py:353` | rewrite (B16) |
| `test_command_templates.py:481` | keep (`REVIEW_DECISION == "completed"`). It also forbids the quoted literal `"complete"` (work item 6) |
| `test_command_templates.py:516`, `:523` | rewrite (B14). `:529` asserts `BP_PIPELINE_COMPLETE` is absent, which inverts |
| `test_command_templates.py:532`, `:570`, `:578`, `:678` | remove. `:678` asserts Step 16.5's policy banner |
| `test_command_templates.py:652` | re-anchor: Step 12's platform store precedes its completion contract, and `Automatic Task Generation` stays absent |
| `test_command_templates.py:812` | keep only the main-critic half |
| `test_command_templates.py:339` | keep. Do not name a variable `MAX_ACTIVE_WORKERS` (asserted at `:348-349`) |
| `test_command_templates.py:1188` | rewrite: drop the `workflow_guidance_markdown: WORKFLOW_GUIDANCE_MARKDOWN` assertion, because invocations no longer carry it; keep the rest |
| `test_command_templates.py:500`, `:508`, `:666`, `:1176`, `:1382`, `:1539` | keep |
| `tests/unit/platform_tests/test_tool_enums_and_validation.py:123` | rewrite to `Task(bp-pipeline)` |
| `tests/unit/platform_tests/test_tool_enums_and_validation.py:126-127` | remove |
| `tests/unit/platform_tests/test_tui_adapters.py:904` | remove (Step 16.5 banner) |
| `tests/unit/platform_tests/test_tui_adapters.py:895` | keep |
| `test_frontend_elicitation_phase10.py:101`, `:155`, `:175`, `:200`, `:219`, `:230`, `:238` | remove |
| `test_frontend_elicitation_phase10.py:128`, `:163`, `:184`, `:208` | re-anchor (B17, B12, B15, B13) |
| `test_frontend_elicitation_phase10.py:58`–`:93`, `:114`, `:122`, `:140` | keep |
| `test_ux_contract.py:42` | remove |
| `test_ux_contract.py:91` | re-anchor on Step 10 (B29) |
| `test_ux_contract.py:54`, `:64`, `:74`, `:81`, `:122` | keep |
| `test_phase_design_layer.py:52` | re-anchor (B19) |
| `test_phase_design_layer.py:26`, `:41`, `:63` | keep |
| `test_phase_section_references.py` | keep; re-point the import (work item 6) |
| `tests/unit/models/test_content_loss_detection.py` | keep; re-point the import at `:21` (work item 6) |
| `test_phase_runtime_language_config.py`, phase 1's B11 | re-anchor on `step_body('3')`. Keep the `respec-ai language-guidance` and `### Language Authoring Notes` assertions and the `ELSE` fallback. Narrow the "no `EXIT:`" assertion to the language-guidance block, because Step 3 also holds the loop link's fail-closed exits (today's Step 4.2, `phase_command.py:377`, `:393`) |
| `test_phase_runtime_language_config.py`, phase 1's B12 | re-anchor on the briefing. The architect half stays: it contains `(verify: ask user` and names `no_preference`. Its `explore` branch raises the missing-verify-command OD with the three options above, and Step 6 ends the run on Option A. Delete the `step_body('12.6')` assertions with the step |
| `tests/conftest.py:164-191` (`phase_threshold=90`) | keep. A score of 100 clears 90, and 0 never does |

**Soft-cap call sites** lose their keyword arguments:
- `test_agent_templates.py:475`, `:488`, `:541`, `:548`, `:560`, `:570`, `:588`, `:601`, `:613`,
  `:623`, `:672`, `:840`
- `test_frontend_elicitation_phase10.py:49`
- `test_phase_design_layer.py:57`, `:68`
- `test_ux_contract.py:67`, `:75`, `:84`

Every other phase-architect or phase-critic test is expected to stay green. If one goes red, decide
keep, re-anchor or remove using testing.md's discriminating question, and add it to this table.

**9. Trim create-phase** (`src/platform/templates/agents/create_phase.py`).
- **Move the completeness gate.** Move `MANDATORY PHASE COMPLETENESS VALIDATION GATE`
  (`create_phase.py:172-189`) to between STEP 1 and STEP 2 (`create_phase.py:95-110`), so it runs
  before the MCP store (B30).
- **Delete the stale and contradictory error-handling text:**
  - *Phase Context Issues* (`create_phase.py:227-238`): *"Proceed with partial phase extraction"*
    contradicts the gate.
  - *Phase Validation Failures* and *Quality Assurance* (`create_phase.py:255-273`): *"Verify
    research requirements and architecture decisions documented"* is stale for a sparse phase.
- **Keep unchanged**, because both roadmap paths dispatch this agent
  (`src/platform/templates/commands/roadmap_command.py:490-536`,
  `src/platform/templates/agents/roadmap_orchestrator.py:237-266`):
  - the invocation contract
  - the `FROZEN_DISCARD_WARNING` check (`create_phase.py:105-109`)
  - the output protocol (`create_phase.py:136-162`)
  - `TASKS:` and `## Invocation Contract`, which `tests/unit/templates/test_agent_templates.py:729`
    requires

**10. The respec-code gate** (open call 2).
- **The change.** `src/platform/templates/commands/code_command.py:221` (*"IF SHAPE_GATE not in
  ["shape-settled", "shape-amended"]:"*) accepts only `shape-settled`. Update the DIAGNOSTIC at
  `src/platform/templates/commands/code_command.py:223` to match.
- **The test.** Add one beside
  `test_coding_workflow_refuses_to_start_when_shape_was_never_settled`
  (`tests/unit/templates/test_task_removal_workflow.py:59`). Its gate condition names
  `shape-settled` and not `shape-amended`. This is a legitimate string assertion, because the
  orchestrator writes these exact values.

**11. Remove the soft caps.**
- **The change.** Delete `phase_length_soft_cap` and `phase_shape_soft_cap` from `LoopConfig`
  (`src/utils/setting_configs.py:29-37`), and their wiring
  (`src/platform/template_generator.py:274-276`).
- **The consequence is small.** `LoopConfig` keeps `extra='forbid'`
  (`src/utils/setting_configs.py:10`), but pydantic-settings ignores unknown prefixed environment
  variables.
  - Probe on 2026-11-13, pydantic-settings 2.14.1: `LOOP_TASK_THRESHOLD=80` with today's
    `LoopConfig` constructs without error. So a stale `LOOP_PHASE_LENGTH_SOFT_CAP` is silently
    ignored; it does not raise at import.
  - `docs/phase-refactor/phase-6-task-removal.md` ("Traps") claims the opposite and is wrong on
    this point.
  - `extra='forbid'` rejects only unknown constructor keywords: any code or test that builds
    `LoopConfig(phase_length_soft_cap=…)`. Today that is none (`tests/conftest.py:171-187` passes
    no soft caps).

**12. Tool descriptions the architect reads** (F31). Generalize the `store_current_analysis` and
`get_previous_analysis` docstrings (`src/mcp/tools/feedback_tools_unified.py:976-982`,
`src/mcp/tools/feedback_tools_unified.py:1000-1006`). They describe only the analyst workflow; make
them describe a per-loop notes slot that each write replaces in full.

**13. Documents.**
- `docs/TEMPLATE_AUDIT.md`: add a contract update note after `docs/TEMPLATE_AUDIT.md:5-10` recording
  that respec-phase dispatches `bp-pipeline` directly (decisions.md).
- decisions.md: record the outcomes of open calls 1 and 2, and M7's result (open call 1).
- `deferred-issues.md`:
  - Delete phase 1's "Step 3's settled route skips Step 4.5" row. The new Step 3 loads the config
    context before Step 4 routes.
  - The Linear/GitHub draft-persistence gap (judgment calls above).
  - Probable, so confirm before logging: a background subagent on Claude Code keeps only a fixed
    list of built-in tools (sub-agents doc, "Available tools"), and `DesignSync` is not on it. The
    tools reference does not list `DesignSync` at all, so whether the filter applies to it is
    unverified. Spawn the architect on a UI phase and check whether `DesignSync` is available. If
    it is not, the architect's live-design grounding (frontend-refactor phase 8) silently degrades
    to the local bundle.
  - F39's duplicated codex guardrail.
- README, in the same commit as the code that needs each change:
  - **"Settled decision entry".** Five amendments:
    - The reserved `supersedes=unresolved-checks` token (Step 10).
    - A `materializer` source for unmaterialized and unintrospectable paths (Step 11).
    - Which fields each source carries: `user-edit` carries `section=` and no `supersedes` or
      `rejected`; `materializer` carries neither.
    - SD IDs are the next unused number (work item 6, "IDs and marks").
    - Today's `user-menu` and `user-override` sources are retired in favor of `user`.
  - **"Relay protocol" step 5.** Replace *"The tag lets the architect apply only what is new"*.
    Newness is decided by `## User Input` position, and the tag is context (work item 5, STEP 2).
  - **"bp invocation per TUI".** Replace *"Whether `check` also confirms that the `bp-pipeline` agent
    is installed is unverified"* with the result in work item 2.
  - **"Agents and modes" and "Cross-cutting risks" 6.** Correct them if M7 shows that a path-scoped
    `Write` is not enforced on Claude Code either. decisions.md's caveat already says it is
    unverified there.
- `docs/WORKFLOWS.md`: rewrite "How it works" under `/respec-phase` (`docs/WORKFLOWS.md:223-228`) for
  the three touchpoints, and the `/respec-phase` threshold row (`docs/WORKFLOWS.md:589`).

## Out of scope

- **The structural checks in `validate_document`** (phase 3). `validate_document` stays a
  content-loss check in this phase (F29), used only on the user's hand edits.
- **The brief format** (phase 4). That means:
  - Grounding, Delegation Bounds, Behaviors & Acceptance and Guardrails
  - step delegation briefs
  - the finalizer and the cold-start check
  - the TUI-tiered handoff
- **Language neutrality** (phase 1). This phase only has to stay green against phase 1's guard.
- **Updating respec-code or respec-patch readers.** Work item 10 is the one sanctioned edit.
- **Persisting the draft on Linear and GitHub**, DesignSync in background subagents, and F39. Log
  them (work item 13).
- **The upstream best-practices-rag defects** (F17). Work around them as specified; do not fix them.

## Exit criteria

- [ ] B1–B30 observed failing first, then pass. B2, B3, B5 and B7 pass on day one; B2's
      temporary-break check and the B5 and B7 negative self-tests are what prove them.
- [ ] Every red test that no B-row covers has been added to work item 8's table with its fate.
- [ ] Both "Already done?" probes print nothing, and phase 1's prerequisite probe still passes.
- [ ] `uv run pytest` is green. The postgres half of B1 and B2 has been run against a live database,
      not skipped.
- [ ] `uv run respec-ai regenerate --force --tui all` completes in a scratch project, after
      `respec-ai models opencode` and `respec-ai models codex`. The written artifacts are valid for
      all three TUIs.
- [ ] The open calls are recorded: decisions.md for the Write grant; decisions.md, or
      deferred-issues.md, for the respec-code gate.
- [ ] **M1, opencode research.** The installed opencode dispatches the `"hidden": true`
      `bp-pipeline` subagent by name, and honors `permission.task` (README "bp invocation per TUI").
      Until this passes, the opencode research path is unverified; say so in README.
- [ ] **M2, end to end on Claude Code.** On a markdown scratch project:
  - at most three touchpoints are counted
  - deny-all research produces zero `bp-pipeline` tasks
  - approving one `synthesis-only` RP adds a `- Read:` line
  - a design-review change resumes the architect with `SendMessage` and no re-exploration
  - every background completion notification is waited for, with no prompt in between
- [ ] **M3.** The 4-question batch limit has been confirmed against the live `AskUserQuestion` tool
      definition, and `selection_batch_limit` corrected if it differs.
- [ ] **M4, resume.** Check three things:
  - Interrupt during design review and re-run: the run resumes at Step 9 → Step 10 from the on-disk
    draft.
  - Interrupt after the briefing and before the draft, then re-run: no settled decision is asked
    again, and no `[declined]` proposal is offered again.
  - Re-open a signed-off phase: the marker reads `shape-amended`, then `shape-settled` after the
    next sign-off.
- [ ] **M5, the frozen reader.** On the signed-off output:
  - `extract_steps` (`tests/support/plan_extraction.py`) finds every step of the produced
    `implementation.md`
  - the Checklist items carry `(Step N)` and `(verify: …)`
  - respec-code passes its shape gate and its implementation-plan read
    (`src/platform/templates/commands/code_command.py:219-241`)
- [ ] **M6.** Reword every prompt in the new flow arbitrarily, and the suite stays green. If it goes
      red, those tests pin phrasing rather than behavior; fix the tests.
- [ ] **M7, the write scope on Claude Code.** Spawn the regenerated architect and have it write a
      file outside `.respec-ai/plans/*/phases/*/implementation.md`. Record whether the
      `Write(<glob>)` entry in its `tools` list resolves at all, and whether it refuses that write.
      Do not assume either answer (open call 1). Record the result in decisions.md.
