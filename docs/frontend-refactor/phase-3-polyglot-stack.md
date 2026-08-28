# Phase 3 — Polyglot stack config

**Depends on:** Phase 1. **Blocks:** Phase 5.
**Risk:** moderate. `ProjectStack` is read in several places and the change is structural.

## Start here

**Prerequisites:** Phase 1 complete. Verify: `grep -rn "LanguageMaterializer" src/utils/` returns
output.

**Already done?** `grep -n "css_framework" src/platform/standards_config.py` — output means complete.

**Read first:** [README.md](README.md), `docs/phase-refactor/testing.md`, `CLAUDE.md`, and
[findings.md](findings.md) **F2**, **F22**, **F23**, **F25**. The
[deferred-issues.md](deferred-issues.md) entry *"Fully polyglot `ProjectStack`"* defines this phase's
boundary — read it before deciding how far to go, because "make `ProjectStack` polyglot" is a much
larger change than what frontend support requires.

**First action:** write B1 — a Python-backend + React-frontend project puts `frontend_framework` under
`[language.typescript]` — and watch it fail against the current renderer. It fails in a specific and
instructive way, and seeing it makes the rest of the phase obvious.

**Scope discipline is the main risk here.** The flat single-language assumption reaches into detection,
prompts, and several agent instructions. Chasing all of it balloons the phase. The boundary: fix what
makes a polyglot project *configure correctly*, and stop. Consumers that need per-file language
resolution should use the extension map from phase 1, not per-project stack data.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Make a polyglot project — a Python backend and a React frontend, the common frontend case — configure
correctly, and add the optional keys phase 5 needs to start a dev server.

## Why this blocks frontend work

`render_stack_toml` (`standards_config.py:475-497`, attachment logic `:480-487`) attaches every stack
attribute to `primary_language` only, because `ProjectStack` (`models/project.py:11-31`) is flat and
single-language.

For a Python+React project the generated `stack.toml` contains `frontend_framework = "react"` under
**`[language.python]`**, while `[language.typescript]` gets empty strings for `frontend_framework`,
`package_manager`, `runtime_version`, `backend_framework`, and the rest.

Two compounding causes (**F2**):
- `detect_project_stack` (`tooling_defaults.py:283-292`) checks `pyproject.toml` first and runs exactly
  one detector, so the JS/TS half is never detected at all.
- `BUILD_FILE_TO_LANGUAGE` (`:47-53`) insertion order puts `pyproject.toml` first, so
  `detected_languages[0]` — and therefore `primary_language` (`:294-295`) — is Python whenever a
  `pyproject.toml` exists.

Nearly every frontend project is polyglot, so nothing downstream can trust the stack config until this
is fixed. Phase 5's preflight reads `dev_command` from a per-language table that does not yet reliably
exist.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A Python+React project puts `frontend_framework` under `[language.typescript]`, not `[language.python]` |
| B2 | Both languages are detected; neither detector short-circuits the other |
| B3 | `css_framework` and `ui_components` reach disk and survive a re-render |
| B4 | `dev_command`, `base_url`, `storage_state_path` round-trip and are **optional** — absence validates clean |
| B5 | A TypeScript project's configured `type_checker` is honored, not silently dropped |
| B6 | A single-language project produces a `stack.toml` identical to today |
| B7 | Materialization sourcing language from `stack.toml` agrees with extension-map resolution |

B6 is the regression guard. B7 is the phase-1 reconciliation — see below.

## Scope

### Per-language stack attributes

`ProjectStack` (`models/project.py:11-31`) becomes language-keyed for the attributes that genuinely
vary by language: `frontend_framework`, `css_framework`, `ui_components`, `package_manager`,
`runtime_version`, `type_checker`. (`test_runner` was already correctly per-language via the
`tooling: dict[str, LanguageTooling]` parameter `render_stack_toml` already took — no change needed
there; verified during implementation.) Project-level attributes — `architecture`, `api_style`,
`database`, `backend_framework` — stay flat; they describe the project, not a language, and a
project is assumed to have one backend.

Implemented as a new `LanguageStackProfile` model (mirroring the existing `LanguageTooling` /
`ProjectToolingConfig` shape) and a `ProjectStack.language_stack: dict[str, LanguageStackProfile]`
field, replacing the old flat `frontend_framework`/`css_framework`/`ui_components`/
`package_manager`/`runtime_version`/`type_checker` fields (breaking change, per README).

`render_stack_toml:475-497` distributes accordingly instead of attaching everything to
`primary_language`.

