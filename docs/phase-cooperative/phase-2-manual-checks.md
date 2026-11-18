# Phase 2: manual checks for a live TUI

These are the phase 2 exit checks that need a person at a live Claude Code session. Each one is
written so it can be run cold. Record every result in the place each section names, with the date.

| Check | What it settles | Status (2026-11-16) |
|---|---|---|
| M1 | opencode dispatches the hidden `bp-pipeline` subagent and honors `permission.task` | **Not run. Not blocking**: opencode is no longer used. README marks the opencode research path unverified. |
| M2 | End-to-end on Claude Code: three touchpoints, the research cost invariant, resume by `SendMessage`, background waits | To run |
| M3 | The `AskUserQuestion` batch limit of 4 | Done. Confirmed against the live tool schema on 2026-11-13 |
| M4 | Resume from the stage marker after an interrupt, and re-open | To run |
| M5 | The frozen reader accepts the signed-off output | Scripted half done (stage S5). The live half is step M2.9 below |
| M6 | Rewording prompts never breaks the suite | Done, scripted (stage S5) |
| M7 | Whether Claude Code enforces the architect's path-scoped `Write` | To run. The result goes in decisions.md |
| P3.1 | A structural defect hand-edited into `phase.md` is repaired before you see it, and the happy path keeps three touchpoints | To run |
| P3.2 | An unrepairable defect reaches you once as an unresolved check, and accepting it sticks | To run |
| P3.3 | A bare `---` in an extra section is a content-loss prompt, never a structural one | To run |
| P3.4 | codex and opencode agents call `validate_document`, and the critic Globs `paths_to_verify` | To run. **Not blocking** for opencode, which is no longer used |
| P3.5 | The tool description and a sample of findings read well | To run |
| P4.1 | Three touchpoints, and no prompt between design approval and sign-off | To run |
| P4.2 | Going back from sign-off and signing off again regenerates the finalizer's sections | To run |
| P4.3 | `phase.md` holds no retired section, and `implementation.md` keeps its frozen formats | To run |
| P4.4 | Frozen respec-code reads a phase-4 brief | To run |
| P4.5 | Brief quality, judged against the spec's judgment calls 1-4 | To run |
| P4.6 | A fresh session implements the brief with no guesses, in two languages without special support and one with a materializer | To run |
| P4.7 | The finalizer on opencode and codex | To run. **Not blocking** for opencode, which is no longer used |

## 0. Setup (once)

The checks must run against an MCP server built from the working tree. The `respec-ai`
server registered at user scope is `respec-ai mcp-server`, which proxies to the released Docker
image (`src/cli/commands/mcp_server.py`). That image does not have phase 2's storage rule (B1)
or phase 3's key-mode `validate_document`, so against it Step 9's gate fails closed on the
first draft.
Run everything in a scratch project, never in the respec-ai repo.

1. Set two variables for the shell you run the checks from:

   ```bash
   export REPO=/path/to/your/respec-ai/checkout
   export LIVE=/tmp/respec-p2-live
   ```

2. Bring the dev database up to date. `respec_dev` on `localhost:5433` was at migration 028 on
   2026-11-16; `migrations/029_v2_drop_tasks.sql` was pending.

   ```bash
   cd "$REPO"
   DATABASE_URL=postgresql://respec:respec_dev@localhost:5433/respec_dev uv run python scripts/migrate.py
   docker exec respec-ai-db-dev psql -U respec -d respec_dev -Atc "select max(version) from schema_migrations"
   ```

   Expected: `29`.

3. Create the scratch project. A Go module is used because respec-ai has no special support for
   Go, and `init` needs a detectable language or `regenerate` refuses the stack config.

   ```bash
   rm -rf "$LIVE" && mkdir -p "$LIVE" && cd "$LIVE"
   git init -q .
   printf 'module example.invalid/livecheck\n\ngo 1.22\n' > go.mod
   printf 'package main\n\nfunc main() {}\n' > main.go
   git add -A && git commit -qm "scratch: start"
   "$REPO/.venv/bin/respec-ai" init --platform markdown --skip-mcp-registration --yes
   ```

   Use the venv binary from inside `$LIVE`. `init` acts on the current directory, and
   `uv --directory "$REPO" run …` would change the directory to the repo.

