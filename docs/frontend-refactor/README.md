# respec-ai — Language-agnostic materialization and frontend design/review

Working design documents for making respec-ai's design → skeleton → TDD → review spine work for any
language, and for giving the review layer the ability to look at a rendered page.

Breaking changes are in scope.

---

## Start here — fresh session

If you have just picked this up with no prior context, this section is your entry point.

**1. Read in this order.** All paths are relative to the repository root.

1. `docs/frontend-refactor/README.md` — this file. Problem, principles, phase index.
2. `docs/phase-refactor/testing.md` — **required.** How to test in this codebase. Non-obvious,
   because respec-ai generates prompts and those resist ordinary behavioral testing. Not duplicated
   here; same codebase, same conventions.
3. `docs/frontend-refactor/findings.md` — skim now, return to it whenever a phase document asserts
   something surprising about the codebase. Phase documents cite findings as **F1**–**F28** rather
   than restating the evidence.
4. `docs/frontend-refactor/decisions.md` — read before questioning any design choice. Five were
   reversed during design and the reasoning is recorded.
5. The phase document you are implementing.

Also read `CLAUDE.md` at the repository root — project coding standards are mandatory and override
general defaults.

`docs/phase-refactor/` is the **previous** major refactor (v2, interface-first phase design). Its
phases are complete. This refactor builds directly on that machinery, so its `README.md`,
`findings.md`, and `decisions.md` are useful background when a phase document here references the
shape gate, the human gates, or skeleton materialization.

**2. Find out which phase to work on.**

```bash
# Phase 0 done?  → output means done
grep -n "DESIGN_CONFORMANCE_REVIEWER" src/models/enums.py
# Phase 1 done?  → output means done
grep -rn "LanguageMaterializer" src/utils/
# Phase 2 done?  → output means done
grep -n "\.tsx" src/platform/templates/agents/phase_architect.py
# Phase 3 done?  → output means done
grep -n "css_framework" src/platform/standards_config.py
# Phase 4 done?  → output means done
grep -n "UX Contract" src/platform/templates/agents/phase_architect.py
# Phase 5 done?  → file exists means done
ls src/cli/commands/frontend_preflight.py
# Phase 6 done?  → output means done
grep -n "SPECIALIST_DOMAIN_GROUPS" src/utils/review_weighting.py
# Phase 7 done?  → output means done
grep -n "browser_tools" src/platform/models/code.py
# Phase 8 done?  → output means done
grep -rn "DesignSync" src/platform/
# Phase 9 done?  → file exists means done
ls src/platform/templates/agents/coder_contracts.py
```

Work the lowest-numbered incomplete phase, respecting the dependencies in the phase table below.
Phase 4 is independent of phases 1–3 and may be done in parallel with them.

**3. Line numbers may be stale.** Every `file:line` reference in these documents was verified at
design time. The codebase moves. Before acting on a reference, open it and confirm it says what the
document claims. If it does not, search for the symbol instead, and correct the reference in the
document as part of your change — these documents are meant to be maintained, not archived.

**4. Working agreement.**

- Test-first, always. Each phase document opens with *Behaviors to pin* — write those tests, run
  them, confirm they fail for the right reason, and only then implement.
- Tests pin behavior, not implementation. See `docs/phase-refactor/testing.md` for the discriminating
  question.
- Do not start a phase whose predecessor is incomplete.
- Do not expand a phase's scope. Each has an explicit *Out of scope* section; if something seems
  missing, it is probably deliberately assigned to a later phase.
- Commit per the `CLAUDE.md` convention: conventional-commit style, no attribution lines.

**5. If something in a phase document is wrong or ambiguous,** fix the document as part of the work.
A stale design document is worse than none, and the next session inherits whatever you leave.

---

## The problem

Two independent gaps, which turn out to share a root.

**respec-ai assumes the user writes Python.** The materialization layer is not "Python with some
hardcoding" — it is a pipeline with *no language parameter anywhere*, from the architect prompt
through the CLI to the renderer (**F3**). `skeleton_generator.py` emits `def`, `class`, `self`, `from
X import Y`, and `raise NotImplementedError` unconditionally (**F4**), and the Skeleton Index grammar
the architect writes is itself Python-shaped (**F5**). Point a Skeleton Index entry at a `.tsx` file
and you get Python inside it, committed, with no error — `phase_command.py:766-772` runs `git add` and
`git commit --no-verify` on whatever was written.

**The review layer cannot see the running application.** `frontend-reviewer` is a placeholder that
scores UI by reading source files. It never starts the app, never renders a page, never checks that a
flow completes or that a form is reachable by keyboard.

