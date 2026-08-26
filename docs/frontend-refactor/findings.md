# Verified findings

Each finding below was confirmed by reading the referenced file, not inferred from documentation or
naming. Line numbers reflect the state of the codebase at the time of the frontend design work; if a
reference no longer matches, re-verify before acting on it and correct the reference here.

These are the load-bearing facts underneath [README.md](README.md) and the phase documents. Phase
documents cite findings by number rather than restating the evidence.

---

## Blocking defects in shipped code

**F1 — `design-conformance-reviewer` is rostered but unregistered; HEAD is broken.**
`src/platform/reviewer_mapping.py:33` appends `'design-conformance-reviewer'` whenever the phase has
a Skeleton Index. The same append is duplicated in prose at
`src/platform/templates/commands/code_command.py:329` and
`src/platform/templates/commands/patch_command.py:397`, and
`src/platform/template_helpers.py:1031` has the agent store with `max_score='50'`.

But `CriticAgent` (`src/models/enums.py:70-83`) has **no** `DESIGN_CONFORMANCE_REVIEWER` member, so
`_parse_reviewer_name` (`src/mcp/tools/feedback_tools_unified.py:730-735`) raises
`ToolError('Unknown reviewer_name: design-conformance-reviewer')`.

Effect: every `/respec-code` run against a phase with a non-empty Skeleton Index fails at the
reviewer's `store_reviewer_result`, then fails again at `consolidate_review_cycle`. Introduced in
commit `22cfd24` ("add design-conformance-reviewer and close the write-back loop (Phase 7)").

**Why it survived:** `tests/unit/platform_tests/test_reviewer_mapping.py:95-100` asserts only that
the *string* appears in the returned roster. Nothing cross-checks roster output against enum
membership, max-score coverage, or weight-table coverage.

**F2 — Polyglot projects are silently mis-configured.**
`render_stack_toml` (`src/platform/standards_config.py:475-497`, attachment logic at `:480-487`)
attaches every stack attribute to `primary_language` only, because `ProjectStack`
(`src/platform/models/project.py:11-31`) is a flat single-language model.

For a Python backend + React frontend, the generated `stack.toml` contains
`frontend_framework = "react"` under **`[language.python]`**, while `[language.typescript]` gets
empty strings for `frontend_framework`, `package_manager`, `runtime_version`, and the rest.

Two compounding causes:
- `detect_project_stack` (`src/platform/tooling_defaults.py:283-292`) checks `pyproject.toml` first
  and runs exactly one detector, so the JS/TS half of a polyglot repo is never detected at all.
- `BUILD_FILE_TO_LANGUAGE` (`:47-53`) dict insertion order puts `pyproject.toml` first, and
  `detect_project_tooling` iterates in that order, so `detected_languages[0]` — and therefore
  `primary_language` (`:294-295`) — is Python whenever a `pyproject.toml` exists, regardless of the
  project's actual center of gravity.

Nearly every frontend project is polyglot, so frontend support is impossible until this is fixed.

---

## The materialization layer has no language seam

**F3 — The materialization pipeline has no language parameter anywhere.**
This is the headline finding. It is not "Python with some hardcoding" — there is no language input
at any point in the path:

- `phase_command.py:697` invokes `respec-ai materialize-skeletons --skeleton-index-file …
  --test-list-file …` — no `--language`.
- `src/cli/commands/materialize_skeletons.py:37-38` — `run()` takes only `Path.cwd()` plus two
  markdown blobs.
- `src/utils/skeleton_generator.py` never imports `standards_config` or `tooling_defaults`.

The only consumer of `stack.toml` anywhere in the codebase is **prose inside agent prompts**
(`coder.py:179` and the four domain reviewers). The redesign must *add* a language-resolution layer,
not swap a renderer.

**F4 — `skeleton_generator.py` emits Python source unconditionally.**

| Line | Assumption | Effect |
|---|---|---|
| `153-161` `_render_member_body` | `def`/`async def`, `-> Ret:`, 4-space indent, `raise NotImplementedError` | Silently corrupts |
| `155-156` | Injects `self` as first method param | Silently corrupts |
| `164-168` `_render_import_lines` | `from {module} import {name}` | Silently corrupts |
| `186` | `class {name}:` colon-and-indent block form | Silently corrupts |
| `193-197` `render_test_module` | `def test_x() -> None: raise AssertionError(...)` — pytest bare-function convention | Silently corrupts |
| `190` | `\n\n\n` block join (PEP 8) | Cosmetic |

