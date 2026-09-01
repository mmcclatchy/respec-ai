# Deferred issues

Things this refactor deliberately does not do, why, and what would justify revisiting. Anything here
is a conscious omission with a recorded reason — not an oversight and not a backlog wish list.

The standing rule from [decisions.md](decisions.md): a design decision that makes some language
second-class should be reconsidered on the spot, and only deferred when treating it first-class is
*significant* extra effort. Each entry below records which side of that line it fell on.

---

## TypeScript signature introspection

**What:** `extract_existing_signatures` for TypeScript — reading an existing `.ts`/`.tsx` file and
recovering its public signatures, which is what enables merge-into-existing-file and signature
reconciliation.

**Why deferred:** significant effort, and it needs a dependency decision that should be made with the
seam in hand rather than ahead of it. Two viable routes:

- **TypeScript compiler API** — accurate, but pulls a Node toolchain dependency into a Python CLI and
  requires the user's project to have `typescript` installed at a compatible version.
- **Regex heuristics** — no dependency, but brittle against generics, overloads, decorators, and JSX.

Python keeps introspection via stdlib `ast` (no dependency cost), so phase 1 ships with Python
introspecting and TypeScript create-only. This is exactly the asymmetry the optional-capability
protocol exists to absorb.

**Cost of the gap:** TypeScript entries whose target file already exists cannot be merged or
reconciled; they surface as create-only notices at phase 11.5. Acceptable because the common case in
a new phase is new files.

**Revisit when:** users hit the create-only notice often enough to be friction, or when a second
non-Python language needs introspection and the dependency question has to be answered anyway. Decide
the route once and apply it to both.

---

## Go, Rust, Java, and the remaining 22 languages

**What:** `LanguageMaterializer` implementations beyond Python and TypeScript.

**Why deferred:** not frontend work, and cheap to add once the seam exists — which is the point of
building the seam first. `language_standards.json` already carries `testing.framework`, `.location`,
and `.naming` for all 26 languages (F21), so the test-scaffold half is close to free. What each
language still needs is a declaration-emit template and a signature grammar.

**This is the entry most likely to be misread as "Python and TypeScript are special."** They are not.
They are the first two implementations of a protocol built for many, chosen because Python is what
exists today and TypeScript is what frontend needs. Adding a language should be a contribution, not a
refactor; if it ever isn't, the seam is wrong and that is a bug in phase 1, not a limitation here.

**Revisit when:** any user project uses a third language, or immediately if adding one turns out to
require changes outside its own materializer module.

---

## Fully polyglot `ProjectStack`

**What:** phase 3 makes per-language stack attributes attach to the correct `[language.X]` table,
which is what frontend work requires. It does not restructure every consumer of `ProjectStack` to be
language-aware.

**Why deferred:** the flat model reaches further than the stack file — detection, prompts, and several
prose-level agent instructions all assume a single project stack. Chasing all of it would balloon
phase 3 well past what frontend support needs.

**Cost of the gap:** consumers outside the stack-rendering path continue to see a primary-language
view. Where that matters for review scoping, the extension map (phase 1) is the correct mechanism
anyway, since it resolves per *file* rather than per *project*.

**Revisit when:** a reviewer or command demonstrably needs per-language stack data that phase 3 did
not thread through.

---

## Detected language name can disagree with source file extensions

**What:** `detect_project_stack` names the JS/TS half of a project from `tsconfig.json` presence (a
build-file check), not by scanning source files. A project that already has `.tsx` files but has not
added `tsconfig.json` yet detects and renders as `[language.javascript]`, while the extension map
(phase 1, used by materialization) resolves those same files to `typescript`. Pinned by
`test_detected_language_name_can_disagree_with_source_extensions_without_tsconfig` in
`tests/unit/platform_tests/test_standards_config.py` so the gap stays visible rather than silently
reintroduced or silently fixed by accident.

