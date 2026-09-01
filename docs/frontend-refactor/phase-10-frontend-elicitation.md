# Phase 10 — Frontend elicitation and user-elected shape-act research

**Depends on:** Phase 4 (the UX Contract). Phase 8 is not required, but its portability
invariant constrains this phase. **Blocks:** nothing.
**Risk:** low mechanically — prompt changes plus one new command sub-step, no document-model
change and no migration. The risk is entirely in whether the added decisions are real design or
ceremony, and in whether the research gate stays free when declined.

## Start here

**Prerequisites:** Phase 4 complete. Verify: `grep -n "UX Contract"
src/platform/templates/agents/phase_architect.py` returns output.

**Already done?** `grep -n "Design Research" src/platform/templates/agents/phase_architect.py` —
output means complete.

**Read first:** [README.md](README.md), `docs/phase-refactor/testing.md`, `CLAUDE.md`, and
[decisions.md](decisions.md) — the three entries *"Frontend granularity is a setting on existing
dials, not a new mode"*, *"Design Source is a decision, not a field"*, and *"Shape-act research is
user-elected, never automatic."* The third records three rejected alternatives; implementing any of
them would look reasonable and be wrong.

Background: `docs/phase-refactor/phase-3-human-gate.md` describes the shape act this phase extends,
and [phase-4-ux-contract.md](phase-4-ux-contract.md) the contract it elicits decisions for.

**First action:** run `/respec-phase` on a real UI objective on a scratch project and read the
shape-act output before changing anything — see *Step 0* below. This phase is a hypothesis about
what that run shows.

**The judgment call, and it is the main risk:** three new `OD-###` entries that the user clicks
through without reading are worse than none. They add a stop, train the user to accept defaults, and
give the critic more presence to enforce. The exit criteria include reading real generated output
for exactly this, and no test substitutes for it.

**The cost invariant, and it is absolute:** a user who declines research at Step 5.5 must pay
*exactly* what they pay today — zero additional `bp` invocations, on every iteration. `phase_command.py`'s
`MANDATORY COST-AWARE SYNTHESIS POLICY` is the governing constraint, not a guideline. B6 and B11
pin it.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Two things, sharing a home in the shape act:

1. Make the shape act elicit the frontend decisions with the largest blast radius, which its
   currently OOP-shaped quality checks do not.
2. Let the user *choose*, once per shape pass, to have a knowledge gap researched before deciding —
   without adding cost to any iteration where they don't ask.

## Why these are one phase

Both are prompt-level changes to the same act, and the second exists to serve the first: the
decisions in (1) are exactly the ones a user is least equipped to make from intuition on unfamiliar
frontend ground, which is what makes optional pre-decision research worth having at all. Shipping
(1) without (2) leaves the user answering three new consequential questions with no more information
than before.

## The problem

**The architect never asks the frontend questions with the largest blast radius.** Its quality
checks (`phase_architect.py:930-937`) are *"would two engineers write the same public API"* and
*"does every abstraction name what varies behind it"* — the right questions for a service layer. On
a UI phase the expensive-to-reverse decisions are different, and nothing elicits them. The result is
a UX Contract that correctly describes observable behavior, sitting on a component tree nobody made
a decision about.

**The shape act has knowledge-base access it cannot record.** The architect's Step 0.6 runs
`best-practices-rag query-kb` on every invocation, in both modes. But shape mode is forbidden from
writing `### Research Requirements` (`phase_architect.py:566-568`), so the results have no
destination, and unresolved gaps cannot become `Synthesize:` prompts until the detail act. The
synthesis that closes that loop runs at Step 16.5 — *after* the shape gate at Step 11. The human
approves the design in the one place ecosystem convention matters most, with the research machinery
idle.

## What this phase does not change, and why

**Granularity stays phase-scoped.** Component-at-a-time design was considered and rejected: the
workflow is sized to "one sprint's worth of work" (`phase_architect.py:944-955`), and the per-unit
dial already exists as the Step 7 skeleton opt-in. See [decisions.md](decisions.md).

**No wireframe step and no new human gate.** The UX Contract is the wireframe in text; what a visual
wireframe adds is `##### Design Source`. `decisions.md`'s *"No new human gate for the UX Contract"*
stands unchanged. Step 5.5 is a conditional prompt that skips silently when it has nothing to offer,
not a stop the user must pass through.

**No change to `src/models/phase.py`.** `#### Design Research` lives under `### Design Shape -
Additional Sections`, shape mode's own territory — the same placement argument phase 4 made for the
UX Contract. No migration, no F13 positional-UPSERT hazard.

## Where this lands in the workflow

Step numbering is from `phase_command.py` as it stands, not from the phase-3 design document, whose
numbering predates phases 4-6.