`generate_skeletons` (`:258`) writes the file and reports success. Nothing errors.

**F5 — The Skeleton Index / Test List grammar is itself Python-shaped.**
- `_SIGNATURE` (`skeleton_generator.py:8-11`) requires `name(params) -> return_type`. A Go signature
  (`func (r *Repo) Get(id string) (*User, error)`) or a TS one (`get(id: string): Promise<User>`) is
  **unparseable** → `ValueError` at `:101`, uncaught.
- `_QUALIFIED_TYPE_REF` (`:15`) infers imports from dotted-path-with-Capitalized-tail, documented as
  *"Builtin generics like `list[str]` … have no dot"* — a Python builtin-generic assumption baked
  into the import rule.
- `parse_test_list` (`:132-143`) assumes `path::test_name` — pytest node-id syntax.

Consequence: the on-disk contract format the architect writes must be versioned/extended, not just
the renderer. And this format is **user-visible** — it appears in the Phase document approved at the
human gate.

**F6 — `ast.parse` runs unguarded on the user's source.**
`skeleton_generator.py:213` (`extract_existing_signatures`), called from `generate_skeletons:268` and
`merge_new_members:313`. `src/cli/commands/materialize_skeletons.py:80` catches **only**
`SkeletonPathEscapesProjectError`.

A Skeleton Index entry pointing at an *existing* non-Python file raises `SyntaxError` → unhandled
traceback. `phase_command.py:701` fail-closes on non-zero exit, so the phase aborts with a Python
stack trace as the user-facing diagnostic. Same defect in
`src/cli/commands/check_conformance.py:27`, which has no `try/except` at all.

**F7 — The design-conformance gate silently passes on non-Python.**
`src/utils/design_conformance.py`:
- `:92` — `project_root.rglob('*.py')`. In a TS project the loop finds zero candidates, so
  `_is_referenced_from_another_module` always returns `False`, and every new public member is
  classified `added_internal` (a finding) instead of `added_cross_module` (a **blocker**). The
  blocker for undeclared public seams never fires.
- `:61`, `:149` — `ast.parse` on the owning file, unguarded (see F6).
- `:7` `_TEST_PATH_MARKERS` / `:83-85` `_is_test_file` — knows only the pytest `test_` prefix; misses
  `*.spec.ts`, `*.test.js`, `*_test.go`, `#[cfg(test)]`. Go/TS test files are treated as production
  modules for the cross-module check.
- `:79-80` `_module_dotted_path` — Python dotted-import semantics.
- `:101-106` — matches `ast.ImportFrom` only.
- `:243` `_render_member_line` — re-emits Python-ish `(params) -> ret` into the Skeleton Index
  write-back, locking the round-trip into Python grammar.

**F8 — The architect that authors the Skeleton Index is never told the language.**
`phase_architect.py` is the **only** major agent never given `project_config_context_markdown`
(contrast `coder.py:160`, `backend_api_reviewer.py:43`, `database_reviewer.py:43`,
`infrastructure_reviewer.py:43`).

Its entry-format spec hardcodes Python: `:42-45` requires *"a fully-qualified dotted path"* and names
Python explicitly; `:45` defines an `, async` tag (a Python coroutine concept); `:52` mandates pytest
node-id syntax and `test_` prefixes; `:107-108` hardcodes `pytest tests/unit/test_repo.py` as the
verify command; `:717-728` is a full paragraph of Python builtin-type rules. Duplicated at
`phase_command.py:22-31`.

**F9 — The coder is taught a Python-only skeleton sentinel.**
`coder.py:375` — *"public signatures stubbed as `raise NotImplementedError` — materialized at the
shape gate, not created by you."* In a TypeScript skeleton the coder is hunting for a marker that
cannot exist.

---

## Review-loop mechanics

**F10 — `consolidate_review_cycle` hard-fails on a rostered reviewer with no stored result.**
`src/mcp/tools/feedback_tools_unified.py:336-339`:

```python
missing_reviewers = [name for name in active_critic_agents if name not in results_by_reviewer]
if missing_reviewers:
    raise ToolError(f'Cannot consolidate review cycle: missing reviewer submissions: {missing}')
```

