# Phase 7 — The frontend reviewer

**Depends on:** Phases 4 and 5. Phase 6 is not a hard dependency but makes this reviewer's score
meaningful rather than decorative.
**Risk:** highest uncertainty in the refactor. Most expensive, least mechanical, and the one whose
success depends on the quality of an artifact produced elsewhere.

## Start here

**Prerequisites:** Phase 4 complete (`grep -n "UX Contract" src/platform/templates/agents/phase_architect.py`)
and Phase 5 complete (`ls src/cli/commands/frontend_preflight.py`). Phase 6 strongly recommended first.

**Already done?** `grep -n "browser_tools" src/platform/models/code.py` — output means complete.

**Read first:** [README.md](README.md), `docs/phase-refactor/testing.md`, `CLAUDE.md`,
`docs/AGENT_DEVELOPMENT_GUIDELINES.md` (the whole thing — this phase adds an agent), and
[findings.md](findings.md) **F10**, **F12**, **F13**, **F18**, **F19**, **F20**. In
[decisions.md](decisions.md) read *"The frontend reviewer is replaced, not extended"*, *"Degradation is
a preflight gate"*, *"Runtime evidence drives the loop through blockers"*, *"Score on accessibility
snapshots, not screenshots"*, and *"The reviewer gets no write grant"* — four of the five were
reversals.

The 10-step *"Adding a New Reviewer"* checklist at `docs/AGENT_DEVELOPMENT_GUIDELINES.md:1767-1778` is
the procedure to follow.

**First action:** run phase 5's preflight by hand against your test project, then drive the browser
manually through one Interaction Flow from a real UX Contract — before writing any agent template. You
need to know what the evidence actually looks like, and whether a flow's pass condition is checkable as
written, before encoding either into a prompt.

**The existing `frontend-reviewer` is a placeholder being replaced, not extended.** Its 25-point rubric
scores UI by reading source files and was never intended for use in its current form. Do not preserve
its structure out of caution.

**Two judgment calls, both consequential:**

1. **Which findings may block.** The rubric below assigns this, but you will meet cases it does not
   cover. The test: could a second reviewer, given the same UX Contract and the same page, mechanically
   reach the same verdict? If not, it is not a blocker.
2. **How much exploratory browsing to do beyond the contract.** Some real defects are not in any flow.
   But a reviewer that ranges freely produces findings the user never agreed to be judged against, and
   `[Severity:P0]` text markers are picked up as blockers regardless of source (**F12**). Lean toward the
   contract; report the rest as observations, not blockers.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

One frontend reviewer whose evidence is **both** source and the rendered page, scoring conformance
against the UX Contract, driving the loop through blockers that each trace to a line the human approved
at Gate 1a.

## Degradation is a roster gate, not an in-agent bail-out

This is the constraint that shapes the phase, and the intuitive design is wrong.

`consolidate_review_cycle` **hard-fails** on a rostered reviewer with no stored result
(`feedback_tools_unified.py:336-339`). A reviewer that starts, finds no dev server, and declines to
store does not drop out — it detonates the workflow through `code_command.py:560-600`'s bounded-recovery
path to `EXIT: Workflow terminated`. It also cannot report the problem as a blocker, because
`_validate_reviewer_blockers` (`:704-728`) rejects blockers containing execution-report markers
(**F10**).

**Therefore:**

- The reviewer is **rostered** whenever `"frontend" in STEP_MODES` — which, after phase 1, is derived
  from the extension map rather than a hardcoded list (**F14**).
- **Runtime evidence is gated separately**, on `frontend-preflight --start` reporting ready. When the
  browser is unavailable the reviewer still runs, on source evidence alone, and reports runtime as
  skipped context.

So it never fails by being absent. Infrastructure failure degrades the *evidence*; it does not remove
the *reviewer*.

## Never reuse sign-off

`code_command.py:514-526` asks the orchestrator to invalidate a signed-off reviewer when changes "touch
that reviewer's responsibility." Tractable for a source reviewer. For one whose input is the rendered
application, transitive changes — a shared token, a component, an API response shape — will be missed
and a stale pass verdict reused (**F13**).

