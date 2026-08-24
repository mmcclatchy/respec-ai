# Phase 6 — Task removal

**Depends on:** Phase 5. **Blocks:** Phase 7.
**Risk:** high — the most cross-file coupling in the project.

## Start here

**Prerequisites:** Phase 5 complete. Verify: `grep -rln "implementation.md" src/platform/templates/`
returns output. Phase 4 is recommended but not strictly required.

**Already done?** `ls src/platform/templates/commands/task_command.py` — "No such file" means
complete.

**Read first:** `docs/phase-refactor/README.md`, `docs/phase-refactor/testing.md`, `CLAUDE.md`. **Read the Traps section
below before writing any code** — findings F13 and F14 describe failures that are silent or that
brick the CLI, and both are easy to trigger accidentally here.

**First action:** write B5, the stale-environment-variable test, and confirm it is green *before* you
delete the `task_*` config fields and red immediately after. That is the trap most likely to reach a
user, because it breaks at import time and affects the whole CLI rather than just the Task path.

**Then confirm Phase 5's migrations are complete.** This phase deletes `task_planner.py`. If any of
the five migrated pieces of logic did not actually land in Phase 5, it is gone. Diff the file against
the Phase 5 migration table before deleting it.

**Work the scope list top-down.** It is ordered by dependency — Group A (models/state) before B
(templates) before C (registries) before D (consumers). Each group compiles independently; going out
of order produces a long tail of import errors that obscure real problems.

**Line numbers below were verified at design time.** Confirm each before acting — this document
cites more of them than any other, and this is the phase where the codebase moves most.

## Goal

Remove the Task workflow entirely: command, agents, loop type, `DocumentType`, tools, state-manager
methods, and tables. Rewire `respec-code` and `respec-patch` to read `phase.md` and
`implementation.md` directly.

Wide but mechanical. It lands late deliberately — by now `implementation.md` exists and is proven, so
the system is never without a home for build ordering.

## Traps — read before starting

> **F14 — `LoopConfig` forbids extra env keys.** `src/utils/setting_configs.py:14-30` sets
> `extra='forbid'` with `env_prefix='LOOP_'`. Deleting `task_threshold`,
> `task_improvement_threshold`, and `task_checkpoint_frequency` means any environment with
> `LOOP_TASK_THRESHOLD` exported raises a `ValidationError` at **import time**, bricking the MCP
> server *and* the CLI — not just the task path. Ship one release with `extra='ignore'` first, or
> document the break prominently in release notes.

> **F13 — positional UPSERT.** Phase 2 already rewrote `postgres.py:453-485`. Dropping
> `phases.task_breakdown` happened there. Verify no further index shift is introduced here.

> `phases.task_breakdown` (the column, dropped in Phase 2) and `DocumentType.TASK_BREAKDOWN` (the
> enum, dropped here) are unrelated things sharing a name.

## Behaviors to pin (red step — write these first)

Removal phases are where behavioral testing pays off most: the suite should prove the *capability*
survives, not that particular symbols are gone.

| # | Behavior |
|---|---|
| B1 | A phase can be implemented end-to-end with no Task anywhere |
| B2 | The coding workflow gets its build order from the implementation plan |
| B3 | The coding workflow refuses to start on a phase whose design was never settled |
| B4 | Reviewer selection still responds to the domains a phase touches |
| B5 | The server and CLI start even when a stale `LOOP_TASK_*` variable is set |
| B6 | An amendment still records its scope and passes the phase-integrity gate |
| B7 | Delivery intent still resolves, with one fewer source |

**B5 is the trap test** (finding F14). `LoopConfig` uses `extra='forbid'` with `env_prefix='LOOP_'`,
so deleting the `task_*` fields turns any environment with `LOOP_TASK_THRESHOLD` exported into an
**import-time** failure that bricks the server and CLI — not just the task path. Write it with
`monkeypatch.setenv` before deleting the fields:

```python
def test_server_starts_with_a_stale_task_threshold_variable_set(monkeypatch):
    monkeypatch.setenv('LOOP_TASK_THRESHOLD', '95')
    importlib.reload(setting_configs)  # must not raise
```

**Do not write tests asserting symbols are absent.** `assert not hasattr(DocumentType, 'TASK')` pins
an implementation detail and tells you nothing about whether the system works. The `EXPECTED_*` counts
derive from `len()` (`template_generator.py:114-115`) and follow automatically; the only place a
literal needs updating is `tests/unit/cli/config/test_template_generator.py`, and that literal is
itself worth replacing with a symbolic reference.

**B1 and B6 are end-to-end**, run against a scratch project. They are the real proof the removal was
complete — a green unit suite after deleting a workflow mostly proves you also deleted its tests.

## Scope, in dependency order

### A. Models and state

1. `src/models/enums.py` — drop `DocumentType.TASK` (`:133`) and `DocumentType.TASK_BREAKDOWN`
   (`:134`); drop `CriticAgent.TASK_CRITIC` (`:68`) and the `BUILD` / `BUILD-CRITIC` / `TASK` aliases
   (`:92-94`).