A reviewer that starts, finds its prerequisites unmet, and declines to store does not drop out — it
detonates the workflow through `code_command.py:560-600`'s bounded-recovery path to
`EXIT: Workflow terminated`. It also cannot report the problem as a blocker, because
`_validate_reviewer_blockers` (`:704-728`) rejects blockers containing the execution-report marker.

**Therefore degradation must be a preflight gate in roster resolution, before invocation.**

**F11 — Weights renormalize correctly, but the domain pool is fixed regardless of phase shape.**
`_compute_weighted_score` (`:677-703`) divides by `active_weight_total`, so a reviewer that is not
rostered renormalizes away cleanly — a backend project loses nothing by having no frontend reviewer.

The defect is the inverse. `_phase1_core_weights` (`:39-43`) holds 85 (AQC 25 / spec-alignment 35 /
code-quality 25) and `_phase1_domain_weight_pool` (`:44`) is a fixed 15.0 split evenly among active
specialists (`:45-50`, division at `:653-660`). On a frontend-dominant phase the frontend reviewer
gets ~7.5/100 — the thing the phase is actually about carries almost no weight, and
`_detect_stagnation` (`src/utils/loop_state.py:146-157`) will never see its opinions move the score.

**F12 — Blockers bypass the score entirely.**
`decide_next_loop_action` (`src/utils/loop_state.py:88-91`) returns COMPLETED only when
`score >= threshold AND not latest_blockers`. `consolidate_review_cycle:351-356` propagates every
active reviewer's blockers regardless of weight, and `_effective_blockers_for_feedback` (`:120-138`)
falls back to bare text markers (`[blocking]`, `[severity:p0]`) for `REVIEW_CONSOLIDATOR`.

So a single `[Severity:P0]` on a subjective finding blocks completion no matter what the score says.
Any reviewer emitting subjective judgments needs an explicit contract rule about which findings may
be P0.

**F13 — Reviewer sign-off reuse is prompt-judged, not path-derived.**
`code_command.py:514-526` asks the orchestrator to invalidate a signed-off reviewer when "new or
changed work touches that reviewer's responsibility." Tractable for a static source reviewer. For a
reviewer whose input is the *rendered application*, transitive changes — a shared token, a component,
an API response shape — will be missed and a stale pass verdict reused.
`consolidate_review_cycle:368` counts these as `reused_count`.

**F14 — `STEP_MODES` frontend detection is a second hardcoded extension list.**
`code_command.py:300-322` matches `templates/, static/, components/, *.tsx, *.jsx, *.vue, *.svelte,
*.css`. A project using `.astro`, `.mdx`, Blade, or ERB silently never activates a frontend reviewer.
This is the same drift hazard as the three duplicated roster copies (F1).

---

## Agent/template constraints

**F15 — Shape mode may not write standalone domain H2 sections.**
`phase_architect.py:463-469` — shape mode must not write *"Technology Stack, Functional Requirements,
… or any domain-specific section — those are the detail act's responsibility,"* and must preserve
existing detail-act content **verbatim**.

So a `## UX Contract` H2 emitted in shape mode is out of contract and at risk of being dropped by the
detail-act expansion (Steps 13-16). `MCPModel.find_content_loss` (`src/models/base.py:188-207`) warns
on orphan H3s but would **not** catch a dropped H2.

`### Design Shape - Additional Sections` (`src/models/phase.py:26`, rendered `:124-125`) **is** shape
mode's own territory (`phase_architect.py:442`, H4-format rule `:953`) and round-trips today.

**F16 — Schema completeness is prompt-enforced, not code-enforced.**
`validate_document` → `src/mcp/tools/document_tools.py:38-46` → `src/mcp/tools/base.py:16-22` →
`MCPModel.find_content_loss` (`src/models/base.py:188-207`) reports only (i) mapped headings whose
content is truncated after parsing and (ii) orphan H3 headings that will be dropped. **It never
checks that a section is present.** A Phase with an empty `### Skeleton Index` validates clean.

Schema *shape* is code; schema *completeness* is prompt.

**F17 — `BASH_OUTPUT` / `KILL_SHELL` crash template generation for OpenCode.**
`src/platform/tui_adapters/opencode.py:36-37` maps both capabilities to `None`, and
`TemplateToolBuilder.build()` (`src/platform/template_helpers.py:83-89`) **raises `ValueError`** when
`render_builtin_tool_name` returns `None`. Adding either to a `builtin_tools` classvar breaks
`respec-ai regenerate` for OpenCode outright.

Long-running process management must therefore go through a CLI subcommand invoked with plain `BASH`.