**This reviewer must never enter `PHASE1_SIGNED_OFF_REVIEWERS`.** It re-runs every iteration. The cost is
one reviewer run per iteration; the alternative is reporting COMPLETED on a visibly broken UI, which is
the worst failure this refactor could produce.

## Evidence: snapshots, not screenshots

`review_model` is hardcoded to `sonnet` only in Claude Code (`claude_code.py:134-135`); `opencode.py:129`
and `codex.py:205` resolve it from **user config** with no vision guarantee (**F18**). Anything carrying
score must work when the review model cannot see images.

`browser_snapshot` returns the accessibility tree as text — structured, cheap, diffable across
iterations, model-agnostic. That is the deterministic substrate. Screenshots remain useful for the small
subjective slice and are Claude-Code-preferred, never required.

Convenient consequence (**F19**): snapshots, console messages, and network requests return **inline
text**, and axe-core injected via `browser_evaluate` returns JSON inline. Screenshots and traces are
written by the **MCP server** into its output directory, not by the agent. **The reviewer needs no
`WRITE` grant.**

## Rubric — deterministic signals justify blockers

25 points, matching `_reviewer_max_scores`. Phase 6 makes this score matter on a frontend-dominant
phase; blockers remain the hard gate either way (**F12**).

| Signal | Pts | How it is checked | Blocker condition |
|---|---|---|---|
| Interaction flows | 7 | read `browser_snapshot`/`browser_find` for each step's stated pass condition (no dedicated verify tool exists — see Scope's correction note) | any flow fails → **blocker** |
| **Seam integration** | **5** | declared contract vs `browser_network_requests` evidence | shape/status mismatch, or an undeclared seam → **blocker** |
| Required states | 4 | snapshot per state, compared to the contract | missing error or loading state on a contract route → **blocker** |
| Accessibility | 5 | axe-core via `browser_evaluate`, counted by impact | any `critical` / `serious` → **blocker** |
| Console errors | 2 | `browser_console_messages` | uncaught error on a contract route → **blocker** |
| Stack-idiomatic maintainability | 1 | source review against `stack.toml` | never |
| Visual fit vs `##### Design Source` | 1 | subjective; screenshot; Claude-Code-preferred | **never** |

Network requests fold into seam integration rather than sitting in their own bucket, since that is what
they are evidence *of*. These numbers are a starting point — validate them against real phases and
adjust rather than treating them as derived.

**Every blocker traces to a line in the UX Contract the human approved.** That is the property that
makes blockers legitimate rather than an LLM's opinion with workflow-stopping power.

**Visual fit is capped at P2 by contract, not by weighting.** `_effective_blockers_for_feedback`
(`loop_state.py:120-138`) picks up bare `[Severity:P0]` text markers, so a single subjective P0 blocks
completion regardless of the 2-point cap (**F12**). The cap must be stated in the agent contract, not
merely implied by the rubric.

## Seam review — verifying the two sides met

If [phase 9](phase-9-coder-split.md) has landed, the frontend and backend coders never communicate; they
implement independently against the same approved design contract. **Something has to verify they
actually met in the middle, and this reviewer is the only agent with the evidence to do it.**

`browser_network_requests` yields real request/response pairs, so seam review is empirical rather than a
static type comparison — not *"the shapes look compatible"* but *"the form called `POST /api/session`,
got 200, and the response matched what the component destructures."*

**Enumerate seams from Phase `### Collaboration And Wiring`** (**F36**) — the design contract's
coordination section, human-approved at the shape gate, language-neutral, and already what both sides
implement against. Report one block per declared seam rather than inventing a list.

**An FE→BE call observed at runtime but absent from that section is itself a finding.** An undeclared
seam is precisely the class of problem the design gate exists to prevent, so it blocks.

### Findings must carry a routing target

With two coders, `(priority, feedback)` is no longer actionable (**F35**) — a seam finding is useless
unless it names which side changes. Extend the existing tag convention, which is parsed from feedback
text and so needs no schema or migration change:

