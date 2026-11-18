# respec-ai — Cooperative phase design that produces an agent-ready brief

Working design documents for reworking `/respec-phase` into a design conversation between the user
and the LLM, whose output is an implementation brief that any agentic harness can build from.

Breaking changes are in scope. The project has no users and no backward-compatibility requirement,
so each phase replaces code in place; nothing is built alongside an old mode only to be deleted
later.

---

## Start here — fresh session

If you have just picked this up with no prior context, this section is your entry point.

**1. Read in this order.** All paths are relative to the repository root.

1. `docs/phase-cooperative/README.md`: this file. It covers the problem, the principles, the phase
   index and the **Shared contracts**, which every phase document must follow.
2. `docs/phase-refactor/testing.md`: **required.** It explains how to test in this codebase. This is
   not obvious, because respec-ai generates prompts and prompts resist ordinary behavioral testing.
   It is not duplicated here: same codebase, same conventions.
3. `docs/phase-cooperative/findings.md`: skim it now, and come back whenever a phase document
   asserts something surprising about the codebase. Phase documents cite findings as **F1**–**F40**
   rather than restating the evidence.
4. `docs/phase-cooperative/decisions.md`: read it before questioning any design choice. Three
   decisions of the previous effort and one recorded contract are revised there, and the reasoning
   is recorded.
5. The phase document you are implementing.

Also read `CLAUDE.md` at the repository root. Its coding standards are mandatory and override
general defaults.

`docs/phase-refactor/` (interface-first design, the human gate, skeletons) and
`docs/frontend-refactor/` (the language seam, the UX Contract, user-elected research) are the
**previous** efforts. Both are complete. This effort rebuilds the workflow they produced, so their
decision logs explain much of what is kept.

**2. Find out which phase to work on.** Each probe was run on 2026-11-13 and reported "not done".

```bash
# Phase 1 done?  → both hold: the guard test passes (exit 0) AND the grep prints nothing
uv run pytest -q tests/unit/templates/test_phase_language_neutrality.py
grep -n -i -E "python|typescript|\.tsx|jsx" src/platform/templates/phase_contract_grammar.py
# Phase 2 done?  → both print nothing (grep -L lists each file still missing the report contract;
#                  the second grep prints each removed mechanism still present)
grep -L "## Decisions needed" src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/templates/commands/phase_command.py
grep -n -E 'post_synthesis|AUTO_API_PROMPTS|phase_mode == "shape"|Task\(bp\)|--no-verify' src/platform/templates/commands/phase_command.py src/platform/templates/agents/phase_architect.py src/platform/templates/agents/phase_critic.py src/platform/template_helpers.py src/platform/models/phase.py
# Phase 3 done?  → output means done (the MCP checks AND their wiring into the command)
grep -q "async def validate(" src/mcp/tools/phase_tools.py && grep -n "structural_findings" src/platform/templates/commands/phase_command.py
# Phase 4 done?  → output means done (the finalizer AND the Claude Code handoff, which lands last)
test -f src/platform/templates/agents/phase_finalizer.py && grep -n "def brief_handoff_extension" src/platform/tui_adapters/claude_code.py
```

Each probe is the phase document's own "Already done?" check. A phase is done only when every line
of its probe agrees, so a partly landed phase never reads as done. On 2026-11-13 the phase 2 residue
grep printed 35 lines, and the phase 3 and phase 4 lines printed nothing.

Work the lowest-numbered incomplete phase, respecting the dependencies in the phase table below.

**3. Line numbers may be stale.** Every `file:line` reference in these documents was verified at
design time, but the codebase moves. Before acting on a reference, open it and confirm it says what
the document claims. If it does not, search for the symbol instead, and correct the reference in
the document as part of your change. These documents are meant to be maintained, not archived.
Paths that start with `~/` are outside the repository; they belong to the best-practices-rag
installation.

**4. Working agreement.**

- Test-first, always. Each phase document opens with *Behaviors to pin*. Write those tests, run them,
  confirm they fail for the right reason, and only then implement.
- Tests pin behavior, not implementation. See `docs/phase-refactor/testing.md` for the
  discriminating question.
- Do not start a phase whose predecessor is incomplete.
- Do not expand a phase's scope. Each has an explicit *Out of scope* section; if something seems
  missing, it is probably assigned to a later phase on purpose. Log out-of-scope defects in
  [deferred-issues.md](deferred-issues.md).
- Commit per the `CLAUDE.md` convention: conventional-commit style, no attribution lines.

**5. If something in a phase document is wrong or ambiguous,** fix the document as part of the work.
A stale design document is worse than none, and the next session inherits whatever you leave.

---

## The problem

The previous effort added a human in the loop on top of an automated architect↔critic loop. That
first pass was never exercised end to end, and it grew to:
- two acts, each with its own loop and critic mode
- about ten kinds of human stop
- a 1,833-line orchestrator (`src/platform/templates/commands/phase_command.py`)
- a 90-point scoring loop that runs after the human is done

It also has correctness bugs:
- **F1:** "Accept current quality" in Step 16 cannot exit.
- **F2:** the first send-back is probably lost, because the architect reads feedback through a tool
  it does not hold.
- **F3:** `shape-amended` is overloaded. It means both "re-shape in progress" and "settled".
- **F4:** every agent write overwrites the stage marker.
- **F5:** `implementation.md` is approved before the detail act writes the content it orders.

Three structural problems sit underneath the bugs:
- **The critic grades the document against a template, not against whether an agent can build from
  it.** It penalizes the file paths and test IDs the design layer requires (F6, F7), and makes
  research mandatory (F8).
- **The workflow is language-biased throughout.** The shared grammar, the architect and the critic
  name Python, TypeScript, pytest, npm, React and JSX, and render a hardcoded
  `('python', 'typescript')` loop (F20–F22).
- **Research never had a working invocation.** `Task(bp)` names nothing that can run on any of the
  three TUIs (F15).

The strategic picture has also shifted. respec-code is likely outdated: modern harnesses already
orchestrate subagents, task lists and verification. respec-ai's lasting value is upstream, in the
plan and the phase design. So the phase output should no longer be respec-code's private input
contract.

## The outcome

The phase workflow becomes a design conversation with **at most three human touchpoints** on the
happy path:

1. **Briefing.** The architect explores first: the plan and its constraints, the existing code, and
   local KB lookups. The user then hears what exists to build on, an approach sketch, and the top
   decisions with recommendations. They approve, deny or edit proposed research.
