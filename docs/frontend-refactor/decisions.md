# Decision log

Rationale for the design positions in the frontend refactor, including the rejected alternatives.
Four of these changed during design; those are marked **(revised)** with the original position,
because the reasoning that moved them is the part most likely to be lost.

Read this before re-opening a settled question.

---

## The materializer gets a language seam, not a Python guard **(revised)**

**Rejected:** guard `skeleton_generator` to skip non-`.py` paths, reporting them as unmaterialized.

**Why:** it entrenches exactly the assumption the project is trying to remove — Python as the
privileged language, everything else as second-class. And because frontend code is essentially never
Python, a Python-only materializer means frontend work permanently bypasses the design → skeleton →
TDD-red spine that is respec-ai's central mechanism. The guard would have made the corruption visible
without making the feature possible.

**Originally:** the guard was proposed as a cheap correctness fix (stop writing Python into `.tsx`)
with a real materializer deferred. The scope looked smaller because the seam looked bigger than it
is — see [the extensibility lever](README.md#the-extensibility-lever) for why most languages are
cheap once the protocol exists.

**Still true from the original position:** silent skip is itself a bug. The Test List would promise
tests the coder is instructed to build against that were never created. Whatever cannot be
materialized must be reported, not dropped.

---

## Introspection is an optional capability, not a required protocol method

**Rejected:** require every `LanguageMaterializer` to implement `extract_existing_signatures`.

**Why:** the four capabilities a language needs have wildly different costs (F21). Rendering test
scaffolds is nearly free — `language_standards.json` already carries `testing.framework`,
`.location`, and `.naming` for all 26 languages. Rendering declarations is a small template. Parsing
the Skeleton Index grammar is one regex per language. But **introspecting existing source files** is
genuinely expensive: Python has stdlib `ast`; TypeScript, Go, and Rust each need an external parser
or hand-written heuristics.

Requiring introspection makes the expensive capability the gate on the cheap ones, so adding a
language becomes a project rather than a contribution. Making it optional means a new language needs
only the two cheap capabilities to be first-class for *new* code, with merge-into-existing-file as an
independent later upgrade.

**Consequence to accept:** languages without introspection degrade to create-only and cannot
participate in signature reconciliation. That degradation must be surfaced to the user, never silent.

---

## Scope is Python + TypeScript, with the seam built for many

**Why TypeScript second rather than Go or Rust:** it is the language most likely to *lack* cheap
introspection, so implementing it proves the optional-capability seam under real load instead of
leaving it hypothetical. A second language that happened to have an easy parser would validate
nothing about the split.

**Why not more now:** the remaining languages are cheap to add *once the seam exists* (F21), and none
of them are frontend work. Adding them before the seam is proven risks doing it twice.

**The standing requirement:** any design decision that would make a future language second-class
should be reconsidered on the spot. If treating it first-class is minimal or moderate extra effort,
do it. If significant, record the reason in [deferred-issues.md](deferred-issues.md) rather than
letting the shortcut go unremarked.

---

## Language resolves from the extension map, not `stack.toml` — until phase 3

**Rejected:** resolve language from `stack.toml` in phase 1, where the materializer is built.

**Why:** the per-language tables in `stack.toml` are empty for the non-primary language until phase 3
lands (F2). For a Python+React project, phase 1 would consult a `stack.toml` that says the project is
Python and resolve the TypeScript entries as Python — reintroducing the exact corruption the phase
exists to fix. The dependency is inverted.

The extension map is sufficient for per-entry dispatch, is built in phase 1 anyway, and has no such
dependency. `stack.toml` consultation is added in phase 3, once the tables it reads are populated,
and phase 3's exit criteria assert both paths agree.

---

## The UX Contract lives under `### Design Shape - Additional Sections` **(revised)**

**Rejected:** a standalone `## UX Contract` H2 via the `additional_sections` dict.

**Why:** both routes are zero-code and both round-trip, but shape mode is explicitly forbidden from
writing standalone domain H2s — `phase_architect.py:463-469` reserves those for the detail act (F15).
A `## UX Contract` written in shape mode is out of contract and can be dropped by the detail-act
expansion, and `find_content_loss` warns on orphan H3s but would not catch a dropped H2. The failure
would be silent.

`### Design Shape - Additional Sections` is shape mode's own territory, sits *inside* the design
contract where a UX contract belongs semantically, and is reviewed at the existing shape gates.

**Originally:** the `additional_sections` H2 was chosen because `phase_architect.py:63-70` already
seeds domain H2s that way (`API Design`, `Data Models`). That seeding happens in the **detail act**,
which is why it does not license shape-mode use.

**Not chosen:** a first-class `### UX Contract` field on the `Phase` model. It costs a Pydantic field,
a `HEADER_FIELD_MAPPING` entry, a `build_markdown` branch, a DB migration across both state managers,
the F13 positional-UPSERT hazard from
[`docs/phase-refactor/phase-2-design-layer.md:44-56`](../phase-refactor/phase-2-design-layer.md), and
five prompt edits — and buys nothing `additional_sections` does not already provide, since no section
is ever code-required anyway (F16). Revisit only if the runtime reviewer proves the section
load-bearing.

---

## No new human gate for the UX Contract

**Rejected:** a dedicated approval gate for the visual/UX design.

**Why:** the contract is authored in shape mode and therefore already passes through Human Gate 1a
(`phase_command.py:471-521`) and the joint gate 1b (`:620-678`). A separate gate would add a stop
without adding a decision. The existing gates are where the user edits the phase document directly,
which is exactly the interaction a UX contract needs.

---

## The frontend reviewer is replaced, not extended **(revised)**

**Rejected:** keep the existing `frontend-reviewer` and add a separate runtime reviewer alongside it.

**Why:** the existing reviewer is a placeholder that was never intended for use in its current form.
Building around it would mean carrying a rubric nobody believes in and splitting frontend review
across two agents for no reason other than the placeholder's existence. One reviewer whose evidence
is both source and the rendered page is the coherent design.

**Originally:** a static/runtime pair was proposed on the assumption the static reviewer was
load-bearing, with the split justified by incompatible contracts (long-running server, browser
driving, scratch writes). That justification dissolved twice over — the placeholder is not worth
preserving, and F19 shows the write conflict was mostly illusory.

**Preserved from the original position:** availability. The reviewer must still function when no
browser is available, running on source evidence alone and reporting runtime as skipped context.
That is now a mode of one agent rather than a second agent.

---

## Degradation is a preflight gate in roster resolution, not an in-agent bail-out

**Rejected:** let the reviewer start, discover no dev server, and decline to store a result.

**Why:** `consolidate_review_cycle` hard-fails on a rostered reviewer with no stored result (F10) —
it does not drop out, it terminates the workflow. And it cannot report the problem as a blocker,
because `_validate_reviewer_blockers` rejects execution-report content in blockers.

Clean split: **infrastructure** failure means not on the roster; **UX-contract** failure means a
blocker. The preflight runs before invocation and decides which.

---

## Runtime evidence drives the loop through blockers; the score is secondary **(revised)**

**Rejected — and inverted:** weight deterministic signals heavily "so aesthetic variance does not
thrash `_detect_stagnation`."

**Why the original diagnosis was backwards:** at a ~7.5/100 relative weight (F11), nothing this
reviewer says can thrash the composite — variance moves it by fractions of a point. The risk was never
instability; it was **impotence**. Score was the wrong lever entirely.

`decide_next_loop_action` requires `score >= threshold AND not latest_blockers` (F12), and blockers
propagate regardless of weight. So hard pass/fail conditions on the UX Contract emit blockers, and
those are what drive REFINE.

**Corollary that must be in the agent contract, not just the rubric:** because bare `[Severity:P0]`
text markers are picked up as blockers (F12), a single subjective P0 blocks completion no matter what
the score says. Only flow failure, an accessibility violation at or above the configured level, or a
console/network error may be P0. Visual fit is capped at P2 by contract.

---

## Domain weights scale with phase shape **(revised)**

**Rejected:** keep the fixed 15-point domain pool and rely entirely on blockers.

**Why:** blockers alone make the score a poor signal of frontend quality — a phase whose entire point
is the UI scores it at ~7.5/100 (F11). Sizing the pool by what the phase is actually about fixes the
root cause instead of routing around it, and it makes the reviewer's score meaningful rather than
decorative. Blockers remain the hard gate either way.

**Also rejected:** adding the frontend reviewer as a fifth member of the fixed pool. That dilutes
backend/database/infrastructure weights in existing projects for no gain.

**Also rejected:** per-phase configurable weights. Most control, but another thing to author per
phase, and a wrong setting silently skews every review with no signal that it happened.

**The load-bearing constraint:** domain shares are computed from the **Phase design** — Skeleton
Index, Module Layout, UX Contract presence — not from per-iteration changed files.
`_detect_stagnation` compares score deltas across iterations; if weights shift because the changed-file
mix shifted, a score drop is indistinguishable from a weighting artifact and stagnation detection
breaks. Design-derived shares stay stable for the whole loop while still reflecting composition.

**Bounds:** pool floor stays 15 so a backend-only phase is numerically identical to today (assert this
by test, do not assume it); ceiling around 35 so core reviewers keep the majority — AQC,
spec-alignment, and code-quality apply to frontend code too, and a frontend phase must not stop caring
whether the tests pass.

---

## `design-conformance-reviewer` is core-tier and domain-neutral

**Why core rather than pooled:** it stores with `max_score='50'` (F1). Only AQC and spec-alignment are
50; every domain specialist is 25. Pooling a 50-point reviewer would make it worth ~5 points of
composite, which is clearly not the intent encoded in its max score. Adding it to
`_phase1_core_weights` at 20 — rebalancing spec-alignment 35→30 and code-quality 25→20 — keeps core at
85 and the pool at 15.

**Why domain-neutral:** it checks conformance to the approved design contract, which pure-backend
phases have as much as frontend ones. It stays gated on `has_skeleton_index`, not on frontend
presence. When a phase has no Skeleton Index it is simply not rostered and its weight renormalizes
away (F11).

---

## Long-running processes go through a CLI subcommand, not background-shell tools

**Rejected:** grant the reviewer `BASH_OUTPUT` / `KILL_SHELL` to manage a dev server directly.

**Why:** `opencode.py:36-37` maps both to `None` and `TemplateToolBuilder.build()` **raises
`ValueError`** on `None` (F17). Using either breaks `respec-ai regenerate` for OpenCode outright —
not a degradation, a hard failure. A `respec-ai frontend-preflight` subcommand invoked with plain
`BASH` is portable across all three TUIs and keeps process lifecycle in tested Python rather than in
prompt text.

---

## Score on accessibility snapshots, not screenshots

**Why:** `review_model` is hardcoded to `sonnet` only in Claude Code; OpenCode and Codex resolve it
from user config with no vision guarantee (F18). Anything that carries score must work when the review
model cannot see images.

`browser_snapshot` returns the accessibility tree as text — structured, cheap, diffable across
iterations, and model-agnostic. Screenshots remain useful as optional evidence for the small
subjective slice, and are Claude-Code-preferred rather than required.

---

## The reviewer gets no write grant

**Why:** the conflict turned out to be mostly illusory (F19). Snapshots, console messages, and network
requests return inline text; axe-core injected via `browser_evaluate` returns JSON inline. Screenshots
and traces are written by the **MCP server** into its `--output-dir`, not by the agent.

So rather than a general scratch-dir write carve-out, the contract needs one narrow clause: artifacts
the MCP server wrote into the run scratch directory are citable evidence the agent must not author or
write into itself.

**Implementation note:** add a *sibling* to `render_reviewer_output_contract` rather than
parameterizing it. That renderer is shared by every reviewer; parameterizing changes the generated
text of all of them and breaks their tests for no benefit.

---

## Claude Design is wired for Claude Code, on top of a portable seam **(revised)**

**Rejected:** capability parity — hold every TUI to what all three can do, and treat Claude Design as
documentation only.

**Why:** parity caps the best TUI at the level of the weakest. OpenCode and Codex have nothing like
Claude Design, and refusing to wire it means Claude Code users lose real capability purely to preserve
symmetry. The right model is **tiered capability**: a portable core every TUI gets, plus per-TUI
extensions layered on top.

**Originally:** Claude Design was to be documentation only — export a handoff bundle, name the path,
done — on the grounds that `DesignSync` is Claude-Code-only and interactively authenticated, so wiring
it would break portability. The premise was right; the conclusion did not follow. Portability means the
*core* must work everywhere, not that no TUI may exceed it.

**What this looks like in practice — two layers:**

- **Portable seam (all TUIs, phase 4):** `##### Design Source` in the UX Contract names a local
  handoff bundle, tokens file, or components to match. Read with `Read`. Everything downstream behaves
  identically whether the design came from Claude Design, a Figma export, or a hand-written token file.
- **Claude Code extension (phase 8):** a `/respec-design-sync` command that pushes the project's
  component library up to a Claude Design project, and the ability for `##### Design Source` to name a
  live project that the architect reads via `DesignSync`.

**The property preserved from the original position:** the portable seam is the load-bearing one, and it
must stay sufficient on its own. Phase 8 may make Claude Code better; it may not make the other TUIs
worse, and no phase-4 behavior may come to depend on it.

**Extension-open, not extension-complete.** Other TUIs get the capability declaration point and nothing
else. When one ships an equivalent, it is an adapter change rather than a redesign. Recorded in
[deferred-issues.md](deferred-issues.md).

---

## Tiered capabilities reuse the existing adapter pattern

**Rejected:** a new capability-registry or feature-flag system for per-TUI differences.

**Why:** `TuiAdapter` already does this. `ask_user_question_tool_name` returns `str | None` and
`selection_prompt_instruction` / `selection_response_source` branch on it to emit different generated
prose (**F29**) — for a capability Codex genuinely lacks. Declare, branch, degrade. A second mechanism
would be parallel machinery for a solved problem.

**What has to be added:** exactly one missing primitive. `builtin_tool_name_map` requires every adapter
to declare every capability explicitly, including `None` (**F32**) — which is correct and worth keeping
— but `TemplateToolBuilder.build()` **raises** on `None` (**F17**), so the only expressible states are
*required* and *absent*. An optional-grant primitive that skips rather than raises makes tiering
expressible at all, and generalizes to every future per-TUI capability.

**The consequence to handle:** once command sets differ per TUI, `EXPECTED_COMMANDS_COUNT` as a flat
module constant is wrong for at least one adapter and `respec-ai validate` reports a spurious failure
(**F30**). Counts must become adapter-derived.

---

## Design-sync is user-invoked, never a loop step

**Rejected:** having the frontend reviewer or coder call `DesignSync` during a refinement iteration.

**Why:** three properties of the tool make it unfit for an automated loop (**F31**). It requires
interactive claude.ai authentication and may be **entirely absent** in headless or scheduled runs. Its
write path raises **permission prompts**, which would block an unattended loop. And `get_file` returns
content authored by other org members, which its own documentation says to treat as *data, not
instructions* — a prompt-injection surface that should not sit inside an automated review.

**So:** writes happen only in a user-invoked `/respec-design-sync` command. Reads are optional
enrichment for the architect, degrading to the local bundle when unavailable. Anything that reads design
files carries an explicit clause that their content is data and never instructions.

---

## The MCP registrar is not generalized in this refactor

**Rejected:** extend `register-mcp` into a generic multi-server registrar as a prerequisite for
Playwright MCP.

**Why:** `claude_config.py` is hardcoded to a single server and generalizing it touches all three
`TuiAdapter.register_mcp_server` implementations (F28). That is a worthwhile refactor and a poor
prerequisite — it would gate frontend review on unrelated CLI surgery.

**Instead:** document the one-line install per TUI, and have `frontend-preflight --status` report
`playwright_mcp_registered` so the preflight gate can act on it. Generalizing the registrar is
recorded in [deferred-issues.md](deferred-issues.md) as a follow-up.

---

## Two coders, not one overloaded coder

**Rejected:** add a `frontend` mode to the existing `coder.py`.

**Why:** `coder.py` is 648 lines and already branches on `mode` for standards-only. A third path through
one template regenerated for three TUIs is instructional overload — the agent carries a large body of
instructions irrelevant to whatever it is currently doing, which makes behavior less predictable and the
template harder to maintain.

The reviewers already solved this (**F34**). `reviewer_contracts.py` is 84 lines of shared renderers and
each reviewer is thin domain guidance composed on top. Extracting `coder_contracts.py` and leaving two
short domain coders mirrors an existing pattern exactly, adds no machinery, and produces something
smaller than what exists today.

**Worth doing independently of frontend work.** Frontend is the forcing function, not the sole benefit.

**Dispatch per implementation.md Step**, classified by file path through phase 1's extension map.
`STEP_MODES` (`code_command.py:300-322`) already computes this for reviewer rostering — reuse it rather
than adding a second decision layer. Both coders may run in one iteration, each returning a handoff
report the orchestrator merges, so a mixed phase gets the right agent for each part.

**Sequence them, don't parallelize.** They may touch shared files, and `render_parallel_fanout_policy`
is built for independent workers collecting into a parent — which coders are not.

---

## Coordination is design-time, not runtime **(revised)**

**Rejected:** Agent Teams — peer messaging between a frontend coder and a backend coder while they work.

**Why not, mechanically:** teams are real and shipped in Claude Code v2.1.178+ (`SendMessage`, shared
task list, mailboxes), but they are unusable as respec-ai's substrate (**F33**). They are experimental
and require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, which respec-ai cannot set in a user's project.
There is no team field among supported `.claude/agents/*.md` frontmatter keys — the docs state that
subagents cannot coordinate via their frontmatter definition at all. And they are Claude Code only, with
no confirmed OpenCode or Codex equivalent.

**Why not, architecturally — the more durable reason:** what two coders would negotiate is the interface
between them, and **the design layer already fixes it before either runs.** `### Skeleton Index` carries
exact signatures with fully-qualified cross-module types; `### Collaboration And Wiring` defines
ownership and construction (**F36**). Both are human-approved at the shape gate and materialized as
skeleton files. The frontend coder reads the same approved seam the backend coder is filling in.

Design-time coordination is better than runtime negotiation here on every axis: deterministic across
iterations, human-approved, inspectable after the fact, and it does not require both agents to run
concurrently. Runtime messaging would let two agents renegotiate a contract the human already approved —
which is the opposite of what the shape gate is for.

**Originally:** this was framed as "peer communication doesn't exist, so orchestrator-mediated is the
only option." That premise turned out to be wrong — it does exist. The conclusion survives on the
architectural argument alone, which is the stronger one.

**What covers the remainder.** `get_reviewer_feedback_context` (`feedback_tools_unified.py:499-524`)
already curates findings between agents through MCP shared state — durable and inspectable rather than
ephemeral. Mid-implementation deviation reaches the other coder one iteration later via the handoff
report's `Deviations:` field (`coder.py:568`); with an 8-iteration budget that is affordable. And phase
7's seam review verifies empirically that the two sides met.

Recorded as a future capability tier in [deferred-issues.md](deferred-issues.md), following the phase-8
pattern.

---

## Seam review belongs to the frontend reviewer

**Rejected:** a separate integration reviewer, or leaving cross-boundary verification to
`design-conformance-reviewer`.

**Why the frontend reviewer:** it is the only agent with runtime evidence. `browser_network_requests`
yields real request/response pairs, so seam review can be empirical — *"the form called
`POST /api/session`, got 200, and the response matched what the component destructures"* — rather than a
static type comparison.

**Why not design-conformance:** it asks whether each module matches its *declared signature*, per module,
statically. In a `display_name` / `displayName` mismatch, **both sides individually conform**. The defect
exists only *between* them, which per-module conformance structurally cannot see. Stating this boundary
in the phase doc is necessary or three reviewers will report the same thing three ways.

**Findings need a routing target.** With two coders, `(priority, feedback)` is unactionable for a
cross-boundary finding (**F35**) — it must name which side changes. Extending the existing text-parsed
tag convention with `[Target:frontend|backend|both]` requires no schema change or migration, and a
`both` finding carries the same seam ID to both coders so they converge on one resolution instead of
colliding.

**Seams come from `### Collaboration And Wiring`** (**F36**), not from the reviewer's own inference — it
is human-approved and already what both sides implement against. A call observed at runtime but absent
from that section is an *undeclared seam*, which blocks: that is exactly the class of problem the design
gate exists to prevent.

---

## Reviewer markdown is audit evidence; structured fields are the channel

**Rejected:** describing seam problems in a `#### Seam Review` markdown block and expecting the coder to
act on them.

**Why:** `consolidate_review_cycle` (`feedback_tools_unified.py:351-365`) reads **only** structured
`blockers`/`findings` and never touches `feedback_markdown` (**F37**). A problem described only in prose
affects nothing — not the score, not the blocker gate, not the coder. And `get_reviewer_feedback_context`
filters markdown through an **exact-lowercase heading allowlist** (`:579-585`), so a non-allowlisted
section is silently absent from the coder's curated context.

**So:** every actionable seam item is a structured finding or blocker. The markdown block is the
declared-vs-observed detail a human (or the coder, via `get_reviewer_result`) can read for context.

**Placement rules, forced by two non-raising heuristics (F37):** H4, before the execution report; never
`#####` after the execution report (silently deleted); never the execution-report marker string in prose
(substring-matched on every line, sets `heading_level = 6`, eats to the next heading).

**Not chosen:** naming the section `#### Findings` or `#### Required Corrections`. Both are unused
allowlist slots and would be coder-visible with zero code change — but `findings` collides conceptually
with the structured `findings` field and would confuse reviewer authors and coders alike. Spend one line
adding `'seam review'` to the allowlist and leave the reserved slots free.

---

## Structural validation belongs in a field validator, not `ConfigDict`

**Rejected:** `ConfigDict(extra='forbid')` or similar to catch malformed reviewer markdown.

**Why:** `ConfigDict` governs model *fields*. `feedback_markdown` is a single `str`, and Pydantic has no
visibility into heading structure inside a string value. The correct mechanism is a
`@field_validator('feedback_markdown')` on `ReviewerResult` — matching the validators already there for
`score`, `max_score`, and `blockers` (`src/models/feedback.py:209-231`).

**Scope it narrowly.** Reject only unambiguous structural errors: an `#` or `##` heading (breaks nesting
under the container formats), more than one `###`, an `#####` after the execution report, the marker
string in prose, or a missing required H4.

**Do not validate H4 names against the allowlist.** Rubric-category H4s legitimately are not in it — they
are scoring detail and correctly audit-only. A validator cannot infer intent, and rejecting them would
break all nine reviewers.

**The fail-closed hazard is why narrowness matters.** A validation failure means the reviewer cannot
store, `consolidate_review_cycle` hard-fails on the missing submission (**F10**), and the workflow
terminates — and the MCP retry contract forbids retrying deterministic validation errors. A cosmetic
markdown issue must never become a workflow termination.

**Most of the value is at build time.** Pair the validator with a test asserting every reviewer
template's example markdown passes it. That catches authoring drift before shipping; the runtime
validator is only the backstop.

---

## Coders act only on findings they own

**Rejected:** leaving `coder.py:403-425`'s generic *"use blockers, findings, key issues, and
recommendations"* instruction unchanged after the split.

**Why:** that instruction is correct today precisely because there is one coder and everything is its
responsibility (**F39**). After the split the same words make each coder act on the other's findings.
This is not an additive change — **existing prose becomes wrong and must be narrowed.**

Two failure modes, and the second is worse: a frontend coder editing a backend handler produces changes
nobody designed; both coders independently fixing the same seam produce two incompatible resolutions in
one iteration.

**The rule:** act on `[Target:<your domain>]` and `[Target:both]`; ignore the other's entirely — no fix,
no comment, no "noted for later." `both` means fix *your side* to match the declared contract. An
untagged finding is not yours by default; report it as unroutable rather than adopting it silently.

**Enforcement is prose, not code.** Consumption is prompt-level — an LLM reading markdown, not a parser
(**F39**) — so this lives in `coder_contracts.py` in the register of the existing
`MANDATORY FILESYSTEM BOUNDARY RESTRICTION` (`coder.py:79-101`), with an explicit `VIOLATION:` clause,
and is pinned by generated-template tests.

**Escalation, not unilateral repair:** if honoring a finding would require changing a seam declared in
`### Collaboration And Wiring`, that is a design change the human owns — `DOCUMENT_AMENDMENT_REQUIRED`
via the existing mechanism at `coder.py:90-96`.

---

## Python is invisible to the user

Not a trade-off so much as an acceptance criterion, recorded here because several findings are
violations of it rather than ordinary bugs.

respec-ai is written in Python and its MCP server runs Python; neither fact may reach the user. The
user's contact surface is the CLI, the generated agent-definition markdown, `.respec-ai/config/stack.toml`,
and the per-language standards TOMLs. Nothing in that surface should imply a language for either
respec-ai or the user's project.

Violations to fix, in severity order: Python source emitted into non-Python files (F4); Python
tracebacks as user-facing diagnostics (F6 — `phase_command.py:701` fail-closes and shows a stack trace
as the explanation); Python-shaped contract grammar visible in the Phase document the user approves
(F5, F8); Python-flavored defaults such as `uv run` prefixes and Python-only type-checker options
offered to any language (F25).

Every failure introduced by this refactor must produce a clean CLI message naming the file and the
reason. Internal exception types stay internal.