```
SHAPE ACT
  Step 4     Init SHAPE_LOOP_ID; 4.2 link; 4.5 project config
  Step 5     phase-architect, phase_mode="shape"
               - Step 0.6 `query-kb` runs here, free, already
               - NEW: emits #### Design Research (Read: / Gap:)
               - NEW on UI phases: OD for design source, state ownership,
                 screen decomposition, component provenance
  Step 5.5   NEW - RESEARCH GATE (skips silently when no offerable Gap:)
  Step 6     Design conversation - walks OD-### highest blast radius first
  Step 7     Skeleton opt-in
  Step 8/9   Edit gate; APPROVED_VERSION recorded
  Step 10    phase-critic, phase_mode="shape"
  Step 11    Joint gate -> refine returns to STEP 5  <-- why 5.5 must be idempotent
  Step 11.5  Materialize skeletons
  Step 12    Shape Gate -> shape-settled

DETAIL ACT
  Step 16.5  bp synthesis, once, bounded 3 workers
               - EXTENDED: seeds from and emits #### Design Research paths
```

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A UI phase's shape output requires an OD entry for state ownership, decomposition, and provenance |
| B2 | A backend-only phase is unchanged — no new OD classes, no `#### Design Research`, no Step 5.5 prompt |
| B3 | The critic blocks a UI phase missing any of the three decision classes |
| B4 | The critic neither blocks nor deducts on declined or absent research |
| B5 | `#### Design Research` round-trips through `get_document` on **both** state managers |
| B6 | Electing nothing at Step 5.5 invokes `bp` zero times |
| B7 | Step 5.5 renders and blocks for a response on all three TUIs |
| B8 | A path fetched at Step 5.5 is not re-synthesized at Step 16.5, and does reach `### Research Requirements` |
| B9 | `bp` unavailable at Step 5.5 displays a notice and proceeds to Step 6; Step 16.5 still hard-exits |
| B10 | Phase 8's B7 still holds — identical UX Contract from a local bundle on all three TUIs |
| B11 | A Step 11 refine returning to Step 5 does not re-offer researched or declined gaps |

**B2 is the regression guard** and should be written first — it is what proves this phase costs
existing backend users nothing. **B6 and B11 are the cost guards**; between them they assert the
invariant stated at the top of this document. **B8** is what makes the whole research half useful
rather than write-only. **B10** is inherited from phase 8 and must not regress.

B5 is not optional: the positional-UPSERT hazard at
[`docs/phase-refactor/phase-2-design-layer.md:44-56`](../phase-refactor/phase-2-design-layer.md)
means in-memory passing tells you little about postgres — even though this phase adds no column,
`### Design Shape - Additional Sections` content still traverses that path.

Template assertions go through `tests/support/template_contract.py`, never string grepping.

## Scope

### 1. Frontend decision classes — `phase_architect.py`

Shape-mode branch (`:479-520`) and the quality checks (`:876-883`).

Gated on the *same* user-facing-UI condition that already gates the UX Contract at `:495-500` — do
not introduce a second, separately-drifting predicate. Require an `OD-###` for each class unless
`### Settled Design Decisions` already answers it:

1. **State ownership and the data boundary** — server state vs. local component state vs. URL
   state; where the fetch boundary sits; what is cached and who invalidates it. This is the frontend
   analog of *"what varies behind this abstraction"*, and the decision whose reversal rewrites the
   most files.
2. **Screen decomposition** — route vs. modal vs. nested layout vs. in-place panel, per UX Contract
   flow. Shapes the whole component tree; reversing it is a rewrite, not a refactor.
3. **Component provenance** — consume an existing library or design system, or author components in
   this phase. Upstream of the other two.

These use the existing `OD-###` format parsed at `phase_command.py:544`, so they inherit
blast-radius ranking, the Step 6 walk, the "accept recommended defaults for all remaining" exit, and
`SD-###` recording. **No new machinery, and no new parsing.**

`### Collaboration And Wiring` gains a UI-phase requirement: alongside ownership and construction it
must carry the **state-ownership map** from (1) — which module owns which slice, and how it reaches
a component. That section is what the frontend and backend coders coordinate through
([decisions.md](decisions.md), *"Coordination is design-time, not runtime"*), so it must be explicit
there rather than implied by the Skeleton Index.

New quality checks alongside the existing three:

- *Would two engineers given this shape put the same state in the same place? ✓*
- *Does every screen in the Route Index have a decided decomposition, not a default? ✓*
- *Does every component entry carry real props, or just a name? ✓*

**Do not add a component-inventory section.** The Skeleton Index already carries components
correctly — props as the public seam, JSX/styling/hooks explicitly excluded (`:794-802`). A second
list would duplicate it and drift.

### 2. Design Source becomes a decision — `phase_architect.py`

