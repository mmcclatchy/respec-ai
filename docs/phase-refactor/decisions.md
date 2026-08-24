# Decision log

Rationale for the design positions in v2, including the rejected alternatives. Four of these changed
during design; those are marked **(revised)** with the original position, because the reasoning that
moved them is the part most likely to be lost.

Read this before re-opening a settled question.

---

## Skeletons are written into the real codebase **(revised)**

**Rejected:** a copy under `.respec-ai/plans/{plan}/phases/{phase}/skeletons/` mirroring the source tree.

**Why:** a second copy of the code is duplication that drifts, and it is the exact failure mode the
design is trying to eliminate. More concretely, a copy under `.respec-ai/` cannot be type-checked
against real imports and cannot be imported by tests — so it can never produce a genuine TDD red
state, only a described one. Written to real paths, mypy and ruff check the seam and scaffolded tests
actually fail.

**Originally:** skeletons lived in the phase bundle, to preserve the boundary that only respec-code
writes source. That boundary turned out to be worth less than the duplication cost, and the
create-only rule below preserves the safety it was protecting.

---

## Skeleton writes are create-only

**Rejected:** overwrite existing files; or merge signatures automatically.

**Why:** on re-runs, patches, and brownfield phases the target file already contains working code. A
clobber destroys it. When the file exists, the workflow shows a signature diff and the user chooses:
accept the design change, keep the existing signature, or merge. This is non-negotiable rather than a
nicety, and its test lands before the write path.

---

## The critic runs *after* user approval **(revised)**

**Rejected:** the conventional order — architect and critic iterate to a quality threshold, then show
the user the polished result.

**Why:** an LLM-polished design the user had no hand in defeats the purpose of the gate. Reversing
the order makes the critic a safety net on the user's judgment rather than a gatekeeper ahead of it.
The act exits only when the user approves **and** the critic passes on that version, tracked via
`Phase.version` (finding F22).

Two consequences: in the shape act, `refine` must route to the user rather than auto-refining, which
is an explicit exception to the mandatory decision protocol at `phase_command.py:417-428` and must be
stated as such. And an override option exists, so the critic cannot hold a design hostage over a
judgment call the user has already made — it only has to be recorded.

**Originally:** critic loop first, gate afterward.

---

## No cap on the number of design decisions **(revised)**

**Rejected:** a hard cap of five open decisions, enforced as a critic blocker.

**Why:** a magic number is a false threshold that truncates a live conversation when there is still
more worth discussing. Replaced with three mechanisms that address the real concern:

- **Rank by blast radius** — how much has to change if this is reversed after implementation.
  Attention goes where reversal is expensive.
- **An explicit user exit** — *"accept the recommended default for all remaining"* at any point. That
  is an informed decision to stop, not a silent cutoff.
- **A critic blocker for under-surfacing** — *"is there a consequential choice that was never
  surfaced as a decision?"* This is the actual risk the cap was clumsily proxying.

Additionally: decision fatigue comes from *bad* decisions, not many. Surfacing a choice with an
obvious answer is the real cost, so options that do not genuinely diverge in structure are themselves
a shape-mode blocker.

**Originally:** `MAX_OPEN_DECISIONS = 5`, fail closed above it.

---

## Frozen fields are repaired, not deleted **(revised)**

**Rejected:** removing `frozen=True` from `objectives`/`scope`/`dependencies`/`deliverables` along
with `FROZEN_PHASES_FIELDS` and the preservation branch.

**Why:** the freeze protects roadmap intent (finding F12) against unattended agent refinement, which
still happens in the detail act. The repaired version binds *agents only* — the human gate is a
sanctioned place to change those four, recorded as a `source=user-edit` Settled Decision — so the
constraint never blocks the user. If it earns less than it costs in practice, deleting it later is
isolated: three call sites plus the constants in `src/utils/state_manager/base.py`.

Note that "keeping" it means **fixing** it: per finding F10 it does not work on the live path today.

**Originally:** delete it, on the grounds that the human gate makes it redundant and that
`store_phase` already bypasses it.

---

## Reuse `LoopType.PHASE` for both acts

**Rejected:** a new `LoopType.SHAPE`.

**Why:** finding F15 — a new loop type requires all three of `shape_threshold`,
`shape_improvement_threshold`, and `shape_checkpoint_frequency` in `LoopConfig`, and omitting one
produces an `AttributeError` at *decision* time, mid-workflow, rather than at import. Reuse keeps the
`LoopConfig` change to pure deletion.

