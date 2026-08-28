# Phase 4 — The UX Contract

**Depends on:** Phase 0. Independent of phases 1–3 and may run in parallel with them.
**Blocks:** Phases 6, 7.
**Risk:** low mechanically — zero code changes to the document model. The risk is entirely in whether
the generated contracts are any good.

## Start here

**Prerequisites:** Phase 0 complete. Nothing else — this phase touches prompts, not machinery.

**Already done?** `grep -n "UX Contract" src/platform/templates/agents/phase_architect.py` — output
means complete.

**Read first:** [README.md](README.md), `docs/phase-refactor/testing.md`, `CLAUDE.md`, and
[findings.md](findings.md) **F15**, **F16**. In [decisions.md](decisions.md) read *"The UX Contract
lives under `### Design Shape - Additional Sections`"* and *"No new human gate for the UX Contract"* —
the first was a reversal and the placement is not arbitrary.

Background: `docs/phase-refactor/phase-3-human-gate.md` explains the gates this contract passes
through.

**First action:** read `phase_architect.py:436-471` — the shape-mode section — and confirm for yourself
that `:463-469` forbids writing standalone domain H2 sections. That prohibition is the whole reason
this contract lives where it does, and it is easy to miss.

**This is the highest value-per-line phase in the refactor**, and the one that most directly addresses
the authoring gap: the visual design decisions that are hardest to author now have a structured home.
It is also the phase whose failure mode is quietest — see the judgment call below.

**The judgment call, and it is the main risk:** a UX Contract whose Interaction Flows say *"the page
looks right"* is **worse than no contract at all**. It gives phase 7's reviewer false authority to emit
blockers against something unmeasurable. Every flow step needs an observable pass condition. The exit
criteria include reading real generated output for exactly this, and no test substitutes for it.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Give phases with a user interface a design contract describing *observable behavior* — the frontend
analog of what Skeleton Index and Test List do for code shape — authored in shape mode and approved at
the existing human gates.

## Why the placement is what it is

Shape mode may not write standalone domain H2 sections. `phase_architect.py:463-469` reserves those for
the detail act and requires preserving existing detail-act content verbatim (**F15**). A
`## UX Contract` H2 written in shape mode is out of contract and can be dropped by the detail-act
expansion (Steps 13-16) — and `find_content_loss` (`src/models/base.py:188-207`) warns on orphan H3s but
would **not** catch a dropped H2 (**F16**). The failure would be silent.

`### Design Shape - Additional Sections` (`src/models/phase.py:26`, rendered `:124-125`) is shape mode's
own territory (`phase_architect.py:442`, H4-format rule `:953`), round-trips today, and sits *inside*
the design contract where a UX contract belongs semantically.

So: a `#### UX Contract` block with H5 subsections underneath, and **zero changes to
`src/models/phase.py`**.

A first-class Pydantic field was considered and rejected — it costs a migration across both state
managers plus the positional-UPSERT hazard documented at
`docs/phase-refactor/phase-2-design-layer.md:44-56`, and buys nothing, since no section is ever
code-required anyway (**F16**). See [decisions.md](decisions.md).

**No new gate.** The contract is authored in shape mode and therefore already passes Human Gate 1a
(`phase_command.py:471-521`) and the joint gate 1b (`:620-678`), which is where the user edits the phase
document directly. A separate approval step would add a stop without adding a decision.

## The contract

Emitted only when the phase has a user-facing UI.

- **`##### Route Index`** — path :: purpose :: auth requirement. The auth column is load-bearing: phase
  7 uses it to know which routes it can reach without a session.
- **`##### Required States`** — per route: loading / empty / error / success / validation, each with an
  observable assertion.
- **`##### Interaction Flows`** — `FLOW-N:` numbered steps, **each with an explicit observable pass
  condition**. Not "the form submits" but "submitting an invalid email shows an inline error and the
  form is not cleared."
- **`##### Accessibility Requirements`** — target conformance level, keyboard paths, focus order,
  landmark and heading structure, contrast.
- **`##### Breakpoints`** — the specific named widths that must be verified and what changes at each.
- **`##### Design Source`** — Claude Design handoff bundle path, design tokens file, or existing
  components to match.

