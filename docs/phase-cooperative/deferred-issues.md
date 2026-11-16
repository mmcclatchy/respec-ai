# Deferred issues

A running log of small, real issues found while implementing a phase that were deliberately **not**
fixed at the time — because fixing them was out of that phase's scope, unrelated to what it touches,
or would have expanded the diff beyond what the phase document called for. This is not a bug tracker
for the phases themselves (each phase document tracks its own *Behaviors to pin* and exit criteria) —
it exists so small out-of-scope findings don't get lost between sessions.

**When to add an entry:** you're implementing or reviewing a phase, you notice something wrong or
worth cleaning up, and fixing it now would mean touching code the current phase document doesn't
claim. Log it here instead of fixing it inline or letting it evaporate at the end of the session.

**When to remove an entry:** once fixed, delete the row rather than marking it done — this file should
only ever list live debt. If the fix needs its own commit message context, that belongs in git
history, not here.

**Format:**

| Found in | Location | Issue | Why deferred |
|---|---|---|---|
| Phase N — short phase name | `file.py:line` or `file.py` (function/section) | One or two sentences: what's wrong, concretely | Why it wasn't fixed as part of that phase's work |

---

## Open

| Found in | Location | Issue | Why deferred |
|---|---|---|---|
| Phase 1 — Language-neutral foundation | `src/platform/standards_config.py:324-326` (`_is_incomplete_value`), `:338-341` (`_validate_language_config` commands loop); default written at `:219-227` | `no_preference`, the test command written for languages with no canonical command (c, clojure, dart, objective-c, powershell, terraform; F25), passes `respec-ai standards validate` and the same check `regenerate` runs (`regenerate.py:99-105`): only empty and `TODO` values count as incomplete. Phase 1 treats it as missing on the architect side only, where it gets the `(verify: ask user — …)` marker. | Rejecting it in validation would make `standards validate` fail and `regenerate` abort for those six languages until the user sets a command. That is a config-UX decision (phase 1 *Out of scope*). |
| Phase 1 — Language-neutral foundation (exit verification) | `src/utils/materializers/typescript_materializer.py:100` (`render_test_module`) | A TypeScript Test List name containing `'` or `\` produces an invalid test file. The name goes unescaped into `throw new Error('Not implemented: <name>')`. Probed: `renders the user's name` wrote `throw new Error('Not implemented: renders the user's name')`, which ends the string early; `renders C:\x path` wrote `'Not implemented: renders C:\x path'`, an invalid `\x` escape. Pre-existing (HEAD `:69`). The authoring notes now tell the architect to keep quotes and backslashes out of the name. | A materializer rendering fix. Phase 1 only moves authoring rules into the materializers. |
| Phase 1 — Language-neutral foundation (exit verification) | `src/utils/materializers/python_materializer.py` (skeleton rendering); `materialize_skeletons.py:88` | A Skeleton Index entry whose `<params>` or `<Result>` text is not valid Python is written to disk as a skeleton that does not parse, with exit 0 and no report. Probed: copying the architect's example verbatim, `` `src/kb/client.py` :: KnowledgeBase.query(<question parameter>) -> <list of best-practice records>``, wrote `def query(self, <question parameter>) -> <list of best-practice records>:`. The CLI's `SyntaxError` backstop never fires, because nothing parses the rendered file. Phase 1's neutral example keeps angle-bracket placeholders in that position, which makes a verbatim copy more likely. | Validating the rendered source belongs to the materializers (a parse check before the create-only write). Phase 1 changes only the prose that teaches the notation. |
| Phase 1 — Language-neutral foundation (exit verification) | `src/cli/commands/language_guidance.py:34-35` | A `stack.toml` whose `project` is not a table (`project = "oops"`) crashes `respec-ai language-guidance` with an `AttributeError` traceback (exit 1). A `languages` string instead of a list (`languages = "python"`) prints one section per character (`#### p` … `#### n`) with exit 0. Step 4.5 falls back cleanly on the first; the second hands the architect nonsense notes. | Phase 1 item 4 specifies exactly `_validate_stack_v2`'s reading (`standards_config.py:366-368`), which has the same shape assumptions. Shape-checking `[project]` belongs with stack validation. |
| Phase 1 — Language-neutral foundation (exit verification) | `src/cli/ui/console.py:4` (`Console()`), used by `language_guidance.py:31` | When stdout is not a terminal, rich wraps `print_error` output at 80 columns. Step 4.5's fallback quotes `[first line of command output]`, so it gets a truncated line. Probed on a malformed `stack.toml`: `✗ Could not read .respec-ai/config/stack.toml: Expected ']' at the end of a`. The line still names `stack.toml`. | Console width affects every `print_error` caller. That is a CLI-wide output decision outside phase 1. |
| Phase 1 — Language-neutral foundation (review) | `src/cli/commands/language_guidance.py` (reads `[project].languages`); `src/utils/skeleton_generator.py` (`get_materializer(language_for_path(...))`) | Authoring notes are chosen from the languages declared in `stack.toml`, but materialization picks a materializer by file extension. A language that is used but not declared gets no notes while its files are still materialized. Two ordinary init paths do this: a greenfield `init` writes `languages = []` (which `_validate_stack_v2` rejects, but `init --yes` writes it anyway), and a Python root with a `frontend/` TypeScript subdirectory is detected as `["python"]`, so `.tsx` component entries get no TypeScript notes. Probed: on a `.py` path with no notes, a Test List entry in the taught plain-sentence form wrote `def reconnects after a timeout() -> None:` with exit 0. | Phase 1 item 4 deliberately keys the notes on declared languages ("only for the project's languages", decisions.md). Fixing it means either making the briefing (phase 2) flag languages present in Module Layout paths but missing from `stack.toml`, or a phase 3 structural check that a materialized path's language is declared. Decide in phase 2 or 3; the materializer parse check in the row above is the backstop. |
| Phase 2 — Cooperative flow | `src/platform/adapters/linear.py:14-29` and `src/platform/adapters/github.py:14` (`phase_sync_instructions`), used by Step 2 of `phase_command.py` | The disk mirror (B23) protects a re-run only on the markdown platform. On Linear and GitHub, Step 2 syncs from the platform record, which holds the sparse roadmap phase until Step 12 stores the signed-off version. A re-run before sign-off on those platforms therefore starts again from explore and asks the briefing again; settled decisions and research marks written during the interrupted run are not on the platform. | Persisting the in-review draft to the platform is outside phase 2 (*Out of scope*). It needs a platform write per review round, or a sync that prefers the local mirror. |
| Phase 2 — Cooperative flow | `src/platform/templates/commands/phase_command.py` (the guardrail line in the header), `src/platform/tui_adapters/codex.py:123-124` | F39: on codex the subagent guardrail renders twice in the phase command, once from the template's `subagent_invocation_guardrail` and once from the adapter's delegation prefix. Cosmetic. | Out of scope for phase 2 (*Out of scope*: F39). Fixing it means deciding which of the two owns the guardrail for every delegating command. |

## Fixed (kept briefly for continuity, then removed)

*(empty — entries move here only if you want a paper trail across one hand-off; otherwise delete
outright once fixed)*