**F18 — `review_model` has no vision guarantee outside Claude Code.**
`src/platform/tui_adapters/claude_code.py:134-135` hardcodes `'sonnet'`, but
`opencode.py:129` and `codex.py:205` resolve `review_model` from **user config** and can be anything.
Screenshots therefore cannot carry score in the portable core.

Playwright's `browser_snapshot` returns the accessibility tree as text — structured, diffable, and
model-agnostic. That is the deterministic substrate; screenshots are optional evidence.

**F19 — Reviewers need no write grant for browser artifacts.**
Playwright MCP returns snapshots, console messages, and network requests as **inline text**, and
axe-core injected via `browser_evaluate` returns JSON inline. Screenshots and traces are written by
the **MCP server** into its `--output-dir`, not by the agent.

So the "MUST NOT write files to disk" contract (`frontend_reviewer.py:86-98`) needs only a narrow
amendment acknowledging server-authored artifacts as citable evidence — not a general write carve-out.

**F20 — `add_platform_tools` is the supported escape hatch for third-party MCP tools.**
`src/platform/template_helpers.py:65-72` accepts arbitrary pre-formatted tool-name strings verbatim,
bypassing the `RespecAITool` enum (which is deliberately scoped to respec-ai's own server). Already
used for `mcp__linear-server__*` and `mcp__github__*`. Tool grants are per-agent by construction —
each reviewer has its own factory function — so granting browser tools to one agent affects no other.

---

## Config surface

**F21 — `language_standards.json` already carries testing conventions for 26 languages.**
`src/platform/data/language_standards.json`, surfaced by `available_languages()`
(`standards_config.py:49-54`, which prepends a synthetic `universal`). Each entry carries
`naming`/`imports`/`type_system`/`documentation`/`error_handling`/`code_structure` **and a `testing`
block** with `framework`, `location`, `naming`, `extras` — e.g. Go: *"`*_test.go` files alongside
source"* / *"TestFunctionName_Scenario"*; Rust: *"`#[cfg(test)] mod tests` in source files"*.

**This data is currently consumed only by standards-guide rendering and never by materialization.**
It is exactly what a language-aware test-scaffold renderer needs, and it is the single biggest reason
supporting many languages is cheaper than it looks.

Two narrower lists diverge from it, which is itself a finding:
- `_command_defaults` (`standards_config.py:95-216`) — 20 languages. Missing `c, clojure, dart,
  objective-c, powershell, terraform`.
- `TOOLING_DEFAULTS` (`tooling_defaults.py:8-45`) — 4 languages (python, javascript, go, rust);
  typescript synthesized from JS at `:62-65`. This is all auto-detection can populate.

**F22 — Closed key sets that silently drop extras.**
- Standards `[commands]` table: `render_language_toml` (`standards_config.py:288-296`) writes exactly
  `test`, `coverage`, `type_check`, `lint`. Any extra key in the source dict is **dropped on
  re-render**. Do not try to add `dev_command` here.
- `stack.toml` `[language.<lang>]`: fixed key set rendered at `:475-497`, validated by
  `_validate_stack_v2` (`:384-392`), which requires the four `*_command` keys.

**F23 — `css_framework` and `ui_components` are modeled but never rendered.**
`ProjectStack` defines them (`src/platform/models/project.py:29-30`); `render_stack_toml:483` emits
only `frontend_framework`. Meanwhile `frontend_reviewer.py:134` tells the reviewer that `stack.toml`
is the source of truth for *"frontend framework, rendering strategy, component model, and styling
system"* — three of those four have no field that reaches disk.

**F24 — `no_preference` passes validation.**
`_is_incomplete_value` (`standards_config.py:322-324`) rejects only empty / `todo` / `[todo` prefixes,
not `no_preference`. `_command_defaults` (`:217-225`) returns all-`no_preference` for any language
absent from its dict. So `respec-ai standards init <lang>` for those six languages writes
`test = "no_preference"` and `respec-ai standards validate` **passes** — a project appears fully
configured with zero enforceable quality gates.

**F25 — `type_checker` overrides are gated to Python.**
`apply_stack_to_tooling` (`tooling_defaults.py:83-105`) gates the `type_checker` override on
`if language == 'python'`. A TypeScript project that sets `type_checker` in `stack.toml` has it
**silently ignored**. Related: `stack_prompts.py:8-18` offers only `ty, mypy, pyright, pytype` — all
four Python — to a project of any language.

**F26 — `standards init` has no escape hatch for an unshipped language.**
`src/cli/commands/standards.py:53-64` is a closed allowlist against `language_standards.json`: an
unknown language prints `Unsupported language(s): …` and exits 1. The error is clean, but there is no
bring-your-own-language path. `build_language_template()` (`standards_config.py:257-274`) produces
exactly the empty scaffold such a flow would need and is **dead code — nothing calls it.**

---

## Existing patterns worth copying

**F27 — Three mature strategy-registry patterns already exist.**
No language dispatch exists anywhere in the codebase, but the shape to copy does:

| Pattern | Location | Shape |
|---|---|---|
| TUI adapters (closest match) | `src/platform/tui_adapters/__init__.py:8-12` | `_ADAPTER_MAP: dict[TuiType, type[TuiAdapter]]` literal registry + `get_tui_adapter()` factory |
| Platform adapters | `src/platform/adapters/factory.py:7-15` | enum → factory → ABC → subclass; **raises `ValueError` on unknown**, the fail-loud behavior to mirror |
| Command strategies | `src/platform/command_strategies/__init__.py`, `base.py` | Protocol + ABC + per-command implementation |

`coder.py:160-189` is the **prose-level** precedent for language dispatch — *"Match language config
file to the Phase specification language → read `[commands]` table"* — with a documented fallback
chain. The code layer should be made to honor what the prompt layer already describes.

**F28 — The `TuiAdapter` MCP-registration contract.**
`src/platform/tui_adapters/base.py:117-127` declares `register_mcp_server`, `add_mcp_permissions`,
`is_mcp_registered`, `unregister_mcp_server` — implemented per TUI in `claude_code.py`, `codex.py`,
`opencode.py`. But `src/cli/config/claude_config.py` is hardcoded to a **single** server
(`MCP_SERVER_NAME = 'respec-ai'`, `:9-15`; `register_mcp_server()` shells `claude mcp add` at
`:163-176`; `add_mcp_permissions()` writes `mcp__respec-ai__*` at `:240-278`). It is not a generic
registrar, and generalizing it touches all three adapters.

---

## Per-TUI capability tiering

**F29 — `TuiAdapter` already has an optional-capability pattern; do not invent a new one.**
`ask_user_question_tool_name` (`src/platform/tui_adapters/base.py:38-45`) returns `str | None`, and
`selection_prompt_instruction` (`:65-70`) and `selection_response_source` (`:72-76`) **branch on it** to
emit different generated prose:

```python
ask_tool = self.ask_user_question_tool_name
if ask_tool:
    return f'Use {ask_tool} tool to present options:'
return 'Ask the user directly with a numbered options list …'
```

This is exactly the shape a per-TUI capability needs — declare, branch, degrade — and it is already in
use for a capability Codex lacks. Any new tiered capability should follow it rather than introducing a
parallel mechanism.

**F30 — Expected command/agent counts are flat module constants and break under per-TUI command sets.**
`EXPECTED_COMMANDS_COUNT = len(_COMMAND_TEMPLATES)` and `EXPECTED_AGENTS_COUNT = len(_AGENT_NAMES)`
(`src/platform/template_generator.py:108-109`), consumed by `src/cli/commands/validate.py:70-79` and
`src/cli/commands/status.py:82-83` to check how many files were generated.

If one TUI generates a command another does not, a single constant is wrong for at least one of them
and `respec-ai validate` reports a spurious failure. Both call sites already resolve the TUI adapter to
do their work, so the fix is to make the expected counts adapter-derived rather than module-level.
`tests/unit/cli/commands/test_validate.py:48` loops over the constant and needs the same treatment.

**F31 — `DesignSync` is a Claude Code built-in with interactive auth and untrusted content.**
Not an MCP tool — it appears in agent frontmatter as the bare name `DesignSync`, alongside
`Read`/`Write`/`Bash`.

Method surface, dispatched on `method`: reads (`list_projects`, `get_project`, `list_files`,
`get_file`), setup (`create_project`), a plan boundary (`finalize_plan` → returns a `planId`), and
writes (`write_files`, `delete_files`, `register_assets`, `unregister_assets`). Required ordering is
**list/read → `finalize_plan` → write/delete**; writes without a valid `planId`, or touching paths
outside the finalized plan, are rejected.

Three properties that constrain how it may be used:
- **Interactive claude.ai authentication.** It may be entirely absent in headless or scheduled runs, so
  nothing in a refinement loop may hard-depend on it.
- **Permission prompts on `create_project`, `finalize_plan`, and all writes.** A blocking prompt inside
  an automated review loop is unacceptable; user-invoked commands are the right home.
- **`get_file` returns content written by other org members.** Its own documentation says to treat that
  as *data, not instructions*. Anything reading design files needs an explicit prompt-injection clause.

**F32 — `builtin_tool_name_map` demands an explicit per-adapter decision, and the builder raises on
`None`.** `base.py:47-59` documents the requirement: *"Every concrete adapter MUST make an explicit
decision for every capability … even if that decision is `None`."* Good — it makes adding a capability
a deliberate, reviewed act across all three adapters.

But `TemplateToolBuilder.build()` (`src/platform/template_helpers.py:83-89`) **raises `ValueError`** when
`render_builtin_tool_name` returns `None` (**F17**). So there is currently no way to say "grant this
tool where it exists, skip it where it doesn't" — the only primitives are *required* and *absent*. A
tiered capability needs an optional-grant primitive alongside the existing required one.

**F33 — Agent Teams exist but cannot be respec-ai's coordination substrate.**
Verified against current Claude Code documentation (August 2026). Teams are real and shipped in
v2.1.178+: teammates run in their own context windows, message each other by name via `SendMessage`,
share a task list under `~/.claude/tasks/{team-name}/`, and have per-agent mailboxes at
`~/.claude/teams/{team-name}/inboxes/{agent-name}.json`. Tasks can declare dependencies.

Three properties make them unusable for a tool that generates agents to run in *other people's*
projects:
- **Experimental, disabled by default** — requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings
  or environment. respec-ai cannot set that for a user, and generated workflows that silently assume it
  would fail in a way that is very hard to diagnose.
- **Not declarable in respec-ai's output surface.** The sub-agents documentation states plainly that
  *"subagents cannot directly coordinate with other agents in their frontmatter definition."* Supported
  `.claude/agents/*.md` frontmatter keys are `name`, `description`, `tools`, `disallowedTools`, `model`,
  `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`,
  `isolation`, `color`, `initialPrompt` — **no team membership field.** Teams are configured at session
  level, outside what respec-ai generates.
- **Claude Code only.** No confirmed OpenCode or Codex equivalent.

Also relevant: teammates cannot spawn teammates (only the lead manages the team), and there is no shared
mutable state beyond the task list — coordination is strictly message-passing, not a blackboard.

Recorded as a future capability tier in [deferred-issues.md](deferred-issues.md), following the phase-8
pattern.

**F34 — `coder.py` is a monolith; the reviewers already show the way out.**

| File | Lines | Shape |
|---|---|---|
| `src/platform/templates/agents/coder.py` | 648 | One template, already branching on `mode` for standards-only |
| `src/platform/templates/agents/reviewer_contracts.py` | 84 | Shared renderers: `render_reviewer_mcp_retry_contract:1`, `render_reviewer_output_contract:24`, `render_reviewer_execution_report_contract:59` |
| `src/platform/templates/agents/frontend_reviewer.py` | 224 | Pure domain guidance composed on top |

Every reviewer template imports the shared renderers and adds only its own domain content. `coder.py`
has no equivalent — the TDD cycle, filesystem boundary, todolist gate, and iteration handoff format are
all inline, so a second coder would either duplicate them or add a third branch to a 648-line template
regenerated for three TUIs.

**F35 — Reviewer findings carry no routing target.**
`ReviewFinding` is `(priority, feedback)`, and `consolidate_review_cycle:363-365` merges findings by
priority with only a `[reviewer_name]` prefix. Sufficient when one coder consumes everything.

With two coders, a cross-boundary finding is unactionable unless it names which side changes — "the
response shape is wrong" does not say whether the frontend or the backend moves. The existing tag
convention (`[Severity:P0]`, `[Scope:changed-file]`, parsed from feedback text by
`_effective_blockers_for_feedback:120-138`) is the natural place to extend, since it requires no schema
or migration change.

**F37 — Reviewer `feedback_markdown` has no schema, but two heuristics decide what reaches the coder.**
This is the most misunderstood machinery in the review pipeline. Get it wrong and a reviewer section is
silently invisible with no error and no failing test.

*What is validated:* almost nothing. `store_reviewer_result` (`feedback_tools_unified.py:250-308`)
checks only that `feedback_markdown` is **non-empty** (`:261-268`). No heading check, no level check, no
section-name check. It is stored as an opaque blob.

*What actually reads it:* only `get_reviewer_feedback_context`, via two scanners — neither of which
raises. They silently include or drop.

**1. `_strip_reviewer_execution_report` (`:613-633`)** removes the execution report. Two hazards:
- The marker test is a **substring test on every line**, not just headings (`:619`). Any prose line
  containing the literal `Reviewer Execution Report (Non-Actionable)` triggers a strip with
  `heading_level = 6`, deleting everything up to the next heading of *any* level.
- The strip loop breaks only on a heading of level `<= 4`, so **any `#####` section placed after the
  execution report is silently deleted**.

**2. `_extract_actionable_reviewer_excerpt` (`:577-611`)** is an **allowlist by exact lowercase heading
text** (`:579-585`):

```python
actionable_sections = {
    'assessment results', 'key issues', 'recommendations', 'findings', 'required corrections',
}
```

Matching is level-agnostic; a section body runs until the next heading of level `<=` its own.
**Non-matching headings are dropped entirely** from `### Actionable Review Excerpts`. Fallback when
nothing matches (`:566-568`): *"No actionable markdown excerpts found; use structured findings."*

Note `findings` and `required corrections` are in the allowlist but used by **zero** reviewer templates —
unused reserved slots.

*The escape hatch:* `get_reviewer_result` (`:452-497`) returns `feedback_markdown` verbatim and
unfiltered under `## Full Feedback Markdown`, execution report included.

*Consequence:* markdown is for humans and audit. **`consolidate_review_cycle` (`:351-365`) reads only
structured `blockers`/`findings` and never touches `feedback_markdown`** — so markdown alone cannot
affect scoring, the blocker gate, or loop decisions. Anything a coder must act on has to be a structured
finding or blocker.

**F38 — The reviewer heading skeleton is a convention with existing precedent for extension.**
No code validates it and `tests/unit/templates/test_review_agent_templates.py` asserts only *membership*
(`:640`, `:53`), never a complete or ordered H4 set — so adding a section needs no test change.

Common skeleton across reviewers:
```
### <Reviewer Title> (Score: {TOTAL}/<MAX>)      ← H3, exactly one
#### <Rubric Category> (Score: {X}/<n>)          ← H4, repeated
#### Reviewer Execution Report (Non-Actionable)  ← H4, shared block from reviewer_contracts.py:59-84
#### Key Issues                                  ← H4
#### Recommendations                             ← H4
```

**Precedent for reviewer-specific extra H4s already exists:** `spec_alignment_reviewer.py:194+` adds
`#### Completion Certification Matrix`, `#### Phase-To-Implementation Coverage`,
`#### Unverifiable Requirements`, `#### Deviation Assessment`; `design_conformance_reviewer.py:135+`
adds `#### Classification Summary` and `#### Design Record Write-Back`. `coding_standards_reviewer.py:258-266`
nests `##### <Section>` under an H4.

*Placement rule that falls out of F37:* a new section must be **H4, placed before the execution
report**, must never contain the execution-report marker string in its prose, and must have its heading
text added to the allowlist if the coder is meant to see it.

**F39 — Coders are told to use feedback generically, with no ownership filter.**
`coder.py:403-425` instructs: *"Use only user feedback, blockers, critical findings, key issues, and
recommendations as implementation guidance"*, with exactly one exclusion — *"Ignore any `Reviewer
Execution Report (Non-Actionable)` section."* There is no notion of a finding belonging to one coder
rather than another, because today there is only one coder.

Consumption is **prompt-level, not code-level**: an LLM reading markdown, not a parser. So ownership
enforcement must be written as contract prose and pinned by generated-template tests, not implemented as
filtering logic.

**F36 — `### Collaboration And Wiring` is the declared home for cross-boundary seams.**
`src/models/phase.py:24` maps it under `## Design Shape`; `phase_architect.py:441-443` lists it among the
sections shape mode owns, where *"concrete paths and signatures belong … and only here."*
`coder.py:381` instructs the coder to *"wire construction and ownership per Phase
`### Collaboration And Wiring`."*

It is human-approved at the shape gate, language-neutral, and already the contract both sides of a seam
implement against — so it is the correct source for enumerating seams to review, rather than having a
reviewer infer its own list.
