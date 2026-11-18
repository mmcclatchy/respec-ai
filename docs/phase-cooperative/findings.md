# Verified findings

Each finding below was confirmed by opening the referenced file, by running a probe against the
code, or by reading the cited external document, not by inference from names. Line numbers reflect
the codebase on 2026-11-13 (branch `phase-cooperative`, baseline `uv run pytest`: 1671 passed, 84
skipped). If a reference no longer matches, re-verify it before acting on it, and correct this file.

Paths that start with `~/` are **outside this repository**. They belong to the best-practices-rag
installation on the design machine and are an external dependency, not code respec-ai owns.

These are the facts underneath [README.md](README.md) and the phase documents. Phase documents
cite them as **F1**–**F40** rather than restating the evidence.

## Correctness bugs in the current workflow

**F1 — Step 16 "Accept current quality and proceed" cannot exit the loop.**
`phase_command.py:1260` offers *"Accept current quality and proceed"*. `:1269` records
*"User accepted current phase quality"*, and then `:1273` runs *"Return to Step 14 (phase-architect
will incorporate user guidance)"* for every option, accept included. The only other exit,
`ELIF LOOP_DECISION == "MAX_ITERATIONS"` at `:1275`, tests a status that does not exist: `LoopStatus`
has only `initialized`, `in_progress`, `completed`, `user_input` and `refine`
(`src/utils/enums.py:25-30`). The branches at `phase_command.py:1217` and `phase_command.py:1221`
also compare against `"REFINE"` and `"USER_INPUT"`, while the enum values are lowercase.
**Implication:** after "Accept", the only way out is the critic scoring `completed`. The user's
decision to stop is turned into one more refinement round. Step 16 is removed in phase 2; do not
port its menu.

**F2 — The first shape send-back is probably lost: the architect reads feedback through a tool it
does not hold, behind a counter that never counts user feedback.**
Verified facts:
- The architect's STEP 0 says *"CALL {tools.get_loop_status}"* (`phase_architect.py:240`), but
  `PhaseArchitectAgentTools.respec_ai_tools` grants only `GET_DOCUMENT`, `UPDATE_DOCUMENT`,
  `LINK_LOOP_TO_DOCUMENT` and `GET_FEEDBACK` (`src/platform/models/phase.py:188-193`). On Claude
  Code the call is outside the agent's `tools` list.
- Feedback is fetched only *"IF LOOP_STATUS.iteration >= 1"* (`phase_architect.py:246`). The only
  defined fallback is *"Set: PREVIOUS_FEEDBACK = None (First iteration — no prior feedback
  exists)"* (`phase_architect.py:251-253`).
- The loop counter counts critic feedback only: `self.iteration = len(self.feedback_history)`
  (`src/utils/loop_state.py:182`), and it starts at 1 (`src/utils/loop_state.py:44`,
  `migrations/001_initial_schema.sql:16`). A user send-back at Step 8 (`phase_command.py:685-689`)
  happens before the critic's first run at Step 10, so the counter cannot tell "the user sent this
  back" from "nothing has happened yet".
- The command's own narration says the architect fetches feedback *"(if iteration > 1)"*
  (`phase_command.py:438`, `phase_command.py:1120`), which contradicts the agent's `>= 1`.
- STEP 2 frames feedback as critic output only: *"Analyze specific issues identified by critic"*
  (`phase_architect.py:452-459`).

Not reproduced at runtime. If the `get_loop_status` call works, `iteration >= 1` is always true and
feedback is fetched; if it fails, the architect lands in the "no prior feedback" branch.
**Implication:** whichever path the model takes, the fix is the same: delete the gate. The architect
always calls `get_feedback` and needs no loop status at all (decisions.md, "The architect always
fetches feedback").

**F3 — `shape-amended` means two incompatible things.**
The architect writes it for a draft in progress: *"set `### Shape Gate` to `shape-proposed` (or
`shape-amended` if this iteration follows a critic-requested or user-requested re-shape rather than
a first pass)"* (`phase_architect.py:543-545`). Every reader treats it as **settled**:
- `phase_command.py:348` routes it straight to the detail act, skipping the gate.
- `phase_architect.py:561` and `phase_architect.py:618` treat it as settled.
- `phase_critic.py:1078` skips the whole shape blocker lane.
- `code_command.py:221` lets coding start.

Step 12 then overwrites it with `shape-settled` (`phase_command.py:979`), so it has no distinct
settled meaning either.
**Implication:** a re-shape interrupted after one architect pass leaves an unapproved draft marked
as settled. A re-run then skips the gate, and respec-code accepts the draft.