`##### Design Source` (`:840-842`) is currently a slot the architect fills. With no design available
it invents the visual decisions or writes nothing, and the user finds out after the contract exists.

Emit it as the **first** `OD-###` on a UI phase, upstream of the three above:

```
- OD-001 | title: Visual design source for this phase
  - Option A: Design in Claude Design first, export the handoff bundle, name its path
  - Option B: Match existing components at <path> — no new visual design needed
  - Recommended: <A|B> — <why>
```

Choosing A suspends the shape act at Step 6. The user designs, then re-runs the command, which
resumes at Step 5 through the `shape-proposed` branch at Step 3. **No new resume machinery** — that
path already exists.

Option B must remain fully sufficient. Phase 8's B7 (identical contract from a local bundle on all
three TUIs) is the assertion that it does, and it must stay green.

### 3. `#### Design Research` — `phase_architect.py`

Shape mode emits, under `### Design Shape - Additional Sections`, following the H4 nesting rule at
`:953`:

```markdown
#### Design Research
- Read: `.best-practices/<path>.md` — applied to: OD-002 (state ownership)
- Gap: <technologies> / <topics> — bears on OD-003 (screen decomposition)
```

`Read:` entries come from Step 0.6's already-running, free `query-kb` cache hits. `Gap:` entries
state what the KB did not answer. **A `Gap:` is a statement, not a request** — nothing synthesizes
because a gap exists.

Be clear-eyed about the ceiling: on a cold knowledge base this section is all `Gap:` and delivers
nothing on its own. It is the free floor, not the feature.

### 4. Step 5.5, the research gate — `phase_command.py`

New sub-step between Step 5 and Step 6, following the decimal convention already used by 4.2, 4.5,
11.5, 12.5, 12.6, and 16.5.

```text
Parse "#### Design Research"; OFFERABLE_GAPS = Gap: entries NOT marked [declined]

IF OFFERABLE_GAPS is empty:
  Proceed to Step 6.              <- silent: no prompt, no output line

{selection_prompt_instructions}
Header: "Design Research"
Question: "The architect flagged these knowledge gaps. Research any before we walk the
           design decisions?"
multiSelect: true
Options: one per OFFERABLE_GAPS, plus "None — proceed to the design decisions" (default)

WAIT for {selection_response_source}.   [+ the full non-termination block]

IF selection is "None" or empty:
  Mark every OFFERABLE_GAPS entry "[declined]"; store; Proceed to Step 6.

Run SELECTED_GAPS through the shared synthesis renderer (below).
Rewrite each synthesized gap as: - Read: `<path>` — Source: shape-act
Mark unselected offerable gaps "[declined]"; store; Proceed to Step 6.
```

Four properties, each of which is a test:

- **Zero forced cost (B6).** The default is "None". Declining costs exactly what today costs.
- **Loop-safe (B11).** Step 11's refine path returns to **Step 5**, so Step 5.5 re-runs on every
  shape iteration. Idempotence comes from state, not position: a researched gap is now a `Read:`
  entry and no longer offerable; a declined gap carries `[declined]` and is filtered out. Only a
  genuinely new gap from a re-shaped design reappears.
- **Portable (B7).** `multiSelect: true` with `{selection_prompt_instructions}` /
  `{selection_response_source}` is exactly Step 7's skeleton opt-in (`phase_command.py:611-622`), so
  it renders on Codex, where `ask_user_question_tool_name` is `None` (**F18**, **F29**).
  **`Task(bp)` is already granted at command level** (`template_helpers.py:171`) — no tool-grant
  change is needed. Verify it anyway before assuming: phase 3 shipped exactly this defect class with
  `Write` (`docs/phase-refactor/phase-3-human-gate.md:45-56`).
- **Degrades, never terminates (B9).** Step 16.5's SUB-STEP 4 *hard-exits* when `bp` is unavailable,
  and that is correct there — the detail act promised those documents. Step 5.5 must display a
  notice and proceed to Step 6, because the user asked for optional enrichment, not a dependency.

**Extract Step 16.5's SUB-STEPs 3-5 as one shared renderer parameterized on failure posture** —
bounded workers, `BP_PATH_REGEX` output validation, non-existent-path guard. Two divergent copies of
that error handling is precisely the drift the phase-9 coder split existed to prevent, and the
posture difference above is the one thing that must be a parameter rather than an accident of
copying.

### 5. Downstream wiring — `phase_command.py` Step 16.5

A path recorded only in `#### Design Research` is read by the architect during the shape act and is
then **invisible to every reviewer and both coders**. They extract `.best-practices/` paths from
`### Research Requirements` (`spec_alignment_reviewer.py:166`, `code_quality_reviewer.py:140`, and
the four domain reviewers), and SUB-STEP 6 reconstructs that section from `COMPLETE_READ_BLOCKS`
only. This is the same "prose that affects nothing" failure [decisions.md](decisions.md) documents
for reviewer markdown under *"Reviewer markdown is audit evidence; structured fields are the
channel."*