4. Register the working-tree server for this project only. Local scope takes precedence over the
   user-scope `respec-ai` while you are in `$LIVE`, and it writes nothing into the repo.

   ```bash
   cd "$LIVE"
   claude mcp add respec-ai -s local \
     -e MCP_STATE_MANAGER=database \
     -e DATABASE_URL=postgresql://respec:respec_dev@localhost:5433/respec_dev \
     -e MCP_LOG_FILE="$LIVE/mcp-server.log" \
     -- uv --directory "$REPO" run python -m src.mcp
   claude mcp get respec-ai
   ```

   Expected: `claude mcp get` shows the `uv … python -m src.mcp` command, not
   `respec-ai mcp-server`. The tools stay `mcp__respec-ai__*`, which the generated commands grant.

5. Check that bp is available. Some M2 steps need it.

   ```bash
   best-practices-rag check --tui claude; echo "exit=$?"
   ```

   With a non-zero exit, the workflow still runs but offers only `in-kb` research. Steps M2.4 and
   M2.5 then cannot run; record them as blocked by bp, not as failures.

6. Start Claude Code in `$LIVE`. Run `/mcp` and confirm `respec-ai` is connected. Note whether fork
   mode is on; the sub-agents doc's "Turn fork mode off" describes the setting. Record it with M2.

7. Make a plan with at least three roadmap phases. Use a small but real topic, and if you can,
   one that the knowledge base already covers, so that a `synthesis-only` proposal appears.
   Include one UI phase if you want the DesignSync check (M2.10).
   - `/respec-plan p2-live-check` (or `/respec-plan-conversation` first)
   - `/respec-roadmap p2-live-check`

   The three phases are called **A**, **B** and **C** below.

## M2: End to end on Claude Code

Record the results in `docs/phase-cooperative/phase-2-cooperative-flow.md`, under Exit criteria, M2.

**Run A, the happy path with research denied.** Run `/respec-phase p2-live-check <phase A>`.

- **M2.1 Three touchpoints.** Count the stages where the workflow stops and waits for you:
  - accept the recommended default at the first decision
  - deny every research proposal
  - choose "Continue"
  - approve the design
  - sign off without committing

  Expected: exactly three stopping stages, in this order:
  - Step 6, Briefing
  - Step 10, Design Review
  - Step 11, Sign-off

  Several questions inside one stage count as one stop. The critic review and the automatic
  repairs (Step 9) never stop for you.

- **M2.2 Research costs nothing when denied.** Expected:
  - The transcript contains no subagent call to `bp-pipeline`.
  - `.best-practices/` is unchanged.
  - In `.respec-ai/plans/p2-live-check/phases/<phase A>/phase.md`, under
    `### Research Requirements`, every proposal you denied ends with `[declined]`.

- **M2.3 Waits.** Expected:
  - After each architect or critic call (a subagent spawn or a `SendMessage`), no prompt appears
    and no later step runs until that agent's report arrives.
  - With fork mode on, note whether the orchestrator still waited. That wording is a judgment call
    the spec says only a live run can confirm.

- **M2.4 Brief quality** (README "Cross-cutting risks" 1). Read:
  - the briefing as shown at Step 6
  - the signed-off `phase.md`
  - `implementation.md`, next to `phase.md`

  Judge whether the briefing is useful and the draft is sound: no speculative abstraction, seams
  justified, steps a cold agent could run. Write a one-paragraph verdict.

**Run B, research, a change request and a commit.** Run `/respec-phase p2-live-check <phase B>`.

- **M2.5 One approved research proposal becomes a `- Read:` line** (needs bp). At the briefing,
  approve exactly one `synthesis-only` proposal and deny the rest. Expected:
  - one `bp-pipeline` call
  - a new `.best-practices/<slug>.md`
  - a line in `### Research Requirements` of the form
    ``- Read: `.best-practices/<file>.md` — informs: … — Source: RP-NNN``

- **M2.6 A change request resumes the same architect.** At the design review's final prompt,
  choose "Tell me what to change" and give one concrete change. Expected:
  - The next architect engagement is a `SendMessage` addressed to the agent ID recorded at
    explore, not a new subagent spawn.
  - The resumed architect calls `get_document`, `get_feedback` and `get_previous_analysis` first.
  - It runs no knowledge-base lookups (`best-practices-rag generate-slug`, `check-file-cache` or
    `query-kb`) and no fresh exploration of the codebase.
  - The critic reviews again (Step 9) before the design review returns.

  Also record whether `to: ARCHITECT_AGENT_ID` (`src/platform/template_helpers.py:199`) resolved.
  If the send was refused and the orchestrator fell back to a fresh `revise` invocation, copy the
  error text. This settles the open question stages S2 and S4b raised about addressing a typed
  spawn by ID.

