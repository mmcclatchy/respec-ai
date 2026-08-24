# Phase 2 — Design layer in the document

**Depends on:** Phase 1. **Blocks:** Phase 3.
**Risk:** highest in the project — the postgres UPSERT rewrite.

## Start here

**Prerequisites:** Phase 1 complete. Verify: `grep -n "phase.md" src/platform/path_constants.py`
returns output.

**Already done?** `grep -n "module_layout" src/models/phase.py` — output means complete.

**Read first:** `docs/phase-refactor/README.md`, `docs/phase-refactor/testing.md`, `CLAUDE.md`, and `docs/phase-refactor/decisions.md`
(the seam-index and loop-type entries). Findings F1, F2, F7, F13 are the evidence.

**First action:** write B3 — the field-by-field round-trip test — and run it against **postgres**,
not just in-memory. It must be green before you touch the UPSERT and green after. This is the only
guard against the highest-risk edit in the project.

**Two things in this phase are not machine-checkable** and need your judgment:
1. Section naming must avoid substring collisions (finding F7). The Phase 0 heading-collision test
   catches violations, but choosing good names is on you.
2. Whether the architect produces real design or plausible ceremony. See the manual quality review in
   the exit criteria — this is the main risk here, and no test substitutes for reading the output.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Give the design layer a home. The architect starts naming modules, public seams, and test behaviors;
the coder and spec-alignment reviewer start reading them. **No human gate yet and no skeleton files
yet** — this phase is the document model plus the prompts that fill it.

## Why this lands before the gate

