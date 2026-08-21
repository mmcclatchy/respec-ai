# respec-ai v2 — Interface-First Phase Design with a Human Gate

Working design documents for a major-version rework of the phase workflow.
Breaking changes are in scope.

---

## Start here — fresh session

If you have just picked this up with no prior context, this section is your entry point.

**1. Read in this order.** All paths are relative to the repository root.

1. `docs/v2/README.md` — this file. Problem, principles, phase index.
2. `docs/v2/testing.md` — **required.** How to test in this codebase. Non-obvious, because
   respec-ai generates prompts and those resist ordinary behavioral testing.
3. `docs/v2/findings.md` — skim now, return to it whenever a phase document asserts something
   surprising about the codebase.
4. `docs/v2/decisions.md` — read before questioning any design choice. Several were reversed during
   design and the reasoning is recorded.
5. The phase document you are implementing.

Also read `CLAUDE.md` at the repository root — project coding standards are mandatory and override
general defaults.

**2. Find out which phase to work on.**

```bash
# Phase 0 done?  → no output means done
grep -rn "Development Environment\|Test Organization" src/platform/templates/
# Phase 1 done?  → output means done
grep -n "phase.md" src/platform/path_constants.py
# Phase 2 done?  → output means done
grep -n "module_layout" src/models/phase.py
# Phase 3 done?  → output means done
grep -rn "validate_document" src/mcp/tools/
# Phase 4 done?  → output means done
grep -rn "skeleton" src/platform/templates/commands/phase_command.py
# Phase 5 done?  → output means done
grep -rln "implementation.md" src/platform/templates/
# Phase 6 done?  → "No such file" means done
ls src/platform/templates/commands/task_command.py
# Phase 7 done?  → file exists means done
ls src/platform/templates/agents/design_conformance_reviewer.py
```

Work the lowest-numbered incomplete phase. Phases 4 and 5 are independent of each other and may be
done in either order.

**3. Line numbers may be stale.** Every `file:line` reference in these documents was verified at
design time. The codebase moves. Before acting on a reference, open it and confirm it says what the
document claims. If it does not, search for the symbol instead, and correct the reference in the
document as part of your change — these documents are meant to be maintained, not archived.

**4. Working agreement.**

- Test-first, always. Each phase document opens with *Behaviors to pin* — write those tests, run
  them, confirm they fail for the right reason, and only then implement.
- Tests pin behavior, not implementation. See `testing.md` for the discriminating question.
- Do not start a phase whose predecessor is incomplete.
- Do not expand a phase's scope. Each has an explicit *Out of scope* section; if something seems
  missing, it is probably deliberately assigned to a later phase.
- Commit per the `CLAUDE.md` convention: conventional-commit style, no attribution lines.

**5. If something in a phase document is wrong or ambiguous,** fix the document as part of the work.
A stale design document is worse than none, and the next session inherits whatever you leave.

---

## The problem

respec-ai works well on greenfield projects, but the gap between what the user understands and
what gets generated is uncomfortably wide, and complex features come out superficial. The user's
only real lever on *how* code gets written is the standards TOMLs, which is far too blunt.

The sharpest symptom — class and service interfaces built ad hoc — has a mechanical cause:

- `phase_architect.py:487-489` explicitly forbids naming files (*"Wrong: Create `src/neo4j_client.py`"*)
  and `:520` justifies it by leaving task-planner *"freedom to choose file organization."*
- `task_planner.py:250-262` lists the required Task sections. None hold file layout or interfaces.
  The architect deferred; the planner was never given a place to receive.
- `coder.py:378,380` tells the coder to *"Match directory organization from Phase Development
  Environment section"* and *"Place tests according to Test Organization specifications."*
  **Neither section can exist** — `src/models/phase.py:14-36` has no such mapping.
  `spec_alignment_reviewer.py:182` grades against the same phantom.

So public seams are invented per-iteration by the coder, and the only corrective signal is post-hoc
review. That is the blackbox.

Separately, the phase workflow is the **only** stage that never actually stops for the user.
`phase_command.py:451-458` displays feedback and returns to Step 5 — no `WAIT`, no
`store_user_feedback`, no prompt — despite its own protocol at `:407` declaring *"user_input → ONLY
status that involves the user."* See [findings.md](findings.md) F5/F6.

## The outcome

The phase workflow becomes a design conversation with three gates:

1. **Shape** — the user approves the public seams as real skeleton code, plus the behaviors to test.
2. **Critic** — runs on what the user approved, as a safety net rather than a gatekeeper ahead of them.
3. **Implementation plan** — the user confirms or alters the build strategy.

respec-code then fills in bodies, and a new reviewer keeps the design record honest about where
reality diverged from the design.

## Guiding principles

**Design the messages, not the internals.** What binds is the protocol between objects: what a
module exposes, what crosses a boundary, what the tests exercise. Everything behind a seam stays the
coder's call and is never a blocker.