Two additions, no new mechanism:

- **SUB-STEP 2** — also seed `EXISTING_READ_PATHS` from `#### Design Research`. This doubles as the
  dedupe: nothing the shape act already fetched is synthesized a second time.
- **SUB-STEP 6** — emit those paths as `Read:` blocks into the reconstructed
  `### Research Requirements`, with `Source: shape-act`.

B8 pins both halves.

### 6. Critic — `phase_critic.py`

Additions to the existing shape-mode lane. Blockers:

- A UI phase whose `### Open Design Decisions` names none of the three classes. The critic already
  blocks generically on *"a consequential choice was never surfaced as a decision"*; this makes it
  specific.
- A UI phase with no `##### Design Source` decision recorded either way.
- A UX Contract flow whose screen decomposition is undecided.

**Respect the BINDING SCOPE guard**
([`docs/phase-refactor/phase-2-design-layer.md:194-213`](../phase-refactor/phase-2-design-layer.md)).
These are decision-**presence** checks. The critic must never block on a decision's *content* —
whether server state belongs in a query cache is the user's call, and blocking on it turns the
critic into the conformance checker that guard exists to prevent.

**No blocker and no score deduction may reference `#### Design Research` (B4).** Declining research
is a legitimate choice. A critic that penalizes it converts an opt-in into a mandate and defeats the
entire cost design — which is the quietest way this phase could fail.

## Out of scope

- **Any change to `src/models/phase.py`.** If you are editing the document model, you have chosen
  the first-class-field route phase 4 already rejected for the UX Contract, for the same reasons.
- **A new human gate.** Step 5.5 skips silently when it has nothing to offer.
- **Automatic synthesis anywhere in the shape act.** Three variants were considered and rejected;
  see [decisions.md](decisions.md). This is the constraint most likely to be re-opened by someone
  who has not read that entry.
- **Roadmap or plan KB grounding.** Recorded in [deferred-issues.md](deferred-issues.md).
- **Coder-authored end-to-end specs as the frontend Test List.** Already deferred with a stated
  revisit trigger; this phase does not pre-empt it.
- **Component-inventory or wireframe sections.** See *What this phase does not change*.

## Exit criteria

**Status (implementation session):** Step 0's live `/respec-phase` run was not performed by the
implementing agent — it requires a scratch project's plan/roadmap and several interactive human
gates, which the user elected to run themselves in a separate session rather than delegate. Everything
below was implemented as a hypothesis per that plan, test-first, and mechanically verified; the
criteria that require a live run and human judgment (marked below) are explicitly open until that
session happens.

- [x] B1-B11 observed failing first, then passing (`tests/unit/templates/test_frontend_elicitation_phase10.py`).
      B5 verified against **postgres** specifically (`tests/integration/test_state_manager_model_roundtrip.py`,
      `db_state_manager` parametrization, run against `docker-compose.dev.yml`'s db service).
- [x] `uv run pytest` green (1647 passed). `uv run respec-ai regenerate` valid for claude-code and
      codex, confirmed against a scratch project. OpenCode's CLI regenerate needs a one-time
      `respec-ai models opencode` run unrelated to this phase; portability itself is covered by the
      adapter-parametrized unit tests (B7 across ClaudeCodeAdapter/CodexAdapter/OpenCodeAdapter).
- [ ] **Cost check, measured not assumed.** Not run live — needs the user's real `/respec-phase`
      session. B6 pins the static claim (the "None" branch never reaches `Task(bp)`); this criterion
      additionally wants a measured `invoked_bp` count from a real run (Step 16.5 summary line —
      now `phase_command.py:1462` after this phase's edits, verify before relying on it).
- [ ] **Loop check.** Not run live. B11 pins the static claim (idempotence by state, not position).
- [ ] **Backend regression.** Not run live — "byte-identical" is a claim about what the architect
      *produces* for a real backend phase, which only a live before/after diff can prove. B2 pins the
      static claim instead (the new instructions live entirely inside the same `user-facing UI`
      conditional the UX Contract already used, and the full existing suite — including phases 0-9 —
      is green with no changes required to any of them), which is evidence but not the proof this
      criterion asks for.
- [ ] **Manual quality review — the criterion that matters.** Open until the user's live
      `/respec-phase` session on a real UI objective. This is the one criterion no test substitutes
      for — see the phase document's own "judgment call" note above.
- [ ] Portability with a local design bundle on a real UI objective: open until the live session.
      The static invariant (Option B stays fully sufficient; phase 8's B7 untouched) holds by
      construction — no phase 8 code was touched.