- **M2.7 The hand-edit window at Step 10.2** (stage S4b's open item). On the next design review,
  while the open questions are still being asked:
  1. Edit `phase.md` by hand: add one sentence to `### Collaboration And Wiring`.
  2. Answer the remaining questions.

  Expected outcomes:
  - **The window is real** if your sentence is gone from `phase.md` at the final prompt. Step
    10.2's disk-mirror write (`src/platform/templates/commands/phase_command.py:1079-1085`) ran
    before Step 10.4's re-read (`:1125`).
  - **No window** if the sentence survives, or if the final prompt's re-read detects it and runs
    the hand-edit path (Step 10.5).

  Record which. If the window is real, the fix is to re-read the disk before 10.2's write.

- **M2.8 Commit with hooks.** At sign-off, choose "Sign off and commit". Expected:
  - `git log -1 --stat` shows one commit, `design: sign off <phase B>`.
  - It contains exactly `phase.md`, `implementation.md` and any skeleton files this run wrote.
  - It contains no scratch files.
  - If you have a commit hook, it ran.
  - `### Shape Gate` in `phase.md` reads `shape-settled`.

- **M2.9 The live half of M5.** In the same session, run `/respec-code p2-live-check <phase A>`
  and stop it once it displays "✓ Phase and implementation plan resolved". Expected:
  - It passes the shape gate (`src/platform/templates/commands/code_command.py:221`).
  - It reads `implementation.md` from `dirname(phase.md)` (`:231-232`) without an error.

- **M2.10 DesignSync in a background subagent** (optional, only with a UI phase). Run
  `/respec-phase` on the UI phase. In the explore architect's transcript, check whether the
  `DesignSync` tool is available, or whether a call to it fails because the tool is missing. If
  it is missing, log the deferred-issues entry phase 2 work item 13 describes: the architect's
  live-design grounding silently falls back to the local bundle. If you have no UI phase, record
  "not run".

## M4: Resume

Record the results under Exit criteria, M4, in the phase 2 document.

- **M4.1 Interrupt during design review.**
  1. Run `/respec-phase p2-live-check <phase C>` up to the design review (Step 10).
  2. Interrupt the session at any question there.
  3. Check that `phase.md` on disk holds the draft and that `### Shape Gate` reads
     `shape-proposed`.
  4. Re-run the same command.

  Expected:
  - "↻ Resuming the design review from the draft on disk".
  - Then a critic review (Step 9), then the design review (Step 10).
  - No briefing, and no explore.

- **M4.2 Interrupt after the briefing, before the draft.**
  1. Pick a phase that has not been run yet: a fourth roadmap phase, or a fresh plan with one
     phase. (`respec-ai db delete-plan` deletes a whole plan, not one phase's design.)
  2. Run `/respec-phase` on it.
  3. Answer the briefing: settle at least one decision and decline at least one proposal.
  4. Interrupt as soon as Step 7 or Step 8 starts.
  5. Check that `phase.md` on disk holds the new `SD-NNN` entries and the `[declined]` marks, and
     that `### Shape Gate` still reads `unshaped`.
  6. Re-run.

  Expected:
  - Explore runs again.
  - No settled decision is asked again.
  - No `[declined]` proposal is offered again.

- **M4.3 Re-open a signed-off phase.** Run `/respec-phase p2-live-check <phase A>`, which was
  signed off in M2. Expected:
  1. The workflow offers to re-open the phase or show the handoff. Choose re-open.
  2. Right after you choose, `### Shape Gate` in `phase.md` reads `shape-amended`.
  3. While it is `shape-amended`, `/respec-code p2-live-check <phase A>` refuses at the shape
     gate with "### Shape Gate is 'shape-amended', not 'shape-settled'" (B28).
  4. After review and sign-off, the marker reads `shape-settled` again.

## M7: The architect's write scope on Claude Code

Record the result in `docs/phase-cooperative/decisions.md`, at "M7 result" under "The writing
agents put the `implementation.md` draft on disk themselves". If the scope is not enforced, also
correct README "Agents and modes" and "Cross-cutting risks" 6 (phase 2 work item 13).

The architect's own prompt forbids any other write, so it cannot show whether the tool layer
enforces the scope. Use a probe agent with the same `tools` entry instead.

1. In `$LIVE`, confirm the regenerated architect's grant:

   ```bash
   grep '^tools:' .claude/agents/respec-phase-architect.md
   ```

   It must contain `Write(.respec-ai/plans/*/phases/*/implementation.md)`.

2. Create `$LIVE/.claude/agents/m7-write-probe.md` with exactly this content:

   ```markdown
   ---
   name: m7-write-probe
   description: Probe whether a path-scoped Write grant is enforced on a subagent
   tools: Read, Write(.respec-ai/plans/*/phases/*/implementation.md)
   ---
   Report first whether you have a Write tool at all. Then make exactly these two writes with the
   Write tool, in order, and report each tool result verbatim (success, or the exact error or
   denial text). Use no other tool to write.
   1. Write the text "m7 outside" to `m7-outside.txt` in the project root.
   2. Write the text "m7 inside" to `.respec-ai/plans/m7/phases/m7/implementation.md`.
   ```

3. Restart Claude Code in `$LIVE`, then ask: "Run the m7-write-probe agent." If a permission
   prompt appears for the outside write, deny it and note that it appeared.

4. Record one of these outcomes:
   - **No Write tool.** The `Write(<glob>)` entry does not resolve inside a subagent's `tools`
     list. This is a defect: the architect cannot write `implementation.md` on Claude Code. Raise
     it before relying on the draft step.
   - **Outside write refused by the tool layer, inside write succeeded.** The scope is enforced.
   - **Outside write produced a permission prompt.** The tool list did not narrow `Write`; only the
     session's permission layer stood in the way.
   - **Both writes succeeded silently.** The scope rests on the prompt alone, as it does on
     opencode and codex.

5. Clean up: delete `.claude/agents/m7-write-probe.md`, `m7-outside.txt` and `.respec-ai/plans/m7`.

## M1: opencode research dispatch (not run)

opencode is no longer used, so M1 does not block phase 2. README "bp invocation
per TUI" marks the opencode research path unverified. If opencode is used again, check two things
before relying on research there:
- The installed opencode dispatches the `"hidden": true` `bp-pipeline` subagent by name from the
  generated `cmd-respec-phase` agent.
- It honors that agent's `permission.task` map. Today the map is `{"*": "deny",
  "respec-phase-architect": "allow", "respec-phase-critic": "allow", "bp-pipeline": "allow"}`,
  written by `src/platform/tui_adapters/opencode.py:288`.

## Teardown

```bash
cd "$LIVE" && claude mcp remove respec-ai -s local
DATABASE_URL=postgresql://respec:respec_dev@localhost:5433/respec_dev "$REPO/.venv/bin/respec-ai" db delete-plan p2-live-check --force
rm -rf "$LIVE"
```

The user-scope `respec-ai` registration is never touched by these steps.

## Already verified without a TUI (stage S5, 2026-11-16)

- **Regenerate.** In a scratch project with HOME and every XDG directory isolated, these all
  exited 0:
  - `respec-ai init --platform markdown --skip-mcp-registration --yes`
  - `models opencode … --project`
  - `models codex … --project --no-apply`
  - `regenerate --force --tui all`

  No TUI reported a failure. The artifacts checked out as follows:
  - Every codex TOML and `openai.yaml` parses, `opencode.json` parses, and every `{file:…}`
    reference in it resolves.
  - Every Claude Code and codex frontmatter block parses. The five commands whose bracketed
    `argument-hint` (for example `[plan-name] [phase request]`) is not strict YAML were already
    rendered that way before phase 2.
  - No artifact sets `context: fork`.
  - No opencode or codex artifact mentions `SendMessage`.
  - codex dispatches `bp-pipeline` by its exact name and keeps the close-after-harvest line.
  - Claude Code grants `Task(bp-pipeline)`, `SendMessage` and `AskUserQuestion`, and the
    architect's tools contain no question tool.
  - All three phase commands render 12 steps and one loop initialization.
- **M5, scripted.** A `phase.md` built through Step 8's store and Step 11.5's three edits was run
  through the real store, disk-sync and get paths. Results:
  - It keeps `shape-settled`, the `- Constraint:` line, the materializer SD and the
    `- Read:`/`- Applied:` ledger.
  - respec-code's gate extraction passes it and refuses a `shape-amended` copy.
  - Its Step 1.2 glob and Step 5 path resolve the architect's `implementation.md`.
  - `extract_steps` finds every step. Every Checklist item carries `(Step N)` and one
    `(verify: …)` per language: Go's `[commands].test`, or the verbatim ask-user marker.
  - The Execution Intent Policy and the Deferred Risk Register parse.
- **M6, scripted.** The rendered phase command was post-processed on every TUI with 43 rewordings (42 matched the render; the other, a label comparison, matched nothing):
  - every question, header, option label and description
  - display lines
  - sub-step and step titles

  The `IF … == "<label>"` comparisons were changed with their labels. The full suite stayed at 2264
  passed, 1 skipped. A control run that reworded only the contract strings (`WAIT for`,
  `resume at Step`, `TOUCHPOINT`) failed 36 tests, which shows the reworded render reached the
  tests. No test pins prompt phrasing.

## Phase 3: structural checks (run in the same session as M2, before Teardown)

These cover the phase 3 manual exit checks in `phase-3-structural-checks.md`, under Exit criteria.
Use the same `$LIVE` project and the working-tree server from section 0. Record each result under
that heading, with the date. Use only the defects below: each one the architect can repair without
touching your intent, except P3.2, which is meant to reach you.

Hand edits are made in `.respec-ai/plans/p2-live-check/phases/<phase>/phase.md` while `/respec-phase`
waits at the design review's final prompt. Afterwards choose "I edited phase.md myself". Replace
`<phase>` with the phase name you are running. The phase needs a design layer (`## Design Shape`
with Module Layout, Skeleton Index and Test List), which any phase that reaches design review has.

