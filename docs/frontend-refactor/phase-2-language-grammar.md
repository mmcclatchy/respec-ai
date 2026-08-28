# Phase 2 — Per-language contract grammar

**Depends on:** Phase 1. **Blocks:** nothing hard; phase 7 is much weaker without it.
**Risk:** moderate. Prompt-only changes, but the output format is user-visible and hard to change later.

## Start here

**Prerequisites:** Phase 1 complete. Verify: `grep -rn "LanguageMaterializer" src/utils/` returns
output, and `phase_architect` receives `project_config_context_markdown`.

**Already done?** `grep -n "\.tsx" src/platform/templates/agents/phase_architect.py` — output means
complete. (Do not probe for "typescript"; `:277` already names it in an unrelated multi-language
example list.)

**Read first:** [README.md](README.md), `docs/phase-refactor/testing.md`, `CLAUDE.md`, and
[findings.md](findings.md) **F5**, **F8**, **F21**. `docs/phase-refactor/phase-2-design-layer.md`
explains what the Skeleton Index is for and why its entries are shaped the way they are — read it
before changing the format.

**First action:** read `phase_architect.py:36-54` and `:693-728` end to end before editing anything.
The entry-format spec and the worked examples are the whole surface of this phase, and they are more
entangled than they look — `:717-728` is a paragraph of Python builtin-type rules that only makes sense
in the context of `:42-45`'s dotted-path requirement.

**This phase is mostly writing prompts, which resist ordinary testing.** Read
`docs/phase-refactor/testing.md` on this specifically. The tests you can write assert *structure* of
generated output; the thing that actually matters — whether the architect produces a useful component
contract or plausible ceremony — needs you to read real output. That manual review is in the exit
criteria and is not optional.

**One judgment call with no right answer in the codebase:** how much a component contract should say.
Too little (just a signature) and it is thin exactly where frontend needs depth. Too much (every prop,
every event, every state transition) and it becomes a second implementation the user has to review.
Guidance below, but you will be calibrating.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Teach the architect to emit language-appropriate Skeleton Index and Test List entries, so that what
phase 1's machinery materializes is a contract that fits the language rather than a Python signature
wearing a `.tsx` extension.

## Why the grammar has to change, not just the renderer

Phase 1 made the machinery language-aware. But the on-disk contract format is itself Python-shaped
(**F5**), and it is **user-visible** — it appears in the Phase document approved at Human Gate 1a. A
`.tsx` entry written as `LoginForm(props: Props) -> JSX.Element` parses fine and materializes fine
after phase 1, and is still wrong: it says nothing about props shape, state, or events. The contract is
thinnest exactly where frontend needs it to be thickest.

Forcing components into method-signature form was considered and rejected — see
[decisions.md](decisions.md). A React component is not `Class.method(params) -> Return`, and pretending
otherwise produces a design contract that cannot carry the design.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | A React component entry round-trips: `parse_signature` → render → re-parse yields the same structure |
| B2 | The architect emits TS-shaped entries for TS paths and Python-shaped entries for Python paths **in the same phase** |
| B3 | Test List entries use the language's own convention — `.spec.ts` naming for TS, pytest node IDs for Python |
| B4 | A component entry carries prop names and types, not just a component name |
| B5 | Checklist verify commands come from config, not a hardcoded `pytest …` |
| B6 | A phase with no TypeScript files produces output identical to today |

B6 is the regression guard. B2 is the one that matters most — the polyglot case is the real case, and
a per-language grammar that only works when the whole phase is one language has not solved anything.

## Scope

**`src/platform/templates/agents/phase_architect.py`** — the entry-format spec, selected by language:

**Done.** These items now live at (line numbers post-implementation; re-verify before further edits):

- The Skeleton Index / Module Layout / Test List placeholder entry formats moved to a shared constant
  module, `src/platform/templates/phase_contract_grammar.py`, imported by both `phase_architect.py` and
  `phase_command.py` (see the duplication-collapse note below) — no longer duplicated inline.
- `phase_architect.py:745-770` — the dotted-path rule now branches per language: fully-qualified dotted
  path for Python, verbatim-as-declared for TypeScript (import specifiers deferred to the coder, since
  TypeScript specifiers are relative paths, not dotted module names).
- The `, async` tag stayed universal rather than per-language (`phase_architect.py:766-769`) — Python and
  TypeScript both use `async` identically, and Go/Rust are out of scope for this phase, so there was no
  live case requiring per-language tag lists yet. Revisit when a language needing a different async
  convention is added.
- `phase_architect.py:113-121` (`_test_list_naming_convention_block`) — test naming is rendered from
  `language_standards.json[lang]['testing']` (**F21**) via a new `language_testing_convention()` accessor
  in `standards_config.py`, at template-generation time, for python and typescript only.
