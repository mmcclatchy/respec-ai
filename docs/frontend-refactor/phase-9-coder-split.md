# Phase 9 — Split the coder (frontend / backend)

**Depends on:** Phase 1 (extension map for Step classification) and Phase 4 (UX Contract as frontend
coder guidance). **Blocks:** nothing.
**Risk:** moderate. The extraction itself is mechanical; the orchestration change is where mistakes
hide.

## Start here

**Prerequisites:** Phase 1 complete (`grep -rn "LanguageMaterializer" src/utils/`) and Phase 4 complete
(`grep -n "UX Contract" src/platform/templates/agents/phase_architect.py`).

**Already done?** `ls src/platform/templates/agents/coder_contracts.py` — file exists means complete.

**Read first:** [README.md](README.md), `docs/phase-refactor/testing.md`, `CLAUDE.md`,
`docs/AGENT_DEVELOPMENT_GUIDELINES.md` (this phase adds an agent and restructures another), and
[findings.md](findings.md) **F33**–**F36**. In [decisions.md](decisions.md) read *"Two coders, not one
overloaded coder"* and *"Coordination is design-time, not runtime"*.

**First action:** read `coder.py` end to end — all 648 lines — and mark which sections are *contract*
(true for any coder) and which are *domain* (backend-specific). That partition is the entire phase, and
doing it on paper before touching code prevents the common failure where "shared" quietly accumulates
backend assumptions.

**This phase is worth doing even without frontend work.** Extracting `coder_contracts.py` improves a
648-line template that already carries a `standards-only` mode branch. Frontend is the forcing function,
not the sole benefit.

**Two judgment calls no test will catch:**

1. **Where contract ends and domain begins.** The TDD cycle is shared. "Run the configured test command"
   is shared. "A component test asserts rendered output for each required state" is domain. The
   discriminating question: *would this sentence still be true and useful for a Go CLI coder?* If yes,
   it is contract.
2. **How much the frontend coder should say about component testing.** Too little and it reverts to
   generic TDD prose that adds nothing; too much and you have rebuilt the monolith in a new file. The
   ~250-line ceiling in the exit criteria is a forcing constraint, not a target.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Two focused coder agents sharing a contract, dispatched per implementation.md Step, so neither carries
instructions irrelevant to its work.

## Why split rather than add a mode

`coder.py` is 648 lines and already branches on `mode` for standards-only (`:51-65`). A frontend branch
makes three paths through one template that is regenerated for three TUIs — exactly the instructional
overload that makes agent behavior unpredictable and templates unmaintainable.

The reviewers solved this already (**F34**): `reviewer_contracts.py` is 84 lines of shared renderers and
each reviewer is thin domain guidance composed on top. `coder.py` has no equivalent, so its TDD cycle,
filesystem boundary, todolist gate, and handoff format are all inline.

Mirror the reviewer pattern. No new machinery, and the result is smaller than what exists today.

## Why not Agent Teams

Claude Code shipped Agent Teams in v2.1.178+ — real peer messaging via `SendMessage`, a shared task
list, per-agent mailboxes (**F33**). It is the obvious thing to reach for and it is the wrong choice
here:

- **Experimental, off by default.** Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. respec-ai
  generates agents that run in other people's projects and cannot set that flag for them. Generated
  workflows that assume it fail confusingly.
- **Not declarable where respec-ai works.** *"Subagents cannot directly coordinate with other agents in
  their frontmatter definition"* — and there is no team field among supported `.claude/agents/*.md`
  keys. Teams are session-level configuration, outside respec-ai's output surface.
- **Claude Code only**, with no confirmed OpenCode or Codex equivalent. Codex already requires *bounded*
  parallelism (`codex.py:302`).

Recorded as a future capability tier in [deferred-issues.md](deferred-issues.md), following phase 8's
pattern. When teams graduate from experimental, adopting them is an adapter change plus an orchestrator
option — not a redesign.

## Why the coders do not need to talk

What two coders would negotiate is the interface between them. **The design layer already fixes it
before either runs.**

`### Skeleton Index` carries exact signatures with fully-qualified cross-module types, and
`### Collaboration And Wiring` defines ownership and construction (**F36**). Both are approved by the
human at the shape gate and materialized as skeleton files on disk. So the frontend coder does not ask
the backend coder for a response shape — it reads the same approved seam the backend coder is filling
in.

