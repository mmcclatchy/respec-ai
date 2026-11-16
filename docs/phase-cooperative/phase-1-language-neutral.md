# Phase 1 — Language-neutral foundation

**Depends on:** nothing. **Blocks:** Phase 2, and through it phases 3 and 4.
**Risk:** low to moderate. Most of the work is prompt text, plus one small CLI subcommand. It can go
wrong in two ways:
- Python and TypeScript projects silently lose rules that materialization depends on, if those rules
  leave the static templates but never arrive at runtime. Python skeletons then fail type checks
  and Python test modules fail to parse.
- The denylist is noisy enough that someone weakens it.

## Start here

**Prerequisites.** No other phase. Verify the baseline and the foundation documents:

```bash
uv run pytest -q   # baseline, re-run 2026-11-13: 1671 passed, 84 skipped
ls docs/phase-cooperative/findings.md docs/phase-cooperative/decisions.md
```

If `findings.md` is missing, stop. This document cites findings by number and does not restate
them.

**Already done?** This is the README probe, copied verbatim. Phase 1 is done when both hold:

```bash
uv run pytest -q tests/unit/templates/test_phase_language_neutrality.py   # exit 0
grep -n -i -E "python|typescript|\.tsx|jsx" src/platform/templates/phase_contract_grammar.py   # prints nothing
```

- Run the pytest command on its own, with nothing after a pipe. `| tail` replaces pytest's exit code
  with tail's own.
- Run on 2026-11-13, both reported "not done":
  - pytest exited 4 with *"file or directory not found"*.
  - grep printed six lines: `phase_contract_grammar.py:12`, `:17`, `:20`, `:22`, `:32` and `:33`.
- Neither probe false-positives on unrelated text:
  - The first names a file that only this phase creates.
  - The second reads only the shared grammar module, and every hit there is in this phase's scope.

**Partial progress.** If you are resuming, these show which work items have landed:

```bash
uv run respec-ai language-guidance                                             # item 4: exit 2, "invalid choice" until it lands
grep -n "class SkeletonIndexParseError" src/utils/skeleton_types.py            # item 3
grep -n "language-guidance" src/platform/templates/commands/phase_command.py   # item 5
grep -n "verify: ask user" src/platform/templates/agents/phase_architect.py    # item 7
```

**Read first:**
- `docs/phase-cooperative/README.md`, in particular:
  - "Guiding principles → Zero language bias"
  - "Shared contracts → Section naming and frozen-reader compatibility", which lists the Skeleton
    Index, Test List and Checklist forms every phase must keep emitting
- `docs/phase-refactor/testing.md`. Required.
- `CLAUDE.md`.
- `findings.md`:
  - **F20**–**F22**: the bias inventory
  - **F23**: tests that require the bias
  - **F24**: why the Skeleton Index must stay a meta-notation
  - **F25**: the runtime language-config gaps
  - **F37**: hermetic rendering
- `decisions.md`:
  - "Zero language bias, enforced by a denylist guard test"
  - "'Neutral' means a uniform meta-notation, not native syntax"

**First action:** write B1–B4, the guard and its self-tests, then run B1 and read the failure
output. That output is this phase's work inventory. The anchors in *Scope* came from a prototype of
the same scan, re-run on 2026-11-13 with exactly the denylist and rendering specified in item 1.
Counting one hit per (rendered line, denylist entry), the Claude Code + markdown render has 82 hits
in `respec-phase-architect`, 26 in the `respec-phase` command, 5 in `respec-phase-critic` and none
in `respec-create-phase`. Across all 36 renders (3 TUIs × 3 platforms × 4 templates) there are 1017.
Every other render's hits are a subset of the Claude Code + markdown render's, and every one of
those hits maps to item 2 (the shared grammar), to item 7 (the verify-command rule and its
example), or to a row in the item 6 or item 8 tables.
- *Corrected during implementation (2026-11-13).* The prototype counted 80, 25 and 990 because it
  matched `::test_` with word boundaries. That misses `test_module.py::test_x`, where the character
  before `::` is a word character, so the grammar's `:29` example and `phase_architect.py:807` were
  not counted under `::test_` (both lines were still hits through `.py`). The guard matches `::test_`
  as a plain substring (item 1, explicit entries); re-running the scan with the word-bounded form
  reproduces 80, 25 and 990 exactly.

**Judgment calls no test will catch:**
1. **A neutral example still has to teach.** Placeholders everywhere teach less than a concrete
   example.
   - Use concrete, language-free domain examples such as a ledger, a storage client or a query
     translator, written in the meta-notation.
   - Read every rewritten passage and ask whether a model could still produce a good entry from it.
2. **The guard is a floor, not a ceiling.** Paradigm words are deliberately not denylisted,
   because they collide with ordinary prose (see the exclusions in item 1). Examples are "class",
   "method", "interface" and "protocol".
   - Re-read each passage you touch for object-oriented assumptions.
   - The neutral vocabulary is: *public seam*, *exported unit*, *owner*, *member*, *unit*.
3. **The moved per-language rules must be complete.** The materializer notes (item 4) replace text
   that Python and TypeScript projects rely on today. Review the moved content against its source
   lines, not from memory.
4. **Do not redesign passages that phase 2 deletes.** Examples are the FSDD rubric, Step 16.5's
   automatic API research and the command's Research Requirements example. Phase 1 still
   neutralizes them, because the guard must be green at phase 1's exit. Make the smallest neutral
   substitution and move on.
5. **Never write the literal `## Decisions needed` into any template.** It is the phase 2 completion
   probe (README "Find out which phase to work on"). Phase 1 keeps the current flow. The
   verify-command fallback uses the existing channel instead (item 7): the architect only writes a
   marker, and the orchestrator asks the user. No subagent asks the user anything (F10).
6. **The guard sees template output, not adapter write wrappers.**
   - Adapters add text when they write files, for example codex's guardrail prefix (F39).
   - Today `grep -n -i -E "python|typescript|react|pytest|npm" src/platform/tui_adapters/*.py`
     finds no hits.
   - If an adapter later adds prose to written artifacts, extend the guard to the written files.
7. **New prose must pass the imperative-language audits.** These two tests reject `should`,
   `consider`, `think about`, `try to`, `you will`, `your role is`, `may` and `can`. They apply to
   every line in an actionable section, including lines inside `text` fences:
   - `test_agent_templates.py:660-681` covers the architect and the critic. The word list is at
     `:53-62`.
   - `test_command_templates.py:1176-1186` covers the command. The word list is at `:15-24`.

   "can" is the likeliest slip in rewritten rules. Every replacement text in this document already
   avoids these words.