**`##### Interaction Flows` is the single most important element in this refactor.** It is what phase 7
turns into verified `browser_snapshot`/`browser_find` evidence per step (the real Playwright MCP server
has no dedicated `browser_verify_*` tool family — see phase 7's Scope correction), and it is what makes
runtime review deterministic rather than aesthetic. Everything else in the contract supports it.

Note the contract is framework- and language-agnostic by construction: routes, states, flows,
accessibility, and breakpoints describe observable behavior, not implementation. A React app, an HTMX
app, and a server-rendered Rails app produce the same shape of contract. That is deliberate and should
survive any edits.

## Claude Design — the portable half

`##### Design Source` is where Claude Design lands. **This phase builds only the portable path**, which
works identically on all three TUIs: a local handoff bundle, tokens file, or named components, read with
`Read`.

Claude Code additionally gets `/respec-design-sync` and live-project reads via the `DesignSync` tool —
that is **[phase 8](phase-8-claude-design.md)**, and it is deliberately separate. `DesignSync` requires
interactive claude.ai authentication, raises permission prompts on write, and returns content authored
by other org members that must be treated as data rather than instructions (**F31**). None of that
belongs in the phase that establishes the contract format.

**The invariant this phase owns:** the portable path must be sufficient on its own. Phase 8 may make
Claude Code better; nothing here may come to depend on it. A Codex project with a local bundle must
produce the same contract quality. See [decisions.md](decisions.md).

The workflow to document in `docs/WORKFLOWS.md`:

1. Design in Claude Design — the visual step respec-ai has never had an answer for.
2. Export the handoff bundle and unpack it into the repo.
3. Name the path under `##### Design Source`.
4. The architect reads the bundle's README when writing the contract; the reviewer uses it as visual
   reference.
5. On Claude Code, `/respec-design-sync` optionally pushes the built component library back up so future
   designs start from real components — phase 8.

**The property this buys:** everything downstream behaves identically whether the design came from
Claude Design, a Figma export, or a hand-written token file. respec-ai gains a design-source seam, not a
Claude Design dependency. Do not let step 4 grow into anything that only works for one source.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A phase with a UX Contract round-trips byte-identically through `get_document` |
| B2 | B1 holds on **both** state managers — in-memory and postgres |
| B3 | The contract survives the detail act (Steps 13-16) unchanged |
| B4 | A backend-only phase produces no UX Contract and is otherwise unchanged |
| B5 | The critic rejects an Interaction Flow step with no observable pass condition |
| B6 | The contract appears in the material presented at Human Gate 1a |

**B3 is the phase's real risk** and the reason **F15** matters — write it early and run it against a
real two-act phase, not a fixture. **B2** is not optional: the positional-UPSERT hazard at
`docs/phase-refactor/phase-2-design-layer.md:44-56` means in-memory passing tells you little about
postgres.

## Scope

**`src/platform/templates/agents/phase_architect.py`**
- Shape-mode instructions (`:436-471`): emit `#### UX Contract` under `### Design Shape - Additional
  Sections` when the phase has user-facing UI. Extend the shape-mode section list at `:442`.
- Add the subsection format spec alongside the existing Skeleton Index / Test List entry formats
  (`:36-54`, elaborated `:708-728`).
- Follow the H4+ nesting rule at `:953`.

**`src/platform/templates/agents/phase_critic.py`**
- Check that every `FLOW-N` has an explicit observable pass condition, and reject prose like "looks
  right" or "works correctly." This is the automated half of the quality bar; the manual read is the
  other half.
- Check the Route Index auth column is present when routes exist.

**`src/platform/templates/commands/phase_command.py`**
- Surface the contract at the existing gates (1a `:471-521`, joint 1b `:620-678`). Presentation only —
  **no new gate**.

**`src/platform/templates/agents/frontend_reviewer.py`**
- Score workflow (8pts) and accessibility (5pts) **against the UX Contract when present**, falling back
  to today's behavior when absent. The placeholder is replaced in phase 7, but this makes it useful in
  the meantime at near-zero cost — and it is how you find out whether the contracts are actually
  legible to a reviewer before building phase 7 on top of them.

**`docs/WORKFLOWS.md`** — the Claude Design workflow above.

## Out of scope

- **Any change to `src/models/phase.py`.** If you are editing the document model, you have chosen the
  first-class-field route this phase explicitly rejected.
- **A new human gate.**
- **Browser or runtime anything.** Phases 5 and 7.
- **Shape-aware weighting.** Phase 6 consumes UX Contract presence; it is not defined here.

## Exit criteria

- B1–B6 green, with **B2 verified against postgres** and **B3 verified on a real two-act phase**.
- **Manual quality review — the criterion that matters.** Run `/respec-phase` on a real UI objective
  and read the generated contract yourself:
  - Could phase 7's reviewer mechanically check every flow's pass condition? If any step needs human
    interpretation, the contract is not yet a contract.
  - Are the Required States actually observable, or restatements of the route's purpose?
  - Is the Accessibility section specific (keyboard path, focus order) or boilerplate ("must be
    accessible")?
  - Would *you*, as the user, want to edit this at the gate — or does it read as ceremony you would
    approve without reading? The second is the failure mode.
- `respec-ai regenerate` completes for all three TUIs.
- `uv run pytest` clean.