**Why deferred:** fixing it means detection scanning the source tree for `.tsx`/`.jsx` file
presence, which is a materially larger change (walking the project, applying the same extension map
detection uses, reconciling with the build-file-based heuristic) than phase 3's scope of "attach
attributes to the right table." `BUILD_FILE_TO_LANGUAGE`-based detection is also the existing
pattern for every other language; special-casing JS/TS to scan source now would be inconsistent with
the rest of `tooling_defaults.py` without also fixing the equivalent gap for e.g. Go/Rust.

**Cost of the gap:** the affected table is keyed `javascript` instead of `typescript` until
`tsconfig.json` is added (a one-time, easily-noticed transition most React/Vue-with-TypeScript setups
hit within their first day, since `create-vite`/`create-next-app` templates ship `tsconfig.json` from
the start). Phase 5's preflight, which reads `dev_command` from `[language.<lang>]`, must resolve the
language the same way `detect_project_stack` did — i.e., from `stack.toml`'s own `[project]` table,
not by re-deriving it from source extensions — to avoid looking in the wrong table.

**Revisit when:** phase 5 or later needs to resolve "the frontend language" from source files
directly rather than from `stack.toml`, or a user reports the mismatch as confusing in practice.

---

## Existing projects have no upgrade path to the new optional stack.toml keys

**What:** `write_project_config_files` only writes `stack.toml` when it does not already exist (an
idempotency guard that predates phase 3). A project initialized before phase 3 keeps a `stack.toml`
with no `css_framework`/`ui_components`/`dev_command`/`base_url`/`storage_state_path` keys at all, and
nothing offers to add them short of `respec-ai init --force` (which discards the rest of the existing
configuration too).

**Why deferred:** an incremental-merge writer for `stack.toml` — one that adds newly-introduced keys
to an existing file without touching what the user already configured — is a distinct, general
capability (config migration) that phase 3's scope of "make a polyglot project configure correctly"
does not require: a freshly-initialized project already gets everything phase 3 adds.

**Cost of the gap:** an existing project cannot get `dev_command`/`base_url`/`storage_state_path`
without hand-editing `stack.toml` or a full `--force` reinit. Phase 5's preflight depends on these
keys, so this becomes a real onboarding step for any project that adopted respec-ai before phase 3.

**Revisit when:** phase 5 ships and existing-project adoption friction is reported, or before phase 5
if it wants to hand users a clean upgrade path from day one. The likely fix is a targeted "add missing
keys" merge step, not a general config migration framework.

---

## Agent Teams as a coordination substrate

**What:** Claude Code shipped Agent Teams in v2.1.178+ — teammates in independent context windows,
peer messaging via `SendMessage`, a shared task list under `~/.claude/tasks/{team-name}/`, per-agent
mailboxes, and task dependencies. Phase 9's frontend and backend coders are an obvious candidate.

**Why deferred:** three blockers, in order (**F33**).
- **Experimental, disabled by default.** Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. respec-ai
  generates agents that run in *other people's* projects and cannot set that flag for them. Generated
  workflows silently assuming it would fail confusingly.
- **Not declarable in respec-ai's output surface.** The docs state that subagents cannot coordinate via
  their frontmatter definition, and no team field exists among supported `.claude/agents/*.md` keys.
  Teams are session-level configuration.
- **Claude Code only**, with no confirmed OpenCode or Codex equivalent.

**Cost of the gap: smaller than it looks, and this is the important part.** What two coders would
negotiate is the interface between them, and the design layer already fixes it before either runs —
`### Skeleton Index` and `### Collaboration And Wiring`, human-approved at the shape gate and
materialized as skeleton files (**F36**). Runtime messaging would let two agents renegotiate a contract
the human already approved, which inverts the point of the gate. What remains is mid-implementation
deviation, which reaches the other coder one iteration later through the handoff report's `Deviations:`
field — affordable within an 8-iteration budget — and phase 7's seam review verifies empirically that
the two sides met.