2. `src/utils/loop_state.py:58` — drop `CriticAgent.TASK_CRITIC` from
   `_DOCUMENT_BLOCKER_STAGNATION_CRITICS`.
3. `src/utils/enums.py:10` — drop `LoopType.TASK`.
4. `src/utils/setting_configs.py:18,24,30` — drop the three `task_*` fields. **See F14 above.**
5. `src/mcp/tools/loop_tools.py:20` — `valid_types = {'plan','roadmap','phase','analyst'}`.
6. Delete `src/models/task.py`; update `src/models/__init__.py`.
7. Delete `src/mcp/tools/task_tools.py`; remove from `document_tools.py:8,19,25,26` (`_tool_map`).
8. `src/utils/state_manager/base.py:154-185` — delete the nine task abstract methods and the `Task`
   import at `:9`.
9. `src/utils/state_manager/in_memory.py` and `postgres.py:708,716-841` — delete implementations,
   `_row_to_task:80`, and `loop_to_task_mappings` queries.
10. Migration `029_v2_drop_tasks.sql` — `DROP TABLE tasks; DROP TABLE loop_to_task_mappings;`
    Drop, do not orphan — precedent at `migrations/017_drop_loop_history_table.sql`.

No on-disk Task migration is needed: `.md` Task files are derived artifacts, fully regenerable by
re-running the phase workflow. State this in release notes.

### B. Templates and agents

11. Delete `src/platform/templates/agents/task_planner.py` and `task_plan_critic.py`; update
    `templates/agents/__init__.py`.
12. Delete `src/platform/templates/commands/task_command.py`; update `templates/commands/__init__.py`.
13. Delete `src/platform/command_strategies/task_strategy.py`; update `__init__.py` (both the import
    and `__all__`).
14. Delete `src/platform/models/task.py`; update `platform/models/__init__.py:47`.

Confirm the migrations in Phase 5 are complete before deleting `task_planner.py` — the constraint
carry-forward, execution intent, Deferred Risk Register, Research Read Log, and checklist/steps logic
all needed to move.

### C. Registries

15. `src/platform/template_generator.py` — **four edit sites**: `_COMMAND_TEMPLATES:70`;
    `_COMMAND_CATEGORY_BY_NAME:83` (**finding F17** — indexed directly at `:142`, omission is a
    `KeyError`); `_AGENT_NAMES:100-101` (drives `EXPECTED_AGENTS_COUNT` at `:115` via `len()`);
    `_get_agent_specs:233-234,255-256` plus imports at `:34-35,56-57` and tools-builder calls at
    `:225-244`.
16. `src/platform/template_coordinator.py:12,30` — drop `TaskCommandStrategy`.
17. `src/platform/tool_enums.py` — drop `RespecAICommand.TASK:190`; `RespecAIAgent.TASK_PLANNER:159`,
    `TASK_PLAN_CRITIC:160`, `CREATE_TASK:161`, `TASK_CRITIC:165`, and the already-dead
    `PHASE_PLANNER:164`; `AbstractOperation.CREATE_TASK_TOOL:136` and `LIST_PHASE_TASKS_TOOL:137`
    (both already dead — verified no references).
18. `src/platform/template_helpers.py` — delete `create_task_planner_agent_tools`,
    `create_task_plan_critic_agent_tools`, `create_task_tools`; delete `task_command_invocation` from
    `create_phase_command_tools:208-211` and `create_code_command_tools:474-477`; rewire the task-doc
    tool renderers at `:494`, `:508-514`, `:543-555`.
19. `src/platform/tui_adapters/codex.py:18-21` — drop `'respec-task': 'respec-phase'` from
    `_SECONDARY_COMMAND_PARENTS`. `claude_code.py` and `opencode.py` are generic — no edits.
20. `src/platform/startup_validation.py:100-117` — drop `task_sync_instructions`,
    `task_discovery_instructions`, `task_location_hint`, `create_task_tool`, `retrieve_task_tool`,
    `update_task_tool`, `list_tasks_tool` from the required-adapter-property list.
21. `src/platform/platform_orchestrator.py:96-100` — drop the four task tool mappings.
22. `src/platform/adapters/{base,markdown,linear,github}.py` — drop all task-tool and
    task-instruction properties.
23. `src/platform/path_constants.py:10,27-40` — drop `TASKS_DIR` and `build_task_path`.

### D. Consumers

**`code_command.py`:**

- **Step 5 (`:197-273`)** collapses to: init `PHASE_LOOP_ID` (`loop_type="phase"`),
  `link_loop_to_document(doc_type="phase")`, retrieve phase, read `implementation.md` by path. **The
  Task selection menu disappears entirely** — one phase, no ambiguity. Add a fail-closed gate: if
  `### Shape Gate != "shape-settled"`, error and direct the user to `respec-phase`.
  Rename `TASK_LOOP_ID` → `PHASE_LOOP_ID` throughout (`:393`, `:479-482`, `:1124`, and
  `template_helpers.py:394,409,451,466`).
- **Step 6 (`:274-304`)** — `## Architectural Override Proposals` → `#### Shape Amendment Request`
  under `### Design Shape - Additional Sections`. Same suspend-and-direct behavior.
