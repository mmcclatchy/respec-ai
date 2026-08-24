# Phase 1 — Bundle restructure

**Depends on:** Phase 0. **Blocks:** Phase 2.
**Risk:** medium — wide but mechanical. Existing user data is affected.

## Start here

**Prerequisites:** Phase 0 complete. Verify:
`grep -rn "Development Environment\|Test Organization" src/platform/templates/` returns nothing.

**Already done?** `grep -n "phase.md" src/platform/path_constants.py` — output means complete.

**Read first:** `docs/phase-refactor/README.md`, `docs/phase-refactor/testing.md`, `CLAUDE.md`. Finding F19 in
`docs/phase-refactor/findings.md` is the motivation.

**First action:** build the legacy-plan fixture described in B2 — a plan with *both*
`phases/{name}.md` and a populated `phases/{name}/`. That is the data-loss case, and having it in
hand shapes the rest of the work.

**This phase touches real user data.** The migration command must be idempotent and must refuse
rather than guess. Test it before shipping it.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Give every phase a directory of its own, so it has somewhere to keep supporting files and so
discovery stops being ambiguous. Pure file-layout change: no new sections, no semantic change, no
workflow behavior change.

## Why

Finding F19 — today `phases/{PHASE_NAME}.md` and `phases/{PHASE_NAME}/` are a sibling file and
directory sharing a stem, so `phases/{PARTIAL}*.md` (`markdown.py:10`) and `Glob(phases/*.md)`
(`:123`) glob a namespace where the phase name denotes two different things.

Later phases need a home for `implementation.md` and `research/`, which is the other half of the
motivation.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A phase is found by name regardless of how many phases share a name prefix |
| B2 | Migrating a plan preserves every phase document and every file already inside a phase directory |
| B3 | Migrating twice changes nothing the second time |
| B4 | Migration refuses rather than merges when the target is ambiguous |
| B5 | Every workflow that locates a phase finds it on the new layout |

B2 is the one that matters. The dangerous input is a plan that has *both* `phases/{name}.md` and a
populated `phases/{name}/` — the case that silently loses data if handled naively (finding F19). Build
that fixture first and assert on content, not on file counts:

```python
def test_migration_preserves_phase_content_and_existing_directory_contents(legacy_plan):
    before = read_all_files(legacy_plan)
    migrate(legacy_plan)
    assert set(before.values()) == set(read_all_files(legacy_plan).values())
```

Note: comparing by basename (as an earlier draft of this snippet did) breaks the moment two phases
exist, because `phase-1-foo.md` and `phase-2-bar.md` both migrate to a basename of `phase.md` and
collide in the dict. Compare the multiset of file *contents* under the plan root instead.

B1 is behavioral rather than a path-string assertion — it should pass whatever the layout is, which
is exactly why it is worth writing. Give it phases named `auth`, `auth-tokens`, and `auth-tokens-v2`
so prefix ambiguity is real.

B5 is covered by the end-to-end check rather than a unit test; keep it on the list so it is not
forgotten.

## Target layout

```
.respec-ai/plans/{plan}/
  plan.md
  plan-state.md
  phases/
    phase-{N}-{title}/
      phase.md            ← the MCP-stored Phase document
      implementation.md   ← added in Phase 5
      research/*.md       ← bp synthesis output
```

Discovery becomes `Glob(phases/*/phase.md)` — unambiguous.

Skeletons are deliberately absent: they live in the real codebase (see
[decisions.md](decisions.md)).

## Scope

### Path construction

`src/platform/path_constants.py:6-46`:
- `build_phase_path` → `.../phases/{phase}/phase.md`
- `build_research_path` → new
- `build_task_path` — leave for now; Phase 6 removes it. Verified at implementation time: it already
  built `.../phases/{phase}/tasks/{task}.md`, i.e. already matched the bundle layout, so no change was
  needed here.

### Adapters

All four `src/platform/adapters/*.py`. For markdown the concentrated set is
`markdown.py:10,16,61,95-127,135-155` — glob patterns, read/write/edit tool renderings, the example
path at `:151`, and the `mkdir -p` instruction at `:155`.

### Command discovery

`phase_command.py:180-241` — the multi-match disambiguation logic. Canonical phase name now comes
from the *directory* basename, not the file stem. Same treatment in `task_command.py:26-128`,
`code_command.py:62-170`, and `patch_command.py:200-267`, which all repeat the pattern.

### Migration command

New `respec-ai migrate` CLI subcommand (`src/cli/commands/`, registered in `src/cli/main.py:41-120`
and `src/cli/commands/__init__.py`).

For each `phases/{name}.md`: create `phases/{name}/`, move the file to `phases/{name}/phase.md`, and
merge any pre-existing `phases/{name}/` contents. Must be idempotent and must refuse to run on a
dirty target rather than merging blindly.

## Out of scope

New Phase sections or fields. Any change to what the workflow *does*.

## Exit criteria

- [x] B1–B4 observed failing first, then pass. (B1 was written as a regression guard rather than a red
      step — it holds on both the old and new layout by design, per the note above.)
- [x] `tests/unit/platform_tests/test_path_constants.py` updated. Prefer assertions about *what
      resolves* over assertions about literal path strings — the latter re-break on any future layout
      change without catching a real defect.
- [x] `tests/integration/test_markdown_platform_scoping.py` green.
- [x] `uv run pytest` green.
- [x] `uv run respec-ai regenerate` valid for all three TUIs. Verified via direct
      `generate_templates()` calls for claude-code, opencode, and codex (the `respec-ai init --tui
      opencode/codex` CLI path additionally requires those tools' own CLIs and model-tier config to be
      present locally, which is an environment dependency unrelated to this phase).
- [x] Manual (B5): on a scratch project with existing phases, ran `respec-ai migrate`, confirmed
      content and existing `tasks/` contents preserved, second run a no-op. Full `respec-phase` /
      `respec-task` / `respec-code` execution needs a live agent session and was not run end-to-end in
      this pass — the generated templates were confirmed structurally correct (canonical-name
      extraction, bundle paths, mkdir precedent) for all three TUIs instead.
- [x] Manual: run `respec-ai migrate` on an already-migrated project — no changes, no errors.