2. **Design review.** The user sees the design and build order that the critic has already
   reviewed. Mechanical issues are already fixed. The critic's judgment calls arrive as questions.
   The user says what to change, or edits `phase.md` directly, until they are happy.
3. **Sign-off.** The user answers any queued questions. Then the workflow writes `phase.md` and
   `implementation.md`, materializes skeletons (create-only), offers a commit, and shows a handoff
   for the user's harness.

The output is an **agent-ready brief**:
- `phase.md` holds what to build and why: grounding, design, decisions with rejected alternatives,
  delegation bounds, behaviors and guardrails.
- `implementation.md` holds how, and in what order: steps written as self-contained delegation
  briefs, with dependencies, test IDs and verify commands taken from project config.

Every item carries an ID, so a harness can build subagent briefs by citing IDs instead of copying
prose.

## Guiding principles

**The user shapes; the LLM drafts.** The user's input arrives as decisions and reactions in
conversation, not as edits to a document a parser can break. Hand edits remain possible, and they
are validated and reconciled.

**Bring a point of view.** Never ask for a decision without showing the sketch it applies to, the
options with their trade-offs, and a recommendation.

**Ground the design before asking anything.** The plan constraints, the existing codebase and any
research are read before the first question.

**Checks stay invisible unless a human is needed.** Structural problems and mechanical critic
findings are fixed before the user sees anything. Only judgment calls reach the user.

**Only the orchestrator talks to the user.** This is not a style choice. Subagents cannot ask the
user anything (F10). They return questions as data.

**Write for a cold-start implementer.** A fresh agent with only the brief and the repository must
be able to execute any step without guessing.

**Zero language bias.** No workflow text names a language, framework, test runner or file
extension. Language specifics arrive at runtime, from the target project's config, and only for
that project's languages. The MCP server and CLI being written in Python is irrelevant.

## Phases

Four phases. Each one leaves the system working end to end. The new user experience lands in
phase 2. Each phase has its own document, linked in the first column.

| # | Phase | Delivers | Depends on |
|---|---|---|---|
| [1](phase-1-language-neutral.md) | Language-neutral foundation | Neutral grammar placeholders that keep the meta-notation (F24). Runtime language guidance: standards TOMLs plus materializer authoring notes, injected only for the project's languages. The verify-command fallback (empty, `TODO` or `no_preference` means ask; F25). Malformed Skeleton Index lines reported cleanly instead of as tracebacks. The denylist guard test, with the biased tests inverted (F23). | — |
| [2](phase-2-cooperative-flow.md) | Cooperative flow | The architect's `explore`/`draft`/`revise` modes and the critic's `review` mode, all returning the fixed report. The rewritten orchestrator implementing the relay protocol: briefing, then research approval, then approved `bp-pipeline` runs only, then draft, critic, review loop, sign-off and materialize. The orchestrator-owned stage marker with its storage rule (F4). The respec-code gate edit. Guard tests. Removes the two acts, the FSDD rubric, Step 16, automatic API research and the post-synthesis critic. Trims `create_phase`. | 1 |
| [3](phase-3-structural-checks.md) | Structural checks in `validate_document` | Pure, unit-tested structural checks behind a `PhaseTools.validate` override, reported separately from content loss (F29), covering `additional_sections` (F27). Wired into the draft step, so mechanical issues are fixed before the user sees them. The MCP-side checks can be built in parallel with phase 2; the wiring needs phase 2. | 1 (MCP side), 2 (wiring) |
| [4](phase-4-agent-ready-brief.md) | Agent-ready brief format | The fixed-H2 brief sections. Step delegation briefs in `implementation.md`. The `respec-phase-finalizer` agent and the critic's cold-start check. The structural checks for the new fields. The TUI-tiered handoff. Stops generating the old detail fields, folding their content into the new sections, while keeping the frozen-reader contracts. | 2, 3 |

**Why this order.**
- **Phase 1 is small and makes everything written afterwards neutral by construction.** The phase 2
  rewrite then cannot reintroduce bias without turning the guard red.
- **Phase 2 is the user-visible change.** It runs on the current sections, so it can ship and be used
  before the brief format changes.
- **Phase 3 comes before phase 4.** Phase 4's new fields need somewhere to be checked, and its
  finalizer needs checks to repair against.

## Per-phase exit criteria

Every phase is done when all of the following hold:

- Every behavior in its *Behaviors to pin* list has a test that was observed failing first.
- `uv run pytest` is green. The baseline on 2026-11-13 was 1671 passed, 84 skipped.
- `uv run respec-ai regenerate --force --tui all` completes with no per-TUI failure in a scratch
  project, and the written artifacts are valid for claude-code, opencode and codex.
  - `--force` is required because regeneration is version-gated (`src/cli/commands/regenerate.py:117-120`).
  - `--tui all` is required because `auto` regenerates only TUIs that already have artifacts
    (`:203-221`).
  - opencode and codex must have model tiers configured first (`respec-ai models opencode`,
    `respec-ai models codex`), or rendering raises (F37).
- The phase's guard tests pass on all three TUIs. Each guard also has a negative self-test that feeds
  it a synthetic violating template, so it is proven to fire. Several guards would otherwise pass on
  day one with no red step.
- From phase 2 on, a real phase runs end to end on a scratch project, with at most three happy-path
  touchpoints counted.
- The manual checks in the phase document pass. Some properties, design quality and brief usability
  above all, are not machine-checkable and must be judged by a person.

The effort as a whole is verified at the end of phase 4:
- Run real phases on scratch projects in two languages respec-ai has no special support for (for
  example Go and Elixir), plus one that has a materializer.
- Hand each resulting brief to a fresh Claude Code session, and confirm it implements the steps with
  no clarifying guesses.

Testing method: `docs/phase-refactor/testing.md` ("assert the contract, not the prose"). Render
helpers parametrized over all three adapters are the pattern there. Agent-level tests must build
`CodexAdapter` and `OpenCodeAdapter` with `model_overrides` to stay hermetic (F37).

---

## Shared contracts

Every phase document follows these contracts. A phase that needs to change one changes it **here
first**, in the same commit, and says so.

**Pending amendments.** Each phase document lists the changes it makes to this section: phase 1
item 10, phase 2 work item 13, phase 3 work item 10 and phase 4 Scope 0. They land here in the same
commit as the code that needs them, so until a phase lands, this section still shows the earlier
text. Where this section and the phase document you are implementing disagree about that phase's
own work, the phase document describes the target. Phase 2's amendments (its work item 13) landed
here on 2026-11-16. Phase 3's amendments (its work item 10) landed here on
2026-11-16. Phase 4's amendments (its Scope 0) landed here on 2026-11-17.