**F4 — The stage marker is overwritten by every agent write.**
`Phase.shape_gate` defaults to `ShapeGate.UNSHAPED` (`src/models/phase.py:88`) and is parsed from
`## Metadata > ### Shape Gate` (`src/models/phase.py:42`). Both `update_phase` implementations carry
over only the frozen fields and bump `iteration`/`version`
(`src/utils/state_manager/postgres.py:584-601`, `src/utils/state_manager/in_memory.py:396-412`).
Everything else, `shape_gate` included, comes from the incoming markdown. The architect writes with
`update_document` (`src/platform/models/phase.py:191`); the command writes with `store_document`
(`src/platform/models/phase.py:19`).
**Implication:** "only the orchestrator writes the stage marker" cannot be enforced by prompt text.
An architect that omits or rewrites `### Shape Gate` changes it, and an omitted heading silently
resets it to `unshaped`. A storage rule is needed (decisions.md, "The stage marker is
orchestrator-owned").

**F5 — `implementation.md` is generated and approved before the detail act runs.**
Step 12.5 invokes the architect in `implementation-plan` mode and Step 12.6 writes the file on
approval, then *"Proceed to Step 13"*, the detail act (`phase_command.py:987-1058`). That mode is
told *"These are the only inputs — do NOT read or reference Architecture, Technology Stack, or other
detail-act sections"* (`phase_architect.py:565-567`).
**Implication:** the build order is fixed before the content it orders exists, and the detail act
can later contradict a plan the user has already approved. In the new flow, `implementation.md` is
drafted with the design and reviewed in the same touchpoint.

## The critic's rubric conflicts with the design it reviews

**F6 — The critic penalizes the file paths and test IDs the design layer requires.**
- `phase_critic.py:335` says *"The Phase is NOT: … Specific file names or directory structures for
  the target project"*.
- `phase_critic.py:1259` deducts *"Specific file names/paths: -2 points (e.g., "Create
  `src/neo4j_client.py`")"*, and `phase_critic.py:1262` deducts *"Test case IDs: -1 point"*.
- The same template's BINDING SCOPE requires module paths and public seams
  (`phase_critic.py:1098-1109`).
- The rubric is stale in several places. It still writes for a task-planner and a "Task document",
  both removed by phase-refactor phase 6 (`phase_critic.py:322`, `:329`, `:332`, `:337`, `:1030`,
  `:1057`, `:1257`; the architect repeats it at `phase_architect.py:1295`).

**Implication:** the critic cannot score the brief this effort produces, which is built on paths,
seams and IDs (SD-n, T-n, step n), without deducting for exactly those. The rubric goes in phase 2;
it is not patched.

**F7 — The rubric rewards bloat and penalizes length in the same pass, behind a 90-point gate.**
Domain-specific sections earn *"3 points per section (up to 5 sections = 15 points)"* plus 15 for
substance (`phase_critic.py:1204-1213`). The length penalty runs to -50 (`phase_critic.py:73-79`).
The Two-Lane contract says *"Do NOT deduct score for procedural/format violations"*
(`phase_critic.py:339-349`), yet the over-detailing and length penalties are both deductions.
Completion requires the score to reach `phase_threshold`, 90 by default
(`src/utils/setting_configs.py:17`).
**Implication:** the score measures conformance to an FSDD template rather than whether an agent
can build from the document. "No numeric rubric" replaces it (decisions.md).

**F8 — API-coverage blockers make research mandatory, which breaks the cost invariant.**
- The critic raises *"[API Research Coverage Missing - BLOCKING]"* for any detected external API
  without a `Read:`/`Synthesize:` entry (`phase_critic.py:743-746`, `phase_critic.py:1044-1046`).
- The architect is told every inventoried API *"MUST have official-doc research coverage"*
  (`phase_architect.py:323`).
- Step 16.5 adds automatically generated API prompts: *"SYNTHESIS_QUEUE = deduplicated list of
  normalized SYNTHESIZE_PROMPTS + AUTO_API_PROMPTS"* (`phase_command.py:1385-1404`).
- The post-synthesis critic can send the workflow back to Step 14 on the same blockers
  (`phase_command.py:1519-1532`).

**Implication:** a user who declines all research still cannot pass the critic. That contradicts
the cost invariant already stated at `phase_command.py:462` (*"a user who declines here pays
exactly what they pay today — zero additional `bp` invocations"*). All four mechanisms go in
phase 2.

**F9 — "No numeric rubric" still needs a score, and every critic run in a loop replaces the last.**
`CriticFeedback.overall_score` is a required `int` (`src/models/feedback.py:34`), and parsing fails
fast without it (`src/models/feedback.py:127-131`). The loop completes only when
*"self.current_score >= self.loop_type.threshold and not latest_blockers"*
(`src/utils/loop_state.py:88`). Critic feedback is written with `upsert_feedback`
(`src/mcp/tools/feedback_tools_unified.py:82`, `:438`), keyed by `(critic_agent, iteration)`
(`src/utils/loop_state.py:189-198`). The critic computes its iteration as
*"SHAPE_ITERATION = SHAPE_LOOP_STATUS.iteration + 1"* (`phase_critic.py:300-301`; post-synthesis
the same at `phase_critic.py:397-399`), but the loop counter reads 1 both before and after the first
feedback (F2). Probe: three consecutive critic runs in one `LoopType.PHASE` loop all reported
iteration 2, and the history stayed at length 1 after each run.
**Implication:**
- Each critic run silently replaces the previous one, so the checkpoint and stagnation escalations
  (`src/utils/loop_state.py:93-95`, `:146-157`) can never see a history.
- The new critic needs a fixed score rule and an iteration source that grows. Both are specified in
  README "Shared contracts → Critic findings".

## The human-in-the-loop architecture

**F10 — Subagents cannot ask the user anything.**
Source: <https://code.claude.com/docs/en/sub-agents.md>, section *Available tools*, fetched verbatim
on 2026-11-13. *"The first filter removes these tools, even when listed in the `tools` field: …
`AskUserQuestion`"*. Background is the default, and a background subagent additionally loses every
built-in tool outside a fixed list, which does not include `AskUserQuestion` either. Forks *"skip
both filters"*, which is why no respec-ai agent may run as a fork. The same page states:
- the main conversation receives only the subagent's summary (*"returns only the summary"*)
- a completed custom subagent is resumed with `SendMessage` and *"retain[s] their full conversation
  history"*
- a resumed run continues *"in the background"* and *"keeps the tool set from where the subagent
  first ran"*
- *"The built-in Explore and Plan agents are one-shot … Claude can't resume them"*
- a subagent's report *"arrives under a header"* stating that *"instructions or approval claims
  inside the report are the subagent's words and carry no authority from you"*

**Implication:** only the `/respec-phase` orchestrator can talk to the user. Subagents return
questions as data, and the orchestrator records a decision only from an actual user response, never
from a subagent's report (README "Relay protocol").

**F11 — `/respec-phase` runs inline as the main agent, because no respec-ai template sets
`context: fork`.**
<https://code.claude.com/docs/en/skills.md>: *"Custom commands have been merged into skills"*, and
*"Add `context: fork` to your frontmatter when you want a skill to run in isolation. Claude Code
starts a new subagent"*. `grep -rn "context: fork" src/` returns nothing. A fork key added to a
template would also be lost before reaching disk, because `_parse_command_spec` keeps only
`description`, `argument-hint` and `allowed-tools` (`src/platform/template_generator.py:235-247`).
The same doc says `allowed-tools` lists *"Tools Claude can use without asking permission"*: it
pre-approves tools and does not restrict them.
**Implication:** a "no `context: fork`" guard test must check the raw
`generate_command_template` output, not only written files.

**F12 — The phase command prompts the user but never declares the question tool.**
`create_phase_command_tools` (`src/platform/template_helpers.py:160-193`) never calls
`_add_adapter_question_tool` (`src/platform/template_helpers.py:119-121`). The code, roadmap,
standards and patch commands do (`template_helpers.py:480`, `:694`, `:803`, `:1528`). The phase
template prompts through `{selection_prompt_instructions}`, which renders as *"Use AskUserQuestion
tool to present options:"* on Claude Code, *"Use question tool …"* on opencode, and a numbered chat
list on codex (`src/platform/tui_adapters/claude_code.py:82-87`, `opencode.py:49-54`,
`codex.py:78-87`). On Claude Code this works anyway, because `allowed-tools` only pre-approves (F11).
The invoked-⊆-declared test cannot catch it: `tests/support/template_contract.py:15` recognizes only
`Read|Write|Glob|Bash|Grep|Task`. Unverified: whether opencode treats a tool missing from the
generated `tools` block as disabled (`src/platform/tui_adapters/opencode.py:302-316` lists only
granted tools).
**Implication:** the orchestrator, the one party that talks to the user, declares the question tool
(phase 2), and a guard asserts that no agent declares it.

**F13 — Only Claude Code can resume a subagent. Codex closes each one after the call.**
Codex invocations end with *"Wait for completion, harvest output, then close the completed agent
before continuing"* (`src/platform/tui_adapters/codex.py:245-262`). `SendMessage` is not a
`BuiltInToolCapability` (`src/platform/tool_enums.py:51-94`). Every adapter must map every
capability explicitly (`src/platform/tui_adapters/base.py:49-60`), and a test enforces it
(`tests/unit/platform_tests/test_tui_adapters.py:88-92`). There is precedent for a subagent that
returns user decisions as data: the roadmap orchestrator states *"You have NO channel to the
user"* and *"The caller owns every user decision"*
(`src/platform/templates/agents/roadmap_orchestrator.py:34-38`).
**Implication:** MCP rehydration is the portable core. `SendMessage` resume is a Claude Code
extension behind a new capability that maps to `None` on opencode and codex.

**F14 — Least-privilege tool grants are enforced only on Claude Code.**
Codex agent TOMLs carry `name`, `description`, `model`, `sandbox_mode = "workspace-write"` and
instructions, with no tool list (`src/platform/tui_adapters/codex.py:377-387`). opencode's per-agent
`tools` block skips `mcp__*` and `Task(...)` entries and strips path parameters to the base name
(`src/platform/tui_adapters/opencode.py:302-316`).
**Implication:** "the critic and finalizer are read-only" and any path-scoped write guarantee must
also be stated in the prompt. On opencode and codex they are prompt-enforced only.

## Research (`bp`)

**F15 — `Task(bp)` names nothing that can run, on any of the three TUIs.**
- **The grant:** `builder.add_builtin_tool(BuiltInToolCapability.TASK, 'bp')`
  (`src/platform/template_helpers.py:172`).
- **The preflight is a tautology:** *"IF "Task(bp)" is NOT present in allowed tools OR runtime
  cannot invoke bp"* (`phase_command.py:78`). It checks only the grant string.
- **The call text is hardcoded, not adapter-rendered:** *"Task(bp):"* (`phase_command.py:92-93`).
- **Claude Code:** `bp` is a command, which is now a skill (`~/.claude/commands/bp.md:1-8`, *"Invoke
  as `/bp <query>`"*). The agent is `bp-pipeline` (`~/.claude/agents/bp-pipeline.md:1-7`), and no
  agent named `bp` exists.
- **opencode:** the command's `Task(...)` entries become `{'*': 'deny', …}` plus one allow per name
  (`src/platform/tui_adapters/opencode.py:274`, `:282-283`). `bp` is only a command there, and
  `bp-pipeline` is a `"hidden": true` subagent (`~/.config/opencode/opencode.json:5-27`), so
  research is denied today.
- **Codex:** *"Allowed tools: …"* is plain prose (`src/platform/tui_adapters/codex.py:365`). `bp` is
  a skill invoked as `$bp` (`~/.codex/skills/bp/SKILL.md:1-8`), and `bp-pipeline` is a custom agent
  (`~/.codex/agents/bp-pipeline.toml:1-4`). The adapter's invocation helper would also rename it to
  `respec-bp-pipeline-agent` (`src/platform/tui_adapters/codex.py:369-375`).

**Implication:** the research flow has never had a working invocation. The phase 2 mechanism is in
README "bp invocation per TUI".

**F16 — `bp-pipeline` is a published caller contract, and it names respec-phase.**
`~/.config/best-practices-rag/references/bp-pipeline-interface.md:3`: *"Intended for use by `/bp`,
`/bpr`, and respec-phase Step 7.5 parallel dispatch."* `bp-pipeline-interface.md:5`: *"Claude Code
and OpenCode dispatch `bp-pipeline` with `Task(bp-pipeline)`. Codex dispatches it as a custom agent
from `.codex/agents/bp-pipeline.toml`."* `bp.md` itself delegates the same way
(`~/.claude/commands/bp.md:137-157`), and bp's design runs Steps 1–4 in the caller: *"Steps 1-4 run
in the main session and produce scalar parameters"* (`~/.claude/commands/bp.md:23`). This
contradicts the recorded contract *"`respec-phase` invokes `bp` as the public entrypoint"*
(`docs/TEMPLATE_AUDIT.md:5-10`, commit `be39e52`).
**Implication:** direct `bp-pipeline` dispatch is the supported route. The caller must compute bp's
Steps 1–4 inputs itself: `TECH_VERSIONS_JSON`, `CUTOFF_DATE`, `PRIMARY_QUERY`, and `OUTPUT_FILE`
from `generate-slug` (`bp-pipeline-interface.md:11-30`, `~/.claude/commands/bp.md:54-131`).

**F17 — bp's cost tiers, side effects, and two upstream defects.**
- **Tiers** (`~/.claude/commands/bp.md:74-131`):
  - a cache hit skips everything
  - *"Full coverage"* goes straight to synthesis
  - *"Partial gap"* researches the uncovered technologies
  - *"Full gap"* runs full research
- **Both gap tiers write to the global Neo4j KB**, which is served to every project on the machine
  (`docs/frontend-refactor/decisions.md:647-651`).
- **`query-kb` is read-only but not side-effect free:** it writes `/tmp/bp_kb_bodies.txt` with
  `--include-bodies`, and reports `neo4j_unavailable` when the KB is down
  (`~/.local/share/uv/tools/best-practices-rag/lib/python3.14/site-packages/best_practices_rag/cli.py:887`,
  `cli.py:908`).
- **Upstream defect, cache check:** `check-file-cache` reports a miss with `"reason":
  "model_mismatch"` whenever `--model` differs from the model that wrote the file
  (`cli.py:140-146`). bp tells the caller to pass its own model (`~/.claude/commands/bp.md:79-81`).
- **Upstream defect, parallel runs:** `bp-pipeline` writes Exa results to fixed paths such as
  `/tmp/bp_exa_primary.md` (`~/.claude/agents/bp-pipeline.md:93-121`), while the interface doc
  claims *"parallel dispatch safe"* (`bp-pipeline-interface.md:136`).

**Implication:**
- Call `check-file-cache` without `--model`.
- Run gap-tier (web research) items one at a time; synthesis-only items may run in parallel.
- Label proposals with the tier the user actually pays for.

**F18 — The Claude Code orchestrator guardrail forbids any non-respec agent.**
*"Invoke ONLY the respec-* agents explicitly named in this workflow"*
(`src/platform/tui_adapters/claude_code.py:30-34`).
**Implication:** dispatching `bp-pipeline` from the orchestrator requires a named exception in the
guardrail. Without one, a strict model refuses or improvises. Nothing in the test suite would catch
it.

**F19 — Step 5.5 already has the right approval semantics; the rest of the research flow does not.**
Step 5.5 defaults to *"None — proceed … Costs nothing — no bp invocation"*. It marks declined gaps
`[declined]` and never re-offers them, and degrades rather than terminating when bp is unavailable
(`phase_command.py:462-469`, `phase_command.py:476-520`). But when `query-kb` fails, the architect
is told to *"Add all topics to "External Research Needed" using the structured `Synthesize:`
format"* (`phase_architect.py:1344-1348`; also `phase_architect.py:345-348`). Step 16.5 then
synthesizes every `Synthesize:` line plus automatic API prompts (F8).
**Implication:** keep the Step 5.5 semantics and its tests' intent. Remove the "synthesize
everything" fallback; KB unavailability is reported in the briefing instead.

## Language bias

**F20 — The shared Skeleton Index / Test List grammar is language-biased, and both phase templates
import it.**
`src/platform/templates/phase_contract_grammar.py:10-34` uses `.py`/`.tsx` paths, *"JSX.Element"*,
*"Python: a non-builtin type MUST be a fully-qualified dotted path"*, *"TypeScript: write the type
exactly as declared"*, and *"pytest node-id style for Python"*. It is imported by
`phase_architect.py:8` and `phase_command.py:6`.
**Implication:** neutralizing it here fixes both templates at once (phase 1).

**F21 — The architect template carries language bias well beyond the grammar.**
- **A generation-time loop:** `for language in ('python', 'typescript'):` (`phase_architect.py:113-121`).
- **Verify commands:**
  - `pytest`/`npm test` in the example (`phase_architect.py:107-109`)
  - `pytest …` and `npm test` named in the rule that forbids copying examples
    (`phase_architect.py:603-604`)
- **Named stacks:**
  - *"a Python+React project"* (`phase_architect.py:200`, `:818`)
  - *"for example Python, TypeScript, Node.js, browser, AWS Lambda"* (`phase_architect.py:318`)
  - LlamaIndex/Neo4j/Pydantic examples (`phase_architect.py:776-783`)
  - fenced `python` and `typescript` signature examples (`phase_architect.py:785-793`)
  - `.py`/`.tsx`/`.spec.ts` path examples (`phase_architect.py:802-809`)
  - per-language signature rules (`phase_architect.py:815-850`)
  - *"React, HTMX"* (`phase_architect.py:883`)
  - Pydantic, *"Query 'Python errors'"* and `Settings` class examples (`phase_architect.py:893-902`)
  - SQL and GraphQL schema blocks (`phase_architect.py:1133-1159`)
  - `--tech "react,graphql"` (`phase_architect.py:1321`)
- **Paradigm bias:**
  - *"internal … class"* (`phase_architect.py:472-479`)
  - *"JSX/styling/hooks"* (`phase_architect.py:540-542`)
- **A broken find-and-replace:** *"Web src/APIs"* (`phase_architect.py:1031`, `:1143`, `:1161`,
  `:1173`; `phase_critic.py:1218`).

**Implication:** no list stays complete, which is why the denylist guard test is the authority
(decisions.md, "Zero language bias").

**F22 — The command and critic carry bias too, and the critic gets no project config at all.**
The command has `(examples: Python, TypeScript, Node.js, browser, AWS Lambda)`
(`phase_command.py:1332`) and React/GraphQL/PostgreSQL research examples
(`phase_command.py:1654-1659`). The critic has *"(interface, base class, protocol) … use a concrete
class, not an interface"* (`phase_critic.py:1121-1129`) and a pytest-shaped `::test_...` example
(`phase_critic.py:1136`). The critic's invocations pass no `project_config_context_markdown`
(`src/platform/template_helpers.py:240-272`); only the architect's three invocations do
(`template_helpers.py:211`, `:224`, `:237`).
**Implication:** critic checks must be purely structural, or they need the project config passed
in.

**F23 — Existing tests require the bias, and one requires it in a frozen template.**
`tests/unit/templates/test_agent_templates.py:848-857` asserts `'```typescript' in template`, and
`test_agent_templates.py:859-870` asserts that the Python and TypeScript naming conventions are
rendered into the architect. `test_agent_templates.py:362-371` asserts that the coder names a
TypeScript sentinel; the coder belongs to frozen respec-code.
**Implication:** phase 1 inverts the first two in the same change that adds the denylist guard. The
guard is scoped to phase-workflow templates, or it is permanently red.

**F24 — The Skeleton Index grammar must stay a uniform meta-notation; a native signature crashes
the CLI.**
Every Skeleton Index line, for any language, must match
`^(?:Owner\.)?member\((params)\)\s*->\s*(return)$` (`src/utils/skeleton_types.py:6-9`), or it raises
*"Unparseable Skeleton Index signature"* (`src/utils/skeleton_types.py:76-78`). This applies even to
paths with no materializer (`src/utils/skeleton_generator.py:58-66`, `:77-95`).
`materialize-skeletons` catches only `SkeletonPathEscapesProjectError` and `SyntaxError`
(`src/cli/commands/materialize_skeletons.py:85-89`). `check-conformance` catches only
`ConformanceParseError` (`src/cli/commands/check_conformance.py:29-30`), while
`src/utils/design_conformance.py:245` calls the parser unwrapped. Probe:
`Server.Start(ctx context.Context) -> error` on a `.go` path parses. `func (s *Server) Start(ctx
context.Context) error` raises `ValueError`.
**Implication:** the plan's placeholder *"`<path> :: <signature in that file's language>`"* would
crash materialization on Go or Elixir. The neutral placeholder keeps the meta-notation
`<Owner>.<member>(<params>) -> <Result>`; only the type and parameter text are in the file's
language. Phase 1 also turns the uncaught `ValueError` into a structured error.

**F25 — Language guidance arrives at runtime, with gaps.**
- **What reaches the agents:** Step 4.5 loads `stack.toml` and the non-universal standards TOMLs into
  `PROJECT_CONFIG_CONTEXT_MARKDOWN` (`phase_command.py:402-425`). Only the architect receives it
  (F22).
- **Gap: detection.** Tooling detection knows five build files (`src/platform/tooling_defaults.py:48-54`).
- **Gap: test commands.** Languages without a canonical command get `no_preference` as their test
  command (`src/platform/standards_config.py:226-234`): c, clojure, dart, objective-c, powershell
  and terraform, confirmed by probe. `_is_incomplete_value('no_preference')` returns `False`
  (`src/platform/standards_config.py:331-333`), so validation passes.
- **Gap: materializers.** Only python and typescript have one
  (`src/utils/materializers/__init__.py:9-12`).
- **Dead code.** `test_path_convention()` is declared on the protocol
  (`src/utils/materializers/base.py:25`) but has no callers.
- **Python test names.** The Python test renderer writes each `::` test name as a function name,
  unchecked (`src/utils/materializers/python_materializer.py:86-90`).

**Implication:**
- The verify-command fallback treats empty, `TODO` and `no_preference` all as missing.
- Per-language authoring notes come from the materializer at runtime, only for the project's
  languages.

## Persistence and parsing

**F26 — New prose under new H2 headings round-trips with no migration.**
Unmapped H2s are captured raw into `additional_sections` (`src/models/base.py:407-429`). Postgres
stores them as one JSONB column (`migrations/001_initial_schema.sql:89`), read back by
`_row_to_phase` (`src/utils/state_manager/postgres.py:45-50`). The in-memory backend stores the
`Phase` object itself. Probe: `## Grounding` containing `### Exemplar Files` round-trips as
`{'Grounding': '### Exemplar Files\n- path/a'}`.
**Implication:** the plan's "no migration" claim holds for **H2** sections, provided the traps in
F27 and F28 are avoided.

**F27 — Four parser traps for new H2 sections. None is reported by `validate_document`.**
1. **Substring matching.** `_extract_content_from_raw_markdown` takes the first `##` line
   *containing* the name (`src/models/base.py:66-71`). Probe: a new `## Design` captured
   `### Architecture` from `## System Design`, and `## Decisions` captured
   `### Settled Design Decisions`. The new sections' own text was lost.
2. **Truncation.** Extraction stops at the next `##` line or any bare `---`, and is not
   fence-aware (`src/models/base.py:77-85`). Probe: `## Guardrails` holding `Rule one / --- / Rule
   two` stored only `Rule one`.
3. **No detection.** `find_content_loss` checks only `HEADER_FIELD_MAPPING` paths and orphan H3s
   (`src/models/base.py:211-221`). The probe above returned `LOSS: []`.
4. **Ordering.** `build_markdown` emits `additional_sections` after every typed section, just before
   Metadata (`src/models/phase.py:172-177`). Postgres `jsonb` does not preserve key order, so
   section order differs between backends.

**Implication:**
- New H2 names must not contain, or be contained in, any other H2 name. `Design` and `Decisions`
  from the plan's table are unusable as written.
- Brief prose must not use bare `---` or fenced `##` lines.
- Phase 3's checks cover additional sections.
- Template order must not matter.

`tests/unit/templates/test_phase_section_references.py:92-101` already guards template H2 names
against shadowing.

**F28 — A new H3 under a mapped H2 is silently dropped.**
An H3 under a mapped H2 that the mapping does not list is an orphan (`src/models/base.py:183-199`):
reported by `find_content_loss`, dropped by `parse_markdown`. Overview's four fields are also frozen
once they hold real content (`src/utils/state_manager/base.py:17-29`).
**Implication:** "Out of scope" cannot be a new `### Out of Scope` under `## Overview`, and an agent
cannot append it to frozen Scope. It needs its own H2 or a home inside another new H2.

**F29 — `validate_document` today is a content-loss check with a single, user-facing consumer.**
`DocumentToolsInterface.validate` runs only `find_content_loss` and returns `COMPLETED` or
`USER_INPUT` (`src/mcp/tools/base.py:16-22`); the tool wrapper only dispatches by type
(`src/mcp/tools/document_tools.py:38-46`). It never parses, so a title that `store` would reject
still validates. Its only consumer is the user-facing *"Content Would Be Lost"* menu
(`phase_command.py:702-748`). `implementation.md` is not a `DocumentType`; there are only `plan`,
`roadmap` and `phase` (`src/models/enums.py:134-137`). The MCP container is started with no project
volume (`src/cli/docker/manager.py:196-206`).
**Implication:**
- Structural findings must be reported apart from content loss, or mechanical issues reach the user.
- Checking `implementation.md` needs a new input path.
- "Cited file exists" cannot run server-side under the shipped deployment.

**F30 — `Phase.version` is a write counter, and a roadmap re-store wipes everything.**
Every write to an existing row sets `iteration` and `version` to existing+1
(`src/utils/state_manager/postgres.py:594-601`, `src/utils/state_manager/in_memory.py:406-412`). A
roadmap store first runs `mark_phases_inactive`, then re-stores each phase from the roadmap
(`src/mcp/tools/roadmap_tools.py:28-35`), replacing design content and `additional_sections` in MCP.
The on-disk `phase.md` survives.
**Implication:** no new gate may compare versions, because every orchestrator write bumps them. On a
re-run, the disk copy is the source the orchestrator syncs from.

**F31 — `get_feedback` returns all user feedback, untagged. `store_current_analysis` is one slot.**
`count` limits only critic entries. Every `store_user_feedback` entry is appended as *"## User Input
{i}"*, in insertion order, after the critic block (`src/mcp/tools/feedback_tools_unified.py:183-196`).
The MCP signature requires `count` (`src/mcp/tools/feedback_tools_unified.py:915`).
`store_current_analysis` writes one row per loop (`migrations/023_add_unified_feedback_tables.sql:11-15`,
`loop_id … PRIMARY KEY`), and its docstring describes only the analyst workflow
(`src/mcp/tools/feedback_tools_unified.py:974-982`).
**Implication:**
- User feedback entries carry a round tag.
- Each write of exploration notes is a full replacement, not a delta.
- The tool descriptions agents read are generalized when the architect starts using them.

## What downstream readers depend on (the frozen contracts)

**F32 — Downstream workflows read the parsed document, not the file.**
respec-code and respec-patch sync `phase.md` from disk with `store_document`
(`src/platform/adapters/markdown.py:14-17`, `src/platform/models/code.py:86-87`), which parses it
(`src/mcp/tools/phase_tools.py:173`, `:198`). Agents then read `build_markdown()` output
(`src/mcp/tools/phase_tools.py:58`, `:73`).
**Implication:** for downstream readers, the parser decides what survives, not the prompt
wording (F27, F28).

**F33 — respec-code reads `implementation.md` raw, with three hard contracts.**
- **Location:** the file must sit at `{PHASE_DIR}/implementation.md`, or respec-code fails closed
  (`code_command.py:230-241`).
- **Step headings:** steps are found only as *"each "#### Step N:" section in
  IMPLEMENTATION_PLAN_MARKDOWN's "## Build Order > ### Steps""* (`code_command.py:291`). With no
  steps found, dispatch silently becomes backend-only (`code_command.py:518`).
- **Checklist gate:** the coder must *"Read implementation.md's `## Checklist` section completely"*
  before any work (`src/platform/templates/agents/coder_contracts.py:134-146`). Items have the form
  `- [ ] … (Step N) (verify: …)` (`phase_architect.py:106-109`).

**Implication:** extra H2s in `implementation.md` are harmless, but all three must survive phase 4.
The plan's "Start here / Steps / Exit criteria" layout drops two of them.

**F34 — respec-code and respec-patch also depend on these `phase.md` contracts.**
- **Gate:** *"IF SHAPE_GATE not in ["shape-settled", "shape-amended"]"* fails closed
  (`code_command.py:219-228`).
- **Success Criteria:** the spec-alignment reviewer blocks when *"a Phase objective, scope item, or
  deliverable is absent from Phase success criteria"*
  (`src/platform/templates/agents/spec_alignment_reviewer.py:140`).
- **Constraint lines:** `- Constraint:` lines (each with a backticked path) under `### Implementation Plan References`
  are *"HARD CONSTRAINTS"* (`coder_contracts.py:159-170`).
- **Research:** read from *"Phase's "### Research Requirements" section"* (`coder_contracts.py:234`).
- **Conformance write-back:** replaces `### Skeleton Index` and appends to
  `### Settled Design Decisions` (`code_command.py:1158-1169`).
- **Review weighting:** reads `#### UX Contract` in `design_shape_additional`
  (`src/utils/review_weighting.py:18`, `:63-65`).
- **Test List grammar:** `` - `path::name` `` (`src/utils/skeleton_generator.py:99-108`).
- **respec-patch:** reads the *"Overview section … first 30 lines"* (`patch_command.py:227`) and
  owns `## Evolution Log` (`patch_command.py:1109-1112`).
- **Pre-existing bug:** respec-code writes *"Status: "IMPLEMENTED""* (`code_command.py:1176`), which
  is not a `PhaseStatus` (`src/models/enums.py:30-36`).

**Implication:** see README "Shared contracts → Section naming and frozen-reader compatibility".

**F35 — No Python parses decision entries, and two OD shapes are in use.**
`SD-` appears in Python only in `design_conformance.py` writers (`src/utils/design_conformance.py:287`,
`:318`). The orchestrator parses ODs by prompt as *"OD-NNN | title | Option A: name — tradeoff |
Option B: name — tradeoff | Recommended: X — why"* (`phase_command.py:545-546`). The architect emits
a nested form with indented `Option A:` / `Option B:` / `Recommended:` lines
(`phase_architect.py:519-524`). The critic blocks an OD missing any of title, Option A, Option B or
Recommended (`phase_critic.py:290-297`). Today's SD writers: `phase_command.py:571-581`
(`source=user-menu`), `phase_command.py:751-752` (`source=user-edit`), `phase_command.py:834-835`
(`source=user-override`).
**Implication:** the decision format is free to define, as long as one canonical form is chosen
(README "Shared contracts → Subagent report format").

## Tests that pin behavior this effort removes

**F36 — Inventory of pinned behavior, by fate.** Line numbers point at each test's `def` line, except
the two `test_tool_enums_and_validation.py` entries, which point at the asserting lines. Files are
under `tests/unit/templates/` unless a path is given. The phase documents refine these fates in their
own test tables (phase 2 work item 8, phase 3 work item 9). Where a phase table is more specific, it
wins.

| Test | Pins | Fate |
|---|---|---|
| `test_phase_workflow_gates.py:52` `test_shape_act_and_detail_act_use_separate_loops…` | two acts, two loops, `phase_mode` counts | remove (phase 2) |
| `test_phase_workflow_gates.py:19` `test_workflow_waits_for_the_user_when_the_loop_requests_input` | user_input branch blocks and persists | keep the behavior, re-anchor on the new relay branch |
| `test_phase_workflow_gates.py:31` `test_every_tool_the_phase_command_invokes_is_declared…` | invoked ⊆ declared | keep unchanged; extend the helper's tool pattern (F12) |
| `test_phase_shape_act_gate.py:31`, `:43`, `:61` | joint gate, version re-approval, override | remove |
| `test_phase_shape_act_gate.py:71` | hand edit validated, diffed, stored | keep, re-anchor on design review |
| `test_phase_shape_act_gate.py:86`, `:100` | WAIT/resume parity per step, TUI parity | keep the pattern, new step list |
| `test_phase_skeleton_materialization_gate.py:33`, `:46`, `:59` | materialize only after the joint gate | keep as "only after sign-off", re-anchor |
| `test_phase_skeleton_materialization_gate.py:70`, `:81` | conflict reconciliation, unmaterialized display | keep, re-anchor on sign-off |
| `test_phase_implementation_plan_gate.py:100` | Step 12.6 gate | remove |
| `test_phase_implementation_plan_gate.py:89` | constraint carry-forward in `implementation-plan` mode | keep the obligation, move it to draft/finalize |
| `test_phase_implementation_plan_gate.py:62`, `:71` | `#### Step N:` and DR format via the example constant | keep; the neutralized example must keep three steps and a DR line |
| `test_agent_templates.py:440`, `:451`, `:462` | shape mode, verbatim preservation, skeleton opt-in | remove |
| `test_agent_templates.py:487` | API detection and post-synthesis mode | remove |
| `test_agent_templates.py:559` | two-lane numeric score | remove (F7) |
| `test_agent_templates.py:569` | critic storage contract | keep (F9) |
| `test_agent_templates.py:583` | Under-Surfaced Decision and Non-Divergent Options as shape-mode blockers | re-anchor in `review` mode as `[judgment]` CQs, not blockers (phase 2 B19) |
| `test_agent_templates.py:607` | detail skip | remove |
| `test_agent_templates.py:618` | OD format (Malformed Decision Entry) | keep in `review` mode through phase 2; phase 3 deletes it when the check moves to `validate_document` (phase 3 B4) |
| `test_agent_templates.py:848`, `:859` | TypeScript grammar, Python/TS naming | invert (phase 1, F23) |
| `test_agent_templates.py:872` | config-derived verify commands | keep |
| `test_agent_templates.py:903`, `:956` | official-API research protocol, API synth topics | remove |
| `test_agent_templates.py:932` | structured Technologies/Topics/Query | keep as the research proposal shape |
| `test_agent_templates.py:661` | imperative-language audit (architect, critic) | keep; add the finalizer |
| `test_command_templates.py:516`, `:523` | `Task(bp)` grant and preflight string | rewrite for `bp-pipeline` (F15) |
| `test_command_templates.py:532`, `:570`, `:578` | automatic API queue, Step 16 → 16.5, post-synthesis critic | remove |
| `test_command_templates.py:812` | fail-closed main and post-synthesis | split: keep the main-critic half |
| `test_command_templates.py:353` | bounded bp workers, output validation | keep; add the gap-tier cap (F17) |
| `test_command_templates.py:481` | every listed command contains `"completed"` | keep a `completed` branch, or drop PHASE from the tuple |
| `test_command_templates.py:652`, `:666` | storage before completion, completion contract | keep the behavior, re-anchor the titles |
| `test_command_templates.py:1176`, `:1539` | imperative audit, adapter-owned selection prompt | keep |
| `test_frontend_elicitation_phase10.py:155`–`:219` | Step 5.5 research gate | keep zero-bp-on-decline (`:163`), degrade-when-unavailable (`:184`) and `[declined]` idempotence (`:208`), re-anchored on the briefing; remove the rest |
| `test_frontend_elicitation_phase10.py:200`, `:230`, `:238` | Step 16.5 synthesis | remove |
| `test_ux_contract.py:42` | Design Shape preserved verbatim in the detail act | remove |
| `test_ux_contract.py:91` | UX Contract surfaced at Step 8 | keep, re-anchor on design review |
| `tests/unit/platform_tests/test_tool_enums_and_validation.py:123`, `:126` | `Task(bp)` in tools, `invoke_phase_critic_post_synthesis` | rewrite / remove |
| `tests/conftest.py:164-176`, autouse `stable_loop_config` (`phase_threshold=90`) | the 90-point loop | revisit when the score policy changes (F9) |

Every `create_phase_critic_agent_tools(adapter, phase_length_soft_cap=…, phase_shape_soft_cap=…)`
call breaks mechanically when the length tiers are cut, for example
`tests/unit/templates/test_phase_design_layer.py:57`.

**F37 — Agent rendering is not hermetic.**
`OpenCodeAdapter` raises *"OpenCode reasoning model not configured"* without model config
(`src/platform/tui_adapters/opencode.py:106-111`). A bare `CodexAdapter()` resolves models from the
user's global config. Precedent for hermetic construction:
`tests/unit/templates/test_coder_split_phase9.py:32-46` (`OpenCodeAdapter(model_overrides=…)`).
**Implication:** agent-level guard tests pass `model_overrides` to both adapters.
`regenerate --tui all` needs `respec-ai models opencode|codex` configured first.

## Smaller defects found while mapping

**F38 — `mcp_tools_reference` always renders empty.**
Its list includes `'store_plan'` and `'get_plan_markdown'` (`src/platform/models/phase.py:111-121`),
which are not registered MCP tools; a bare `except Exception: return ''` swallows the lookup error
(`src/platform/models/phase.py:123-127`).
**Implication:** delete the field in the phase 2 rewrite.

**F39 — Codex renders the subagent guardrail twice in the phase command.**
The template embeds `{tools.tui_adapter.subagent_invocation_guardrail}` (`phase_command.py:139`),
and the codex adapter prepends it again whenever a command delegates
(`src/platform/tui_adapters/codex.py:117-120`). Cosmetic.

**F40 — Text under a mapped H2 before its first H3 is dropped on parse and not reported.**
A narrative line placed directly under `## Design Shape`, before `### Module Layout`, is absent
from the parsed `Phase`, and `Phase.find_content_loss` reported nothing. Probed on 2026-11-13, and
again on 2026-11-17 after phase 3's validation override landed, with the same result. The same holds
for every mapped H2 (`Overview`, `System Design`, `Design Shape`, `Design Decisions`,
`Implementation`, `Additional Details`). Text before the first H3 of an *additional* section is kept.
**Implication:** the design narrative lives in `#### Design Narrative`, and phase 4 teaches
`find_content_loss` to report this case (spec Scope 5, B17).