Most of the quality benefit arrives here. The ad hoc interface problem is caused by nobody owning the
design layer (findings F1–F4); giving it an owner fixes it even without human involvement. If work
stopped after this phase, output would still be meaningfully better. The gate in Phase 3 then adds
the user's judgment on top of a layer that already exists.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A phase document with every section populated round-trips with nothing lost |
| B2 | No section name can shadow another (Phase 0's B2, now exercised against the new names) |
| B3 | A stored phase reads back with every field intact — **on both backends** |
| B4 | Roadmap-seeded objectives still survive an agent write after the schema change |
| B5 | The architect names concrete file paths in the design sections and never in Objectives/Scope |
| B6 | A design proposing an abstraction with one implementation and no stated variation is blocked |
| B7 | The coder is instructed to build the modules the design names, at the paths it names |

**B3 is the test that catches the UPSERT hazard** (finding F13). Populate every field with a
*distinct* recognizable value and assert field-by-field equality after a round trip. A transposed
positional parameter surfaces as "field A came back holding field B's value" — which this catches and
which no mock-based test ever will. Run it parametrized across in-memory and postgres.

```python
async def test_stored_phase_reads_back_with_every_field_intact(state_manager, phase_with_distinct_field_values):
    await state_manager.store_phase('plan', phase_with_distinct_field_values)
    assert await state_manager.get_phase('plan', ...) == phase_with_distinct_field_values
```

**B5 and B6 test generated prompts**, so they go through the contract helper rather than grepping.
B6 in particular should assert that the critic *declares* the unjustified-seam rule as a blocker, not
that the template contains a specific sentence:

```python
def test_critic_blocks_abstractions_with_no_stated_axis_of_variation(phase_critic):
    assert 'unjustified-seam' in template_contract(phase_critic).blocker_conditions()
```

That requires the contract helper to learn `blocker_conditions()` — a natural increment on what
Phase 0 built.

**What B5/B6 cannot check** is whether the architect actually produces *good* designs. No test does.
That is the manual quality review in the exit criteria, and it is the highest-risk item in this phase.

## Scope

### 1. Phase model

`src/models/phase.py`. Target tree — additions marked:

```
## Overview            ### Objectives / Scope / Dependencies / Deliverables   (roadmap-seeded, frozen)
## System Design       ### Architecture / Technology Stack / …Additional Sections
## Design Shape        ← NEW
                       ### Module Layout
                       ### Skeleton Index
                       ### Collaboration And Wiring
                       ### Test List
                       ### Design Shape - Additional Sections
## Design Decisions    ← NEW
                       ### Open Design Decisions
                       ### Settled Design Decisions
## Implementation      ### Functional Requirements / Non-Functional Requirements
                       ### Development Plan / Testing Strategy / …Additional Sections
                       (### Task Breakdown — REMOVED)
## Additional Details  ### Implementation Plan References / Research Requirements
                       ### Success Criteria / Integration Context / …Additional Sections
## Metadata            ### Iteration / Version / Status / Shape Gate ← NEW
```

Seven new fields; `task_breakdown` removed from `HEADER_FIELD_MAPPING:14-36`, the field block
`:39-72`, and `build_markdown:96,107-108`.

**Substring-collision audit is mandatory** (finding F7). Verified clean: no H2 contains another —
`System Design` ⊄ `Design Shape`, `Design Shape` ⊄ `Design Decisions`. `Open Design Decisions` and
`Settled Design Decisions` do not contain each other, but **never key a lookup on bare
`Design Decisions`**. **Do not name the metadata field `Shape Status`** — `Status` is a substring of
it and `phase_status` maps to `('Metadata', 'Status')`. Hence `Shape Gate`.

The heading-collision guard test from Phase 0 must stay green through this change. If it goes red,
the naming is wrong, not the test.

New enum in `src/models/enums.py`:

```python
class ShapeGate(str, Enum):
    UNSHAPED = 'unshaped'
    SHAPE_PROPOSED = 'shape-proposed'
    SHAPE_SETTLED = 'shape-settled'
    SHAPE_AMENDED = 'shape-amended'
```

Present but unused this phase; Phase 3 drives it. `str→StrEnum` coercion on parse already works, as
`phase_status` demonstrates.

### 2. Persistence

`src/utils/state_manager/in_memory.py` and `postgres.py`, plus migration
`028_v2_design_layer.sql` — **additive only**: add the seven columns and `shape_gate`, drop
`phases.task_breakdown`. No table drops (those are Phase 6).

> **The dangerous edit.** Finding F13 — the postgres phases UPSERT
> (`src/utils/state_manager/postgres.py:453-485`) uses positional `$1..$19`. Removing one column and
> adding eight shifts every index. **Rewrite the column list and renumber in one pass.** An
> off-by-one here is silent data corruption, not a crash.
>
> **Write B3 before touching the UPSERT.** It is the only thing that reliably catches a
> transposition, and it must be red-then-green against the *postgres* backend specifically — an
> in-memory-only pass proves nothing about positional parameters.

Note `phases.task_breakdown` (column) and `DocumentType.TASK_BREAKDOWN` (enum) are unrelated things
sharing a name. Only the column goes here.

### 3. Architect prompt

`src/platform/templates/agents/phase_architect.py`.

**The central fix, at `:485-508`.** The `❌ Specific File Names` rule becomes *scoped* rather than
global:

```
❌ Specific File Names — in Objectives, Scope, Deliverables, Development Plan
   Wrong: Objectives: "Create `src/neo4j_client.py`"
   Right: Objectives: "Neo4j client module: connection management, query execution"

✅ Specific File Names — REQUIRED in `### Module Layout`, `### Skeleton Index`, `### Test List`
   Right: `src/kb/neo4j_client.py` — owns connection lifecycle + Cypher execution
   Right: `tests/unit/kb/test_neo4j_client.py::test_reconnects_after_timeout`
```

Delete the quality check at `:520` (*"Does task-planner have freedom to choose file organization?"*).
Replace with:
- *"Would two engineers given these skeletons write the same public API? ✓"*
- *"Is every Test List entry an observable behavior, not a file name? ✓"*
- *"Does every abstraction name what varies behind it? ✓"*

`### Skeleton Index` format — one line per public message, the durable contract the Phase 7 reviewer
diffs against:

```
- src/kb/neo4j_client.py :: Neo4jClient.query(cypher: str) -> list[BestPractice]
```

### 4. Critic prompt

`src/platform/templates/agents/phase_critic.py`. Add shape-layer criteria. No `phase_mode` flag yet —
that arrives with the two-act split in Phase 3; here the criteria simply join the existing pass.

**The anti-speculative-abstraction blocker** — the most important addition in this phase:

```
[Unjustified Seam - BLOCKING]: <Interface> has one implementation and no stated axis of
variation. Every skeletoned abstraction must name what varies behind it. If nothing varies
yet, make it a concrete class.
```

Without this, the design layer makes output *worse*: the architect produces plausible ceremony, and
from Phase 3 onward the user approves it and the critics enforce it.

**The anti-anchoring guard**, verbatim block:

```
BINDING SCOPE
Blocker lane, ONLY these:
1. Module boundaries in `### Module Layout`
2. Public seams in `### Skeleton Index`
3. Ownership/construction in `### Collaboration And Wiring`
4. Every SD-### in `### Settled Design Decisions`
5. Test List → implementation-step coverage

Score lane ONLY, NEVER a blocker:
- Private helpers, internal data structures, algorithm choice
- Intra-module file splits, step ordering
- Error message text, naming of locals
- Additions that do not contradict 1-5 (new private modules are ALLOWED)

VIOLATION: emitting a blocker for an internal implementation detail turns this critic
           into a conformance checker and defeats the purpose of keeping the shape thin.
```

Other shape blockers: empty Test List; Test List entries naming files instead of behaviors; skeleton
index entry for a module absent from Module Layout.

### 5. Consumers

- `coder.py:374-385` — replace the Phase 0 interim targets with the real ones: create the modules
  named in `### Module Layout` at the paths given; honor `### Skeleton Index` signatures; wire per
  `### Collaboration And Wiring`; create test files at `### Test List` paths; internal structure is
  the coder's own.
- `spec_alignment_reviewer.py:182` — grade against `### Skeleton Index` and `### Module Layout`.
  Narrow `:183` so alternatives are valid for *internals* only; a different public seam is `[BLOCKING]`.

### 6. Config

`src/utils/setting_configs.py` — add `phase_shape_soft_cap: int = Field(default=10_000, ...)` covering
`## Design Shape` + `## Design Decisions`, threaded to the critic as a blocker threshold via
`PhaseCriticAgentTools`. "Deliberately thin" enforced by prose is not enforced.

## Out of scope

The human gate, `validate_document`, skeleton files on disk, `implementation.md`, any Task removal.

## Exit criteria

- [x] B1–B7 observed failing first, then pass.
- [x] B3 verified against **postgres specifically**, not just in-memory (live db via
      `docker-compose.dev.yml`, `test_design_shape_fields_survive_store_and_retrieve[db_state_manager]`).
- [x] Phase 0's B1 (no phantom section references) still green against the new real targets.
- [x] Phase 0's B2 (no shadowing section names) still green with the new sections.
- [x] `tests/unit/models/test_phase*.py` audited for implementation-detail drift — none found; no
      changes needed.
- [x] `uv run pytest` green (1374 passed); `regenerate` valid for all three TUIs (claude-code,
      opencode, codex) on a scratch project.
- [ ] **Manual: run `respec-phase` on a scratch project** and confirm the Phase contains a concrete
      Module Layout, Skeleton Index, and behavioral Test List. **Not done in this session** — this
      requires a live agent invocation of the phase-architect against a real feature, which the
      implementing session could not perform. Templates were verified to *render* correctly
      (see generated `.claude/agents/respec-phase-architect.md` / `respec-phase-critic.md`), but no
      live architect output was produced or read.
- [ ] **Manual quality review — the main risk in this phase.** Read the generated Skeleton Index
      critically. Is it real design or plausible ceremony? Are there interfaces with one
      implementation? Does every abstraction name what varies behind it? No test makes this judgment,
      and getting it wrong makes output *worse* than before the phase, because from Phase 3 onward the
      user approves it and the critics enforce it. Do this on at least two different features before
      declaring the phase done. **Not done — blocked on the same live-run gap above.**