### Agents and modes

| Agent | `phase_mode` values | Persists | Granted, beyond today |
|---|---|---|---|
| `respec-phase-architect` | `explore`, `draft`, `revise` | `phase.md` content via `update_document`; exploration notes via `store_current_analysis`; the `implementation.md` draft via a `Write` grant scoped to `.respec-ai/plans/*/phases/*/implementation.md` | `store_current_analysis`, `get_previous_analysis` (today only plan-workflow agents hold them: `src/platform/models/plan.py:19-20`); `validate_document` (phase 3: the self-check on the stored phase) |
| `respec-phase-critic` | `review` | critic feedback via the existing store tool | `validate_document` (phase 3: relays `implementation_findings` and reads `paths_to_verify`; still read-only, with no Write, Edit, `update_document` or `store_document`; on opencode and codex this is also stated in the prompt, F14) |
| `respec-phase-finalizer` (phase 4) | — (one job; its report says `mode: finalize`) | `phase.md` via `update_document`; `implementation.md` via the same scoped `Write`, declared in `PhaseFinalizerAgentTools.builtin_tools` as the architect's is in `PhaseArchitectAgentTools.builtin_tools` | `get_previous_analysis` (it reads the architect's exploration notes and writes none, so it gets no `store_current_analysis`: least privilege, F14); `validate_document` (its self-check, the way phase 3 has the architect check itself) |

