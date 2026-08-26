# Phase 1 — The language seam

**Depends on:** Phase 0. **Blocks:** Phases 2, 3, 6.
**Risk:** highest in the refactor — this is the phase that decides whether adding a language later is
a contribution or a rewrite.

## Start here

**Prerequisites:** Phase 0 complete. Verify: `grep -n "DESIGN_CONFORMANCE_REVIEWER"
src/models/enums.py` returns output, **and** a real `/respec-code` run has reached consolidation.

**Phase 3 depends on this phase**, and phase 2 does too — but neither is a prerequisite *for* it. If
you are choosing between phases, this one has no upstream blockers beyond phase 0.

**Already done?** `grep -rn "LanguageMaterializer" src/utils/` — output means complete.

**Read first:** [README.md](README.md) (especially *"The expensive capability is the optional one"*),
`docs/phase-refactor/testing.md`, `CLAUDE.md`, and [findings.md](findings.md) **F3**–**F9**, **F21**,
**F27**. In [decisions.md](decisions.md), read *"The materializer gets a language seam, not a Python
guard"*, *"Introspection is an optional capability"*, and *"Language resolves from the extension map,
not `stack.toml`"* — all three were reversals and all three will look wrong if you only read the code.

Background: `docs/phase-refactor/phase-4-skeletons.md` is where the materializer was built and explains
what it is for.

**First action:** write B4 — Python materialization produces byte-identical output to today — and get
it green *before* moving a single line. This is a refactor of working code; the Python path must come
out the other side unchanged, and that is much easier to assert before the code moves than after.

**Two things here need your judgment and no test will catch them:**

1. **Where the protocol boundary falls.** The test of a correct boundary is: adding Go later touches
   only a new Go materializer module and a registry entry. If you find yourself wanting to special-case
   a language *outside* its own module, the boundary is wrong. Cross-cutting risk #1 in the README.
2. **What TypeScript's `not_implemented_sentinel` should be.** It has to be something the coder can
   recognize (**F9**), something a type checker accepts, and something that fails at runtime rather
   than silently returning `undefined`. `throw new Error('Not implemented')` is the obvious candidate;
   confirm it type-checks in a `.tsx` component position before committing to it.

**Line numbers below were verified at design time.** Confirm each before acting.

## Goal

Make materialization dispatch by language. Python behaves exactly as it does today; TypeScript works
for the first time; the remaining 24 languages in `language_standards.json` become additive.

## Why this is the largest and most valuable phase

Frontend code is essentially never Python, so this is not one of several improvements — it is what
makes frontend code eligible for the design → skeleton → TDD-red spine at all. It is also
independently shippable: a project gains correct TypeScript materialization whether or not any later
phase ever lands.

The current state is worse than "unsupported." `_SIGNATURE` (`skeleton_generator.py:8-11`) *matches*
TS-shaped signatures like `LoginForm(props: Props) -> JSX.Element`, so a TypeScript entry does not
error — it produces Python inside a `.tsx` file, which `phase_command.py:766-772` then `git add`s and
`git commit --no-verify`s. Silent corruption, committed. See **F4**, **F5**.

## The capability split

This is the design decision the phase exists to encode. The four things a language needs from the
materializer differ enormously in cost:

| Capability | Cost | Why |
|---|---|---|
| Test scaffold rendering | Minimal | `language_standards.json` already has `testing.framework`, `.location`, `.naming` for all 26 languages (**F21**) |
| Declaration rendering | Low-moderate | A small emit template |
| Signature parsing | Moderate | One grammar per language |
| Introspecting existing source | **Significant** | Python has stdlib `ast`; TS/Go/Rust need a parser or heuristics |

**So `extract_existing_signatures` is optional on the protocol.** Languages that implement it get
merge-into-existing-file and signature reconciliation. Languages that don't degrade to **create-only
with an explicit user-facing notice** — never a silent skip, and never Python emitted into a foreign
file.

