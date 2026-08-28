# Phase 5 — `respec-ai frontend-preflight`

**Depends on:** Phase 3. **Blocks:** Phase 7.
**Risk:** moderate. Process lifecycle management is easy to get subtly wrong, and orphaned dev servers
are an unpleasant failure mode for the user.

## Start here

**Prerequisites:** Phase 3 complete. Verify: `grep -n "css_framework" src/platform/standards_config.py`
returns output, and a polyglot fixture has `dev_command` under the right `[language.X]` table.

**Already done?** `ls src/cli/commands/frontend_preflight.py` — file exists means complete.

**Read first:** [README.md](README.md) (cross-cutting risk #4), `docs/phase-refactor/testing.md`,
`CLAUDE.md`, and [findings.md](findings.md) **F17**, **F28**. In [decisions.md](decisions.md) read
*"Long-running processes go through a CLI subcommand"* and *"The MCP registrar is not generalized"*.

Model the command on `src/cli/commands/materialize_skeletons.py` — same shape, same JSON-on-stdout
contract, same registration pattern in `src/cli/main.py`.

**First action:** write B5 and B6 — the failure paths — before the happy path. Missing config and a
dev server that exits immediately are the cases that must behave gracefully, and building them first
stops you from designing a command that only works when everything is fine.

**Ship and use this standalone before phase 7 exists.** It is a CLI command with no agent involvement;
you can exercise every path by hand. Do that. A preflight with a subtle lifecycle bug discovered from
inside an agent loop is very hard to debug.

**This phase exists because determinism is the hard part.** If the application is in a different state
each iteration, phase 7's feedback is noise and the loop cannot converge. That is why this is a
separate phase rather than a section of phase 7.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Make the reviewed application reach a known, reproducible state — dev server running, base URL
reachable, scratch directory prepared — and report cleanly when it cannot.

## Why a CLI subcommand and not agent tooling

The obvious approach is to let the reviewer manage the dev server with background-shell tools. That
breaks the build.

`src/platform/tui_adapters/opencode.py:36-37` maps `BASH_OUTPUT` and `KILL_SHELL` to `None`, and
`TemplateToolBuilder.build()` (`src/platform/template_helpers.py:83-89`) **raises `ValueError`** when
`render_builtin_tool_name` returns `None` (**F17**). Adding either to a `builtin_tools` classvar breaks
`respec-ai regenerate` for OpenCode outright — a hard failure, not a degradation.

A subcommand invoked with plain `BASH` is portable across all three TUIs and keeps process lifecycle in
tested Python rather than in prompt text, where it cannot be tested at all.

## Interface

JSON on stdout, synchronous, **exit 0 even when not ready** — "no dev server configured" is a normal
outcome, not an error.

**`--start`** — read `dev_command` / `base_url` from the appropriate `[language.<lang>]` table. If
either is missing, emit `{"ready": false, "reason": "no dev_command configured"}` and exit 0. Otherwise
spawn detached (`subprocess.Popen`, `start_new_session=True`), redirect output to a log under
`.respec-ai/run/`, write a pidfile, and poll `base_url` until it responds or a timeout elapses
(default 60s, `--timeout`).

Returns: `ready`, `base_url`, `pid`, `log_path`, `scratch_dir`, `playwright_mcp_registered`. On failure,
`reason` plus a `log_tail` so the user can see why the server did not come up.

**`--status`** — pidfile liveness plus a URL probe. **Idempotent**: a second call must reuse a running
server, never start a second one. Also reports `playwright_mcp_registered`.

**`--stop`** — kill the process group (not just the pid — dev servers spawn children), remove the
pidfile. Safe to call when nothing is running.

**`--seed`** — run an optional `seed_command` if configured. Absent config means the reviewer reviews
whatever state exists and says so; it does not fail.

## Scratch directory

`.respec-ai/run/review/<coding_loop_id>/<review_iteration>/`, created by `--start` and returned in the
JSON.

**Gitignored via `init` *and* excluded from the commit steps.** Both are required. `phase_command.py:764-768`
does `git add -- <paths>` and the code loop commits per iteration via `/respec-commit`; a screenshot or
trace that lands in history is a real annoyance to remove later.

`--stop` does **not** delete it — evidence outlives the run, and phase 7's findings cite it. Prune via
the existing `src/cli/commands/cleanup.py`.

## Authentication

Deliberately minimal. One optional `storage_state_path` in `stack.toml` pointing at a Playwright
`storageState` JSON the user generates once by hand. **Correction from phase 7:** the real
Playwright MCP server has no `browser_set_storage_state` tool — storage state is a server
*startup* flag (`--storage-state <path>`), applied once at Playwright MCP registration
(`docs/CLI_GUIDE.md`), not passed per-call by the reviewer.

When absent, the UX Contract's `##### Route Index` auth column tells the reviewer which routes are
public; the rest are reported as skipped context using the existing pattern from
`frontend_reviewer.py`. Honest and bounded.

Do not build an auth framework here. See
[deferred-issues.md](deferred-issues.md#authentication-beyond-a-hand-generated-storagestate) — and note
that scripting a login as a `seed_command` covers most of what a framework would, at a fraction of the
cost.

## Playwright MCP registration

**Do not generalize the registrar in this phase.** `src/cli/config/claude_config.py` is hardcoded to a
single server (`MCP_SERVER_NAME = 'respec-ai'`, `:9-15`; `register_mcp_server()` shells `claude mcp add`
at `:163-176`; `add_mcp_permissions()` writes `mcp__respec-ai__*` at `:240-278`), and generalizing it
touches all three `TuiAdapter.register_mcp_server` implementations (**F28**, `base.py:117-127`).

That is a worthwhile refactor and a poor prerequisite — it would gate frontend review on unrelated CLI
surgery. See [deferred-issues.md](deferred-issues.md).

**What ships instead:** document the one-line install per TUI in `docs/CLI_GUIDE.md`, and have
`--status` report `playwright_mcp_registered` by checking for the server in the TUI config. That is what
phase 7's roster gate acts on, so an unregistered server produces a clean skip rather than an obscure
tool-not-found failure inside an agent.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | `--start` returns `ready: true` with a reachable `base_url` within the timeout |
| B2 | `--status` called twice does not start a second server |
| B3 | `--stop` leaves no process **and no orphaned children** |
| B4 | The scratch dir is created, returned, gitignored, and excluded from commit steps |
| B5 | Missing `dev_command` → `{"ready": false, "reason": ...}`, **exit 0** |
| B6 | A `dev_command` that exits non-zero → `ready: false` with `log_tail`, exit 0, no orphan process |
| B7 | A `base_url` that never responds → `ready: false` at timeout, and the process is cleaned up |
| B8 | `--status` reports `playwright_mcp_registered` accurately for the configured TUI |

B3 and B7 are the ones that bite. A dev server left running after a failed start, or a `--stop` that
kills the parent but not the Vite child, is the kind of bug users notice and cannot diagnose.

## Scope

**`src/cli/commands/frontend_preflight.py`** — new, modeled on `materialize_skeletons.py`.

**`src/cli/main.py`** — register the subcommand (parser and dispatch; see how `materialize-skeletons` is
wired at `:112`).

**`src/cli/config/gitignore.py`** (new), **`src/cli/commands/init.py`**, **`src/cli/commands/sync.py`** —
`.gitignore` generation did not exist before this phase (verified: no call site referenced `.gitignore`
anywhere in `src/`), so this phase adds it as `ensure_gitignore_entries`, appending `.respec-ai/run/`
idempotently, rather than extending an existing generator as originally worded above. It has to be
called from both `init.py`'s fresh-init path and `sync.py` (which is also what `init.py` delegates to
for an already-initialized project) — an existing project only ever reaches `sync.py`, never the
fresh-init branch.

**`src/platform/models/project.py`, `src/platform/standards_config.py`** — not in the original scope list;
added because `--seed` needs a `seed_command` source and none existed anywhere in the codebase (verified
by repo-wide grep). Added as a fourth per-language optional key alongside `dev_command`/`base_url`/
`storage_state_path`, following the same pattern phase 3 established — optional, never validated as
required, additive to `render_stack_toml`.

**`docs/CLI_GUIDE.md`** — the per-TUI Playwright MCP install line, and the preflight command reference.

## Out of scope

- **Any agent or reviewer changes.** Phase 7.
- **Generalizing the MCP registrar.** Deferred, above.
- **An auth framework.** Deferred, above.
- **Browser interaction.** This command starts a server and reports readiness. It does not drive a
  browser and never imports Playwright.

## Exit criteria

- B1–B8 green.
- **Exercised by hand against a real frontend project**, not only fixtures: start, status twice, `curl`
  the URL, stop, confirm with `ps` that nothing survives.
- The three failure paths — no config, server exits, server never responds — all exit 0 with a usable
  `reason`, and leave no process behind.
- No Python traceback reaches stdout or stderr on any path. Every failure is a clean message
  (Python-invisibility, see [README.md](README.md)).
- `uv run pytest` clean.