Design-time coordination beats runtime negotiation on every axis that matters here: it is deterministic
across iterations, human-approved, inspectable after the fact, and it does not require both agents to
run concurrently.

For what remains, respec-ai already has an agent→agent channel: `get_reviewer_feedback_context`
(`feedback_tools_unified.py:499-524`) curates findings through MCP shared state — durable and
inspectable rather than ephemeral. The genuine gap is mid-implementation deviation, and the handoff
report already carries a `Deviations:` field (`coder.py:568`) that reaches the other coder one iteration
later via the orchestrator. With an 8-iteration budget, that latency is affordable.

Phase 7's [seam review](phase-7-frontend-reviewer.md) is what verifies the two sides actually met.

## Dispatch: per implementation.md Step

Classify each Step by its file paths using phase 1's extension map. `STEP_MODES`
(`code_command.py:300-322`) already computes exactly this classification for reviewer rostering — reuse
it rather than adding a second decision layer.

Both coders may run in one iteration. Each returns its own iteration handoff report; the orchestrator
merges them into the single report that drives `/respec-commit` and the review cycle. A mixed phase
therefore gets the right agent for each part without either coder seeing instructions for the other's
domain.

Sequence them rather than running them concurrently: they may touch shared files (a types module, a
route table), and the fan-out policies are built for independent workers collecting into a parent
(`render_parallel_fanout_policy`), which coders are not.

## Ownership boundary — each coder fixes only what it owns

Today there is one coder, so `coder.py:403-425` tells it generically to use *"user feedback, blockers,
critical findings, key issues, and recommendations"* with a single exclusion — ignore the execution
report (**F39**). There is no notion of a finding belonging to one coder rather than another, because
there has never been more than one.

With two coders that is unsafe in both directions: a frontend coder "helpfully" editing a backend
handler produces changes nobody designed, and worse, both coders independently fixing the same seam
produces two incompatible resolutions in a single iteration.

**Consumption is prompt-level, not code-level** (**F39**) — an LLM reading markdown, not a parser. So
this is contract prose in `coder_contracts.py`, parameterized by domain, and pinned by generated-template
tests. There is no filtering layer to write.

### The contract, shared by both coders

- **Act only on findings targeting your domain.** Each finding carries exactly one `[Target:frontend]`,
  `[Target:backend]`, or `[Target:both]` tag (phase 7). Act on your own and on `both`; **ignore the
  other's entirely** — do not fix, do not comment on, do not "note for later."
- **`[Target:both]` means fix your side of it only.** Both coders receive the same seam ID. Each changes
  its own side to match the declared contract in `### Collaboration And Wiring`. Neither reaches across.
- **An untagged finding is not yours by default.** Report it in the handoff report as unroutable rather
  than assuming ownership. Silent adoption is how both coders end up fixing the same thing.
- **File boundary, enforced like the existing filesystem restriction.** Write and edit only files in
  your domain, as classified by the extension map. Encountering a needed change on the other side is a
  handoff-report entry, never an edit.
- **Conflict with the design contract is a `DOCUMENT_AMENDMENT_REQUIRED` handoff**, not a unilateral
  fix. If honoring a finding would require changing a seam declared in `### Collaboration And Wiring`,
  that is a design change and the human owns it — the existing mechanism at `coder.py:90-96` already
  covers this.

Write it in the same register as the existing `MANDATORY FILESYSTEM BOUNDARY RESTRICTION`
(`coder.py:79-101`), with an explicit `VIOLATION:` clause. That block is already the strongest boundary
statement in the template and the coders respect it; this is the same kind of rule.

### Auditing the existing backend coder

Before writing the frontend coder, **read `coder.py:403-425` and confirm what the backend coder will
now over-reach on.** Today it correctly acts on everything, because everything is its responsibility.
After the split, that same instruction makes it act on frontend findings too. The change is not additive
— existing prose becomes wrong and must be narrowed, not merely supplemented.