Python ships with introspection (stdlib, no dependency cost). **TypeScript ships without it** — see
[deferred-issues.md](deferred-issues.md) for why the parser-dependency decision is deliberately not
made here. That asymmetry is the point: it exercises the optional path under real load rather than
leaving it hypothetical.

## Behaviors to pin (red step — write these first)

| # | Behavior |
|---|---|
| B1 | An unsupported language produces a clear message naming the path and language — not Python in a foreign file, not a traceback |
| B2 | A Python Skeleton Index entry materializes valid Python, verified by parsing the output with `ast`, not by string matching |
| B3 | A TypeScript entry materializes valid TypeScript, verified by parsing the output with real TS tooling |
| B4 | Python materialization output is byte-identical to the pre-refactor implementation |
| B5 | A pre-existing `.tsx` at a Skeleton Index path yields a create-only notice, not a `SyntaxError` |
| B6 | A pre-existing `.py` still yields signature reconciliation exactly as today |
| B7 | Unmaterializable and unintrospectable paths appear in the CLI JSON and are displayed at phase step 11.5 |
| B8 | `check-conformance` classifies a new cross-module TypeScript export as `added_cross_module` (a blocker) |
| B9 | A `.spec.ts` / `.test.ts` file is recognized as a test file, not as a production module |
| B10 | The coder template refers to the language's own sentinel, not `raise NotImplementedError`, for a TS phase |
| B11 | `STEP_MODES` derives frontend detection from the extension map — an `.astro` file activates frontend mode |

B4 is the regression guard for the whole phase; write it first and keep it green throughout. B2 and
B3 must parse rather than string-match, or they will pass on syntactically broken output.

## Scope

### The extension map

No file-extension → language mapping exists anywhere in the codebase, and it is a prerequisite for
both materialization and for scoping reviewers to changed files. New module, seeded from
`language_standards.json`.

This is consumed by four things: the materializer registry (this phase), `design_conformance.py`
(this phase), `STEP_MODES` detection (this phase), and phase 6's domain classification. Design it for
all four.

### The protocol and registry

Model on `src/platform/tui_adapters/__init__.py:8-12` — a literal `_ADAPTER_MAP` dict plus a
`get_*` factory — which is the closest existing structural match (**F27**). Fail-loud on unknown,
matching `src/platform/adapters/factory.py:7-15`.

Required protocol members: `render_skeleton_module`, `render_test_module`, `parse_signature`,
`test_path_convention`, `not_implemented_sentinel`. Optional: `extract_existing_signatures`.

Seed test conventions from `language_standards.json[lang]['testing']` so the test-scaffold renderer is
**data-driven rather than per-language code**. This is what makes the remaining 24 languages cheap; if
you find yourself writing a per-language test renderer, stop and reconsider.

### Splitting `skeleton_generator.py`

The module already has a clean seam. Everything from `_render_member_body:153` down is Python-specific
and moves into the Python materializer:

`_render_member_body:153-161` · `_render_import_lines:164-168` · `render_skeleton_module:171-190` ·
`render_test_module:193-197` · `_render_signature:200-207` · `extract_existing_signatures:210-224` ·
`_class_insertion_point:279-290` (indent-based, so Python-only) · `_QUALIFIED_TYPE_REF:15` and
`_extract_imports_and_bare_text:18-28` (dotted-path import inference)

Everything above it is already language-neutral and **stays**: `_BULLET_PATH:6`, `_strip_tags:82-94`,
`parse_skeleton_index:116-129`, `parse_test_list:132-143`, `_resolve_within_project:146-150`,
`_filter_declined_internals:249-255`, and the orchestration in `generate_skeletons:258-276`,
`merge_new_members:293-339`, `generate_tests:342-353`.

`_SIGNATURE:8-11` moves to the Python materializer as its `parse_signature`. TypeScript needs its own,
and its own import-specifier convention — dotted paths are meaningless there.

The dataclasses (`SkeletonMember`, `SkeletonIndexEntry`, `TestListEntry`, `ReconciliationChoice`, the
result types) stay language-neutral. `SkeletonMember.required_imports` is currently
`frozenset[tuple[str, str]]` shaped as `(module_path, name)`; TypeScript needs `(specifier, name)`
where the specifier is a relative path. Same shape, different semantics — decide whether that is
honest or whether it needs renaming.