**Revisit when:** teams graduate from experimental *and* team membership becomes declarable in agent
frontmatter. Both are required; the first alone does not help, because respec-ai's entire output surface
is frontmatter plus command orchestration. At that point adopt it as a capability tier following the
phase-8 pattern — an adapter change plus an orchestrator option, not a redesign.

**What would genuinely change the calculus:** evidence that one-iteration deviation latency is actually
costing convergence on real mixed phases. If phase 9 ships and mixed phases routinely burn iterations on
FE/BE round-trips, that is the signal. Measure before assuming.

---

## Design-tool integration for OpenCode and Codex

**What:** phase 8 wires Claude Design for Claude Code — `/respec-design-sync`, and live-project reads in
the architect. OpenCode and Codex get the capability declaration point (`None` in their
`builtin_tool_name_map`) and nothing more.

**Why deferred:** neither has anything equivalent to wire. This is not respec-ai choosing to under-serve
them — there is no OpenCode or Codex design tool to integrate. Building speculative abstraction for an
unknown future tool would be guessing at its shape.

**Cost of the gap:** none to correctness. Both use the portable design-source path — a local handoff
bundle, tokens file, or named components — which phase 4 guarantees is sufficient on its own and which
phase 8's B7 asserts produces an equally good UX Contract. What they lack is the *convenience* of
pushing a component library up and reading a live project back.

**What makes revisiting cheap:** the capability is declared per adapter and generated prose branches on
it (**F29**), and phase 8 adds the optional-grant primitive that lets a tool be granted where it exists
and skipped where it does not (**F32**). So adding an equivalent later is: implement the tool name in
that adapter's `builtin_tool_name_map`, let command filtering pick it up, adjust the adapter-derived
counts. No redesign.

**Revisit when:** OpenCode or Codex ships a design tool with a comparable API. Check first whether its
model is push-a-library-up (like `DesignSync`) or export-a-bundle-down — if the latter, it may need no
wiring at all, since the portable path already covers it.

---

## Generic multi-server MCP registrar

**What:** `respec-ai register-mcp` currently registers exactly one server. `claude_config.py` hardcodes
`MCP_SERVER_NAME = 'respec-ai'` (`:9-15`) and there is no generic path for a second server (F28).

**Why deferred:** generalizing it touches all three `TuiAdapter.register_mcp_server` implementations
plus their permission-writing counterparts. Worthwhile refactor; poor prerequisite — it would gate
frontend review on unrelated CLI surgery.

**What ships instead:** the one-line manual install per TUI is documented, and
`frontend-preflight --status` reports `playwright_mcp_registered` so the preflight gate can act on its
absence rather than failing obscurely.

**Revisit when:** a second third-party MCP server is needed, or when manual Playwright MCP setup
proves to be a common support burden. At that point do it properly for all three adapters at once.

---

## Authentication beyond a hand-generated `storageState`

**What:** the reviewer supports one optional `storage_state_path` pointing at a Playwright
`storageState` JSON the user generates once by hand.

**Why deferred:** a real auth framework — credential storage, login-flow scripting, token refresh,
per-environment secrets — is a large surface with security implications, and it is not what makes
frontend review work. Most of the value is in reviewing unauthenticated routes plus authenticated ones
behind a static session.

**Cost of the gap:** projects whose sessions expire quickly, or whose login cannot produce a reusable
`storageState`, get review only of their public routes. The UX Contract's `#### Route Index` auth
column tells the reviewer which those are, and the rest are reported as skipped context rather than
silently unreviewed.

**Revisit when:** a project's reviewable surface is mostly authenticated and `storageState` proves
insufficient. Prefer scripting the login as a `seed_command` before building anything framework-shaped.

---

## Coder-authored end-to-end specs as the frontend Test List

**What:** having `respec-coder` write Playwright specs inside its existing TDD cycle, so they become
committed, replayable artifacts that the reviewer executes rather than re-deriving.