**The shared root:** frontend code is essentially never Python, so the language gap is not a separate
inconvenience — it is what keeps frontend work outside the design → skeleton → TDD-red spine
altogether. Fixing the reviewer without fixing the seam would produce a reviewer with nothing
trustworthy to review.

Two things compound it. Polyglot projects — which nearly every frontend project is — are silently
mis-configured: `frontend_framework = "react"` lands under `[language.python]` while
`[language.typescript]` gets empty strings (**F2**). And the review score cannot express frontend
quality anyway: all domain specialists split a fixed 15-point pool, so on a phase whose entire point
is the UI, the frontend reviewer is worth ~7.5/100 (**F11**).

Separately, there is a gap *upstream* of code that respec-ai has never addressed: the visual design
itself — layout, color, hierarchy. No workflow produces it, so it arrives as ad hoc prose or not at
all.

## The outcome

- The materializer dispatches by language behind a `LanguageMaterializer` protocol. Python and
  TypeScript ship; the remaining 24 languages in `language_standards.json` become contributions
  rather than refactors.
- The Skeleton Index grammar is language-appropriate — a React component is described as a component,
  not forced into `Class.method(params) -> Return`.
- Polyglot projects configure correctly, so a Python backend and a React frontend can coexist.
- Phases with a UI carry a **UX Contract** — routes, required states, interaction flows with explicit
  pass conditions, accessibility requirements, breakpoints, and a design source — authored in shape
  mode and approved at the existing human gates.
- One frontend reviewer scores conformance against that contract using **both** source and the
  rendered page, driving the loop through blockers rather than through a score too small to matter.
- Review weight scales with what the phase is actually about.
- **Claude Design** becomes the answer to the visual-design gap. Portably: design there, export the
  handoff bundle, name it under `##### Design Source` — and everything downstream behaves identically
  whether it came from Claude Design, a Figma export, or a hand-written token file. On Claude Code
  additionally: `/respec-design-sync` pushes the component library up so designs start from real
  components, and the contract can name a live design project.

## Guiding principles

**Python is invisible to the user.** respec-ai is written in Python and its MCP server runs Python;
neither fact may reach the user. Their contact surface is the CLI, the generated agent markdown,
`stack.toml`, and the standards TOMLs — nothing in it should imply a language for either respec-ai or
their project. This is an acceptance criterion, not a nicety: Python source in a `.tsx` file (**F4**),
a Python traceback as a phase-failure diagnostic (**F6**), and a Python-shaped contract grammar in the
document the user approves (**F5**, **F8**) are all violations of it, not merely bugs.

**The expensive capability is the optional one.** A language needs four things from the materializer,
and they differ enormously in cost. Test-scaffold rendering is nearly free — `language_standards.json`
already carries `testing.framework`, `.location`, and `.naming` for all 26 languages (**F21**).
Declaration rendering is a small template. Signature parsing is one grammar. But introspecting
*existing* source is genuinely expensive: Python has stdlib `ast`; TypeScript, Go, and Rust each need
a parser or heuristics. So introspection is **optional** on the protocol. Languages that have it get
merge and reconciliation; languages that don't degrade to create-only with an explicit notice — never
a silent skip, never Python in a foreign file. Adding a language requires only the two cheap
capabilities.

**Score is not the lever; blockers are.** At ~7.5/100 relative weight, nothing a domain reviewer says
can move the composite meaningfully (**F11**). But `decide_next_loop_action` requires
`score >= threshold AND not latest_blockers`, and blockers propagate regardless of weight (**F12**).
So deterministic signals matter because they justify blockers. Phase 6 additionally makes the score
meaningful by scaling weight to phase shape — but blockers remain the hard gate.

**Portable core, tiered extensions — parity must not cap the best TUI.** respec-ai generates for Claude
Code, OpenCode, and Codex. Everything load-bearing works on all three: the UX Contract's
`##### Design Source` names a local handoff bundle, tokens file, or components to match, and that path
is fully supported everywhere. But where one TUI can do more, it should. Claude Code gets Claude Design
wired properly (phase 8) — a component library pushed up, design decisions read back down. OpenCode and
Codex get the capability declaration point and nothing else, because they have nothing equivalent to
declare *yet*; when they do, it is an adapter change rather than a redesign.

The invariant: extensions may make a TUI better, never make the others worse, and no portable behavior
may come to depend on one. `TuiAdapter` already models this — `ask_user_question_tool_name` returns
`str | None` and generated prose branches on it (**F29**) — so tiering reuses an existing pattern rather
than adding machinery.