Check the same for the standards-only mode (`:51-65`), which instructs *"Fix ONLY the issues identified
in the curated reviewer context"* — correct today, but the curated context will contain both domains'
findings once phase 7 tags them.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A backend-only phase produces behavior identical to today's single coder |
| B2 | A frontend-only phase dispatches only the frontend coder |
| B3 | A mixed phase routes each Step to the right coder within one iteration |
| B4 | Both handoff reports merge into one report with no lost fields |
| B5 | A merged report drives `/respec-commit` exactly as a single report does |
| B6 | Both coders emit the same handoff format — asserted against the shared renderer, not duplicated fixtures |
| B7 | `respec-ai regenerate` succeeds for all three TUIs with both coders registered |
| B8 | Neither coder template exceeds ~250 lines of domain content |
| B9 | A `[Target:backend]` finding produces no frontend file changes, and vice versa |
| B10 | A `[Target:both]` finding has each coder change only its own side |
| B11 | An untagged finding is reported as unroutable rather than silently adopted |
| B12 | A finding requiring a `### Collaboration And Wiring` change yields `DOCUMENT_AMENDMENT_REQUIRED`, not an edit |

**B1 is the regression guard** — most existing users are backend-only and must see no change. **B6** is
what keeps the two from drifting apart later. **B9–B12 are the ownership boundary**; they are the
behaviors most likely to regress silently, because an over-reaching coder produces working code that
simply wasn't anyone's design.

## Scope

**`src/platform/templates/agents/coder_contracts.py`** (new), modeled on `reviewer_contracts.py`.
Shared renderers for: the tool-invocation preamble, the filesystem boundary restriction, the mandatory
todolist gate, the TDD cycle and its violation safeguards, feedback integration and blocking-issue
resolution, the **ownership boundary** (parameterized by domain — see above), the iteration strategy,
and the iteration handoff output format.

**`src/platform/templates/agents/coder.py`** — reduced to backend domain guidance plus composition.
Keeps the `standards-only` mode, which is domain-neutral and applies to both coders (decide during
implementation whether it belongs in contracts).

**`src/platform/templates/agents/frontend_coder.py`** (new) — frontend domain guidance: component-level
work units, what a component test asserts, the required states from the UX Contract, accessibility as a
build-time concern rather than a review-time surprise, and the language sentinel from phase 1's
materializer rather than `raise NotImplementedError` (**F9**).

**`src/platform/models/code.py`** — `FrontendCoderAgentTools`, mirroring `CoderAgentTools:144-171`. Same
grants: `WRITE/EDIT/READ/GLOB/BASH/TODO_WRITE` and the three read-only MCP tools.

**`src/platform/template_helpers.py`** — factory for the new agent.

**Registration** — `templates/agents/__init__.py`, `template_generator.py` (`_AGENT_NAMES:86-104` and
the spec list at `:240-272`).

**`src/platform/templates/commands/code_command.py`** and **`patch_command.py`** — per-Step dispatch and
handoff merging, plus **finding routing**: the same `[Target:...]` tag that phase 7 emits determines
which coder receives which findings next iteration. Step dispatch and finding routing are the same
mechanism applied to different inputs; implement them together so they cannot drift.

**Test counts** — `tests/unit/templates/test_template_generator.py`, and adapter-derived counts if phase
8 has landed (**F30**).

## Out of scope

- **Agent Teams.** Deferred; see above and [deferred-issues.md](deferred-issues.md).
- **Any change to reviewer write permissions.** Reviewers stay read-only, reporting exclusively through
  `store_reviewer_result`. That is already correct.
- **Component preview generation.** Decided separately once the frontend coder exists and it is clear
  what falls out of its normal work naturally.
- **Splitting any other agent.** The reviewers are already correctly factored.
- **Changing the design contract.** `### Skeleton Index` and `### Collaboration And Wiring` are the
  coordination mechanism and need no modification for this phase.

## Exit criteria

- B1–B8 green.
- **A real mixed phase**, end to end: an API endpoint plus the component that calls it. Each Step routes
  correctly, both handoff reports merge, the commit contains both sides, and the review cycle runs
  normally.
- **A real backend-only phase** behaves identically to before the split — run one and compare.
- **The partition holds:** read `coder_contracts.py` and confirm nothing in it is backend-specific. Ask
  the discriminating question of each section — *would this still be true for a Go CLI coder?*
- **Ownership holds under adversarial input.** Hand the frontend coder a review cycle whose findings are
  mostly `[Target:backend]`, including one that is tempting and trivially fixable. Confirm it changes no
  backend file and mentions the finding nowhere but the handoff report. This is a judgment behavior, not
  a mechanical one — verify it on real output, not only in a fixture.
- Neither coder template exceeds ~250 lines of domain content. If one does, the partition is wrong.
- `respec-ai regenerate` clean for all three TUIs; `uv run pytest` clean.
