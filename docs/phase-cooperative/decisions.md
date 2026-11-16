# Decision log

Rationale for the design positions in this effort, including the alternatives that were rejected.
Three of these revise decisions recorded by the previous effort (`docs/phase-refactor/decisions.md`)
and one revises a recorded contract (`docs/TEMPLATE_AUDIT.md`). Those are marked **(revised)** and
keep the original position, because the reasoning that moved them is the part most likely to be
lost.

Findings are cited as **F1**–**F39** ([findings.md](findings.md)). Read this file before re-opening
a settled question.

---

## The critic reviews drafts before the user sees them **(revised)**

**Chosen:**
- The critic runs on the architect's draft before design review, and again on the finalized brief
  before sign-off.
- It never edits the document. Each finding is classified (README "Shared contracts → Critic
  findings"):
  - `[mechanical]` findings go back to the architect automatically, for at most two repair rounds.
  - `[judgment]` findings become questions in the orchestrator's next "Decisions needed" prompt.
- The user keeps the final say. Overruling a finding is recorded as a Settled Decision, and the
  critic never raises it again.

**Rejected:**
1. *Critic after user approval, with a joint gate* (the previous effort's position). The user
   approved, the critic ran, and the act closed only when both agreed on the same `Phase.version`
   (`phase_command.py:794-852`). This produced the approve → critic → re-approve cycle and a
   version-equality gate. Every orchestrator write bumps the version (F30), so that gate trips on the
   workflow's own bookkeeping.
2. *Critic iterates to a quality threshold before the user sees anything* (the conventional order).
   Still rejected for the original reason: the user would receive an LLM-polished design they had no
   hand in.
3. *Critic edits the document directly.* That makes the critic a second, unattributed designer, and
   its edits would bypass the user.

**Why the reversal is safe now:** the original concern, a polished design the user had no hand in,
is met earlier. The user settles the consequential decisions in the briefing, before any draft
exists. The critic now only raises questions, and checks stay invisible unless a human is needed
(plan principle 4).

**Consequence: the score.** No numeric rubric (F6, F7). `CriticFeedback` still requires an
`overall_score`, and loop completion still reads it (F9). So the critic reports a fixed score: 100
when `### Blockers` is empty, 0 otherwise. `### Blockers` holds `[mechanical]` findings only.

**Originally:** "The critic runs *after* user approval" (`docs/phase-refactor/decisions.md:38-55`).

---

## `implementation.md` is reviewed inside the design review **(revised)**

**Chosen:**
- `implementation.md` stays a sibling file next to `phase.md`.
- The architect drafts its build order in the same `draft` pass as the design.
- The user reviews both in one design-review touchpoint.
- The finalizer later expands each step into a delegation brief (phase 4).

**Rejected:** *a separate implementation-plan gate* (Step 12.6). It was generated from shape
artifacts only, before the detail act existed (F5). It added a human stop, and it fixed the build
order before the content being ordered was written.

**Originally:** "`implementation.md` is a bundle sibling, not sections inside `phase.md`"
(`docs/phase-refactor/decisions.md:119-128`), which also gave build strategy *"its own gate"*. The
sibling-file half is kept; the gate is revised.

---

## The phase output targets any agentic harness **(revised)**

**Chosen:**
- The output is an agent-ready implementation brief. Claude Code, opencode, codex, or a human with
  an agent can plan from it, delegate from it and verify against it.
- respec-code is one possible consumer, not the design target.
- Its typed contracts are kept stable, but never optimized for (see "respec-code and respec-patch
  are frozen" below).

**Rejected:** *keep shaping the output as respec-code's private input contract.* Modern harnesses
already orchestrate subagents, task lists and verification well. respec-ai's lasting value is
upstream: design decided with the user, grounded in the repo, and written so a cold-start agent does
not guess.

**Originally:** the previous effort's outcome was *"respec-code then fills in bodies"*
(`docs/phase-refactor/README.md:103`).

---

## Only the orchestrator talks to the user

**Chosen:**
- The `/respec-phase` command runs inline as the main agent (F11), and it is the only party that ever
  talks to the user.
- Subagents return questions as data in a fixed report format.
- The orchestrator asks them through the TUI's own prompt mechanism and records the outcomes
  deterministically (README "Relay protocol").

**Rejected:**
1. *Let subagents ask the user.* This is impossible on Claude Code. `AskUserQuestion` is removed from
   every subagent, even when listed in `tools` (F10). No other TUI offers a portable alternative
   either.
2. *Run the architect as a fork, so it can keep the user's conversation.* Forks skip the tool filters
   (F10), but they would carry the whole conversation into the heavy-context worker, and that is the
   split this design exists to avoid. The Claude Code guardrail already forbids spawning a fork
   that the workflow does not name, and forbids substituting one for a respec agent
   (`claude_code.py:30-34`).
3. *Run the command with `context: fork`.* The orchestrator would then become a subagent and lose
   the user (F11).

**Why this split:** heavy context (codebase reads, KB lookups, drafts) stays in subagents. The
user's thread holds only the briefing and summaries, so it stays responsive and behaves the same on
every TUI.

**Guards (phase 2):**
- No agent declares the TUI's question tool.
- No command sets `context: fork`; this is checked on the raw template output (F11).
- The orchestrator declares the question tool (F12).

---

## The architect always fetches feedback

**Chosen:** on every engagement, fresh or resumed, the architect reads the document and all
feedback from MCP before it changes anything. There is no iteration gate, and the architect is not
granted loop status.

**Rejected:**
1. *Grant `get_loop_status` and keep the `iteration >= 1` gate.* The counter counts critic feedback
   only and starts at 1, so it cannot express "the user sent this back" (F2).
2. *Rely on a resumed architect's memory.* Between engagements the orchestrator writes Settled
   Decisions and research marks into the document, so a resumed architect's copy is stale.

**Why:** this is the root-cause fix for the lost first send-back (F2), whichever of its two paths
actually fires at runtime.

---

## Research is proposed by the architect and approved by the user

**Chosen:**
- **Automatic, local and read-only.** These run during `explore` to assign cost tiers: `query-kb`,
  checks of `.best-practices/`, `generate-slug`, and `check-file-cache` without `--model` (F17).
- **Existing KB docs are used unless the user removes them.** They appear as "will use" in the
  briefing.
- **Synthesis and web research run only after explicit approval.** They run before drafting, so the
  draft is informed by them.
- **Proposals are capped, ranked, and each tied to the decision or module it de-risks.** The user
  can approve, deny, edit or add.
- **Denied proposals are `[declined]` and never re-offered.** A genuinely new gap found during
  design review is offered once, through the same flow.
- **Cost invariant:** a user who denies everything pays zero `bp` calls.
- **Nothing triggers research automatically:** no automatic API prompts, no post-synthesis critic,
  and no blocker that demands research (F8).

**Rejected:**
1. *Today's detail-act synthesis of every `Synthesize:` line plus automatic API prompts*
   (`phase_command.py:1281-1469`), with a post-synthesis critic that can loop back. This is over-eager,
   and it makes research mandatory (F8).
2. *Automatic research on architect-flagged gaps.* The frontend effort already rejected three
   variants of this (`docs/frontend-refactor/decisions.md:633-660`). Gap-tier results are written to
   a Neo4j KB shared by every project on the machine, so a weak query is a permanent cost (F17).
3. *Approval required even for local lookups.* That adds touchpoints for work that is free and
   read-only, and it leaves the briefing unable to say what research would cost.

**Extends:** the frontend effort's "Shape-act research is user-elected, never automatic", from the
shape act to the whole workflow. Step 5.5's semantics and test intent are reused (F19).

---

## Research runs through `bp-pipeline` directly **(revised)**

**Chosen:**
- The orchestrator dispatches the `bp-pipeline` agent itself, with each TUI's own syntax and the
  inputs from the published interface (F16).
- The orchestrator computes those inputs at dispatch time, from local commands only. The architect
  assigns only each proposal's cost tier, during `explore`.
- The orchestrator recomputes the slug and tier for any proposal the user edits or adds.
- Full mechanism: README "bp invocation per TUI".

**Rejected:**
1. *`Task(bp)`*, as today. On all three TUIs it names something that cannot run (F15).
2. *`Skill(bp)` on Claude Code.* It works only on Claude Code and runs inline and serially in the
   orchestrator's context. bp's own Step 1 may also ask the user about language
   (`~/.claude/commands/bp.md:25-52`), which adds an unplanned touchpoint. opencode would still have
   no route.
3. *Ask the user to run `/bp` themselves.* That pushes work onto the user, and the result would not
   return as data.

**Originally:** *"`respec-phase` invokes `bp` as the public entrypoint. `bp` may delegate to
`bp-pipeline` internally"* (`docs/TEMPLATE_AUDIT.md:5-10`, commit `be39e52`). bp's own interface
document names respec-phase as an intended direct caller of `bp-pipeline` (F16), so the "don't
reach into internals" rationale does not hold. Update `TEMPLATE_AUDIT.md` in phase 2.

---

## Structural document checks live in MCP `validate_document`

**Chosen:**
- `validate_document` gains language-neutral structural checks: document structure only, never code
  semantics.
- They are implemented as pure, unit-tested functions behind a `PhaseTools.validate` override.
- Structural issues are reported **separately** from content loss (F29). The orchestrator routes
  structure to the architect, and routes content loss to the user only for the user's own edits.
- The draft step runs the checks, so mechanical issues are fixed before the user sees anything.

**Rejected:**
1. *Checks as critic prompt text.* They become non-deterministic, untestable, and paid for in critic
   tokens on every round.
2. *A separate MCP tool.* It would duplicate `validate_document`'s dispatch, and the orchestrator
   already calls `validate_document`.
3. *Checks that read the target project from the MCP server.* The container has no project mount
   (F29). Phase 3 runs file-existence checks host-side: `validate_document` returns the cited paths
   as `paths_to_verify`, and the agents check them with Glob.

**Constraints phase 3 inherits:**
- `implementation.md` is not a `DocumentType` (F29).
- The checks must cover `additional_sections` (F27).
- A Skeleton Index line that does not parse must be reported as a finding, not as a crash (F24).

---

## Zero language bias, enforced by a denylist guard test

**Chosen:**
- No phase-workflow template text names a programming language, framework, test runner, or file
  extension.
- Language specifics arrive only at runtime, from the target project's config and only for its
  languages:
  - standards TOMLs via `PROJECT_CONFIG_CONTEXT_MARKDOWN`
  - per-language authoring notes from the materializer
  - verify commands only from `[commands].test`
- If a verify command is empty, `TODO` or `no_preference` (F25), the briefing asks the user and
  points to `[commands].test` in `.respec-ai/config/standards/<language>.toml`. Nothing guesses.
  - **Corrected from the plan,** which pointed to `/respec-standards`. That command renders guides
    and *"MUST NOT edit canonical TOML files"*
    (`src/platform/templates/commands/standards_command.py:16`), and the `respec-ai standards` CLI
    has only `init` and `validate`. Phase 1, item 7 records the evidence.
- A guard test renders every phase-workflow template on all three TUIs and asserts that a denylist is
  absent.

**Guard scope:**
- **Covered:** the phase command, `respec-phase-architect`, `respec-phase-critic`, the finalizer and
  `respec-create-phase`.
- **Excluded:** frozen respec-code and respec-patch templates. They still name languages, and a
  coder test requires a TypeScript sentinel (F23).
- **Never denylisted:** respec-ai's own tooling nouns, which are not target-project languages, for
  example the Neo4j KB behind `best-practices-rag`. Products and infrastructure are left off the
  denylist, so no allowlist mechanism is needed (phase 1, item 1).
- A negative self-test feeds the guard a synthetic biased template, so it is proven to fire.

**Rejected:**
1. *An audit list of offending lines.* It is incomplete by the time it is written (F21 lists hits
   the plan's own audit missed).
2. *Render every known language's conventions into the template* (today's
   `for language in ('python', 'typescript')`, `phase_architect.py:113-121`). It is biased toward
   whatever is registered, and it grows without bound.
3. *A guard over every template in the repository.* It is permanently red until respec-code is
   retired, which is a separate decision.

---

## "Neutral" means a uniform meta-notation, not native syntax

**Chosen:**
- Skeleton Index entries keep respec-ai's uniform notation:
  `` - `<path>` :: <Owner>.<member>(<params>) -> <Result> ``, with optional trailing tags.
- Only the parameter and type text is written in the owning file's language.
- Test List entries keep `` - `<test path>::<behavior>` ``.
- Per-language rules, such as Python's dotted types or identifier-safe test names, come from
  materializer guidance at runtime.

**Rejected:** *`<path> :: <signature in that file's language>`* (the plan's draft placeholder).
Every Skeleton Index line is parsed against the meta-notation, even for languages with no
materializer, and a native signature crashes `materialize-skeletons` and `check-conformance` (F24).

---

## The stage marker is orchestrator-owned and reuses the `ShapeGate` values

**Chosen:** the `### Shape Gate` metadata field is the stage marker, with clean semantics:

| Value | Means | Written when |
|---|---|---|
| `unshaped` | No design exists | create-phase / roadmap (unchanged) |
| `shape-proposed` | A draft exists and is in review | the orchestrator persists the first draft |
| `shape-settled` | Signed off by the user | sign-off — always this value, including after a re-open |
| `shape-amended` | A settled phase deliberately re-opened by the user | the user chooses to re-open a `shape-settled` phase |

**The architect never writes the marker.** Prompt text cannot enforce this, because every
`update_document` call replaces `shape_gate` (F4). So the storage layer enforces it:
- `update_phase`, the agent write path, preserves the live row's `shape_gate`, the same way it
  preserves frozen fields.
- `store_document`, the orchestrator write path, writes it.

The phase 2 test runs against both state managers.

**Resume** is driven by the marker:
- `unshaped`: run explore and the briefing. Already-settled decisions are not asked again.
- `shape-proposed` or `shape-amended`: resume at design review from the on-disk draft.
- `shape-settled`: offer to re-open the phase or show the handoff.

**Rejected:**
1. *A new stage field or new enum values* (`briefed`, `drafted`, `signed-off`). This needs migration
   030 to replace the CHECK constraint (`migrations/028_v2_design_layer.sql:14-16`), and the existing
   four values express every needed state.
2. *Prompt-only ownership.* Unenforceable (F4).
3. *Orchestrator re-asserts the marker after every architect turn.* It costs a write per turn, and
   MCP is wrong whenever a run stops mid-turn.

**Consequence for frozen respec-code:** `code_command.py:221` accepts `shape-amended` as settled
(F34). Under the new meaning, a re-opened phase that has not been re-signed-off would pass that
gate. Sign-off always writes `shape-settled`, so the exposure is limited to the window while a
re-open is in progress. That window is closed by the one sanctioned edit to respec-code in this
effort (see "respec-code and respec-patch are frozen" below).

**Fixes:** F3, where `shape-amended` was overloaded.

---

## Kept from the previous effort

Kept unchanged, with the original reasoning in `docs/phase-refactor/decisions.md`:
- `CriticAgent.PHASE_CRITIC` with a `phase_mode` scalar (`docs/phase-refactor/decisions.md:108-117`).
  The critic's modes become `review` only. The scalar stays because a new critic outside the
  blocker-gate sets silently gates nothing.
- `LoopType.PHASE` (`docs/phase-refactor/decisions.md:97-106`): one loop per run, the channel for
  critic and user feedback.
- Create-only skeleton writes (`docs/phase-refactor/decisions.md:27-36`) and the materialize CLI
  (`docs/phase-refactor/decisions.md:166-183`). Conflict prompts appear only when target files exist.
- `### Skeleton Index` as the durable contract (`docs/phase-refactor/decisions.md:130-138`).
- No cap on the number of design decisions (`docs/phase-refactor/decisions.md:57-77`), with
  blast-radius ranking and the "accept the recommended default for all remaining" exit.
- Frozen Overview fields that bind agents only (`docs/phase-refactor/decisions.md:79-95`).
- User-elected research (`docs/frontend-refactor/decisions.md:633`), extended above.

---

## Brief prose lives under fixed H2 headings captured by `additional_sections`

**Chosen:**
- New agent-facing prose goes under new, fixed **H2** headings, which round-trip as raw markdown
  with no migration (F26).
- Typed fields stay only where code parses them, or where a frozen reader depends on them (F33,
  F34).
- The H2 names are chosen to be substring-safe against every other H2 (F27): **Grounding**,
  **Guardrails**, **Delegation Bounds**, **Behaviors & Acceptance**.
- The plan's "Design" and "Decisions" rows are served by the existing typed `## Design Shape` and
  `## Design Decisions` sections. The new decision fields, such as rejected alternatives, go inside
  SD entries.
- "Out of scope" goes inside **Delegation Bounds**. It cannot be an H3 under Overview (F28).

**Rejected:**
1. *New typed fields and columns.* Migration 030, plus parser and persistence changes, for prose no
   code reads.
2. *New H3s under existing H2s.* They are silently dropped on round trip (F28).
3. *The plan's literal H2 names `Design` and `Decisions`.* They capture content from
   `## System Design` and `## Design Decisions` (F27, probe).

**Rule for every phase:** brief prose never uses a bare `---` line, and never puts a `## `/`### `
line inside a fenced block (F27).

---

## respec-code and respec-patch are frozen

**Chosen:**
- Do not spend effort updating their readers for the new sections.
- Keep emitting every typed contract they parse (README "Frozen-reader compatibility").
- They may lose Tech Stack and other context folded into new sections; accept that.
- Their retirement, and the conformance reviewer's, is a separate decision outside this effort.

**The one sanctioned exception:** `code_command.py:221` changes to accept only `shape-settled`, in
phase 2, with a test. This is not an update for new sections. It keeps a safety gate correct after
this effort changes the meaning of the value it tests (see the stage-marker decision). **Confirmed by
the user on 2026-11-13.**

**Rejected:**
1. *Update them alongside.* That spends effort on a consumer whose future is undecided.
2. *Let them break.* They are still the only shipped consumer, and breaking them silently would
   look like a phase-side regression.

---

## The finalizer is a separate agent file

**Chosen:** phase 4 adds `respec-phase-finalizer`
(`src/platform/templates/agents/phase_finalizer.py`, `RespecAIAgent.PHASE_FINALIZER`). It writes the
brief prose and the per-step delegation briefs once the design is approved.

**Rejected:** *a fourth `phase_mode` on the architect.* Agent files are static, and the mode
arrives only at runtime, so every architect invocation would carry every mode's instructions.
Splitting is the only way to keep each prompt focused.

**Registration:** the finalizer must appear in both `_AGENT_NAMES` (`src/platform/template_generator.py:109`)
and the specs list in `_get_agent_specs` (`:250`), and the phase command must grant it with
`add_task_agent`. On opencode, an ungranted subagent is denied by `'*': 'deny'`
(`opencode.py:282-283`).

---

## The writing agents put the `implementation.md` draft on disk themselves

**Status: confirmed by the user on 2026-11-13, before phase 2.** Chosen by the design work, not by the
plan. Phase 2's manual check M7 still records whether Claude Code enforces the path scope on a
subagent; the decision stands either way.

**Chosen:**
- The architect, and in phase 4 the finalizer, gets a `Write` grant scoped to
  `.respec-ai/plans/*/phases/*/implementation.md`.
- Each writes its `implementation.md` draft there directly.
- `implementation.md` has no MCP home, because it is not a `DocumentType` (F29). The report format
  carries no document bodies, so the orchestrator's context stays light (README "Shared contracts →
  Agents and modes").

**Rejected:**
1. *The report carries the body,* in an extra section, as Step 12.5 does today with the whole
   document. Every draft and revision would flow through the orchestrator's context, which is what
   the relay split exists to prevent.
2. *The orchestrator writes it from the report.* Same context cost as (1), plus one more place for
   the text to be transcribed wrongly.
3. *Make `implementation.md` a `DocumentType`.* This needs a model, a parser, persistence and
   probably a migration, for a file that frozen respec-code reads raw from disk anyway (F33).
   Phase 3 adds the smaller change instead: `validate_document` accepts the body as
   `implementation_markdown`.

**Caveat (F14):** the path scope can hold only on Claude Code. opencode strips path parameters, so
the grant becomes unscoped `write`, and codex enforces no tool list. Even on Claude Code it is
unverified: commit `35a954b` found that Claude Code matches file-permission rules on `Edit(path)`
only, and the sub-agents doc never says a path inside a subagent's `tools` list narrows `Write`.
Phase 2's manual check M7 settles it and records the result here. On those TUIs, "write only
`implementation.md`" is enforced by the prompt alone. That is a least-privilege regression for an
otherwise read-only agent. If phase 2 judges it unacceptable, fall back to (2) and accept the
context cost.