- `phase_architect.py:529-535` — Checklist verify-command prose now instructs deriving `(verify: command)`
  from the Step's language `[commands].test` entry in the *project's own*
  `.respec-ai/config/standards/<language>.toml` (read via `project_config_context_markdown` at
  `/respec-phase` runtime) rather than hardcoding `pytest`. This is necessarily prose, not a
  generation-time render like the test-naming block above — the project's configured command doesn't
  exist yet when `respec-ai regenerate` builds the static template, only when `/respec-phase` later runs
  against a real project.
- `phase_architect.py:715-722` — the "Interface Signatures" example now shows both a Python and a
  TypeScript worked example, not a replacement.
- `phase_architect.py:745-775` — Python builtin-type rules are now scoped under a `**Python**:` heading
  alongside a `**TypeScript**:` heading and a `**Component entries**:` heading (props with real names and
  types, exports, contract-relevant state only — no JSX/styling/hooks).

`src/platform/templates/commands/phase_command.py`'s duplicate copy was collapsed into the same shared
`phase_contract_grammar.py` constants rather than merely kept in sync by hand.

**Per-materializer `parse_signature`** replaces the single `_SIGNATURE` regex. Phase 1 defined
`LanguageMaterializer.parse_signature` and `TypeScriptMaterializer.parse_signature`, but **did not wire
them in** — `skeleton_generator.parse_skeleton_index`/`_parse_member` called `parse_python_signature`
unconditionally for every entry regardless of the owning path's language, so a TypeScript entry's
dotted-looking type (e.g. `kb.Result`) was silently run through Python's dotted-import extraction and
corrupted before it ever reached `TypeScriptMaterializer`. This was found, not assumed, while
implementing this phase: B2 cannot be satisfied without it, since no prompt change fixes a parser that
ignores the language of the path it's parsing. The fix was made here — `parse_skeleton_index` now
resolves each path's materializer once and dispatches `parse_signature` through it, falling back to the
language-neutral `parse_bare_signature` for unsupported languages so nothing raises. This phase supplies
the TypeScript grammar *and* completes the dispatch wiring phase 1 left unfinished; render/extract
dispatch (`generate_skeletons`, `generate_tests`, `merge_new_members`) was already correctly wired by
phase 1 and was not touched.

### What a component contract should carry

The calibration question. A component entry should be enough for a reviewer to check conformance and a
coder to implement without inventing the interface — and no more:

- **Component name and file path** — as today.
- **Props**, with names and types. This is the main thing method-signature form loses.
- **Exports** — what the module makes available, which is what `design_conformance.py`'s cross-module
  check reads (**F7**).
- **Notable state or effects**, only where they are part of the contract rather than an implementation
  choice. A component that owns fetch-and-cache behavior should say so; one that uses `useState` for a
  toggle should not.

Not in the contract: JSX structure, styling, internal helpers, hook implementation details. Those are
the coder's, per the v2 principle *"design the messages, not the internals"* — see
`docs/phase-refactor/README.md`.

For Vue and Svelte single-file components the natural unit is the component file with its props and
emitted events; the same principle applies. Do not build those grammars now — but if the TypeScript
format you choose could not accommodate them without restructuring, choose differently.

## Out of scope

- **Render/extract materializer machinery** (`generate_skeletons`, `generate_tests`,
  `merge_new_members`, the `_MATERIALIZER_MAP` registry). Phase 1, already correctly wired — do not
  touch. The one exception, made in this phase and explained above under "Per-materializer
  `parse_signature`", was completing phase 1's unfinished *signature-parse* dispatch, which is a
  precondition for B2 rather than a redesign of dispatch itself.
- **`stack.toml` reading.** Phase 3.
- **Vue, Svelte, Go, or Rust grammars.** TypeScript and Python only. See
  [deferred-issues.md](deferred-issues.md).
- **The UX Contract.** Phase 4. That describes *behavior*; this describes *code shape*. They are
  complementary and independent — do not merge them.

## Exit criteria

- B1–B6 green.
- A polyglot phase produces correct entries for both languages, and both materialize.
- **Manual quality review — the criterion that matters most.** Run `/respec-phase` on a real
  frontend objective and read the generated Skeleton Index yourself. Ask: could a coder implement
  these components without inventing the interface? Could a reviewer check conformance against them?
  Is anything in there an implementation detail masquerading as a contract? If the answer to the last
  one is yes, the format is too thick. No test substitutes for this read.
- `respec-ai regenerate` completes for all three TUIs.
- `uv run pytest` clean.