```
[Severity:P0] [Scope:acceptance-gap] [Target:backend] SEAM-2 — LoginForm destructures
`user.displayName` but POST /api/session returns `display_name`
(src/components/LoginForm.tsx:34, src/api/session.py:71)
```

`[Target:frontend]` · `[Target:backend]` · `[Target:both]`. The orchestrator routes by target for the
next iteration; a `both` finding goes to both coders carrying the same seam ID so they converge on one
resolution rather than each guessing and colliding.

### Output format — and the rules that make it visible

**Markdown is audit evidence. Structured `findings`/`blockers` are the only channel that reaches the
loop.** `consolidate_review_cycle` (`:351-365`) reads *only* the structured fields and never touches
`feedback_markdown` (**F37**), so a seam problem described only in prose affects nothing — not the
score, not the blocker gate, not the coder. **Every actionable seam item must also be a structured
finding or blocker.** The markdown block exists so a human (and the coder, via
`get_reviewer_result`) can see declared-vs-observed in full.

Placement is constrained by two heuristics in `get_reviewer_feedback_context` (**F37**), neither of
which raises — they silently drop:

1. **H4, placed before `#### Reviewer Execution Report (Non-Actionable)`.** Matches the existing
   precedent set by `spec_alignment_reviewer.py:194+` and `design_conformance_reviewer.py:135+`
   (**F38**).
2. **Never place an `#####` section after the execution report** — `_strip_reviewer_execution_report`
   breaks only on a heading of level `<= 4`, so deeper headings following it are silently deleted.
3. **Never write the literal string `Reviewer Execution Report (Non-Actionable)` in seam prose** — the
   marker is matched as a substring on *every* line, and a prose match sets `heading_level = 6` and eats
   everything up to the next heading of any level.
4. **Add `'seam review'` to `actionable_sections`** (`feedback_tools_unified.py:579-585`) or the section
   never appears in the coder's `### Actionable Review Excerpts`. One-line change.

On (4): the allowlist has two unused slots, `findings` and `required corrections`, and naming the
section one of those would make it coder-visible with zero code change. **Don't** — `findings` collides
conceptually with the structured `findings` field and would confuse both the reviewer author and the
coder. Spend the one line on an honest name and leave the reserved slots free.

Per-seam blocks nest at `#####` under the H4 — the same pattern as
`coding_standards_reviewer.py:258-266`, and safe because the parent H4 precedes the execution report.

```markdown
#### Seam Review

##### SEAM-1: LoginForm → POST /api/session
- Declared: `create_session(email: str, password: str) -> api.models.Session`
  (phase `### Collaboration And Wiring`)
- Frontend side: src/components/LoginForm.tsx:34
- Backend side: src/api/session.py:71
- Observed: POST /api/session → 200, body `{user: {display_name, id}, token}`
- Verdict: mismatch — response field `display_name` vs destructured `displayName`
- Finding: [Severity:P0] [Scope:acceptance-gap] [Target:backend] (also stored in `findings`)
```

### Harden the format so this class of mistake fails loudly

The placement rules above are currently unenforced — `store_reviewer_result` checks only that
`feedback_markdown` is non-empty (**F37**), and no test enumerates the H4 set (**F38**). A reviewer can
emit a section that is silently invisible, with no error anywhere.

Add a `@field_validator('feedback_markdown')` to `ReviewerResult` (`src/models/feedback.py:198-231`),
matching the existing validators for `score`, `max_score`, and `blockers`. (`ConfigDict` cannot do this —
it governs model fields, and this is heading structure *inside* a string value.)

Reject only unambiguous structural errors:

| Check | Why |
|---|---|
| No `#` or `##` headings | Reviewer markdown is embedded under container H1/H2 (`# Reviewer Result` / `## Full Feedback Markdown`); an H1/H2 inside breaks nesting |
| Exactly one `###` | The scored title. More than one is malformed |
| No `#####`+ after the execution-report H4 | The silent-deletion trap |
| Marker string appears only as its own H4 heading | The substring footgun |
| Required H4s present: execution report, `Key Issues`, `Recommendations` | Already mandated by the shared contract |