**The design is a hypothesis, not a contract.** Implementation will discover things the design got
wrong. The goal is not conformance — it is that deviation is *cheap but never silent*, and that the
design record converges toward reality instead of quietly becoming a lie. That is the difference
between guardrails and bureaucracy.

**The human approves first; the critic checks second.** An LLM critic polishing a design before the
user sees it produces a coherent artifact they had no hand in. Reversing the order makes the critic a
safety net on the user's judgment rather than a gatekeeper ahead of it.

## Phases

Eight phases, each independently shippable and leaving the system working end-to-end. Ordered so
value arrives early and the widest mechanical change lands late, when the target shape is known.

| # | Phase | Delivers | Depends on |
|---|---|---|---|
| [0](phase-0-repairs.md) | Repairs & guard rails | `respec-phase` actually stops for the user; phantom refs fixed; bug class made impossible | — |
| [1](phase-1-bundle.md) | Bundle restructure | `phases/{name}/phase.md`; unambiguous discovery | 0 |
| [2](phase-2-design-layer.md) | Design layer in the document | Architect emits Module Layout / Skeleton Index / Test List; coder consumes them | 1 |
| [3](phase-3-human-gate.md) | `validate_document` + the human gate | User approves the design; critic runs after, not ahead | 2 |
| [4](phase-4-skeletons.md) | Skeleton materialization | Real skeleton files at real paths; genuine TDD red state | 3 |
| [5](phase-5-implementation-plan.md) | `implementation.md` + its gate | Build-strategy conversation | 3 |
| [6](phase-6-task-removal.md) | Task removal | Workflow, DocumentType, tables, rewiring | 5 |
| [7](phase-7-conformance.md) | `design-conformance-reviewer` | Deviation classified and written back | 4, 6 |

**Why this order.** Phase 0 is pure repair and ships in about a day. Phase 2 delivers most of the
quality benefit *before* the gate exists — the architect naming files and seams already fixes the ad
hoc interface problem, so stopping there would still be a net improvement. Phases 4 and 5 are
independent of each other and can be reordered or parallelized. Task removal (6) comes late
deliberately: it is wide and mechanical, and doing it after `implementation.md` exists means the
system is never without a home for build ordering. Phase 7 needs both skeletons on disk (4) and the
Task rewiring done (6).

**Two migrations, not one.** Phase 2 adds columns only (additive, safe). Phase 6 drops `tasks`,
`loop_to_task_mappings`, and `phases.task_breakdown`. Splitting them keeps each reviewable and means
rolling back the destructive one does not take the design layer with it.

## Supporting documents

- **[testing.md](testing.md)** — **required reading before writing any code.** The TDD methodology
  and the behavior-vs-implementation guide for each layer of this codebase. Templates are prompts and
  resist ordinary behavioral testing, so the approach there is deliberate and non-obvious.
- **[findings.md](findings.md)** — 22 verified `file:line` findings underpinning the design. Each was
  confirmed by reading the file, not inferred. This is the perishable asset; treat it as the
  reference when a phase document seems to assume something surprising.
- **[decisions.md](decisions.md)** — the decision log with rejected alternatives and rationale,
  including four positions that changed during design. Read this before re-opening a settled question.

## How every phase is built

**Test-first, behavior-pinned, without exception.** Each phase document opens with a *Behaviors to
pin* list — those are the red step, written and confirmed failing before any implementation. Each
test names the behavior it protects, not the function it calls.

The discriminating question, from [testing.md](testing.md): *if I reimplemented this a completely
different way but kept the observable outcome identical, would this test still pass?* If no, it is an
implementation-detail test and does not belong in the suite.

Phase 0 is the natural starting point for this discipline: several of its tests go red against
existing code, so the red step costs nothing and proves the harness works before anything depends
on it.

## Per-phase exit criteria

Every phase is done when all of the following hold:

- Every behavior in its *Behaviors to pin* list has a test that was observed failing first.
- `uv run pytest` is green.
- `uv run respec-ai regenerate` produces valid artifacts for claude-code, opencode, and codex.
- A real phase runs end-to-end on a scratch project.
- The manual checks in the phase document pass — some properties (design quality above all) are not
  machine-checkable and must be judged by a person.

## Cross-cutting risks

1. **Skeleton quality is the whole feature** (Phases 2 and 4). If the architect produces speculative
   abstraction, the user approves it and the critics enforce it — output gets *worse* than today.
   Mitigated by the unjustified-seam blocker plus manually reviewing the first two or three real runs.
   This is a prompt-quality problem, and prompts drift; treat it as ongoing, not one-and-done.
2. **The postgres UPSERT renumbering** (Phase 2, finding F13) — silent data corruption, not a crash.
3. **Create-only enforcement** (Phase 4) — a clobber destroys working code.
4. **`LoopConfig` import-time break** (Phase 6, finding F14).
5. **Critic drifting into conformance-checking** (Phase 3 onward) — mitigated only by the
   anti-anchoring guard block and observation.