**Why deferred:** attractive — it reuses the whole TDD and Test List scaffold machinery instead of
building a second verification path — but it depends on the language seam (phase 1) and the per-language
Test List grammar (phase 2) both being solid, and it is best judged after the UX Contract has proven
itself in practice. Committing to it early risks encoding flows into specs before the contract format
has settled.

**Revisit when:** phases 4 and 7 have run on a real project and the UX Contract's
`#### Interaction Flows` format has stabilized. At that point the specs are close to a mechanical
translation of the contract, which is the right time to automate it.

---

## `no_preference` passing validation, and the six unconfigured languages

**What:** `_is_incomplete_value` (`standards_config.py:322-324`) does not reject `no_preference`, so
`standards init` for `c`, `clojure`, `dart`, `objective-c`, `powershell`, or `terraform` writes
all-`no_preference` commands and `standards validate` passes (F24). The project appears fully
configured with zero enforceable quality gates.

**Why deferred:** a real bug, but orthogonal to frontend support and to the language seam — it is about
*command* configuration, not materialization. Folding it in would widen phases already carrying their
own risk.

**Revisit:** soon, and independently. It is small, self-contained, and the fix is obvious: reject
`no_preference` for command keys in `_validate_language_config`. Pair it with wiring up the dead
`build_language_template()` (`:257-274`) to give unshipped languages a bring-your-own path (F26).

---

## De-privileging Python in project detection

**What:** `BUILD_FILE_TO_LANGUAGE` insertion order makes `primary_language` default to Python whenever
a `pyproject.toml` exists, and `detect_project_stack` runs only the first matching detector (F2).

**Partially addressed:** phase 3 fixes the multi-detector problem, because polyglot detection is a
hard requirement for frontend work.

**Still deferred:** the broader question of how `primary_language` *should* be chosen when a repo has
several — file counts, build-file precedence, explicit user declaration. Phase 3 makes detection
complete; it does not make the primary-language heuristic smart.

**Revisit when:** a user reports the wrong primary language on a genuinely polyglot repo. The right
fix is probably to ask during `init` rather than to guess better.

---

## Knowledge-base grounding for the roadmap and plan workflows

**What:** `best-practices-rag` is wired into exactly one agent — `phase_architect.py`, whose Step
0.6 runs `query-kb` and whose unresolved gaps become `Synthesize:` prompts executed at
`phase_command.py` Step 16.5. Phase 10 extends that to the shape act. Neither `roadmap.py` nor
`plan_analyst.py` / the plan workflow queries the KB at all; `roadmap.py`'s single
`best-practices` reference is an example string in a heading format.

**Why deferred:** roadmap decomposition is plausibly where ecosystem convention matters *most* —
how a plan splits into phases follows framework structure closely, and a Next.js app conventionally
decomposes into routes, layouts, and server components in ways a model may or may not reproduce. But
the roadmap workflow has its own refinement loop with its own critic, and adding a research step
there means re-deciding the same cost questions phase 10 just answered for the shape act, in a
workflow whose iteration profile has not been examined. Folding it into phase 10 would double that
phase's surface and its risk.

**The constraint any future version inherits:** `phase_command.py:1257-1265` states that the phase
command is the **only** workflow that runs `bp` synthesis. Grounding the roadmap in the KB via
`query-kb` alone (the free half) does not violate it; adding synthesis there does, and would need
that policy amended deliberately rather than by implication.

**Cost of the gap:** roadmap phase boundaries are drawn from the model's priors rather than from
stored convention. Downstream this is partly recoverable — the shape act can still restructure
within a phase — but a badly-drawn phase boundary is not something the shape act can fix, since it
operates inside one phase.

**Revisit when:** phase 10 has run on real projects and the Step 5.5 election data shows what users
actually want researched. If the gaps they elect are consistently structural ("how does this
framework organize a feature") rather than local ("how does this hook work"), that is evidence the
need is upstream of the phase, in the roadmap. Measure before building.