`LanguageTooling` (`:33-40`) and `ProjectToolingConfig` (`:43-47`) are already language-keyed dicts and
need no change — worth reading as the shape to follow.

### Detection

`detect_project_stack` (`tooling_defaults.py:283-292`) runs **all** matching detectors, not the first.
A repo with both `pyproject.toml` and `package.json` gets both halves.

`_detect_from_pyproject` (`:162-215`) is Python-only framework/version parsing and is fine as *one
branch* — but note there is no equivalent for `go.mod` or `Cargo.toml`: `:288-290` produce a bare
`ProjectStack(language='go')` with no framework or version detection. Out of scope to fix here; worth
knowing it is a hole.

De-privilege Python in `BUILD_FILE_TO_LANGUAGE:47-53` primary-language selection. Making the heuristic
genuinely *smart* is deferred (see [deferred-issues.md](deferred-issues.md)); making it not
accidentally-Python-by-dict-ordering is in scope.

### New optional keys

Add `dev_command`, `base_url`, and `storage_state_path` to the `[language.<lang>]` table.

**They must stay optional.** `_validate_stack_v2:384-392` requires the four `*_command` keys; do not
add these to that tuple. Their absence is exactly the signal phase 5's preflight uses to skip cleanly —
making them required breaks every existing backend-only project.

**Put them in the stack table, not the standards `[commands]` table.** `render_language_toml`
(`:288-296`) writes exactly `test`, `coverage`, `type_check`, `lint` and **drops any extra key on
re-render** (**F22**). A `dev_command` added there vanishes the next time standards are rendered.

### Fixes that ride along

- **`css_framework` / `ui_components` reach disk** (**F23**). Both are modeled at `models/project.py:29-30`
  and neither is emitted by `render_stack_toml:483`, while `frontend_reviewer.py:134` tells the
  reviewer `stack.toml` is the source of truth for *"frontend framework, rendering strategy, component
  model, and styling system."* Three of those four have no field that reaches disk. Update that prompt
  line once the fields exist.
- **Drop the `language == 'python'` gate on `type_checker`** in `apply_stack_to_tooling`
  (`tooling_defaults.py:83-105`) (**F25**). A TypeScript project setting `type_checker` currently has
  it silently ignored.
- **`stack_prompts.py:8-18`** offers only `ty, mypy, pyright, pytype` — all Python — as type-checker
  options regardless of language. Make the offered list language-aware. `_build_options_list:50-54`
  already prepends detected-but-unlisted values, so this is a smaller change than it looks.
- **Prompt for the new keys during `init`** when a frontend framework is set.

### Reconciling with phase 1

Phase 1 deliberately resolves language from the **extension map**, not `stack.toml`, because the
per-language tables were empty until now (see [decisions.md](decisions.md)). With the tables populated,
`stack.toml` becomes usable as a source.

**Do not switch phase 1 over.** Add `stack.toml` as a *cross-check*: B7 asserts both paths agree. The
extension map stays authoritative for per-entry dispatch — it resolves per *file*, which is what
materialization needs, whereas `stack.toml` resolves per *project*. If they ever disagree, that is a
signal worth surfacing, not a reason to prefer one silently.

## Out of scope

- **Restructuring every `ProjectStack` consumer.** See
  [deferred-issues.md](deferred-issues.md#fully-polyglot-projectstack). Fix configuration; leave the
  rest.
- **A smarter `primary_language` heuristic.** Deferred — the right answer is probably to ask during
  `init` rather than guess better.
- **Go/Rust/Java detection.** The hole at `tooling_defaults.py:288-290` is real and not this phase's.
- **`no_preference` validation** (**F24**). Orthogonal; see [deferred-issues.md](deferred-issues.md).
- **Anything the reviewer reads at review time.** Phase 7.

## Exit criteria

- B1–B7 green.
- A real Python+React scratch project: `respec-ai init` detects both languages, `stack.toml` puts each
  attribute under the right table, `respec-ai validate` is clean, and deleting `dev_command` keeps it
  clean.
- An existing single-language project regenerates a `stack.toml` with identical values for every
  field that existed before this phase; `css_framework`, `ui_components`, `dev_command`, `base_url`,
  and `storage_state_path` are additive new optional fields, not byte-identical to pre-phase-3 output
  (they didn't exist to be identical to — see B3/B4).
- The `frontend_reviewer.py:134` source-of-truth claim is now true.
- `uv run pytest` clean; `respec-ai validate` clean on a polyglot fixture.