- **P3.1 A repairable structural defect never reaches you.** Run `/respec-phase p2-live-check <phase C>`
  to the design review. At the final prompt, edit `phase.md` twice:
  1. Under `### Skeleton Index`, add one line whose path appears nowhere in `### Module Layout`,
     in the form below, with a real extension of your project's language. Note the path you used.

     ```text
     - `src/zz_extra/extra.<ext>` :: Extra.run(input: Input) -> Output
     ```

  2. In another existing Skeleton Index line, delete the backticks around its path.

  Then choose "I edited phase.md myself". Expected:
  - Neither problem is shown to you as a question, menu or report line.
  - The critic does not run until both are repaired. The architect is re-engaged (Step 9 repair
    round) without a prompt.
  - When the design review returns, the extra path is a new entry in `### Module Layout` and the
    backticks are back on the other line. Open `phase.md` to confirm.
  - The happy path still has at most three stopping stages (M2.1's count).

  If the review returns with an "unresolved checks" decision for either defect, record the finding
  text: the architect could not repair it.

- **P3.2 An unrepairable defect reaches you once, and accepting it sticks.** On a phase with at
  least one `OD-NNN` under `### Open Design Decisions`, delete one OD's `- Option B:` line, and
  choose "I edited phase.md myself". Restoring the line would undo your edit, so the architect
  leaves it. Expected:
  - You see it once, as one unresolved-checks decision naming `decision-entry-malformed OD-NNN [Option B]`.
  - Choose "accept as-is". `phase.md` gains an SD whose line contains
    `supersedes=unresolved-checks` and quotes that finding key.
  - Send the design back once more with any small change request. Expected: the decision is not
    asked again, and the critic's report does not mention the finding.

- **P3.3 A bare `---` is content loss, not structure.** Add a new H2 section at the end of
  `phase.md`, for example `## Extra Notes`, with a line containing only `---` in the middle of it.
  Choose "I edited phase.md myself". Expected:
  - The content-loss menu shows you the `Extra Notes` heading, because the text after the rule
    would be dropped.
  - No structural finding is reported for it, and no repair round runs for it.

  Then remove the section, so later checks start clean.

- **P3.4 Grants on codex and opencode** (prompt-enforced: F14). Run a design review on codex. In
  the transcripts, confirm that the architect calls `validate_document` after it persists the phase,
  and that the critic calls it once and then Globs the paths in `paths_to_verify`.
  - **Not blocking for opencode.** It is no longer used. If you do run it, record the same result;
    if you do not, record "not run, not blocking".
  - On Claude Code, the grants are in the agents' frontmatter (`tools:`), and the critic's list
    has no `Write`, `Edit`, `update_document` or `store_document`. Confirm that in
    `.claude/agents/respec-phase-critic.md`.

- **P3.5 Read the output as the architect would.** Run `/mcp` or inspect the tool list, and read
  the `validate_document` description. Then run the key-mode call on the stored phase, and read a
  sample finding rendered as `<check> <subject> [<part>] — <detail>`. Expected:
  - Each finding names its subject and its single fix.
  - No `detail` names a programming language, framework or file extension.

  This is a judgment check. B9 (`tests/unit/utils/test_phase_structure.py`) is the machine check.

## Phase 4: the agent-ready brief (run in the same session as M2 and Phase 3, before Teardown)

These cover the phase 4 manual exit checks in `phase-4-agent-ready-brief.md`, under Exit criteria.
Use the same `$LIVE` project and working-tree server from section 0, and a working-tree
`respec-ai regenerate --force` first, so `.claude/agents/respec-phase-finalizer.md` exists. Record
each result under its heading, with the date. Replace `<phase>` with the phase name you are running.

- **P4.1 Touchpoints, and nothing between approval and sign-off.** Run
  `/respec-phase p2-live-check <phase D>` to the end, answering only what it asks. Expected:
  - At most three stopping stages (M2.1's count). Finalizing the brief and reviewing it are not
    stages.
  - After you choose "Approve the design", no prompt appears until the sign-off stage. The
    transcript shows the finalizer engaged once, a structure check, and the brief critic engaged,
    all without asking you anything.
  - At sign-off you see the brief summary. Brief questions, if any, are asked inside the sign-off
    stage, in one batch.

- **P4.2 Go back and sign off again.** At sign-off choose "go back to design review" and ask for one
  change (for example, one more Test List behavior). Approve the design again. Expected:
  - The finalizer runs again. `phase.md`'s `## Grounding`, `## Behaviors & Acceptance` and
    `## Guardrails`, and `implementation.md`'s `## Start here`, `## Exit criteria` and
    `## Deviations`, mention the new behavior. None of them is left from the first pass.
  - Still no prompt between approval and sign-off, and the touchpoint count over the whole run
    stays at three plus the one extra design review you asked for.

- **P4.3 No retired section, frozen formats kept.** Open the signed-off files. Expected:
  - `phase.md` has none of the retired sections: `## System Design`, `## Implementation`, or the
    headings `Architecture`, `Technology Stack`, `Functional Requirements`,
    `Non-Functional Requirements`, `Development Plan`, `Testing Strategy` and `Integration Context`.
    Run `grep -n -E '^#{2,4} (System Design|Implementation$|Architecture|Technology Stack|Functional Requirements|Non-Functional Requirements|Development Plan|Testing Strategy|Integration Context)' <phase.md>`.
    It prints nothing.
  - `## Grounding`, `## Delegation Bounds`, `## Behaviors & Acceptance` and `## Guardrails` appear in
    that order.
  - `implementation.md` keeps `#### Step N:` headings, `## Checklist` and `## Policy`.

- **P4.4 Frozen readers still work.** In the same project run `/respec-code` on the signed-off
  phase, and stop it after the planning steps. Expected:
  - The `shape-settled` gate passes.
  - The steps are found, so dispatch is not silently backend-only: the command lists one task per
    `#### Step N:`.
  - The coder reads the `## Checklist`.

- **P4.5 Judge the brief.** Read `phase.md` and `implementation.md` as the implementer would.
  Judgment calls 1-4 in the spec are the yardstick. Expected:
  - Every path under `## Grounding` exists in the repository.
  - `## Delegation Bounds` lines each name a seam, a module, a decision or a concrete condition.
  - `## Behaviors & Acceptance` is a one-line-per-item map, not prose.
  - Every step reads as executable from cold: goal, files, dependencies, verify command and done
    condition are all concrete. No `<...>` placeholder remains, and no command was guessed.
  - The brief is not much longer than the `docs/phase-refactor/phase-*.md` documents (7-18 KB).
  - Cold-start questions asked at sign-off number at most four. Record the count.

- **P4.6 The effort-level check, two languages.** Create two scratch projects in languages
  respec-ai has no special support for (for example Go and Elixir), and a third in a language that
  has a materializer. In each, configure `[commands]` in the standards TOML first, then run one real
  phase to sign-off. Expected, per project:
  - The handoff at the end of the run shows the Claude Code delegation instruction.
  - Paste that instruction into a fresh Claude Code session in the project. It implements the steps
    in dependency order, runs each step's Verify command, and asks no clarifying question.
  - Record every point where it had to guess in
    [deferred-issues.md](deferred-issues.md), or fix the prompts and rerun.

- **P4.7 codex and opencode.** Run one phase on codex. In the transcripts confirm that the
  orchestrator invokes `respec-phase-finalizer-agent`, and that the finalizer writes
  `implementation.md`. The handoff on codex has no delegation instruction (Claude Code only).
  - **Not blocking for opencode.** It is no longer used. If you run it, record the same result;
    if not, record "not run, not blocking".