**Correction: implemented as four checks at the Pydantic level, not five.** B17 (the pinned
behavior) only names three of the five checks above — the H1/H2, second-`###`, and
`#####`-after-report rules — and is the narrower, authoritative statement of what the model layer
must enforce. Required-H4 presence is enforced instead at the template layer (B18: every real
reviewer template's example markdown is asserted to contain the boilerplate), because dozens of
pre-existing `ReviewerResult` test fixtures across the suite construct minimal markdown like
`'### X (Score: 50/50)'` for unrelated purposes (scoring math, blocker validation) and are not
reviewers — coupling presence-of-boilerplate to every `ReviewerResult` in existence would force
rewriting all of them for no correctness gain outside phase 7's actual scope. The marker-placement
check is written as "wherever the marker appears, it must be a proper heading," which is vacuously
true when the marker is absent — so it does not smuggle a presence requirement back in.

**Do not validate H4 names against the allowlist.** Rubric-category H4s legitimately are not in it —
they are scoring detail and correctly audit-only. A validator cannot infer intent, and rejecting them
would break all nine reviewers.

**Fail-closed caution — this is why the validator must stay narrow.** A validation failure means the
reviewer cannot store, `consolidate_review_cycle` hard-fails on the missing submission (**F10**), and
the workflow terminates. The MCP retry contract explicitly forbids retrying deterministic validation
errors. So error messages must name the exact violation *and* the fix, and the rules must be ones no
correct reviewer could trip.

**Pair it with build-time tests**, which is where most of the value is: assert in
`tests/unit/templates/test_review_agent_templates.py` that **every** reviewer template's example
markdown passes the validator. That catches authoring drift before shipping rather than at runtime in a
user's project. The runtime validator is the backstop; the template test is the guard.

This hardening benefits all nine reviewers, not just this one — it is scoped here because this is the
phase that adds a new section and therefore the phase that surfaces the risk.

### Boundary against the other reviewers

The overlap here is real and must be explicit, or three reviewers will report the same thing three ways:

| Reviewer | Question |
|---|---|
| `design-conformance-reviewer` | Does each module match its declared signature? *(static, per-module)* |
| `spec-alignment-reviewer` | Does the implementation satisfy the plan's intent? *(static, whole-phase)* |
| **this reviewer's seam review** | **Do the two sides actually integrate at runtime?** *(empirical, cross-boundary)* |

Only the third catches `display_name` vs `displayName`. Both sides individually conform to their declared
signatures — the mismatch exists solely *between* them, which is why static per-module conformance
cannot see it.

**Evidence scope widens accordingly.** `Read`/`Glob` are already granted so no tool change is needed, but
the grounded-evidence contract below must permit reading the **backend side** of each declared seam. It
otherwise scopes reading to frontend files, which would make seam review impossible.

**When runtime evidence is unavailable** (preflight not ready), seam review degrades to a static
contract comparison — read both sides, compare against the declared signature — and reports the absence
of runtime confirmation as skipped context. Static seam review still catches name and type mismatches;
it cannot catch status codes or serialization differences.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | Rostered when frontend files change; consolidation succeeds with it present |
| B2 | Preflight not-ready → reviewer still runs on source evidence, reports runtime skipped, loop converges |
| B3 | A failing Interaction Flow produces a blocker citing the flow ID |
| B4 | A `critical` axe violation produces a blocker citing the rule ID |
| B5 | A subjective visual finding is at most P2 and never blocks |
| B6 | The reviewer re-runs on an iteration where only a backend file changed |
| B7 | Generated frontmatter contains no `BashOutput` and no `Write` grant, for all three TUIs |
| B8 | `respec-ai regenerate` completes for opencode and codex without `ValueError` |
| B9 | No dev server survives a reviewer crash |
| B10 | Every seam in `### Collaboration And Wiring` gets a `#### Seam Review` block |
| B11 | A response-shape mismatch produces a `[Target:backend]` blocker citing both file:line locations |
| B12 | An FE→BE call absent from `### Collaboration And Wiring` is reported as an undeclared seam and blocks |
| B13 | Every seam finding carries exactly one `[Target:...]` tag |
| B14 | With preflight not ready, seam review degrades to static comparison and reports runtime as skipped |
| B15 | Every actionable seam item appears in structured `findings`/`blockers`, not only in markdown |
| B16 | `#### Seam Review` survives `get_reviewer_feedback_context` and appears in `### Actionable Review Excerpts` |
| B17 | The `feedback_markdown` validator rejects an H1/H2, a second H3, and an `#####` after the execution report |
| B18 | Every existing reviewer template's example markdown passes the new validator |

**B2 is what F10 exists to make pass.** **B7/B8** catch the `TemplateToolBuilder` failure (**F17**) at
test time rather than at a user's `regenerate`. **B13** is what makes findings routable by the
orchestrator once phase 9 lands — an untagged seam finding is unactionable.

## Scope

Following `docs/AGENT_DEVELOPMENT_GUIDELINES.md:1767-1778`:

1. **`src/platform/templates/agents/frontend_reviewer.py`** — rewritten. Reuse the renderers in
   `reviewer_contracts.py`.
2. **`src/platform/models/code.py`** — tools model, mirroring `FrontendReviewerAgentTools:270-287`.
   `builtin_tools = [(READ,''), (GLOB,''), (BASH,'')]`. **No `WRITE`** (**F19**), **no `BASH_OUTPUT`**
   (**F17**).
3. **`src/platform/template_helpers.py`** — factory, modeled on `:1112-1140`. Browser tools go through
   `add_platform_tools` (`:65-72`) as verbatim strings, the same mechanism already used for Linear and
   GitHub (**F20**). Grant only what is needed and **exclude `browser_run_code_unsafe`**.

   **Correction, verified at implementation time against the real, currently-published
   `@playwright/mcp` server (queried its live `tools/list` response over stdio, not just its
   `--help` text):** the tool list and the `testing`/`storage` caps claim above do not match
   reality. There is no `browser_verify_*` tool family and no `browser_set_storage_state` tool at
   all — `--caps` only ever adds `vision`, `pdf`, `devtools`, and neither `testing` nor `storage`
   exists as a capability. Storage state is a server **startup** flag (`--storage-state <path>`),
   set once at Playwright MCP registration, not a per-call tool the reviewer can invoke — see the
   corrected install line in `docs/CLI_GUIDE.md`. The actual grant is:
   `browser_navigate`, `_snapshot`, `_click`, `_hover`, `_type`, `_fill_form`, `_select_option`,
   `_press_key`, `_wait_for`, `_resize`, `_evaluate`, `_console_messages`, `_network_requests`,
   `_network_request` (singular — added; not in the original list above, needed for seam review's
   full request/response body since `_network_requests` only returns a numbered summary),
   `_take_screenshot`, `_close`. Interaction Flow and Required States pass conditions are verified
   by reading `browser_snapshot`/`browser_find` output for the expected element/text/value, not by
   a dedicated verify call. Re-verify this list before relying on it again — Playwright MCP is
   evolving quickly (the server queried here reported version `1.63.0-alpha-2026-08-05`) and a
   `browser_verify_*` family has been discussed for it, so it may exist by the time this is read.
4. **`src/platform/templates/agents/__init__.py`** and **`src/platform/template_generator.py`**.
5. **`src/models/enums.py`** — reuse `FRONTEND_REVIEWER`; the agent is replaced, not renamed.
6. **`src/mcp/tools/feedback_tools_unified.py`** — confirm `max_score` stays 25 and the frontend domain
   group from phase 6 is correct.
7. **All three roster copies** — `reviewer_mapping.py:25-37`, `code_command.py:317-335`,
   `patch_command.py:397`. Their drift is how **F1** shipped; phase 0's cross-check test should catch a
   mistake here, which is a good reason to confirm it still runs.
8. **`review_consolidator`** merge format.
9. **Test counts** in `tests/unit/templates/test_template_generator.py` and `test_feedback_enums.py`.

### Contract wording

`render_reviewer_output_contract` in `reviewer_contracts.py` hardcodes *"Do NOT write files to disk"*
and is shared by every reviewer. **Add a sibling renderer rather than parameterizing it** —
parameterizing changes the generated text of every reviewer and breaks their tests for no benefit.

Clauses this reviewer needs:

- No authoring files; no `>` redirection. There is no `Write` tool.
- Bash is for `respec-ai frontend-preflight` **only** — not for starting servers directly, installing
  packages, running git, or running project build commands.
- Artifacts the MCP server wrote into the run scratch directory are **citable evidence**; the agent does
  not author them and must not write into that directory itself.
- No `git add`, no `git commit`.
- All findings go exclusively through `store_reviewer_result`.
- **Evidence citation**, matching the existing GROUNDED REVIEW EVIDENCE CONTRACT style: every negative
  finding cites either `relative/path.ext:123` in project source, **or** a UX Contract flow ID
  (`FLOW-3 step 2`) plus the exact `browser_snapshot`/`browser_find` evidence or axe rule that failed. Never "the button looks
  wrong." **Seam findings cite both sides** — the frontend and backend `file:line` — plus the observed
  request/response.
- **Routing target on every seam finding**: exactly one of `[Target:frontend]`, `[Target:backend]`,
  `[Target:both]`.
- **Severity rule:** only flow failure, an accessibility violation at or above the configured
  conformance level, or a console/network error may be `P0`/`[BLOCKING]`. Visual fit is never blocking —
  maximum P2.
- Teardown calls `frontend-preflight --stop`.

Add a belt-and-braces `--stop` in `code_command`'s post-review path so a crashed reviewer cannot leak a
dev server (B9).

## Out of scope

- **Coder-authored Playwright specs.** Deferred — see
  [deferred-issues.md](deferred-issues.md#coder-authored-end-to-end-specs-as-the-frontend-test-list).
  Best judged once the UX Contract format has stabilized in practice.
- **Weighting.** Phase 6.
- **Generalizing the MCP registrar** or **building auth**. Both deferred in phase 5.
- **A second reviewer.** One agent, two evidence sources. Splitting was considered and rejected.

## Exit criteria

- B1–B9 green.
- **Happy path, end to end.** Implement a UX Contract deliberately wrong — omit one route's error state,
  remove a form label. Confirm: consolidation succeeds; feedback carries at least two blockers, one
  citing a `FLOW-N` and one citing an axe rule ID; the loop returns **REFINE despite the composite
  score**. Fix both defects, re-run, confirm blockers clear and it reaches COMPLETED.
- **Degradation.** Unregister Playwright MCP (or stop the dev server) and re-run the same phase: the
  reviewer runs on source evidence, reports runtime as skipped, consolidation succeeds, the loop
  converges. This is the **F10** test.
- **Reuse exemption.** Break the UI without touching any frontend file — change a shared token or an API
  response shape — and confirm the loop does not report COMPLETED.
- **Seam review, end to end.** Rename a backend response field without touching the frontend. Confirm:
  a `#### Seam Review` block for that seam, verdict `mismatch`, a P0 blocker tagged
  `[Target:backend]` citing both `file:line` locations and the observed response, and the loop returns
  REFINE. Then delete the seam's entry from `### Collaboration And Wiring` while leaving the call in
  place, and confirm it is reported as an undeclared seam.
- **Stability.** Run the same unchanged frontend phase through three iterations and confirm the score
  does not oscillate. If it does, subjective judgment is leaking into the deterministic signals.
- **Portability.** `respec-ai regenerate` for opencode and codex: no `ValueError`, frontmatter lists
  lowercase `bash`, no `BashOutput`, no `Write`.
- `uv run pytest` clean; `respec-ai check-conformance` clean.