---

## Reuse `CriticAgent.PHASE_CRITIC` with a `phase_mode` scalar

**Rejected:** a dedicated shape-critic agent.

**Why:** finding F16 — a new critic that is in neither `_MARKER_BLOCKER_GATE_CRITICS` nor
`_DOCUMENT_BLOCKER_STAGNATION_CRITICS` silently gates nothing, and nothing in the type system says
so. `PHASE_CRITIC` is already in the latter set. The mode flag follows the existing `phase2_mode` /
`validation_mode` precedent documented in `AGENT_DEVELOPMENT_GUIDELINES.md:180-186`.

---

## `implementation.md` is a bundle sibling, not sections inside `phase.md`

**Rejected:** absorbing the Task content into `phase.md` as an `## Execution Plan` H2.

**Why:** it keeps `phase.md` under the length soft cap without raising it, and it gives build
strategy its own gate rather than making it a byproduct of the shape conversation. The Task
*workflow*, command, loop, agents, and `DocumentType` are still removed — only the artifact survives,
as a file referenced by `phase.md`.

---

## `### Skeleton Index` is the durable contract

**Rejected:** diffing against the git commit that introduced the skeletons.

**Why:** a compact index of `path :: Class.method(sig) -> ret` lines survives rebases and messy
history, is human-readable and hand-editable, and gives the conformance reviewer something stable to
check against. A git baseline is fragile in exactly the situations where drift detection matters most.

---

## Deviation is classified and written back, not enforced

**Rejected:** strict conformance — implementation must match the approved skeleton.

**Why:** the design is a hypothesis and implementation is the experiment. Enforcing conformance makes
a wrong design expensive to escape; abandoning the record silently makes the index a lie, and every
later phase then reasons from a false picture. The middle path is that the coder may deviate, must
record it, and confirmed-legitimate deviations are written back into `### Skeleton Index` so the
record converges toward reality.

The reviewer therefore classifies rather than gates uniformly: a missing designed message blocks; a
new *cross-module* public seam blocks (that is the original complaint reappearing); a module-internal
addition is fine; a changed protocol needs a recorded reason.

---

## Two migrations, not one

**Rejected:** a single migration covering the design layer and the Task removal.

**Why:** Phase 2's migration is purely additive (new columns) and Phase 6's is destructive (dropping
`tasks`, `loop_to_task_mappings`, `phases.task_breakdown`). Splitting them keeps each reviewable, and
rolling back the destructive one does not take the design layer with it.

---

## Skeleton writes go through a CLI subcommand, not the agent's Write tool or an MCP tool

**Rejected:** an MCP tool (`mcp__respec-ai__materialize_skeletons`) that writes files server-side;
also rejected: the agent's own `Write` tool writing every skeleton/test file directly.

**Why:** the MCP server can run in Docker (`src/cli/docker.py`) without filesystem access to the
target project, so an MCP tool cannot reliably write into the user's real source tree. The agent's
own `Write` tool *can*, but B1-B6 (phase-4-skeletons.md) require the create-only guarantee and the
`ty`/`ruff`/`pytest` subprocess checks to run against a pure, independently-testable function —
prompt-driven `Write` calls can't be exercised that way (testing.md: templates resist behavioral
testing). The resolution: `src/utils/skeleton_generator.py` is a plain Python module, unit-tested
directly; `respec-ai materialize-skeletons` (`src/cli/commands/materialize_skeletons.py`) is a thin
CLI wrapper around it, invoked via the `Bash` capability the phase command already holds — the same
pattern `regenerate.py` uses (`Path.cwd()` as project root, no Docker boundary). This kept the
`WRITE` capability grant to source paths unnecessary; only the existing `.respec-ai/plans/*/phases/*`
glob was widened to cover two scratch files that hand section content to the CLI command.

---

## Dropped tables are dropped, not orphaned

**Rejected:** leaving `tasks` and `loop_to_task_mappings` in place, unused.

**Why:** precedent exists at `migrations/017_drop_loop_history_table.sql`, and dead tables with live
foreign keys on a major version are pure confusion. On-disk Task markdown files are derived artifacts
that are fully regenerable by re-running the phase workflow, so no data migration is required for
them — only the directory move handled by `respec-ai migrate`.