- **Step 6.5 (`:306-328`)** — scan `implementation.md` steps for mode keywords, **and add
  `### Skeleton Index` paths to the scan**. File paths like `migrations/*.sql` or `src/api/routes.py`
  are a far stronger reviewer signal than prose keywords, and they are now available for free.
- **Step 6.7 (`:406-465`)** — read execution intent from `implementation.md`
  `### Execution Intent Policy`. **Collapse the precedence chain from three levels to two**:
  phase-policy → plan-default → default-MVP. `PHASE_OVERRIDE` at `:419-420` is gone (Phase 5 deleted
  `#### Delivery Intent Override`), so `AMBIGUOUS_MODE` at `:443` can now only mean a phase-vs-plan
  conflict.

**`patch_command.py`:**

- patch-planner no longer manufactures a Task. Rewrite it to emit an **amendment scope block** stored
  in the planning loop via the existing `store_review_section`, rather than a document.
- `TASK_LOOP_ID = PLANNING_LOOP_ID` (`:326`, `:531`) → `PHASE_LOOP_ID` linked to the Phase.
- Step 4.1 (`:418-422`) reads the amendment block; Step 4.1.1's `TASK_MODE` (`:427`) reads
  `implementation.md`.
- **The byte-integrity gate (`:1086-1125`) is structurally unchanged and still correct** — finding
  F21, it keys on section *names*, not content. Two edits only: add `Design Shape, Design Decisions`
  to the protected enumeration at `:1101-1103`, and change `- Amendment Task: …` at `:1103` to
  `- Amendment Scope: <summary>`. Patch must never write into `implementation.md` or skeletons.

**`phase_command.py`:** delete Steps 9–10 (`:813-931`) — the fail-closed chain into `respec-task` and
its "exactly one task exists" verification. Replace with a completion contract chaining to
`{tools.code_command_invocation}`.

### E. Documentation

`docs/WORKFLOWS.md`, `ARCHITECTURE.md`, `CLI_GUIDE.md`, `DATABASE_STATE_MANAGER.md`,
`AGENT_DEVELOPMENT_GUIDELINES.md`, `TEMPLATE_AUDIT.md`, `PLAN_WORKFLOW_PATTERNS.md`,
`OPENCODE_INVOCATION_SPEC.md`, plus `README.md`, `CLAUDE.md`, `AGENT.md`, `AGENTS.md`.

Live checklist:

```bash
grep -rn "task" src tests migrations docs --include="*.py" --include="*.sql" --include="*.md" -il
```

Filter out unrelated noise: `rich.progress` `TaskID` / `{task.description}` in
`cli/commands/{sync,regenerate}.py`, and `BuiltInToolCapability.TASK`.

## Out of scope

This phase removes and rewires. It does not improve.

- **No behavior changes to the coding workflow** beyond swapping its input from Task to Phase +
  `implementation.md`. Resist the temptation to fix things you notice in `code_command.py` while you
  are in there — file them, do them separately.
- **No new sections, fields, or agents.** The design layer is Phase 2's; the conformance reviewer is
  Phase 7's.
- **No changes to the shape gate or the implementation-plan gate.** They are already built and
  working.
- **No `implementation.md` schema changes.** If it turns out to be missing something the coding
  workflow needs, that is a Phase 5 defect — go fix it there, with its tests, and return.
- **No refactoring of the patch workflow** beyond what removing Task requires. Its integrity gate is
  correct as-is (finding F21).

The instinct to tidy adjacent code is strong in a removal phase and it is exactly what turns a
mechanical change into an unreviewable one.

## Exit criteria

- [ ] B1–B7 observed failing first, then pass. B5 in particular must be red before the `task_*` field
      deletion, or it is not testing the trap.
- [ ] Deleted tests were *deleted*, not weakened. Any test that previously covered Task behavior
      either has a Phase-based equivalent or is genuinely obsolete — decide which, deliberately, for
      each one.
- [ ] No new test asserts the absence of a symbol.
- [ ] These suites updated: `tests/unit/mcp/test_document_tools.py`, `test_loop_tools.py`,
      `test_loop_management.py`; `tests/unit/models/test_critic_feedback.py`,
      `test_enhanced_loop_state.py`, `test_feedback_enums.py`; `tests/unit/utils/test_enums.py`,
      `test_state_manager.py`, `test_database_state_manager.py`, `test_database_specifics.py`;
      `tests/unit/platform_tests/test_tool_enums_and_validation.py`, `test_tui_adapters.py`,
      `test_path_constants.py`; `tests/unit/cli/config/test_template_generator.py`.
- [ ] Migration `029` applies and rolls back cleanly against a populated database.
- [ ] `uv run pytest` green; `regenerate` valid for all three TUIs.
- [ ] `ls .claude/commands .claude/agents` — no `respec-task*`, no task-planner, no task-plan-critic.
- [ ] Manual (B1): `respec-phase` → `respec-code` end-to-end with no Task anywhere.
- [ ] Manual (B6): `respec-patch` on an implemented phase; the phase-integrity gate still passes.
