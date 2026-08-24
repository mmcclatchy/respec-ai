# Phase 4 — Skeleton materialization

**Depends on:** Phase 3. **Independent of:** Phase 5 (either order, or parallel).
**Risk:** the create-only rule is the danger — a clobber destroys working code.

## Start here

**Prerequisites:** Phase 3 complete. Verify: `grep -rn "validate_document" src/mcp/tools/` returns
output.

**Already done?** `grep -rn "skeleton" src/platform/templates/commands/phase_command.py` — output
means complete.

**Read first:** `docs/phase-refactor/README.md`, `docs/phase-refactor/testing.md`, `CLAUDE.md`, and the
skeletons-in-the-codebase and create-only entries in `docs/phase-refactor/decisions.md`.

**First action: write B1 — "an existing source file is never overwritten" — before any write path
exists.** This is the most important test in the rework. A clobber destroys a user's working code and
nothing downstream recovers it. If you build the write path first and test after, delete the write
path, confirm the test goes red, and restore it. The ordering is the safeguard, not a formality.

**This phase is unusually testable.** Skeleton generation produces real files, so `mypy`, `ruff`, and
`pytest` can be run against the output as subprocesses. Use that — do not settle for asserting on
generated strings.

**Note the boundary change:** this is the first time the phase workflow writes real source. That is
deliberate and decided; see `decisions.md`. It does not license writing anywhere else.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Turn `### Skeleton Index` from a description into real files at real source paths, with scaffolded
failing tests. This is what makes the design verifiable rather than aspirational, and what gives
respec-code a genuine TDD red state to work from.

## Why the real codebase

See [decisions.md](decisions.md). Briefly: a copy under `.respec-ai/` is duplication that drifts,
cannot be type-checked against real imports, and cannot be imported by tests — so it can only ever
describe a red state, never produce one.

```python
# src/kb/neo4j_client.py — written at the shape gate
class Neo4jClient:
    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        raise NotImplementedError

    async def query(self, cypher: str) -> list[BestPractice]:
        """Execute Cypher, return structured results."""
        raise NotImplementedError
```

## Behaviors to pin (red step — write these first)

This is the most testable phase in the rework: skeleton generation produces real files, so the
behaviors are directly executable. Do not waste that on string assertions.

| # | Behavior |
|---|---|
| B1 | **An existing source file is never overwritten** |
| B2 | A divergent existing signature raises the reconciliation choice instead of proceeding silently |
| B3 | Generated skeletons type-check |
| B4 | Generated skeletons satisfy the project's own coding standards |
| B5 | Generated tests fail before implementation — a genuine red state |
| B6 | Generated tests pass once the seams are implemented |
| B7 | Skeletons are written only from a design the user approved and the critic passed |

**B1 is the single most important test in the entire suite.** A clobber destroys a user's working
code and nothing downstream recovers it. Write it before the write path exists, and assert on file
*content*, not on a "would overwrite" flag:

```python
def test_existing_source_file_is_never_overwritten(tmp_project):
    original = write_file(tmp_project / 'src/kb/client.py', IMPLEMENTED_SOURCE)
    generate_skeletons(tmp_project, index_naming(tmp_project / 'src/kb/client.py'))
    assert read_file(tmp_project / 'src/kb/client.py') == original
```

**B3–B6 run real tools** — invoke `mypy`, `ruff`, and `pytest` as subprocesses against a temp project
and assert on exit codes. That is the behavior the feature promises, stated exactly.

B5 and B6 together are the TDD promise of the feature made testable: red before, green after. Drive
B6 by filling one seam with a trivial correct implementation inside the test.

**B7** is a sequencing behavior — assert that no files are written when the gate has not passed. Drive
it by running the act with a critic that fails and asserting the source tree is untouched.

## Scope

### 1. Create-only enforcement — build and test this first

**Non-negotiable.** If a target path already exists — re-runs, patches, brownfield phases — the
workflow does **not** write. It extracts the current public signatures, diffs them against
`### Skeleton Index`, and presents:

1. Accept the design change (record an SD; the coder reconciles during implementation)
2. Keep the existing signature (update `### Skeleton Index` to match reality)
3. Merge — add only the genuinely new members

Write the test before the write path. A single clobber destroys a user's working code, and no amount
of downstream review recovers it.

### 2. Write step

Inserted into the shape act after the joint gate passes (Phase 3, Step 11) and before the gate flips
to `shape-settled`. Ordering matters: skeletons are written from the design the user approved *and*
the critic passed, never from an intermediate draft.

For each entry in `### Skeleton Index`:
- New path → write the skeleton: imports, class, public signatures with full type annotations,
  docstrings where the "why" is not obvious, bodies `raise NotImplementedError`.
- Existing path → the diff conversation above.

For each entry in `### Test List`:
- Write the test file with named test functions matching the behaviors, each failing (`assert False`
  with the behavior described, or a call into the unimplemented seam).

Respect `CLAUDE.md` project standards in generated skeletons — full typing, `str | None` syntax,
absolute imports at top, no obvious docstrings. The skeletons are the first thing the user reads;
generating code that violates the project's own standards undermines the whole gate.

### 3. The `design:` commit

Commit skeletons and scaffolded tests as their own commit before the detail act begins. This gives a
clean baseline in history and makes the red state visible. respec-code already does checkpoint
commits (`code_command.py:648-653`), so committing from a workflow is in-pattern.

Conventional-commit style per `CLAUDE.md`, no attribution lines.

### 4. Boundary amendment

`phase_command.py:805-819` currently forbids the phase workflow from writing files mid-workflow.
Amend to permit create-only skeleton writes at the gate, scoped to paths named in
`### Skeleton Index` and `### Test List`.

`coder.py:88`'s prohibition concerns *planning documents* and is unaffected.

Add the needed capabilities to `create_phase_command_tools`
(`src/platform/template_helpers.py:150-168`): `WRITE` scoped to source paths, and `BASH` for the
commit (already present).

### 5. Coder handoff

`coder.py` — the skeleton files now already exist at their real paths. Fill in bodies, honor the
signatures, record any deviation in the iteration handoff report. Internal structure remains the
coder's own. Remove the instruction to create files from scratch (`coder.py:439-443` assumes a
Phase-defined structure that previously did not exist).

## Out of scope

The conformance reviewer (Phase 7). `implementation.md` (Phase 5).

## Exit criteria

- [ ] B1–B7 observed failing first, then pass.
- [ ] **B1 was written before the write path existed.** If the write path came first, delete it,
      re-run the test to confirm red, and restore — the ordering is the whole safeguard here.
- [ ] B3–B6 invoke real `mypy` / `ruff` / `pytest` subprocesses rather than asserting on generated
      strings.
- [ ] `uv run pytest` green (respec-ai's own suite; scaffolded tests live in the temp project).
- [ ] `regenerate` valid for all three TUIs.
- [ ] Manual: run a phase on a scratch project; skeletons land at real paths; `mypy` passes on them;
      scaffolded tests fail; the `design:` commit exists.
- [ ] Manual: re-run the same phase; confirm no clobber, diff conversation appears instead.
- [ ] Manual: `respec-code` fills bodies and the scaffolded tests go green.
- [ ] Manual: **read a generated skeleton as a reviewer would.** Are the seams ones you would have
      chosen? This is the Phase 2 quality risk resurfacing in concrete form, and it is now much easier
      to judge because the output is real code.
