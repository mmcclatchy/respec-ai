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

On 2026-11-16, after stage S4b, both print nothing.

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
  `_BANNED_ACTION_PATTERNS` (`tests/unit/templates/test_agent_templates.py:52-61`) bans `should`,
  `consider`, `may`, `can` and others. It applies under `_AGENT_ACTION_SECTION_TOKENS`
  (`tests/unit/templates/test_agent_templates.py:63`) and `_COMMAND_ACTION_SECTION_TOKENS`
  (`tests/unit/templates/test_command_templates.py:32`), which include every heading that starts with `### Step`
  and every `MANDATORY` banner.
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
| B6 | The orchestrator declares the question tool it prompts with (F12), on every TUI that has one. codex has none (`src/platform/tui_adapters/codex.py:77`). | same; plus the extended invoked ⊆ declared test |
| B7 | No command can run as a fork. No raw `generate_command_template` output, for any command on any TUI, sets `context: fork` (F11). A negative self-test proves the checker fires. | same |
| B8 | Every subagent returns the fixed four-section report, and the orchestrator stops on a failed or malformed one. The architect and critic templates require `## For the user`, `## Decisions needed`, `## Research proposals` and `## Status`, in order, with `- None` for an empty section. The command branches on `## Status` `result`, and `failed` or a malformed report ends the workflow. | new `tests/unit/templates/test_phase_cooperative_flow.py` |
| B9 | A decision is recorded only from a user's answer. Every write of a `source=user` SD in the command comes after a blocking prompt in the same step (F10). Match `source=user` only when a space follows it, because `source=user-edit` also contains `source=user`. | same |
| B10 | The happy path has at most three touchpoints. At most three steps carry the touchpoint token, and they are briefing, design review and sign-off. Every `WAIT for` outside them sits under a condition naming its trigger. A negative self-test proves the checker fires. | same, with the `wait_sites()` helper (work item 7) |
| B11 | Every user prompt blocks and has a resume point, and the prompts are identically shaped on all three TUIs. This re-anchors `tests/unit/templates/test_phase_shape_act_gate.py:86` and `tests/unit/templates/test_phase_shape_act_gate.py:100`. | same |
| B12 | Research costs nothing unless approved. On the deny-all path no `bp-pipeline` invocation is reachable. The single dispatch site runs only `[approved]` lines, after the approval prompt. This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:163` (now `:155`). A negative self-test proves the checker fires. | same |
| B13 | A declined proposal is never offered again. Only a genuinely new gap is offered, and only once. This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:208` (now `:200`). | same |
| B14 | Research dispatch names something runnable on every TUI. `Task(bp-pipeline)` is granted, and the invocation names `bp-pipeline` exactly on all three TUIs, never `respec-bp-pipeline-agent` on codex. There is no `Task(bp)`, `Skill(bp)` or `$bp` (F15). | same; `tests/unit/platform_tests/test_tool_enums_and_validation.py` |
| B15 | When bp is unavailable the workflow degrades and never terminates. The preflight is `best-practices-rag check --tui <tui>`. On failure the run continues without research and tells the user. This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:184` (now `:176`). | `test_phase_cooperative_flow.py` |
| B16 | Only validated research becomes a `- Read:` line, and dispatch is bounded. A result counts only if it contains `BP_PIPELINE_COMPLETE. Output:` and the file exists. `synthesis-only` items run at most 3 in parallel; `web-research` items run one at a time (F17). This re-anchors `tests/unit/templates/test_command_templates.py:353` (now `:359`). | same |
| B17 | Nothing makes research mandatory. There are no automatic API prompts and no post-synthesis critic, and no critic finding concerns research coverage or declined research (F8). This re-anchors `tests/unit/templates/test_frontend_elicitation_phase10.py:128`. | same; `TestPhaseCriticTemplate` |
| B18 | The user only sees a design the critic has reviewed. Mechanical findings get two automatic repair rounds, then reach the user as one "unresolved checks" decision. The loop's `user_input` status is repaired like `refine` while repair rounds remain, and routes to that decision once they are spent. It can arrive before any repair (Step 9). Every loop-decision branch compares against a real `LoopStatus` value (F1). This re-anchors `tests/unit/templates/test_phase_workflow_gates.py:19`. | same |
| B19 | Critic judgment calls reach the user as questions and never block. Unjustified seams, under-surfaced decisions, non-divergent options and plan-constraint fit are `[judgment]` `CQ-NNN` entries, never blocker conditions. Sign-off requires every `CQ` to be answered or its default accepted. This re-anchors `tests/unit/templates/test_agent_templates.py:583`, `tests/unit/templates/test_agent_templates.py:838` and `tests/unit/templates/test_phase_design_layer.py:52`. | same; `TestPhaseCriticTemplate` |
| B20 | A send-back is never lost. Direction is stored with its round tag before the architect is re-engaged. The architect fetches all feedback on every engagement, with no loop-status gate (F2). It decides what is new by `## User Input <i>` position, not by round number, so the round-0 guidance and a round-0 briefing answer are both applied. | same; architect template tests |
| B21 | Re-engagement works on every TUI, at every re-engagement: explore to draft, a relayed briefing question, an automatic repair, and a design-review change. Claude Code resumes the same architect with `SendMessage` and falls back to a fresh invocation. opencode and codex re-invoke fresh, and no rendered opencode or codex template mentions `SendMessage` (F13). | same |
| B22 | A re-run resumes from the stage marker. `unshaped` goes to explore. `shape-proposed` and `shape-amended` go to critic review, then design review, from the synced draft. `shape-settled` offers to re-open or shows the handoff. | same |
| B23 | Nothing the orchestrator stores is lost to the sync at the start of a re-run (markdown platform). Every orchestrator `store_document` is followed by writing the same markdown to `PHASE_FILE_PATH`: briefing SDs and research marks, `- Read:` lines, the marker, and the draft before every design-review round. | same |
| B24 | Only the orchestrator writes the marker, with the README values: `shape-proposed` at the first draft, `shape-settled` at every sign-off, `shape-amended` at a re-open. No architect or critic instruction sets, tests or branches on a marker value (F3). The one tolerated occurrence is the `### Shape Gate` line inside the architect's embedded example structure: `technical_phase_template` is `Phase(...).build_markdown()`, which always emits `unshaped` (`phase_architect.py:15-51`, rendered at `:959` after stage S3; `:18-66` and `:1075` at `a64f0dc`). B1 makes that line inert, and the test excludes that block. | same; agent template tests |
| B25 | A hand edit of `phase.md` is validated, diffed into `source=user-edit` SDs, and stored. This re-anchors `tests/unit/templates/test_phase_shape_act_gate.py:71`. | same |
| B26 | Skeletons materialize only after sign-off, and a conflict prompt appears only when a target file exists. Unmaterialized and unintrospectable paths are shown to the user and recorded. This re-anchors `tests/unit/templates/test_phase_skeleton_materialization_gate.py`. | same |
| B27 | A commit is offered, never automatic, and never bypasses hooks. The commit runs only after the user says yes, and no `--no-verify` appears anywhere in the phase command. | same |
| B28 | The signed-off output still feeds frozen respec-code. Draft mode carries constraint carry-forward and the `#### Step N:`, Checklist and DR formats, and respec-code's gate accepts only `shape-settled` (F33, F34). The gate half exists only if the user accepts open call 2; if it is rejected, drop that half and log the window instead. This re-anchors `tests/unit/templates/test_phase_implementation_plan_gate.py:89`. | that file; new test beside `tests/unit/templates/test_task_removal_workflow.py:64` (`test_coding_workflow_refuses_a_reopened_phase_until_it_is_signed_off_again`, `:70`) |
| B29 | The UX Contract is surfaced at design review when present. This re-anchors `tests/unit/templates/test_ux_contract.py:91` (now `:79`). | that file |
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
- **The postgres half of B1 and B2 skips without a database** (`tests/conftest.py:284`). Run it
  against a live database before calling B1 green.
