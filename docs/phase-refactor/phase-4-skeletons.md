# Phase 4 — Skeleton materialization

**Depends on:** Phase 3. **Independent of:** Phase 5 (either order, or parallel).
**Risk:** the create-only rule is the danger — a clobber destroys working code.

## Start here

**Prerequisites:** Phase 3 complete. Verify: `grep -rn "validate_document" src/mcp/tools/` returns
output.

**Already done?** `ls src/utils/skeleton_generator.py` — file exists means complete. (Note: grepping
"skeleton" in `phase_command.py` gives a false positive — Phase 3 already added the `### Skeleton
Index` field and Step 7's opt-in prompt, neither of which materializes real files.)

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
# src/kb/neo4j_client.py — written at the shape gate, from
# `### Skeleton Index` entries:
#   - `src/kb/neo4j_client.py` :: Neo4jClient.__init__(uri: str, auth: tuple[str, str]) -> None
#   - `src/kb/neo4j_client.py` :: Neo4jClient.query(cypher: str) -> list[kb.models.BestPractice], async
# The dotted `kb.models.BestPractice` reference becomes a real import; `, async` becomes
# `async def`. See "### Skeleton Index signature format" in phase_architect.py.
from kb.models import BestPractice


class Neo4jClient:
    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        raise NotImplementedError

    async def query(self, cypher: str) -> list[BestPractice]:
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

**B3–B6 run real tools** — invoke `ty` (the project's actual type checker; `mypy` is not a project
dependency — see `pyproject.toml`'s dev group, which ships `ty` instead), `ruff`, and `pytest` as
subprocesses against a temp project and assert on exit codes. That is the behavior the feature
promises, stated exactly.

**B3 is only as strong as the test's own type diversity.** An early pass of B3 tested only builtin
types (`str`, `list[str]`) and stayed green while the generator silently produced an unresolved
reference for any Skeleton Index entry referencing a project-defined type — exactly this document's
own worked example (`list[BestPractice]`). Caught by a plan-vs-implementation audit, not by the
original B3 test. Fixed by the dotted-path import convention above; the regression test
(`test_the_plan_document_worked_example_type_checks`) runs this document's literal example through
`ty check`.

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
- New path → write the skeleton: class, public signatures with full type annotations, bodies
  `raise NotImplementedError`. Any type not built into Python must be written in the Skeleton Index
  as a fully-qualified dotted path (`kb.models.BestPractice`, not bare `BestPractice`) — the
  generator derives a real `from kb.models import BestPractice` from it and rewrites the annotation
  to the bare name; a bare non-builtin name has no import and fails `ty check`. `, async` on a
  signature becomes `async def`. **No docstrings are generated.** The Skeleton Index line format
  (`path :: Class.method(args) -> ReturnType[, tags]`) carries no docstring text, so there is nothing
  for a mechanical generator to emit — a docstring capturing non-obvious "why" is the coder's job
  during implementation, same as any other business-logic comment.
- Existing path → the diff conversation above.
- An internal (module-private) class the architect flagged `internal, consequential` but the user did
  not select at Step 7's opt-in prompt is never materialized, even if that prose step fails to strip
  it from the Skeleton Index — a defensive backstop, since the alternative is silently giving the
  user a file for a class they explicitly declined (README cross-cutting risk #1).

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

`phase_command.py`'s `MANDATORY PHASE FILE STORAGE RESTRICTION` banner (in Step 17) forbade writing
any `.md` file mid-workflow outside the Step 8-9 edit gate. Amended to add a fourth sanctioned
mechanism for Step 11.5 skeleton materialization.

`coder.py:88`'s prohibition concerns *planning documents* and is unaffected.

**Implementation deviation from the write-path design below, recorded here per README.md §5:** real
source/test files are **not** written by the agent's own `Write` tool. The MCP server that backs
`{tools.*}` may run in a Docker container without filesystem access to the target project (see
`src/cli/docker.py`), so file-writing logic instead lives in `src/utils/skeleton_generator.py` (pure,
independently unit-tested per B1-B6) wrapped by a new CLI subcommand,
`respec-ai materialize-skeletons` (`src/cli/commands/materialize_skeletons.py`), invoked via the
`Bash` capability the phase command already has. This is the same pattern `regenerate.py` uses
(`Path.cwd()` as project root). Consequently `create_phase_command_tools`
(`src/platform/template_helpers.py`) needed no new source-path `WRITE` grant for the create-only
path — only `BASH` (already present). `WRITE` *was* widened, but narrowly: the existing
`.respec-ai/plans/*/phases/*/phase.md` glob became `.respec-ai/plans/*/phases/*/*.md`, so Step 11.5
can write the two scratch files (`.skeleton-index.md`, `.test-list.md`) that hand the Skeleton
Index / Test List content to the CLI command. The "merge — add only new members" reconciliation
choice is likewise a CLI flag (`--merge-paths`) rather than an agent-side file edit, keeping that
path testable and avoiding a broad write grant to arbitrary source paths.

### 5. Coder handoff

`coder.py` — the skeleton files now already exist at their real paths. Fill in bodies, honor the
signatures, record any deviation in the iteration handoff report. Internal structure remains the
coder's own. Remove the instruction to create files from scratch (`coder.py:439-443` assumes a
Phase-defined structure that previously did not exist).

## Out of scope

The conformance reviewer (Phase 7). `implementation.md` (Phase 5).

## Exit criteria

- [x] B1–B7 observed failing first, then pass.
- [x] **B1 was written before the write path existed.** If the write path came first, delete it,
      re-run the test to confirm red, and restore — the ordering is the whole safeguard here.
      (Verified live during implementation: the create-only guard was stubbed out, B1 went red on a
      content mismatch — not an ImportError — then the guard was restored and B1 went green again.)
- [x] B3–B6 invoke real `ty` / `ruff` / `pytest` subprocesses rather than asserting on generated
      strings.
- [x] **B3 holds for a signature referencing a project-defined type, not just builtins.** A
      plan-vs-implementation audit found the generator emitted no import for cross-module types,
      failing `ty check` on this document's own worked example. Fixed via the dotted-path convention
      (`kb.models.BestPractice` → `from kb.models import BestPractice`); regression test
      `test_the_plan_document_worked_example_type_checks` runs this exact document's example through
      `ty check`.
- [x] `uv run pytest` green (respec-ai's own suite; scaffolded tests live in the temp project).
- [x] `regenerate` valid for all three TUIs — verified by rendering the phase command template
      through `TemplateCoordinator` for `ClaudeCodeAdapter`/`CodexAdapter`/`OpenCodeAdapter` and
      confirming Step 11.5 and the `materialize-skeletons` invocation render for each, plus the full
      suite's existing per-adapter parametrized template tests.
- [x] `respec-ai materialize-skeletons` verified end-to-end on a real scratch directory: writes a new
      skeleton + test file, correctly refuses to touch an existing one and reports the
      reconciliation diff instead.
- [x] Manual: ran a phase on a real scratch git repository
      (`scratchpad/phase4-e2e`), exercising the production code paths for real rather than through
      mocks:
      - Stored a real `Phase` document (with a Skeleton Index and Test List for a small `KBClient`
        feature) through the live `mcp__respec-ai__store_document`/`get_document` MCP tools, proving
        the document round-trip a real workflow would depend on.
      - Ran `respec-ai materialize-skeletons` against that Skeleton Index/Test List exactly as Step
        11.5 does: it wrote `src/kb/client.py` and `tests/unit/kb/test_client.py` at real paths.
      - `ty check src/kb/client.py` passed on the freshly-materialized skeleton.
      - `pytest` on the scaffolded test file failed with two real `AssertionError`s (a genuine red
        state, not a placeholder).
      - Ran the exact Step 11.5 commit sequence (`git add -- <written paths>`, never `-A`) and
        confirmed the commit contains only the two skeleton/test files — unrelated untracked files
        in the tree (`.respec-ai/`, `phase.md`, `pyproject.toml`) were left alone, proving the
        scoped-add guarantee.
      - Re-ran `materialize-skeletons` against the same Skeleton Index: no clobber. It reported
        `reconciliation_needed` for `src/kb/client.py` (signatures matched, since nothing had
        diverged) and `skipped_existing_tests` for the test file; the working tree was unchanged.
      - Hand-filled both method bodies (standing in for `respec-code`, since no live coding agent
        ran against this project) and re-ran `pytest`: both tests went green, and `ty check` still
        passed — the full TDD red-then-green cycle, live.

      **What this does *not* cover:** the Skeleton Index was hand-authored to stand in for a real
      phase-architect + user design conversation, rather than driven through the actual
      `/respec-phase` slash command with live `AskUserQuestion` prompts — that requires a second,
      independent Claude Code session with a human present to answer them, which this pass could not
      supply. Everything downstream of "a Skeleton Index exists" was exercised against the real
      production code paths (the CLI command, the generator module, real `ty`/`pytest`, a real git
      repo), not simulated.
- [x] Manual: **read the generated skeleton as a reviewer would.**
      ```python
      class KBClient:
          def __init__(self, entries: list[str]) -> None:
              raise NotImplementedError

          def query(self, keyword: str) -> list[str]:
              raise NotImplementedError
      ```
      Both seams are genuinely public and necessary — a constructor and the one query method the
      feature needs — with no speculative abstraction, no unnecessary comments, full typing, and no
      obvious docstrings, matching `CLAUDE.md` as intended. Because this Skeleton Index was
      hand-authored rather than architect-generated, this judges the *generator's* rendering quality
      (formatting, typing, standards compliance) rather than the *architect's* seam-choice judgment —
      the latter is the harder question flagged by README cross-cutting risk #1 and can only really be
      assessed against real phase-architect output from a live run.