- **Inputs.** Agents are invoked with their mode, IDs (`loop_id`, `plan_name`, `phase_name`) and the
  runtime config context (`project_config_context_markdown`). Never pass conversation text, the
  briefing, or document bodies.
  - **The critic** also receives `review_round` (see "Critic findings") and, on every invocation,
    `review_target`: `design` or `brief` (phase 4). Phase 2's `invoke_critic_review` passes
    `design`. `phase_mode` stays `review`; `review_target` is not a new mode (decisions.md, "Kept
    from the previous effort"). On `review_target=brief` the critic also receives
    `phase_file_path`, the orchestrator's `PHASE_FILE_PATH`, for its reviewed-sections check.
  - **The finalizer** has no mode. It receives the IDs, `project_config_context_markdown` and
    `phase_file_path` (the approved copy every restore of a reviewed section reads; declared under its
    own `### Approved Copy Inputs` heading), and builds `.respec-ai/plans/{PLAN_NAME}/phases/{PHASE_NAME}/implementation.md` exactly
    as the architect does. On the markdown platform that is the phase file's sibling, the rule
    frozen respec-code uses (`src/platform/templates/commands/code_command.py:230-231`).
- **Reports never carry document bodies.** `implementation.md` has no MCP home (F29), which is why
  the agents write it to disk themselves. The grant was decided in phase 2 and is recorded with its
  caveat in decisions.md ("The writing agents put the `implementation.md` draft on disk
  themselves"): on opencode and codex the path scope rests on the prompt (F14), and on Claude Code
  it is unverified until manual check M7 runs.
- **Mode names are user-visible on opencode.** The invocation description is prompt text there
  (`opencode.py:208-229`), so it states the mode accurately and names no language.

### Subagent report format

The final message of every `respec-phase-*` subagent consists of exactly these four H2 sections, in
this order. Nothing precedes the first one.

```markdown
## For the user
## Decisions needed
## Research proposals
## Status
```

- **Empty sections are present and contain exactly `- None`.** They are never omitted, so the
  orchestrator and the tests can check structure without guessing.
- **`## For the user`** is markdown the orchestrator shows to the user as written: a briefing, a
  design summary, or a diff summary. It contains no questions; questions go in
  `## Decisions needed`. It holds summaries, never document bodies. H3 subheadings are allowed.
- **`## Decisions needed`** holds decision entries in the canonical format below, ranked by blast
  radius, highest first.
- **`## Research proposals`** holds research proposal entries in the format below, ranked by value.
- **`## Status`** holds these bullets, in this order:

  ```markdown
  - result: complete | needs-user | failed
  - mode: explore | draft | revise | review | finalize
  - persisted: <the design writes, e.g. "phase document updated; implementation.md written"> | nothing
  - detail: <one line; required when result is failed>
  ```

  The orchestrator branches on `result`. A `failed` result stops the workflow with the detail shown
  (fail-closed). `persisted` lists only the phase document and `implementation.md` writes, and is
  `nothing` when neither changed. The architect stores its notes on every engagement and does not
  list them, so a question-only engagement reports `nothing`.

**Decision entry (canonical).** There is one form. The single-line form the orchestrator parsed
before phase 2 is retired. This form is the nested one the architect emits (DECISION ENTRY FORMAT
in `phase_architect.py`), plus `Affects`:

```markdown
- OD-003 | <title>
  - Option A: <name> — <trade-off>
  - Option B: <name> — <trade-off>
  - Recommended: A — <why>
  - Affects: <seam paths, module paths, step numbers, or other IDs>
```

- **IDs.** The architect's entries use `OD-NNN`. The same ID and text also sit in the document's
  `### Open Design Decisions`, and the document wins on any mismatch. The critic's judgment questions
  use `CQ-NNN`. They are asked from its report, and the critic also stores each one in its
  feedback's `### Key Issues` (`- [judgment] [<Marker>] CQ-NNN: …`), because that stored feedback is
  its only memory between rounds. A new CQ takes the next number above every `CQ-NNN` in the
  previous reviews and in the SDs, so a finding keeps its ID across rounds. The finalizer's
  entries (phase 4) use `OD-NNN`, numbered above every OD and SD number in the document. Like `CQ`
  entries, they exist only in its report: the finalizer never edits `## Design Decisions`.
- **Options.** `Option C:` is optional; there is no fourth option. That keeps every question
  answerable in one prompt that also offers the "accept the recommended default for all remaining"
  exit.
- **Validation.** `validate_document` reports an entry missing its title, Option A, Option B or
  Recommended, plus the other entry defects listed in phase 3 work item 2. Python parses these
  entries (`src/utils/phase_structure.py`), so F35's premise no longer holds. The critic no longer
  raises these defects.

**Settled decision entry**, written by the orchestrator only:

```markdown
- SD-007 | source=user | supersedes=OD-003 | decision=<chosen option> | rationale=<user's reason, or the option's trade-off> | rejected=<the other option(s)> | affects=<the settled entry's Affects: line, verbatim> | binding=yes
```

- **`source` values:**
  - `user`: an answer to a prompt
  - `user-edit`: from diffing a hand edit
  - `materializer`: a skeleton-materialization outcome at sign-off (an unmaterialized or
    unintrospectable path, or a merge left untouched). It reports a tool result, not an answer.
  - `architect`: carried forward
  - `implementation`: written back by frozen respec-code (`src/utils/design_conformance.py:287`)

  The earlier `user-menu` and `user-override` sources are retired in favor of `user`.
- **Fields per source.** `user` carries `supersedes` and `rejected` when it settles an `OD-NNN`, a
  `CQ-NNN` or the unresolved checks, plus `affects` when it settles an OD or a CQ (below); an
  answer to a sign-off skeleton-conflict prompt settles no ID and has no `supersedes`. `user-edit`
  carries `section=<H2 > H3>` and neither `supersedes` nor `rejected`. `materializer` carries
  neither.
- **Required fields per source** (`validate_document` reports a missing or empty one; `part` names
  it):

  | `source` | Required, non-empty |
  |---|---|
  | `user` | `decision`, `rationale`, `binding`; plus `rejected` when `supersedes` names an OD or CQ |
  | `user-menu`, `user-override` (legacy, in documents written before phase 2) | `decision`, `rationale`, `binding` |
  | `user-edit` | `decision`, `binding` |
  | `materializer` | `decision`, `rationale`, `binding` |
  | `architect` | `decision`, `rationale`, `binding` |
  | `implementation` | `supersedes`, `reason` |
  | anything else, or missing | defect (`part`: `source`) |

  Keys beyond the required ones are allowed, for example `user-edit`'s `section=`.
- **Segment rules.** An entry is split on ` | `. A key segment starts with a known key followed by
  `=`, and the first occurrence of a key wins. Any other segment, including a repeated key, continues
  the previous value. This keeps frozen respec-code's signatures, which contain ` | `, intact, and
  stops a quoted finding from overwriting the quoting SD's own keys.
- **Accepting findings.** An accept-as-is unresolved-checks SD quotes each structural or
  implementation finding as `<finding key> — <detail>`, all on the SD's one line and joined by a
  semicolon and a space. The finding key is `<check> <subject>`, plus a space and `[<part>]` when `part` is
  non-empty. The server stops reporting a finding whose key is so quoted, and lists it in
  `skipped_checks` as `accepted: <finding key>`.
- **`supersedes`** names the `OD-NNN` or `CQ-NNN` it settles, or the reserved token
  `unresolved-checks`: the user accepted the mechanical findings two automatic repairs did not
  resolve, recorded as `decision=accept as-is: <each finding verbatim>`. The critic never raises an
  accepted finding again.
- **`affects`** (phase 4) records what the decision binds, so that survives the OD leaving
  `### Open Design Decisions`. Every writer of an SD whose `supersedes=` names an OD or a CQ
  (Steps 6, 10 and 11) writes it after `rejected=`, copied verbatim from the settled entry's
  `Affects:` line when it has one. It is absent otherwise: `source=user-edit`,
  `source=implementation`, `source=materializer` and `supersedes=unresolved-checks` have no
  `Affects:` line to copy. `validate_document` never requires it, because it cannot tell whether
  the OD had an `Affects:` line, so it is not in the table above; phase 4's B14 pins the writers.
  The segment rules treat `affects` as a known key (phase 4 Scope 5), so its segment never runs
  into the `rejected` value. Nothing inside an SD entry is checked as a reference.
- **IDs.** An SD takes the next number above every `SD-NNN` already in the document, three digits.
  It never reuses the number of the OD or CQ it settles.
- **Placement.** SD entries go under `### Settled Design Decisions`, and the settled OD is removed
  from `### Open Design Decisions`.

**Research proposal entry:**

```markdown
- RP-002 | <question it answers> | informs: OD-003, `<module path>` | Technologies: <a, b>; Topics: <x, y>; Query: <query> | tier: synthesis-only
```

- **`tier`** is exactly one of:
  - `in-kb:<path>`: an existing `.best-practices/` document. It costs nothing and is listed as "will
    use".
  - `synthesis-only`: KB full coverage. `bp-pipeline` synthesizes only: no web search, no KB write.
  - `web-research`: a partial or full gap. Exa and context7 run, and the result is written to the
    global KB.
- **Tier source.** The architect assigns the tier in `explore`, from local, read-only commands only:
  `generate-slug`, then `check-file-cache` **without** `--model` (F17), then `query-kb`.
- **When the KB is unavailable,** the architect says so in `## For the user` and proposes nothing on
  that basis. There is no "synthesize everything" fallback (F19).
- **Ranking.** Proposals are capped and ranked, and each one names what it informs. The phase 2
  document sets the cap.

### Relay protocol

The protocol is the same at every touchpoint. The critic follows the same pattern as the architect.

1. **Invoke.** The orchestrator invokes the subagent with its mode, IDs and config context, and
   nothing else (see "Agents and modes").
2. **Work and persist.** The subagent works in its own context. Before returning, it persists
   everything it changed:
   - The document goes to MCP via `update_document`.
   - Exploration notes go via `store_current_analysis`. That is one slot per loop that each write
     overwrites (F31), so every write is the **complete** notes, never a delta.
3. **Return the report** in the format above.
4. **Present.** The orchestrator shows `## For the user`, then asks each `## Decisions needed` and
   `## Research proposals` entry through the TUI's selection mechanism
   (`{selection_prompt_instructions}` / `WAIT for {selection_response_source}`; F12).
   - **Portable core:** one question per prompt. A research proposal is one question: approve, deny
     or edit.
   - **Claude Code extension:** questions are batched into one `AskUserQuestion` call, up to four per
     call. The limit of four comes from the tool's own schema; the public docs do not state it, so
     confirm it against the live tool definition when implementing.
   - **Briefing pacing** follows plan-conversation: one or two questions per message, and free-form
     pushback is welcome. The orchestrator holds the free-form conversation itself, from the report
     in its context.
   - **A user question that needs new codebase knowledge** is stored as feedback (step 5) and
     relayed to the architect in its current mode. The answer comes back in `## For the user`.
5. **Record.** The orchestrator records outcomes deterministically, **only from actual user
   responses**. A subagent's report carries no approval authority (F10).
   - Decisions become SD entries, written by the orchestrator into the document with
     `store_document`.
   - Research choices are marked on the RP line: `[approved]`, `[declined]`, or `[approved]` after an
     edit, with the line rewritten. A user-added proposal gets the next RP ID, with
     `source=user` appended.
   - Free-form direction goes through `store_user_feedback`, prefixed with a round tag:
     `[round N | briefing|review|sign-off|question]`. `get_feedback` returns every entry, untagged
     and unbounded (F31). The tag is context for the architect; it does not decide what is new.
     Newness is decided by position: `get_feedback` numbers user entries `## User Input <i>` in
     insertion order, the architect records in its notes the highest `<i>` it has applied, and it
     applies every entry above that. A round number cannot serve, because the run's guidance, the
     briefing answers and relayed questions all share round 0.
   - User hand edits of `phase.md` keep today's path: re-read, `validate_document` for content loss
     (shown to the user, because they are the user's own edits), diff into `source=user-edit` SDs,
     store.
   - Structural findings from `validate_document` go to the architect as a repair round and never
     to the user, unless they are orchestrator-owned or left over once the two-round budget is
     spent. Leftovers reach the user once, as the unresolved-checks decision.
6. **Re-engage.**
   - **Claude Code extension:** `SendMessage` resumes the same architect, with its exploration
     intact. It resumes in the background, with its original tool set (F10), and the orchestrator
     waits for its report. This sits behind a new `BuiltInToolCapability` that maps to `None` on
     opencode and codex (F13).
   - **Portable core:** a fresh invocation with the same mode and IDs. The architect rehydrates from
     `get_document`, `get_previous_analysis` and `get_feedback`.
   - **Either way,** the architect re-reads the document and **always** calls `get_feedback` before
     changing anything (F2; decisions.md "The architect always fetches feedback"). Its memory is
     never the source of truth for the document, because the orchestrator writes SDs and research
     marks between engagements.

### Stage marker

The marker is `## Metadata > ### Shape Gate`. It reuses the `ShapeGate` values, and the existing
CHECK constraint already allows all four (`migrations/028_v2_design_layer.sql:14-16`).

| Value | Means | Written by the orchestrator when |
|---|---|---|
| `unshaped` | No design exists | never; set by create-phase or a roadmap re-store |
| `shape-proposed` | A draft exists and is in review | the first draft is persisted |
| `shape-settled` | Signed off by the user | sign-off, always, including after a re-open |
| `shape-amended` | A settled phase deliberately re-opened by the user | the user chooses to re-open a `shape-settled` phase |

- **Only the orchestrator writes it.** The storage layer enforces this. `update_phase`, the agent
  write path through `update_document`, preserves the live row's `shape_gate`, exactly as it
  preserves frozen fields. `store_document`, the orchestrator path and the disk sync, writes it (F4).
- **Resume:**
  - `unshaped`: explore and briefing. Decisions already settled are not asked again.
  - `shape-proposed` or `shape-amended`: design review, from the on-disk draft.
  - `shape-settled`: offer to re-open, or show the handoff.
- **The draft is on disk.** The orchestrator writes the draft to disk on every review iteration, so
  the disk→MCP sync at the start of a re-run never clobbers newer work.
- **No version comparisons.** No gate compares `Phase.version`, because every write bumps it (F30).

### Research recording

Phases 2 and 3 work on the current sections:
- **The ledger** lives in `## Additional Details > ### Research Requirements`. That section exists for
  every phase, and frozen respec-code reads it (`src/platform/templates/agents/coder_contracts.py:234`). It holds:
  - every RP line, with its `[approved]` or `[declined]` mark
  - one `` - Read: `.best-practices/<file>.md` — informs: <IDs> — Source: <RP-NNN | in-kb> `` line
    per document in use
- **The UI-only `#### Design Research` block is retired** (phase 2). It covered UI phases only.
  Its idempotence semantics carry over unchanged: a `[declined]` proposal is never re-offered, and
  only a genuinely new gap is offered, once.
- **What the architect adds.** The ledger's RP marks and `- Read:` lines are the orchestrator's.
  `draft` and `revise` may add only two things: a nested `- Applied: <where>` line under a
  `- Read:` entry that a step cites, and at most one new unmarked RP line for a new gap. That line
  is also the report's single research proposal, which design review offers.
- **Results become `- Read:` lines.** The orchestrator writes `- Read:` lines only after validating
  `bp-pipeline`'s `BP_PIPELINE_COMPLETE. Output: <path>` signal and confirming the file exists.

Phase 4:
- **The orchestrator writes only the ledger** in `### Research Requirements`, exactly as in phases
  2 and 3. The ledger keeps frozen readers fed (F34).
- **The finalizer writes the agent-facing copy** in `## Grounding > ### Research to read`, from the
  ledger's validated `- Read:` lines, tagging each document with the decision, seam and step IDs it
  informs. Step tags exist only once the steps are finalized, and the finalizer owns
  `## Grounding`.
- **The two copies never disagree once `## Grounding` exists.** Phase 4's
  `research-copies-disagree` check compares their path sets.

### Critic findings

- **Every finding starts with a classification tag.** `[mechanical]` or `[judgment]` comes first,
  before any existing marker, for example
  `- [mechanical] [Verify Command Not Configured - BLOCKING]: …`.
- **`[mechanical]` findings.** These have exactly one correct fix that needs no user preference.
  Examples:
  - a cited path that does not exist
  - a relayed `implementation.md` finding
  - the verify command not matching project config
  - a UX Contract rule violation
  - a frontend presence class
  - a step file or Test List entry that the structure does not cover (phase 2's coverage checks)
  - a step that a cold-start agent cannot execute because something it cites does not exist (phase 4)
  - phase 4's brief-review markers: `Grounding Path Invalid`, `Step File Verb Invalid`,
    `Reviewed Section Changed`, `Cold Start Gap` (an answer that exists but the step does not
    cite) and `Success Criterion Missing` (an objective, scope item or deliverable with no SC-n).
    A brief-review finding is `[mechanical]` only when the finalizer may make its fix. A gap only
    a change to a step's `Goal`, `Files` paths or `Depends on`, or to a reviewed section, would
    close is advisory, and going back to design review closes it.

  The phase-document structural defects (a dangling ID, a seam path missing from Module Layout, a
  malformed decision entry, a Test List entry with no behavior, and the rest of the
  `structural_findings` checks in phase 3 work item 2) are detected by `validate_document` and
  repaired through the gate. The critic never raises them. Structural repair rounds share the
  two-round budget below; orchestrator-owned findings skip it and go straight to the
  unresolved-checks decision. `implementation.md` defects (a step no checklist item verifies, a
  checklist item with no usable verify command, a malformed step heading, a missing section) come
  back as `implementation_findings`. The gate passes no body, so it never sees them. The
  architect's self-check fixes them, and the critic relays any that remain as
  `[mechanical] [Implementation Plan Structure Invalid - BLOCKING]` blockers, repaired in `revise`
  within the same budget.

  Mechanical findings go in `### Blockers`. The architect fixes them in `revise` mode, and the user is not told.
  The orchestrator allows **at most two automatic repair rounds** per review. Anything still open
  after round two goes to the user as one "unresolved checks" decision: send back with direction,
  or accept as-is, recorded as an SD. It is never dropped silently and never loops forever.
- **On `review_target=brief`** (phase 4, the review of the finalized brief in Step 10.7):
  - `[mechanical]` findings, and open `structural_findings` from the Step 10.7 gate, are repaired
    by a fresh **finalizer** invocation, never by the architect's `revise`. They share one
    two-round budget, which resets when Step 10.7 starts.
  - `[judgment]` findings are asked at sign-off.
  - The brief review re-opens no design judgment: the user settled those at design review.
  - Structural repair in Step 10.7 goes to the finalizer; Step 9's gate is unchanged. Ownership is
    computed (`FindingOwner.FINALIZER`, see "Brief format (phase 4)").
- **The review target is in the stored feedback.** The critic's `- **Assessment Summary**:` value
  starts with `Review target: design` or `Review target: brief`, followed by a dash and the
  summary. `get_feedback` shows that value as the first line under each
  `## Iteration N - Score: X` heading, so the finalizer acts only on brief findings and the
  architect only on design findings. `get_feedback` is otherwise untagged (F31): it never renders
  the detailed feedback, and a line before the `# Critic Feedback:` heading is dropped on parse
  (probe, 2026-11-17).
- **`[judgment]` findings.** These are trade-offs where a reasonable designer could choose
  otherwise. Examples:
  - an unjustified seam
  - an under-surfaced decision
  - non-divergent options
  - plan-constraint fit
  - on the brief review, a choice nobody made (`Cold Start Decision`) and a criterion with no
    target value (`Unmeasured Success Criterion`). Their Option A is "leave it to the
    implementer's discretion (recorded under Delegation Bounds)".

  They go in `### Key Issues`, and also in the report's `## Decisions needed` as `CQ-NNN` entries.
  Option A is "keep as designed"; Option B is the critic's alternative. They never block the loop.
  Sign-off requires every `CQ` to be answered, or the recommended default accepted.
- **The critic never edits the document.** A finding that an SD has settled (`supersedes=CQ-NNN`) is
  never raised again.
- **Score rule.** `Overall Score` is 100 when `### Blockers` is empty, and 0 otherwise. There is no
  other scoring (F7, F9). Loop completion, still read through `decide_loop_next_action` as the
  fail-closed check, therefore means "no open mechanical findings".
- **Iteration rule.** The orchestrator passes `review_round`, starting at 1 and incremented on every
  critic invocation in the loop, and the critic stores its feedback with `iteration = review_round`.
  The current `get_loop_status().iteration + 1` rule reports the same number on every run, so each
  run replaces the last (F9).

### bp invocation per TUI

These sources are verified (F15–F18):
- `~/.config/best-practices-rag/references/bp-pipeline-interface.md:5`
- `~/.claude/commands/bp.md:137-157`
- `~/.claude/agents/bp-pipeline.md:1-7`
- `~/.config/opencode/opencode.json:5-27`
- `~/.codex/agents/bp-pipeline.toml:1-4`

The orchestrator dispatches **`bp-pipeline`** directly. It never uses `bp`, `Task(bp)`, `Skill(bp)`
or `$bp`.

| TUI | Grant | Invocation | Status |
|---|---|---|---|
| Claude Code | `Task(bp-pipeline)` in the command's allowed tools | the Task/Agent tool with subagent type `bp-pipeline`; the interface fields form the prompt | Verified. The phase command names `bp-pipeline` as its one external agent right after the shared guardrail (F18). |
| opencode | `Task(bp-pipeline)`, which becomes `permission.task: {"*": "deny", …, "bp-pipeline": "allow"}` (`opencode.py:288`) | `CALL task` with `subagent_type: "bp-pipeline"` | **Unverified:** whether a `"hidden": true` subagent can be dispatched by name, and whether the installed opencode honors the `permission.task` map. Phase 2's manual check M1 was not run: opencode is no longer used, so it does not block phase 2. Run it ([phase-2-manual-checks.md](phase-2-manual-checks.md), M1) before relying on the opencode research path. |
| codex | none enforceable (`Allowed tools:` is prose; F14) | spawn the custom agent `bp-pipeline` by its exact name | Verified. The adapter's helper renames respec agents to `respec-<x>-agent`, so external agents render through `render_external_agent_invocation` (`codex.py:258`), which keeps the exact name. |

Rules for every TUI:
- **The call text is adapter-rendered.** `TuiAdapter.render_external_agent_invocation` renders an
  external, non-respec agent invocation with the exact name, so the template stays TUI-neutral. The
  phase command renders it once, at Step 7, from `PhaseCommandTools.invoke_bp_pipeline`.
- **The preflight is real.** `best-practices-rag check --tui <tui>` runs through Bash at Step 3, the
  check `src/cli/services/best_practices_preflight.py:24` already uses. Verified in phase 2 against
  the installed best-practices-rag v0.2.16 (`best_practices_rag/cli.py:401-426`): `check` confirms
  that the `bp-pipeline` agent file is installed (`agents/bp-pipeline.md` for claude,
  `prompts/bp-pipeline.md` for opencode, `agents/bp-pipeline.toml` for codex), and it also fails
  when Neo4j is unreachable or the Exa key is missing. Any non-zero exit means bp is unavailable. It
  confirms that the file exists, not that the agent can be dispatched; opencode dispatchability is
  manual check M1. If bp is unavailable, the workflow degrades: it continues without research and
  tells the user. It never terminates.
- **The orchestrator computes bp-pipeline's inputs at dispatch time.** This is bp's own split: *"Steps
  1-4 run in the main session and produce scalar parameters"* (`~/.claude/commands/bp.md:23`). The
  inputs come from each approved proposal's Technologies, Topics and Query, using local commands
  only:
  - `OUTPUT_FILE` from `generate-slug`
  - `TECH_VERSIONS_JSON` and `CUTOFF_DATE` from `~/.config/best-practices-rag/references/tech-versions.md`
  - `PRIMARY_QUERY`
  - coverage fields from `query-kb`
  - `MODE: codegen`
  - `LANGUAGES` or `LANGUAGE_AGNOSTIC` from the project's declared languages in `stack.toml`, never
    from template text

  An edited or user-added proposal gets its tier recomputed the same way. If the tier rose, the user
  confirms it again before anything runs.
- **Concurrency.** `synthesis-only` items run with at most 3 parallel workers
  (`MAX_ACTIVE_BP_WORKERS`). `web-research` items run **one at a time**
  (`MAX_ACTIVE_WEB_RESEARCH_WORKERS = 1`), because `bp-pipeline` writes Exa results to fixed `/tmp`
  paths (F17).
- **Completion.** Accept only a result that contains `BP_PIPELINE_COMPLETE. Output: <path>` and
  whose file exists. Anything else fails that item and records nothing.
- **The cost invariant is a guard test.** On the path where the user denies everything, no
  `bp-pipeline` invocation is reachable.

### Section naming and frozen-reader compatibility

- **H2 naming.** A new H2 name must neither contain nor be contained in any other H2 name, typed or
  additional. `tests/unit/templates/test_phase_section_references.py:92-101` guards this for template
  sections; extend it to every new H2. Names fixed for phase 4: `Grounding`, `Guardrails`,
  `Delegation Bounds`, `Behaviors & Acceptance` (decisions.md). Also reserved: `Evolution Log`
  (respec-patch).
- **Prose hygiene.** Brief prose contains no bare `---` line, and no line starting with `##` or `###`
  inside a fenced block (F27).
- **No new H3s under mapped H2s.** New H3s under mapped H2s (`Overview`, `System Design`,
  `Design Shape`, `Design Decisions`, `Implementation`, `Additional Details`) are dropped (F28).
- **No text between a mapped H2 and its first H3.** It is dropped on parse **and not reported by
  `find_content_loss`**: probed on 2026-11-13 with a narrative line directly under
  `## Design Shape`, and again on 2026-11-17 after phase 3's override landed, with the same result.
  So the design narrative lives in `#### Design Narrative`, and phase 4 adds this case to
  `Phase.find_content_loss` ([F40](findings.md)).
- **Frozen-reader compatibility.** Every phase keeps emitting the following, because frozen
  respec-code and respec-patch parse them (F33, F34):
  - `phase.md`:
    - `# Phase: <kebab-case>`, with `## Overview` first
    - `## Design Shape` with `### Module Layout`, `### Skeleton Index` (meta-notation, F24),
      `### Collaboration And Wiring`, `### Test List` (`` - `path::behavior` ``) and
      `### Design Shape - Additional Sections` (home of `#### UX Contract`)
    - `## Design Decisions > ### Settled Design Decisions`
    - `## Additional Details > ### Success Criteria`, covering every objective, scope item and
      deliverable
    - `### Implementation Plan References` with `` - Constraint: `<path>` `` lines
    - `### Research Requirements` with `- Read:` lines
    - `### Shape Gate` = `shape-settled` at sign-off
  - `implementation.md`, at `.respec-ai/plans/<plan>/phases/<phase>/implementation.md`:
    - `## Build Order > ### Steps > #### Step N:` with integer N, each step naming the file paths it
      touches
    - `## Checklist` with `- [ ] <item> (Step N) (verify: <command from [commands].test>)` items.
      A Step whose files belong to several languages carries one `(verify: …)` per language.
      - The command is the `[commands].test` value of the language that owns the Step's files,
        never a hardcoded or remembered one.
      - The only permitted non-command verify value is this marker, written verbatim with the
        language's name (phase 1, item 7):
        `(verify: ask user — no test command configured for <language>; set [commands].test in .respec-ai/config/standards/<language>.toml)`
      - The architect writes the marker when that language has no standards TOML, or its
        `[commands].test` is empty, starts with `TODO` (in any case, optionally bracketed), or is
        `no_preference` (F25).
      - Phase 1's B12 test (`tests/unit/templates/test_phase_runtime_language_config.py`) pins
        the `(verify: ask user` substring. Phase 2's briefing raises the missing command as a
        decision, and phase 3's structural checks accept the marker as a valid verify value.
    - `## Policy` (`### Execution Intent Policy`, `### Deferred Risk Register`)

  Phase 4's `## Start here`, `## Exit criteria` and `## Deviations` sections are **added** as extra
  H2s; they do not replace these.

### Brief format (phase 4)

The writing agents are shown these layouts through `BRIEF_SECTION_PLACEHOLDERS` and
`IMPLEMENTATION_BRIEF_EXAMPLE` (`src/platform/templates/phase_contract_grammar.py`). The four H2
names come from `Phase.BRIEF_SECTIONS` (`src/models/phase.py`). Templates and checks import these;
none restates the layout in its own words.

**`phase.md` brief sections.** All four are raw markdown in `additional_sections` (F26), and
`build_markdown` renders them in this order, ahead of any other additional section:

| H2 | Required H3s | Written by |
|---|---|---|
| `## Grounding` | `### Build on`, `### Leave alone`, `### Exemplars`, `### Conventions`, `### Research to read` | finalizer |
| `## Delegation Bounds` | `### Out of scope`, `### Implementer's discretion`, `### Escalate if` | architect |
| `## Behaviors & Acceptance` | one traceability line per objective, scope item and deliverable, then `### Not covered by tests` | finalizer |
| `## Guardrails` | `### Invariants`, `### Error policy`, `### Security and performance`, `### Deviation protocol` | finalizer |

- Every required H3 is present, and an empty one holds exactly `- None`. A brief H2 with no content
  is dropped on parse, so "empty" is still `- None`.
- Every step reference is a `Step N` token (`informs: Step 2, Step 3`), never `Steps: 2, 3`.
- `## Behaviors & Acceptance` maps each item to its tests and criteria; it never defines a criterion
  (one home per fact).

**Typed homes kept**, because code or frozen readers parse them (F33, F34):

- `### Success Criteria`: `- SC-<n>: <measurable outcome> — measure: <a [commands] value or an
  observable check>`, together covering every objective, scope item and deliverable.
- `### Test List`: `` - `<test path>::<observable behavior>` — T-<n> ``, the ID after the closing
  backtick, because `parse_test_list` reads only the backticked text.
- `### Skeleton Index`: unchanged, with no IDs. A seam is cited as `` `<path>` :: <Owner>.<member> ``.
- `### Settled Design Decisions`: canonical SD entries with `rejected=` and `affects=`.
- `### Design Shape - Additional Sections`: `#### Design Narrative` first, then `#### UX Contract`
  when the phase has a user-facing UI.
- `### Research Requirements` (the ledger) and `### Implementation Plan References`: unchanged.
- **Retired from generation:** Architecture, Technology Stack, System Design - Additional Sections,
  Functional and Non-Functional Requirements, Development Plan, Testing Strategy, Implementation -
  Additional Sections and Integration Context. The model fields stay, so a hand-written one still
  round-trips; removing them is a follow-up migration.

**IDs.** Phase 4 adds these to the OD, SD, CQ, RP and FLOW families:

| ID | Defined by |
|---|---|
| `T-<n>` | a Test List entry's trailing `— T-<n>` |
| `SC-<n>` | a column-0 `- SC-<n>:` in Success Criteria |
| `G-<n>` | a column-0 `- G-<n>:` in Guardrails |
| `Step N` | an `implementation.md` `#### Step N:` heading |
| `DEV-<n>` | a line under `implementation.md`'s `## Deviations` |

An existing T, SC or G number is never renumbered, and a removed one's number is never reused; gaps
are allowed. Steps stay contiguous from 1, and only the architect's `revise` renumbers them,
updating every reference in both files.

**`implementation.md`**, with its H2s in this order: `## Start here` (`### Prerequisites`,
`### Required reading`, `### First action`), `## Build Order` (`### Staging`, `### Steps`),
`## Policy` (`### Execution Intent Policy`, `### Deferred Risk Register`), `## Checklist`,
`## Exit criteria`, `## Deviations`.

- **Step fields.** Each field is one bullet that starts with its bold label, in this order:
  `- **Goal:**`, `- **Context:**`, `- **Files:**`, `- **Depends on:**`,
  `- **Tests to turn green:**`, `- **Verify:**`, `- **Done when:**`. A step holds exactly the three
  draft fields (`Goal`, `Files`, `Depends on`) or all seven. No `##` or `###` line appears inside a
  step.
- **Field values.** `Files` is `create` and `modify` items separated by `;`, each naming one
  backticked path; respec-code dispatches each step by these paths. `Depends on` is `none` or
  `Step N` items. `Tests to turn green` is T-IDs, or `none — <reason>`. `Verify` holds one
  backticked command per language the step touches, the `[commands].test` value or an SD, or
  phase 1's `ask user` marker.
- **`## Deviations`** holds `- DEV-<n> | Step <N> | expected: … | found: … | action: …` lines from
  implementing agents, or `- None`.

**Who writes what.** Everything the user reviews at design review is the architect's. Everything
derived from the approved design afterwards is the finalizer's.

- **The architect**, in `draft` and `revise`: `## Delegation Bounds`, `#### Design Narrative`, the
  Test List's `T-<n>` IDs and the `SC-<n>:` Success Criteria; in `implementation.md`, the draft
  fields, `### Staging`, `## Policy` and `## Checklist`. A `revise` on a document that holds the
  finalizer's three H2s removes them, so the next finalize is a full pass.
- **The finalizer**, in Step 10.7: `## Grounding`, `## Behaviors & Acceptance` and `## Guardrails`.
  In Success Criteria it only completes a missing `measure:` and appends an `SC-<n>` for an
  uncovered objective, scope item or deliverable. In `implementation.md` it writes the four other
  step fields, `## Start here`, `## Exit criteria` and `## Deviations` (`- None` when empty), adds
  a Checklist item for any step without one, and sets each item's `(verify: …)` to its step's
  `Verify`. It reproduces every section the user reviewed verbatim.

**Finding ownership.** `FindingOwner` gains `finalizer`, computed and never guessed:

- A `phase.md` finding is `finalizer`-owned when the first segment of its `location` (the H2) is
  `Grounding`, `Behaviors & Acceptance` or `Guardrails`, or its `check` is
  `success-criterion-malformed`, or it is located in `Additional Details > Success Criteria` while any
  of the finalizer's three H2s is present (the finalizer appends criteria and completes measures
  there; before finalize the architect owns them). An additional section named `Grounding Notes` stays the
  architect's.
- An `implementation.md` finding is `finalizer`-owned when its `location` names a finalize-only
  section or field: `Start here`, `Exit criteria`, `Deviations`, `Context`, `Tests to turn green`,
  `Verify` or `Done when`.
- Phase 3's `orchestrator` rules are unchanged and take precedence. Every other finding stays
  `architect`.
- **Routing.** Step 9's gate acts only on `architect` and `orchestrator` findings, the architect's
  self-check fixes only `architect` findings, and the design-review critic relays only `architect`
  implementation findings, so a `finalizer` finding never reaches the architect. In Step 10.7,
  `architect` and `finalizer` findings go to the finalizer (an `architect` finding there means a
  section it reproduces has drifted), and `orchestrator` findings go to `STRUCTURAL_LEFTOVERS`.

---

## Supporting documents

- **[findings.md](findings.md):** 40 verified findings with `file:line` evidence. This is the
  perishable asset. Treat it as the reference whenever a phase document seems to assume something
  surprising.
- **[decisions.md](decisions.md):** the decision log, with rejected alternatives and rationale. It
  includes three revised decisions of the previous effort and one revised contract. Read it before
  re-opening a settled question.
- **[deferred-issues.md](deferred-issues.md):** small, real issues found while implementing a phase
  and deliberately left for later. Check it when starting a phase, and add to it instead of letting
  the phase you're on grow in scope.
- **`docs/phase-refactor/testing.md`:** the testing method. Required reading.

## Cross-cutting risks

1. **Brief quality is the whole feature.** If the architect drafts speculative abstraction and the
   user signs it off, the brief makes implementing agents *worse*. It is mitigated by the critic's
   judgment checks, its cold-start check (phase 4), and a person reviewing the first real runs.
   Prompts drift, so treat this as ongoing.
2. **The stage-marker storage rule** (phase 2, F4). If `update_phase` stops preserving
   `shape_gate`, an agent can silently mark an unapproved draft as settled.
3. **opencode research dispatch is unverified** (F15, and the bp table above). Do not assume parity
   until the manual check passes. The rule is TUI tiering, never capping Claude Code to match.
4. **Parser traps in new sections** (F27). Substring matching, `---` truncation and the missing
   detection for additional sections are silent. Phase 3's checks are the mitigation, so do not
   ship phase 4's sections before them.
5. **Upstream best-practices-rag defects** (F17). The cache-model mismatch and the fixed `/tmp` paths
   are worked around, not fixed. Report them upstream, and re-check the workarounds when
   best-practices-rag is upgraded.
6. **Least privilege is Claude-Code-only** (F14). Read-only and path-scoped guarantees on opencode
   and codex rest on prompt text. The architect's path-scoped `implementation.md` Write is
   unverified on Claude Code too until manual check M7 runs (decisions.md).