- **The touchpoint token is a contract string.** Any template test that asserts it says so in a
  comment, per testing.md's exception.

## Scope

### The new `/respec-phase` step map

Tests anchor on step numbers through `template_contract.step_body()`, so keep these numbers. The
decision variable in Step 9 must match `_BRANCH_HEADER_PATTERN`
(`tests/support/template_contract.py:29-32`), so name it `REVIEW_DECISION`.

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
  - postgres: `src/utils/state_manager/postgres.py:584-602` (*"frozen_fields = ("* … *"'version':
    existing_data['version'] + 1,"*)
  - in-memory: `src/utils/state_manager/in_memory.py:396-414`
  - **Landed (stage S1, 2026-11-16):** both now carry `'shape_gate': existing_data['shape_gate']`
    in `final_phase`; the anchors above include that line.
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
  (`src/platform/tool_enums.py:51-95`). Map it to `'SendMessage'` in the Claude Code map
  (`src/platform/tui_adapters/claude_code.py:68-89`) and to `None` in the opencode and codex maps.
  `tests/unit/platform_tests/test_tui_adapters.py:89-93` fails until every adapter decides.
- **The external-agent method.** Add `render_external_agent_invocation(agent_name, description,
  params)` to `TuiAdapter`.
  - The base implementation delegates to `render_agent_invocation`. That is correct for Claude Code
    and for opencode (`src/platform/tui_adapters/opencode.py:208-229`).
  - codex overrides it to use the exact name: today's helper renames every agent to
    `respec-<x>-agent` (`src/platform/tui_adapters/codex.py:389-395`).
  - Keep the codex close-after-harvest line (`src/platform/tui_adapters/codex.py:281`).
- **The bp TUI name.** Add an abstract `best_practices_tui` property, the `--tui` value
  `best-practices-rag check` accepts: `claude`, `opencode` or `codex`. This mirrors
  `_normalize_tui_name` (`src/cli/services/best_practices_preflight.py:48-51`). The adapter modules
  must not import CLI commands (`tests/unit/platform_tests/test_tui_adapters.py:82-87`), so this is
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
- **Landed (stage S2, 2026-11-16).** All four, as specified.
  - `SEND_MESSAGE` is `tool_enums.py:70`; Claude Code maps it at `claude_code.py:77`, opencode and
    codex map it to `None` (`opencode.py:39`, `codex.py:68`).
  - `render_external_agent_invocation` is `base.py:160`. codex overrides it at `codex.py:258`;
    both codex paths share `_render_isolated_invocation` (`codex.py:266`), so respec-agent output
    is byte-identical and the external one keeps every lifecycle line, close-after-harvest included.
  - `best_practices_tui` is abstract at `base.py:83` (`claude_code.py:61`, `opencode.py:23`,
    `codex.py:51`). `selection_batch_limit` is `base.py:78` (1) and `claude_code.py:56` (4). M3 is
    confirmed: the live `AskUserQuestion` schema takes 1-4 questions per call (orchestrating session,
    2026-11-13), so 4 stands.
  - Tests: `tests/unit/platform_tests/test_tui_adapters.py`, `TestCooperativePhaseAdapterCapabilities`.
    The bp TUI name is checked against `_normalize_tui_name`, not against literals, so the phase
    preflight and the init preflight cannot drift apart.

**3. Models and invocation helpers.**

`PhaseCommandTools` (`src/platform/models/phase.py:14-200`):
- **Delete these fields:**
  - the six invocations: `src/platform/models/phase.py:34-55`
  - `store_plan` and `get_plan`, which the template never uses: `src/platform/models/phase.py:77`,
    `src/platform/models/phase.py:80`
  - `decide_shape_loop_action`: `src/platform/models/phase.py:84`
  - the shape-act fields: `src/platform/models/phase.py:90-97`
  - `phase_command_reference` and `roadmap_command_invocation`, whose only users were Step 16's
    decomposition branch and Step 16.5's policy banner: `src/platform/models/phase.py:56-57`
  - `plan_command_invocation` (`src/platform/models/phase.py:58`), whose only user is the deleted
    error-scenario tail (`phase_command.py:1690`)
  - `mcp_tools_reference`, which always renders empty (F38): `src/platform/models/phase.py:121-142`,
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

In `create_phase_command_tools` (`src/platform/template_helpers.py:207-440`):
- Replace the grant at `src/platform/template_helpers.py:219` (*"builder.add_builtin_tool(
  BuiltInToolCapability.TASK, 'bp')"*, at `a64f0dc`) with `'bp-pipeline'`.
- Add `_add_adapter_question_tool(builder, adapter)` (`src/platform/template_helpers.py:119-121`)
  for F12.
- Add `builder.add_optional_builtin_tool(BuiltInToolCapability.SEND_MESSAGE)`.
- Keep the Write grant at `src/platform/template_helpers.py:231` and the Glob grant at
  `src/platform/template_helpers.py:234`.

Invocation inputs follow README "Agents and modes":
- **Agents** get `phase_mode`, `loop_id`, `plan_name`, `phase_name` and
  `project_config_context_markdown`. Critic invocations gain that config context too (F22), plus
  `review_round`.
- **Drop `optional_instructions` and `workflow_guidance_markdown`** from every invocation
  (`src/platform/template_helpers.py:258-259`, `src/platform/template_helpers.py:271-272`,
  `src/platform/template_helpers.py:284-285`, `src/platform/template_helpers.py:297`,
  `src/platform/template_helpers.py:308`, `src/platform/template_helpers.py:319`). The contract
  forbids passing conversation text. Step 3 stores Step 1's `WORKFLOW_GUIDANCE_MARKDOWN` as feedback
  tagged `[round 0 | briefing]`, and agents read it through `get_feedback`. This keeps the README
  contract unchanged.
- **Description strings are user-visible on opencode** (README "Agents and modes"), so state the
  mode accurately and neutrally. For example, `explore` is "explore the plan, the codebase and the
  local knowledge base, then return the briefing report".
- **Landed (stage S2, 2026-11-16), command side only.**
  - The eight new fields are `src/platform/models/phase.py:60-74`, built at
    `src/platform/template_helpers.py:341-370` and `:433-439`. Shared inputs are
    `_PHASE_AGENT_IDS`, `_phase_agent_inputs` and `_BP_PIPELINE_DISPATCH_INPUTS`
    (`template_helpers.py:160-187`). `resume_architect` comes from `_render_architect_resume`
    (`template_helpers.py:190`): the tool name is `render_builtin_tool_name(SEND_MESSAGE)`, the
    `to:` line is `ARCHITECT_AGENT_ID`, and the message carries only `phase_mode: ARCHITECT_MODE` and
    the three IDs.
  - `invoke_bp_pipeline` lists every field Step 7 computes, in bp's own Step 5 order. The
    conditional ones state their rule in the value, so Step 7 omits them by that rule: `LANGUAGES` /
    `LANGUAGE_AGNOSTIC` are exclusive, `UNCOVERED_TECH` is partial-gap only, and `COVERED_TECHS` is
    omitted on a full gap.
  - The grant is `Task(bp-pipeline)` (`template_helpers.py:219`). The optional `SEND_MESSAGE` and
    the adapter question tool follow it (`:220-221`); that closes F12 and turns
    `test_phase_workflow_gates.py:31` green on Claude Code.
  - **Not done here; S4b owns it.** Every field on the delete list above still exists, as do
    `store_document_gate_edit` and the six old invocations with their `optional_instructions` /
    `workflow_guidance_markdown` inputs, because the current template still renders them.
    `store_plan` and `get_plan` are unrendered but were kept too, so the deletion lands in one place.
  - **Interim behavior until the template rewrite.** Today's Step 7.5 preflight checks for the old
    `Task(bp)` grant string, so with the new grant the old flow always skips research. The new
    fields are not rendered yet.
  - Tests: `tests/unit/platform_tests/test_tool_enums_and_validation.py`,
    `TestPhaseCommandToolsForTheCooperativeFlow` (B14, B15 and B21 tool halves, B4 invocation half,
    the store for B25), and B6 in `tests/unit/templates/test_phase_relay_guards.py`.
- **Landed (stage S4b, 2026-11-16), the deletions.** Every field on the delete list is gone from
  `PhaseCommandTools` (now `src/platform/models/phase.py:14-138`), with its wiring in
  `create_phase_command_tools` (now `src/platform/template_helpers.py:207-325`): the six old
  invocations, `phase_command_reference`, `roadmap_command_invocation`, `plan_command_invocation`,
  `store_plan`, `get_plan`, `decide_shape_loop_action`, the five shape-act fields
  (`store_document_gate_edit` included) and `mcp_tools_reference`. So are the `optional_instructions`
  and `workflow_guidance_markdown` inputs, which only the old invocations carried.
  - **Changed here, not in the spec:** the `store_document` field's content placeholder is now
    `{PHASE_MARKDOWN}` (was `{EXTRACTED_PHASE_MARKDOWN}`), so every store and its disk-mirror
    write name the same variable. The surviving field descriptions no longer say "detail act",
    and the Write/Glob grant comments cite the new step numbers.
  - **Left in place:** the computed `initialize_refinement_loop_inline_doc`,
    `store_document_inline_doc` and `link_loop_to_document_inline_doc` are no longer rendered by
    the phase command but were not on the delete list. The first one renders
    `` `initialize_refinement_loop(…` `` whenever the tool extractor is initialized, which would break
    the "one loop, in Step 3" count, so the command must not render it.

`PhaseArchitectAgentTools` (`src/platform/models/phase.py:141-164` after stage S4b; `:203-226` after stage S3; `:203-223` before it):
- **Tools:** `GET_DOCUMENT`, `UPDATE_DOCUMENT`, `GET_FEEDBACK`, `STORE_CURRENT_ANALYSIS` and
  `GET_PREVIOUS_ANALYSIS`.
  - Drop `LINK_LOOP_TO_DOCUMENT`, which is granted but unused.
  - Drop the `get_loop_status` field (`src/platform/models/phase.py:220`), which closes F2.
  - Add `store_analysis` and `get_analysis` invocation fields.
- **Built-ins** (`create_phase_architect_agent_tools`, `src/platform/template_helpers.py:793-830` after stage S4b; `:908-945` after stage S3):
  - add `WRITE` scoped to `.respec-ai/plans/*/phases/*/implementation.md` (open call 1)
  - keep the optional `DESIGN_SYNC`

`PhaseCriticAgentTools` (`src/platform/models/phase.py:167-184` after stage S4b; `:229-246` after stage S3; `:226-249` before it):
- **Tools:** drop `GET_LOOP_STATUS` and its field, because the round comes from `review_round` now.
- **Soft caps:** delete `phase_length_soft_cap` and `phase_shape_soft_cap`
  (`src/platform/models/phase.py:241-244`).
- **Factory:** `create_phase_critic_agent_tools` (`src/platform/template_helpers.py:833-857` after stage S4b; `:948-970` after
  stage S3; `:943-972` before it) loses both soft-cap parameters.
- **Landed (stage S3, 2026-11-16), agent side.**
  - The architect is granted `get_document`, `update_document`, `get_feedback`,
    `store_current_analysis` and `get_previous_analysis`, plus Read, Bash, Grep, Glob,
    `Write(.respec-ai/plans/*/phases/*/implementation.md)` and the optional `DESIGN_SYNC`.
    `LINK_LOOP_TO_DOCUMENT` and the `get_loop_status` field are gone; `store_analysis` and
    `get_analysis` are new fields. `get_feedback` stays `count=1` (the latest review only; every
    user entry is returned regardless).
  - The critic is granted `get_document`, `get_feedback` (`count=2`, so it sees the previous
    review's CQ IDs) and `store_critic_feedback`, plus Read, Glob and Bash. `GET_LOOP_STATUS`, its
    field and both soft caps are gone; the factory takes only the adapter.
  - Tests: `tests/unit/templates/test_agent_templates.py`,
    `test_phase_architect_may_write_only_the_implementation_plan` and
    `TestPhaseCriticTemplate::test_template_grants_read_only_review_tools`.

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

- **Landed (stage S3, 2026-11-16).** `phase_critic.py` was rewritten whole. The anchors above
  were re-checked at `e79a794` before the rewrite and still matched (phase 1 did not move the
  critic), so they now describe the pre-rewrite file (`git show e79a794:src/platform/templates/agents/phase_critic.py`).
  The new file, by section:
  - `MANDATORY READ-ONLY REVIEW` (F14), `MANDATORY OUTPUT SCOPE` (the parser-contract and
    storage-failure lines, kept), the Invocation Contract with exactly `phase_mode`, `loop_id`,
    `plan_name`, `phase_name`, `review_round` and `project_config_context_markdown`,
    `MANDATORY PHASE MODE PROTOCOL` (`review` only; anything else is `result: failed`), and
    `MANDATORY FINDING CLASSIFICATION`.
  - STEPs 1-10: validate inputs (a missing or sub-1 `review_round` fails), get the document, get
    feedback (guidance comes from the `[round 0 | briefing]` user entry; every guidance path is
    still read), get the plan, read `implementation.md`, collect settled findings, run the review
    checks, score (100 / 0), store with `Iteration` = `review_round`, report.
  - `## REVIEW CHECKS` holds the Keep list unchanged in substance, classified per the table above,
    plus the Add list.
  - **Not in the spec, decided here:**
    - The stored `### Key Issues` entries carry their ID, `- [judgment] [<Marker>] CQ-NNN: …`,
      because the critic remembers nothing between rounds except its stored feedback. A new CQ
      takes the next number above every `CQ-NNN` in the previous reviews and in the SDs.
    - The implementation.md checks use these mechanical markers: `Implementation Plan Missing`,
      `Step Names No Files`, `Step Without Verify Command`, `Checklist Item Malformed`,
      `Verify Command Not Configured` and `Test List Entry Not Covered`.
    - The report's `result` is `needs-user` when `## Decisions needed` has CQ entries, `complete`
      when it has none, and `failed` on bad inputs or a storage failure.
    - `phase_feedback_template` is built with `CriticFeedback.model_construct`, so the stored
      example shows `Iteration: [review_round from input]` and
      `Overall Score: [100 when ### Blockers is empty, otherwise 0]` instead of `0`.
  - Tests: `TestPhaseCriticTemplate` (B4, B17, B19), the B8 and B24 agent halves in
    `tests/unit/templates/test_phase_cooperative_flow.py`, and the re-anchors listed in work
    item 8. `tests/support/template_contract.py` gained `mechanical_findings()` and
    `judgment_findings()` for them.

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
    orchestrator side is Step 6. **Corrected in stage S3:** the architect's text says only that
    the re-run explores again; it names no marker value, because B24 forbids one anywhere in the
    agent outside the embedded structure example. The unchanged marker is the orchestrator's
    concern (Steps 4 and 6).
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

- **Anchors.** The `phase_architect.py` anchors in this work item were verified at `a64f0dc`;
  phase 1 moved them. At `e79a794`, just before the stage S3 rewrite, they were: invocation
  contract `:160-197`, mode protocol `:201-223`, STEP 0 `:227-246` (`iteration >= 1` at `:235`),
  STEPs 0.5/0.55 `:248-293`, STEP 0.6 `:295-364` (query-kb flag rules `:323-327`, fallback
  `:334-337`), STEP 1.5 `:376-439` (the task-workflow line `:436`), STEP 2 `:441-448` (`:445`),
  the shape/implementation-plan/detail branches `:450-623` (Design Research `:486-494`, UI
  classes `:500-532`, the stale Step references `:514-516`, the marker instruction `:533-535`,
  the gate checks `:551` and `:610`, the "only inputs" restriction `:556-558`, the carry-forward
  `:602-605`), guidance handling `:630-636`, the delivery-intent notes `:648-651` and `:704-706`,
  STEP 4 `:711-721`, STEP 5 `:723-748`, the structure note `:752-753`, the Test Case IDs
  exclusion `:874-876`, "~10 Pages" `:882-890`, Quality Check `:892-902`, "When Decomposing"
  `:932-937`, the domain section lists `:1006-1038` and `:1099-1173`, their checklist
  `:1209-1217`, the domain-H2 block `:1062-1089` with `:1094` and CRITICAL CONSTRAINTS
  `:1091-1095`, REFINEMENT BEHAVIOR `:1225-1253`, KNOWLEDGE BASE INTEGRATION `:1255-1267`, the
  `Synthesize:` format `:1269-1284`, Scanning item 6 `:1301`, the "add all topics" fallback
  `:1313-1318`, Research Identification Challenges `:1320-1329`, COMPLETION `:1353-1361`, the
  `research_requirements` placeholder `:34-42` and the six domain placeholders `:54-61`.
- **Landed (stage S3, 2026-11-16).** `phase_architect.py` was rewritten whole. The new file, by
  section: `MANDATORY RELAY CONTRACT`, the Invocation Contract (exactly `phase_mode`, `loop_id`,
  `plan_name`, `phase_name` and `project_config_context_markdown`), the mode protocol,
  `MANDATORY WRITE SCOPE` (F14), STEP 0 (`get_document`, `get_feedback`, `get_previous_analysis`,
  unconditional, at column 0), STEPs 0.5, 0.55, 1 (guidance from the `[round 0 | briefing]`
  entry) and 1.5, STEP 2 (the feedback rules above), STEP 3 (the three mode branches in one
  `text` fence), the kept plan-context protocols, STEP 4 (persist), STEP 5, `## REPORT FORMAT`,
  `## DECISION ENTRY FORMAT`, and the kept structure, detail and KB sections with the deletions
  above. `DESIGN_RESEARCH_PLACEHOLDER` is deleted from `phase_contract_grammar.py`.
  - **Clarified here; S4 must match:**
    - `persisted` lists only the phase document and `implementation.md` writes, and is `nothing`
      when neither changed. The notes are stored on every engagement and are not listed, so a
      question-only `revise` reports `nothing` and Step 10 returns to its final prompt.
    - `update_document` runs only when the phase document changed; `store_current_analysis` runs
      on every engagement and records `LAST_APPLIED_USER_INPUT`.
    - Draft and revise may add two things to the ledger: nested `- Applied:` lines, and at most one
      new unmarked RP line for a new gap. That line is also the report's single research proposal,
      which is how Step 10 finds it "unmarked in the ledger".
    - Explore's `## Research proposals` lists every unmarked RP line in the ledger, `in-kb` lines
      included.
    - A new OD takes the next number above every `OD-NNN` in the document, including those an SD's
      `supersedes=` names, so a settled OD's number is never reused.
    - `implementation_plan_example` gained a `**Files**:` line per step, so the example satisfies
      the critic's "every step names its files" check. `extract_steps` and the DR format are
      unchanged.
    - The tier comes from `generate-slug`, then `check-file-cache --file` with no model option,
      then `query-kb`, then `Glob`. A cache hit or a confirmed local document is `in-kb:<path>`;
      full coverage is `synthesis-only`; any gap is `web-research`.
  - Tests: B20 and the B8 and B24 agent halves in `tests/unit/templates/test_phase_cooperative_flow.py`,
    including `test_every_input_the_orchestrator_passes_is_one_the_agent_declares` against S2's
    invocations; the architect tests in `TestTemplateConsistency`; and the B12 and B28 re-anchors.
    `tests/support/template_contract.py` gained `guards_for()`, `report_format()`,
    `report_section()` and `declared_inputs()`, each with a self-test.

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
    `tests/unit/templates/test_command_templates.py:470` (`:487` before stage S4b) asserts that the phase command does not
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
    names and error strings, which `test_command_templates.py:700` asserts (`:818` before stage S4b). The iteration checks
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
    fields `tests/unit/templates/test_command_templates.py:562` asserts (`:672` before stage S4b).
  - The handoff names `{tools.code_command_invocation}`
    (`tests/unit/platform_tests/test_tui_adapters.py:960`). The TUI-tiered handoff is phase 4's.
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

- **Red step written (stage S4a, 2026-11-16).** The orchestrator tests are in
  `tests/unit/templates/test_phase_cooperative_flow.py` (orchestrator section), plus B28's half in
  `test_phase_implementation_plan_gate.py`, B29 in `test_ux_contract.py`, and phase 1's B11/B12
  re-anchors in `test_phase_runtime_language_config.py`. They render the command on all three TUIs
  from the same `PhaseCommandTools` they read fields from, and are red against today's command.
  A throwaway prototype written to this item turned every one green, so they are satisfiable
  together. Beyond the bullets above, they pin these shapes; S4b must emit them:
  - **Indent multi-line fields inside a block.** Every invocation and `resume_architect` is
    multi-line. Substituted bare inside an `IF`, its continuation lines sit at column 0 and end
    the block, so guards and branch bodies read wrong. Use `textwrap.indent` in the function body.
  - **`WAIT for` means a user prompt, nothing else.** B10/B11 count it. A subagent wait uses other
    words ("Wait for the report"). Every `WAIT for` has a `resume at Step N` marker; a Step 11
    conflict prompt's marker reads `resume at Step 11` within three lines of its `WAIT for`.
  - **Inline re-engagement at every site:** Step 6 (`explore`), 7, 9, 10, 11 (`revise`), 8
    (`draft`). At each, the step text holds the fresh invocation for that mode. On Claude Code it
    also holds `ARCHITECT_MODE = "<mode>"`, then `resume_architect` under a guard naming
    `ARCHITECT_AGENT_ID`, then the fresh fallback, then `ARCHITECT_AGENT_ID = …`. Step 5 holds the
    fresh `explore` and never `SendMessage`. A generation-time helper that returns the block for a
    mode satisfies this.
  - **Per-step report handling.** Each of Steps 5-11 has an `IF <X>DECISION == "failed"` block whose
    own indented lines hold `EXIT` and the report's `detail`. Every `phase_mode:` value rendered is
    one of `explore`, `draft`, `revise`, `review` or `ARCHITECT_MODE`.
  - **Names the tests read.** The spec's `REVIEW_DECISION`, `REVIEW_ROUND`, `REPAIR_ROUNDS`,
    `ARCHITECT_MODE`, `ARCHITECT_AGENT_ID`, `BP_AVAILABLE`, `RETURN_TO`, `UNRESOLVED_CHECKS`,
    `IMPLEMENTATION_PLAN_PATH`, `PHASE_FILE_PATH` and `WRITTEN_PATHS`; `MAX_ACTIVE_BP_WORKERS = 3`
    (kept from today) for `synthesis-only`; and one name this document did not give,
    **`MAX_ACTIVE_WEB_RESEARCH_WORKERS = 1`**, for the serial `web-research` bound (F17).
  - **Step 9.** `refine` and `user_input` each get their own `REVIEW_DECISION` branch holding
    `REPAIR_ROUNDS < 2`, the increment, a route to Step 9 and, with `UNRESOLVED_CHECKS`, one to
    Step 10. An `ELSE` at the chain's indentation closes it with `EXIT`. Step 9 has no `WAIT for`.
    `REVIEW_ROUND += 1` precedes the critic invocation, and the `## Iteration` heading follows it.
  - **Step 4** routes through an `IF`/`ELIF` chain on the marker values. The re-open prompt sits under
    the `shape-settled` branch; `shape-amended` is written after it, then stored, then "Step 9".
  - **Disk mirror.** Every `mcp__respec-ai__store_document(` in Steps 3-12 is followed by its own
    `Write … PHASE_FILE_PATH` line before the next store in that step. One write after an
    `IF`/`ELSE` pair of stores fails. Step 10 writes before its first `WAIT for`.
  - **Decisions and marks.** Every `source=user` followed by a space sits below a `WAIT for` in its own
    step; that includes format examples, so none goes in the preamble. Steps 6 and 10 name both
    `[approved]` and `[declined]`. Step 7 names `[approved]` and has a guarded route to `RETURN_TO`,
    whose guard names `BP_AVAILABLE`, before its single `bp-pipeline` dispatch. Step 5 never names
    Step 7; Steps 6 and 10 name it after their first `WAIT for`. Step 6 holds a `[round … | question]`
    tag, Step 7 a `review` tag, Step 10 both. Step 3 holds `[round 0 | briefing]`.
  - **Sign-off order in Step 11:** an `EXIT` guarded by `IMPLEMENTATION_PLAN_PATH` (or
    `implementation.md`), then `respec-ai materialize-skeletons`, then a fail-closed `EXIT`, then
    the first later `shape-settled`, then a `PHASE_FILE_PATH` write, then a guarded `git commit`.
    `shape-settled` is named only in Steps 4, 11 and 12 (or the preamble). Any other line naming
    `git commit` or `git add` contains "never"; every real `git add` is `git add --` with the three
    path variables and no scratch file.
  - **Elsewhere.** Step 10 shows the UX Contract notice under an `IF` naming `#### UX Contract`.
    Step 6 ends the run with an `EXIT` under a guard naming `Option A`, after its store. Step 12
    uses the platform `create_phase_tool` before `Completion contract`, then names
    `code_command_invocation`. `initialize_refinement_loop(` appears once, in Step 3, which also
    sets `LOOP_ID`, `PROJECT_CONFIG_CONTEXT_MARKDOWN`, `REVIEW_ROUND = 0` and `REPAIR_ROUNDS = 0`.
  - **Not pinned, because only prose expresses them:** the malformed-report rule (only the `failed`
    branch is pinned), Claude Code's batch sizes, briefing pacing, the "re-read the disk whatever
    the choice" order, and SD and RP numbering. M2 and M6 cover them.

- **Landed (stage S4b, 2026-11-16).** `phase_command.py` was rewritten whole; every S4a test is
  green on all three TUIs. The new file, by section:
  - Module helpers: `_report_check` (`:6`), the per-step "wait for the report" text and the
    `IF REPORT_DECISION == "failed"` block, and `_architect_engagement` (`:21`), the inline
    re-engagement block for one mode (resume plus fresh fallback only where `resume_architect` is
    non-empty). The function body (`:39`) computes every generation-time branch: the resume
    rule, the Claude-Code-only `ARCHITECT_AGENT_ID` lines, the batch sizes from
    `selection_batch_limit`, and the guardrail-exception heading (opencode renders no guardrail).
  - Preamble: Overview (`:96`), the guardrail plus the phase-local exceptions (`bp-pipeline`, and
    the sanctioned disk writes, because the Claude Code guardrail forbids editing phase documents
    by any means its workflow does not list), Responsibilities (`:115`), Orchestration Pattern
    (`:129`), and `MANDATORY RELAY PROTOCOL` (`:146`): inputs, waiting, the four headings and the
    malformed rule, re-engagement, recording (SD IDs, decision sources, RP marks, round tags), the
    stage marker, the disk mirror and prompts.
  - Steps 1-2 (`:194`, `:324`) are the old text verbatim, except one bullet saying the guidance
    reaches the agents as the round-0 feedback entry. Step 3 (`:345`) has sub-steps 3.1 (loop),
    3.2 (config context and `respec-ai language-guidance`) and 3.3 (`IMPLEMENTATION_PLAN_PATH`,
    the `[round 0 | briefing]` store, the bp preflight, the counters). Step 4 `:438`, Step 5
    `:485`, Step 6 `:497` (6.1 present, 6.2 ODs, 6.3 RPs, 6.4 record and the Option A end, 6.5
    close), Step 7 `:688` (7.1 select, 7.2 dispatch, 7.3 record and route), Step 8 `:781`, Step 9
    `:798`, Step 10 `:871` (10.1 disk and present, 10.2 questions, 10.3 send back, 10.4 final
    prompt, 10.5 hand edit, 10.6 act), Step 11 `:1138` (11.1 settle, 11.2 sign-off prompt, 11.3
    plan check, 11.4 materialize, 11.5 settle and mirror, 11.6 commit), Step 12 `:1354` with the
    rewritten storage banner, and Phase Name Normalization (`:1416`), kept.
  - **Decided here; the spec did not say:**
    - `STAGE_MARKER` tracks the marker value in MCP (set in Step 4, Step 8 and Step 11.5); the hand
      edit restores it by variable, so Step 10 names no marker value.
    - `REPAIR_ROUNDS = 0` runs once at Step 10's entry. The only ways back to Step 9 from there
      are send-backs (Step 10 directly, Step 7's follow-up, Step 11), so this equals resetting on
      every send-back. `UNRESOLVED_CHECKS` is cleared at Step 9's top and initialized in Step 3,
      with `OPEN_CRITIC_QUESTIONS`, `DESIGN_CHANGE_SD_IDS` and `UNRESOLVED_DIRECTION`.
    - "Add your own" and the relayed question are options of a closing briefing prompt (Step
      6.5); the design review's final prompt gains "Ask the architect a question". Free-form text
      after such a choice is collected with `WAIT for the user's reply`, which carries its own
      `resume at Step` marker.
    - A user-added RP is confirmed before it runs when its tier is `synthesis-only` or
      `web-research` (the "tier rose" rule for a proposal with no prior tier).
    - Step 11's missing-file retry stores a `[round N | sign-off]` entry before its `revise`, so a
      fresh architect has new feedback to act on.
    - The materialization SDs, the `- Constraint:` line and `shape-settled` go in Step 11.5's one
      store. The merge-time unresolved-conflict SD is `source=materializer`; the three
      conflict-choice SDs are `source=user` with no `supersedes`.
    - Step 4's "show the handoff" goes to Step 12, whose platform store rewrites the same content.
    - Free-form direction the user gives during the briefing, beyond OD answers and RP marks, is
      stored as a `[round N | briefing]` entry before the relayed question and before Step 7, so
      the draft architect reads it.
  - **Open, not decided:** Step 10.2's mirror write replaces the disk file while the user is still
    answering questions, so a hand edit made before the final prompt is lost without notice; Step
    10.4's re-read comes too late to catch it. Step 10.1 tells the user to hand-edit only at the
    final prompt, which reduces the risk but enforces nothing. Check it in M2/M4, and close it
    (re-read the disk before 10.2's write) if it bites.
    - The old trailing argument lines after `{tools.initialize_loop}` and `{tools.store_document}`
      are gone; both fields are complete calls.
  - Probes: both "Already done?" commands print nothing on 2026-11-16.

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
- **Landed (stage S1, 2026-11-16).** `wait_sites()` returns `WaitSite(step, line, guards)`: `step` is
  the heading's number as written (`'1.3'`, or `None` before any step), `top_level_step` drops the
  sub-step part, `guards` lists the enclosing `IF`/`ELIF`/`ELSE` lines innermost first, and
  `guarded` is `bool(guards)`. The upward walk never leaves the WAIT's step. Guard headers match
  case-sensitively, so prose such as "If the user …" is not a guard. A multi-line substitution
  whose continuation lines start at column 0 ends the walk early and reports the WAIT unguarded
  (a false red, never a false green). Self-tests:
  `tests/unit/templates/test_template_contract_helper.py`. With `AskUserQuestion` recognized,
  `test_phase_workflow_gates.py::test_every_tool_the_phase_command_invokes_is_declared_in_its_allowed_tools`
  is red for Claude Code on all three platforms until work item 3 adds `_add_adapter_question_tool`.
- **Extended (stage S3, 2026-11-16).** S3 added these methods, each with a self-test in
  `test_template_contract_helper.py`:
  - `guards_for(marker)`: the enclosing conditions of every line naming a marker, found the way
    `wait_sites()` finds them.
  - `report_format()` and `report_section(heading)`: the fenced block that opens with
    `## For the user`.
  - `declared_inputs(heading)`: an agent's Invocation Contract bullets.
  - `mechanical_findings()` and `judgment_findings()`: findings by classification tag.
  - The module constant `REPORT_HEADINGS`.

- **Extended (stage S4a, 2026-11-16).** Index-based readers for the orchestrator tests, each with
  a self-test in `test_template_contract_helper.py` that was red against a stub:
  - `step_numbers()`, `preamble()` (text before the first step heading).
  - `step_section(n)`: like `step_body()` but spanning sub-steps (`'11'` covers `11.x`); `''` when
    absent.
  - `line_steps()`: the step of every line.
  - `enclosing_at(i)` / `guards_at(i)`: every enclosing header (loops included) or only
    `IF`/`ELIF`/`ELSE`, for one line.
  - `block_sites(block)`: where a multi-line field starts, ignoring indentation; `[]` for an empty
    block.
  - `decision_blocks(value)`: a `*DECISION* == "value"` header with only its own indented lines.

  `_enclosing_guards` is now `_enclosing_lines` filtered, with unchanged behavior.

**8. Existing tests, by fate.** This extends F36 with tests F36 did not list. Line numbers are each
test's `def` line unless the row says otherwise. Paths are under `tests/unit/templates/` unless a path
is given.

| Test | Fate |
|---|---|
| `test_phase_workflow_gates.py:19` | re-anchor (B18): once repair rounds are spent, the `user_input` branch routes to Step 10, which blocks and persists feedback. The branch body itself holds neither a `WAIT for` nor `store_user_feedback`, so the test follows the route. **New version (S4a):** `test_phase_cooperative_flow.py` `test_spent_repairs_reach_a_design_review_that_blocks_and_persists_the_answer`, with the Step 9 branch tests. Delete this one: against a spec-shaped command it still passes, but only because its branch body runs to the end of the template. **Landed (S4b):** deleted. |
| `test_phase_workflow_gates.py:31` | keep; extend the helper (work item 7) **Landed (S4b):** kept; it is now the file's only test, at `:20`. |
| `test_phase_workflow_gates.py:52` | remove **Landed (S4b):** deleted. |
| `test_phase_shape_act_gate.py:31`, `:43`, `:61` | remove **Landed (S4b):** the whole file is deleted. |
| `test_phase_shape_act_gate.py:71` | re-anchor on Step 10 (B25). **New version (S4a):** `test_phase_cooperative_flow.py` `test_a_hand_edit_is_validated_diffed_and_stored_with_the_marker_restored`. **Landed (S4b):** old test deleted with the file. |
| `test_phase_shape_act_gate.py:86`, `:100` | keep the pattern over every step that has a WAIT (B11). **New version (S4a):** `test_phase_cooperative_flow.py` `test_every_user_prompt_blocks_and_names_where_the_workflow_resumes` and `test_every_prompt_is_identically_shaped_on_every_tui`, over Steps 1-12. **Landed (S4b):** old tests deleted with the file. |
| `test_phase_skeleton_materialization_gate.py:33`, `:46`, `:59` | re-anchor: only Step 11's sign-off path reaches `materialize-skeletons` (B26). **New version (S4a):** `test_phase_cooperative_flow.py` `test_skeletons_materialize_only_at_sign_off` and `test_sign_off_checks_the_plan_materializes_marks_settled_mirrors_then_commits`. **Landed (S4b):** the whole file is deleted. |
| `test_phase_skeleton_materialization_gate.py:70`, `:81` | keep; anchor on Step 11. **New version (S4a):** `test_phase_cooperative_flow.py` `test_a_skeleton_conflict_prompt_appears_only_for_an_existing_file_and_resumes_sign_off` and `test_unmaterialized_and_unintrospectable_paths_are_shown_and_recorded`. The old `:70` asserts option labels (prompt wording, M6), and both old tests anchor on `step_body('11.5')`, so delete them. **Landed (S4b):** deleted with the file. |
| `test_phase_implementation_plan_gate.py:62`, `:71`, `:76` | keep |
| `test_phase_implementation_plan_gate.py:89` | re-anchor on the `draft` branch (B28). **Landed (S3)** as `test_draft_mode_carries_forward_every_referenced_constraint` |
| `test_phase_implementation_plan_gate.py:100` | remove **Landed (S4b):** deleted. |
| `test_agent_templates.py:440`, `:451`, `:462`, `:487`, `:559`, `:607` (`:438`, `:449`, `:460`, `:485`, `:557`, `:605` at `e79a794`) | remove. **Landed (S3)** |
| `test_agent_templates.py:474` (now `:486`) | rewrite: keep both path-validity markers; drop the API assertions. **Landed (S3):** both markers are asserted as `[mechanical]` findings |
| `test_agent_templates.py:540` (now `:496`, `test_template_grants_read_only_review_tools`) | drop the `get_loop_status` assertion. **Landed (S3):** it also asserts no document-write, `Write` or `Edit` grant (F14) |
| `test_agent_templates.py:547` (now `:507`) | rewrite for `review`, `review_round` and config context; guidance comes from feedback. **Landed (S3)** as `test_template_declares_exactly_the_inputs_the_orchestrator_passes` |
| `test_agent_templates.py:569` (now `:526`) | keep the parser-contract strings |
| `test_agent_templates.py:583`, `:838` (now `:627`, `:852`) | re-anchor (B19): `[judgment]` CQ, not a blocker condition. **Landed (S3)** |
| `test_agent_templates.py:596` (now `:539`, plus `:551` for the score) | rewrite (B4): `iteration` comes from `review_round`. **Landed (S3)** |
| `test_agent_templates.py:618` (now `:636`) | keep: Malformed Decision Entry is a mechanical blocker in `review`. Phase 3 deletes it later, when the check moves to `validate_document` (phase 3 work item 9). **Landed (S3):** also asserts the `[mechanical]` tag |
| `test_agent_templates.py:891` (now `:881`) | rewrite: guidance is read from the round-0 briefing feedback entry, and every guidance path is still read. **Landed (S3)** as `test_phase_architect_template_declares_exactly_the_inputs_the_orchestrator_passes` |
| `test_agent_templates.py:903`, `:956` | remove. **Landed (S3)** |
| `test_agent_templates.py:932` (now `:900`) | rewrite as the RP line shape (Technologies/Topics/Query). **Landed (S3)** as `test_phase_architect_proposes_research_as_ledger_lines_the_orchestrator_can_dispatch` |
| `test_agent_templates.py:383-437` (`TestCreatePhaseTemplate`, now `:382-461` with B30's two tests at `:437` and `:449`), `:661` (now `:677`), `:815` (now `:829`), `:872` (now `:862`) | keep |
| `test_agent_templates.py:612`, `:916`, `:925` (new, S3) | new: the critic's implementation.md checks are mechanical (work item 4, Add); tiering never passes a model option to the cache check (F17); the architect's only write grant is the scoped implementation.md path (open call 1) |
| `test_command_templates.py:353` (now `:359`) | rewrite (B16). **New version (S4a):** `test_phase_cooperative_flow.py` `test_research_dispatch_is_bounded_and_web_research_runs_one_at_a_time` and `test_only_research_that_bp_pipeline_reports_complete_becomes_a_read_line`. **Landed (S4b):** old test deleted. |
| `test_command_templates.py:481` (now `:487`) | keep (`REVIEW_DECISION == "completed"`). It also forbids the quoted literal `"complete"` (work item 6) **Landed (S4b):** kept, now `:470`. |
| `test_command_templates.py:516`, `:523` (now `:522`, `:529`) | rewrite (B14). `:529` (the assertion line: `:530` at `a64f0dc`, now `:536`) asserts `BP_PIPELINE_COMPLETE` is absent, which inverts. **New version (S4a):** `test_phase_cooperative_flow.py` `test_research_dispatch_names_bp_pipeline_exactly_and_nothing_unrunnable`, `test_research_is_dispatched_from_a_single_site_in_step_7` and `test_the_orchestrator_states_bp_pipeline_as_its_one_external_agent_before_any_step`; the grant half is S2's. **Landed (S4b):** both old tests deleted. |
| `test_command_templates.py:532`, `:570`, `:578`, `:678` (now `:538`, `:576`, `:584`, `:684`) | remove. `:678` asserts Step 16.5's policy banner **Landed (S4b):** deleted. |
| `test_command_templates.py:652` (now `:658`) | re-anchor: Step 12's platform store precedes its completion contract, and `Automatic Task Generation` stays absent. **New version (S4a):** `test_phase_cooperative_flow.py` `test_the_run_stores_to_the_platform_before_its_completion_contract_and_hands_off`. **Landed (S4b):** old test deleted. |
| `test_command_templates.py:812` (now `:818`) | keep only the main-critic half **Landed (S4b):** the post-synthesis assertions are gone, and the test is renamed `test_phase_template_fails_closed_when_critic_feedback_is_missing_or_stale` (`:700`). |
| `test_command_templates.py:339` (now `:345`) | keep. Do not name a variable `MAX_ACTIVE_WORKERS` (asserted at `:354-355`) **Landed (S4b):** kept, still `:345`. |
| `test_command_templates.py:1188` (now `:1217`) | rewrite: drop the `workflow_guidance_markdown: WORKFLOW_GUIDANCE_MARKDOWN` assertion, because invocations no longer carry it; keep the rest **Landed (S4b):** now `:1089`. |
| `test_command_templates.py:500`, `:508`, `:666`, `:1176`, `:1382`, `:1539` (now `:506`, `:514`, `:672`, `:1205`, `:1411`, `:1568`) | keep **Landed (S4b):** kept, now `:489`, `:497`, `:562`, `:1077`, `:1282`, `:1439`. |
| `tests/unit/platform_tests/test_tool_enums_and_validation.py:123` | rewrite to `Task(bp-pipeline)` |
| `tests/unit/platform_tests/test_tool_enums_and_validation.py:126-127` | remove **Landed (S4b):** removed (they were `:138-139` after stage S2). |
| `tests/unit/platform_tests/test_tui_adapters.py:904` (now `:969`, `test_codex_generated_templates_do_not_leak_hardcoded_slash_references`) | remove (Step 16.5 banner) **Landed (S4b):** deleted. |
| `tests/unit/platform_tests/test_tui_adapters.py:895` (now `:960`) | keep |
| `test_frontend_elicitation_phase10.py:101`, `:155`, `:175`, `:200`, `:219`, `:230`, `:238` | remove. **`:101` landed (S3).** S3's deletion moved the command tests: they are now `:147`, `:167`, `:192`, `:211`, `:222` and `:230` (S4b) **Landed (S4b):** every command test is deleted; the file keeps only the architect and critic tests. |
| `test_frontend_elicitation_phase10.py:128`, `:163`, `:184`, `:208` | re-anchor (B17, B12, B15, B13). **`:128` landed (S3)** as `:120`, `test_critic_never_blocks_or_questions_on_research`. The command ones are now `:155`, `:176` and `:200` (S4b). **New versions (S4a):** `test_phase_cooperative_flow.py` `test_research_is_dispatched_from_a_single_site_in_step_7` / `test_research_runs_only_for_proposals_the_user_approved` (B12), `test_the_run_checks_bp_availability_once_and_never_ends_on_its_failure` (B15), `test_every_research_answer_is_marked_so_a_declined_proposal_is_never_offered_again` (B13). **Landed (S4b):** the three old command tests are deleted. |
| `test_frontend_elicitation_phase10.py:58`–`:93`, `:114`, `:122`, `:140` (`:114`, `:122`, `:140` are now `:106`, `:114`, `:132`) | keep |
| `test_ux_contract.py:42` | remove. **Landed (S3)** |
| `test_ux_contract.py:91` (now `:79`) | re-anchor on Step 10 (B29). **New version (S4a):** `test_ux_contract.py` `test_ux_contract_is_surfaced_at_design_review_when_present`. **Landed (S4b):** old test deleted; the new one is `:78`. |
| `test_ux_contract.py:54`, `:64`, `:74`, `:81`, `:122` (now `:42`, `:52`, `:62`, `:69`, `:110`) | keep |
| `test_phase_design_layer.py:52` | re-anchor (B19). **Landed (S3)** as `test_critic_questions_abstractions_with_no_stated_axis_of_variation` |
| `test_phase_design_layer.py:26`, `:41`, `:63` | keep |
| `test_phase_section_references.py` | keep; re-point the import (work item 6) **Landed (S4b):** re-pointed to `phase_architect.technical_phase_template`. It stays green although that copy lost the six domain `additional_sections`. |
| `tests/unit/models/test_content_loss_detection.py` | keep; re-point the import at `:21` (work item 6) **Landed (S4b):** re-pointed. |
| `test_phase_runtime_language_config.py`, phase 1's B11 | re-anchor on `step_body('3')`. Keep the `respec-ai language-guidance` and `### Language Authoring Notes` assertions and the `ELSE` fallback. Narrow the "no `EXIT:`" assertion to the language-guidance block, because Step 3 also holds the loop link's fail-closed exits (today's Step 4.2, `phase_command.py:377`, `:393`). **New version (S4a):** `test_run_setup_gives_every_architect_route_language_notes_and_a_failed_lookup_never_stops_the_run`; delete the `step_body('4.5')` one. **Landed (S4b):** the `step_body('4.5')` test is deleted. |
| `test_phase_runtime_language_config.py`, phase 1's B12 | re-anchor on the briefing. The architect half stays: it contains `(verify: ask user` and names `no_preference`. Its `explore` branch raises the missing-verify-command OD with the three options above, and Step 6 ends the run on Option A. Delete the `step_body('12.6')` assertions with the step. **Architect half landed (S3):** the new `test_explore_raises_a_missing_verify_command_as_a_briefing_decision` (`:80`) pins the explore OD's Option A file, `[commands].test`, `no_preference` and the marker, and that it never points to the standards command. The Step 6 half is S4b's. **Step 6 half written (S4a):** `test_choosing_to_configure_a_verify_command_first_ends_the_run_after_recording_the_choice` (an `EXIT` under a guard naming `Option A`, after the Step 6 store). **Landed (S4b):** green with the rewrite. There were no `step_body('12.6')` assertions left to delete. |
| `tests/unit/utils/test_setting_configs.py:8` (new, S3) | new (work item 11): a stale `LOOP_PHASE_*_SOFT_CAP` value never breaks `LoopConfig` |
| `test_phase_cooperative_flow.py:144` (new, S3) | new: every input the orchestrator's four phase-agent invocations pass is one the agent declares, and vice versa (README "Agents and modes") |
| `tests/conftest.py:164-191` (`phase_threshold=90`) | keep. A score of 100 clears 90, and 0 never does |

**Soft-cap call sites** lose their keyword arguments (**landed, S3**):
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
    requires (now `:743`, `test_all_templates_have_required_sections`)
- **Landed (stage S3, 2026-11-16).** The gate now sits at `create_phase.py:101-118`, between
  STEP 1 (`:95`) and STEP 2 (`:120`), and says "before any storage". Its VIOLATION line names MCP
  storage too. *Phase Context Issues*, *Phase Validation Failures* and *Quality Assurance* are
  deleted. The invocation contract, the `FROZEN_DISCARD_WARNING` check (now `:124-128`) and the
  output protocol are unchanged. Tests: `TestCreatePhaseTemplate::test_create_phase_validates_the_phase_before_it_stores_anything`
  (B30), plus `test_create_phase_still_reports_a_frozen_overview_discard_to_both_roadmap_paths`,
  which was green on day one and was proven by deleting the warning check temporarily.

**10. The respec-code gate** (open call 2).
- **The change.** `src/platform/templates/commands/code_command.py:221` (*"IF SHAPE_GATE not in
  ["shape-settled", "shape-amended"]:"*) accepts only `shape-settled`. Update the DIAGNOSTIC at
  `src/platform/templates/commands/code_command.py:223` to match.
  - **Landed (stage S1, 2026-11-16):** `:221` now reads *"IF SHAPE_GATE != "shape-settled":"*, and
    `:223` names only `shape-settled`.
- **The test.** Add one beside
  `test_coding_workflow_refuses_to_start_when_shape_was_never_settled`
  (`tests/unit/templates/test_task_removal_workflow.py:64`; landed as
  `test_coding_workflow_refuses_a_reopened_phase_until_it_is_signed_off_again`, `:70`). Its gate condition names
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
- **Landed (stage S3, 2026-11-16).** Both fields are gone from `LoopConfig`
  (`src/utils/setting_configs.py:29-37` at `e79a794`), from `PhaseCriticAgentTools` and from the
  critic factory. `template_generator.py` now calls `create_phase_critic_agent_tools(tui_adapter)`
  and no longer imports `loop_config`. The critic template has no length tiers.
  - **Corrects the probe above:** before removal, a stale value outside the old range did raise.
    `LOOP_PHASE_LENGTH_SOFT_CAP=1` failed `ge=30_000` with a `ValidationError` when `LoopConfig()`
    was built. After removal, any value is ignored.
  - Test: `tests/unit/utils/test_setting_configs.py`. It was red before removal, for that reason.

**12. Tool descriptions the architect reads** (F31). Generalize the `store_current_analysis` and
`get_previous_analysis` docstrings (`src/mcp/tools/feedback_tools_unified.py:961-973`,
`src/mcp/tools/feedback_tools_unified.py:988-998`, after the stage S1 rewrite). They describe only the analyst workflow; make
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
  - **Added by stage S3.** The agents now behave as follows, and README does not say so yet:
    - **"Decision entry (canonical)", IDs.** README says CQ IDs "exist only in its report". The
      critic also stores each CQ ID in its feedback's `### Key Issues`
      (`- [judgment] [<Marker>] CQ-NNN: …`), because that stored feedback is its only memory
      between rounds. A new CQ takes the next number above every `CQ-NNN` in the previous reviews
      and the SDs (work item 4, Landed).
    - **"Subagent report format", `## Status` `persisted`.** `nothing` means the phase document
      and `implementation.md` did not change. The architect stores its notes on every engagement
      and does not list them, so README's example *"phase document updated; analysis stored"*
      changes to name design writes only (work item 5, Landed).
    - **"Research recording".** Draft and revise may add two things to the ledger: nested
      `- Applied:` lines, and at most one new unmarked RP line. That line is the single research
      proposal that Step 10 asks (work item 5, Landed).
- `docs/WORKFLOWS.md`: rewrite "How it works" under `/respec-phase` (`docs/WORKFLOWS.md:223-228`) for
  the three touchpoints, and the `/respec-phase` threshold row (`docs/WORKFLOWS.md:589`).
- **Landed (stage S4b, 2026-11-16).**
  - `docs/TEMPLATE_AUDIT.md`: a 2026-11-16 contract note after the 2026-08-24 one, superseding the
    2026-04-22 synthesis contract.
  - decisions.md: the Write grant's status reads "decided in phase 2" with both dates, and M7 is
    recorded as **not yet run** (it needs a live Claude Code spawn). The respec-code exception
    records its landing and test, the stage-marker decision's consequence paragraph now describes
    the closed window, and the bp decision notes TEMPLATE_AUDIT is updated.
  - deferred-issues.md: phase 1's "Step 3's settled route skips Step 4.5" row is deleted. The
    Linear/GitHub draft-persistence gap and F39 are logged. **The DesignSync item is not logged:**
    it needs a live spawn of the architect on a UI phase to confirm, which this stage could not do.
  - README: the "Pending amendments" paragraph says phase 2's landed; "Agents and modes" records the
    grant as decided, with the M7 caveat; "Subagent report format" gives `persisted` its meaning;
    "Decision entry", IDs, records CQ IDs stored in `### Key Issues`; "Settled decision entry" has
    all five amendments (the `materializer` source, fields per source, `unresolved-checks`, SD
    numbering, the retired `user-menu` and `user-override`); "Relay protocol" step 5 decides
    newness by position; "Research recording" lists the two ledger additions; "bp invocation per TUI"
    carries the verified preflight result, the external-render method and the worker names;
    "Cross-cutting risks" 6 adds the M7 caveat. Stale `phase_command.py` anchors in those sections
    are gone.
  - `docs/WORKFLOWS.md`: "How it works" describes the three stops, the critic review and the
    resume rules; the threshold row explains the 100/0 score; the walkthrough's score line, a stale
    tip and the UX Contract note's "shape mode … Phase 3 gate" wording are updated.

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

**Status on 2026-11-16 (stage S5).** Met: B1-B30 were each observed red first (or proven by a
temporary break or negative self-test, per the stage notes above); every red test is in work item
8's table; both "Already done?" probes print nothing and phase 1's probe passes; `uv run pytest`
is green with the live Postgres on :5433 (2264 passed, 1 skipped); `regenerate --force --tui all`
completes in a scratch project with HOME isolated and writes valid artifacts for all three TUIs;
both open calls are recorded in decisions.md; M3 is confirmed; M5 and M6 are done as scripts
(evidence in [phase-2-manual-checks.md](phase-2-manual-checks.md)). Evidence gaps: B28's draft test
failed with a `ValueError` naming the missing draft branch, not an assertion, and B25's tools test
failed on a bare `assert False`. Not done: the live checks M1 (not blocking, opencode is unused),
M2, M4 and M7, with step-by-step instructions in `phase-2-manual-checks.md`. M5's live half is
step M2.9.

- [x] B1–B30 observed failing first, then pass. B2, B3, B5 and B7 pass on day one; B2's
      temporary-break check and the B5 and B7 negative self-tests are what prove them.
- [x] Every red test that no B-row covers has been added to work item 8's table with its fate.
- [x] Both "Already done?" probes print nothing, and phase 1's prerequisite probe still passes.
- [x] `uv run pytest` is green. The postgres half of B1 and B2 has been run against a live database,
      not skipped.
- [x] `uv run respec-ai regenerate --force --tui all` completes in a scratch project, after
      `respec-ai models opencode` and `respec-ai models codex`. The written artifacts are valid for
      all three TUIs.
- [x] The open calls are recorded: decisions.md for the Write grant; decisions.md, or
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
- [x] **M3.** The 4-question batch limit has been confirmed against the live `AskUserQuestion` tool
      definition, and `selection_batch_limit` corrected if it differs.
- [ ] **M4, resume.** Check three things:
  - Interrupt during design review and re-run: the run resumes at Step 9 → Step 10 from the on-disk
    draft.
  - Interrupt after the briefing and before the draft, then re-run: no settled decision is asked
    again, and no `[declined]` proposal is offered again.
  - Re-open a signed-off phase: the marker reads `shape-amended`, then `shape-settled` after the
    next sign-off.
- [x] **M5, the frozen reader.** On the signed-off output:
  - `extract_steps` (`tests/support/plan_extraction.py`) finds every step of the produced
    `implementation.md`
  - the Checklist items carry `(Step N)` and `(verify: …)`
  - respec-code passes its shape gate and its implementation-plan read
    (`src/platform/templates/commands/code_command.py:219-241`)
- [x] **M6.** Reword every prompt in the new flow arbitrarily, and the suite stays green. If it goes
      red, those tests pin phrasing rather than behavior; fix the tests.
- [ ] **M7, the write scope on Claude Code.** Spawn the regenerated architect and have it write a
      file outside `.respec-ai/plans/*/phases/*/implementation.md`. Record whether the
      `Write(<glob>)` entry in its `tools` list resolves at all, and whether it refuses that write.
      Do not assume either answer (open call 1). Record the result in decisions.md.