**Design contracts are approved by the human before the machine scores against them.** Inherited from
the v2 refactor and unchanged: the UX Contract is authored in shape mode, edited by the user at Gate
1a, and only then becomes the thing the reviewer enforces. No new gate is added — a separate approval
step would add a stop without adding a decision.

## Phases

Eight phases. Phase 0 is a repair that unblocks verification for everything else; phases 1–3 make the
spine language-agnostic; phases 4–7 build the frontend design and review loops.

| # | Phase | Delivers | Depends on |
|---|---|---|---|
| [0](phase-0-reviewer-registration.md) | Reviewer registration repair | `/respec-code` works again; the drift bug class made impossible | — |
| [1](phase-1-language-seam.md) | The language seam | `LanguageMaterializer` protocol + registry; extension map; Python and TypeScript | 0 |
| [2](phase-2-language-grammar.md) | Per-language contract grammar | Architect emits language-appropriate Skeleton Index and Test List entries | 1 |
| [3](phase-3-polyglot-stack.md) | Polyglot stack config | Per-language stack tables; `dev_command`/`base_url`; styling fields reach disk | 1 |
| [4](phase-4-ux-contract.md) | The UX Contract | Routes, states, flows with pass conditions, a11y, breakpoints, design source | 0 |
| [5](phase-5-frontend-preflight.md) | `respec-ai frontend-preflight` | Deterministic app state: dev server lifecycle, scratch dir, readiness probe | 3 |
| [6](phase-6-shape-aware-weighting.md) | Shape-aware review weighting | Domain weight scales with what the phase is about | 1, 4 |
| [7](phase-7-frontend-reviewer.md) | The frontend reviewer | Source + rendered-page evidence scored against the UX Contract | 4, 5 |
| [8](phase-8-claude-design.md) | Claude Design integration | Per-TUI capability tiering; `/respec-design-sync` for Claude Code | 4 |
| [9](phase-9-coder-split.md) | Split the coder | `coder_contracts.py` + frontend/backend coders, dispatched per Step | 1, 4 |

**Why this order.** Phase 0 is a live-bug repair measured in hours, and nothing downstream is
verifiable end-to-end until it lands. Phase 1 is the largest and highest-value piece — it is what makes
frontend code eligible for the TDD spine at all, and it is independently shippable: a project gains
correct TypeScript materialization whether or not any later phase exists. Phase 4 touches only prompts
and is independent of the seam, so it can run in parallel with 1–3 if two people are working. Phases 5
and 7 are the browser work, deliberately last — they are the most expensive and the least certain, and
they are worth little without the contract from phase 4 to score against. Phase 8 depends only on phase
4 and can be taken whenever a Claude Code user wants the round-trip; its reviewer half wants phase 7
first. Phase 9 splits the coder — worth doing on its own merits, since it shrinks a 648-line template
that already carries two modes, but sequenced late because phase 7's seam review is what verifies two
independent coders actually met in the middle.

**One structural note that spans phases 7 and 9.** The frontend and backend coders never communicate.
Their coordination is the *design contract* — `### Skeleton Index` and `### Collaboration And Wiring`,
approved by the human at the shape gate and materialized as skeleton files. Phase 7's seam review then
verifies empirically, using real request/response evidence, that the two sides integrate. If you are
reading phase 9 and wondering where inter-agent coordination went, that is the answer: design-time
agreement plus runtime verification, rather than runtime negotiation.

**Stopping early is a real option.** Phases 0–4 alone fix a workflow-breaking regression, stop silent
code corruption, make polyglot projects configurable, and give the user a structured place to pin down
the visual decisions that are hardest to author. That is a shipped win even if the browser work never
happens.

## Cross-cutting risks

**1. The seam is the feature.** Phase 1's protocol boundary determines whether adding Go later is a
contribution or a refactor. If any part of adding a language requires editing code outside that
language's own materializer module, the boundary is drawn wrong. That is a phase 1 bug, and it is much
cheaper to find at phase 1 than at phase 9.

**2. Weight changes affect existing users.** Phase 0 rebalances core weights and phase 6 makes the
domain pool variable. Both change composite scores for projects that are running today. The
regression-safety property — a backend-only phase scores *numerically identically* to before — must be
asserted by test in both phases, not assumed.

**3. Contract quality, not contract presence.** A UX Contract whose Interaction Flows say "the page
looks right" is worse than none: it gives the reviewer false authority to emit blockers. Phase 4's
exit criteria include a manual read of real generated output, and phase 7's rubric is designed so that
only mechanically-checkable conditions may block.

**4. Determinism of the reviewed application.** If the app is in a different state each iteration, the
reviewer's feedback is noise and the loop cannot converge. Phase 5 exists entirely to make that state
reproducible, which is why it is a separate phase rather than part of phase 7.