### Threading language through — from the extension map, **not** `stack.toml`

`materialize-skeletons` and `check-conformance` resolve language **per entry, via the extension map**.

This is deliberate and the dependency runs the way it looks wrong. The per-language tables in
`stack.toml` are empty for the non-primary language until phase 3 lands (**F2**), so consulting
`stack.toml` here would resolve a Python+React project's TypeScript entries as *Python* —
reintroducing exactly the corruption this phase exists to remove. Phase 3 adds `stack.toml`
consultation once the tables it reads are populated, and asserts both paths agree.

Also in this phase:
- Give `phase_architect` `project_config_context_markdown` (**F8**). It is the only major agent
  without it, and it is the natural injection point for phase 2's language-aware prompts. Adding the
  input here means phase 2 is prompt-only.
- Update `coder.py:375` to read `not_implemented_sentinel` rather than hardcoding
  `raise NotImplementedError` (**F9**).
- Drive `STEP_MODES` frontend detection (`code_command.py:300-322`) from the extension map (**F14**).
  It is a second hardcoded extension list and will drift from the first; `.astro`, `.mdx`, Blade, and
  ERB projects currently never activate a frontend reviewer at all.

### Guarding `ast.parse` and making conformance language-aware

Wrap every `ast.parse` call site — `skeleton_generator.py:213`, `design_conformance.py:61,149` — and
widen `except` coverage in `materialize_skeletons.py:80` (currently catches only
`SkeletonPathEscapesProjectError`) and `check_conformance.py:27` (catches nothing). A Python traceback
as a phase-failure diagnostic is a Python-invisibility violation, not just a robustness bug (**F6**);
`phase_command.py:701` fail-closes on non-zero exit and shows whatever came out.

Make `design_conformance.py` language-aware (**F7**): replace the `*.py` glob at `:92` with an
extension-map-driven scan, and drive `_TEST_PATH_MARKERS:7` from `language_standards.json` testing
conventions. Without this the cross-module blocker **silently never fires on frontend code** — a gate
that appears to run and always passes, which is worse than one that is absent.

### Surfacing degradation

Create-only and unmaterializable outcomes must be reported, never silent. Silent skip is its own bug:
the Test List would promise tests the coder is instructed to build against that were never created.

Report `unmaterialized_paths` and `unintrospectable_paths` in the CLI JSON, and display them at
`phase_command.py` step 11.5 (`:680-774`), recording a Settled Decision via the existing reconciliation
pattern at `:745-760`.

## Out of scope

- **Changing what the architect emits.** The prompt-level grammar is phase 2. This phase makes the
  *machinery* language-aware; the architect still writes Python-shaped entries until phase 2 teaches it
  otherwise. That is fine — Python-shaped entries for `.py` files are correct.
- **Reading `stack.toml`.** Phase 3, for the reason above.
- **TypeScript introspection.** Deliberately deferred; see
  [deferred-issues.md](deferred-issues.md#typescript-signature-introspection).
- **Go, Rust, or any third language.** The seam must make them cheap; proving that is a later
  contribution, not this phase's job.
- **`no_preference` validation and the six unconfigured languages** (**F24**, **F26**). Real bugs,
  orthogonal to materialization. See [deferred-issues.md](deferred-issues.md).

## Exit criteria

- B1–B11 green.
- **B4 in particular**: Python output byte-identical to pre-refactor. If it is not, you have changed
  behavior while claiming to move code.
- A phase containing *both* a `.py` and a `.tsx` Skeleton Index entry materializes both correctly in
  one run, each in its own language.
- **The boundary test, by hand:** write down every file you would touch to add Go. If that list
  contains anything other than a new materializer module and one registry entry, the boundary is wrong
  — fix it now. This is the single most important check in the phase and no automated test covers it.
- `respec-ai regenerate` completes for all three TUIs.
- `uv run pytest` clean; `respec-ai check-conformance` clean.