**Line numbers below were verified on 2026-11-13.** Confirm each before acting (README "Line
numbers may be stale").

## Goal

Make every phase-workflow template neutral by construction, and give the architect language
specifics only at runtime, and only for the target project's languages:

- **The shared grammar** teaches respec-ai's uniform meta-notation with neutral placeholders,
  never native syntax (F24).
- **Test naming and location** come from the project's standards TOMLs. They are already loaded into
  `PROJECT_CONFIG_CONTEXT_MARKDOWN` by Step 4.5 (F25). The generation-time
  `('python', 'typescript')` loop goes.
- **Per-language authoring rules** come from each `LanguageMaterializer`. A new CLI subcommand
  prints them for the languages declared in `stack.toml`, and Step 4.5 appends them. A declared
  language with no materializer gets a neutral "recorded but not materialized" note.
- **Verify commands** come only from `[commands].test`. A missing one is marked visibly by the
  architect, never guessed, and shown to the user in the Step 12.6 walkthrough. Phase 2's briefing
  asks about it explicitly (item 7, "Cut from this phase").
- **Malformed Skeleton Index lines** are reported as one readable error, quoting the entry
  verbatim, instead of as a traceback, and the phase command surfaces that error.
- **A denylist guard test** keeps it this way on all three TUIs.

The two-act flow is unchanged. Phase 2 rewrites the flow on top of this foundation, and the guard
keeps that rewrite neutral.

## Behaviors to pin (red step — write these first)

| # | Behavior | Test location | Red today? |
|---|---|---|---|
| B1 | No phase-workflow artifact, rendered for any TUI and any platform, names a programming language, a framework, library or runtime, a test, build or package tool, a language file extension, or language-specific syntax | `tests/unit/templates/test_phase_language_neutrality.py` | yes: 1017 hits |
| B2 | The guard fires for every denylist category | same file | see note |
| B3 | The guard does not fire on neutral workflow prose | same file | see note |
| B4 | Every language and file extension respec-ai knows is covered by the guard, so a newly added language cannot escape it | same file | see note |
| B5 | Test naming conventions reach the architect only from the target project's config. No language's `[testing].naming` value from `language_standards.json` appears in the rendered architect | same file | yes: Python's and TypeScript's are rendered today |
| B6 | A Skeleton Index or Test List entry written in the form the templates teach is accepted by the parser, even for a path no materializer claims | same file | no: regression guard, see note |
| B7 | A malformed Skeleton Index line gets a readable error naming the entry's path and quoting the offending text verbatim, exit 1, and no traceback, from both `materialize-skeletons` and `check-conformance` | `tests/unit/cli/commands/test_materialize_skeletons.py`, `test_check_conformance.py` | yes: `ValueError` propagates (probe below) |
| B8 | Language authoring notes cover exactly the project's declared languages, in `stack.toml` order: a registered language's own notes, and the neutral note for a declared language with no materializer | `tests/unit/cli/commands/test_language_guidance.py` | yes |
| B9 | Every registered language gets its own authoring notes, never the neutral note. This prevents the silent failure where a new language ships with no notes and the architect gets no rules for it | `tests/unit/utils/test_materializer_authoring_notes.py`, parametrized over the keys of the public `sentinel_table()` (exactly the registered languages) | yes |
| B10 | With no declared languages (no `stack.toml`, or an empty `[project].languages`), the CLI exits 0 with a neutral note. With an unreadable or malformed `stack.toml`, it exits 1 with an error that names `stack.toml`, and no traceback | `test_language_guidance.py` | yes |
| B11 | On every TUI, the orchestrator gives the architect the notes: Step 4.5 runs `respec-ai language-guidance`, puts its output under `### Language Authoring Notes` in `PROJECT_CONFIG_CONTEXT_MARKDOWN`, and continues rather than terminating when the command fails | `tests/unit/templates/test_phase_runtime_language_config.py` | yes |
| B12 | A missing verify command is never guessed and stays visible to the user. The architect writes the exact marker `(verify: ask user` when the owning language's `[commands].test` is absent, empty, `TODO` or `no_preference`. The marker is shown to the user in the existing Step 12.6 walkthrough of `implementation.md`; phase 2's briefing turns it into an explicit question (see item 7, "Cut from this phase") | `test_phase_runtime_language_config.py` | yes |

**Keep B11 and B12 out of the guard file.**
- The guard file is phase 1's completion probe, so it must stay green for good.
- B11 and B12 anchor on step numbers that phase 2 deletes or renumbers.
- **Phase 2 re-anchors both in `test_phase_runtime_language_config.py`** (its work item 8):
  - B11 on Step 3, which replaces Step 4.5.
  - B12 on the briefing (decisions.md "Zero language bias": *"the briefing asks the user"*).

**Notes on the red step.**
- **B2–B4 are self-tests of the guard.** Their red step is to run them against a deliberately broken
  scanner:
  - an empty denylist, for B2 and B4
  - a denylist containing `class`, for B3

  Confirm each fails, then restore the scanner. README "Per-phase exit criteria" requires this,
  because a guard with no proven firing proves nothing.
- **B6 passes against today's placeholders,** whose concrete names happen to parse. Prove it can
  fail: point it once at the rejected placeholder ``- `<path>` :: <signature in that file's
  language>`` (decisions.md, "'Neutral' means a uniform meta-notation") and watch it go red.
  - Mechanics: take every bullet line of `SKELETON_INDEX_PLACEHOLDER` and `TEST_LIST_PLACEHOLDER`.
    Replace each `<…>` token with `X`, which yields a path with no extension and therefore no
    materializer. Then run `parse_skeleton_index` / `parse_test_list`.
- **B7, observed 2026-11-13.** Running `respec-ai materialize-skeletons` on
  ``- `internal/server/server.go` :: func (s *Server) Start(ctx context.Context) error`` printed a
  traceback ending in *"ValueError: Unparseable Skeleton Index signature"*.
  - Use a native line whose text contains square brackets as B7's input, for example
    ``- `src/loader.py` :: def load(paths: list[str]) -> dict[str, int]:``. `print_error` renders
    through rich, and rich treats `[str]` as markup and drops it. Probed during review:
    `print_error("… list[str] …")` printed `list`. The test asserts that the offending text appears
    verbatim, so a handler that forgets to escape stays red.
  - Assert on whitespace-normalized output (`' '.join(captured.out.split())`), never on a line count.
    When output is not a terminal, rich wraps at 80 columns, so a realistic message spans several
    physical lines. Probed during review: the example message in item 3 wrapped to three lines.
  - For `check-conformance`, the input goes in the JSON payload on stdin, as in the existing
    `test_check_conformance.py` tests (`monkeypatch.setattr('sys.stdin', io.StringIO(...))`).
- **B8–B10 need a stub first.** Before writing the tests, create two stubs:
  - `src/cli/commands/language_guidance.py`, with `add_arguments` and a `run` that returns 1
  - `language_authoring_notes` in `src/utils/materializers/__init__.py`, returning `''`, plus the
    two note constants from item 4 (`UNMATERIALIZED_LANGUAGE_NOTE` there,
    `NO_DECLARED_LANGUAGES_NOTE` in the CLI module) with their final text

  The red is then an assertion failure, not an `ImportError`, which testing.md treats as the wrong
  reason. B10's malformed-file case asserts that the output names `stack.toml`, so it fails against
  the stub even though the stub already returns 1.
- **B11 and B12 are string assertions, and deliberately so.** Each pinned string is parsed by a
  consumer, which testing.md's exception allows. Say so in a comment in each test.
  - B11 pins the subcommand name, because the CLI parses it. It also pins the
    `### Language Authoring Notes` heading, because the architect's prompt names that heading as
    where its rules arrive (items 2 and 6).
  - B12 pins the marker, because phase 2's briefing scans for it and phase 3's structural checks
    inherit it.
  - Anchor B11 on `template_contract(...).step_body('4.5')`
    (`tests/support/template_contract.py:88-102`), not on the whole template.

## Scope

Work the items in this order. Each item names the behavior it turns green.

### 1. The guard: `tests/unit/templates/test_phase_language_neutrality.py` (B1–B6)

**Rendering.** Render through the same entry points that write artifacts
(`src/platform/template_generator.py:176-187`), with the same `plans_dir=adapter.plans_dir()`
argument they pass:
- **Command:** `TemplateCoordinator().generate_command_template(RespecAICommand.PHASE, platform,
  plans_dir=adapter.plans_dir(), tui_adapter=adapter)`. This is the raw output, frontmatter
  included.
- **Agents:** `_get_agent_specs(adapter, platform, plans_dir=adapter.plans_dir())`. Tests already
  call this private function (`tests/unit/templates/test_coder_split_phase9.py:43`, without
  `plans_dir`). `plans_dir()` returns a constant on every adapter, so passing it keeps rendering
  hermetic, and the hit counts are the same with or without it. Keep every spec whose name starts
  with `respec-phase-`, plus `respec-create-phase`, and scan both `spec.description` and
  `spec.body`.
  The prefix covers phase 4's `respec-phase-finalizer` automatically, which decisions.md's guard
  scope requires.
- **Adapters:** `ClaudeCodeAdapter()`, `OpenCodeAdapter(model_overrides=M)` and
  `CodexAdapter(model_overrides=M)`, where `M` sets `reasoning`, `orchestration`, `coding` and
  `review` (F37).
- **Platforms:** every `PlatformType`, because the command's and create-phase's tool text varies by
  platform.
- **Caching:** cache the rendered set per (adapter class, platform). Each `_get_agent_specs` call
  renders every agent in `_AGENT_NAMES` (`src/platform/template_generator.py:109-131`).
- **Why these entry points:** they do not move when phase 2 changes tool-factory signatures. For
  example, `create_phase_critic_agent_tools`'s soft-cap arguments are cut (F36).

**Scanner.** A pure function in the test module returns hits as (category, matched term, line).
- **Categories.** There are exactly five. B2 needs one sample per category. The *Category* column of
  the explicit-entries table below assigns each entry; derived language names are `language` and
  derived extensions are `extension`.
  - `language`: languages, their alternate spellings, and query or schema languages
  - `framework`: frameworks, libraries and language runtimes
  - `tool`: test runners, package managers, build drivers, type checkers and linters
  - `extension`: language file extensions
  - `syntax`: keyword and test-idiom forms, fence info strings, and object-oriented placeholders
- **Word entries:** case-insensitive with word boundaries, `(?<!\w)term(?!\w)`. This catches
  "Python-specific" and `[language.python]`, but not "pipeline" for `pip`. The one exception is
  `::test_`, matched as a plain substring: it sits between a file name and a test name, so both of
  its neighbors are word characters.
- **Extensions:** case-sensitive, `re.escape(ext) + r'(?![\w-])'`. This catches `foo.py` and
  `` `.tsx` ``, but not `.respec-ai`, `.json` or `.md`.
- **Failure message:** group hits by template, then by term and line, and list which renders contain
  each hit. The red output is then a readable work list rather than 990 lines.

**Category rule.** Anything that presumes the target project's programming language or its ecosystem
is denylisted. That means languages, including query and schema languages, plus frameworks,
libraries, language runtimes, test/build/package tools, file extensions and language-specific
syntax. Products and infrastructure are not denylisted, because they do not presume a language.
Examples of products and infrastructure are datastores, containers and cloud vendors.

**Derived entries.** These grow automatically when respec-ai learns a language (B4):

| Entries | Source | Why |
|---|---|---|
| Every language key except `universal` and the four common-word keys below | `available_languages()` (`src/platform/standards_config.py:51-56`, reading `src/platform/data/language_standards.json`) | A language name in workflow text is the bias itself. Deriving the list means a newly added language is covered with no edit to the guard. |
| Every extension in `EXTENSION_TO_LANGUAGE` and `FRONTEND_EXTENSIONS` | `src/utils/language_extensions.py:7-46` | Example paths such as `src/path/to/module.py` and `Component.tsx` presume a language; today's grammar uses both. |

**Explicit entries:**

| Entries | Category | Why each is on the list |
|---|---|---|
| `golang`, `c++`, `c#` | `language` | Spellings of registered languages that the keys `go`, `cpp` and `csharp` do not match. |
| `sql`, `graphql` | `language` | Query and schema languages. The architect's Data Models and API Design templates present `CREATE TABLE` and GraphQL schemas as *the* notation (`phase_architect.py:1133-1159`). `sql` does not match "NoSQL", "PostgreSQL" or "SQLite". |
| `react`, `vue`, `svelte`, `angular`, `next.js`, `htmx`, `jsx`, `tsx` | `framework` | UI frameworks and their file dialects. `react`, `htmx`, `jsx` and `tsx` are hits today (`phase_architect.py:200`, `:541`, `:883`; the grammar's `JSX.Element`). |
| `django`, `fastapi`, `pydantic`, `sqlalchemy`, `laravel`, `express.js` | `framework` | Server frameworks and libraries tied to one language ecosystem. `pydantic` is a hit today (`phase_architect.py:783`, `:893`). |
| `llamaindex`, `llama-index` | `framework` | A library named as a target-project example (`phase_architect.py:776-782`, `:944`). `llama-index` is its distribution name, which the command's example phase slug used (`phase_command.py:313`, `:1763-1764`; `:1771-1772` after this phase). |
| `fastmcp` | `framework` | A library tied to one language ecosystem, and respec-ai's own dependency (`pyproject.toml`), so a likely leak for the same reason as `uv`. It was the architect's "Example RIGHT" best-practices filename (`phase_architect.py:1293`; `:1260` after this phase). |
| `node.js`, `nodejs`, `deno` | `framework` | Language runtimes. `Node.js` is a hit today (`phase_architect.py:318`, `phase_command.py:1332`). |
| `pytest`, `unittest`, `jest`, `vitest`, `mocha`, `rspec`, `junit`, `phpunit` | `tool` | Test runners. A runner written into a template is exactly how a guessed verify command returns. `pytest` is a hit today (`phase_architect.py:107-108`, `:603`; grammar `:32`). |
| `npm`, `npx`, `yarn`, `pnpm`, `pip`, `poetry`, `uv` | `tool` | Package managers and runners. `npm` is a hit today (`phase_architect.py:109`, `:604`). `uv` is listed because respec-ai itself is developed with it, which makes it the likeliest leak. |
| `cargo`, `gradle`, `maven`, `dotnet`, `go test`, `mix test` | `tool` | Build and test drivers for registered languages. The multi-word forms cover Go and Elixir without matching the English word "go". |
| `mypy`, `ruff`, `eslint`, `tsc` | `tool` | Type checkers and linters, which carry the same verify-command risk. |
| `async def`, `__init__` | `syntax` | Python keyword and dunder forms. The old grammar's `, async` guidance invites them. |
| `::test_` (plain substring, no word boundaries) | `syntax` | A Test List example shaped like a pytest node-id (`phase_critic.py:1136`, grammar `:29`). |
| `describe/it`, `node-id` | `syntax` | Test-framework idioms (grammar `:32-33`). `node id` with a space is not listed, because UX prose uses it for a DOM node. |
| Fence info strings `py`, `ts`, `js`, `jsx`, `tsx`, `rb`, `rs`, `kt`, `cs`, `go`, `c`, `cpp`, `r`, matched as ```` ```<x>\b ```` | `syntax` | Abbreviations the language-name rule cannot see. `go`, `c` and `r` are unambiguous here, though not as words. |
| `ClassName`, `method_name` (case-sensitive), `base class`, `concrete class` | `syntax` | Object-oriented placeholders and vocabulary with a neutral replacement (`<Owner>.<member>`, "concrete unit"). They are hits today (grammar `:16`, `phase_architect.py:842`, `phase_critic.py:1121`, `:1127`). |

**Excluded, with reasons.** The B3 corpus pins each exclusion.

| Not on the list | Why | What covers it instead |
|---|---|---|
| Language keys `c`, `r`, `go`, `shell` | Common words or single letters. "Option C:" is part of the decision format (README "Decision entry"), and "go back to Step 8" is normal prose. | The extensions `.c`, `.r`, `.go`, `.sh`; fence strings; `golang`; `go test` |
| `bash` | It is the TUI's shell tool (`RUN (Bash): …`), not the target's language. | — |
| `class`, `method`, `interface`, `protocol`, `module`, `function`, `component`, `node` | Ordinary workflow vocabulary: "decision classes", "verification methods", "interface contracts", "MANDATORY DECISION PROTOCOL", a graph node. | Judgment call 2, plus the explicit OO placeholders above |
| `express`, `spring`, `rails`, `browser`, `lambda`, `stack` | English words. | `express.js`; nothing else needed today |
| PostgreSQL, Neo4j, Docker, Kubernetes, AWS, GCP, Azure, Prometheus | Products and infrastructure, which presume no programming language. Docker and Neo4j are also respec-ai's own KB runtime (`phase_command.py:1700`). | Item 8 still replaces the command's research examples that name PostgreSQL (`phase_command.py:1655`, `:1659`). Infrastructure placeholders are left to phase 2 (*Out of scope*). |
| `.md`, `.toml`, `.json`, `.yaml`; fence strings `json`, `toml`, `markdown`, `text`, `bash` | respec-ai's own document, config and payload formats, and the agent's own shell commands. | — |

- **No allowlist mechanism.** decisions.md's guard scope says respec-ai's own tooling nouns, such as
  the Neo4j KB behind best-practices-rag, are never denylisted. This design meets that by exclusion:
  products and infrastructure are never denylisted, so no allowlist is needed. respec-ai self-references that
  carry a language extension are reworded instead, for example `code_command.py` at
  `phase_architect.py:590-591` (item 6).
- **Accepted collision risk.** `swift`, `rust`, `dart`, `elixir`, `jest`, `poetry`, `cargo`,
  `angular`, the verb "react", and `.m` in "p.m." can all collide with prose. When one does, reword
  the prose; never delete the entry. Inflections such as "reactions" do not match.

**Self-tests:**
- **B2:** one synthetic line per category must produce at least one hit in that category. Use, for
  example, "written in Python" (`language`), ``"`src/app/main.rs`"`` (`extension`), "built with
  Django" (`framework`), ``"run `pytest -q`"`` (`tool`) and ``"`async def handler`"`` (`syntax`).
- **B3:** a neutral corpus must produce zero hits. The prototype corpus produced none on 2026-11-13.
  The exclusions table says this corpus pins each exclusion, but the prototype's lines did not use
  the bare words "class", "method" or "component", or the products and formats Kubernetes, AWS, GCP,
  Azure, Prometheus, `.json` and `.yaml`. In particular, a scanner broken by adding `class` (the red
  step) stayed green on it, because "classes" does not match the word pattern. The guard adds one
  line for each (marked *added*). It contains:
  - "Option C: keep as designed"
  - "presence-only frontend decision classes"
  - "the class of decision each entry belongs to" (*added*)
  - "interface contracts"
  - "MANDATORY DECISION PROTOCOL"
  - "each module owns one responsibility"
  - "avoid single-function phases"
  - "the verification method for each step" (*added*)
    - *Corrected during the fix pass (2026-11-13).* This line read "verification methods for each
      step", which does not pin `method`: the plural does not match the word pattern, the same flaw
      as "classes". With `method` added to the denylist, B3 stayed green on it.
  - "each component of the design shape" (*added*)
  - "go back to Step 8"
  - "run it through the Bash tool"
  - "check Docker and Neo4j status via `best-practices-rag check`"
  - "`.respec-ai/plans/<plan>/phases/<phase>/phase.md`"
  - "`.respec-ai/config/stack.toml`"
  - "the `.json` payload and the `.yaml` workflow file" (*added*)
  - "the user's reactions to the sketch"
  - "express the decision as an option"
  - "a graph node"
  - "dispatch `bp-pipeline`"
  - "a NoSQL store"
  - "PostgreSQL"
  - "deploy to AWS Lambda behind Kubernetes on GCP or Azure, monitored by Prometheus" (*added*)
  - "the page renders in the browser" (*added*)
  - "the spring release keeps the review on rails" (*added*)
  - "the stack the project declares" (*added*)
  - "read (r) and write (w) access" (*added*)
  - "shell out to the CLI"
  - fence lines for `json`, `bash`, `toml`, `text` and `markdown`
  - "etc.", "e.g.", "i.e."
  - `https://code.claude.com/docs`
- **B4:** for every derived language name and extension, a sample line containing it produces a hit.
  Examples are "written in <name>" and ``"`dir/file<ext>`"``. Each excluded key must also be caught
  through the substitute the exclusions table names for it:
  - `c` through `.c` and ```` ```c ````
  - `r` through `.r` and ```` ```r ````
  - `go` through `.go`, ```` ```go ````, `golang` and `go test`
  - `shell` through `.sh`

  This keeps each exclusion's justification under test. The prototype confirmed all of them on
  2026-11-13.
- **B5:** for every language in `language_standards.json`, its `testing.naming` value is absent from
  every rendered architect. This replaces `test_agent_templates.py:859-870`.
  - Read the values as `build_language_defaults(language)['testing']['naming']` for each language in
    `available_languages()` except `universal` (`src/platform/standards_config.py:51-56`, `:237-263`).
  - Skip empty values, because `'' in template` is always true.
  - Never use `language_testing_convention`. Item 9 deletes it, and the exit criteria grep `tests`
    for its name.
  - *Extended during the fix pass (2026-11-13).* B5 also checks the runtime channel,
    `language_authoring_notes(sorted(sentinel_table()))`. The first implementation copied Python's
    `test_{function}_{scenario}` and TypeScript's test location into the materializer notes, where
    Step 4.5 delivered them to the architect from respec-ai's defaults rather than the project's
    config. Those bullets are deleted (item 4's content list never had them). The TypeScript
    location bullet was a paraphrase, so no exact-value check catches its kind; only `naming` is
    checked, because only exact values are comparable.
- **B6:** as described in the red-step notes.
- **The identifier rule (added during the fix pass, 2026-11-13).** The parser accepts exactly one
  plain identifier for `<Owner>` and for `<member>` (`[A-Za-z_]\w*`), so idiomatic names such as
  `Accounts.valid?`, `User.save!`, `MyApp.Accounts.get_user` or `com.acme.Ledger.post` are rejected
  even for a path no materializer claims. B6 cannot see this, because it substitutes `X`. Two tests
  beside B6 pin it: `SKELETON_INDEX_PLACEHOLDER` and `UNMATERIALIZED_LANGUAGE_NOTE` state the rule,
  and `A.B.c(X) -> X` / `A.c?(X) -> X` are rejected with an error naming the rule while the rewritten
  `B.c(X) -> X` / `A.c_(X) -> X` parse.

B11 and B12 live in `tests/unit/templates/test_phase_runtime_language_config.py`, rendered the same
way on all three TUIs:
- **B11:** on `step_body('4.5')`:
  - It contains `respec-ai language-guidance` and `### Language Authoring Notes`.
  - It contains no `EXIT:`, so no branch of the step terminates the workflow.
  - `outcome_condition(body, 'Language authoring notes unavailable')` starts with `ELSE`, so a
    failed command yields the fallback note rather than a stop.
- **B12:**
  - The rendered architect contains `(verify: ask user` and names `no_preference`. B1 already
    proves that it names no concrete test command.
  - No `step_body('12.6')` assertion: the Step 12.6 prompt is cut (item 7). The existing parity
    test, `test_phase_implementation_plan_gate.py:99-116`, passes unchanged because Step 12.6 is
    not edited.

### 2. Neutral shared grammar: `src/platform/templates/phase_contract_grammar.py` (B1, B6)

Replace `MODULE_LAYOUT_PLACEHOLDER` (`:10-13`), `SKELETON_INDEX_PLACEHOLDER` (`:15-26`) and
`TEST_LIST_PLACEHOLDER` (`:28-34`). These constants render into both the architect and the command
(F20), so this one edit fixes both. Starting text:

```python
MODULE_LAYOUT_PLACEHOLDER = (
    '- `<path to a source file>` — owns [single responsibility]\n'
    '- `<path to another source file>` — owns [single responsibility]'
)

SKELETON_INDEX_PLACEHOLDER = (
    '- `<path to a source file>` :: <Owner>.<member>(<params>) -> <Result>\n'
    '- `<path to a source file>` :: <member>(<params>) -> <Result>\n'
    '  (one line per public seam: every exported unit another module calls. This is the'
    ' durable contract the conformance reviewer diffs against. Every language uses this one'
    ' notation; drop `<Owner>.` for a unit with no owner. Only `<params>` and `<Result>` are'
    ' written in the syntax of the language that owns the path. Never write a native'
    ' declaration: materialization parses this notation and rejects anything else.'
    ' Language-specific rules come from `### Language Authoring Notes` in'
    ' project_config_context_markdown. Append `, async` for an asynchronous member.)'
)

TEST_LIST_PLACEHOLDER = (
    '- `<path to a test file>::<observable behavior under a condition>`\n'
    '  (behaviors, not file names — see Testing Strategy for approach. Take the test file'
    ' location and the name form from the `[testing]` `location` and `naming` values of the'
    " owning language's standards TOML in project_config_context_markdown, and follow that"
    " language's section of `### Language Authoring Notes`.)"
)
```

- **Placeholder style.** Angle-bracket placeholders follow decisions.md's notation and need no brace
  doubling, because these constants are interpolated as values, never parsed as f-strings.
- **B6 reads these constants.** Keep every example entry a `- ` bullet with a backticked path, so
  B6's extraction finds it. Keep explanatory text on non-bullet lines such as the parenthetical,
  which both parsers skip.
- **Rejected-placeholder probe, run during review.** With each `<…>` token replaced by `X`, the two
  Skeleton Index bullets above parse through `parse_skeleton_index`, and the Test List bullet parses
  through `parse_test_list`. The rejected ``- `X` :: X`` raises.
- **Leave the other two constants unchanged.** `UX_CONTRACT_PLACEHOLDER` and
  `DESIGN_RESEARCH_PLACEHOLDER` have no hits. Phase 2 retires the second (README "Research
  recording").
- **Frozen-reader shapes still hold.** The Test List keeps `` - `path::name` `` (F34), and the
  Skeleton Index keeps the parser's grammar (`src/utils/skeleton_types.py:6-9`).
- *Added during the fix pass (2026-11-13).* After *"drop `<Owner>.` for a unit with no owner."* the
  parenthetical states the parser's real constraint: *"`<Owner>` and `<member>` are each one plain
  identifier of letters, digits and underscores that does not start with a digit: write a qualified
  owner as its last segment only, and write any other character in a name as an underscore."* The
  architect's "One notation for every language" bullet (item 6) and `UNMATERIALIZED_LANGUAGE_NOTE`
  (item 4) carry the same sentence.

### 3. Malformed Skeleton Index lines reported cleanly (B7)

- **New exception.** In `src/utils/skeleton_types.py`, add `class SkeletonIndexParseError(ValueError)`.
  `parse_bare_signature` raises it instead of the bare `ValueError` at `:76-78`. It stays a
  `ValueError` subclass, so existing callers keep working. No test matches the old
  *"Unparseable Skeleton Index signature"* text (grep `tests`, run during review).
- **Message with context.** In `src/utils/skeleton_generator.py`, `parse_skeleton_index`
  (`:77-96`) catches `SkeletonIndexParseError` around the `_parse_member` call (`:95`). It raises a
  new `SkeletonIndexParseError` from the caught one (`raise … from error`), with a single-line
  message that names the path and the expected notation and quotes the raw signature, for example:
  *"Skeleton Index entry for `internal/server/server.go` is not in the notation
  `<Owner>.<member>(<params>) -> <Result>`: 'func (s *Server) Start(…) error'"*.
  - The message must stay language-neutral.
  - *Extended during the fix pass (2026-11-13).* The message also names the identifier rule:
    *"… `<Owner>.<member>(<params>) -> <Result>` (`<Owner>` and `<member>` must each be one
    identifier of letters, digits and underscores): '…'"*. Without it, an entry such as
    `Accounts.valid?(changeset) -> boolean()` was told it is not in a notation it visibly follows.
  - *Extended during the fix pass (2026-11-13).* `print_error` passes `emoji=False`
    (`src/cli/ui/console.py`). `escape()` stops rich reading `[…]` as markup, but rich still
    replaced `:name:` shortcodes, so `Router.register(_:on:)` printed with a glyph in place of
    `:on:`. B7 gained that entry as a third case in both CLI tests.
  - Both branches of `_parse_member` raise through the same function. The materializer branch
    reaches it too: `PythonMaterializer.parse_signature` (`python_materializer.py:59-60`) calls
    `_parse_python_signature`, which calls `parse_bare_signature` (`:13-14`), and
    `TypeScriptMaterializer.parse_signature` calls it directly (`typescript_materializer.py:37-43`).
- **CLI handling.** Add `SkeletonIndexParseError` to the caught exceptions in
  `src/cli/commands/materialize_skeletons.py:85` and `src/cli/commands/check_conformance.py:30`.
  Import it from `src.utils.skeleton_types`.
  - `design_conformance.py:245` calls the parser unwrapped, so the CLI is where it is caught (F24).
  - Never catch a bare `ValueError`.
  - In both handlers, print `escape(str(e))`, with `from rich.markup import escape` at the top of
    the module. Without it, rich drops bracketed text such as `list[str]` from the quoted entry
    (see the B7 red-step note).
- **Output stream.** `print_error` writes through rich's default console, which is stdout
  (`src/cli/ui/console.py:4`, `:11-12`). B7 therefore asserts on the captured stdout. The phase
  command's Step 11.5 surfaces only stderr when materialization fails (`phase_command.py:875-877`,
  `DIAGNOSTIC: [surface stderr]`). Once the traceback is gone, the user would therefore see nothing.
  Change that one line to `DIAGNOSTIC: [surface the command's stdout and stderr]`.

### 4. Materializer authoring notes and `respec-ai language-guidance` (B8–B10)

**Protocol.** In `src/utils/materializers/base.py:25`, replace the dead
`def test_path_convention(self) -> str: ...` with an attribute `authoring_guidance: str`. The
method has no callers (F25). Delete the two implementations at `python_materializer.py:92-93` and
`typescript_materializer.py:72-73`.

**Content.** Each materializer's `authoring_guidance` holds the per-language rules that leave the
templates in items 2 and 6. The text belongs in these modules, which are language-specific by
nature and outside the guard. Move it from its source lines and check it against them:

- **Python:**
  - A type that is not built in must be written as a fully-qualified dotted path, so that
    materialization emits a real import. Sources: grammar `:20-22`; `phase_architect.py:820-825`;
    `skeleton_types.py:10-13`.
  - `, async` renders a coroutine (`python_materializer.py:31`).
  - `Owner.member` renders a method on a class named `Owner`. A bare member renders a module-level
    function (`python_materializer.py:62-81`).
  - A Test List name becomes the test function's name, so it must be an identifier with the `test_`
    prefix (`python_materializer.py:86-90`). Today nothing checks this (F25).
- **TypeScript:**
  - Write types exactly as declared or imported in the file. Imports are not inferred, and wiring
    them is the implementer's job per `### Collaboration And Wiring`. Sources:
    `phase_architect.py:826-831`; `typescript_materializer.py:37-43`.
  - A UI component entry in a `.tsx` file is the component name with one props parameter, returning
    the element type. It carries props, exports and contract-relevant state or effects, and never
    markup structure, styling or hook internals (`phase_architect.py:832-840`).
  - A Test List name becomes a `test('<name>', …)` description, so it is a plain sentence
    (`typescript_materializer.py:66-70`).
  - `, async` renders an async function (`typescript_materializer.py:24`).

- *Clarified during the fix pass (2026-11-13).* The notes carry no `[testing]` naming or location
  default. Those come only from the project's standards TOML, or from item 6's fallback (the
  nearest existing test files, then a plain description). B5 checks the notes for naming values.

**Registry function.** In `src/utils/materializers/__init__.py`, add
`language_authoring_notes(languages: Iterable[str]) -> str` and export it in `__all__` (`:30-37`).
- It lowercases each name, matching the lowercase `_MATERIALIZER_MAP` keys and the lowercasing in
  `_validate_language_config` (`src/platform/standards_config.py:342`). It then de-duplicates the
  names, preserving order.
- It emits one `#### <language>` section per language:
  - a registered language (`_MATERIALIZER_MAP`, `:9-12`) gets its `authoring_guidance`
  - any other language gets the neutral note
- The neutral note says that no skeleton or test files are generated for that language's paths, and
  that its Skeleton Index and Test List entries are recorded in the design but not materialized. It
  tells the architect to write them in the same notation as every other language, with only the
  parameter and result text in that language's syntax.
- Keep the neutral note in an exported `UPPER_CASE` constant, `UNMATERIALIZED_LANGUAGE_NOTE`, so
  B8 and B9 compare output against it instead of copying its text.

**Subcommand.** Create `src/cli/commands/language_guidance.py`, with `add_arguments(parser)` (no
arguments) and `run(args) -> int`:
- It reads `Path.cwd() / '.respec-ai' / 'config' / 'stack.toml'` with `load_toml_file`
  (`src/platform/standards_config.py:326-328`), using the current working directory as
  `materialize_skeletons.py:38` does.
- The language list is `[project].languages`, read and stripped exactly as `_validate_stack_v2`
  does: `[str(v).strip() for v in project.get('languages', []) if str(v).strip()]`
  (`src/platform/standards_config.py:373-375`).
- **Missing file, or empty list:** print a neutral note saying that no languages are declared in
  `.respec-ai/config/stack.toml` and no language-specific authoring notes apply. Return 0. Keep it
  in a module constant, `NO_DECLARED_LANGUAGES_NOTE`, which B10 compares against. It is a different
  note from `UNMATERIALIZED_LANGUAGE_NOTE`.
- **Unreadable or malformed file:** catch `(tomllib.TOMLDecodeError, UnicodeDecodeError, OSError)`,
  never a bare `Exception`. Call `print_error` with one line that names `stack.toml` and the escaped
  error text (`escape(str(e))`, as in item 3), and return 1.
  - *Corrected during the fix pass (2026-11-13).* The tuple was `(tomllib.TOMLDecodeError, OSError)`.
    `tomllib.load` decodes the bytes before parsing, so a non-UTF-8 file raised `UnicodeDecodeError`
    as a traceback. The existence check also moved inside the `try`, as a first
    `except (FileNotFoundError, NotADirectoryError)` branch that prints the neutral note and returns
    0: `Path.exists()` raised `PermissionError` when `.respec-ai/config` could not be traversed. The
    branch order matters, because both are `OSError` subclasses.
- **Otherwise:** print `language_authoring_notes(languages)` and return 0.
- **Print the notes and the neutral note with the built-in `print`,** as
  `materialize_skeletons.py:91` prints its JSON. Never use the rich console for them. Step 4.5
  captures this output verbatim, and rich would wrap it and strip bracketed text such as
  `[commands].test` or `list[…]`.

**Registration** in `src/cli/main.py`:
- the import list (`:22-42`), between `init` and `materialize_skeletons`
- an `add_parser('language-guidance', help='Print Skeleton Index authoring notes for the languages
  declared in stack.toml')` beside `materialize-skeletons` (`:111-123`)
- a `case` in the dispatch `match` (`:203-244`)

`src/cli/commands/__init__.py` is empty and needs nothing.

**Tests:**
- **B8:** `stack.toml` declares `["python", "go"]`.
  - The output contains `PythonMaterializer.authoring_guidance`, read from the class rather than
    copied into the test.
  - The output contains `UNMATERIALIZED_LANGUAGE_NOTE` under `#### go`.
  - The output does not contain `TypeScriptMaterializer.authoring_guidance`.
  - Python's section comes before Go's.
- **B9:** parametrize over `sentinel_table()`'s keys (`src/utils/materializers/__init__.py:21-27`),
  which are exactly the registered languages, without importing the private map. For each, assert
  that `language_authoring_notes([language])` has a non-empty section for that language, and that
  the section does not contain `UNMATERIALIZED_LANGUAGE_NOTE`.
- **B10:** three cases, following the `tests/unit/cli/commands/test_materialize_skeletons.py` pattern
  (`monkeypatch.chdir`, `capsys`):
  - no file: exit 0, and the output contains `NO_DECLARED_LANGUAGES_NOTE`
  - `languages = []`: exit 0, and the output contains `NO_DECLARED_LANGUAGES_NOTE`
  - a malformed TOML file: exit 1, the whitespace-normalized output names `stack.toml`, and it
    contains no `Traceback`
  - *Added during implementation and the fix pass (2026-11-13), same assertions as the malformed
    case:* a `stack.toml` that is a directory (implementation), a non-UTF-8 `stack.toml` and a
    `stack.toml` behind an untraversable `.respec-ai/config`, skipped as root (fix pass).

### 5. Step 4.5 hands the notes to the architect: `phase_command.py:402-425` (B11)

**The run.** Inside Step 4.5's `text` block, after the `LANGUAGE_CONFIGS` lines and before the
compose block (`:415`), add:

```text
RUN (Bash): respec-ai language-guidance
IF command exit code == 0:
  LANGUAGE_AUTHORING_NOTES = command output
ELSE:
  LANGUAGE_AUTHORING_NOTES = "Language authoring notes unavailable ([first line of command output]).
    Write Skeleton Index entries in the notation the phase template shows."
  Do NOT terminate the workflow. Continue with the compose block below.
```

The failure branch must fall through to the compose block. Never jump to Step 5 from it, because
that would skip composing `PROJECT_CONFIG_CONTEXT_MARKDOWN` altogether.

Add these two lines to the composed `PROJECT_CONFIG_CONTEXT_MARKDOWN`, after the closing fence of
the `### Language Config TOMLs` block (`:421-424`), not inside that fence:

```text
  ### Language Authoring Notes
  [LANGUAGE_AUTHORING_NOTES]
```

- **No grant change.** Bash is already granted unrestricted (`src/platform/template_helpers.py:173`).
- **Brace escaping.** The template is an f-string, so double any literal braces you add.
- **The architect's input description.** `phase_architect.py:197-202` gains one sentence:
  `### Language Authoring Notes` carries per-language rules for Skeleton Index and Test List
  entries, present only for the project's languages. The same edit removes this line's bias
  (item 6).

### 6. Architect neutralization: `src/platform/templates/agents/phase_architect.py` (B1, B5)

| Anchor | Today | Change to |
|---|---|---|
| `:6`, `:113-121`, `:846` | the `language_testing_convention` import, the `('python', 'typescript')` loop, and its call | Delete all three. Replace `:846-850` with: take each Test List entry's location and name form from the `[testing]` `location` and `naming` of the owning language's standards TOML in `project_config_context_markdown`, and follow that language's section of `### Language Authoring Notes`. If neither exists, follow the existing test files nearest the path. If there are none, use a plain description of the behavior. |
| `:197-202` | *"a Python+React project has both `[language.python]` and `[language.typescript]` sections"* | "a project with several languages has one `[language.<name>]` table per language", plus the item 5 sentence |
| `:318` | *"(for example Python, TypeScript, Node.js, browser, AWS Lambda)"* | Delete the parenthetical. Phase 2 removes the API inventory; this is the minimal edit. |
| `:540-542` | *"(props as the public seam, JSX/styling/hooks explicitly excluded)"* | "(a UI unit's inputs as its public seam; markup structure, styling and internal state handling excluded)" |
| `:589-591` | *"code_command.py and patch_command.py scan for it"* | "respec-code and respec-patch scan for it" |
| `:775-783` | LlamaIndex / Neo4j / Pydantic example | A language-free example, such as a storage client plus a query translator, with the same What/Why/Trade-offs and Structure/Interactions/Data Flow lines |
| `:785-793` | the lead-in *"one worked example per language present in the project"* and the fenced `python` and `typescript` signature blocks | Drop the per-language lead-in. Use one ```` ```text ```` block holding one Skeleton Index bullet, such as ``- `<path to the knowledge-base client>` :: KnowledgeBase.query(<params>) -> <Result>``, with parameter and result text in the owning language's syntax (see `### Language Authoring Notes`) |
| `:801-809` | `src/neo4j_client.py`, `src/kb/neo4j_client.py`, `tests/unit/kb/test_neo4j_client.py::test_…`, and two "Right (TypeScript)" lines | Placeholder paths with no extension, e.g. `` `<path to the storage client file>` `` and `` `<path to its test file>::reconnects after a timeout` ``. Delete both TypeScript lines. **Keep `:801`'s *"Objectives, Scope, Deliverables, Development Plan"* and `:805`'s heading verbatim**; `test_phase_design_layer.py:35` and `:38` pin them. |
| `:815-845` | per-language signature rules (Python, TypeScript, Component entries, the `ClassName.method_name` example) | The neutral rules. There is one notation for every language: `<Owner>.` is optional, and only `<params>` and `<Result>` use the language's syntax. Never write native declarations. Language-specific rules come from `### Language Authoring Notes`. Tags: `, async`, `, internal`, `, consequential`, in any order. The deleted content moves to item 4. |
| `:882-884` | *"whether the phase is React, HTMX, or server-rendered"* | "whatever UI technology the phase uses" |
| `:892-902` | *"Full Pydantic model with validators"*, *"Query 'Python errors'"*, *"Complete `Settings` class code"* | "A complete data model definition with validation code", "Query 'recent errors'", "Complete configuration-loading code". `Settings` is not on the denylist, but phase 2 keeps this block (it deletes only `:896-898` and `:904-912`), so this is the only pass that reaches it. |
| `:944` | *"Neo4j schema and LlamaIndex integration"* | "Storage schema and query-translation integration" |
| `:1293` (added in the fix pass) | *"`.best-practices/fastmcp-server-best-practices-codegen.md`"* as the "Example RIGHT" filename | `.best-practices/mcp-server-best-practices-codegen.md`. B1 missed it until `fastmcp` joined the denylist (item 1). |
| `:1133-1141`, `:1153-1159` | ```` ```sql ```` `CREATE TABLE` block and ```` ```graphql ```` schema block | ```` ```text ```` field lists in a neutral form, for example `Resource: id (identifier, required), field (text, required)`. Retitle `##### GraphQL Schema (if applicable)` to `##### Interface Schema (if applicable)`. The `{{ }}` escapes go with the block. |
| `:1320-1322` | `--tech "react,graphql" --topics "hooks,patterns"` | `--tech "<technology-a>,<technology-b>" --topics "<topic-a>,<topic-b>"` |

Run B1 after this item. On 2026-11-13 every architect hit mapped to a row above, so nothing should be
left. If a hit remains, the template has moved since then: fix the line, and add it to this table.

### 7. Verify-command fallback (B12)

**The rule.** Replace `phase_architect.py:599-605` with:

```text
- `## Checklist` → `- [ ]` items, each with `(Step N)` and `(verify: <command>)`.
  `<command>` MUST be the `[commands].test` value from the standards TOML, in
  `project_config_context_markdown`, of the language that owns the files the Step
  touches — never a hardcoded or remembered command. A Step whose files belong to
  several languages lists one `(verify: …)` per language. IF that language has no
  standards TOML, or its `[commands].test` is empty, starts with `TODO` (in any case,
  optionally bracketed), or is `no_preference`: write exactly
  `(verify: ask user — no test command configured for <language>; set [commands].test in .respec-ai/config/standards/<language>.toml)`
  with the language's name, and never substitute a guess.
```

- **Keep the pinned wording.** The new text must keep `never a hardcoded` and `[commands].test`,
  which `test_agent_templates.py:872-879` pins.
- **Why each case counts as missing:**
  - `no_preference` is what languages with no canonical command receive, and it passes validation
    (F25; `standards_config.py:226-234`, `:331-333`).
  - A language with no standards TOML at all is common: `write_project_config_files` writes TOMLs
    only for languages with detected tooling (`standards_config.py:551-556`).

**The example.** In the implementation plan example at `phase_architect.py:107-109`, replace each
`(verify: pytest …)` and `(verify: npm test)` with `(verify: <[commands].test of the language that
owns this step's files>)`. Keep the three steps and `DR-001`; `test_phase_implementation_plan_gate.py:62-73`
pins them.
- *Added during the fix pass (2026-11-13).* The example's "repository method" (`:84`, `:90`, `:107`)
  became "repository query", so the touched passage no longer assumes methods (judgment call 2).

**Cut from this phase (decided 2026-11-13, before implementation): the Step 12.6 prompt below is
NOT built.** Phase 2 deletes Step 12.6 and moves this question into the briefing, so the prompt, its
two variables and the `step_body('12.6')` half of B12 would exist only to be deleted one phase later,
which the plan rules out ("nothing is built alongside an old mode only to be deleted later"). Phase 1
still works end to end without it: the architect's marker is literal text in `implementation.md`, and
the existing Step 12.6 walkthrough shows that file to the user, who can alter it or leave the marker.
Implement only the architect rule and the example change above, and the architect half of B12. The
text below is kept as the reference design for phase 2's briefing question.

**Step 12.6 (reference only, not built): the orchestrator records the user's answer.** The architect's rule admits only config
values. A command the user types into "Alter specific parts" would therefore be re-marked on
regeneration, and `PROJECT_CONFIG_CONTEXT_MARKDOWN` is never rebuilt after Step 4.5. So the way
out is orchestrator-side and deterministic, in line with README "Relay protocol" step 5. Place it at
the top of Step 12.6's text block, before the walkthrough (`phase_command.py:1016-1017`):

```text
IF IMPLEMENTATION_PLAN_MARKDOWN contains "(verify: ask user":
  FOR each language named in those markers that is in neither USER_VERIFY_COMMANDS nor VERIFY_MARKERS_KEPT:
    {selection_prompt_instructions}
    Header: "Verify Command"
    Question: "No test command is configured for <language>. How do its steps get verified?"
    multiSelect: false
    Options: [
      {{"label": "Type the command", "description": "Used verbatim in this phase's implementation.md only"}},
      {{"label": "Leave the marker", "description": "Set [commands].test in .respec-ai/config/standards/<language>.toml later"}}
    ]

    WAIT for {selection_response_source}.
    DO NOT treat this as workflow completion, cancellation, or failure.
    After the user responds, resume at Step 12.6. Continue immediately.
    DO NOT explain that the workflow is stopping unless the user asks why.

    IF selection == "Type the command":
      Prompt for the command. USER_VERIFY_COMMANDS[<language>] = the user's reply, verbatim.
    ELSE:
      Add <language> to VERIFY_MARKERS_KEPT.
  Replace each marker whose language is in USER_VERIFY_COMMANDS with
    "(verify: <USER_VERIFY_COMMANDS[<language>]>)" in IMPLEMENTATION_PLAN_MARKDOWN.
```

This is the source text inside the f-string, so `{selection_prompt_instructions}` and
`{selection_response_source}` stay single-braced, and the option literals are brace-doubled exactly
as at `phase_command.py:1023-1027`. The four lines from `WAIT for` to `DO NOT explain` are the
repository's standard blocking block (`:1029-1032`). Keep all four:
`test_phase_implementation_plan_gate.py:107-112` requires every `WAIT for` in Step 12.6 to have its
own `resume at Step` marker.

- **Initialization.** Add `USER_VERIFY_COMMANDS = empty map (language → command)` and
  `VERIFY_MARKERS_KEPT = []` to Step 1.1.1's variable block (`phase_command.py:200-206`).
- **Resume and re-entry.** "Resume at Step 12.6. Continue immediately." means continue with the
  `IF selection ==` handling directly below the prompt, then the next language. That is the same
  convention as Step 6's loop (`phase_command.py:565-582`), not a restart of the step. A true
  re-entry happens only when the gate's ELSE branch regenerates the plan through Step 12.5. It
  re-applies known answers and never re-asks about a language already answered or kept.
- The command is used for this phase only. Never write it into the user's TOML.
- A command the user typed is not a guess, so the invariant holds: the architect never invents a
  command, and the orchestrator records only actual user responses.
- The architect never asks the user anything. Its marker is data, and only the orchestrator turns
  it into a question (README "Relay protocol"; F10).
- This is a conditional prompt inside an existing gate. It never appears on the happy path, where
  config is present.
- Phase 2 deletes Step 12.6 and moves this question into the briefing.

**A deliberate deviation from the plan.** The plan's "Verify commands" section says the fallback
*"points to `/respec-standards`"*. That command cannot set a test command: *"This command MUST NOT
edit canonical TOML files"* (`src/platform/templates/commands/standards_command.py:16`).
- `respec-ai standards` has only `init` and `validate` (`uv run respec-ai standards --help`, run
  during review). There is no setter.
- `init` does not help either: for a language with no default it writes `no_preference` again
  (`standards_config.py:226-234`).

The marker therefore names the canonical TOML. decisions.md ("Zero language bias") and phase 2's
missing-verify-command decision already carry this correction; nothing else needs changing.

### 8. Critic and command residue (B1)

**Critic** (`src/platform/templates/agents/phase_critic.py`):
- **`:1121-1129`.** Change *"For each abstraction (interface, base class, protocol)"* to "For each
  abstraction named in `### Skeleton Index`: a seam whose purpose is substitution, whatever the
  owning language calls it".
  - Change *"use a concrete class, not an interface"* to "name the concrete unit directly instead of
    an abstraction".
  - Change the marker placeholder `{{Interface}}` to `{{seam}}`.
  - Keep the marker title `[Unjustified Seam - BLOCKING]`. `template_contract` slugs it to
    `unjustified-seam` (`tests/support/template_contract.py:28`, `:85-86`), and
    `test_phase_design_layer.py:52-60` asserts that slug.
- **`:1135-1138`.** Change *"(e.g. `tests/test_client.py` with no `::test_...` behavior name)"* to
  "(e.g. `` `<path to a test file>` `` with no `::<behavior>` part)".
- **`:1259`.** Change *"(e.g., "Create `src/neo4j_client.py`")"* to "(e.g., "Create
  `<path to a source file>`")". Phase 2 deletes the rubric, so make only this edit.

**Command** (`src/platform/templates/commands/phase_command.py`):
- **`:1332`.** Delete *"(examples: Python, TypeScript, Node.js, browser, AWS Lambda)"*. Step 16.5
  is deleted in phase 2.
- **`:313`, `:1763-1764` (added in the fix pass).** The example phase slug
  `phase-2a-neo4j-schema-and-llama-index-integration` becomes
  `phase-2a-storage-schema-and-query-translation-integration`, item 6's `:944` rewrite in kebab
  case. B1 missed it until `llama-index` joined the denylist (item 1).
- **`:1654-1655` and `:1658-1659`.** These are the Research Requirements format example. Replace the
  React, PostgreSQL and GraphQL lines with
  `- Read: .best-practices/<topic>-codegen.md` and
  `- Synthesize: Technologies: <technology names>; Topics: <topic keywords>; Query: <specific
  research request>`. PostgreSQL is not denylisted, but it goes with its example.

### 9. Tests that change, and dead code (F23)

**Delete** `test_agent_templates.py:848-857`
(`test_phase_architect_template_emits_a_typescript_signature_grammar_alongside_python`):
- It pins behavior this effort reverses on purpose.
- B1 covers its inversion universally, which is F36's fate "invert".

**Replace** `test_agent_templates.py:859-870` with B5.
- Remove the import at `:37` once it is unused.

**Delete** `language_testing_convention` (`src/platform/standards_config.py:59-63`), but only after
`grep -rn "language_testing_convention" src` shows no caller once item 6 lands.
- Delete its test (`tests/unit/platform_tests/test_standards_config.py:19-25`) and the import at
  `:9` with it.

**Must pass unchanged:**
- `test_agent_templates.py:872-879`: item 7 keeps `never a hardcoded` and `[commands].test`
- `test_agent_templates.py:903-930`: item 6's `:318` edit keeps *"Implementation language/runtime
  from the project stack"*
- `test_agent_templates.py:932-954`: the Synthesize-line shape
- `test_command_templates.py:532-556`: item 8's `:1332` edit keeps `IMPLEMENTATION_LANGUAGE_RUNTIME`
- the imperative-language audits, `test_agent_templates.py:660-681` and
  `test_command_templates.py:1176-1186` (judgment call 7)
- `test_phase_implementation_plan_gate.py:62-73`: the three steps and `DR-001`
- `test_phase_implementation_plan_gate.py:99-116`: Step 12.6's `WAIT for` count equals its
  `resume at Step` count (Step 12.6 is not edited; item 7's prompt is cut)
- `test_phase_design_layer.py:26-60`
- the existing tests in `tests/unit/cli/commands/test_materialize_skeletons.py` and
  `test_check_conformance.py`, alongside the new B7 tests
- every `test_phase_*` gate test

If one fails, the rewrite changed behavior. Fix the rewrite, not the test.

**Left alone:** `test_agent_templates.py:362-371`, the coder's TypeScript sentinel. It is frozen
respec-code, outside the guard (decisions.md guard scope).

### 10. Contract and log updates (same commit)

- **README "Shared contracts → Section naming and frozen-reader compatibility".** In the
  `implementation.md` Checklist bullet, record `(verify: ask user — …)` as the only permitted
  non-command verify value, with its exact text from item 7. README rules say a contract change
  lands there first.
- **`deferred-issues.md`, two entries:**
  - `no_preference` passes `respec-ai standards validate` for commands (F25;
    `standards_config.py:331-333`, `:345-348`). Phase 1 treats it as missing on the architect side
    only.
  - Step 3's settled route skips Step 4.5.

  Both are explained under *Out of scope*.
  - *Logged 2026-11-13.* The `standards_config.py` anchors above are HEAD's. Item 9's deletion
    of `language_testing_convention` moves them up by 7 lines, to `:324-326` and `:338-341`, and
    the log entry cites the new lines.

## Out of scope

- **Any flow change.**
  - The two acts, their loops and their gates stay as they are. The only exception is item 3's
    one-line diagnostic fix in Step 11.5. Item 7's Step 12.6 prompt is cut (see item 7).
  - The fixed report format and `## Decisions needed` belong to phase 2.
- **Asking about verify commands earlier.** Asking before any draft exists is phase 2's briefing
  (decisions.md "Zero language bias").
- **Step 3's settled-phase route skipping Step 4.5.** This is a pre-existing gap.
  - `phase_command.py:345-349` sends a `shape-settled` or `shape-amended` phase straight to Step
    13, past Step 4.5 at `:402`.
  - On that route the detail-act architect gets no `PROJECT_CONFIG_CONTEXT_MARKDOWN`: no TOMLs and
    no notes.
  - Phase 1's mechanisms are unaffected, because that route writes neither the Skeleton Index (shape
    mode) nor the Checklist (implementation-plan mode). B11's guarantee therefore covers the shape
    path only.
  - Phase 2 replaces this routing (README "Shared contracts → Stage marker → Resume"). It must run
    the guidance call on every route that invokes the architect. Log the gap in
    `deferred-issues.md`.
- **Passing project config to the critic** (F22). Phase 1 keeps the critic's checks structural.
- **Treating `no_preference` as incomplete in `_validate_language_config`.** That would make
  `respec-ai standards validate` fail, and `respec-ai regenerate` abort (it runs the same check,
  `src/cli/commands/regenerate.py:99-105`), for the six languages with no canonical command. It is
  a config-UX decision, so log it in `deferred-issues.md`.
  - *Corrected during implementation (2026-11-13).* This bullet named `respec-ai validate`, which
    does not run the standards check; `validate_project_config` is called only by
    `standards validate` and `regenerate`.
- **Tooling-detection gaps.** Only five build files are detected (F25).
- **Paradigm text in passages that phase 2 rewrites wholesale:**
  - the skeleton opt-in's "internal class" wording (`phase_architect.py:472-479`,
    `phase_command.py:600-615`)
  - the critic rubric's `Settings` class example (`phase_critic.py:1261`)

  None of these is on the denylist. Phase 2 deletes the skeleton opt-in and the rubric outright
  (its work items 4–6). The architect's own `Settings` example is in item 6, because phase 2 keeps
  that block.
- **Infrastructure and vendor placeholders and the "Web src/APIs" find-and-replace damage.** The
  placeholders are at `phase_architect.py:1185-1195`. The damage is at `phase_architect.py:1031`,
  `:1143`, `:1161`, `:1173` and `phase_critic.py:1218` (F21). They are not language bias; phase 2
  decides what happens to boilerplate sections.
- **Frozen respec-code and respec-patch templates** (decisions.md guard scope).
- **New materializers,** for example Go or Elixir. Declared languages without one get the neutral
  note.
- **The `bp` invocation** (F15). That is phase 2.

## Exit criteria

- [ ] B1–B12 were each observed failing first, then pass. For B2–B4 the failure was observed against
      a broken scanner; for B6, against the rejected placeholder.
- [ ] Both *Already done?* probes report done: pytest exits 0, and grep prints nothing.
- [ ] `uv run pytest` is green. The passed count is the baseline (1671 passed, 84 skipped), minus
      the three deleted tests (`test_agent_templates.py:848` and `:859`, and
      `test_standards_config.py:19`), plus every new test case, counting each parametrized case
      separately. B5 is one of the new tests.
- [ ] Every test listed under item 9 "Must pass unchanged" passes without edits.
- [ ] `grep -rn "test_path_convention\|language_testing_convention" src tests` prints nothing.
- [ ] In a scratch project with opencode and codex model tiers configured (F37),
      `uv run respec-ai regenerate --force --tui all` completes with no per-TUI failure. The README
      exit criteria explain why both flags are needed.
- [ ] **Manual:** run `respec-ai language-guidance` in three scratch projects:
  - one declaring `["python", "typescript"]`: each gets its own notes
  - one declaring `["go", "elixir"]`: both get the neutral note
  - one with no `stack.toml`: the neutral note, exit 0
- [ ] **Manual:** read the rendered architect's Skeleton Index, Test List and Checklist guidance from
      start to finish on one TUI. Confirm the examples still teach, that no passage you touched
      assumes classes or methods, and that the moved Python and TypeScript rules in item 4 match
      their source lines.
- [ ] **Manual:** run `respec-ai materialize-skeletons` on a native-syntax line that contains
      brackets. Confirm it prints one readable error, with the bracketed text intact, and exits 1.
- [ ] The README contract and `deferred-issues.md` are updated as in item 10.
